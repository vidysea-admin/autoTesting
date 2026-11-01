"""Copy the SQLite auth store into the Mongo auth store (mongo-store U8, M45).

One job: read `auth.sqlite` and write it through `MongoAuthStore.transaction()`, the auth store's
own lease and undo journal, never through raw collections. Integer ids, password hashes, account
generations and group links come across verbatim; the id allocators are set above every imported
id so none is handed out twice. An existing account is never overwritten (a differing one is
reported as a conflict). Sessions are copied only when asked, and only the unexpired ones.
The four video tables (shares, links, access requests, comments; E10.1) are copied in the same
transaction through `VideoOps`: every column verbatim, request and comment ids kept with their
allocators seeded above them, a differing row reported `conflicting-id` and never replaced.
`browser_sessions` is not here (U12). Nothing is printed here: counts only, never a value.
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
    "sessions": "token_hash, user_id, created_at, expires_at",
    "video_shares": "slug, video_id, email, granted_by, granted_at",
    "video_links": "token_hash, slug, video_id, created_by, created_at, revoked_at",
    "access_requests": "id, slug, video_id, requester, status, created_at, decided_by, decided_at",
    "video_comments": ("id, slug, video_id, author, at_s, text, created_at, edited_at, "
                       "pointer_line")}
VIDEO_TABLES = ("video_shares", "video_links", "access_requests", "video_comments")
_ID_COLUMN = {"video_links": "token_hash", "access_requests": "id", "video_comments": "id"}
Report = dict[str, Counter[str]]  # verify-row name -> counts; `auth_users` is the account row


def read_auth() -> AuthData | None:
    """The SQLite auth file, opened read-only (never created or migrated); `None` if absent."""
    path = db.auth_db_path()
    if not path.is_file():
        return None
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:  # a file written before the video tables existed simply has none of them
        have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {k: con.execute(f"SELECT {c} FROM {k} ORDER BY 1, 2").fetchall() if k in have
                else [] for k, c in COLUMNS.items()}
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


def _row_name(table: str) -> str:
    """The `store verify` row of a video table: `auth_shares`, `auth_links`, ..."""
    return f"auth_{table.removeprefix('video_')}"


def _report() -> Report:
    return {"auth_users": Counter(), **{_row_name(t): Counter() for t in VIDEO_TABLES}}


def _video_rows(d: AuthData, table: str) -> list[dict[str, Any]]:
    """The table's source rows as column dicts; a hashed or numeric key sits under `_id`."""
    cols = [c.strip() for c in COLUMNS[table].split(",")]
    key = _ID_COLUMN.get(table)
    return [{("_id" if c == key else c): v for c, v in zip(cols, row, strict=True)}
            for row in d[table]]


def _video_state(tx: Any, table: str, want: dict[str, Any]) -> str:
    """`to_insert`, `unchanged` or `conflicting-id` for one source row against the target. A
    share is matched by slug, video and address (its id is never built here); a pending request
    is also matched by person and video, so one pending per person per video still holds."""
    from autotester.auth.store_mongo_video import REQUESTS, SHARES

    if table == "video_shares":
        flt = {"slug": want["slug"], "video_id": want["video_id"]}
        held = next((h for h in tx._docs(SHARES, flt) if h["email"] == want["email"]), None)
    else:
        held = tx._get(table, want["_id"])  # the collections carry the SQLite tables' names
    if held is not None:
        return "unchanged" if all(held.get(k) == v for k, v in want.items()) else "conflicting-id"
    if table == "access_requests" and want["status"] == "pending":
        twin = {k: want[k] for k in ("slug", "video_id", "requester", "status")}
        return "conflicting-id" if tx._docs(REQUESTS, twin) else "to_insert"
    return "to_insert"


def _import_video(tx: Any, d: AuthData, out: Report) -> None:
    """Insert every video row the target lacks, through `VideoOps` (journal and fence), then
    seed the request and comment id allocators above every imported id."""
    for table in VIDEO_TABLES:
        counts = out[_row_name(table)]
        for want in _video_rows(d, table):
            state = _video_state(tx, table, want)
            if state != "to_insert":
                counts[state] += 1
            elif table == "video_shares":
                tx.set_share(want["slug"], want["video_id"], want["email"], True,
                             want["granted_by"], want["granted_at"])
                counts["written"] += 1
            else:
                tx._insert(table, want)
                counts["written"] += 1
        if counts["written"] and table in ("access_requests", "video_comments"):
            _seed_allocator(tx, table)


def import_auth(d: AuthData, sessions: bool) -> Report:
    """SQLite -> the Mongo auth store, one journalled transaction. Returns counts only."""
    from autotester.auth import store_mongo as sm
    from autotester.store.mongo_backend import default_store

    out, users = _report(), Counter[str]()
    with sm.MongoAuthStore(default_store()).transaction() as tx:
        gmap = _import_groups(tx, d, not tx._docs(sm.USERS), users)
        _import_users(tx, d, gmap, users)
        live = tx.known_user_ids()
        for slug, uid, rel in d["project_grants"]:
            grant = sm.MongoAuthTx._grant(slug, uid, rel)
            if uid in live and tx._get(sm.GRANTS, grant["_id"]) is None:
                tx._insert(sm.GRANTS, grant)
                users["written"] += 1
        for digest, uid, born, until in d["sessions"] if sessions else ():
            if until > db.now_iso() and uid in live and not tx.has_session(digest):
                tx.insert_session(digest, uid, born, until)
                users["written"] += 1
        for coll in (sm.USERS, sm.GROUPS):
            if users["written"]:
                _seed_allocator(tx, coll)
        _import_video(tx, d, out)
    out["auth_users"] = users
    return out


def _user_status(tx: Any, d: AuthData) -> Counter[str]:
    out: Counter[str] = Counter()
    for uid, email, pw, _name, off, _born, gen in d["users"]:
        got = tx.login_record(email)
        if got is None:
            out["to_insert"] += 1
        else:
            user, held = got[0], (uid, gen, pw, bool(off))
            same = (user.id, user.generation, got[1], user.disabled) == held
            out["unchanged" if same else "conflicting-id"] += 1
    return out


def auth_status(d: AuthData, remote: bool) -> Report:
    """Each source account and video row against the Mongo store: `unchanged`, `to_insert` or
    `conflicting-id` (a differing id, address, token or column). `remote=False` is a dry run:
    no client is opened, the rows are only counted."""
    from autotester.auth.store_mongo import MongoAuthStore
    from autotester.store.mongo_backend import default_store

    out = _report()
    store = MongoAuthStore(default_store()) if remote else None
    if store is None or not store.exists():
        out["auth_users"]["to_insert"] = len(d["users"])
        for table in VIDEO_TABLES:
            out[_row_name(table)]["to_insert"] = len(d[table])
        return out
    with store.reading() as tx:
        out["auth_users"] = _user_status(tx, d)
        for table in VIDEO_TABLES:
            for want in _video_rows(d, table):
                out[_row_name(table)][_video_state(tx, table, want)] += 1
    return out
