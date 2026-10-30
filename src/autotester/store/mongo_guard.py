"""The only door to the AutoTester Mongo database (contract mongo-store M1-M12; D-120..D-122).

The code is the only fence (the Mongo user can write other databases): the single write
`MongoClient` site, `client[StoreConfig.database]` and nothing else. No API takes a database name,
the URI never selects one (it is parsed as the driver parses it, only to REFUSE a clash, and is
never stored, logged or echoed), and the verb set has no `aggregate`, `command`, `drop*`, `rename`.
"""

from __future__ import annotations

import os
import re
import weakref
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from gridfs import GridFSBucket
from gridfs.errors import NoFile
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.uri_parser import parse_uri

from autotester.schema.store_config import StoreConfig, StoreConfigError, load_store_config

__all__ = ["COLLECTIONS", "INSERT_ONLY", "GuardedBucket", "GuardedCollection", "GuardedStore",
           "InsertOnlyCollection", "StoreConfigError", "StoreDuplicateKey", "StoreNotFound",
           "StoreUnavailable"]

COLLECTIONS = frozenset({
    "projects", "project_docs", "sources", "source_docs", "source_media", "cases", "case_proposals",
    "rubrics", "issues", "requests", "user_personas", "flow_plans", "approvals",
    "approval_revocations", "bench_docs", "bug_events", "bug_config", "scripts", "reviews",
    "ai_docs", "runs", "run_results", "run_verdicts", "run_docs", "run_traces", "bundles", "crawls",
    "crawl_nodes", "crawl_edges", "crawl_issues", "crawl_network", "crawl_docs", "crawl_summaries",
    "kg_nodes", "kg_edges", "schedule_claims", "schedule_records", "delivery_records",
    "notification_prefs", "server_state", "audit_log", "drive_jobs", "auth_users", "auth_groups",
    "auth_sessions", "auth_grants", "auth_meta", "video_shares", "video_links", "access_requests",
    "video_comments", "secrets", "browser_sessions",
})
INSERT_ONLY = frozenset({"approvals", "approval_revocations", "bug_events", "delivery_records"})
UPDATE_OPERATORS = frozenset({"$set", "$setOnInsert", "$inc"})
IMMUTABLE_FIELDS = frozenset({"_id", "generation"})
FORBIDDEN_QUERY_KEYS = frozenset({"$where", "$function", "$accumulator"})
SMOKE_COLLECTION = re.compile(r"t_[a-z0-9_]{1,30}")
MARKER_ID, MARKER_COLLECTION, SCHEMA_VERSION, BUCKET_NAME = "marker", "server_state", 1, "blobs"
# Test seams (tests/fake_mongo.seams only); _REGISTRY keeps driver objects out of instance dicts.
_SEAM: dict[str, Any] = {"config_path": None, "client_factory": None, "bucket_factory": None}
_REGISTRY: weakref.WeakKeyDictionary[Any, Any] = weakref.WeakKeyDictionary()


class StoreUnavailable(RuntimeError):
    """The server did not answer. Carries only the exception CLASS name, never a URI (M9)."""


class StoreDuplicateKey(RuntimeError):
    """A unique index or `_id` was violated: the loser of an exclusive create."""


class StoreNotFound(KeyError):
    """No such blob or revision."""


def _translate(call: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        return call(*args, **kwargs)
    except DuplicateKeyError:
        verdict: Exception = StoreDuplicateKey("duplicate key")
    except NoFile:
        verdict = StoreNotFound("no such blob")
    except PyMongoError as exc:
        verdict = StoreUnavailable(f"state store unavailable ({type(exc).__name__})")
    raise verdict  # outside `except`: no __context__ keeps the driver exception (or its URI)


def _check_query(value: Any) -> None:
    kids = value.items() if isinstance(value, Mapping) else enumerate(
        value if isinstance(value, list | tuple) else ())
    for key, inner in kids:  # list positions are ints and never an operator name
        if key in FORBIDDEN_QUERY_KEYS:
            raise ValueError(f"query operator {key} is not allowed")
        _check_query(inner)


def _require_filter(filter_: Mapping[str, Any]) -> None:
    if not isinstance(filter_, Mapping) or not filter_:
        raise ValueError("a write needs a non-empty filter")
    _check_query(filter_)


def _check_update(update: Mapping[str, Any]) -> None:
    if not update or set(update) - UPDATE_OPERATORS:
        raise ValueError("update operators are limited to $set, $setOnInsert and $inc")
    for fields in update.values():
        if not isinstance(fields, Mapping):
            raise ValueError("an update operator takes a document of fields")
        for name in fields:
            if str(name).split(".")[0] in IMMUTABLE_FIELDS:
                raise ValueError(f"field {name} is immutable")


def _scoped(filter_: Mapping[str, Any]) -> None:
    """`delete_many` must name a project or key by equality or `$in` of plain strings."""
    for key in ("p", "k"):
        value = filter_.get(key)
        if isinstance(value, Mapping) and set(value) == {"$in"}:
            value = value["$in"]
        listed = value if isinstance(value, list) else [value]
        if value and all(isinstance(v, str) and v for v in listed):
            return
    raise ValueError("delete_many needs p or k (equality or $in of non-empty strings)")


class InsertOnlyCollection:
    """Read, insert and index. The whole surface of an insert-only collection (M7)."""

    def __init__(self, store: GuardedStore, name: str, raw: Any) -> None:
        self._store, self._name = store, name
        _REGISTRY[self] = raw  # no attribute or method of this object returns it

    def find(self, filter: Mapping[str, Any] | None = None, *, projection: Any = None,
             sort: Any = None, limit: int = 0) -> list[dict[str, Any]]:
        _check_query([filter or {}, projection or {}])
        kwargs = {k: v for k, v in dict(projection=projection, sort=sort, limit=limit).items() if v}
        return [*_translate(lambda: list(_REGISTRY[self].find(dict(filter or {}), **kwargs)))]

    def find_one(self, filter: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
        _check_query(filter or {})
        return _translate(_REGISTRY[self].find_one, dict(filter or {}))  # type: ignore[no-any-return]

    def count_documents(self, filter: Mapping[str, Any] | None = None) -> int:
        _check_query(filter or {})
        return int(_translate(_REGISTRY[self].count_documents, dict(filter or {})))

    def insert_one(self, document: Mapping[str, Any]) -> Any:
        self._store._before_write(self._name, document)
        return _translate(_REGISTRY[self].insert_one, dict(document)).inserted_id

    def create_index(self, keys: list[tuple[str, int]], *, unique: bool = False,
                     name: str | None = None) -> str:
        self._store._before_write(self._name, {})
        extra = {"name": name} if name else {}
        return str(_translate(_REGISTRY[self].create_index, keys, unique=unique, **extra))


class GuardedCollection(InsertOnlyCollection):
    """Adds the four mutating verbs. `aggregate`/`command`/`bulk_write`/`drop*` do not exist."""

    def replace_one(self, filter: Mapping[str, Any], replacement: Mapping[str, Any], *,
                    upsert: bool = False) -> bool:
        _require_filter(filter)
        _check_query(replacement)
        if "_id" in replacement and replacement["_id"] != filter.get("_id"):
            raise ValueError("a replacement cannot change or introduce _id")
        self._store._before_write(self._name, filter, selects=True)
        result = _translate(_REGISTRY[self].replace_one, dict(filter), dict(replacement),
                            upsert=upsert)
        return bool(result.matched_count or result.upserted_id is not None)

    def update_one(self, filter: Mapping[str, Any], update: Mapping[str, Any], *,
                   upsert: bool = False) -> bool:
        _require_filter(filter)
        _check_update(update)
        self._store._before_write(self._name, filter, selects=True)
        result = _translate(_REGISTRY[self].update_one, dict(filter), dict(update), upsert=upsert)
        return bool(result.matched_count or result.upserted_id is not None)

    def delete_one(self, filter: Mapping[str, Any]) -> bool:
        _require_filter(filter)
        self._store._before_write(self._name, filter, selects=True)
        return bool(_translate(_REGISTRY[self].delete_one, dict(filter)).deleted_count)

    def delete_many(self, filter: Mapping[str, Any]) -> int:
        _require_filter(filter)
        _scoped(filter)
        self._store._before_write(self._name, filter, selects=True)
        return int(_translate(_REGISTRY[self].delete_many, dict(filter)).deleted_count)


class GuardedBucket:
    """GridFS bucket `blobs` inside the configured database. Revisions are append-only."""

    def __init__(self, store: GuardedStore, raw: Any) -> None:
        self._store = store
        _REGISTRY[self] = raw

    def upload(self, filename: str, data: bytes, *, metadata: Mapping[str, Any]) -> Any:
        self._store._before_write("fs", {})
        return _translate(_REGISTRY[self].upload_from_stream, filename, data,
                          metadata=dict(metadata))

    def download(self, filename: str, revision: int = -1) -> bytes:
        stream = _translate(_REGISTRY[self].open_download_stream_by_name, filename, revision)
        return bytes(_translate(stream.read))

    def revisions(self, filename: str) -> list[dict[str, Any]]:
        files = _translate(lambda: list(_REGISTRY[self].find({"filename": filename})))
        return [{"id": f._id, "filename": f.filename, "length": f.length,
                 "metadata": dict(f.metadata or {})} for f in files]

    def delete(self, file_id: Any) -> None:
        self._store._before_write("fs", {})
        _translate(_REGISTRY[self].delete, file_id)


def _uri_path_database(uri: str) -> str:
    """The database the DRIVER reads from `uri` (same parser, no DNS), or ''. Any failure is one
    fixed `StoreConfigError`, raised outside the `except` so nothing chained carries the URI."""
    scheme, _, rest = uri.partition("://")
    try:
        ("mongodb", "mongodb+srv").index(scheme)  # ValueError for any other scheme
        return parse_uri("mongodb://" + rest, validate=False)["database"] or ""
    except Exception:
        pass
    raise StoreConfigError("the store connection string is not a valid mongodb:// URI")


def _default_client(uri: str) -> Any:
    return MongoClient(uri, appname="autotester", serverSelectionTimeoutMS=5000)


class GuardedStore:
    """Holds the one connection. No attribute returns a client, a database or a database name."""

    def __init__(self, uri: str) -> None:
        cfg: StoreConfig = load_store_config(_SEAM["config_path"])
        if _uri_path_database(uri).casefold() == cfg.database.casefold():
            raise StoreConfigError("the connection string path names the store database")
        failed = ""  # a driver message may quote the URI: keep the class name, raise after `except`
        try:
            database = (_SEAM["client_factory"] or _default_client)(uri)[cfg.database]
        except Exception as exc:
            failed = type(exc).__name__
        if failed:
            raise StoreUnavailable(f"cannot open the state store ({failed})")
        _REGISTRY[self] = (database, _SEAM["bucket_factory"] or GridFSBucket)
        self._cfg, self._marked = cfg, False
        self._verify_identity(database)

    def _verify_identity(self, handle: Any) -> None:
        marker = _translate(handle[MARKER_COLLECTION].find_one, {"_id": MARKER_ID})
        if marker is not None:
            self._check_marker(marker)
        elif _translate(handle.list_collection_names):
            raise StoreConfigError("database exists, has collections and no store identity marker")

    def _check_marker(self, marker: Mapping[str, Any]) -> None:
        if str(marker.get("database", "")).casefold() != self._cfg.database.casefold():
            raise StoreConfigError("store identity marker belongs to another database")
        self._marked = True

    def _before_write(self, collection: str, target: Mapping[str, Any], *,
                      selects: bool = False) -> None:
        """`selects`: `target` is a filter; on `server_state` it must name one `_id`."""
        ident = target.get("_id")
        if collection == MARKER_COLLECTION and (
                ident == MARKER_ID or (selects and not isinstance(ident, str))):
            raise ValueError("the store identity marker is not writable")
        if not self._marked:
            self.ensure_marker()

    def ensure_marker(self) -> None:
        """Insert-only: written once, never rewritten (M11)."""
        database = _REGISTRY[self][0]
        doc = {"_id": MARKER_ID, "database": self._cfg.database,
               "created_at": datetime.now(UTC).isoformat(), "schema_version": SCHEMA_VERSION}
        try:
            _translate(database[MARKER_COLLECTION].insert_one, doc)
        except StoreDuplicateKey:
            doc = _translate(database[MARKER_COLLECTION].find_one, {"_id": MARKER_ID})
        self._check_marker(doc)

    def collection(self, name: str) -> GuardedCollection | InsertOnlyCollection:
        if name not in COLLECTIONS and not self._smoke_allowed(name):
            raise ValueError(f"collection {name!r} is not in the closed COLLECTIONS set")
        kind = InsertOnlyCollection if name in INSERT_ONLY else GuardedCollection
        return kind(self, name, _REGISTRY[self][0][name])

    @staticmethod
    def _smoke_allowed(name: str) -> bool:
        """M47: the human-run live smoke only, never under CI."""
        return (os.environ.get("AUTOTESTER_LIVE_MONGO_TEST") == "1"
                and not any(k.upper() == "CI" for k in os.environ)
                and SMOKE_COLLECTION.fullmatch(name) is not None)

    def bucket(self) -> GuardedBucket:
        database, factory = _REGISTRY[self]
        return GuardedBucket(self, factory(database, BUCKET_NAME))

    def collection_names(self) -> list[str]:
        return sorted(_translate(_REGISTRY[self][0].list_collection_names))

    def identity(self) -> dict[str, str]:  # the configured name is not a secret
        return {"database": self._cfg.database}

    def ping(self) -> None:
        _translate(_REGISTRY[self][0].command, "ping")

    def __repr__(self) -> str:
        return f"GuardedStore(database={self._cfg.database!r})"
