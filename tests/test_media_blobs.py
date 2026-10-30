"""mongo-store M24 / M25: run media is written through to the blob store, read back via materialize.

Files stay on disk exactly as today; with the `blobs` area on `mongo` each screenshot, kept video,
leak shot and frame is ALSO put with sha256, kind, masked and content_type. Unmasked screenshots are
refused (M23); the result is saved only after its media is stored; readers survive a missing file.
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from blob_support import MongoRig
from media_blob_support import png_bytes
from test_browser_settle import session_with_fake_page
from test_screenshot_blank_retry import ShotPage

from autotester.schema.enums import EvidenceKind, Outcome
from autotester.schema.run import Evidence, RawResult
from autotester.stages import leak_evidence
from autotester.stages.report_export import png_base64
from autotester.store import run_store
from autotester.store.blobs import BlobRefused
from autotester.store.project_store import ProjectStore

pytest_plugins = ["media_blob_support"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _session(tmp_path: Path):
    session = session_with_fake_page(tmp_path / "root")
    session._page = ShotPage(["content"])
    return session


def _result(*evidence: Evidence) -> RawResult:
    return RawResult(case_id="c1", outcome=Outcome.COMPLETED, evidence=list(evidence))


def _run_dir(store: ProjectStore) -> Path:
    run_dir = store.paths.run_dir("r1")
    run_dir.mkdir(parents=True)
    return run_dir


def test_a_screenshot_is_kept_on_disk_and_put_masked_in_the_blob_store(
        blob_area: MongoRig, tmp_path: Path) -> None:
    ev = _session(tmp_path).screenshot("step01-login", step_order=1)
    local = tmp_path / "root" / "run" / ev.path
    info = blob_area.blobs.stat(f"run/{ev.path}")
    assert local.is_file() and info is not None
    assert (info.kind, info.masked, info.content_type) == ("screenshot", True, "image/png")
    assert info.sha256 == _sha(local.read_bytes()) and info.size == local.stat().st_size


def test_with_the_area_on_file_a_screenshot_is_the_same_file_and_no_blob_is_put(
        file_area: Path, tmp_path: Path) -> None:
    ev = _session(tmp_path).screenshot("step01-login", step_order=1)
    assert (file_area / "run" / ev.path).is_file()
    assert run_store.blob_store() is None and "mongo" not in run_store._BLOBS


def test_an_unmasked_screenshot_is_refused_and_nothing_is_stored(
        blob_area: MongoRig, tmp_path: Path) -> None:
    shot = tmp_path / "root" / "run" / "x.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(png_bytes(tmp_path))
    with pytest.raises(BlobRefused):
        run_store.put_file(shot, kind="screenshot", masked=False)
    assert blob_area.files == []


def test_a_masked_leak_shot_is_put_masked_through_write_blob_file(
        blob_area: MongoRig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    masked = png_bytes(tmp_path, "m.png")

    @contextmanager
    def fake(paths: list[Path]):
        out = paths[0].with_name("masked.png")
        out.write_bytes(masked)
        yield SimpleNamespace(incomplete=False, paths=[out], reasons=[])

    monkeypatch.setattr(leak_evidence, "sanitized_images", fake)
    dest = tmp_path / "root" / "run" / "leak" / "f1.png"
    assert leak_evidence.store_masked_screenshot(b"RAW", dest) == (dest, None)
    info = blob_area.blobs.stat("run/leak/f1.png")
    assert info is not None and info.masked and info.kind == "screenshot"
    assert dest.read_bytes() == masked and blob_area.blobs.get("run/leak/f1.png") == masked


def test_save_result_puts_the_screenshot_and_the_kept_video_before_the_result(
        blob_area: MongoRig, tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path / "root")
    run_dir = _run_dir(store)
    (run_dir / "01-a.png").write_bytes(png_bytes(tmp_path))
    (run_dir / "c1.webm").write_bytes(b"\x1aE\xdf\xa3 webm bytes \xff")
    store.save_result("r1", _result(
        Evidence(kind=EvidenceKind.SCREENSHOT, path="01-a.png", masked=True),
        Evidence(kind=EvidenceKind.VIDEO, path="c1.webm", masked=True)))
    key = "projects/pathlynks/runs/r1/"
    shot, video = blob_area.blobs.stat(key + "01-a.png"), blob_area.blobs.stat(key + "c1.webm")
    assert shot is not None and shot.kind == "screenshot" and shot.content_type == "image/png"
    assert video is not None and video.kind == "video" and video.content_type == "video/webm"
    assert (run_dir / "c1.json").is_file()


def test_a_refused_screenshot_means_the_result_is_not_saved(
        blob_area: MongoRig, tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", tmp_path / "root")
    run_dir = _run_dir(store)
    (run_dir / "01-a.png").write_bytes(png_bytes(tmp_path))
    with pytest.raises(BlobRefused):
        store.save_result("r1", _result(
            Evidence(kind=EvidenceKind.SCREENSHOT, path="01-a.png", masked=False)))
    assert not (run_dir / "c1.json").exists() and blob_area.files == []


def test_save_result_in_file_mode_puts_nothing(file_area: Path, tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", file_area)
    run_dir = _run_dir(store)
    (run_dir / "01-a.png").write_bytes(png_bytes(tmp_path))
    result = _result(Evidence(kind=EvidenceKind.SCREENSHOT, path="01-a.png", masked=True))
    store.save_result("r1", result)
    assert (run_dir / "c1.json").is_file()
    assert run_store.sync_run_blobs(run_dir, result) == 0


def test_a_screenshot_whose_local_file_is_gone_is_still_embedded_from_the_blob_store(
        blob_area: MongoRig, tmp_path: Path) -> None:
    root = tmp_path / "root"
    shot = root / "projects" / "pathlynks" / "runs" / "r1" / "01-a.png"
    shot.parent.mkdir(parents=True)
    data = png_bytes(tmp_path)
    shot.write_bytes(data)
    run_store.put_file(shot, kind="screenshot", masked=True)
    shot.unlink()
    served = run_store.local_blob(shot)
    assert served != shot and served.read_bytes() == data
    assert png_base64(shot, shot.parent, root) is not None


def test_local_blob_is_the_path_itself_while_the_file_exists_and_when_nothing_is_stored(
        blob_area: MongoRig, tmp_path: Path) -> None:
    here = tmp_path / "root" / "run" / "a.png"
    here.parent.mkdir(parents=True)
    here.write_bytes(b"x")
    run_store.put_file(here, kind="console", masked=True)  # stored AND on disk: the file wins
    assert run_store.local_blob(here) == here
    gone = tmp_path / "root" / "run" / "never.png"
    assert run_store.local_blob(gone) == gone
    assert run_store.local_blob(tmp_path / "outside.png") == tmp_path / "outside.png"
