"""mongo-store M51 / M24 (U5b fix cycles 1-2): a `Source` records the LOGICAL path, and every
reader of a stored medium goes through `local_blob`.

Real Drive and email registrations with the blobs area on `mongo`, then the cache directory is
wiped and the recorded path must still read back; file mode records the same path as before.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from blob_support import MongoRig
from test_media_sources_blobs import VIDEO, _commit, _store

from autotester.media import narration
from autotester.schema.base import Provenance
from autotester.schema.enums import SourceKind
from autotester.schema.project import Source
from autotester.sources import adapters
from autotester.sources.audio import TranscriptionOutcome
from autotester.sources.drive import DriveFile
from autotester.sources.drive_register import _dispatch_by_suffix, _write_bytes
from autotester.sources.email import Attachment
from autotester.sources.email_register import _register_email_attachment
from autotester.stages.source_material import resolve_teaching_material
from autotester.store import run_store
from autotester.store.project_store import ProjectStore

pytest_plugins = ["media_blob_support"]


def _wipe_cache(rig: MongoRig) -> None:
    shutil.rmtree(rig.cache, ignore_errors=True)


def _assert_logical_and_readable(rig: MongoRig, source: Source, body: bytes) -> None:
    """The recorded path is the LOGICAL path (not a cache copy) and survives a wiped cache (M51)."""
    assert source.path is not None and not Path(source.path).is_relative_to(rig.cache.resolve())
    assert "blob-cache" not in Path(source.path).parts and not Path(source.path).exists()
    _wipe_cache(rig)
    assert run_store.local_blob(Path(source.path)).read_bytes() == body


def test_a_registered_drive_source_records_the_logical_path_and_survives_a_cache_wipe(
        blob_area: MongoRig, tmp_path: Path) -> None:
    store = _store(tmp_path)
    prov = Provenance(produced_by="drive", inputs=["p"])
    for name, mime in (("notes.txt", "text/plain"), ("pic.png", "image/png"),
                       ("a.mp3", "audio/mpeg"), ("rec.webm", "video/webm"),
                       ("rec.mp4", "video/mp4"), ("rec.mov", "video/quicktime")):
        body = b"drive body " + name.encode()
        written = _write_bytes(store, "p", DriveFile("f1", name, mime), body)
        reg = _dispatch_by_suffix(store, written, DriveFile("f1", name, mime), prov, None, [])
        _assert_logical_and_readable(blob_area, reg.source, body)


def test_a_gridfs_only_audio_is_transcribed_from_a_readable_copy_and_records_the_logical_path(
        blob_area: MongoRig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store, seen = _store(tmp_path), []

    def fake(path: Path, source_id: str, **_: object) -> TranscriptionOutcome:
        seen.append(path.read_bytes())
        return TranscriptionOutcome(None, "stub")

    monkeypatch.setattr(adapters, "transcribe_audio", fake)
    drive_file = DriveFile("f1", "a.mp3", "audio/mpeg")
    written = _write_bytes(store, "p", drive_file, b"audio bytes")
    reg = _dispatch_by_suffix(store, written, drive_file, Provenance(produced_by="drive"), None, [])
    assert seen == [b"audio bytes"]
    _assert_logical_and_readable(blob_area, reg.source, b"audio bytes")


def test_a_registered_email_attachment_records_the_logical_path_and_survives_a_cache_wipe(
        blob_area: MongoRig, tmp_path: Path) -> None:
    store = _store(tmp_path)
    for name, mime in (("a b.txt", "text/plain"), ("pic.png", "image/png")):
        body = b"mail body " + name.encode()
        reg = _register_email_attachment(
            store, SimpleNamespace(id="m1"), Attachment(name, body, mime), None, [])
        _assert_logical_and_readable(blob_area, reg.source, body)


def test_two_folders_with_the_same_bytes_and_name_each_keep_their_own_logical_path(
        blob_area: MongoRig, tmp_path: Path) -> None:
    """W1: no process-global map; the path a register call returns is the one it was given."""
    store = _store(tmp_path)
    drive_file = DriveFile("f1", "n.txt", "text/plain")
    a = _write_bytes(store, "A", drive_file, b"same body")
    b = _write_bytes(store, "B", drive_file, b"same body")
    assert a.parent.parent.name == "A" and b.parent.parent.name == "B"
    assert run_store.local_blob(a).read_bytes() == run_store.local_blob(b).read_bytes()
    assert not hasattr(run_store, "_LOGICAL") and not hasattr(run_store, "source_path")


def test_drive_and_email_sources_in_file_mode_record_the_same_path_as_today(
        file_area: Path, tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", file_area)
    drive_file = DriveFile("f1", "notes.txt", "text/plain")
    written = _write_bytes(store, "p", drive_file, b"d")
    drive = _dispatch_by_suffix(store, written, drive_file, Provenance(produced_by="drive"),
                                None, [])
    mail = _register_email_attachment(
        store, SimpleNamespace(id="m1"), Attachment("x.txt", b"m", "text/plain"), None, [])
    assert drive.source.path == str(written.resolve())
    assert mail.source.path == str((store.paths.source_dir("m1") / "attachments"
                                    / "x.txt").resolve())


def test_teaching_material_of_a_gridfs_only_video_and_document_is_available(
        blob_area: MongoRig, tmp_path: Path) -> None:
    store = _store(tmp_path)
    video = _commit(store, tmp_path)
    body = b"the lesson text"
    target = store.paths.source_dir("d1") / "files" / "lesson.txt"
    run_store.store_media(target, body)
    doc = store.add_source(Source(project="pathlynks", kind=SourceKind.DOC, path=str(target),
                                  sha256=hashlib.sha256(body).hexdigest()))
    _wipe_cache(blob_area)
    for src in (video, doc):
        material = resolve_teaching_material(store, src, [src])
        assert not material.unavailable and not any(
            "unavailable" in p for p in material.problems), material.problems
    assert [u.text for u in resolve_teaching_material(store, doc, [doc]).units] == [
        "the lesson text"]


def test_narration_of_a_gridfs_only_video_transcribes_the_verified_copy(
        blob_area: MongoRig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(tmp_path)
    source = _commit(store, tmp_path)
    seen: list[bytes] = []

    def fake(video: Path, source_id: str, provider: object, secrets: object):
        seen.append(video.read_bytes())
        return narration._missing_narration(source_id, "stub")

    monkeypatch.setattr(narration, "_transcribe_video_audio", fake)
    narration.ensure_narration(store, source)
    assert seen == [VIDEO]
