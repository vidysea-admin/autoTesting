"""The files the scheduler writes: slot claim markers, slot records and the tick heartbeat.

Its one job is making those writes safe on Windows and Ubuntu with only `os.open`/`os.replace`
(R65: no `fcntl`, no `flock`). The caller passes every path; this module knows no data root.

- **Claim marker**: `os.open(O_CREAT | O_EXCL | O_WRONLY)` is the atomic "first wins" for a
  slot. The file name is the percent-encoded `slot_key` (reversible, no `:` for Windows).
- **Slot record**: one JSON line appended with a single `os.write` on an `O_APPEND` handle.
- **Purge**: `purge_project` removes a deleted project's markers and its own records file,
  together or not at all.
- **Heartbeat**: written to a temp file then `os.replace`d, so a reader sees old or new, never half.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

from pydantic import ValidationError

from autotester.schema.schedule import SlotClaim, SlotRecord

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


def append_record(path: Path, record: SlotRecord) -> bool:
    """Append one record unless its slot already has one. True when a line was written.

    Idempotent per `slot_key`: a re-drive that races the original winner writes nothing. The
    check-then-append has a tiny window, so `read_records` also keeps only the first record
    per slot, and a duplicate line can never show twice."""
    if any(r.slot_key == record.slot_key for r in read_records(path)):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (record.model_dump_json() + "\n").encode("utf-8")
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)
    return True


def read_records(path: Path) -> list[SlotRecord]:
    """One record per slot, oldest first. A torn line (power cut mid-append) is skipped, not
    fatal, and a second line for the same slot (a re-drive race) is ignored."""
    if not path.is_file():
        return []
    out: list[SlotRecord] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = SlotRecord.model_validate_json(line)
        except ValidationError:
            continue
        if rec.slot_key not in seen:
            seen.add(rec.slot_key)
            out.append(rec)
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


def purge_project(claim_dir: Path, records_path: Path, project: str) -> None:
    """Delete a project's claim markers and its records file (project deleted, HO24). Idempotent.

    Two-phase, so the markers and the records go together or not at all: every file is first
    `os.replace`d into a staging directory (rolled back if any move fails, e.g. a Windows sharing
    violation), then the staging directory is removed. Refuses a records file that holds another
    project's lines (the old shared layout): purging it would mean rewriting them."""
    if records_path.is_file() and any(r.project != project for r in read_records(records_path)):
        raise ValueError(f"{records_path.name} is shared with another project; "
                         "records are kept one file per project (project_records_path)")
    files = [claim_path(claim_dir, k) for k in list_claims(claim_dir)
             if k.startswith(f"{project}:")]
    files += [records_path] if records_path.is_file() else []
    if not files:
        return
    stage = claim_dir.parent / f".purge-{uuid.uuid4().hex}"
    stage.mkdir(parents=True)
    moved: list[tuple[Path, Path]] = []
    try:
        for n, src in enumerate(files):
            os.replace(src, stage / str(n))
            moved.append((src, stage / str(n)))
    except OSError:
        for src, held in reversed(moved):
            os.replace(held, src)
        shutil.rmtree(stage, ignore_errors=True)
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
