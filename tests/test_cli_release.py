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


def _two_flow_store(store: ProjectStore) -> None:
    """f1 has a plan (2 cases); f2 is in the FlowSpec but has no plan."""
    store.save_flowspec(FlowSpec(project="demo", flows=[
        Flow(id="f1", name="f1", entry_screen="home"),
        Flow(id="f2", name="f2", entry_screen="cart")]))
    store.save_flow_plan(FlowPlan(project="demo", flow_id="f1", case_ids=["c1", "c2"]))


def test_pause_shows_the_release_manager_what_he_is_approving(store: ProjectStore) -> None:
    _two_flow_store(store)
    grant_live_case_approval(store)
    paused = runner.invoke(app, ["release", "demo", "--run-id", "rel1", "--git-sha", "abc123"])
    assert paused.exit_code == 0 and "paused for your decision" in paused.output
    assert "flow f1 - 2 case(s)" in paused.output          # flows + case count
    assert "2 case(s)" in paused.output and "action(s)" in paused.output  # totals + actions
    assert "build: abc123" in paused.output
    assert "unplanned" in paused.output and "f2" in paused.output  # not run, named


def test_approve_says_what_happened_and_what_to_run_next(store: ProjectStore) -> None:
    grant_live_case_approval(store)
    runner.invoke(app, ["release", "demo", "--run-id", "rel1"])
    answered = runner.invoke(app, ["release", "demo", "--run-id", "rel1", "--approve-by", "rm"])
    assert answered.exit_code == 0
    assert "approved by rm" in answered.output
    assert "next:" in answered.output and "release-log demo rel1" in answered.output


def test_decline_does_not_claim_a_release_record_exists(store: ProjectStore) -> None:
    grant_live_case_approval(store)
    runner.invoke(app, ["release", "demo", "--run-id", "rel1"])
    declined = runner.invoke(app, ["release", "demo", "--run-id", "rel1", "--decline-by", "rm"])
    assert declined.exit_code == 0
    assert "finished" not in declined.output
    assert "see `autotester release-log" not in declined.output
    assert "declined by rm" in declined.output and "nothing was run" in declined.output
    assert "next:" in declined.output and "autotester release demo" in declined.output
    assert runner.invoke(app, ["release-log", "demo", "rel1"]).exit_code == 1  # no record


def test_answering_an_already_answered_release_is_a_one_line_refusal(
        store: ProjectStore) -> None:
    grant_live_case_approval(store)
    runner.invoke(app, ["release", "demo", "--run-id", "rel1"])
    runner.invoke(app, ["release", "demo", "--run-id", "rel1", "--decline-by", "rm"])
    again = runner.invoke(app, ["release", "demo", "--run-id", "rel1", "--approve-by", "rm"])
    assert again.exit_code == 1
    assert not isinstance(again.exception, ValueError) and "Traceback" not in again.output
    assert "already answered" in again.output and len(again.output.strip().splitlines()) == 1
