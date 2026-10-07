"""`autotester approve` grant bounds (consent.md CN10/CN11 clause 3, CLI path).

Split from `test_approve_cli.py` at the 300-line cap. The CLI must refuse a
nonpositive or nonfinite action/probe/wall-clock bound WITHOUT writing a row,
and must default to positive finite bounds and `production=False`.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli import app
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

runner = CliRunner()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
BASE_URL = "https://demo.test/"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    ProjectStore("demo", tmp_path).save_project(Project(
        slug="demo", name="Demo", base_url=BASE_URL, allowed_domains=["demo.test"]))
    return tmp_path


def grant(*extra: str) -> object:
    return runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "read-only crawl", "--granted-by", "umesh",
        "--expires", TOMORROW, *extra,
    ])


@pytest.mark.parametrize("flag,value", [
    ("--wall-clock", "nan"), ("--wall-clock", "inf"), ("--wall-clock", "-inf"),
    ("--wall-clock", "0"), ("--wall-clock", "-1"),
    ("--max-actions", "0"), ("--max-actions", "-1"),
    ("--max-probes", "0"), ("--max-probes", "-1"),
])
def test_approve_refuses_a_nonpositive_or_nonfinite_bound_and_writes_nothing(
    root: Path, flag: str, value: str,
) -> None:
    result = grant(flag, value)

    assert result.exit_code != 0, f"{flag} {value} was accepted"
    assert ProjectStore("demo", root).list_approvals() == [], "a refused grant left a row"


def test_approve_defaults_are_positive_finite_and_not_production(root: Path) -> None:
    import math

    result = grant()

    assert result.exit_code == 0, result.output
    row = ProjectStore("demo", root).list_approvals()[0]
    assert row.max_actions > 0 and row.max_probes > 0
    assert row.wall_clock_s > 0 and math.isfinite(row.wall_clock_s)
    assert row.production is False
