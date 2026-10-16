"""One job: append a stamp to `qa/.last-tick` atomically and never shrink the file (AT-644).

`loop-status` treats this log as the liveness record, so a truncating `>` write silently
turns a long outage into a clean 2-tick history. The write here reads the old content,
builds old + new line, writes a temp file in the same directory and `os.replace`s it, so a
reader sees the old or the new file, never a partial one; it refuses to replace when the
result would have fewer lines than before.
"""

from __future__ import annotations

import os
from pathlib import Path


def append_tick(path: Path, line: str) -> None:
    """Append one stamp line to `path` via temp file + replace; raise if it would shrink."""
    line = line.rstrip("\r\n")
    if not line.strip():
        raise ValueError("tick line is empty")
    old = path.read_bytes() if path.exists() else b""
    if old and not old.endswith(b"\n"):
        old += b"\n"
    new = old + line.encode("utf-8") + b"\n"
    if new.count(b"\n") <= old.count(b"\n"):
        raise ValueError(f"refusing to shrink {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with tmp.open("wb") as handle:
            handle.write(new)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
