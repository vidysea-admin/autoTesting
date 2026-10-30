"""`MongoBackend`: the `StateBackend` over the one configured Mongo database (mongo-store U4).

One job: turn a state key and its text into documents, through `store.mongo_guard.GuardedStore`
and nothing else (M2, M5, M6: no database name is ever named here). A `.jsonl` key is an ordered
set of row documents `(k, seq)`; any other key is one document `_id = key` holding the text
verbatim, so `get` returns byte-for-byte what `put` stored (M18). Every write passes the secret
gate and the size cap first (M8, M18); insert-only collections (D-018) refuse replace, update and
delete with a named error (M7).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any

from autotester.core.env import MONGO_URI_ENV, mongo_uri
from autotester.core.redact import Redactor
from autotester.core.safe_names import safe_key
from autotester.store import mongo_routes as routes
from autotester.store.mongo_guard import (
    INSERT_ONLY,
    GuardedCollection,
    GuardedStore,
    StoreDuplicateKey,
    StoreUnavailable,
)
from autotester.store.mongo_routes import repo_redactor  # re-exported: the secret gate's default

__all__ = ["MongoBackend", "default_backend", "repo_redactor", "reset_default_backend"]

LOG = logging.getLogger(__name__)
MAX_DOC_BYTES, WARN_DOC_BYTES, APPEND_RETRIES = 12 * 1024 * 1024, 4 * 1024 * 1024, 8
INDEXES: tuple[tuple[list[tuple[str, int]], bool, str], ...] = (
    ([("k", 1)], False, "k"), ([("p", 1), ("k", 1)], False, "p_k"),
    ([("k", 1), ("seq", 1)], True, "k_seq"),
)
HAS_TEXT = {"text": {"$exists": True}}  # the identity marker shares `server_state`: not state
_CACHE: dict[str, MongoBackend] = {}


def _doc(route: routes.Route, key: str, text: str, seq: int | None = None) -> dict[str, Any]:
    """A document (`seq` None: `_id` is the key, `h` its digest) or one row of a row set."""
    base = {"k": key, "p": route.project, "text": text, "updated_at": time.time()}
    if seq is None:
        return {"_id": key, **base, "h": routes.text_sha(text)}
    return {"_id": f"{key}|{seq}", **base, "seq": seq}


class MongoBackend:
    def __init__(self, store: GuardedStore, redactor: Redactor | None = None) -> None:
        self._store, self._redactor = store, redactor
        self.ensure_indexes()

    def ensure_indexes(self) -> None:
        for name in sorted(routes.ROUTED_COLLECTIONS):
            for keys, unique, label in INDEXES:
                self._store.collection(name).create_index(keys, unique=unique, name=label)

    def _guard(self, key: str, text: str) -> None:
        self._redactor = self._redactor or repo_redactor()
        refused = False
        try:
            self._redactor.assert_clean(f"{key}\n{text}")
        except ValueError:
            refused = True
        if refused:  # outside `except`: nothing chained; neither the key nor the text is quoted
            raise routes.StoreSecretRefused("refusing to store: the key or text carries a secret")
        size = len(text.encode("utf-8"))
        if size > MAX_DOC_BYTES:
            raise routes.StoreDocTooLarge(f"{key!r} is {size} bytes; the limit is {MAX_DOC_BYTES}")
        if size > WARN_DOC_BYTES:
            LOG.warning("state document %s is %d bytes", key, size)

    def _route(self, key: str, *, rows: bool | None = None) -> routes.Route:
        route = routes.route(safe_key(key))
        if rows is not None and route.rows != rows:
            raise ValueError(f"{key!r} is {'not ' if rows else ''}a .jsonl row set")
        return route

    def _mutable(self, route: routes.Route) -> GuardedCollection:
        coll = self._store.collection(route.collection)
        if not isinstance(coll, GuardedCollection):
            raise routes.StoreImmutable(f"{route.collection} is insert-only (D-018)")
        return coll

    def _docs(self, route: routes.Route, key: str) -> list[dict[str, Any]]:
        return self._store.collection(route.collection).find({"k": key}, sort=[("seq", 1)])

    def get(self, key: str) -> str | None:
        route = self._route(key)
        if route.rows:
            lines = self.rows(key)
            return "".join(f"{line}\n" for line in lines) if lines else None
        doc = self._store.collection(route.collection).find_one({"_id": key, **HAS_TEXT})
        return None if doc is None else self._text_of(doc, key)

    def put(self, key: str, data: str | bytes) -> None:
        text = data.decode("utf-8") if isinstance(data, bytes) else data
        route = self._route(key)
        if route.rows:
            self.replace_rows(key, [line for line in text.splitlines() if line.strip()])
            return
        self._guard(key, text)
        old = self._generation(route, key)
        doc = self._build(route, key, text)
        coll = self._store.collection(route.collection)
        if isinstance(coll, GuardedCollection):
            coll.replace_one({"_id": key}, doc, upsert=True)
        elif not self._claim(coll, doc) and (
                (coll.find_one({"_id": key}) or {}).get("text") != doc["text"]):  # same text: no-op
            raise routes.StoreImmutable(f"{key!r} already exists and its collection is insert-only")
        if old and old != doc.get("split"):
            self._drop_graph(key, old)

    def put_if(self, key: str, text: str, expect_sha: str | None) -> bool:
        route = self._route(key, rows=False)
        coll = self._mutable(route)
        self._guard(key, text)
        if expect_sha is None:
            return self._claim(coll, _doc(route, key, text))
        return coll.replace_one({"_id": key, "h": expect_sha}, _doc(route, key, text))

    def create_exclusive(self, key: str, text: str) -> bool:
        route = self._route(key, rows=False)
        self._guard(key, text)
        return self._claim(self._store.collection(route.collection), _doc(route, key, text))

    @staticmethod
    def _claim(coll: Any, doc: dict[str, Any]) -> bool:
        try:
            coll.insert_one(doc)
        except StoreDuplicateKey:
            return False
        return True

    def delete(self, key: str) -> bool:
        route = self._route(key)
        coll = self._mutable(route)
        if route.rows:
            hits = self._docs(route, key)  # by _id: the catch-all refuses a bare k filter
            return bool([coll.delete_one({"_id": hit["_id"]}) for hit in hits])
        old = self._generation(route, key)
        gone = coll.delete_one({"_id": key})
        if old:
            self._drop_graph(key, old)
        return gone

    def exists(self, key: str) -> bool:
        route = self._route(key)
        flt = {"k": key} if route.rows else {"_id": key, **HAS_TEXT}
        return self._store.collection(route.collection).count_documents(flt) > 0

    def mtime(self, key: str) -> float | None:
        coll = self._store.collection(self._route(key).collection)
        stamps = [d["updated_at"] for d in coll.find({"k": key})]
        return max(stamps) if stamps else None

    def keys(self, prefix: str, suffix: str = "") -> list[str]:
        safe_key(prefix, prefix=True)
        found = {doc["k"] for name in {c for c, _ in routes.under(prefix.rpartition("/")[0])}
                 for doc in self._store.collection(name).find(
                     {"k": {"$regex": "^" + re.escape(prefix)}}, projection={"k": 1})}
        return sorted(k for k in found if k.endswith(suffix))

    def children(self, key: str, suffix: str = "") -> list[str]:
        base = safe_key(key) if key else ""
        return routes.child_names(self.keys(base + "/" if base else ""), base, suffix)

    def is_dir(self, key: str) -> bool:
        return bool(self.keys(safe_key(key) + "/")) if key else True

    def delete_prefix(self, prefix: str) -> int:
        victims = [k for k in self.keys(routes.require_scope(prefix)) if routes.within(k, prefix)]
        for victim in victims:  # check first: an insert-only family refuses before any delete
            if routes.route(victim).collection in INSERT_ONLY:
                raise routes.StoreImmutable(f"{victim!r} is in an insert-only collection (D-018)")
        return sum(self.delete(k) for k in victims)

    def rows(self, key: str) -> list[str]:
        route = self._route(key)
        if not route.rows:
            return [line for line in (self.get(key) or "").splitlines() if line.strip()]
        return [d["text"] for d in self._docs(route, key)]

    def append_text(self, key: str, text: str) -> None:
        """Extend a log: a row set gets one row per line (all vetted first), a document a CAS."""
        if self._route(key).rows:
            lines = list(filter(str.strip, text.splitlines()))
            for line in lines:
                self._guard(key, line)
            for line in lines:
                self.append_row(key, line)
            return
        for _ in range(16 * APPEND_RETRIES):
            old = self.get(key)
            if self.put_if(key, (old or "") + text, None if old is None else routes.text_sha(old)):
                return
        raise StoreUnavailable("state store unavailable (append kept losing to other writers)")

    def append_row(self, key: str, text: str) -> None:
        route = self._route(key, rows=True)
        self._guard(key, text)
        coll = self._store.collection(route.collection)
        for _ in range(APPEND_RETRIES):  # (k, seq) is unique: a racing writer makes us retry
            last = coll.find({"k": key}, sort=[("seq", -1)], limit=1)
            if self._claim(coll, _doc(route, key, text, (last[0]["seq"] if last else 0) + 1)):
                return
        raise StoreUnavailable("state store unavailable (append kept losing to other writers)")

    def upsert_row(self, key: str, field: str, value: str, text: str) -> None:
        route = self._route(key, rows=True)
        coll = self._mutable(route)
        hits = [d for d in self._docs(route, key) if routes.row_matches(d["text"], field, value)]
        if not hits:
            return self.append_row(key, text)
        self._guard(key, text)
        for hit in hits:
            coll.replace_one({"_id": hit["_id"]}, {**hit, "text": text, "updated_at": time.time()})
        return None

    def delete_row(self, key: str, field: str, value: str) -> bool:
        route = self._route(key, rows=True)
        coll = self._mutable(route)
        hits = [d for d in self._docs(route, key) if routes.row_matches(d["text"], field, value)]
        for hit in hits:
            coll.delete_one({"_id": hit["_id"]})
        return bool(hits)

    def replace_rows(self, key: str, rows: list[str]) -> None:
        """New rows go in after the old ones, then the old ones go: a crash leaves duplicates,
        never a lost set."""
        route = self._route(key, rows=True)
        coll = self._mutable(route)
        for row in rows:
            self._guard(key, row)
        old = self._docs(route, key)
        base = max((d["seq"] for d in old), default=0)
        for number, row in enumerate(rows, start=1):
            coll.insert_one(_doc(route, key, row, base + number))
        for doc in old:
            coll.delete_one({"_id": doc["_id"]})

    def ping(self) -> None:
        self._store.ping()

    def _build(self, route: routes.Route, key: str, text: str) -> dict[str, Any]:
        """The document to store; a persona over 4 MB keeps its graph as `kg_*` rows instead."""
        doc = _doc(route, key, text)
        parts = (routes.split_graph(text) if key.endswith(routes.PERSONA_SUFFIX)
                 and len(text.encode("utf-8")) > routes.KG_SPLIT_BYTES else None)
        if parts is None:
            return doc
        skeleton, nodes, edges = parts
        generation = uuid.uuid4().hex[:12]
        for name, items in zip(routes.KG_COLLECTIONS, (nodes, edges), strict=True):
            coll = self._store.collection(name)
            for seq, item in enumerate(items, start=1):
                coll.insert_one(_doc(route, f"{key}@{generation}", item, seq))
        return {**doc, "text": skeleton, "split": generation}

    def _generation(self, route: routes.Route, key: str) -> str | None:
        if not key.endswith(routes.PERSONA_SUFFIX):
            return None
        doc = self._store.collection(route.collection).find_one({"_id": key})
        return doc.get("split") if doc else None

    def _text_of(self, doc: dict[str, Any], key: str) -> str:
        generation = doc.get("split")
        if not generation:
            return str(doc["text"])
        nodes, edges = ([d["text"] for d in self._store.collection(name).find(
            {"k": f"{key}@{generation}"}, sort=[("seq", 1)])] for name in routes.KG_COLLECTIONS)
        return routes.join_graph(doc["text"], nodes, edges)

    def _drop_graph(self, key: str, generation: str) -> None:
        for name in routes.KG_COLLECTIONS:
            coll = self._store.collection(name)
            if isinstance(coll, GuardedCollection):
                coll.delete_many({"k": f"{key}@{generation}"})


def default_backend() -> MongoBackend:
    """The process's one backend, opened on first use from `core.env.mongo_uri` (U9)."""
    if "backend" not in _CACHE:
        uri = mongo_uri()
        if not uri:
            raise routes.StoreSelectionError(f"{MONGO_URI_ENV} is not set; the store needs it")
        _CACHE["backend"] = MongoBackend(GuardedStore(uri))  # gate: repo_redactor() lazily
    return _CACHE["backend"]


def reset_default_backend() -> None:
    _CACHE.clear()


def default_store() -> GuardedStore:  # the credential door's handle on `secrets` (U11)
    return default_backend()._store
