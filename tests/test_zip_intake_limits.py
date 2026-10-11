"""Zip intake, bomb limits (team-intake.md TI2; R39).

Each case is an archive that a hostile or careless uploader can really produce."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest
from zip_fixtures import (
    add_member,
    build_zip,
    make_store,
    video,
)

from autotester.schema.intake import IntakeOutcome, IntakeStatus, ZipLimits
from autotester.sources import zip_intake
from autotester.sources.bounded_write import CHUNK_SIZE
from autotester.sources.zip_intake import expand_zip
from autotester.store.project_store import ProjectStore

MIB = 1024 * 1024
CAP = MIB  # per-file cap injected small, standing in for the 2 GiB admin setting

def _run(store: ProjectStore, archive: Path, **kwargs):
    kwargs.setdefault("max_file_bytes", CAP)
    return expand_zip(store, archive, **kwargs)


def _rows(store: ProjectStore):
    return store.list_sources()


def _by_outcome(report, outcome: IntakeOutcome):
    return [m for m in report.members if m.outcome == outcome]


# ---- TI2 --------------------------------------------------------------------

def _no_copy(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a byte was written for an archive that must be refused first")

    monkeypatch.setattr(zip_intake, "copy_bounded", refuse)


@pytest.mark.parametrize(("limits", "named"), [
    (ZipLimits(max_entries=3), "entries"),
    (ZipLimits(max_videos=2), "video count"),
    (ZipLimits(max_total_bytes=10_000), "total uncompressed"),
    (ZipLimits(max_archive_bytes=100), "archive size"),
])
def test_ti2_archive_level_limit_refused_before_any_write_and_names_the_limit(
        tmp_path, monkeypatch, limits, named):
    """A zip with 5 entries (3 videos, 4 KiB each) that trips one archive-level cap."""
    store = make_store(tmp_path)
    members = [(f"v{i}.mp4", video(f"v{i}")) for i in range(3)] + [("a.pdf", b"x"), ("b.txt", b"y")]
    archive = build_zip(tmp_path / "in.zip", members)
    _no_copy(monkeypatch)
    report = _run(store, archive, limits=limits)
    assert report.status is IntakeStatus.FAILED and report.exit_code == 2
    assert named in report.members[0].reason
    assert _rows(store) == []


def test_ti2_declared_size_over_per_file_cap_refused_before_extraction(tmp_path, monkeypatch):
    """A member whose central directory already says it is bigger than the upload limit."""
    store = make_store(tmp_path)
    archive = build_zip(tmp_path / "in.zip", [("big.mp4", os.urandom(CAP + 1)),
                                              ("ok.mp4", video("ok"))])
    report = _run(store, archive)
    big = next(m for m in report.members if m.member == "big.mp4")
    assert big.outcome is IntakeOutcome.FAILED and "per-file limit" in big.reason
    assert [s.label for s in _rows(store)] == ["ok.mp4"]


def test_ti2_zero_bomb_over_ratio_refused_without_writing(tmp_path, monkeypatch):
    """A 4 MiB run of zeros deflates to a few KiB: far over a 20:1 ratio cap."""
    store = make_store(tmp_path)
    archive = tmp_path / "bomb.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        add_member(zf, "zeros.mp4", b"\0" * (4 * MIB), compress=zipfile.ZIP_DEFLATED)
    _no_copy(monkeypatch)
    report = _run(store, archive, max_file_bytes=64 * MIB, limits=ZipLimits(max_ratio=20))
    assert "ratio" in report.members[0].reason and report.exit_code == 2
    assert _rows(store) == []


class _LyingStream:
    """What a reader yields when the header says 10 bytes and the data says otherwise."""

    def __init__(self, total: int) -> None:
        self.remaining = total
        self.consumed = 0

    def read(self, size: int = -1) -> bytes:
        take = min(size if size > 0 else CHUNK_SIZE, self.remaining)
        self.remaining -= take
        self.consumed += take
        return b"\0" * take

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def close(self) -> None:
        return None


def _patch_open(monkeypatch, streams: dict[str, _LyingStream]) -> None:
    real_open = zipfile.ZipFile.open

    def fake(self, name, mode="r", pwd=None, *, force_zip64=False):
        key = getattr(name, "orig_filename", name)
        return streams[key] if key in streams else real_open(self, name, mode, pwd,
                                                             force_zip64=force_zip64)

    monkeypatch.setattr(zipfile.ZipFile, "open", fake)


def test_ti2_header_that_lies_is_stopped_at_cap_plus_one_chunk_and_removed(tmp_path, monkeypatch):
    """The central directory understates `liar.mp4`; the inflated stream is 10x the cap."""
    store = make_store(tmp_path)
    archive = build_zip(tmp_path / "in.zip", [("liar.mp4", video("liar", size=10)),
                                              ("ok.mp4", video("ok"))])
    liar = _LyingStream(10 * CAP)
    _patch_open(monkeypatch, {"liar.mp4": liar})
    report = _run(store, archive)
    assert liar.consumed <= CAP + CHUNK_SIZE
    failed = _by_outcome(report, IntakeOutcome.FAILED)
    assert len(failed) == 1 and "per-file limit" in failed[0].reason
    assert [s.label for s in _rows(store)] == ["ok.mp4"]
    assert not [p for p in tmp_path.rglob("*.mp4") if "liar" in p.name]
    assert not list((tmp_path / ".work" / "intake").glob("*/*"))


def test_ti2_total_cap_holds_while_streaming_across_members(tmp_path, monkeypatch):
    """Two members each pass the per-file cap but together blow the total cap."""
    store = make_store(tmp_path)
    archive = build_zip(tmp_path / "in.zip", [("a.mp4", video("a", size=10)),
                                              ("b.mp4", video("b", size=10))])
    first, second = _LyingStream(CAP), _LyingStream(10 * CAP)
    _patch_open(monkeypatch, {"a.mp4": first, "b.mp4": second})
    report = _run(store, archive, limits=ZipLimits(max_total_bytes=CAP + 100 * 1024))
    assert first.consumed + second.consumed <= CAP + 100 * 1024 + CHUNK_SIZE
    assert any("total uncompressed" in (m.reason or "") for m in report.members)


def test_ti2_nested_archive_by_name_and_by_signature_refused(tmp_path):
    """`inner.zip` is named as an archive; `sneaky.mp4` is a zip wearing a video suffix."""
    store = make_store(tmp_path)
    inner = build_zip(tmp_path / "inner.zip", [("deep.mp4", video("deep"))]).read_bytes()
    archive = build_zip(tmp_path / "in.zip", [("inner.zip", inner), ("sneaky.mp4", inner),
                                              ("ok.mp4", video("ok"))])
    report = _run(store, archive)
    nested = [m for m in report.members if "nested archive" in (m.reason or "")]
    assert {m.member for m in nested} == {"inner.zip", "sneaky.mp4"}
    assert all(m.outcome is IntakeOutcome.FAILED for m in nested)
    assert [s.label for s in _rows(store)] == ["ok.mp4"]


