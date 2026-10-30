"""One job: a cross-process advisory file lock (`msvcrt.locking` on Windows, `flock` elsewhere).

Shared by the env editor and the scheduler's append-only record files, so two OS processes
serialise their read-modify-write on the same sidecar inode. `atomic_write` is its companion:
the temp-file + `os.replace` write the state store's `FileBackend` uses.
"""

from __future__ import annotations

import contextlib
import math
import os
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path


def atomic_write(path: Path, text: str | bytes) -> None:
    """Replace `path` with `text` atomically: a reader sees the old file or the new one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        mode, options = ("wb", {}) if isinstance(text, bytes) else ("w", {"encoding": "utf-8"})
        with os.fdopen(fd, mode, **options) as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


@contextlib.contextmanager
def file_lock(lock_path: Path, timeout_s: float = 5.0, *, what: str = "file") -> Iterator[None]:
    """Hold an exclusive advisory lock on `lock_path` (created if absent). TimeoutError on wait."""
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError(f"{what} lock timeout must be positive and finite")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "r+b") as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            try:
                handle.write(b"\0")
                handle.flush()
            except PermissionError:
                pass  # another holder initialised and locked the byte first; it is there now
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"{what} writer lock timed out") from exc
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
