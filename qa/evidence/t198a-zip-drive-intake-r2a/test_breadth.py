# ruff: noqa
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from attack_cases import healthy
from zip_fixtures import make_store

from autotester.sources import zip_intake
from autotester.sources.zip_names import UnsafePath


def _arc(tmp_path):
    p = tmp_path / "h.zip"
    p.write_bytes(healthy((0, 8)))
    return p


@pytest.mark.parametrize("exc", [KeyboardInterrupt(), SystemExit(3), MemoryError()])
def test_read_time_baseexceptions_propagate(tmp_path, monkeypatch, exc):
    real = zipfile.ZipExtFile.read

    def read(self, n=-1):
        if self.name.endswith("m0.mp4"):
            raise exc
        return real(self, n)

    monkeypatch.setattr(zipfile.ZipExtFile, "read", read)
    with pytest.raises(type(exc)):
        zip_intake.expand_zip(make_store(tmp_path), _arc(tmp_path))


@pytest.mark.parametrize("exc", [KeyboardInterrupt(), SystemExit(3), MemoryError()])
def test_constructor_baseexceptions_propagate(tmp_path, monkeypatch, exc):
    def boom(*a, **k):
        raise exc

    monkeypatch.setattr(zipfile, "ZipFile", boom)
    with pytest.raises(type(exc)):
        zip_intake.expand_zip(make_store(tmp_path), _arc(tmp_path))


def test_bug_in_our_commit_code_is_not_swallowed(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("our bug")

    monkeypatch.setattr(zip_intake, "commit_video", boom)
    with pytest.raises(RuntimeError, match="our bug"):
        zip_intake.expand_zip(make_store(tmp_path), _arc(tmp_path))


def test_bug_in_our_hash_or_copy_code_is_not_swallowed(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise ValueError("our copy bug")

    monkeypatch.setattr(zip_intake, "copy_bounded", boom)
    with pytest.raises(ValueError, match="our copy bug"):
        zip_intake.expand_zip(make_store(tmp_path), _arc(tmp_path))


def test_containment_refusal_still_raises(tmp_path, monkeypatch):
    def refuse(path, root):
        raise UnsafePath("destination escapes its directory")

    monkeypatch.setattr(zip_intake, "ensure_inside", refuse)
    with pytest.raises(UnsafePath):
        zip_intake.expand_zip(make_store(tmp_path), _arc(tmp_path))


def test_classify_bug_is_not_swallowed(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("classify bug")

    monkeypatch.setattr(zip_intake, "_classify", boom)
    with pytest.raises(RuntimeError, match="classify bug"):
        zip_intake.expand_zip(make_store(tmp_path), _arc(tmp_path))
