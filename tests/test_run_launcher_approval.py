"""TF2 (team-foundation.md, CRITICAL): the live-case approval is re-verified inside the launcher
for every entry point, and nothing a caller passes can skip it (AT-570, D-018, consent.md).

Rows: trigger {manual as the Test button, schedule as the tick, ci} x {no approval, covering
approval}. A refusal leaves the data root byte-identical and neither the browser nor the grader
is touched (the "transport" is the browser session and the judge: nothing else can reach the
network in a run).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from run_approval_fixture import grant_live_case_approval

from autotester.browser.session import BrowserSession
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result, Trigger
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import RawResult, Run
from autotester.schema.team_enums import RunVia
from autotester.schema.verdict import Verdict
from autotester.stages import run_launcher
from autotester.stages.parallel_run import ParallelPlan
from autotester.stages.run_launcher import LaunchRefused, RunSeams, launch_run
from autotester.store.project_store import ProjectStore

GOLDEN = Path(__file__).parent / "golden" / "run_pre_t205.json"
ENTRY_POINTS = {
    "manual": dict(trigger=Trigger.MANUAL, requested_by="user-1", via=RunVia.TEAM_BUTTON),
    "schedule": dict(trigger=Trigger.SCHEDULE, requested_by="owner-1",
                     slot_key="demo:fixed:2026-10-11T09:30Z"),
    "ci": dict(trigger=Trigger.CI),
}


class Counters:
    sessions = 0
    judgments = 0


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[ProjectStore, RunSeams]:
    import autotester.ui.run_execution as run_execution

    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    store.add_case(Case(project="demo", flow_id="f", kind=CaseKind.BEST,
                        case_class=CaseClass.HAPPY, title="t",
                        steps=[Step(order=0, action=Action.CLICK, target="#go")]))
    Counters.sessions = Counters.judgments = 0
    original_init = BrowserSession.__init__

    def counting_init(self, *a, **kw):
        Counters.sessions += 1
        original_init(self, *a, **kw)

    class Judge:
        trace = None

        def available(self) -> bool:
            return True

        def judge(self, *a, **kw):
            Counters.judgments += 1
            raise AssertionError("the grader must not be reached")

    def fake_run_and_grade(case_, session, judge, run_id, store_):
        return (RawResult(case_id=case_.id, outcome=Outcome.COMPLETED),
                Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                        grader_provider="mock"))

    monkeypatch.setattr(BrowserSession, "__init__", counting_init)
    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)
    monkeypatch.setattr(run_execution, "run_and_grade_case_resilient", fake_run_and_grade)
    plan = ParallelPlan(1, 1, 1, "config", 99999.0, 8)
    return store, RunSeams(judge_factory=Judge, planner=lambda *a, **kw: plan)


def _listing(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("entry", sorted(ENTRY_POINTS))
def test_no_covering_approval_refuses_before_anything_exists(world, entry, tmp_path) -> None:
    store, seams = world
    before = _listing(tmp_path)
    with pytest.raises(LaunchRefused) as refused:
        launch_run("demo", seams=seams, **ENTRY_POINTS[entry])
    assert refused.value.status == 403
    assert "live_case" in refused.value.reason and "no approval exists" in refused.value.reason
    assert _listing(tmp_path) == before          # byte-identical: no run dir, no result, no row
    assert Counters.sessions == 0 and Counters.judgments == 0
    assert not store.paths.runs_dir.exists()


@pytest.mark.parametrize("entry", sorted(ENTRY_POINTS))
def test_a_covering_approval_proceeds_and_records_who_and_how(world, entry) -> None:
    store, seams = world
    grant_live_case_approval(store)
    kwargs = ENTRY_POINTS[entry]
    run = launch_run("demo", seams=seams, **kwargs)
    assert Counters.sessions >= 1
    saved = store.load_run(run.id)
    assert saved == run
    assert saved.trigger is kwargs["trigger"]
    assert saved.requested_by == kwargs.get("requested_by")
    assert saved.slot_key == kwargs.get("slot_key")
    assert saved.via == kwargs.get("via")


def test_the_gate_is_not_a_parameter() -> None:
    """No flag, however named, lets a caller skip the approval check."""
    tree = ast.parse(Path(run_launcher.__file__).read_text(encoding="utf-8"))
    banned = ("skip", "bypass", "force", "unchecked", "no_approval", "approved", "trusted")
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        names = [a.arg for a in fn.args.args + fn.args.kwonlyargs]
        assert not [a for a in names if any(b in a.lower() for b in banned)], (fn.name, names)


def test_a_run_json_written_before_this_unit_loads_unchanged() -> None:
    raw = json.loads(GOLDEN.read_text(encoding="utf-8"))
    run = Run.model_validate(raw)
    assert (run.requested_by, run.slot_key, run.via) == (None, None, None)
    assert run.id == raw["id"] and run.bounds is not None
    assert json.loads(run.model_dump_json(exclude_none=True))["id"] == raw["id"]
