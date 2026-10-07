"""Intake schema and the one upload-limit accessor (team-intake.md TI9, TI11, TI2 defaults).

The accessor is the single source of the limit for the HTTP upload, the Drive fetch and zip
member inflation (R41, D-072#10). The cases below are the ones an admin or an attacker can
actually produce: a missing or hand-edited settings file, a tester's zip at the limit, a
`sources.jsonl` written before the provenance fields existed.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from zip_fixtures import build_zip, make_store

from autotester.core.ids import content_id
from autotester.core.upload_limit import SETTINGS_ENV, human_bytes, read_max_upload_bytes
from autotester.schema.enums import SourceKind
from autotester.schema.intake import (
    DEFAULT_MAX_UPLOAD_BYTES,
    DriveOrigin,
    IntakeOutcome,
    MemberResult,
    UploadOrigin,
    ZipLimits,
    ZipOrigin,
)
from autotester.schema.project import Source
from autotester.sources.zip_intake import expand_zip
from autotester.store.filestore import read_jsonl

MIB = 1024 * 1024
SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"


def _settings(tmp_path: Path, value) -> Path:
    path = tmp_path / "server_settings.json"
    path.write_text(json.dumps({"max_upload_bytes": value}), encoding="utf-8")
    return path


# ---- TI9: the accessor ------------------------------------------------------

def test_ti9_default_is_2_gib_when_no_setting_exists(tmp_path):
    """A fresh server: nobody has opened the admin settings page yet."""
    limit = read_max_upload_bytes(tmp_path / "absent.json")
    assert limit.bytes == 2 * 1024**3 == DEFAULT_MAX_UPLOAD_BYTES
    assert limit.from_default and "default" in limit.note


@pytest.mark.parametrize("value", [MIB, 5 * MIB, 64 * 1024**3])
def test_ti9_a_valid_admin_value_is_used_as_written(tmp_path, value):
    """The admin sets the limit between HO15's bounds (1 MiB .. 64 GiB)."""
    limit = read_max_upload_bytes(_settings(tmp_path, value))
    assert limit.bytes == value and not limit.from_default


@pytest.mark.parametrize("value", [0, -1, MIB - 1, 64 * 1024**3 + 1, "2", "x", 2.5, True, None,
                                   2**63, [5]])
def test_ti9_a_hand_edited_bad_value_falls_back_to_default_and_says_so(tmp_path, value):
    """Someone edits the settings file by hand and gets a type or range wrong."""
    limit = read_max_upload_bytes(_settings(tmp_path, value))
    assert limit.bytes == DEFAULT_MAX_UPLOAD_BYTES and limit.from_default
    assert "max_upload_bytes" in limit.note


@pytest.mark.parametrize("text", ["{not json", "[]", "", "\x00\x00"])
def test_ti9_corrupt_settings_file_falls_back_to_default(tmp_path, text):
    """A half-written or truncated settings file."""
    path = tmp_path / "server_settings.json"
    path.write_text(text, encoding="utf-8")
    assert read_max_upload_bytes(path).from_default


def test_ti9_value_is_read_at_request_time_so_a_change_applies_without_restart(tmp_path):
    """The admin lowers the limit between two uploads."""
    path = _settings(tmp_path, 5 * MIB)
    assert read_max_upload_bytes(path).bytes == 5 * MIB
    _settings(tmp_path, 2 * MIB)
    assert read_max_upload_bytes(path).bytes == 2 * MIB


def test_ti9_environment_names_the_settings_file(tmp_path, monkeypatch):
    """The server is started with `AUTOTESTER_SERVER_SETTINGS` pointing at the admin file."""
    monkeypatch.setenv(SETTINGS_ENV, str(_settings(tmp_path, 7 * MIB)))
    assert read_max_upload_bytes().bytes == 7 * MIB


def test_ti9_message_names_the_limit_in_human_units():
    assert human_bytes(5 * MIB) == "5 MiB"
    assert human_bytes(2 * 1024**3) == "2 GiB"
    assert human_bytes(1536) == "1.5 KiB"
    assert human_bytes(10) == "10 B"


def test_ti9_zip_member_cap_is_the_setting_and_the_next_request_obeys_a_change(
        tmp_path, monkeypatch):
    """With the setting at 5 MiB a 5 MiB video registers and 5 MiB + 1 byte is refused;
    raising the setting to 6 MiB lets the same bytes in on the very next request."""
    monkeypatch.setenv(SETTINGS_ENV, str(_settings(tmp_path, 5 * MIB)))
    store = make_store(tmp_path)
    exact = build_zip(tmp_path / "exact.zip", [("exact.mp4", b"A" * (5 * MIB))])
    over_bytes = b"B" * (5 * MIB + 1)
    over = build_zip(tmp_path / "over.zip", [("over.mp4", over_bytes)])

    assert expand_zip(store, exact).exit_code == 0
    refused = expand_zip(store, over)
    assert refused.exit_code == 2 and "5 MiB" in refused.members[0].reason
    assert not [p for p in tmp_path.rglob("*.mp4") if p.stat().st_size == len(over_bytes)]

    _settings(tmp_path, 6 * MIB)
    assert expand_zip(store, over).exit_code == 0
    assert len(store.list_sources()) == 2


def test_ti9_no_second_copy_of_the_limit_anywhere_in_src():
    """One concept, one place: the only 2 GiB literal is the settings default."""
    pattern = re.compile(r"2\s*\*\s*1024\s*\*\*\s*3|2147483648"
                         r"|2\s*\*\s*1024\s*\*\s*1024\s*\*\s*1024|2\s*<<\s*30|0x80000000")
    offenders = [p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py")
                 if p.name != "intake.py" and pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


# ---- TI2: the other caps are named defaults in one place ---------------------

def test_ti2_named_defaults_match_the_contract():
    limits = ZipLimits()
    assert (limits.max_entries, limits.max_videos, limits.max_ratio) == (1000, 20, 100)
    assert limits.max_total_bytes == 10 * 1000**3 and limits.max_archive_bytes == 5 * 1000**3


@pytest.mark.parametrize("field", ["max_entries", "max_videos", "max_total_bytes",
                                   "max_archive_bytes", "max_ratio"])
def test_ti2_a_zero_or_negative_cap_is_refused_at_construction(field):
    """A cap of 0 would silently refuse every archive; refuse the configuration instead."""
    with pytest.raises(ValidationError):
        ZipLimits(**{field: 0})


# ---- TI11: provenance fields ------------------------------------------------

def test_ti11_new_provenance_fields_default_to_none_and_id_does_not_move():
    plain = Source(project="demo", kind=SourceKind.VIDEO, sha256="abc123")
    rich = Source(project="demo", kind=SourceKind.VIDEO, sha256="abc123", uploaded_by="a@x.io",
                  uploaded_at=datetime(2026, 10, 7, tzinfo=UTC),
                  origin=ZipOrigin(archive_name="in.zip", member_path="a/clip.mp4"))
    assert plain.uploaded_by is None and plain.uploaded_at is None and plain.origin is None
    assert plain.id == rich.id == content_id("src", {"k": "video", "v": "abc123"})


def test_ti11_a_sources_jsonl_written_before_the_change_still_loads_with_the_same_id(tmp_path):
    """A project whose sources.jsonl predates `uploaded_by` / `origin`."""
    sid = content_id("src", {"k": "video", "v": "deadbeef"})
    old_row = {"schema_version": 1, "created_at": "2026-09-01T00:00:00Z", "id": sid,
               "project": "demo", "kind": "video", "path": "x/recording.mp4",
               "sha256": "deadbeef", "label": "old clip"}
    path = tmp_path / "sources.jsonl"
    path.write_text(json.dumps(old_row) + "\n", encoding="utf-8")
    [loaded] = read_jsonl(path, Source)
    assert loaded.id == sid and loaded.uploaded_by is None and loaded.origin is None


def test_ti11_source_and_origin_models_reject_unknown_fields():
    with pytest.raises(ValidationError):
        Source(project="demo", kind=SourceKind.VIDEO, sha256="a", surprise=1)
    with pytest.raises(ValidationError):
        ZipOrigin(archive_name="a.zip", member_path="x.mp4", extra="no")


@pytest.mark.parametrize("payload", [
    {"kind": "upload"},                                   # no file name
    {"kind": "upload", "file_id": "x"},                   # a drive field on an upload
    {"kind": "zip", "archive_name": "a.zip"},             # no member path
    {"kind": "drive", "file_id": "x", "file_name": "y"},  # an upload field on drive
    {"kind": "email", "file_id": "x"},                    # an unknown shape
])
def test_ti11_origin_is_exactly_one_of_the_three_typed_shapes(payload):
    with pytest.raises(ValidationError):
        Source(project="demo", kind=SourceKind.VIDEO, sha256="a", origin=payload)


@pytest.mark.parametrize("origin", [UploadOrigin(file_name="a.mp4"),
                                    ZipOrigin(archive_name="a.zip", member_path="d/a.mp4"),
                                    DriveOrigin(file_id="1AbC_d-9")])
def test_ti11_each_origin_shape_round_trips_through_sources_jsonl(tmp_path, origin):
    store = make_store(tmp_path)
    store.add_source(Source(project="demo", kind=SourceKind.VIDEO, sha256="a1",
                            origin=origin, uploaded_by="dev@x.io",
                            uploaded_at=datetime(2026, 10, 7, 9, 30, tzinfo=UTC)))
    [back] = store.list_sources()
    assert back.origin == origin and back.uploaded_by == "dev@x.io"
    assert back.uploaded_at == datetime(2026, 10, 7, 9, 30, tzinfo=UTC)


def test_ti11_zip_intake_records_archive_member_who_and_when(tmp_path):
    """A developer uploads `suite.zip`; the registered row says whose, when and which member."""
    from autotester.sources.zip_intake import expand_zip as run

    store = make_store(tmp_path)
    archive = build_zip(tmp_path / "suite.zip", [("flows/login.mp4", b"L" * 4096)])
    moment = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
    report = run(store, archive, archive_name="suite.zip", max_file_bytes=MIB,
                 uploaded_by="dev@x.io", now=lambda: moment)
    [row] = store.list_sources()
    assert report.members[0].outcome is IntakeOutcome.REGISTERED
    assert row.uploaded_by == "dev@x.io" and row.uploaded_at == moment
    assert row.origin == ZipOrigin(archive_name="suite.zip", member_path="flows/login.mp4")


def test_ti11_member_result_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        MemberResult(member="a", outcome=IntakeOutcome.SKIPPED, bogus=1)
