"""The files the scheduler writes: slot claim markers, slot records and the tick heartbeat.

Its one job is making those writes safe on Windows and Ubuntu with only `os.open`/`os.replace`
(R65: no `fcntl`/`flock` here; appends also take `core.file_lock`, so processes
serialise). The caller passes every path; this module knows no data root.

- **Claim marker**: `os.open(O_CREAT | O_EXCL | O_WRONLY)` is the atomic "first wins" for a
  slot. The file name is the percent-encoded `slot_key` (reversible, no `:` for Windows).
- **Slot record**: one JSON line appended with a single `os.write` on an `O_APPEND` handle.
- **Purge**: `purge_project` removes a deleted project's markers and its own records file,
  together or not at all, also across an interrupt or a kill (a manifest lets the next purge adopt
  a stranded stage).
- **Heartbeat**: written to a temp file then `os.replace`d, so a reader sees old or new, never half.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

from pydantic import ValidationError

from autotester.core.file_lock import file_lock
from autotester.schema.schedule import SlotClaim, SlotOutcome, SlotRecord

_CLAIM_SUFFIX = ".claim"


def claim_path(claim_dir: Path, key: str) -> Path:
    return claim_dir / (quote(key, safe="") + _CLAIM_SUFFIX)


def claim(claim_dir: Path, key: str, body: SlotClaim) -> bool:
    """Atomically claim a slot. True for the one caller that created the marker, else False."""
    claim_dir.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(claim_path(claim_dir, key), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(body.model_dump_json())
    return True


def list_claims(claim_dir: Path) -> dict[str, SlotClaim | None]:
    """Every claimed slot key. The value is None while the winner has not finished writing
    (or the file is torn): the slot is still claimed, but cannot be re-driven yet."""
    out: dict[str, SlotClaim | None] = {}
    if not claim_dir.is_dir():
        return out
    for path in sorted(claim_dir.glob(f"*{_CLAIM_SUFFIX}")):
        key = unquote(path.name[: -len(_CLAIM_SUFFIX)])
        try:
            out[key] = SlotClaim.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValidationError):
            out[key] = None
    return out


class QueueUnreadable(Exception):
    """The run queue's file exists but cannot be read: whether the project is busy is unknown."""


def amend_record(path: Path, slot_key: str, outcome: SlotOutcome, detail: str) -> bool:
    """Record a terminal outcome for a slot already decided (a worker died after the enqueue,
    TS7) by APPENDING an `amended` line; `read_records` lets the latest amendment win. Nothing
    is rewritten, so a concurrent O_APPEND from another tick can never be lost. False when the
    slot has no record."""
    base = next((r for r in read_records(path) if r.slot_key == slot_key), None)
    if base is None:
        return False
    line = base.model_copy(update={"outcome": outcome, "detail": detail[:500], "amended": True})
    return _append_line(path, line)


_APPEND_LOCK = threading.RLock()  # Windows' CRT emulates O_APPEND (seek, write): not atomic


def _lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


def _append_line(path: Path, record: SlotRecord) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (record.model_dump_json() + chr(10)).encode("utf-8")
    # thread lock for in-process callers, file lock so separate OS processes serialise too
    with _APPEND_LOCK, file_lock(_lock_path(path), what="records"):
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_BINARY", 0))
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
    return True


def append_record(path: Path, record: SlotRecord) -> bool:
    """Append one record unless its slot already has one. True when a line was written.

    Idempotent per `slot_key`: a re-drive that races the original winner writes nothing. The
    check-then-append has a tiny window, so `read_records` also keeps only the first record
    per slot, and a duplicate line can never show twice."""
    if any(r.slot_key == record.slot_key for r in read_records(path)):
        return False
    return _append_line(path, record)


def read_records(path: Path) -> list[SlotRecord]:
    """One record per slot, oldest first. A torn line (power cut mid-append) is skipped, not
    fatal; a second plain line for the same slot (a re-drive race) is ignored, while an
    `amended` line replaces it in place (latest amendment wins)."""
    if not path.is_file():
        return []
    out: list[SlotRecord] = []
    seen: dict[str, int] = {}
    with _APPEND_LOCK:
        lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = SlotRecord.model_validate_json(line)
        except ValidationError:
            continue
        if rec.slot_key not in seen:
            seen[rec.slot_key] = len(out)
            out.append(rec)
        elif rec.amended:
            out[seen[rec.slot_key]] = rec
    return out


def read_all_records(records_dir: Path) -> list[SlotRecord]:
    """Every project's slot records (the inbox lists the blocked ones: TS5). Empty if none."""
    if not records_dir.is_dir():
        return []
    return [r for f in sorted(records_dir.glob("*.jsonl")) for r in read_records(f)]


def project_records_path(records_dir: Path, project: str) -> Path:
    """The one records file of a project. One file per project, never one shared file: a purge
    then never touches another project's lines, so a neighbour's append cannot be lost."""
    return records_dir / (quote(project, safe="") + ".jsonl")


_MANIFEST = "manifest.json"


def _stage_prefix(project: str) -> str:
    """Stage dirs are named per project, so a purge only ever adopts its own project's leftovers
    (another project's purge may be running right now)."""
    return ".purge-" + hashlib.sha256(project.encode("utf-8")).hexdigest()[:16] + "-"


def _restore_stage(stage: Path) -> bool:
    """Put back what an uncommitted purge moved into `stage`, then delete it. True once it is gone.

    The manifest is written before the first move and deleted at the commit point, so: no
    manifest means nothing to put back (never started, or committed and only the delete was
    interrupted); a manifest means the purge did not finish. Every file is tried (one stuck
    file never strands the rest), and a file is never put over one that is already there."""
    manifest = stage / _MANIFEST
    if not manifest.is_file():
        shutil.rmtree(stage, ignore_errors=True)
        return True
    try:
        sources = json.loads(manifest.read_text(encoding="utf-8"))["sources"]
    except (OSError, ValueError, KeyError, TypeError):
        return False
    clean = True
    for n, src in enumerate(sources):
        held, dest = stage / str(n), Path(src)
        if not held.exists():
            continue
        try:
            if dest.exists():
                raise FileExistsError(dest)
            os.replace(held, dest)
        except OSError:
            clean = False
    if clean:
        shutil.rmtree(stage, ignore_errors=True)
    return clean


def _recover_stages(claim_dir: Path, project: str) -> int:
    done = 0
    for stage in sorted(claim_dir.parent.glob(_stage_prefix(project) + "*")):
        done += stage.is_dir() and _restore_stage(stage)
    return done


def recover_stale_purges(claim_dir: Path, records_path: Path, project: str) -> int:
    """Adopt the `.purge-*` stage dirs a killed purge of this project left behind: put the files
    back if that purge had not committed, delete the stage if it had. Returns stages cleared."""
    with _APPEND_LOCK, file_lock(_lock_path(records_path), what="purge"):
        return _recover_stages(claim_dir, project)


def purge_project(claim_dir: Path, records_path: Path, project: str) -> None:
    """Delete a project's claim markers and its records file (project deleted, HO24). Idempotent.

    Two-phase, so the markers and the records go together or not at all: every file is first
    `os.replace`d into a staging directory, then the staging directory is removed. Any exception
    (OSError, SystemExit, Ctrl-C) rolls every file back. A hard kill cannot roll back by itself,
    so the stage keeps a manifest and the next purge of this project adopts it first
    (`_restore_stage`). Refuses a records file that holds another project's lines (the old
    shared layout): purging it would mean rewriting them."""
    with _APPEND_LOCK, file_lock(_lock_path(records_path), what="purge"):
        _recover_stages(claim_dir, project)
        _purge_locked(claim_dir, records_path, project)


def _purge_locked(claim_dir: Path, records_path: Path, project: str) -> None:
    if records_path.is_file() and any(r.project != project for r in read_records(records_path)):
        raise ValueError(f"{records_path.name} is shared with another project; "
                         "records are kept one file per project (project_records_path)")
    files = [claim_path(claim_dir, k) for k in list_claims(claim_dir)
             if k.startswith(f"{project}:")]
    files += [records_path] if records_path.is_file() else []
    if not files:
        return
    stage = claim_dir.parent / f"{_stage_prefix(project)}{uuid.uuid4().hex}"
    stage.mkdir(parents=True)
    try:
        (stage / (_MANIFEST + ".tmp")).write_text(
            json.dumps({"sources": [str(f) for f in files]}), encoding="utf-8")
        os.rename(stage / (_MANIFEST + ".tmp"), stage / _MANIFEST)  # all of it, or none
        for n, src in enumerate(files):
            os.replace(src, stage / str(n))
        (stage / _MANIFEST).unlink()  # the commit point: from here recovery deletes, not restores
    except BaseException:
        _restore_stage(stage)
        raise
    shutil.rmtree(stage, ignore_errors=True)


def write_heartbeat(path: Path, now: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"last_tick": now.isoformat()}), encoding="utf-8")
    os.replace(tmp, path)


def read_heartbeat(path: Path) -> datetime | None:
    """The last tick time, or None when absent or unreadable (never shown as healthy)."""
    try:
        stamp = datetime.fromisoformat(json.loads(path.read_text(encoding="utf-8"))["last_tick"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return stamp if stamp.tzinfo is not None else None
