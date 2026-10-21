"""Read one multipart upload from the wire into a staged file, stopping at the admin limit.

Contract: hosting.md HO30 and team-intake.md TI9. The framework's own `UploadFile` spools the
whole body before a handler runs, so it cannot stop an endless one. Here the body is pulled one
chunk at a time and fed to a streaming parser; the file part is written, hashed and counted as it
arrives, and the byte that would pass the limit ends the read (nothing from the declared
`Content-Length` is trusted: it can lie either way). What reaches disk never exceeds the limit
and what was read never exceeds the limit plus one chunk plus the form overhead.

The file's NAME is checked the moment its headers end, before a byte of it is stored: only a
recording suffix or `.zip` goes on. The name is never used as a path; the caller stores the
bytes under a generated name.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO
from urllib.parse import parse_qs

from fastapi import Request
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import MultipartParser, parse_options_header

from autotester.core.upload_limit import human_bytes
from autotester.sources.bounded_write import LimitExceeded
from autotester.stages.ingest import NotARecording, require_recording_suffix

FORM_OVERHEAD = 256 * 1024
"""Headers and small text fields around the file; the body as a whole may not pass limit + this."""
FIELD_CAP = 16 * 1024
MAX_FIELDS = 8
FIELDS_TOTAL_CAP = 32 * 1024
"""At most this many text fields, and this many bytes of them together, are kept (the form
only uses `label`); more is refused so memory cannot grow with the body."""
HEADER_CAP = 8 * 1024
FORM_CAP = 64 * 1024
FILE_FIELD = "recording"
STAGED_NAME = "upload.part"


class UploadRefused(Exception):
    """The upload was refused; `status` and `message` go to the page. Nothing was registered."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status, self.message = status, message


class StagedUpload:
    """What a finished read left behind: the staged file, its client name, hash and text fields."""

    def __init__(self, path: Path, filename: str, size: int, sha256: str, is_zip: bool,
                 fields: dict[str, str]) -> None:
        self.path, self.filename, self.size, self.sha256 = path, filename, size, sha256
        self.is_zip, self.fields = is_zip, fields


def _too_big(limit: int) -> UploadRefused:
    return UploadRefused(413, f"That upload is larger than the {human_bytes(limit)} limit the "
                              "administrator set. Send a smaller file, or ask for the limit to "
                              "be raised.")


def _vet_name(filename: str) -> bool:
    """True for a zip, False for a recording; anything else is refused (TI3, nothing stored)."""
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    if base.lower().endswith(".zip"):
        return True
    try:
        require_recording_suffix(base)
    except NotARecording as exc:
        raise UploadRefused(400, f"{exc}, or a .zip of them") from None
    return False


class _Reader:
    """The parser callbacks: collects part headers, text fields, and the one file part."""

    def __init__(self, staging: Path, limit: int,
                 vet: Callable[[str], bool] = _vet_name) -> None:
        self.staging, self.limit, self._vet = staging, limit, vet
        self.fields: dict[str, str] = {}
        self.filename: str | None = None
        self.is_zip = False
        self.size = 0
        self.sha = hashlib.sha256()
        self._handle: BinaryIO | None = None
        self._name = ""
        self._buffer = bytearray()
        self._head: dict[bytes, bytes] = {}
        self._key = b""
        self._value = b""
        self._file_done = False
        self._current_is_file = False
        self._kept = 0

    def callbacks(self) -> dict:
        return {"on_part_begin": self._begin, "on_header_field": self._hfield,
                "on_header_value": self._hvalue, "on_header_end": self._hend,
                "on_headers_finished": self._headers, "on_part_data": self._data,
                "on_part_end": self._end}

    def _begin(self) -> None:
        self._head, self._key, self._value, self._buffer = {}, b"", b"", bytearray()
        self._name, self._current_is_file = "", False

    def _hfield(self, data: bytes, start: int, end: int) -> None:
        self._key += data[start:end]
        self._check_header_size()

    def _hvalue(self, data: bytes, start: int, end: int) -> None:
        self._value += data[start:end]
        self._check_header_size()

    def _check_header_size(self) -> None:
        if len(self._key) + len(self._value) > HEADER_CAP:
            raise UploadRefused(400, "A form header in that upload is too long.")

    def _hend(self) -> None:
        self._head[self._key.lower()] = self._value
        self._key = self._value = b""

    def _headers(self) -> None:
        _, params = parse_options_header(self._head.get(b"content-disposition", b""))
        self._name = params.get(b"name", b"").decode("utf-8", "replace")
        raw = params.get(b"filename")
        self._current_is_file = raw is not None
        if raw is None:
            return
        if self._file_done or self._handle is not None:
            raise UploadRefused(400, "Send one file at a time.")
        name = raw.decode("utf-8", "replace")
        if not name.strip():
            raise UploadRefused(400, "Choose a file to upload.")
        self.is_zip = self._vet(name)
        self.filename = name
        self.staging.mkdir(parents=True, exist_ok=True)
        self._handle = (self.staging / STAGED_NAME).open("wb")

    def _data(self, data: bytes, start: int, end: int) -> None:
        piece = data[start:end]
        if self._current_is_file and self._handle is not None:
            if self.size + len(piece) > self.limit:
                raise LimitExceeded(self.limit, self.size)
            self._handle.write(piece)
            self.sha.update(piece)
            self.size += len(piece)
        elif not self._current_is_file:
            self._buffer += piece
            if len(self._buffer) > FIELD_CAP:
                raise UploadRefused(400, "A form field in that upload is too long.")

    def _end(self) -> None:
        if self._current_is_file and self._handle is not None:
            self._handle.close()
            self._handle, self._file_done = None, True
        elif not self._current_is_file and self._name:
            self._keep_field()

    def _keep_field(self) -> None:
        if self._name not in self.fields and len(self.fields) >= MAX_FIELDS:
            raise UploadRefused(400, "That upload has too many form fields.")
        self._kept += len(self._name) + len(self._buffer)
        if self._kept > FIELDS_TOTAL_CAP:
            raise UploadRefused(400, "The form fields in that upload are too long.")
        self.fields[self._name] = self._buffer.decode("utf-8", "replace")

    @property
    def complete(self) -> bool:
        """The file part's closing boundary arrived (a cut-off body never gets here)."""
        return self._file_done

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def _boundary(request: Request) -> bytes:
    kind, params = parse_options_header(request.headers.get("content-type", "").encode("latin-1"))
    boundary = params.get(b"boundary")
    if kind != b"multipart/form-data" or not boundary:
        raise UploadRefused(400, "That request is not a file upload form.")
    return boundary


async def stream_upload(request: Request, staging: Path, limit: int,
                        vet: Callable[[str], bool] = _vet_name) -> StagedUpload:
    """Read the request body into `staging`/upload.part; raises `UploadRefused` (413 over the
    limit, 400 for a bad name or form). The caller removes `staging` on every exit. `vet` judges
    the client's file name before a byte is stored (default: a recording or a zip, TI3); another
    caller passes its own, e.g. the benchmark answer list accepts only `.json`."""
    reader = _Reader(staging, limit, vet)
    parser = MultipartParser(_boundary(request), reader.callbacks())
    total = 0
    try:
        async for chunk in request.stream():
            total += len(chunk)
            if total > limit + FORM_OVERHEAD:
                raise _too_big(limit)
            parser.write(chunk)
        parser.finalize()
    except LimitExceeded:
        raise _too_big(limit) from None
    except MultipartParseError:
        raise UploadRefused(400, "That upload could not be read as a form.") from None
    finally:
        reader.close()
    if reader.filename is None:
        raise UploadRefused(400, "Choose a file to upload.")
    if not reader.complete:
        raise UploadRefused(400, "That upload was cut off before it finished.")
    if reader.size == 0:
        raise UploadRefused(400, "That file is empty.")
    return StagedUpload(staging / STAGED_NAME, reader.filename, reader.size,
                        reader.sha.hexdigest(), reader.is_zip, reader.fields)


async def read_small_form(request: Request) -> dict[str, str]:
    """A small urlencoded form (the Drive link box), bounded so it cannot be used to fill memory."""
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > FORM_CAP:
            raise UploadRefused(413, "That form is too large.")
    try:
        parsed = parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True,
                          max_num_fields=50)
    except ValueError:
        raise UploadRefused(400, "That form has too many fields.") from None
    return {key: values[0] for key, values in parsed.items()}
