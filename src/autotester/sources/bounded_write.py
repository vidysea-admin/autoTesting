"""One bounded, hashing copy for every intake path (zip member, Drive fetch).

Contract: team-intake.md TI2 and TI9. A body is written chunk by chunk and stops the moment the
NEXT chunk would take it past the cap, so what reaches disk never exceeds the cap and what was
READ never exceeds the cap plus one chunk. The partial file is removed before the error leaves.
Memory does not grow with the file, and an endless source ends at the cap.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

CHUNK_SIZE = 64 * 1024


class LimitExceeded(Exception):
    """The body is larger than its cap. `written` is what had reached disk (then removed)."""

    def __init__(self, cap: int, written: int) -> None:
        super().__init__(f"body exceeds {cap} bytes")
        self.cap, self.written = cap, written


class CopyResult(NamedTuple):
    size: int
    sha256: str
    md5: str | None


def copy_bounded(chunks: Iterable[bytes], dest: Path, cap: int, *, want_md5: bool = False
                 ) -> CopyResult:
    """Write `chunks` to `dest`, hashing as it goes; past `cap`, raise `LimitExceeded`
    (the partial file is removed first)."""
    sha, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False) if want_md5 else None
    written = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with dest.open("wb") as handle:
            for chunk in chunks:
                if written + len(chunk) > cap:
                    raise LimitExceeded(cap, written)
                handle.write(chunk)
                sha.update(chunk)
                if md5 is not None:
                    md5.update(chunk)
                written += len(chunk)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return CopyResult(written, sha.hexdigest(), md5.hexdigest() if md5 is not None else None)


def read_chunks(stream, first: bytes = b"") -> Iterable[bytes]:
    """`first` (already read, for a signature sniff) then `stream.read(CHUNK_SIZE)` until empty."""
    if first:
        yield first
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            return
        yield chunk
