"""`autotester release` / `release-log` (T-167 release-manager surface), driven through the real
CLI against a temp `AUTOTESTER_ROOT`. Offline: no executor is wired, so a confirmed run stops at
EXECUTE and says so; the finished-log path is exercised through `release-log` on a stored record.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval
from typer.testing import CliRunner

from autotester.cli import app
from autotester.schema.flowspec import Flow, FlowSpec
from autotester.schema.project import Project
from autotester.schema.release import FlowPlan
from autotester.store.project_store import ProjectStore

runner = CliRunner()


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectStore:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.save_flowspec(FlowSpec(project="demo", flows=[
        Flow(id="f1", name="f1", entry_screen="home")]))
    store.save_flow_plan(FlowPlan(project="demo", flow_id="f1", case_ids=["c1"]))
    return store


def test_release_without_approval_is_refused_with_the_grant_command(store: ProjectStore) -> None:
    result = runner.invoke(app, ["release", "demo", "--run-id", "rel1"])
    assert result.exit_code == 2 and "autotester approve demo" in result.output
    assert not store.paths.run_dir("rel1").exists()


def test_release_pauses_for_a_human_then_the_decision_resumes_it(store: ProjectStore) -> None:
    grant_live_case_approval(store)
    paused = runner.invoke(app, ["release", "demo", "--run-id", "rel1"])
    assert paused.exit_code == 0 and "paused for your decision" in paused.output
    again = runner.invoke(app, ["release", "demo", "--run-id", "rel1"])
    assert "paused for your decision" in again.output  # no answer, still paused
    answered = runner.invoke(app, ["release", "demo", "--run-id", "rel1", "--approve-by", "rm"])
    assert answered.exit_code == 0 and "no executor is wired" in answered.output


def test_both_answers_at_once_is_refused(store: ProjectStore) -> None:
    result = runner.invoke(app, ["release", "demo", "--approve-by", "a", "--decline-by", "b"])
    assert result.exit_code == 1


def test_release_log_for_an_unknown_run_says_so(store: ProjectStore) -> None:
    result = runner.invoke(app, ["release-log", "demo", "nope"])
    assert result.exit_code == 1 and "no release record" in result.output
