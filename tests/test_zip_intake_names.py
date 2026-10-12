"""Zip intake, member names and containment (team-intake.md TI1; R39, R65).

Each case is a hostile or benign zip a team member uploads on the Add-videos page."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from zip_fixtures import (
    SPECIAL_MODES,
    build_special,
    build_zip,
    files_outside_project_sources,
    make_store,
    plant_sentinels,
    video,
)

from autotester.schema.intake import IntakeOutcome, IntakeStatus
from autotester.sources.zip_intake import expand_zip
from autotester.sources.zip_names import UnsafePath, ensure_inside, vet_member_name
from autotester.store.project_store import ProjectStore

MIB = 1024 * 1024
CAP = MIB  # per-file cap injected small, standing in for the 2 GiB admin setting

HOSTILE = [  # (member name exactly as stored in the zip, reason keyword)
    ("../x.mp4", "traversal"),
    ("..\\x.mp4", "traversal"),
    ("a/../../x.mp4", "traversal"),
    ("a\\..\\..\\x.mp4", "traversal"),
    ("/abs.mp4", "absolute"),
    ("\\abs.mp4", "absolute"),
    ("C:\\x.mp4", "drive letter"),
    ("C:x.mp4", "drive letter"),
    ("\\\\host\\share\\x.mp4", "UNC"),
    ("a.mp4:evil", "alternate data stream"),
    ("CON", "reserved device name"),
    ("nul.mp4", "reserved device name"),
    ("AUX.txt", "reserved device name"),
    ("COM1", "reserved device name"),
    ("sub/LPT1.mp4", "reserved device name"),
    ("a\x00b.mp4", "control character"),
    ("a\u202eb.mp4", "control character"),
    ("a\x07b.mp4", "control character"),
]


def _run(store: ProjectStore, archive: Path, **kwargs):
    kwargs.setdefault("max_file_bytes", CAP)
    return expand_zip(store, archive, **kwargs)


def _rows(store: ProjectStore):
    return store.list_sources()


def _by_outcome(report, outcome: IntakeOutcome):
    return [m for m in report.members if m.outcome == outcome]


# ---- TI1 --------------------------------------------------------------------

@pytest.mark.parametrize(("name", "keyword"), HOSTILE)
def test_ti1_hostile_member_refused_by_name_never_written_benign_still_registered(
        tmp_path, name, keyword):
    """A tester uploads a zip carrying one hostile entry beside a real recording."""
    store = make_store(tmp_path)
    sentinels = plant_sentinels(tmp_path, store)
    archive = build_zip(tmp_path / "in.zip", [(name, b"evil"), ("ok.mp4", video("ok"))])
    before = files_outside_project_sources(tmp_path, store)

    report = _run(store, archive)

    assert vet_member_name(name) is not None and keyword in vet_member_name(name)
    refused = _by_outcome(report, IntakeOutcome.FAILED)
    assert len(refused) == 1 and "refused" in refused[0].reason
    assert keyword in refused[0].reason
    assert len(_by_outcome(report, IntakeOutcome.REGISTERED)) == 1
    assert report.status is IntakeStatus.PARTIAL
    for spot, content in sentinels.items():
        assert spot.read_bytes() == content
    assert files_outside_project_sources(tmp_path, store) == before
    assert len([p for p in store.paths.sources_dir.rglob("*") if p.is_file()]) == 1


@pytest.mark.parametrize("kind", sorted(SPECIAL_MODES))
def test_ti1_symlink_device_fifo_socket_entries_refused(tmp_path, kind):
    """A Unix-made zip carries a symlink (or device) entry pointing outside the tree."""
    store = make_store(tmp_path)
    archive = build_special(tmp_path / "in.zip", "link.mp4", SPECIAL_MODES[kind])
    report = _run(store, archive)
    refused = _by_outcome(report, IntakeOutcome.FAILED)
    assert len(refused) == 1 and "refused" in refused[0].reason and kind[:3] in refused[0].reason
    assert len(_rows(store)) == 1


@pytest.mark.parametrize("separator", ["/", "\\"])
@pytest.mark.parametrize(("name", "keyword"), HOSTILE)
def test_ti1_same_refusal_whichever_host_separator_rules_apply(
        monkeypatch, separator, name, keyword):
    """The Windows dev host and the Ubuntu server must refuse the same names for the same
    reason: `vet_member_name` may not consult `os.sep`."""
    monkeypatch.setattr(os, "sep", separator)
    assert keyword in vet_member_name(name)


@pytest.mark.parametrize("name", ["a/b/clip.mp4", "Clip (1).MP4", "dir\\sub\\clip.mp4",
                                  "über/ファイル.mp4", "a..b/clip.mp4", "...mp4"])
def test_ti1_benign_names_pass_vetting(name):
    """Backslash-separated folders from old zip tools and unicode names are legitimate."""
    assert vet_member_name(name) is None


def test_ti1_containment_uses_resolved_relative_path_not_a_string_prefix(tmp_path):
    """`staging-evil` shares a string prefix with `staging`; only a real containment check
    tells them apart, and an unresolved `..` must not slip through."""
    staging = tmp_path / "staging"
    staging.mkdir()
    (tmp_path / "staging-evil").mkdir()
    ensure_inside(staging / "m00001.mp4", staging)
    with pytest.raises(UnsafePath):
        ensure_inside(tmp_path / "staging-evil" / "x.mp4", staging)
    with pytest.raises(UnsafePath):
        ensure_inside(staging / ".." / "staging-evil" / "x.mp4", staging)


