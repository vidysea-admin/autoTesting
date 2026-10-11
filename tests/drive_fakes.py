"""A fake Drive for intake tests: ids map to metadata and bytes, a download can lie about its size
or md5, and every `open` is recorded so a test can prove a file was NOT fetched."""

from __future__ import annotations

import hashlib

from autotester.schema.intake import DriveItem
from autotester.sources.drive_errors import DriveError

FOLDER = "application/vnd.google-apps.folder"


class FakeDownload:
    def __init__(self, data: bytes, size, md5):
        self.data, self.size, self.md5, self.closed = data, size, md5, False

    def chunks(self):
        for start in range(0, len(self.data), 64 * 1024):
            yield self.data[start:start + 64 * 1024]

    def close(self):
        self.closed = True


class FakeDrive:
    def __init__(self):
        self.items: dict[str, DriveItem] = {}
        self.data: dict[str, bytes] = {}
        self.children: dict[str, list[str]] = {}
        self.lie: dict[str, dict] = {}
        self.opened: list[str] = []
        self.downloads: list[FakeDownload] = []
        self.error: DriveError | None = None

    def add(self, fid, data=b"", *, name="clip.mp4", mime="video/mp4", checksums=True):
        self.items[fid] = DriveItem(
            id=fid, name=name, mime_type=mime, size=len(data) if checksums else None,
            md5=hashlib.md5(data, usedforsecurity=False).hexdigest() if checksums else None)
        self.data[fid] = data
        return fid

    def folder(self, fid, children):
        self.items[fid] = DriveItem(id=fid, name="a folder", mime_type=FOLDER)
        self.children[fid] = list(children)

    def metadata(self, file_id):
        if self.error:
            raise self.error
        return self.items[file_id]

    def list_folder(self, folder_id):
        return [self.items[c] for c in self.children[folder_id]]

    def open(self, file_id):
        self.opened.append(file_id)
        item = self.items[file_id]
        fields = {"size": item.size, "md5": item.md5, **self.lie.get(file_id, {})}
        download = FakeDownload(self.data[file_id], fields["size"], fields["md5"])
        self.downloads.append(download)
        return download
