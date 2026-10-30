"""mongo-store M51 / M24: source-media bytes go to the blob store; readers go through materialize.

With the `blobs` area on `mongo` a video commit, a drive register and an email attachment leave the
bytes in GridFS and NO file under the data root; the `Source` reference stays readable through
`local_blob` / `materialize`. With the area on `file` each writer is as before. A fresh interpreter
with the default selection never imports a database driver.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from blob_support import MongoRig, tree
from media_blob_support import png_bytes

from autotester.core.paths import code_root
from autotester.media import frames as frame_mod
from autotester.schema.intake import UploadOrigin
from autotester.schema.project import Source
from autotester.sources.drive import DriveFile
from autotester.sources.drive_register import _write_bytes
from autotester.sources.email import Attachment
from autotester.sources.email_register import _write_attachment_to_disk
from autotester.sources.intake_commit import commit_video
from autotester.stages import media_prep
from autotester.store import run_store
from autotester.store.project_store import ProjectStore
from autotester.ui.routes_video import _safe_video_path

pytest_plugins = ["media_blob_support"]
VIDEO = b"\x1aE\xdf\xa3 a recording \xff\xfe" * 40


def _media_files(tmp_path: Path) -> list[str]:
    """Every file under the data root's projects except the state index (sources.jsonl)."""
    return [p for p in tree(tmp_path / "root" / "projects") if not p.endswith(".jsonl")]


def _store(tmp_path: Path) -> ProjectStore:
    return ProjectStore("pathlynks", tmp_path / "root")


def _commit(store: ProjectStore, tmp_path: Path, data: bytes = VIDEO) -> Source:
    staged = tmp_path / "staged.webm"
    staged.write_bytes(data)
    source, created = commit_video(
        store, staged, digest=hashlib.sha256(data).hexdigest(), suffix=".webm", label="demo",
        origin=UploadOrigin(file_name="demo.webm"), uploaded_by="umesh")
    assert created
    return source


def test_a_committed_video_lives_only_in_gridfs_and_reads_back_through_materialize(
        blob_area: MongoRig, tmp_path: Path) -> None:
    store = _store(tmp_path)
    source = _commit(store, tmp_path)
    assert source.path is not None and not Path(source.path).exists()
    assert _media_files(tmp_path) == []
    key = Path(source.path).resolve().relative_to((tmp_path / "root").resolve()).as_posix()
    assert blob_area.count(key) == 1 and blob_area.blobs.stat(key).kind == "source"
    served = run_store.local_blob(Path(source.path))
    assert served.read_bytes() == VIDEO and served.is_relative_to(blob_area.cache)
    assert store.list_sources()[0].path == source.path


def test_a_committed_video_in_file_mode_is_the_same_file_as_today(
        file_area: Path, tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", file_area)
    staged_before = tmp_path / "staged.webm"
    source = _commit(store, tmp_path)
    assert Path(source.path).read_bytes() == VIDEO and not staged_before.exists()
    assert Path(source.path).name == "recording.webm" and "mongo" not in run_store._BLOBS


def test_a_recording_whose_bytes_do_not_match_its_digest_is_not_stored(
        blob_area: MongoRig, tmp_path: Path) -> None:
    staged = tmp_path / "staged.webm"
    staged.write_bytes(VIDEO)
    target = _store(tmp_path).paths.source_dir("s1") / "recording.webm"
    with pytest.raises(ValueError, match="sha256"):
        run_store.place_media(staged, target, hashlib.sha256(b"other").hexdigest())
    assert blob_area.files == [] and staged.is_file()


def test_a_drive_file_is_put_in_gridfs_not_on_disk_and_a_clash_is_kept_apart(
        blob_area: MongoRig, tmp_path: Path) -> None:
    store = _store(tmp_path)
    drive_file = DriveFile("f1", "notes.txt", "text/plain")
    first = _write_bytes(store, "src1", drive_file, b"first body")
    second = _write_bytes(store, "src1", drive_file, b"second body")
    assert first.read_bytes() == b"first body" and second.read_bytes() == b"second body"
    assert first != second and second.name.endswith("_notes.txt")
    assert _media_files(tmp_path) == []
    assert len(blob_area.files) == 2
    assert _write_bytes(store, "src1", drive_file, b"first body") == first  # same bytes: same path


def test_an_email_attachment_is_put_in_gridfs_not_on_disk(
        blob_area: MongoRig, tmp_path: Path) -> None:
    store = _store(tmp_path)
    path = _write_attachment_to_disk(store, "m1", Attachment("a b.txt", b"hello", "text/plain"))
    assert path.name == "a_b.txt" and path.read_bytes() == b"hello"
    assert _media_files(tmp_path) == [] and len(blob_area.files) == 1


def test_drive_and_email_writers_in_file_mode_write_the_file_as_before(
        file_area: Path, tmp_path: Path) -> None:
    store = ProjectStore("pathlynks", file_area)
    drive = _write_bytes(store, "src1", DriveFile("f1", "notes.txt", "text/plain"), b"d")
    mail = _write_attachment_to_disk(store, "m1", Attachment("a b.txt", b"m", "text/plain"))
    assert drive == store.paths.source_dir("src1") / "files" / "notes.txt"
    assert mail == store.paths.source_dir("m1") / "attachments" / "a_b.txt"
    assert (drive.read_bytes(), mail.read_bytes()) == (b"d", b"m")


def test_a_secret_value_in_an_ingested_text_is_refused_and_nothing_is_stored(
        blob_area: MongoRig, tmp_path: Path) -> None:
    from blob_support import SECRET

    from autotester.store.blobs import BlobRefused

    with pytest.raises(BlobRefused):
        _write_bytes(_store(tmp_path), "src1", DriveFile("f1", "n.txt", "text/plain"),
                     f"password={SECRET}".encode())
    assert blob_area.files == []


def test_frames_of_a_gridfs_only_video_are_extracted_and_put_as_unmasked_frames(
        blob_area: MongoRig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(tmp_path)
    source = _commit(store, tmp_path)
    seen: list[Path] = []

    def fake_extract(video: Path, t_s: float, out_png: Path) -> bool:
        seen.append(video)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        out_png.write_bytes(png_bytes(tmp_path))
        return True

    monkeypatch.setattr(frame_mod, "extract_frame", fake_extract)
    analysis = SimpleNamespace(screens=[SimpleNamespace(screenshot_ts=[1.0, 2.5])])
    frames = media_prep.extract_frames(store, source, analysis)
    assert len(frames) == 2 and seen[0].read_bytes() == VIDEO
    info = blob_area.blobs.stat(frames[0].resolve().relative_to(
        (tmp_path / "root").resolve()).as_posix())
    assert info is not None and (info.kind, info.masked) == ("frame", False)


def test_a_run_video_with_no_local_file_is_served_from_the_blob_store(
        blob_area: MongoRig, tmp_path: Path) -> None:
    run_dir = tmp_path / "root" / "projects" / "pathlynks" / "runs" / "r1"
    run_dir.mkdir(parents=True)
    video = run_dir / "c1.webm"
    video.write_bytes(VIDEO)
    run_store.put_file(video, kind="video", masked=True)
    video.unlink()
    served = _safe_video_path(run_dir, "c1.webm")
    assert served is not None and served.read_bytes() == VIDEO
    assert _safe_video_path(run_dir, "never.webm") is None
    assert _safe_video_path(run_dir, "../c1.webm") is None


def test_a_default_selection_run_never_imports_a_database_driver(tmp_path: Path) -> None:
    script = (
        "import sys\n"
        "from pathlib import Path\n"
        "from autotester.store import run_store\n"
        "from autotester.store.project_store import ProjectStore\n"
        "root = Path(sys.argv[1])\n"
        "store = ProjectStore('pathlynks', root)\n"
        "shot = store.paths.run_dir('r1') / 'a.png'\n"
        "shot.parent.mkdir(parents=True)\n"
        "shot.write_bytes(b'png')\n"
        "assert run_store.put_file(shot, kind='screenshot', masked=True) is None\n"
        "assert run_store.local_blob(shot) == shot\n"
        "target = store.paths.source_dir('s1') / 'recording.webm'\n"
        "staged = root / 'staged.webm'\n"
        "staged.write_bytes(b'v')\n"
        "import hashlib\n"
        "run_store.place_media(staged, target, hashlib.sha256(b'v').hexdigest())\n"
        "assert target.read_bytes() == b'v'\n"
        "assert run_store.store_media(root / 'x' / 'y.txt', b'z').read_bytes() == b'z'\n"
        "drivers = {'pymongo', 'gridfs', 'bson'}\n"
        "print(sorted(m for m in sys.modules if m.split('.')[0] in drivers))\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("AUTOTESTER_STORE")}
    env.update(PYTHONPATH=str(code_root() / "src"), AUTOTESTER_ROOT=str(tmp_path))
    done = subprocess.run([sys.executable, "-c", script, str(tmp_path)], env=env,
                          capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stderr[-1500:]
    assert done.stdout.strip().splitlines()[-1] == "[]"
