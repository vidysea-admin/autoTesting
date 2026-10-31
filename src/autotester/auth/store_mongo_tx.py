"""The write-transaction primitives of the Mongo auth store (mongo-store U6b), over
`store.mongo_guard` only: the write LEASE (`auth_meta/tx_lock`: insert under a unique `_id`, take
over an expired one by compare-and-set), the JOURNAL that makes a refused or interrupted change
undoable after a crash, and the never-reused id counter. Mongo promises one document at a time,
so these three are what make first-admin, claim and the last-admin check (AU7, AU9, D-109) see
one writer. The journal is write-ahead and lives in the store: an entry is durable BEFORE the
write it undoes, `auth_meta/journal` is the commit marker (deleting it commits), and whoever
next takes the lease replays what a dead holder left. No auth rule lives here and no database
name (M2/M5)."""

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from typing import Any

from autotester.store.mongo_guard import GuardedCollection, GuardedStore, StoreDuplicateKey

__all__ = ["AuthStoreBusy", "Doc", "Lease", "MongoTxBase", "coll_of", "lease", "recover"]

LOG = logging.getLogger(__name__)
Doc = dict[str, Any]
META, LOCK_ID, JOURNAL_ID = "auth_meta", "tx_lock", "journal"
JOURNAL_COLL, UNDO = "auth_users", "undo"  # entries sit beside the hashes they may carry (M30)
LEASE_SECONDS, WAIT_SECONDS, POLL_SECONDS = 30.0, 15.0, 0.005


class AuthStoreBusy(RuntimeError):
    """The write lease could not be had in time (or was lost). Carries no data."""


def coll_of(store: GuardedStore, name: str) -> GuardedCollection:
    coll = store.collection(name)
    if not isinstance(coll, GuardedCollection):
        raise TypeError(f"{name} is insert-only")
    return coll


class Lease:
    """A held write lease; calling it says whether this holder still owns it."""

    def __init__(self, meta: GuardedCollection, owner: str) -> None:
        self._meta, self.owner = meta, owner

    def __call__(self) -> bool:
        return self._meta.find_one({"_id": LOCK_ID, "owner": self.owner}) is not None


def _replay(store: GuardedStore, entry: Doc) -> None:
    """Undo one journalled write. Idempotent, and a patch is undone only if the document still
    holds what it wrote (compare-and-set), so nothing newer is ever overwritten."""
    coll, doc_id = coll_of(store, entry["coll"]), entry.get("doc_id")
    if entry["op"] == "ins":
        coll.delete_one({"_id": doc_id})
    elif entry["op"] == "set":
        coll.update_one({"_id": doc_id, **entry["after"]}, {"$set": entry["prior"]})
    else:
        with suppress(StoreDuplicateKey):  # already back
            coll.insert_one(entry["doc"])


def recover(store: GuardedStore, only: str | None = None) -> None:
    """Undo, newest first, every write of a holder that never committed (its journal marker is
    still there), then drop the marker. `only`: just that holder's own journal (its rollback).
    Entries are removed as they are undone, so a crash inside recovery resumes where it was."""
    meta, entries = coll_of(store, META), coll_of(store, JOURNAL_COLL)
    head = meta.find_one({"_id": JOURNAL_ID})
    if head is None or (only is not None and head["owner"] != only):
        return
    for entry in sorted((d for d in entries.find({"kind": UNDO}) if d["owner"] == head["owner"]),
                        key=lambda d: str(d["_id"]), reverse=True):
        _replay(store, entry)
        entries.delete_one({"_id": entry["_id"]})
    meta.delete_one({"_id": JOURNAL_ID})


class MongoTxBase:
    def __init__(self, store: GuardedStore, writable: bool, held: Lease | None = None) -> None:
        self._s, self._writable, self._held = store, writable, held
        self._keys: list[str] = []  # journal entries this transaction wrote
        self._open = False

    def _docs(self, name: str, flt: Doc | None = None) -> list[Doc]:
        return [d for d in coll_of(self._s, name).find(flt) if d.get("kind") != UNDO]

    def _one(self, name: str, flt: Doc) -> Doc | None: return coll_of(self._s, name).find_one(flt)
    def _get(self, name: str, doc_id: Any) -> Doc | None: return self._one(name, {"_id": doc_id})

    def _writer(self, name: str) -> GuardedCollection:
        if not self._writable:
            raise RuntimeError("the auth store was opened for reading")
        return coll_of(self._s, name)

    def _log(self, step: Doc) -> None:
        """Write-ahead: the undo entry is durable before the write it undoes, and only while
        this holder still owns the lease (a stalled holder writes nothing after losing it)."""
        held = self._held
        if held is None or not held():
            raise AuthStoreBusy("the auth store lease was lost")
        if not self._open:
            try:
                coll_of(self._s, META).insert_one({"_id": JOURNAL_ID, "owner": held.owner})
            except StoreDuplicateKey:
                raise AuthStoreBusy("another writer's journal is open") from None
            self._open = True
        key = f"{UNDO}:{held.owner}:{len(self._keys) + 1:06d}"
        # `email` and `generation` carry the key so the users' unique indexes accept the entry
        coll_of(self._s, JOURNAL_COLL).insert_one({"_id": key, "email": key, "generation": key,
                                                   "kind": UNDO, "owner": held.owner, **step})
        self._keys.append(key)

    def _insert(self, name: str, doc: Doc) -> None:
        coll = self._writer(name)
        self._log({"op": "ins", "coll": name, "doc_id": doc["_id"]})
        coll.insert_one(doc)

    def _patch(self, name: str, doc_id: Any, /, **fields: Any) -> bool:
        coll, old = self._writer(name), self._get(name, doc_id)
        if old is not None:
            self._log({"op": "set", "coll": name, "doc_id": doc_id, "after": fields,
                       "prior": {key: old.get(key) for key in fields}})
            coll.update_one({"_id": doc_id}, {"$set": fields})
        return old is not None

    def _drop(self, name: str, doc_id: Any) -> bool:
        coll, old = self._writer(name), self._get(name, doc_id)
        if old is not None:
            self._log({"op": "del", "coll": name, "doc_id": doc_id, "doc": old})
            coll.delete_one({"_id": doc_id})
        return old is not None

    def _drop_where(self, name: str, flt: Doc) -> None:
        for doc in self._docs(name, flt):
            self._drop(name, doc["_id"])

    def commit(self) -> None:
        """Deleting the marker IS the commit: one atomic step, and it fails if the lease was
        lost (a successor already undid this holder's writes). The entries are swept after."""
        if not self._open:
            return
        held = self._held
        if held is None or not coll_of(self._s, META).delete_one(
                {"_id": JOURNAL_ID, "owner": held.owner}):
            raise AuthStoreBusy("the auth store lease was lost; the change was undone")
        self._open = False
        try:
            for key in self._keys:
                coll_of(self._s, JOURNAL_COLL).delete_one({"_id": key})
        except Exception as exc:  # inert leftovers: nothing reads them, recovery skips them
            LOG.error("auth journal not swept (%s)", type(exc).__name__)

    def rollback(self) -> None:
        """Undo this holder's writes from the journal, if it still owns the lease; if it does
        not, its successor already undid them. A store that cannot be reached leaves the journal
        for the next holder (only the exception class name is logged)."""
        if not self._open:
            return
        try:
            if self._held is not None and self._held():
                recover(self._s, only=self._held.owner)
        except Exception as exc:
            LOG.error("auth rollback deferred to the next lease holder (%s)", type(exc).__name__)

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
def lease(store: GuardedStore) -> Iterator[Lease]:
    """Hold the write lease, after undoing a dead holder's journal; yields the `Lease`."""
    meta, owner = coll_of(store, META), secrets.token_hex(8)
    _acquire(meta, owner)
    try:
        recover(store)  # whatever a holder that died mid-transaction left behind
        yield Lease(meta, owner)
    finally:
        try:
            meta.delete_one({"_id": LOCK_ID, "owner": owner})
        except Exception as exc:  # unreachable store: the lease expires by itself
            LOG.error("auth lease not released (%s)", type(exc).__name__)
