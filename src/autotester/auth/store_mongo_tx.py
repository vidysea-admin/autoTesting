"""The write-transaction primitives of the Mongo auth store (mongo-store U6b/U6bf), over
`store.mongo_guard` only: the write LEASE (`auth_meta/tx_lock`) with a FENCING EPOCH
(`auth_meta/epoch`, one more at every acquire), the write-ahead JOURNAL that makes a refused or
interrupted change undoable, and the never-reused id counter. Mongo promises one document at a
time, so these are what make first-admin, claim and the last-admin check see one writer.

Every write by a holder of epoch e is fenced three ways: (1) its undo entry (in `auth_users`, M30)
is durable BEFORE the write and the lease is re-checked after the entry and before the write;
(2) the write is conditional on the document's stamp `_e` as read, and every write re-stamps; (3)
whoever takes the lease next first resolves every other epoch's journal: it aborts the marker
`auth_meta/tx:<e>` (commit is a compare-and-set on it, so a stalled holder cannot commit later),
re-stamps the documents the entries name (so a stalled holder's late write fails its condition,
and an insert finds a tombstone) and replays the entries newest first. No auth rule lives here
and no database name (M2/M5)."""

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from typing import Any

from autotester.store.mongo_guard import GuardedCollection, GuardedStore, StoreDuplicateKey

__all__ = ["AuthStoreBusy", "Doc", "Lease", "MongoTxBase", "coll_of", "dead_marker", "lease",
           "recover"]

LOG = logging.getLogger(__name__)
Doc = dict[str, Any]
META, LOCK_ID, EPOCH_ID = "auth_meta", "tx_lock", "epoch"
TX = "tx"
JOURNAL_COLL = "auth_users"  # entries sit beside the hashes (M30)
UNDO = "undo"
FENCE = "fence"
HIDDEN = (UNDO, FENCE)
LEASE_SECONDS, WAIT_SECONDS, POLL_SECONDS = 30.0, 15.0, 0.005


class AuthStoreBusy(RuntimeError):
    """The write lease could not be had in time, or was lost. Carries no data."""


def coll_of(store: GuardedStore, name: str) -> GuardedCollection:
    coll = store.collection(name)
    if not isinstance(coll, GuardedCollection):
        raise TypeError(f"{name} is insert-only")
    return coll


def tx_id(epoch: int) -> str: return f"{TX}:{epoch:08d}"


class Lease:
    """A held write lease and its epoch; calling it says whether this holder still owns it."""

    def __init__(self, meta: GuardedCollection, owner: str, epoch: int) -> None:
        self._meta, self.owner, self.epoch = meta, owner, epoch

    def __call__(self) -> bool:
        return self._meta.find_one({"_id": LOCK_ID, "owner": self.owner}) is not None


def _replay(store: GuardedStore, entry: Doc, by: int | None) -> None:
    """Undo one journalled write. A dead holder's (`by` = the epoch doing the recovery) is first
    fenced: the document is re-stamped if it is still as the write found it, so a late write
    fails its condition; an insert leaves a tombstone only a later epoch may remove. The undo
    applies only to a document still stamped by that write (or by the fence)."""
    coll, i, op = coll_of(store, entry["coll"]), entry["doc_id"], entry["op"]
    fence = None if by is None else f"F:{by:08d}"
    mine = {"$in": [entry["me"], *([fence] if fence else [])]}
    if fence and op == "ins":
        key = f"{FENCE}:{entry['coll']}:{i}"
        with suppress(StoreDuplicateKey):  # the id is taken (landed, or fenced): fine
            coll.insert_one({"_id": i, "kind": FENCE, "f": by, "email": key, "generation": key})
    elif fence:
        coll.update_one({"_id": i, "_e": entry["pre"]}, {"$set": {"_e": fence}})
    stamp = fence or entry["pre"]
    if op == "ins":
        coll.delete_one({"_id": i, "_e": mine})
    elif op == "set":
        coll.update_one({"_id": i, "_e": mine}, {"$set": {**entry["prior"], "_e": stamp}})
    else:
        with suppress(StoreDuplicateKey):  # already back
            coll.insert_one({**entry["doc"], "_e": stamp})


def _resolve(store: GuardedStore, epoch: int, by: int | None) -> None:
    """Finish one epoch's journal: abort its marker unless committed (the CAS that stops a late
    commit), replay its entries newest first (or only sweep them, when committed), drop both."""
    meta, users = coll_of(store, META), coll_of(store, JOURNAL_COLL)
    meta.update_one({"_id": tx_id(epoch), "state": "open"}, {"$set": {"state": "aborted"}})
    marker = meta.find_one({"_id": tx_id(epoch)})
    committed = marker is not None and marker["state"] == "committed"
    for entry in sorted(users.find({"kind": UNDO, "epoch": epoch}), key=lambda d: str(d["_id"]),
                        reverse=True):
        if not committed:
            _replay(store, entry, by)
        users.delete_one({"_id": entry["_id"]})  # one at a time: a crash resumes where it was
    meta.delete_one({"_id": tx_id(epoch)})


def recover(store: GuardedStore, epoch: int) -> None:
    """Resolve every journal of an epoch other than `epoch` (the caller's, holding the lease):
    a dead or stalled holder's is undone, a committed one's leftovers are swept."""
    seen = {m["epoch"] for m in coll_of(store, META).find({"kind": TX})}
    seen |= {e["epoch"] for e in coll_of(store, JOURNAL_COLL).find({"kind": UNDO})}
    for other in sorted(seen - {epoch}):
        _resolve(store, other, epoch)


def dead_marker(store: GuardedStore) -> bool:
    """True if an uncommitted journal (open, or aborted half way) belongs to a holder that no
    longer holds a live lease: readers take the lease once to undo it before they read."""
    meta = coll_of(store, META)
    owners = {m["owner"] for m in meta.find({"kind": TX, "state": {"$ne": "committed"}})}
    held = meta.find_one({"_id": LOCK_ID}) if owners else None
    return bool(owners) and (held is None or held["expires"] < time.time()
                             or held["owner"] not in owners)


class MongoTxBase:
    def __init__(self, store: GuardedStore, writable: bool, held: Lease | None = None) -> None:
        self._s, self._writable, self._held = store, writable, held
        self._keys: list[str] = []  # journal entries this transaction wrote
        self._open = False

    def _docs(self, name: str, flt: Doc | None = None) -> list[Doc]:
        return [d for d in coll_of(self._s, name).find(flt) if d.get("kind") not in HIDDEN]

    def _one(self, name: str, flt: Doc) -> Doc | None: return coll_of(self._s, name).find_one(flt)

    def _get(self, name: str, doc_id: Any) -> Doc | None:
        doc = self._one(name, {"_id": doc_id})
        return None if doc is None or doc.get("kind") in HIDDEN else doc

    def _writer(self, name: str) -> GuardedCollection:
        if not self._writable:
            raise RuntimeError("the auth store was opened for reading")
        return coll_of(self._s, name)

    def _alive(self) -> bool:
        """Still the holder: the lease is mine and, once I write, my journal marker is open."""
        held = self._held
        return held is not None and held() and (not self._open or coll_of(self._s, META).find_one(
            {"_id": tx_id(held.epoch), "state": "open", "owner": held.owner}) is not None)

    def _log(self, step: Doc) -> str:
        """Write-ahead, fenced: refuse unless still the holder, make the undo entry durable,
        refuse again, and only then let the caller write. Returns the write's stamp."""
        held = self._held
        if held is None or not self._alive():
            raise AuthStoreBusy("the auth store lease was lost")
        if not self._open:
            coll_of(self._s, META).insert_one({
                "_id": tx_id(held.epoch), "kind": TX, "state": "open",
                "epoch": held.epoch, "owner": held.owner})
            self._open = True
        stamp = f"{held.epoch:08d}.{len(self._keys) + 1:06d}"
        key = f"{UNDO}:{stamp}"  # `email`/`generation` carry it so the users' unique indexes agree
        coll_of(self._s, JOURNAL_COLL).insert_one({
            "_id": key, "email": key, "generation": key, "kind": UNDO, "epoch": held.epoch,
            "owner": held.owner, "me": stamp, **step})
        self._keys.append(key)
        if not self._alive():
            raise AuthStoreBusy("the auth store lease was lost")
        return stamp

    @staticmethod
    def _landed(ok: bool) -> None:
        if not ok:
            raise AuthStoreBusy("the document changed under this writer; the change was refused")

    def _insert(self, name: str, doc: Doc) -> None:
        coll = self._writer(name)
        doc = {**doc, "_e": self._log({"op": "ins", "coll": name, "doc_id": doc["_id"],
                                       "pre": None})}
        try:
            coll.insert_one(doc)
        except StoreDuplicateKey:  # a tombstone of an undone insert may sit on this id
            held = self._held
            if held is None or not coll.delete_one(
                    {"_id": doc["_id"], "kind": FENCE, "f": {"$lt": held.epoch}}):
                self._landed(coll.find_one({"_id": doc["_id"], "kind": FENCE}) is None)
                raise  # fenced by a later epoch -> refused above; else a real duplicate
            coll.insert_one(doc)

    def _patch(self, name: str, doc_id: Any, /, **fields: Any) -> bool:
        coll, old = self._writer(name), self._get(name, doc_id)
        if old is not None:
            stamp = self._log({"op": "set", "coll": name, "doc_id": doc_id, "pre": old.get("_e"),
                               "prior": {key: old.get(key) for key in fields}})
            self._landed(coll.update_one({"_id": doc_id, "_e": old.get("_e")},
                                         {"$set": {**fields, "_e": stamp}}))
        return old is not None

    def _drop(self, name: str, doc_id: Any) -> bool:
        coll, old = self._writer(name), self._get(name, doc_id)
        if old is not None:
            self._log({"op": "del", "coll": name, "doc_id": doc_id, "pre": old.get("_e"),
                       "doc": old})
            self._landed(coll.delete_one({"_id": doc_id, "_e": old.get("_e")}))
        return old is not None

    def _drop_where(self, name: str, flt: Doc) -> None:
        for doc in self._docs(name, flt):
            self._drop(name, doc["_id"])

    def commit(self) -> None:
        """Compare-and-set the marker open -> committed: one atomic step that fails if a
        successor aborted this journal. The entries are swept after, best effort."""
        held = self._held
        if not self._open:
            return
        if held is None or not coll_of(self._s, META).update_one(
                {"_id": tx_id(held.epoch), "state": "open", "owner": held.owner},
                {"$set": {"state": "committed"}}):
            raise AuthStoreBusy("the auth store lease was lost; the change was undone")
        self._open = False
        try:
            for key in self._keys:
                coll_of(self._s, JOURNAL_COLL).delete_one({"_id": key})
            coll_of(self._s, META).delete_one({"_id": tx_id(held.epoch)})
        except Exception as exc:  # committed leftovers: the next lease holder sweeps them
            LOG.error("auth journal not swept (%s)", type(exc).__name__)

    def rollback(self) -> None:
        """Undo this holder's writes, if it still owns the lease; otherwise its successor does.
        A store that cannot be reached leaves the journal for the next holder."""
        if not self._open:
            return
        try:
            if self._held is not None and self._held():
                _resolve(self._s, self._held.epoch, None)
                self._open = False
        except Exception as exc:  # only the class name is logged
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


def _next_epoch(meta: GuardedCollection) -> int:
    """The fencing epoch of a new holder: a counter that only grows, advanced by compare-and-set."""
    while True:
        counter = meta.find_one({"_id": EPOCH_ID})
        if counter is None:
            with suppress(StoreDuplicateKey):
                meta.insert_one({"_id": EPOCH_ID, "n": 1})
                return 1
        elif meta.update_one({"_id": EPOCH_ID, "n": counter["n"]},
                             {"$set": {"n": counter["n"] + 1}}):
            return int(counter["n"]) + 1


@contextmanager
def lease(store: GuardedStore) -> Iterator[Lease]:
    """Hold the write lease under a new epoch, after resolving every other epoch's journal."""
    meta, owner = coll_of(store, META), secrets.token_hex(8)
    _acquire(meta, owner)
    try:
        epoch = _next_epoch(meta)
        recover(store, epoch)  # whatever a holder that died or stalled left behind
        yield Lease(meta, owner, epoch)
    finally:
        try:
            meta.delete_one({"_id": LOCK_ID, "owner": owner})
        except Exception as exc:  # unreachable store: the lease expires by itself
            LOG.error("auth lease not released (%s)", type(exc).__name__)
