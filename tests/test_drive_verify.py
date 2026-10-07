"""Drive fetch verification, pure core (team-intake.md TI7 verification, TI9 on the Drive path).

The fetch sits behind `DriveFetcher`, so every case here uses a fake: no network, no `gws`,
no token. The scenarios are the ones a real Drive download produces: a good file, a corrupted
or truncated one, a file bigger than the admin limit, and a stream that never ends.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from zip_fixtures import make_store

from autotester.core.upload_limit import SETTINGS_ENV
from autotester.schema.intake import DriveOrigin
from autotester.sources.bounded_write import CHUNK_SIZE
from autotester.sources.drive_verify import DriveVerifyError, fetch_and_verify
from autotester.sources.intake_commit import commit_video

MIB = 1024 * 1024
FILE_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz_-0123"


class FakeDownload:
    def __init__(self, parts: list[bytes], *, size: int | None, md5: str | None) -> None:
        self.size, self.md5, self._parts, self.consumed = size, md5, parts, 0

    def chunks(self) -> Iterator[bytes]:
        for part in self._parts:
            self.consumed += len(part)
            yield part


class FakeFetcher:
    def __init__(self, download: FakeDownload) -> None:
        self.download, self.opened = download, []

    def open(self, file_id: str) -> FakeDownload:
        self.opened.append(file_id)
        return self.download


def _good(data: bytes, **overrides) -> FakeFetcher:
    parts = [data[i:i + 1000] for i in range(0, len(data), 1000)] or [b""]
    meta = {"size": len(data), "md5": hashlib.md5(data).hexdigest()} | overrides
    return FakeFetcher(FakeDownload(parts, **meta))


def _leftovers(staging: Path) -> list[Path]:
    return [p for p in staging.rglob("*") if p.is_file()]


def test_ti7_good_md5_and_size_stage_the_file_with_its_sha256(tmp_path):
    """A shared Drive video whose metadata matches the bytes received."""
    data = b"V" * 5000
    staged = fetch_and_verify(_good(data), FILE_ID, tmp_path / "staging", max_bytes=MIB)
    assert staged.path.read_bytes() == data and staged.size == len(data)
    assert staged.sha256 == hashlib.sha256(data).hexdigest() and staged.verified


def test_ti7_wrong_md5_is_refused_and_staging_is_removed(tmp_path):
    """Drive's md5 does not match what arrived (bit-flip in transit)."""
    fetcher = _good(b"V" * 5000, md5="0" * 32)
    with pytest.raises(DriveVerifyError, match="md5"):
        fetch_and_verify(fetcher, FILE_ID, tmp_path / "staging", max_bytes=MIB)
    assert _leftovers(tmp_path / "staging") == []


def test_ti7_short_read_is_refused_and_staging_is_removed(tmp_path):
    """The connection dropped after 4000 of 5000 bytes."""
    fetcher = FakeFetcher(FakeDownload([b"V" * 4000], size=5000, md5=None))
    with pytest.raises(DriveVerifyError, match="size"):
        fetch_and_verify(fetcher, FILE_ID, tmp_path / "staging", max_bytes=MIB)
    assert _leftovers(tmp_path / "staging") == []


def test_ti7_a_drive_file_with_no_checksum_is_accepted_but_marked_unverified(tmp_path):
    """Google-native files carry neither md5 nor size."""
    fetcher = FakeFetcher(FakeDownload([b"V" * 100], size=None, md5=None))
    staged = fetch_and_verify(fetcher, FILE_ID, tmp_path / "staging", max_bytes=MIB)
    assert staged.verified is False and staged.size == 100


def test_ti7_uppercase_md5_from_drive_still_matches(tmp_path):
    """Some metadata sources upper-case the hex digest."""
    data = b"Q" * 300
    fetcher = _good(data, md5=hashlib.md5(data).hexdigest().upper())
    assert fetch_and_verify(fetcher, FILE_ID, tmp_path / "s", max_bytes=MIB).verified


@pytest.mark.parametrize("bad_id", ["", "../x", "a b", "a/b", "x" * 200, "id;rm -rf", "ab"])
def test_ti7_an_id_outside_the_drive_character_set_is_refused_before_any_fetch(tmp_path, bad_id):
    """A pasted value that is not a Drive id never reaches the fetcher."""
    fetcher = _good(b"V")
    with pytest.raises(DriveVerifyError, match="Drive id"):
        fetch_and_verify(fetcher, bad_id, tmp_path / "staging", max_bytes=MIB)
    assert fetcher.opened == []


def test_ti7_the_fetch_error_text_never_carries_a_token(tmp_path):
    """The transport fails with a token in its message: staging is cleaned and the
    exception is the caller's to classify (TI8), so nothing here repackages it."""
    class Boom(FakeDownload):
        def chunks(self):
            yield b"abc"
            raise ConnectionError("Authorization: Bearer CANARY-TOKEN")

    fetcher = FakeFetcher(Boom([], size=None, md5=None))
    with pytest.raises(ConnectionError):
        fetch_and_verify(fetcher, FILE_ID, tmp_path / "staging", max_bytes=MIB)
    assert _leftovers(tmp_path / "staging") == []


def test_ti7_a_verified_download_registers_with_a_drive_origin(tmp_path):
    """The Drive path registers exactly as an upload does, with the Drive file id as origin."""
    store = make_store(tmp_path)
    data = b"D" * 3000
    staged = fetch_and_verify(_good(data), FILE_ID, tmp_path / "staging", max_bytes=MIB)
    source, created = commit_video(store, staged.path, digest=staged.sha256, suffix=".mp4",
                                   label="from drive", origin=DriveOrigin(file_id=FILE_ID),
                                   uploaded_by="dev@x.io")
    assert created and Path(source.path).read_bytes() == data
    assert source.origin == DriveOrigin(file_id=FILE_ID) and source.uploaded_by == "dev@x.io"
    assert store.paths.source_dir(source.id) in Path(source.path).parents


# ---- TI9 on the Drive path ---------------------------------------------------

def test_ti9_declared_size_over_the_limit_is_refused_before_a_byte_is_fetched(tmp_path):
    """Drive's metadata already says the file is bigger than the admin limit."""
    fetcher = _good(b"V" * 2000)
    with pytest.raises(DriveVerifyError, match="limit"):
        fetch_and_verify(fetcher, FILE_ID, tmp_path / "staging", max_bytes=1000)
    assert fetcher.download.consumed == 0 and _leftovers(tmp_path / "staging") == []


def test_ti9_a_stream_with_no_end_stops_at_limit_plus_one_chunk(tmp_path):
    """An endless body (or a lying size) cannot hold a worker or fill the disk."""
    class Endless(FakeDownload):
        def chunks(self):
            while True:
                self.consumed += CHUNK_SIZE
                yield b"\0" * CHUNK_SIZE

    download = Endless([], size=None, md5=None)
    with pytest.raises(DriveVerifyError, match="limit"):
        fetch_and_verify(FakeFetcher(download), FILE_ID, tmp_path / "staging", max_bytes=MIB)
    assert download.consumed <= MIB + CHUNK_SIZE
    assert _leftovers(tmp_path / "staging") == []


def test_ti9_exactly_the_limit_succeeds_and_one_byte_more_is_refused(tmp_path):
    """Boundary on the Drive path, with the limit at 5 MiB."""
    exact = b"E" * (5 * MIB)
    ok = fetch_and_verify(_good(exact), FILE_ID, tmp_path / "a", max_bytes=5 * MIB)
    assert ok.size == 5 * MIB
    over = FakeFetcher(FakeDownload([exact, b"x"], size=None, md5=None))
    with pytest.raises(DriveVerifyError, match="5 MiB"):
        fetch_and_verify(over, FILE_ID, tmp_path / "b", max_bytes=5 * MIB)


def test_ti9_drive_path_reads_the_same_setting_at_request_time(tmp_path, monkeypatch):
    """With no explicit limit the fetch calls the shared accessor, so lowering the admin
    setting between two requests changes the second one."""
    settings = tmp_path / "server_settings.json"
    monkeypatch.setenv(SETTINGS_ENV, str(settings))
    data = b"S" * (3 * MIB)
    settings.write_text('{"max_upload_bytes": 5242880}', encoding="utf-8")
    assert fetch_and_verify(_good(data), FILE_ID, tmp_path / "one").size == len(data)
    settings.write_text('{"max_upload_bytes": 2097152}', encoding="utf-8")
    with pytest.raises(DriveVerifyError, match="2 MiB"):
        fetch_and_verify(_good(data), FILE_ID, tmp_path / "two")
