"""One job: append a stamp to `qa/.last-tick` atomically and never shrink the file (AT-644).

`loop-status` treats this log as the liveness record, so a truncating `>` write silently
turns a long outage into a clean 2-tick history. The write takes a sidecar lock, reads the
old content, writes old + new line to a uniquely named temp file and `os.replace`s it, so a
reader sees the old or the new file, never a partial one, and concurrent appenders cannot
lose each other's line. On Windows `os.replace` fails while a reader holds the target
open; it is retried with short backoff and, if every retry fails, the error is raised so a
tick is never lost silently.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path

from autotester.core.file_lock import file_lock

_RETRY_DELAYS_S = (0.02, 0.05, 0.1, 0.2, 0.4, 0.8)


def _replace_with_retry(tmp: Path, path: Path) -> None:
    for delay in (*_RETRY_DELAYS_S, None):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if delay is None:
                raise
            time.sleep(delay)


def append_tick(path: Path, line: str) -> None:
    """Append one stamp line to `path` via temp file + replace; raise if it would shrink."""
    line = line.rstrip("\r\n")
    if not line.strip():
        raise ValueError("tick line is empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path.with_name(path.name + ".lock"), timeout_s=30.0, what="tick log"):
        old = path.read_bytes() if path.exists() else b""
        if old and not old.endswith(b"\n"):
            old += b"\n"
        new = old + line.encode("utf-8") + b"\n"
        if new.count(b"\n") <= old.count(b"\n"):
            raise ValueError(f"refusing to shrink {path}")
        tmp = path.with_name(
            f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
        try:
            with tmp.open("wb") as handle:
                handle.write(new)
                handle.flush()
                os.fsync(handle.fileno())
            _replace_with_retry(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
