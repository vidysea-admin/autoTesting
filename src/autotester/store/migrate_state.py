"""Copy the file-backed state into the Mongo state store, or compare the two (mongo-store U8).

One job: the file-to-Mongo comparison and copy behind `autotester store migrate` and `verify`.
The same walk serves both: it classifies every key (document, blob, or never moves: M25),
compares each with what the target holds, and writes only on `apply`. Blobs go in before the
documents that name them. A stored value that differs from the file is a conflict and is never
overwritten; no source file is read for write, moved or deleted. Approvals and revocations travel
as the exact rows they are, so a signed row is never re-signed (M43). A dry run passes
`tgt=None, blobs=None`: no connection exists to open. Nothing here prints; callers render a `Tally`.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autotester.core.safe_names import UnsafeName, safe_key
from autotester.store import mongo_routes as routes
from autotester.store.blobs import BlobRefused
from autotester.store.filestore import FileBackend

PRIVATE = ".work/ceo-bench/"  # D-128: moves, but only its count and hash are ever reported
ROOT_DIRS = ("projects/", ".work/notification_prefs/", ".work/drive-jobs/", ".work/team/", PRIVATE)
ROOT_FILES = (".work/run_queue.json", ".work/audit.jsonl", ".work/server_settings.json")
SKIP = frozenset({"profiles", "chunks", "exports", "crawl_summaries", ".blobmeta"})
IMAGES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})
VIDEOS = frozenset({".webm", ".mp4", ".mov", ".mkv"})
BINARY = IMAGES | VIDEOS | {".pdf", ".mp3", ".m4a", ".wav", ".ogg", ".opus", ".zip"}
EXACT = frozenset({"approvals", "approval_revocations"})  # M43: compared as written
Found = tuple[list[str], dict[str, str]]  # (document keys, blob key -> kind)


@dataclass
class Tally:
    """What a run found, per collection, without one value in it."""

    counts: dict[str, Counter[str]] = field(default_factory=dict)
    kinds: Counter[str] = field(default_factory=Counter)  # bytes per kind
    sizes: list[tuple[int, str]] = field(default_factory=list)  # documents only
    skipped: Counter[str] = field(default_factory=Counter)  # M25: scratch, profiles, chunks, ...
    unsafe: list[str] = field(default_factory=list)  # keys that failed safe_key
    private: list[str] = field(default_factory=list)  # sha256 of each private file (D-128)

    def note(self, coll: str, status: str, size: int, key: str, kind: str) -> None:
        self.counts.setdefault(coll, Counter())[status] += 1
        self.kinds[kind] += size
        if kind != "blob" and not key.startswith(PRIVATE):  # a private file's name is not shown
            self.sizes.append((size, key))

    def private_line(self) -> str:
        """The only thing the report says about the CEO-benchmark list: a count and one hash."""
        digest = hashlib.sha256("".join(sorted(self.private)).encode()).hexdigest()
        return f"ceo-bench (private, D-128): {len(self.private)} file(s), content hash {digest}"

    def bad(self) -> int:
        """Anything that is not already the same in the target (a verify failure)."""
        return sum(n for c in self.counts.values() for s, n in c.items() if s != "unchanged")

    def stuck(self) -> int:
        """What an apply could not settle: a conflict or a refusal."""
        return sum(c["conflicting-id"] + c["refused"] for c in self.counts.values())


def classify_key(key: str) -> tuple[str, str]:
    """`(doc|blob|skip, kind or reason)`: profiles, chunks, exports, `.env*`, xlsx never move."""
    parts, suffix = key.split("/"), Path(key).suffix.lower()
    for part in parts:
        if part in SKIP or part.startswith(".env"):
            return "skip", part
    if suffix == ".xlsx":
        return "skip", suffix
    if suffix in VIDEOS:
        return "blob", "video" if "runs" in parts else "source"
    if suffix in BINARY:
        shot = suffix in IMAGES and {"runs", "crawl"} & set(parts)
        return "blob", "screenshot" if shot else "source"
    return "doc", routes.route(key).collection


def _count_scratch(src: FileBackend, t: Tally) -> None:
    """M25: what sits outside the migrated roots is named in the report, never listed as work."""
    known = (*ROOT_DIRS[1:], *ROOT_FILES)
    for key in src.keys(".work/"):
        if not key.startswith(known):
            t.skipped[".work-scratch"] += 1
    if src.exists(".env"):
        t.skipped[".env"] += 1


def scan_tree(src: FileBackend, project: str | None, t: Tally) -> Found:
    roots = [f"projects/{project}/", f"{PRIVATE}{project}/"] if project else ROOT_DIRS
    keys = {k for d in roots for k in src.keys(d)}
    keys |= {k for k in ROOT_FILES if not project and src.exists(k)}
    if not project:
        _count_scratch(src, t)
    docs: list[str] = []
    blobs: dict[str, str] = {}
    for key in sorted(keys):
        try:
            safe_key(key)
            action, what = classify_key(key)
        except UnsafeName:
            t.unsafe.append("<private>" if key.startswith(PRIVATE) else key)
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
        except (ValueError, AttributeError, UnicodeDecodeError):
            continue
        out |= {f"{key.rpartition('/')[0]}/{e['path']}" for e in items
                if isinstance(e, dict) and e.get("masked") is False and "path" in e}
    return out


def _blob(src: FileBackend, key: str, kind: str, blobs: Any, apply: bool, bare: set[str],
          t: Tally) -> None:
    data = src.get_bytes(key) or b""
    held = blobs.stat(key) if blobs is not None else None
    sha = hashlib.sha256(data).hexdigest()
    if key.startswith(PRIVATE):
        t.private.append(sha)
    status = ("to_insert" if held is None else
              "unchanged" if held.sha256 == sha else "conflicting-id")
    if apply and status == "to_insert":
        try:
            blobs.put(key, data, kind=kind, masked=key not in bare,
                      content_type=mimetypes.guess_type(key)[0] or "application/octet-stream")
            status = "written"
        except (BlobRefused, UnsafeName):
            status = "refused"
    t.note("gridfs", status, len(data), key, "blob")


def migrate_state(src: FileBackend, found: Found, t: Tally, tgt: Any, blobs: Any, apply: bool,
                  wanted: set[str]) -> None:
    """Blobs first, then documents (M42). `tgt`/`blobs` are `None` when nothing is connected."""
    docs, media = found
    if "blobs" in wanted:
        bare = _unmasked(src, docs)
        for key, kind in media.items():
            _blob(src, key, kind, blobs, apply, bare, t)
    for key in (k for k in docs if routes.route(k).area in wanted):
        try:
            text = src.get(key) or ""
        except UnicodeDecodeError:
            t.skipped["not-utf8"] += 1
            continue
        if key.startswith(PRIVATE):
            t.private.append(hashlib.sha256(text.encode()).hexdigest())
        status = doc_status(text, tgt, key)
        if apply and status == "to_insert":
            status = _write(tgt, key, text)
        route = routes.route(key)
        t.note(route.collection, status, len(text.encode()), key, "rows" if route.rows else "doc")


def verify_approvals(tgt: Any, docs: list[str]) -> Counter[str]:
    """M43: every approval row the target holds is intact, and signed rows verify when the key is
    present. Reads the approval key (verify only; `migrate` never touches it)."""
    from autotester.core.ids import SigningKeyMissing
    from autotester.schema.approval import RunApproval
    from autotester.schema.approval_revocation import ApprovalRevocation

    out: Counter[str] = Counter()
    for key in (k for k in docs if routes.route(k).collection in EXACT):
        model = RunApproval if routes.route(key).collection == "approvals" else ApprovalRevocation
        for row in tgt.rows(key):
            try:
                item = model.model_validate_json(row)
            except ValueError:
                out["unreadable"] += 1
                continue
            if isinstance(item, RunApproval):
                out["not_intact"] += not item.is_intact
                try:
                    ok = not item.signature or item.is_signed_and_verified
                    out["signature_failed"] += not ok
                except SigningKeyMissing:
                    out["signature_unchecked"] += 1
            out["rows"] += 1
    return out
