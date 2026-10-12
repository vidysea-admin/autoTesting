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


@pytest.mark.parametrize("bad", ["..", "../escaped", "..\\escaped", "/abs/x", "C:\\x", "a/b", "."])
def test_at900_unsafe_run_id_is_refused_before_any_write(store: ProjectStore, bad: str,
                                                        tmp_path: Path) -> None:
    grant_live_case_approval(store)
    before = set(tmp_path.rglob("*"))
    result = runner.invoke(app, ["release", "demo", "--run-id", bad])
    assert result.exit_code == 1 and "invalid --run-id" in result.output
    assert set(tmp_path.rglob("*")) == before
    assert not (tmp_path.parent / "escaped").exists()


def test_at900_encoded_separators_stay_one_segment_under_runs(store: ProjectStore) -> None:
    for rid in ("..%2fescaped", "%2e%2e", "a%5cb"):
        d = store.paths.run_dir(rid)
        assert d.parent == store.paths.runs_dir
    with pytest.raises(ValueError):
        store.paths.run_dir("../x")


def test_at898_release_persists_flow_plans_from_approved_cases(store: ProjectStore) -> None:
    from autotester.schema.case import Case
    from autotester.schema.enums import CaseClass, CaseKind, CaseStatus
    from autotester.schema.release import FlowPlan  # noqa: F401
    store.paths.flow_plans.unlink()  # no hand-seeded plan: the producer must make it
    case = store.add_case(Case(project="demo", flow_id="f1", kind=CaseKind.BEST,
                               case_class=CaseClass.HAPPY, title="t",
                               status=CaseStatus.APPROVED))
    grant_live_case_approval(store)
    res = runner.invoke(app, ["release", "demo", "--run-id", "rel1"])
    assert res.exit_code == 0 and "flows to run: 1" in res.output
    assert [p.case_ids for p in store.list_flow_plans()] == [[case.id]]
    assert store.load_release_scope("rel1").plans[0].flow_id == "f1"


def test_at899_pause_shows_scope_and_approve_decline_say_what_happened(
        store: ProjectStore) -> None:
    grant_live_case_approval(store)
    paused = runner.invoke(app, ["release", "demo", "--run-id", "rel1", "--git-sha", "abc123"])
    assert "abc123" in paused.output and "flows to run: 1" in paused.output
    assert "1 cases" in paused.output
    bad = runner.invoke(app, ["release", "demo", "--run-id", "rel1", "--decline-by", "rm"])
    assert "declined by rm" in bad.output and "finished - see" not in bad.output
    again = runner.invoke(app, ["release", "demo", "--run-id", "rel1", "--approve-by", "rm"])
    assert again.exit_code == 1 and "Traceback" not in again.output
    assert "cannot answer release rel1" in again.output


def test_at899_approve_names_the_next_step(store: ProjectStore) -> None:
    grant_live_case_approval(store)
    runner.invoke(app, ["release", "demo", "--run-id", "rel2"])
    ok = runner.invoke(app, ["release", "demo", "--run-id", "rel2", "--approve-by", "rm"])
    assert "approved by rm" in ok.output and "Next:" in ok.output
