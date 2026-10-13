"""TF2 (team-foundation.md, CRITICAL): the live-case approval is re-verified inside the launcher
for every entry point, and nothing a caller passes can skip it (AT-570, D-018, consent.md).

Rows: trigger {manual as the Test button, schedule as the tick, ci} x {no approval, covering
approval}. A refusal leaves the data root byte-identical and neither the browser nor the grader
is touched (the "transport" is the browser session and the judge: nothing else can reach the
network in a run).
"""

from __future__ import annotations

import inspect
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

        def __init__(self, project: Project) -> None:    # the factory is asked per project (LL2)
            self.project = project

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


PINNED = {
    "launch_run": {"slug", "run_id", "trigger", "requested_by", "slot_key", "via", "seams",
                   "priorities",          # priorities: T-178 FB4 selection, not a gate
                   "requested_at"},        # requested_at: T-201b attribution, not a gate
    "prepare_run": {"slug", "seams", "priorities"},
    "require_live_case_approval": {"project", "store", "cases", "secrets", "account_keys"},
}
PINNED_SEAMS = {"judge_factory", "planner", "free_ram_mb", "ledger"}


def test_the_gate_is_not_a_parameter() -> None:
    """The launcher's whole input surface is an exact, pinned allow-list: every parameter of
    `launch_run`, `prepare_run` and the gate, and every `RunSeams` field. A new knob of any
    name (or a `**kwargs`) fails here and must be argued for, with the gate still unskippable."""
    for name, expected in PINNED.items():
        params = inspect.signature(getattr(run_launcher, name)).parameters
        assert all(p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params.values()), name
        assert set(params) == expected, (name, sorted(set(params) ^ expected))
    assert set(RunSeams._fields) == PINNED_SEAMS, sorted(set(RunSeams._fields) ^ PINNED_SEAMS)


class Marker:
    """A truthy stand-in for any seam value: callable, delegating, and claiming every flag."""

    def __init__(self, inner: object) -> None:
        self.inner = inner

    def __bool__(self) -> bool:
        return True

    def __call__(self, *args: object, **kwargs: object) -> object:
        return self.inner(*args, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self.inner, name, True)


@pytest.mark.parametrize("sentinel", ["marker", "true"])
@pytest.mark.parametrize("field", RunSeams._fields)
def test_no_seam_value_skips_the_approval(world, field, sentinel, tmp_path) -> None:
    """Every `RunSeams` field, set to a truthy sentinel, still ends in a refusal with nothing
    created: the field list is read from the class, so a future `skip_approval` seam is covered
    the moment it exists."""
    store, seams = world
    current = getattr(seams, field)
    value = True if sentinel == "true" or isinstance(current, bool) else Marker(current)
    before = _listing(tmp_path)
    with pytest.raises(Exception) as raised:      
        launch_run("demo", seams=seams._replace(**{field: value}), **ENTRY_POINTS["manual"])
    if isinstance(raised.value, LaunchRefused):
        assert raised.value.status == 403 and "no approval exists" in raised.value.reason
    assert _listing(tmp_path) == before and not store.paths.runs_dir.exists()
    assert Counters.sessions == 0 and Counters.judgments == 0


def test_a_run_json_written_before_this_unit_loads_unchanged() -> None:
    raw = json.loads(GOLDEN.read_text(encoding="utf-8"))
    run = Run.model_validate(raw)
    assert (run.requested_by, run.slot_key, run.via) == (None, None, None)
    assert run.id == raw["id"] and run.bounds is not None
    assert json.loads(run.model_dump_json(exclude_none=True))["id"] == raw["id"]
