"""Fixture for the media write-through tests: the blobs area on `mongo`, over the fake GridFS.

`AUTOTESTER_ROOT` is `<tmp>/root` (the data root), the `blobs` area is selected through the real
`AUTOTESTER_STORE_AREAS`, and the rig's `MongoBlobStore` is injected where `run_store.blob_store`
would otherwise build one from `AUTOTESTER_MONGO_URI`. State stays on files.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from blob_support import SECRET, MongoRig
from PIL import Image, ImageDraw

from autotester.core.redact import Redactor
from autotester.store import run_store


def png_bytes(tmp: Path, name: str = "shot.png") -> bytes:
    """A small real PNG with some content (not blank)."""
    path = tmp / name
    image = Image.new("RGB", (60, 40), "white")
    ImageDraw.Draw(image).rectangle((4, 4, 30, 20), fill="black")
    image.save(path)
    data = path.read_bytes()
    path.unlink()
    return data


@pytest.fixture
def blob_area(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[MongoRig]:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    monkeypatch.delenv("AUTOTESTER_STORE", raising=False)
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", "blobs=mongo")
    rig = MongoRig(tmp_path, redactor=lambda: Redactor({"TEST_PASSWORD": SECRET}))
    monkeypatch.setitem(run_store._BLOBS, "mongo", rig.blobs)
    yield rig


@pytest.fixture
def file_area(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("AUTOTESTER_ROOT", str(root))
    monkeypatch.delenv("AUTOTESTER_STORE", raising=False)
    monkeypatch.delenv("AUTOTESTER_STORE_AREAS", raising=False)
    monkeypatch.delitem(run_store._BLOBS, "mongo", raising=False)
    return root
