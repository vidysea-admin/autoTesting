"""Zip intake, registration and the outcome table (team-intake.md TI3-TI5; R39)."""

from __future__ import annotations

import hashlib
import random
import zipfile
from pathlib import Path

import pytest
from zip_fixtures import (
    add_member,
    bad_utf8_name,
    build_zip,
    flip_data_byte,
    make_store,
    mark_encrypted,
    video,
)

from autotester.core.redact import Redactor
from autotester.schema.intake import IntakeOutcome, IntakeStatus
from autotester.sources import zip_intake
from autotester.sources.zip_intake import expand_zip
from autotester.stages import ingest
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


# ---- TI3 --------------------------------------------------------------------

def test_ti3_three_videos_one_pdf_one_text_register_three_and_skip_two(tmp_path):
    """The standard hand-off: a folder of recordings plus a spec PDF and a readme."""
    store = make_store(tmp_path)
    members = [("one.mp4", video("1")), ("two.mkv", video("2")), ("sub/three.webm", video("3")),
               ("spec.pdf", b"%PDF"), ("readme.txt", b"hello")]
    report = _run(store, build_zip(tmp_path / "in.zip", members))
    assert len(_by_outcome(report, IntakeOutcome.REGISTERED)) == 3
    skipped = _by_outcome(report, IntakeOutcome.SKIPPED)
    assert {m.member for m in skipped} == {"spec.pdf", "readme.txt"}
    assert all(m.reason for m in skipped)
    assert report.status is IntakeStatus.OK and report.exit_code == 0
    assert len(_rows(store)) == 3 and all(s.kind.value == "video" for s in _rows(store))


def test_ti3_dotfile_scripts_no_suffix_and_directories_are_never_kept(tmp_path):
    """A zip with `.env`, a PowerShell script, a bare name and folder entries."""
    store = make_store(tmp_path)
    members = [(".env", b"SECRET=1"), ("run.ps1", b"x"), ("a.exe", b"x"), ("b.bat", b"x"),
               ("c.sh", b"x"), ("d.js", b"x"), ("noext", b"x"), ("docs/", b""),
               ("ok.mp4", video("ok"))]
    report = _run(store, build_zip(tmp_path / "in.zip", members))
    skipped = {m.member for m in _by_outcome(report, IntakeOutcome.SKIPPED)}
    assert skipped == {".env", "run.ps1", "a.exe", "b.bat", "c.sh", "d.js", "noext"}
    assert "docs/" not in {m.member for m in report.members}
    kept = [p.name for p in tmp_path.rglob("*") if p.is_file()]
    assert not any(n in kept for n in (".env", "run.ps1", "a.exe", "noext"))


def test_ti3_allowlist_is_the_ingest_definition_not_a_second_list(tmp_path, monkeypatch):
    """Adding a suffix to `ingest.RECORDING_SUFFIXES` must change zip intake too."""
    store = make_store(tmp_path)
    monkeypatch.setattr(ingest, "RECORDING_SUFFIXES", ingest.RECORDING_SUFFIXES | {".xyz"})
    report = _run(store, build_zip(tmp_path / "in.zip", [("clip.xyz", video("x"))]))
    assert len(_by_outcome(report, IntakeOutcome.REGISTERED)) == 1
    source = Path(zip_intake.__file__).read_text(encoding="utf-8")
    assert '".mp4"' not in source and "'.mp4'" not in source


# ---- TI4 --------------------------------------------------------------------

def test_ti4_same_bytes_twice_in_one_zip_and_again_in_a_second_zip_are_duplicates(tmp_path):
    """A tester re-uploads a recording that is already in the project."""
    store = make_store(tmp_path)
    same = video("same")
    first = _run(store, build_zip(tmp_path / "a.zip", [("x/one.mp4", same), ("y/two.mp4", same)]))
    registered = _by_outcome(first, IntakeOutcome.REGISTERED)[0]
    dup = _by_outcome(first, IntakeOutcome.DUPLICATE)[0]
    assert dup.duplicate_of == registered.source_id
    second = _run(store, build_zip(tmp_path / "b.zip", [("z.mp4", same)]))
    assert _by_outcome(second, IntakeOutcome.DUPLICATE)[0].duplicate_of == registered.source_id
    assert len(_rows(store)) == 1


def test_ti4_two_members_with_one_basename_get_distinct_stored_files(tmp_path):
    """`a/clip.mp4` and `b/clip.mp4` are different recordings from two folders."""
    store = make_store(tmp_path)
    report = _run(store, build_zip(tmp_path / "in.zip", [("a/clip.mp4", video("A")),
                                                         ("b/clip.mp4", video("B"))]))
    rows = _rows(store)
    assert len(rows) == 2 and len({r.path for r in rows}) == 2
    assert {Path(r.path).read_bytes() for r in rows} == {video("A"), video("B")}
    assert report.status is IntakeStatus.OK


@pytest.mark.parametrize("name", ["x" * 296 + ".mp4", "con.mp4.", "my clip (final).mp4 ",
                                  "ünï/cödé.mp4", "trail.dots...mp4"])
def test_ti4_stored_path_never_contains_text_from_the_member_name(tmp_path, name):
    """Long, spaced, unicode and dotted names must not influence where bytes land."""
    store = make_store(tmp_path)
    _run(store, build_zip(tmp_path / "in.zip", [(name, video(name[:8]))]))
    for row in _rows(store):
        stored = Path(row.path)
        assert stored.parent == store.paths.source_dir(row.id)
        assert stored.name == "recording.mp4"
        assert stored.read_bytes() == video(name[:8])


def test_ti4_label_and_origin_pass_the_scrubber_before_storage(tmp_path):
    """A credential pasted into a file name must not reach sources.jsonl or the report."""
    store = make_store(tmp_path)
    scrub = Redactor({"TOKEN": "sk-CANARY-123"}).scrub
    report = _run(store, build_zip(tmp_path / "in.zip",
                                   [("sk-CANARY-123/clip.mp4", video("c"))]), scrub=scrub)
    assert "sk-CANARY-123" not in store.paths.sources_index.read_text(encoding="utf-8")
    assert "sk-CANARY-123" not in report.model_dump_json()


# ---- TI5 --------------------------------------------------------------------

def test_ti5_corrupt_middle_member_is_failed_others_register_status_partial_exit_2(tmp_path):
    """A download that lost a byte in the middle video of three."""
    store = make_store(tmp_path)
    archive = build_zip(tmp_path / "in.zip", [("a.mp4", video("a")), ("b.mp4", video("b")),
                                              ("c.mp4", video("c"))])
    flip_data_byte(archive, "b.mp4")
    report = _run(store, archive)
    failed = _by_outcome(report, IntakeOutcome.FAILED)
    assert [m.member for m in failed] == ["b.mp4"] and failed[0].reason
    assert {s.label for s in _rows(store)} == {"a.mp4", "c.mp4"}
    assert report.status is IntakeStatus.PARTIAL and report.exit_code == 2
    assert not list((tmp_path / ".work" / "intake").glob("*/*"))


def _noise(tag: str, size: int = 6000) -> bytes:
    """Bytes that barely compress (so a flipped byte lands inside real compressed data)."""
    out, n = b"", 0
    while len(out) < size:
        out += hashlib.sha256(f"{tag}{n}".encode()).digest()
        n += 1
    return out[:size]


@pytest.mark.parametrize("method", [zipfile.ZIP_LZMA, zipfile.ZIP_BZIP2, zipfile.ZIP_DEFLATED])
@pytest.mark.parametrize("fraction", [0.2, 0.5, 0.8])
def test_ti5_a_damaged_compressed_member_is_failed_whatever_the_decompressor_raises(
        tmp_path, method, fraction):
    """LZMA raises LZMAError, bzip2 OSError, deflate zlib.error: each is one failed member."""
    store = make_store(tmp_path)
    archive = tmp_path / "in.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for tag in ("a", "b", "c"):
            add_member(zf, f"{tag}.mp4", _noise(tag), compress=method)
    with zipfile.ZipFile(archive) as zf:
        info = zf.getinfo("b.mp4")
        offset = info.header_offset + 30 + len(info.orig_filename.encode()) + len(info.extra)
        offset += int(info.compress_size * fraction)
    raw = bytearray(archive.read_bytes())
    raw[offset] ^= 0xFF
    archive.write_bytes(bytes(raw))
    report = _run(store, archive)
    assert [m.member for m in _by_outcome(report, IntakeOutcome.FAILED)] == ["b.mp4"]
    assert {s.label for s in _rows(store)} == {"a.mp4", "c.mp4"}
    assert report.status is IntakeStatus.PARTIAL and report.exit_code == 2
    assert not list((tmp_path / ".work" / "intake").glob("*/*"))


def test_ti5_a_zip_version_python_cannot_read_is_a_failed_report_not_a_crash(tmp_path):
    """extract_version 9.9: the stdlib refuses to list it; the intake must not crash."""
    store = make_store(tmp_path)
    archive = tmp_path / "in.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        add_member(zf, "a.mp4", video("a"))
        info = zipfile.ZipInfo("b.mp4")
        info.extract_version = 99
        zf.writestr(info, video("b"))
    report = _run(store, archive)
    assert report.status is IntakeStatus.FAILED and report.exit_code == 2
    assert "version" in report.members[0].reason and _rows(store) == []


def test_ti5_utf8_flag_with_an_invalid_utf8_name_is_a_failed_report_not_a_crash(tmp_path):
    """The checker's case: the stdlib raises UnicodeDecodeError while listing the archive."""
    store = make_store(tmp_path)
    archive = build_zip(tmp_path / "in.zip", [("zz.mp4", video("a")), ("ok.mp4", video("b"))])
    bad_utf8_name(archive, b"zz.mp4", b"\xffz.mp4")
    with pytest.raises(UnicodeDecodeError):
        zipfile.ZipFile(archive)  # the premise: the stdlib really does raise on this archive
    report = _run(store, archive)
    assert report.status is IntakeStatus.FAILED and report.exit_code == 2
    assert len(report.members) == 1 and report.members[0].outcome is IntakeOutcome.FAILED
    assert _rows(store) == [] and not list((tmp_path / ".work" / "intake").glob("*/*"))


def test_ti5_no_mutation_of_a_healthy_zip_makes_expand_zip_raise(tmp_path):
    """Seeded fuzz of a mixed-method archive (40 mutants; each costs ~0.3 s of file I/O here)."""
    healthy = tmp_path / "healthy.zip"
    with zipfile.ZipFile(healthy, "w") as zf:
        for i, method in enumerate((zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_LZMA,
                                    zipfile.ZIP_BZIP2)):
            add_member(zf, f"d{i}/m{i}.mp4", _noise(f"m{i}", 3000), compress=method)
        add_member(zf, "notes.txt", b"hello")
    flagged = tmp_path / "flagged.zip"  # same archive with the UTF-8 flag on every header
    flagged.write_bytes(healthy.read_bytes())
    bad_utf8_name(flagged, b"", b"")
    originals = (healthy.read_bytes(), flagged.read_bytes())
    rng = random.Random(198)
    for i in range(40):
        raw = bytearray(originals[i % 2])
        for _ in range(rng.randint(1, 4)):
            at = rng.randrange(len(raw))
            if rng.random() < 0.3:
                raw[at:at + rng.randint(2, 12)] = rng.randbytes(rng.randint(0, 12))
            else:
                raw[at] ^= rng.randint(1, 255)
        if rng.random() < 0.15:
            del raw[rng.randrange(len(raw)):]
        mutant = tmp_path / f"mut{i}.zip"
        mutant.write_bytes(bytes(raw))
        store = make_store(tmp_path / f"s{i}")
        report = _run(store, mutant)  # must return a report, never raise
        assert report.status in set(IntakeStatus)
        assert not list((tmp_path / f"s{i}" / ".work" / "intake").glob("*/*"))
        for row in _rows(store):
            assert Path(row.path).is_file()


def test_ti5_password_protected_member_is_failed_not_success(tmp_path):
    """A zip whose members are encrypted (flag bit 0)."""
    store = make_store(tmp_path)
    archive = build_zip(tmp_path / "in.zip", [("a.mp4", video("a"))])
    mark_encrypted(archive)
    report = _run(store, archive)
    assert report.status is IntakeStatus.FAILED and report.exit_code == 2
    assert "encrypted" in report.members[0].reason and _rows(store) == []


def test_ti5_a_renamed_text_file_is_one_failure_and_registers_nothing(tmp_path):
    """Someone renames notes.txt to notes.zip and uploads it."""
    store = make_store(tmp_path)
    fake = tmp_path / "notes.zip"
    fake.write_text("just some notes", encoding="utf-8")
    report = _run(store, fake)
    assert report.status is IntakeStatus.FAILED and report.exit_code == 2
    assert len(report.members) == 1 and report.members[0].outcome is IntakeOutcome.FAILED
    assert "not a zip" in report.members[0].reason and _rows(store) == []


