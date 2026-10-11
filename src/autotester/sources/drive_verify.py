"""Drive fetch verification: bound the download, check size and md5, stage it, or remove it.

Contract: team-intake.md TI7 (R40), TI9 (the Drive path reads the shared upload limit), HO33.
The network is behind `DriveFetcher`, so this module is pure and testable with fakes: no HTTP,
no `gws` call, no credential ever passes through it. The real fetcher (the existing `gws` auth,
the HO32 host rules, the five failure messages of TI8) belongs to the integration slice and only
has to implement `open(file_id)`.

`fetch_and_verify` stops reading at the limit plus at most one chunk, compares the received byte
count and md5 with Drive's metadata when Drive supplied them (a mismatch refuses), and removes
the partial file on ANY failure. Errors it raises itself never carry a token or a URL; an
exception from the transport propagates unchanged for the caller to classify.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple, Protocol

from autotester.core.ids import ulid
from autotester.core.upload_limit import human_bytes, read_max_upload_bytes
from autotester.schema.intake import DriveItem
from autotester.sources.bounded_write import LimitExceeded, copy_bounded
from autotester.sources.drive_link import DRIVE_ID


class DriveVerifyError(Exception):
    """A Drive file that must not be registered: bad id, over the limit, size or md5 mismatch.
    The message is safe to show: it names sizes and limits only."""


class DriveDownload(Protocol):
    """One open download: Drive's metadata (None when Drive did not supply it) and the bytes."""

    size: int | None
    md5: str | None

    def chunks(self) -> Iterator[bytes]: ...

    def close(self) -> None:
        """Release whatever the download holds (a staged file); optional, idempotent."""


class DriveFetcher(Protocol):
    """The ONE injectable Drive seam (fetch, metadata and folder listing); a fake implements
    it in tests and `gws_drive.GwsDrive` implements it for real."""

    def open(self, file_id: str) -> DriveDownload: ...

    def metadata(self, file_id: str) -> DriveItem: ...

    def list_folder(self, folder_id: str) -> list[DriveItem]: ...


class StagedDownload(NamedTuple):
    """A verified file in staging. `verified` is False when Drive gave neither size nor md5."""

    path: Path
    size: int
    sha256: str
    md5: str
    verified: bool


def _check_declared(download: DriveDownload, max_bytes: int) -> None:
    if download.size is not None and download.size > max_bytes:
        raise DriveVerifyError(f"the file is {human_bytes(download.size)}, over the upload "
                               f"limit of {human_bytes(max_bytes)}")


def _compare(download: DriveDownload, size: int, md5: str) -> bool:
    """True when Drive supplied a size or md5 and the received bytes match every one supplied."""
    if download.size is not None and size != download.size:
        raise DriveVerifyError(f"size mismatch: received {size} bytes, Drive reports "
                               f"{download.size}")
    if download.md5 is not None and md5.lower() != download.md5.strip().lower():
        raise DriveVerifyError("md5 mismatch: the received bytes differ from Drive's checksum")
    return download.size is not None or download.md5 is not None


def fetch_and_verify(fetcher: DriveFetcher, file_id: str, staging: Path, *,
                     max_bytes: int | None = None) -> StagedDownload:
    """Stream `file_id` into `staging` under the upload limit and verify it against Drive.

    `max_bytes=None` reads the admin limit through the shared accessor at call time (TI9).
    On any failure nothing is left in `staging`. The staged name is generated, never Drive's."""
    if not DRIVE_ID.fullmatch(file_id):
        raise DriveVerifyError("that is not a valid Google Drive id "
                               "(letters, digits, - and _ only)")
    limit = max_bytes if max_bytes is not None else read_max_upload_bytes().bytes
    download = fetcher.open(file_id)
    dest = staging / f"drive-{ulid()}.part"
    chunks = None
    try:
        _check_declared(download, limit)
        chunks = download.chunks()
        copied = copy_bounded(chunks, dest, limit, want_md5=True)
        verified = _compare(download, copied.size, copied.md5 or "")
    except LimitExceeded:
        raise DriveVerifyError(f"the download passed the upload limit of {human_bytes(limit)}"
                               ) from None
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    finally:
        for closer in (getattr(chunks, "close", None), getattr(download, "close", None)):
            if closer is not None:
                closer()
    return StagedDownload(dest, copied.size, copied.sha256, copied.md5 or "", verified)
