"""Drive intake end to end behind a fake Drive (team-intake.md TI7, TI9, TI11; hosting.md HO33).

`FakeDrive` stands in for `gws`: ids map to metadata and bytes, a download can lie about its size
or md5, and every `open` is recorded so a test can prove a file was NOT fetched. Nothing touches
the network. After each refusal the checks are the contract's: no source row, no recording file
in the project, no leftover staging.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from drive_fakes import FakeDownload, FakeDrive
from zip_fixtures import add_member, make_store, video

from autotester.core.paths import ENV_ROOT
from autotester.schema.intake import DriveOrigin, DriveRef, IntakeOutcome, ZipLimits
from autotester.schema.server_settings import ServerSettings
from autotester.sources.drive_errors import MESSAGES, DriveError, DriveFailure
from autotester.sources.drive_intake import intake_drive
from autotester.store.server_settings import save_server_settings

MIB = 1024 * 1024


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_ROOT, str(tmp_path))
    return make_store(tmp_path), FakeDrive(), tmp_path


def _leftovers(tmp_path: Path) -> list[Path]:
    """Anything left in the working areas an intake or a fetch uses."""
    found = []
    for area in ("intake", "drive-fetch", "gws"):
        base = tmp_path / ".work" / area
        found += [p for p in base.rglob("*") if p.is_file()] if base.exists() else []
    return found


def _run(store, drive, fid, kind="unknown", **kwargs):
    return intake_drive(store, DriveRef(id=fid, kind=kind), drive, **kwargs)


def test_ti7_a_verified_file_registers_under_the_projects_stable_path(env):
    """Good md5: one VIDEO source, path built from the source id, origin = the Drive id."""
    store, drive, tmp = env
    fid = drive.add("FILE000001", video("one"), name="Onboarding walk-through.mp4")
    report = _run(store, drive, fid, uploaded_by="dev@vidysea.test")
    assert report.exit_code == 0 and report.counts["registered"] == 1
    [source] = store.list_sources()
    assert Path(source.path) == store.paths.source_dir(source.id) / "recording.mp4"
    assert source.origin == DriveOrigin(file_id=fid)
    assert source.uploaded_by == "dev@vidysea.test" and source.uploaded_at is not None
    assert source.label == "Onboarding walk-through.mp4"
    assert _leftovers(tmp) == [] and all(d.closed for d in drive.downloads)


def test_ti4_a_hostile_drive_file_name_never_reaches_a_stored_path(env):
    store, drive, tmp = env
    long_name = "x" * 300 + ".mp4"
    for i, name in enumerate(["../../evil.mp4", "con.mp4", long_name, "a b..mp4"]):
        drive.add(f"HOSTILE{i:04d}", video(f"h{i}"), name=name)
        assert _run(store, drive, f"HOSTILE{i:04d}").exit_code == 0
    for source in store.list_sources():
        assert Path(source.path).name == "recording.mp4"
        assert store.paths.sources_dir in Path(source.path).parents
    assert not (tmp.parent / "evil.mp4").exists() and not (tmp / "evil.mp4").exists()


def test_ti7_a_wrong_md5_refuses_and_leaves_nothing(env):
    store, drive, tmp = env
    fid = drive.add("BADMD50001", video("m"))
    drive.lie[fid] = {"md5": "0" * 32}
    report = _run(store, drive, fid)
    assert report.exit_code == 2 and report.status.value == "failed"
    assert "md5" in report.members[0].reason
    assert store.list_sources() == [] and _leftovers(tmp) == []
    assert not list(store.paths.sources_dir.rglob("recording.*"))


def test_ti7_a_short_read_refuses_and_leaves_nothing(env):
    store, drive, tmp = env
    fid = drive.add("SHORTRD001", video("s", size=1000))
    drive.lie[fid] = {"size": 5000}
    report = _run(store, drive, fid)
    assert report.exit_code == 2 and "size mismatch" in report.members[0].reason
    assert store.list_sources() == [] and _leftovers(tmp) == []


def test_ti7_a_file_with_no_checksum_registers_but_says_it_was_not_verified(env):
    store, drive, _ = env
    fid = drive.add("NOCHKSUM01", video("n"), checksums=False)
    report = _run(store, drive, fid)
    assert report.exit_code == 0 and any("not verified" in n for n in report.notes)


def test_ti4_the_same_bytes_twice_is_a_duplicate(env):
    store, drive, _ = env
    a = drive.add("DUPFILE001", video("d"))
    b = drive.add("DUPFILE002", video("d"), name="copy.mp4")
    first, second = _run(store, drive, a), _run(store, drive, b)
    assert first.counts["registered"] == 1
    assert second.members[0].outcome is IntakeOutcome.DUPLICATE
    assert second.members[0].duplicate_of == first.members[0].source_id
    assert len(store.list_sources()) == 1


def test_ti7_a_folder_fetches_videos_and_lists_a_pdf_without_downloading_it(env):
    store, drive, tmp = env
    drive.add("VID0000001", video("v1"), name="a.mp4")
    drive.add("VID0000002", video("v2"), name="b.mov", mime="video/quicktime")
    drive.add("PDF0000001", b"%PDF-1.4", name="notes.pdf", mime="application/pdf")
    drive.folder("FOLDER0001", ["VID0000001", "PDF0000001", "VID0000002"])
    report = _run(store, drive, "FOLDER0001", kind="folder")
    assert report.counts == {"registered": 2, "duplicate": 0, "skipped": 1, "failed": 0}
    assert report.exit_code == 0
    skipped = next(m for m in report.members if m.outcome is IntakeOutcome.SKIPPED)
    assert skipped.member == "notes.pdf" and "not a recording" in skipped.reason
    assert "PDF0000001" not in drive.opened  # never downloaded
    assert len(store.list_sources()) == 2 and _leftovers(tmp) == []


def test_ti7_a_pasted_folder_id_without_a_hint_is_found_by_its_type(env):
    store, drive, _ = env
    drive.add("VID0000001", video("v1"))
    drive.folder("FOLDER0002", ["VID0000001"])
    assert _run(store, drive, "FOLDER0002").counts["registered"] == 1


def test_ti2_a_folder_with_too_many_videos_is_refused_before_any_download(env):
    store, drive, _ = env
    ids = []
    for i in range(3):
        ids.append(drive.add(f"MANYVID{i:04d}", video(f"m{i}")))
    drive.folder("FOLDER0003", ids)
    report = _run(store, drive, "FOLDER0003", limits=ZipLimits(max_videos=2))
    assert report.exit_code == 2 and "video count" in report.members[0].reason
    assert drive.opened == [] and store.list_sources() == []


def test_ti7_a_failing_video_in_a_folder_is_partial_and_the_rest_register(env):
    store, drive, _ = env
    drive.add("GOODVID001", video("g"))
    bad = drive.add("BADVID0001", video("b"))
    drive.lie[bad] = {"md5": "f" * 32}
    drive.folder("FOLDER0004", ["GOODVID001", bad])
    report = _run(store, drive, "FOLDER0004")
    assert report.status.value == "partial" and report.exit_code == 2
    assert report.counts["registered"] == 1 and report.counts["failed"] == 1


def test_ti7_a_zip_id_goes_through_the_zip_rules_after_the_fetch(env, tmp_path):
    """A Drive zip with a hostile member: that member is refused, the benign video registers."""
    store, drive, tmp = env
    archive = tmp_path / "bundle.zip"
    import zipfile
    with zipfile.ZipFile(archive, "w") as zf:
        add_member(zf, "../escape.mp4", video("x"))
        add_member(zf, "good.mp4", video("g"))
    sentinel = tmp_path.parent / "escape.mp4"
    fid = drive.add("ZIPFILE001", archive.read_bytes(), name="bundle.zip", mime="application/zip")
    report = _run(store, drive, fid, uploaded_by="dev@vidysea.test")
    assert report.status.value == "partial" and report.exit_code == 2
    refused = next(m for m in report.members if m.outcome is IntakeOutcome.FAILED)
    assert refused.member == "../escape.mp4" and "refused" in refused.reason
    [source] = store.list_sources()
    assert source.origin.kind == "zip" and source.origin.archive_name == "bundle.zip"
    assert source.uploaded_by == "dev@vidysea.test"
    assert not sentinel.exists() and _leftovers(tmp) == []


def test_ho33_a_file_that_is_not_a_video_or_zip_is_refused_without_a_download(env):
    store, drive, _ = env
    fid = drive.add("DOCFILE001", b"%PDF", name="notes.pdf", mime="application/pdf")
    report = _run(store, drive, fid)
    assert report.exit_code == 2 and "not a video" in report.members[0].reason
    assert drive.opened == []


def test_ti9_the_drive_path_obeys_the_admin_limit_and_a_change_applies_next_request(env):
    """5 MiB exactly succeeds, 5 MiB + 1 is refused; raising the setting lets the same bytes in."""
    store, drive, tmp = env
    save_server_settings(ServerSettings(max_upload_bytes=5 * MIB), tmp)
    exact = drive.add("EXACT00001", b"E" * (5 * MIB))
    over = drive.add("OVER000001", b"O" * (5 * MIB + 1))
    drive.lie[over] = {"size": None, "md5": None}  # no metadata: only streaming can catch it
    assert _run(store, drive, exact).exit_code == 0
    refused = _run(store, drive, over)
    assert refused.exit_code == 2 and "5 MiB" in refused.members[0].reason
    assert len(store.list_sources()) == 1 and _leftovers(tmp) == []
    save_server_settings(ServerSettings(max_upload_bytes=6 * MIB), tmp)
    assert _run(store, drive, over).exit_code == 0


def test_ti9_an_endless_drive_body_stops_at_the_limit_plus_one_chunk(env):
    store, drive, tmp = env
    save_server_settings(ServerSettings(max_upload_bytes=2 * MIB), tmp)
    drive.add("ENDLESS001", b"", checksums=False)
    read = {"n": 0}

    def endless():
        while True:
            read["n"] += 64 * 1024
            yield b"z" * 64 * 1024

    download = FakeDownload(b"", None, None)
    download.chunks = endless
    drive.open = lambda fid: download
    report = _run(store, drive, "ENDLESS001")
    assert report.exit_code == 2 and "2 MiB" in report.members[0].reason
    assert read["n"] <= 2 * MIB + 64 * 1024 and _leftovers(tmp) == []


@pytest.mark.parametrize("kind", list(DriveFailure))
def test_ti8_a_drive_failure_is_a_failed_row_with_its_fixed_message(env, kind):
    store, drive, tmp = env
    drive.add("ERRFILE001", video("e"))
    drive.error = DriveError(kind)
    report = _run(store, drive, "ERRFILE001")
    assert report.exit_code == 2 and report.members[0].reason == MESSAGES[kind]
    assert store.list_sources() == [] and _leftovers(tmp) == []


def test_ti3_a_name_with_no_video_suffix_uses_the_type_not_the_name(env):
    store, drive, _ = env
    fid = drive.add("NOSUFFIX01", video("q"), name="screen recording", mime="video/webm")
    assert _run(store, drive, fid).exit_code == 0
    assert store.list_sources()[0].path.endswith("recording.webm")
