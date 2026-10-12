"""Guard for `qa/.last-tick`: atomic appends, and detection of a truncated file.

AT-644 (D-087 item 2, Approved-by Umesh): a session once wrote the tick log with
`>` instead of `>>`, collapsing 47 annotated lines to 2 bare stamps, and
`loop-status --strict` read that as a clean two-tick history -- a false all-clear
from the detector built to catch a dead loop. Nothing in src/ writes the file, so
the guard is twofold: `append_tick` is the one safe write path (temp file in the
same directory, fsync, `os.replace`; it refuses to produce a file with fewer
lines than it read), and `problems` lets a reader flag a file that is empty,
partial, or not in tick format instead of silently trusting it.

Format is unchanged: each entry starts with an ISO stamp (some span several lines)
and the file ends with a newline.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from autotester.core.paths import repo_root

_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})(\s|$)")


class TickGuardError(Exception):
    """A write that would damage `qa/.last-tick` was refused."""


def tick_path() -> Path:
    return repo_root() / "qa" / ".last-tick"


def text_problems(text: str) -> list[str]:
    """Why `text` is not a trustworthy tick log; empty list means it is valid."""
    if not text.strip():
        return ["empty: no tick lines"]
    found = []
    if not text.endswith("\n"):
        found.append("partial: last line has no trailing newline (interrupted write)")
    # Entries may span several lines (continuation prose), so only the first
    # line must be a stamp.
    if not _STAMP.match(text.lstrip()):
        found.append("first line does not start with an ISO stamp")
    return found


def problems(path: Path) -> list[str]:
    """Problems with the tick log at `path`. A missing file is not a problem here."""
    if not path.exists():
        return []
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return ["not valid UTF-8"]
    return text_problems(text)


def atomic_write(path: Path, text: str) -> None:
    """Temp file next to `path`, fsync, then `os.replace`: never a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-tick-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def append_tick(path: Path, line: str) -> None:
    """Append one tick line atomically; refuse if it would shrink or corrupt the log."""
    line = line.rstrip("\r\n")
    if "\n" in line or not _STAMP.match(line):
        raise TickGuardError("tick line must be one line starting with an ISO stamp")
    old = path.read_bytes().decode("utf-8") if path.exists() else ""
    bad = problems(path) if old else []
    if bad:
        raise TickGuardError(f"existing {path.name} is damaged, not appending: {bad[0]}")
    new = old + line + "\n"
    if len(new.splitlines()) < len(old.splitlines()):
        raise TickGuardError("refusing a write that shrinks the tick log")
    atomic_write(path, new)
