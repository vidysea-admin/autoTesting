"""The fence half of the Mongo auth store's write transaction (mongo-store U6b/U6bf/U6c, D-129):
the journal vocabulary, the replay that undoes a journalled write, the resolution of one epoch's
journal and the fenced insert. `store_mongo_tx.py` holds the lease and the transaction object and
calls only these functions. No auth rule or database name lives here (M2/M5).

A stalled holder's LATE INSERT must never land (AT-1431). Two kinds of collection:
- ids that are never re-created (users, groups, sessions: allocator or random ids): an undone
  insert leaves a `FENCE` tombstone (`kind`, `f` = the recovering epoch) on the id.
- ids that ARE re-created (`SLOTTED`: a grant is `slug|user|relation`, a share is
  `slug|video|sha256(email)`): the id slot is never empty again once it has been used. An undone
  insert and a committed delete both leave a hidden document stamped `G:<epoch>.000000` or
  `G:<stamp>`, and a legitimate insert takes the slot over with a compare-and-set on the stamp
  it read, only if that stamp's epoch is not later than its own. A stalled writer of an older
  epoch therefore finds a duplicate key and a stamp from a later epoch, and is refused, however
  many holders came and went in between (a tombstone that is cleared and re-created would leave
  the id absent for it to land in).
- delete, then re-create, of one slotted id in ONE transaction (E10.3): undoing the re-insert puts
  the slot back to the `G:` stamp of the same transaction's delete (a rollback), or leaves it
  hidden at the recoverer's epoch where the delete's restore also looks (a recovery), so the
  original document comes back whole either way.
"""

from __future__ import annotations

import re
from contextlib import suppress
from typing import Any

from autotester.store.mongo_guard import GuardedCollection, GuardedStore, StoreDuplicateKey

__all__ = [
    "FENCE",
    "HIDDEN",
    "JOURNAL_COLL",
    "META",
    "SLOTTED",
    "TX",
    "UNDO",
    "AuthStoreBusy",
    "Doc",
    "close_epoch",
    "coll_of",
    "gone",
    "hidden",
    "insert_fenced",
    "landed",
    "recover",
    "tx_id",
]

Doc = dict[str, Any]
META = "auth_meta"
TX = "tx"
JOURNAL_COLL = "auth_users"  # entries sit beside the hashes (M30)
UNDO = "undo"
FENCE = "fence"
HIDDEN = (UNDO, FENCE)
SLOTTED = frozenset({"auth_grants", "video_shares"})  # deterministic ids that are re-created
_EPOCH = re.compile(r"(\d{8})\.\d{6}$")


class AuthStoreBusy(RuntimeError):
    """The write lease could not be had in time, or was lost. Carries no data."""


def coll_of(store: GuardedStore, name: str) -> GuardedCollection:
    coll = store.collection(name)
    if not isinstance(coll, GuardedCollection):
        raise TypeError(f"{name} is insert-only")
    return coll


def tx_id(epoch: int) -> str: return f"{TX}:{epoch:08d}"
def gone(stamp: Any) -> bool: return str(stamp).startswith("G:")
def hidden(d: Doc) -> bool: return d.get("kind") in HIDDEN or gone(d.get("_e"))
def hide_stamp(epoch: int) -> str: return f"G:{epoch:08d}.000000"


def stamp_epoch(stamp: Any) -> int:
    """The epoch a stamp was written under; a stamp that carries none sorts after every epoch."""
    found = _EPOCH.search(str(stamp))
    return int(found.group(1)) if found else 2**62


def landed(ok: bool) -> None:
    if not ok:
        raise AuthStoreBusy("the document changed under this writer; the change was refused")


def _hide_slot(coll: GuardedCollection, i: Any, mine: Doc, epoch: int,
               back: str | None = None) -> None:
    """Make the slot `i` hidden at `epoch`: place the hidden document, or hide the landed one
    that is mine, or raise an older hidden stamp. A live document of anyone else is left. With
    `back` (E10.3), a landed document of mine goes back to the hidden stamp it took over."""
    hid = hide_stamp(epoch)
    for _ in range(4):  # a few races (the zombie landing, another recoverer) are tolerated
        try:
            coll.insert_one({"_id": i, "_e": hid})
            return
        except StoreDuplicateKey:
            cur = coll.find_one({"_id": i})
        if cur is None:
            continue
        stamp = cur.get("_e")
        if not (stamp in mine["$in"] or (gone(stamp) and stamp_epoch(stamp) < epoch)):
            return  # a live document of someone else, or already hidden at this epoch or later
        blank = {k: None for k in cur if k not in ("_id", "_e")}  # nothing of the write stays
        to = back if back is not None and stamp in mine["$in"] else hid
        if coll.update_one({"_id": i, "_e": stamp}, {"$set": {**blank, "_e": to}}):
            return


def _took(store: GuardedStore, entry: Doc) -> str | None:
    """The hidden stamp an undone insert took over from THIS transaction's own earlier delete of
    the same id (delete, then re-create): the earlier entry restores a slot stamped `G:<its me>`,
    so the slot must go back to that stamp or the original document is lost (E10.3)."""
    older = [d for d in coll_of(store, JOURNAL_COLL).find(
        {"kind": UNDO, "epoch": entry["epoch"], "coll": entry["coll"], "doc_id": entry["doc_id"]})
        if str(d["_id"]) < str(entry["_id"])]
    last = max(older, key=lambda d: str(d["_id"]), default=None)
    return f"G:{last['me']}" if last is not None and last["op"] == "set" and last["gone"] else None


def replay(store: GuardedStore, entry: Doc, by: int | None) -> None:
    """Undo one journalled write, only on a document still stamped by it (`me`, `G:me`, or `F:me`
    left by undoing the next entry on it). A dead holder's (`by` = the recovering epoch) is fenced
    first: re-stamped if as the write found it, an insert leaves a tombstone for later epochs."""
    coll, i, me = coll_of(store, entry["coll"]), entry["doc_id"], entry["me"]
    ins, pre = entry["op"] == "ins", entry["pre"]
    mine = {"$in": [me, f"G:{me}", f"F:{me}"]}
    if ins and entry["coll"] in SLOTTED:
        _hide_slot(coll, i, mine, entry["epoch"] if by is None else by,
                   _took(store, entry) if by is None else None)
        return
    if by is not None and entry["coll"] in SLOTTED:  # a later undone insert hid the slot at `by`
        mine = {"$in": [*mine["$in"], hide_stamp(by)]}
    stamp = pre if by is None else f"F:{pre}"  # a recoverer must not reopen the old stamp
    if by is not None and ins:
        key = f"{FENCE}:{entry['coll']}:{i}"  # a placeholder for every unique index
        with suppress(StoreDuplicateKey):  # the id is taken (landed, or fenced): fine
            coll.insert_one({"_id": i, "kind": FENCE, "f": by, "email": key, "generation": key,
                             "name": key})
    elif by is not None:
        coll.update_one({"_id": i, "_e": pre}, {"$set": {"_e": stamp}})
    if ins:
        coll.delete_one({"_id": i, "_e": mine})
    else:
        coll.update_one({"_id": i, "_e": mine}, {"$set": {**entry["prior"], "_e": stamp}})


def close_epoch(store: GuardedStore, epoch: int, by: int | None) -> None:
    """Finish one epoch's journal: abort its marker unless committed (the CAS that stops a late
    commit), replay its entries newest first (or only sweep them, when committed), drop both."""
    meta, users = coll_of(store, META), coll_of(store, JOURNAL_COLL)
    meta.update_one({"_id": tx_id(epoch), "state": "open"}, {"$set": {"state": "aborted"}})
    marker = meta.find_one({"_id": tx_id(epoch)})
    committed = marker is not None and marker["state"] == "committed"
    for entry in sorted(users.find({"kind": UNDO, "epoch": epoch}), key=lambda d: str(d["_id"]),
                        reverse=True):
        if not committed:
            replay(store, entry, by)
        elif entry.get("gone") and entry["coll"] not in SLOTTED:  # a committed delete is physical
            coll_of(store, entry["coll"]).delete_one({"_id": entry["doc_id"],
                                                      "_e": f"G:{entry['me']}"})
        users.delete_one({"_id": entry["_id"]})  # one at a time: a crash resumes where it was
    meta.delete_one({"_id": tx_id(epoch)})


def recover(store: GuardedStore, epoch: int) -> None:
    """Resolve every journal of an EARLIER epoch than `epoch` (the caller's, holding the lease):
    a dead or stalled holder's is undone, a committed one's leftovers are swept. A later epoch
    is a live holder that took over a lease this caller lost: never touched."""
    seen = {m["epoch"] for m in coll_of(store, META).find({"kind": TX})}
    seen |= {e["epoch"] for e in coll_of(store, JOURNAL_COLL).find({"kind": UNDO})}
    for other in sorted(e for e in seen if e < epoch):
        close_epoch(store, other, epoch)


def insert_fenced(coll: GuardedCollection, name: str, doc: Doc, epoch: int | None) -> None:
    """Insert `doc` (already stamped, its undo entry durable). On a duplicate id: a slotted
    collection takes over a hidden slot of an epoch not later than `epoch`; any other collection
    clears a tombstone of an epoch not later than `epoch`. A later one, or a live document,
    refuses the insert."""
    try:
        coll.insert_one(doc)
        return
    except StoreDuplicateKey:
        cur = coll.find_one({"_id": doc["_id"]})
        if name in SLOTTED and cur is not None and gone(cur.get("_e")):
            landed(epoch is not None and stamp_epoch(cur["_e"]) <= epoch and coll.update_one(
                {"_id": doc["_id"], "_e": cur["_e"]},
                {"$set": {k: v for k, v in doc.items() if k != "_id"}}))
            return
        if name in SLOTTED or epoch is None or not coll.delete_one(
                {"_id": doc["_id"], "kind": FENCE, "f": {"$lte": epoch}}):
            landed(cur is None or cur.get("kind") != FENCE)
            raise  # fenced by a later epoch -> refused above; else a real duplicate
    coll.insert_one(doc)
