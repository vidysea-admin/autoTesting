"""TF6 (team-foundation.md): `Project` gains optional `schedule` and `tracker`, and `Source` gains
optional `uploaded_by`, `uploaded_at` and `origin`; all backward-compatible."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.schema.enums import SourceKind
from autotester.schema.project import Project, Source, TrackerConfig
from autotester.schema.schedule import ScheduleConfig
from autotester.schema.team_enums import ScheduleMode, SourceOriginKind

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "golden"


def test_every_committed_project_file_loads_and_round_trips() -> None:
    files = sorted((ROOT / "projects").glob("*/project.json"))
    assert files, "no committed projects/*/project.json to prove back-compat against"
    for path in files:
        loaded = Project.model_validate_json(path.read_text(encoding="utf-8"))
        again = Project.model_validate_json(loaded.model_dump_json())
        assert again == loaded, path
        assert loaded.schedule is None and loaded.tracker is None, path


def test_a_file_without_the_new_keys_loads_with_defaults() -> None:
    project = Project.model_validate_json(
        (GOLDEN / "project_without_team_keys.json").read_text(encoding="utf-8"))
    assert project.schedule is None  # None means manual
    assert project.tracker is None


def test_a_file_with_the_new_keys_round_trips() -> None:
    text = (GOLDEN / "project_with_team_keys.json").read_text(encoding="utf-8")
    project = Project.model_validate_json(text)
    assert isinstance(project.schedule, ScheduleConfig)
    assert project.schedule.mode is ScheduleMode.FIXED
    assert project.tracker == TrackerConfig()
    saved = json.loads(project.model_dump_json())
    assert Project.model_validate(saved) == project


def test_an_unknown_key_is_still_rejected_on_project_and_the_new_models() -> None:
    base = json.loads((GOLDEN / "project_without_team_keys.json").read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        Project.model_validate({**base, "surprise": 1})
    with pytest.raises(ValidationError):
        Project.model_validate({**base, "tracker": {"surprise": 1}})
    with pytest.raises(ValidationError):
        Project.model_validate({**base, "schedule": {"mode": "hourly"}})


def test_new_fields_are_optional_not_required() -> None:
    assert Project.model_fields["schedule"].is_required() is False
    assert Project.model_fields["tracker"].is_required() is False


def test_source_id_derivation_is_unchanged() -> None:
    """Idempotent re-ingest: adding team fields to Project must never move an existing id."""
    assert Source(project="demo", kind=SourceKind.TEXT, text="hello").id == "src_21e38144fee2"


PROVENANCE = ("uploaded_by", "uploaded_at", "origin")
SRC_TIME = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _plain_source(**extra: object) -> Source:
    return Source(project="demo", kind=SourceKind.TEXT, text="hello", created_at=SRC_TIME, **extra)


def test_source_provenance_fields_exist_optional_and_default_none() -> None:
    for name in PROVENANCE:
        field = Source.model_fields[name]
        assert field.is_required() is False and field.default is None, name
    plain = _plain_source()
    assert [getattr(plain, name) for name in PROVENANCE] == [None, None, None]


def test_a_source_without_provenance_serialises_exactly_as_before() -> None:
    """The bytes `append_jsonl` writes (exclude_none) carry none of the new keys."""
    line = _plain_source().model_dump_json(exclude_none=True)
    assert line == ('{"schema_version":1,"created_at":"2026-10-01T12:00:00Z",'
                    '"id":"src_21e38144fee2","project":"demo","kind":"text","text":"hello"}')


def test_an_old_sources_line_loads_and_a_provenance_line_round_trips() -> None:
    old = Source.model_validate_json(_plain_source().model_dump_json(exclude_none=True))
    assert old == _plain_source()
    full = _plain_source(uploaded_by="user-1", uploaded_at=SRC_TIME, origin=SourceOriginKind.ZIP)
    again = Source.model_validate_json(full.model_dump_json(exclude_none=True))
    assert again == full and again.origin is SourceOriginKind.ZIP and again.uploaded_at == SRC_TIME


def test_origin_is_a_closed_set_and_provenance_never_moves_the_id() -> None:
    assert {m.value for m in SourceOriginKind} == {"upload", "zip", "drive", "recording"}
    for bad in ("email", "UPLOAD", ""):
        with pytest.raises(ValidationError):
            _plain_source(origin=bad)
    with pytest.raises(ValidationError):
        _plain_source(uploaded_at="not a time")
    ids = {_plain_source().id,
           _plain_source(uploaded_by="u", uploaded_at=SRC_TIME, origin=SourceOriginKind.DRIVE).id}
    assert ids == {"src_21e38144fee2"}


def test_a_source_still_rejects_an_unknown_key() -> None:
    with pytest.raises(ValidationError):
        _plain_source(uploader="x")
