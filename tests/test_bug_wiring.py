"""T-199d: a finished run reaches the bug store through `launch_run`, the one launcher.

Covers the gap that nothing called `process_run`: a failing verdict makes a tracked bug visible on
the tracker page, a re-run updates it rather than duplicating, two consecutive evidenced passes
fix it (TB2), a bug-loop fault is logged and does not lose the run, and the wiring touches no sheet
client (D-090).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from run_approval_fixture import grant_live_case_approval

from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result, Trigger
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.tracked_bug import BugStatus
from autotester.schema.verdict import Failure, Verdict
from autotester.stages import bug_wiring
from autotester.stages.parallel_run import ParallelPlan
from autotester.stages.run_launcher import RunSeams, launch_run
from autotester.store.bug_store import BugStore
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

SRC = Path(__file__).resolve().parents[1] / "src" / "autotester"


class Outcomes:
    result = Result.FAIL


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ProjectStore, RunSeams]:
    import autotester.ui.run_execution as run_execution

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.add_case(Case(project="demo", flow_id="f", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="Checkout works",
                        steps=[Step(order=0, action=Action.CLICK, target="#go")]))
    grant_live_case_approval(store)
    Outcomes.result = Result.FAIL

    class Judge:
        trace = None

        def __init__(self, project: Project) -> None:
            self.project = project

        def available(self) -> bool:
            return True

    def graded(case_, session, judge, run_id, store_):
        if Outcomes.result is Result.FAIL:
            verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.FAIL,
                              criteria_met=0, criteria_total=1, grader_provider="mock",
                              failures=[Failure(criterion_id="C1", reason="nothing happened")])
        else:
            verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                              criteria_met=1, criteria_total=1, grader_provider="mock")
        store_.save_verdict(run_id, verdict)
        return RawResult(case_id=case_.id, outcome=Outcome.COMPLETED), verdict

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", graded)
    plan = ParallelPlan(1, 1, 1, "config", 99999.0, 8)
    return store, RunSeams(judge_factory=Judge, planner=lambda *a, **kw: plan)


def _bugs(store: ProjectStore) -> dict:
    return BugStore(store.paths.dir).bugs()


def test_a_failing_run_creates_a_bug_visible_on_the_tracker_page(world) -> None:
    store, seams = world
    run = launch_run("demo", seams=seams, trigger=Trigger.MANUAL, requested_by="u1")
    (bug,) = _bugs(store).values()
    assert bug.status is BugStatus.OPEN and bug.count == 1 and bug.evidence_run_id == run.id
    html = TestClient(app).get("/projects/demo/tracker").text
    assert "Checkout works" in html and run.id in html


def test_a_rerun_updates_the_bug_and_never_duplicates_it(world) -> None:
    store, seams = world
    launch_run("demo", seams=seams, trigger=Trigger.CI)
    launch_run("demo", seams=seams, trigger=Trigger.CI)
    (bug,) = _bugs(store).values()
    assert bug.count == 2 and bug.status is BugStatus.OPEN


def test_two_evidenced_passes_fix_it_and_a_later_fail_reopens_it(world) -> None:
    store, seams = world
    launch_run("demo", seams=seams, trigger=Trigger.CI)
    Outcomes.result = Result.PASS
    launch_run("demo", seams=seams, trigger=Trigger.CI)
    (bug,) = _bugs(store).values()
    assert bug.status is BugStatus.OPEN          # one pass is k < N
    launch_run("demo", seams=seams, trigger=Trigger.CI)
    (bug,) = _bugs(store).values()
    assert bug.status is BugStatus.FIXED and len(bug.closed_by_verdicts) == 2
    Outcomes.result = Result.FAIL
    launch_run("demo", seams=seams, trigger=Trigger.CI)
    (bug,) = _bugs(store).values()
    assert bug.status is BugStatus.REOPENED


def test_processing_the_same_run_again_changes_nothing(world) -> None:
    store, seams = world
    run = launch_run("demo", seams=seams, trigger=Trigger.CI)
    before = {p.name: p.read_bytes() for p in (store.paths.dir / "bug_events").iterdir()}
    again = bug_wiring.record_run_bugs(store, run.id)
    assert again is not None and again.applied == 0
    assert {p.name: p.read_bytes() for p in (store.paths.dir / "bug_events").iterdir()} == before


def test_a_bug_loop_fault_is_logged_and_the_run_survives(world, monkeypatch,
                                                         caplog: pytest.LogCaptureFixture) -> None:
    store, seams = world

    def boom(*_a, **_kw):
        raise OSError("disk went away")

    monkeypatch.setattr(bug_wiring, "process_run", boom)
    with caplog.at_level(logging.ERROR, logger=bug_wiring.__name__):
        run = launch_run("demo", seams=seams, trigger=Trigger.CI)
    assert store.load_run(run.id) is not None and _bugs(store) == {}
    assert run.id in caplog.text and "disk went away" in caplog.text


def test_the_wiring_uses_no_sheet_client() -> None:
    text = (SRC / "stages" / "bug_wiring.py").read_text(encoding="utf-8")
    assert "SheetClient" not in text and "sheet_write" not in text and "sheet_sync" not in text
    assert ProjectPaths("demo").dir.name == "demo"
