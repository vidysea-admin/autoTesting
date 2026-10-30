"""The write-transaction primitives of the Mongo auth store (mongo-store U6b), over
`store.mongo_guard` only: the write LEASE (`auth_meta/tx_lock`: insert under a unique `_id`, take
over an expired one by compare-and-set), the UNDO log that rolls a refused change back whole, and
the never-reused id counter. Mongo promises one document at a time, so these three are what make
first-admin, claim and the last-admin check (AU7, AU9, D-109) see one writer. No auth rule lives
here and no database name (M2/M5)."""

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from autotester.store.mongo_guard import GuardedCollection, GuardedStore, StoreDuplicateKey

__all__ = ["AuthStoreBusy", "Doc", "MongoTxBase", "coll_of", "lease"]

LOG = logging.getLogger(__name__)
Doc = dict[str, Any]
META, LOCK_ID = "auth_meta", "tx_lock"
LEASE_SECONDS, WAIT_SECONDS, POLL_SECONDS = 30.0, 15.0, 0.005


class AuthStoreBusy(RuntimeError):
    """The write lease could not be had in time (or was lost). Carries no data."""


def coll_of(store: GuardedStore, name: str) -> GuardedCollection:
    coll = store.collection(name)
    if not isinstance(coll, GuardedCollection):
        raise TypeError(f"{name} is insert-only")
    return coll


class MongoTxBase:
    def __init__(self, store: GuardedStore, writable: bool) -> None:
        self._s, self._writable = store, writable
        self._undo: list[Callable[[], object]] = []

    def _docs(self, name: str, flt: Doc | None = None) -> list[Doc]:
        return coll_of(self._s, name).find(flt)

    def _one(self, name: str, flt: Doc) -> Doc | None: return coll_of(self._s, name).find_one(flt)
    def _get(self, name: str, doc_id: Any) -> Doc | None: return self._one(name, {"_id": doc_id})

    def _writer(self, name: str) -> GuardedCollection:
        if not self._writable:
            raise RuntimeError("the auth store was opened for reading")
        return coll_of(self._s, name)

    def _insert(self, name: str, doc: Doc) -> None:  # every write records its own undo
        coll = self._writer(name)
        coll.insert_one(doc)
        self._undo.append(lambda: coll.delete_one({"_id": doc["_id"]}))

    def _patch(self, name: str, doc_id: Any, /, **fields: Any) -> bool:
        coll, old = self._writer(name), self._get(name, doc_id)
        if old is not None:
            coll.update_one({"_id": doc_id}, {"$set": fields})
            prior = {key: old.get(key) for key in fields}
            self._undo.append(lambda: coll.update_one({"_id": doc_id}, {"$set": prior}))
        return old is not None

    def _drop(self, name: str, doc_id: Any) -> bool:
        coll, old = self._writer(name), self._get(name, doc_id)
        if old is not None:
            coll.delete_one({"_id": doc_id})
            self._undo.append(lambda: coll.insert_one(old))
        return old is not None

    def _drop_where(self, name: str, flt: Doc) -> None:
        for doc in self._docs(name, flt):
            self._drop(name, doc["_id"])

    def rollback(self) -> None:
        while self._undo:
            try:
                self._undo.pop()()
            except Exception as exc:  # keep undoing; only the class name is logged
                LOG.error("auth rollback step failed (%s)", type(exc).__name__)

    def _allocate(self, collection: str) -> int:
        """The next integer id of `collection`: a counter, never handed out twice and never
        reused after a delete (a rolled-back id is burned, which is harmless)."""
        meta, key = self._writer(META), f"alloc:{collection}"
        current = meta.find_one({"_id": key})
        if current is None:
            first = max((d["_id"] for d in self._docs(collection)), default=0) + 1
            meta.insert_one({"_id": key, "next": first + 1})
            return first
        taken = int(current["next"])
        if not meta.update_one({"_id": key, "next": taken}, {"$set": {"next": taken + 1}}):
            raise AuthStoreBusy("could not allocate an id; try again")
        return taken


def _acquire(meta: GuardedCollection, owner: str) -> None:
    """Take the write lease: insert it, or take over an expired one by compare-and-set."""
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        now = time.time()
        try:
            meta.insert_one({"_id": LOCK_ID, "owner": owner, "expires": now + LEASE_SECONDS})
            return
        except StoreDuplicateKey:
            held = meta.find_one({"_id": LOCK_ID})
            if held is not None and held["expires"] < now and meta.update_one(
                    {"_id": LOCK_ID, "owner": held["owner"], "expires": held["expires"]},
                    {"$set": {"owner": owner, "expires": now + LEASE_SECONDS}}):
                return
        if time.monotonic() > deadline:
            raise AuthStoreBusy("the auth store is busy; try again")
        time.sleep(POLL_SECONDS)


@contextmanager
def lease(store: GuardedStore) -> Iterator[Callable[[], bool]]:
    """Hold the write lease; yields `holds()`, true while this holder still owns it."""
    meta, owner = coll_of(store, META), secrets.token_hex(8)
    _acquire(meta, owner)
    try:
        yield lambda: meta.find_one({"_id": LOCK_ID, "owner": owner}) is not None
    finally:
        try:
            meta.delete_one({"_id": LOCK_ID, "owner": owner})
        except Exception as exc:  # unreachable store: the lease expires by itself
            LOG.error("auth lease not released (%s)", type(exc).__name__)
