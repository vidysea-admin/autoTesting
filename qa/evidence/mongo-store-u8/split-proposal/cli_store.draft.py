"""`autotester store`: copy the file-backed state into the one Mongo database, then prove it
(mongo-store U8, M41-M46).

One job: the `migrate` and `verify` commands. `migrate` is a dry run unless `--apply`, and a dry run
opens no connection. Blobs go in before the documents that name them; no source file is ever edited,
moved or deleted; a stored value that differs from the file is reported as a conflict, never
overwritten. Approvals and revocations travel as the exact rows they are (signed: never re-signed).
Auth goes through the auth store's own lease and journal, keeping the SQLite integer ids, hashes and
generations; credentials go through the credential door, only for keys a project declares. Nothing
here prints a URI, a hash or a credential value, and a failure prints its class name only (M9).
"""

from __future__ import annotations

import contextlib
import hashlib
import heapq
import json
import mimetypes
import os
import sqlite3
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer

from autotester.auth import db
from autotester.core.env import MONGO_URI_ENV, is_server_key, mongo_uri, read_dotenv
from autotester.core.paths import repo_root
from autotester.core.redact import Redactor
from autotester.core.safe_names import UnsafeName, safe_key
from autotester.store import mongo_routes as routes
from autotester.store.blobs import BlobRefused
from autotester.store.filestore import FileBackend

app = typer.Typer(help="Move the file-backed state into the Mongo store (mongo-store U8).",
                  no_args_is_help=True)
ROOT_DIRS = ("projects/", ".work/notification_prefs/", ".work/drive-jobs/", ".work/team/")
ROOT_FILES = (".work/run_queue.json", ".work/audit.jsonl", ".work/server_settings.json")
SKIP = frozenset({"profiles", "chunks", "exports", "crawl_summaries", ".blobmeta", "ceo-bench"})
IMAGES, VIDEOS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"}), frozenset(
    {".webm", ".mp4", ".mov", ".mkv"})
BINARY = IMAGES | VIDEOS | {".pdf", ".mp3", ".m4a", ".wav", ".ogg", ".opus", ".zip"}
EXACT = frozenset({"approvals", "approval_revocations"})  # M43: compared as written
AuthData = dict[str, list[tuple[Any, ...]]]


@dataclass
class Tally:
    """What a run found, per collection, without one value in it."""
    counts: dict[str, Counter[str]] = field(default_factory=dict)
    kinds: Counter[str] = field(default_factory=Counter)  # bytes per kind
    sizes: list[tuple[int, str]] = field(default_factory=list)  # documents only
    skipped: Counter[str] = field(default_factory=Counter)  # M25: scratch, profiles, chunks, ...
    unsafe: list[str] = field(default_factory=list)  # keys that failed safe_name

    def note(self, coll: str, status: str, size: int, key: str, kind: str) -> None:
        self.counts.setdefault(coll, Counter())[status] += 1
        self.kinds[kind] += size
        if kind != "blob":
            self.sizes.append((size, key))

    def bad(self) -> int:
        return sum(c["conflicting-id"] + c["refused"] for c in self.counts.values())


def classify(key: str) -> tuple[str, str]:
    """`(doc|blob|skip, kind or reason)`: scratch, profiles, chunks, exports, `.env*`, xlsx never move."""
    parts, suffix = key.split("/"), Path(key).suffix.lower()
    for part in parts:
        if part in SKIP or part.startswith(".env"):
            return "skip", part
    if suffix == ".xlsx":
        return "skip", suffix
    if suffix in VIDEOS:
        return "blob", "video" if "runs" in parts else "source"
    if suffix in BINARY:
        return "blob", "screenshot" if suffix in IMAGES and {"runs", "crawl"} & set(parts) else "source"
    return "doc", routes.route(key).collection


def scan(src: FileBackend, project: str | None, t: Tally) -> tuple[list[str], dict[str, str]]:
    keys = {k for d in ([f"projects/{project}/"] if project else ROOT_DIRS) for k in src.keys(d)}
    keys |= {k for k in ROOT_FILES if not project and src.exists(k)}
    docs, blobs = [], {}
    for key in sorted(keys):
        try:
            safe_key(key)
            action, what = classify(key)
        except UnsafeName:
            t.unsafe.append(key)
            continue
        if action == "skip":
            t.skipped[what] += 1
        elif action == "blob":
            blobs[key] = what
        else:
            docs.append(key)
    return docs, blobs


def _rows_of(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def _canon(text: str) -> str:
    try:
        return json.dumps(json.loads(text), sort_keys=True)
    except ValueError:
        return text


def doc_status(text: str, tgt: Any, key: str) -> str:
    """to_insert | unchanged | conflicting-id for one document or row set (M41, M44). A row set
    whose stored rows are a leading part of the file's resumes (a half-finished apply)."""
    if tgt is None:
        return "to_insert"
    route = routes.route(key)
    norm = (lambda s: s) if route.collection in EXACT else _canon
    if route.rows:
        have, want = [norm(r) for r in tgt.rows(key)], [norm(r) for r in _rows_of(text)]
        return ("unchanged" if have == want else
                "to_insert" if want[:len(have)] == have else "conflicting-id")
    held = tgt.get(key)
    return "to_insert" if held is None else (
        "unchanged" if norm(held) == norm(text) else "conflicting-id")


def _write(tgt: Any, key: str, text: str) -> str:
    try:
        if routes.route(key).rows:
            for row in _rows_of(text)[len(tgt.rows(key)):]:
                tgt.append_row(key, row)
        else:
            tgt.put(key, text)
    except (routes.StoreSecretRefused, routes.StoreDocTooLarge, routes.StoreImmutable):
        return "refused"
    return "written"


def _unmasked(src: FileBackend, docs: list[str]) -> set[str]:
    """Screenshots a run result records as `masked: false` stay out (the FB3 mirror, M23)."""
    out: set[str] = set()
    for key in (k for k in docs if routes.route(k).collection == "run_results"):
        try:
            items = json.loads(src.get(key) or "{}").get("evidence", [])
        except (ValueError, AttributeError):
            continue
        out |= {f"{key.rpartition('/')[0]}/{e['path']}" for e in items
                if isinstance(e, dict) and e.get("masked") is False and "path" in e}
    return out


def migrate_state(src: FileBackend, found: tuple[list[str], dict[str, str]], t: Tally,
                  tgt: Any, blobs: Any, apply: bool, wanted: set[str]) -> None:
    """Blobs first, then documents (M42). `tgt`/`blobs` are `None` for a dry run (no connection)."""
    docs, media = found
    unmasked = _unmasked(src, docs) if "blobs" in wanted else set()
    for key, kind in media.items() if "blobs" in wanted else ():
        data = src.get_bytes(key) or b""
        held = blobs.stat(key) if blobs is not None else None
        status = ("to_insert" if held is None else "unchanged"
                  if held.sha256 == hashlib.sha256(data).hexdigest() else "conflicting-id")
        if apply and status == "to_insert":
            try:
                blobs.put(key, data, kind=kind, masked=key not in unmasked,
                          content_type=mimetypes.guess_type(key)[0] or "application/octet-stream")
                status = "written"
            except (BlobRefused, UnsafeName):
                status = "refused"
        t.note("gridfs", status, len(data), key, "blob")
    for key in (k for k in docs if routes.route(k).area in wanted):
        try:
            text = src.get(key) or ""
        except UnicodeDecodeError:
            t.skipped["not-utf8"] += 1
            continue
        status = doc_status(text, tgt, key)
        if apply and status == "to_insert":
            status = _write(tgt, key, text)
        route = routes.route(key)
        t.note(route.collection, status, len(text.encode()), key, "rows" if route.rows else "doc")


def read_auth() -> AuthData | None:
    """The SQLite auth file, opened read-only; `None` when there is none. No video tables (U6c)."""
    path = db.auth_db_path()
    if not path.is_file():
        return None
    cols = {"users": "id, email, password_hash, display_name, disabled, created_at, generation",
            "groups": "id, name, seed", "group_permissions": "group_id, permission",
            "memberships": "user_id, group_id", "project_grants": "slug, user_id, relation",
            "sessions": "token_hash, user_id, created_at, expires_at"}
    con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return {k: con.execute(f"SELECT {c} FROM {k} ORDER BY 1, 2").fetchall()
                for k, c in cols.items()}
    finally:
        con.close()


def _seed_allocator(tx: Any, coll: str) -> None:
    """The id counter starts above every imported id, so none is ever handed out twice (M45)."""
    from autotester.auth.store_mongo_tx import META

    top = max((d["_id"] for d in tx._docs(coll)), default=0)
    meta, key = tx._writer(META), f"alloc:{coll}"
    cur = meta.find_one({"_id": key})
    if cur is None:
        meta.insert_one({"_id": key, "next": top + 1})
    elif cur["next"] <= top:
        meta.update_one({"_id": key, "next": cur["next"]}, {"$set": {"next": top + 1}})


def _import_groups(tx: Any, d: AuthData, fresh: bool, out: Counter[str]) -> dict[int, int]:
    from autotester.auth.store_mongo import GROUPS

    have, perms, gmap = tx._docs(GROUPS), {}, {}
    for gid, perm in d["group_permissions"]:
        perms.setdefault(gid, []).append(perm)
    for gid, name, seed in d["groups"]:
        want = sorted(perms.get(gid, []))
        doc = next((h for h in have if (h.get("seed") == seed if seed else h["name"] == name)), None)
        if doc is None:
            gmap[gid] = gid if tx._get(GROUPS, gid) is None else tx._allocate(GROUPS)
            tx._insert(GROUPS, {"_id": gmap[gid], "name": name, "permissions": want,
                                **({"seed": seed} if seed else {})})
            out["groups_inserted"] += 1
            continue
        gmap[gid] = doc["_id"]
        if fresh and (doc["name"], doc["permissions"]) != (name, want):
            tx._patch(GROUPS, doc["_id"], name=name, permissions=want)
    kept = {g[2] for g in d["groups"]}
    for doc in (h for h in have if fresh and h.get("seed") not in (None, *kept)):
        tx._drop(GROUPS, doc["_id"])  # AU11: a default group the source deleted stays deleted
    return gmap


def import_auth(d: AuthData, sessions: bool) -> Counter[str]:
    """SQLite -> the Mongo auth store through its lease and journal (M29, M45): integer ids, hashes
    and generations verbatim; an existing account is left as it is, never overwritten."""
    from autotester.auth import store_mongo as sm
    from autotester.store.mongo_backend import default_store

    out: Counter[str] = Counter()
    with sm.MongoAuthStore(default_store()).transaction() as tx:
        gmap = _import_groups(tx, d, not tx._docs(sm.USERS), out)
        member: dict[int, set[int]] = {}
        for uid, gid in d["memberships"]:
            member.setdefault(uid, set()).add(gmap[gid])
        for uid, email, pw, name, off, born, gen in d["users"]:
            held, twin = tx._get(sm.USERS, uid), tx._one(sm.USERS, {"email": email})
            if held is not None and held["email"] == email:
                out["users_unchanged"] += 1
            elif held is not None or twin is not None:
                out["users_conflicting"] += 1
            else:
                tx._insert(sm.USERS, {"_id": uid, "email": email, "password_hash": pw,
                                      "display_name": name, "disabled": bool(off),
                                      "created_at": born, "generation": gen,
                                      "group_ids": sorted(member.get(uid, ()))})
                out["users_inserted"] += 1
        live = tx.known_user_ids()
        for slug, uid, rel in d["project_grants"]:
            grant = sm.MongoAuthTx._grant(slug, uid, rel)
            if uid in live and tx._get(sm.GRANTS, grant["_id"]) is None:
                tx._insert(sm.GRANTS, grant)
                out["grants_inserted"] += 1
        for digest, uid, born, until in d["sessions"] if sessions else ():
            if until > db.now_iso() and uid in live and not tx.has_session(digest):
                tx.insert_session(digest, uid, born, until)
                out["sessions_inserted"] += 1
        for coll, n in ((sm.USERS, out["users_inserted"]), (sm.GROUPS, out["groups_inserted"])):
            if n:
                _seed_allocator(tx, coll)
    return out


def verify_auth(d: AuthData) -> int:
    """Accounts in the file that are missing or differ in Mongo (id, generation, hash, disabled)."""
    from autotester.auth.store_mongo import MongoAuthStore
    from autotester.store.mongo_backend import default_store

    store = MongoAuthStore(default_store())
    if not store.exists():
        return len(d["users"])
    with store.reading() as tx:
        got = [tx.login_record(row[1]) for row in d["users"]]
    return sum(not (g and (g[0].id, g[0].generation, g[1], g[0].disabled) == (r[0], r[6], r[2],
               bool(r[4]))) for g, r in zip(got, d["users"], strict=True))


@contextlib.contextmanager
def credentials_on() -> Iterator[None]:
    """The credential door only opens with the credentials area on mongo; migrating before the G1
    flip turns it on for this process alone."""
    key, old = "AUTOTESTER_STORE_AREAS", os.environ.get("AUTOTESTER_STORE_AREAS")
    os.environ[key] = f"{old},credentials=mongo" if old else "credentials=mongo"
    try:
        yield
    finally:
        os.environ.pop(key) if old is None else os.environ.__setitem__(key, old)


def credential_pairs(root: Path, project: str | None) -> tuple[list[tuple[str, str, str]], int]:
    """`(slug, key, value)` for each key a project DECLARES that the repo-root `.env` sets, and how
    many were left out as deployment secrets (counted, never named: M36). Filtered here, BEFORE
    the door, so an undeclared `.env` line is never read into the store."""
    from autotester.store.project_store import ProjectStore

    path = root / ".env"
    env = {k: v for k, v in read_dotenv(path).items() if v} if path.is_file() else {}
    pairs, dropped = [], 0
    for slug in [project] if project else FileBackend(root).children("projects"):
        try:
            declared = [r.key for r in getattr(ProjectStore(slug, root).load_project(), "secrets", [])]
        except ValueError:
            continue
        dropped += sum(1 for k in declared if k in env and (k.upper() == MONGO_URI_ENV or is_server_key(k)))
        pairs += [(slug, k, env[k]) for k in declared if k in env and not (
            k.upper() == MONGO_URI_ENV or is_server_key(k))]
    return pairs, dropped


def import_credentials(pairs: list[tuple[str, str, str]], remote: bool, apply: bool) -> Counter[str]:
    """Through `ui/env_editor.py::put_credentials` (the door, M31); a stored key is never replaced."""
    from autotester.core.env import credential_collection
    from autotester.ui.env_editor import CredentialRefused, InvalidEnvValue, put_credentials

    out: Counter[str] = Counter()
    if not remote:
        out["to_insert"] = len(pairs)
        return out
    with credentials_on():
        coll = credential_collection()
        for slug, key, value in pairs:
            held = coll.find_one({"_id": key})
            if held is not None:
                out["unchanged" if (held.get("p"), held["value"]) == (slug, value) else "conflicting-id"] += 1
            elif apply:
                try:
                    put_credentials(slug, {key: value})
                    out["written"] += 1
                except (CredentialRefused, InvalidEnvValue):
                    out["refused"] += 1
            else:
                out["to_insert"] += 1
    return out
