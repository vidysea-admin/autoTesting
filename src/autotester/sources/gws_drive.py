"""The real Drive seam: the existing `gws` CLI login behind `DriveFetcher` (metadata, list, fetch).

Contract: team-intake.md TI7 and TI8, hosting.md HO32/HO33; the owner's answer in
qa/gates/drive-identity.md (D-081): fetching shells out to `gws`; no token is copied into this
repo and none is read here. Only validated Drive ids reach the command line (never a URL, never
a file name), a download goes to a private folder under `work_root`, is bounded by the shared
upload limit and a timeout, and any non-video, non-zip type is refused before a byte moves.
Failures become `DriveError` with a fixed message (`drive_errors`).
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from autotester.core.ids import ulid
from autotester.core.upload_limit import human_bytes, read_max_upload_bytes
from autotester.schema.intake import DriveItem
from autotester.sources.bounded_write import CHUNK_SIZE, LimitExceeded
from autotester.sources.drive_errors import DriveError, DriveFailure, classify_gws_failure
from autotester.sources.drive_link import DRIVE_ID
from autotester.sources.drive_verify import DriveVerifyError
from autotester.sources.gws_runner import GwsResult, GwsRunner, SubprocessGwsRunner

FOLDER_MIME = "application/vnd.google-apps.folder"
ZIP_MIMES = frozenset({"application/zip", "application/x-zip-compressed", "application/x-zip"})
_FIELDS = "id,name,mimeType,size,md5Checksum"
_OUT_NAME = "download.part"
_MAX_PAGES = 10
_PAGE_SIZE = 1000
META_TIMEOUT_S = 60.0
DOWNLOAD_TIMEOUT_S = 3600.0


def item_kind(item: DriveItem) -> str:
    """`video | zip | folder | other`, decided by Drive's own type, never by the file name."""
    if item.mime_type == FOLDER_MIME:
        return "folder"
    if item.mime_type.startswith("video/"):
        return "video"
    return "zip" if item.mime_type in ZIP_MIMES else "other"


def _require_id(value: str) -> str:
    if not DRIVE_ID.fullmatch(value):
        raise DriveVerifyError("that is not a valid Google Drive id "
                               "(letters, digits, - and _ only)")
    return value


def _params(**values: Any) -> list[str]:
    return ["--params", json.dumps(values, separators=(",", ":"))]


def _item(raw: Any) -> DriveItem:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        raise DriveError(DriveFailure.NETWORK_ERROR)
    size = raw.get("size")
    try:
        size = int(size) if size is not None else None
    except (TypeError, ValueError):
        size = None
    md5 = raw.get("md5Checksum")
    return DriveItem(id=raw["id"], name=str(raw.get("name") or ""),
                     mime_type=str(raw.get("mimeType") or ""), size=size,
                     md5=md5 if isinstance(md5, str) else None)


def _json(result: GwsResult) -> dict:
    if result.returncode != 0:
        raise DriveError(classify_gws_failure(result.stdout, result.stderr))
    try:
        body = json.loads(result.stdout)
    except ValueError:
        raise DriveError(DriveFailure.NETWORK_ERROR) from None
    if not isinstance(body, dict):
        raise DriveError(DriveFailure.NETWORK_ERROR)
    return body


class _StagedDownload:
    """A finished `gws` download on disk: Drive's size and md5, the bytes, and `close()`."""

    def __init__(self, folder: Path, item: DriveItem) -> None:
        self._folder, self.size, self.md5 = folder, item.size, item.md5

    def chunks(self) -> Iterator[bytes]:
        with (self._folder / _OUT_NAME).open("rb") as handle:
            while chunk := handle.read(CHUNK_SIZE):
                yield chunk

    def close(self) -> None:
        shutil.rmtree(self._folder, ignore_errors=True)


class GwsDrive:
    """`DriveFetcher` over the `gws` CLI. `limit_bytes` is the shared upload-limit accessor."""

    def __init__(self, runner: GwsRunner | None, work_root: Path, *,
                 limit_bytes: Callable[[], int] | None = None) -> None:
        self._runner = runner or SubprocessGwsRunner()
        self._work_root = work_root
        self._limit = limit_bytes or (lambda: read_max_upload_bytes().bytes)

    def metadata(self, file_id: str) -> DriveItem:
        args = ["drive", "files", "get",
                *_params(fileId=_require_id(file_id), fields=_FIELDS, supportsAllDrives=True)]
        return _item(_json(self._runner.run(args, cwd=None, timeout_s=META_TIMEOUT_S)))

    def list_folder(self, folder_id: str) -> list[DriveItem]:
        query = f"'{_require_id(folder_id)}' in parents and trashed=false"
        items: list[DriveItem] = []
        token: str | None = None
        for _ in range(_MAX_PAGES):
            extra = {"pageToken": token} if token else {}
            args = ["drive", "files", "list", *_params(
                q=query, pageSize=_PAGE_SIZE, supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields=f"nextPageToken,files({_FIELDS})", **extra)]
            body = _json(self._runner.run(args, cwd=None, timeout_s=META_TIMEOUT_S))
            items.extend(_item(raw) for raw in body.get("files", []))
            token = body.get("nextPageToken")
            if not token:
                break
        return items

    def open(self, file_id: str) -> _StagedDownload:
        """Download one video or zip into a private folder; the caller `close()`s it."""
        item = self.metadata(file_id)
        if item_kind(item) not in ("video", "zip"):
            raise DriveVerifyError("that Drive file is not a video or a zip; only recordings "
                                   "are fetched")
        limit = self._limit()
        if item.size is not None and item.size > limit:
            raise DriveVerifyError(f"the file is {human_bytes(item.size)}, over the upload "
                                   f"limit of {human_bytes(limit)}")
        folder = self._work_root / f"dl-{ulid()}"
        args = ["drive", "files", "get", *_params(fileId=item.id, alt="media",
                                                  supportsAllDrives=True), "-o", _OUT_NAME]
        try:
            result = self._run_download(args, folder, limit)
            if result.returncode != 0:
                raise DriveError(classify_gws_failure(result.stdout, result.stderr))
            if not (folder / _OUT_NAME).is_file():
                raise DriveError(DriveFailure.NETWORK_ERROR)
        except LimitExceeded:
            shutil.rmtree(folder, ignore_errors=True)
            raise DriveVerifyError(f"the download passed the upload limit of "
                                   f"{human_bytes(limit)} and was stopped") from None
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        return _StagedDownload(folder, item)

    def _run_download(self, args: list[str], folder: Path, limit: int) -> GwsResult:
        return self._runner.download(args, cwd=folder, out_name=_OUT_NAME, max_bytes=limit,
                                     timeout_s=DOWNLOAD_TIMEOUT_S)
