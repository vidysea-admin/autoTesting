"""The files the scheduler writes: slot claim markers, slot records and the tick heartbeat.

Its one job is making those writes safe on Windows and Ubuntu with only `os.open`/`os.replace`
(R65: no `fcntl`, no `flock`). The caller passes every path; this module knows no data root.

- **Claim marker**: `os.open(O_CREAT | O_EXCL | O_WRONLY)` is the atomic "first wins" for a
  slot. The file name is the percent-encoded `slot_key` (reversible, no `:` for Windows).
- **Slot record**: one JSON line appended with a single `os.write` on an `O_APPEND` handle.
- **Heartbeat**: written to a temp file then `os.replace`d, so a reader sees old or new, never half.
"""

from __future__ import annotations

import json
import os
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


def append_record(path: Path, record: SlotRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (record.model_dump_json() + "\n").encode("utf-8")
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def read_records(path: Path) -> list[SlotRecord]:
    """All records, oldest first. A torn line (power cut mid-append) is skipped, not fatal."""
    if not path.is_file():
        return []
    out: list[SlotRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(SlotRecord.model_validate_json(line))
        except ValidationError:
            continue
    return out


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
