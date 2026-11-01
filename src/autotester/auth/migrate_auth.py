"""Copy the SQLite auth store into the Mongo auth store (mongo-store U8, M45).

One job: read `auth.sqlite` and write it through `MongoAuthStore.transaction()`, the auth store's
own lease and undo journal, never through raw collections. Integer ids, password hashes, account
generations and group links come across verbatim; the id allocators are set above every imported
id so none is handed out twice. An existing account is never overwritten (a differing one is
reported as a conflict). Sessions are copied only when asked, and only the unexpired ones.
`browser_sessions` and the video tables are not here (U12, U6c). Nothing is printed here.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from typing import Any

from autotester.auth import db

AuthData = dict[str, list[tuple[Any, ...]]]
COLUMNS = {
    "users": "id, email, password_hash, display_name, disabled, created_at, generation",
    "groups": "id, name, seed", "group_permissions": "group_id, permission",
    "memberships": "user_id, group_id", "project_grants": "slug, user_id, relation",
    "sessions": "token_hash, user_id, created_at, expires_at"}


def read_auth() -> AuthData | None:
    """The SQLite auth file, opened read-only (never created or migrated); `None` if absent."""
    path = db.auth_db_path()
    if not path.is_file():
        return None
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return {k: con.execute(f"SELECT {c} FROM {k} ORDER BY 1, 2").fetchall()
                for k, c in COLUMNS.items()}
    finally:
        con.close()


def _seed_allocator(tx: Any, coll: str) -> None:
    """The id counter starts above every imported id, so none is ever handed out twice."""
    from autotester.auth.store_mongo_tx import META

    top = max((d["_id"] for d in tx._docs(coll)), default=0)
    meta, key = tx._writer(META), f"alloc:{coll}"
    cur = meta.find_one({"_id": key})
    if cur is None:
        meta.insert_one({"_id": key, "next": top + 1})
    elif cur["next"] <= top:
        meta.update_one({"_id": key, "next": cur["next"]}, {"$set": {"next": top + 1}})


def _import_groups(tx: Any, d: AuthData, fresh: bool, out: Counter[str]) -> dict[int, int]:
    """Source group id -> Mongo group id. A seeded group is matched by its seed, so the default
    groups the store already holds are reused; on a store with no accounts they take the source's
    name and permissions, and a default group the source deleted stays deleted (AU11)."""
    from autotester.auth.store_mongo import GROUPS

    have, perms, gmap = tx._docs(GROUPS), {}, {}
    for gid, perm in d["group_permissions"]:
        perms.setdefault(gid, []).append(perm)
    for gid, name, seed in d["groups"]:
        want = sorted(perms.get(gid, []))
        doc = next((h for h in have
                    if (h.get("seed") == seed if seed else h["name"] == name)), None)
        if doc is None:
            gmap[gid] = gid if tx._get(GROUPS, gid) is None else tx._allocate(GROUPS)
            tx._insert(GROUPS, {"_id": gmap[gid], "name": name, "permissions": want,
                                **({"seed": seed} if seed else {})})
            out["written"] += 1
            continue
        gmap[gid] = doc["_id"]
        if fresh and (doc["name"], doc["permissions"]) != (name, want):
            tx._patch(GROUPS, doc["_id"], name=name, permissions=want)
    kept = {g[2] for g in d["groups"]}
    for doc in (h for h in have if fresh and h.get("seed") not in (None, *kept)):
        tx._drop(GROUPS, doc["_id"])
    return gmap


def _import_users(tx: Any, d: AuthData, gmap: dict[int, int], out: Counter[str]) -> None:
    from autotester.auth.store_mongo import USERS

    member: dict[int, set[int]] = {}
    for uid, gid in d["memberships"]:
        member.setdefault(uid, set()).add(gmap[gid])
    for uid, email, pw, name, off, born, gen in d["users"]:
        held, twin = tx._get(USERS, uid), tx._one(USERS, {"email": email})
        if held is not None and held["email"] == email:
            out["unchanged"] += 1
        elif held is not None or twin is not None:
            out["conflicting-id"] += 1
        else:
            tx._insert(USERS, {"_id": uid, "email": email, "password_hash": pw,
                               "display_name": name, "disabled": bool(off), "created_at": born,
                               "generation": gen, "group_ids": sorted(member.get(uid, ()))})
            out["written"] += 1


def import_auth(d: AuthData, sessions: bool) -> Counter[str]:
    """SQLite -> the Mongo auth store, one journalled transaction. Returns counts only."""
    from autotester.auth import store_mongo as sm
    from autotester.store.mongo_backend import default_store

    out: Counter[str] = Counter()
    with sm.MongoAuthStore(default_store()).transaction() as tx:
        gmap = _import_groups(tx, d, not tx._docs(sm.USERS), out)
        _import_users(tx, d, gmap, out)
        live = tx.known_user_ids()
        for slug, uid, rel in d["project_grants"]:
            grant = sm.MongoAuthTx._grant(slug, uid, rel)
            if uid in live and tx._get(sm.GRANTS, grant["_id"]) is None:
                tx._insert(sm.GRANTS, grant)
                out["written"] += 1
        for digest, uid, born, until in d["sessions"] if sessions else ():
            if until > db.now_iso() and uid in live and not tx.has_session(digest):
                tx.insert_session(digest, uid, born, until)
                out["written"] += 1
        for coll in (sm.USERS, sm.GROUPS):
            if out["written"]:
                _seed_allocator(tx, coll)
    return out


def auth_status(d: AuthData, remote: bool) -> Counter[str]:
    """Each source account against the Mongo store: `unchanged`, `to_insert` or `conflicting-id`
    (id, generation, hash or disabled differ). `remote=False` is a dry run: nothing is opened."""
    if not remote:
        return Counter(to_insert=len(d["users"]))
    from autotester.auth.store_mongo import MongoAuthStore
    from autotester.store.mongo_backend import default_store

    store, out = MongoAuthStore(default_store()), Counter[str]()
    if not store.exists():
        return Counter(to_insert=len(d["users"]))
    with store.reading() as tx:
        for uid, email, pw, _name, off, _born, gen in d["users"]:
            got = tx.login_record(email)
            if got is None:
                out["to_insert"] += 1
            else:
                user, held = got[0], (uid, gen, pw, bool(off))
                same = (user.id, user.generation, got[1], user.disabled) == held
                out["unchanged" if same else "conflicting-id"] += 1
    return out
