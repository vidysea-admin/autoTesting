"""AT-794: the run launcher triggers the advisory UX pass, non-fatally, and exports show it.

Contract: qa/contracts/persona-ux-advisory.md PU2/PU3/PU7 (plan decision 5: an advisory
failure never aborts or flips a run).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval

from autotester.browser.session import BrowserSession
from autotester.providers.mock import MockProvider
from autotester.schema.case import Case
from autotester.schema.enums import (
    Action,
    CaseClass,
    CaseKind,
    EvidenceKind,
    Outcome,
    Result,
    Severity,
    TechComfort,
)
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import Evidence, RawResult
from autotester.schema.user_persona import UserPersona, UXPolicy
from autotester.schema.ux_report import UXCaseStatus, UXDraft, UXJudgment
from autotester.schema.verdict import Verdict
from autotester.stages.parallel_run import ParallelPlan
from autotester.stages.run_launcher import RunSeams, launch_run
from autotester.stages.ux_advisory import add_ux_sheet, load_ux_state, ux_findings_html
from autotester.store.project_store import ProjectStore


def _build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, enabled: bool = True
           ) -> ProjectStore:
    import autotester.ui.run_execution as run_execution

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(
        slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
        user_persona_ref="p1", ux_policy=UXPolicy(enabled=enabled)))
    store.save_user_persona(UserPersona(id="p1", project="demo", role="counsellor",
                                        tech_comfort=TechComfort.LOW, locale="en-US",
                                        device="desktop"))
    store.add_case(Case(project="demo", flow_id="f", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="t",
                        steps=[Step(order=1, action=Action.CLICK, target="#go")]))

    def fake_run_and_grade(case_, session, judge, run_id, store_):
        run_dir = store_.paths.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "s.png").write_bytes(b"png")
        result = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED, evidence=[
            Evidence(kind=EvidenceKind.SCREENSHOT, path="s.png", step_order=1)])
        return result, Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                               grader_provider="mock")

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", fake_run_and_grade)
    grant_live_case_approval(store)
    return store


def _seams(provider: MockProvider) -> RunSeams:
    plan = ParallelPlan(1, 1, 1, "config", 99999.0, 8)
    return RunSeams(judge_factory=lambda project: provider, planner=lambda *a, **kw: plan)


def _findings() -> MockProvider:
    draft = UXDraft(severity=Severity.S2, finding="Label is unclear", step_order=1)
    return MockProvider(responses={"judge": [UXJudgment(findings=[draft])]})


def test_a_run_triggers_the_advisory_pass_with_the_runs_judge(tmp_path, monkeypatch) -> None:
    store = _build(tmp_path, monkeypatch)
    run = launch_run("demo", seams=_seams(_findings()))
    report = store.load_ux_report(run.id)
    assert report is not None and report.run_id == run.id
    assert report.cases[0].status is UXCaseStatus.ANALYZED
    assert report.cases[0].findings[0].finding == "Label is unclear"


def test_a_project_that_did_not_opt_in_gets_no_ux_report(tmp_path, monkeypatch) -> None:
    store = _build(tmp_path, monkeypatch, enabled=False)
    run = launch_run("demo", seams=_seams(_findings()))
    assert store.load_ux_report(run.id) is None


def test_an_advisory_failure_is_swallowed_and_the_verdicts_are_unchanged(
        tmp_path, monkeypatch) -> None:
    store = _build(tmp_path, monkeypatch, enabled=False)
    baseline = launch_run("demo", run_id="run-base", seams=_seams(_findings()))
    base_verdicts = [(v.case_id, v.result) for v in store.load_verdicts(baseline.id)]
    store.save_project(store.load_project().model_copy(
        update={"ux_policy": UXPolicy(enabled=True)}))

    def boom(*a, **kw):
        raise RuntimeError("advisory exploded")

    monkeypatch.setattr("autotester.stages.ux_wiring.run_ux_advisory", boom)
    run = launch_run("demo", run_id="run-boom", seams=_seams(_findings()))
    assert store.load_run(run.id) == run
    assert store.load_ux_report(run.id) is None
    assert [(v.case_id, v.result) for v in store.load_verdicts(run.id)] == base_verdicts


def test_the_pass_output_appears_in_the_exports(tmp_path, monkeypatch) -> None:
    from openpyxl import Workbook

    from autotester.core.redact import Redactor

    store = _build(tmp_path, monkeypatch)
    run = launch_run("demo", seams=_seams(_findings()))
    state = load_ux_state(store, run.id)
    case = store.list_cases()[0]
    html = ux_findings_html(state, case.id, Redactor({}))
    assert "UX findings" in html and "Label is unclear" in html
    wb = Workbook()
    add_ux_sheet(wb, state, {case.id: case}, Redactor({}))
    assert "UX findings (advisory)" in wb.sheetnames
