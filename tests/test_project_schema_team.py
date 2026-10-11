"""TF6 (team-foundation.md): `Project` gains optional `schedule` and `tracker`, backward-compatible.

(`Source` provenance is T-198's: see the manifest's HELD section.)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from autotester.schema.enums import SourceKind
from autotester.schema.project import Project, Source, TrackerConfig
from autotester.schema.schedule import ScheduleConfig
from autotester.schema.team_enums import ScheduleMode

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
