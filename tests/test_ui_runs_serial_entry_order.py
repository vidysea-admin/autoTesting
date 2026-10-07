"""AT-576: the serial route (`ui/routes_runs.py::_run_cases_serially`) must
run every entry case to completion -- its own dedicated session -- BEFORE
the shared session (reused across the run's ordinary cases) is ever
started. Fast, fake-session regression test for the ORDERING decision
itself; `test_ui_runs_serial_entry_mix_live.py` proves the real defect (two
live sync-Playwright drivers on one thread) that only a real browser can
reach -- a fake `BrowserSession.start` cannot see it, which is exactly why
AT-576 shipped undetected. Contract: qa/contracts/ui-run.md RU1-RU4.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_ui_runs import _approve_demo_runs
from test_ui_runs_parallel_trace import _non_entry_case, client, scratch_root
from test_ui_runs_serial_resilience import _entry_case

from autotester.schema.catalog import TIER_BY_CLASS
from autotester.schema.enums import CaseClass, Outcome, Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.store.project_store import ProjectStore

__all__ = ["client", "scratch_root"]


def test_entry_cases_start_before_the_shared_session_starts(
    client: TestClient, scratch_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A run mixing one entry case with one ordinary case: the entry case's
    dedicated session (`ProjectPaths` slug `demo-entry-test`) must start
    before the shared session (slug `demo`) ever starts -- never the shared
    session first. Before the fix, the shared session started FIRST for any
    run with at least one non-entry case, which is the exact precondition
    that made a live entry case start a second sync Playwright driver while
    the shared one was still running (500)."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    store.add_case(_entry_case())
    store.add_case(_non_entry_case(0))

    starts: list[str] = []

    import autotester.ui.routes_runs as routes_runs_module
    from autotester.browser.session import BrowserSession

    def fake_start(self):  # records WHICH session started, in call order
        starts.append(self.paths.slug)
        return self

    monkeypatch.setattr(BrowserSession, "start", fake_start)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", _AvailableProvider)

    import autotester.stages.run_case_pipeline as pipeline_module

    def fake_run_case(case_, session):
        return RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)

    def fake_grade(rubric, result, run_id, judge, run_dir=None, secrets=None):
        return Verdict(run_id=run_id, case_id=result.case_id, result=Result.PASS,
                       grader_provider="mock")

    monkeypatch.setattr(pipeline_module, "run_case", fake_run_case)
    monkeypatch.setattr(pipeline_module, "grade", fake_grade)

    _approve_demo_runs(scratch_root)  # AT-570: the live_case approval a run now needs
    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303, response.text
    assert starts == ["demo-entry-test", "demo"], (
        f"the entry case's own session must start before the shared session: {starts}"
    )


def _mixed_tier_cases():
    """Shuffled distinct stored IDs, including a blocked/pinned adversarial case."""
    classes = [CaseClass.AUTH_WRONG_CREDS, CaseClass.HAPPY, CaseClass.DOUBLE_SUBMIT]
    cases = []
    for idx, case_class in enumerate(classes):
        for pos, entry in enumerate((False, False, True)):
            case = _entry_case() if entry else _non_entry_case(idx)
            case = case.model_copy(update={"id": "", "flow_id": f"tier-{idx}-{pos}",
                                           "case_class": case_class, "pinned": idx == 0})
            cases.append(type(case)(**case.model_dump(exclude={"id"})))
    return cases


def _patch_tier_execution(monkeypatch, events, clock=None):
    """Fake browser/judge collaborators; preserve trigger, dispatch and budgets."""
    import autotester.stages.run_case_pipeline as pipeline
    import autotester.ui.routes_runs as routes
    from autotester.browser.session import BrowserSession
    original_grade = pipeline.grade
    active = set()

    def start(self):
        assert id(self) not in active
        if self.paths.slug == "demo-entry-test":
            assert not active, "entry driver must never nest inside a shared/fan-out driver"
        active.add(id(self))
        events.append(("session", self.paths.slug))
        return self

    def close(self):
        active.remove(id(self))
        events.append(("close", self.paths.slug))

    def run(case, session):
        budget = getattr(session, "budget", None)
        if budget is not None:  # one mocked step, spent through the real d063 budget API
            budget.check(actions=1)
        events.append(("case", case.id))
        if clock is not None:
            clock[0] = 11.0
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    def grade(rubric, result, run_id, judge, run_dir=None, secrets=None):
        if result.outcome is Outcome.ERRORED:
            return original_grade(rubric, result, run_id, judge, run_dir=run_dir, secrets=secrets)
        events.append(("grade", result.case_id))
        return Verdict(run_id=run_id, case_id=result.case_id, result=Result.PASS,
                       grader_provider="mock")

    class Judge:
        def available(self):
            return True
        def judge(self, *args, **kwargs):
            pytest.fail("unexpected provider judgment")

    monkeypatch.setattr(BrowserSession, "start", start)
    monkeypatch.setattr(BrowserSession, "close", close)
    monkeypatch.setattr(pipeline, "run_case", run)
    monkeypatch.setattr(pipeline, "grade", grade)
    monkeypatch.setattr(routes, "LangChainFallbackProvider", Judge)
    import autotester.ui.run_execution as execution
    monkeypatch.setattr(execution.shutil, "rmtree",
                        lambda path, **kw: events.append(("wipe", path)))
    return routes, Judge()


@pytest.mark.parametrize("width", [1, 2])
def test_real_trigger_orders_tiers_and_persists_blocked_pinned_cases(
    client, scratch_root, monkeypatch, width,
):
    from test_ui_runs import _only_run_id

    from autotester.stages.parallel_run import ParallelPlan
    client.post("/onboard", data={"slug": "demo", "name": "Demo",
                                "base_url": "https://demo.test", "allowed_domains": "demo.test"})
    store = ProjectStore("demo", scratch_root)
    cases = _mixed_tier_cases()
    for case in cases:
        store.add_case(case)
    events = []
    routes, _ = _patch_tier_execution(monkeypatch, events)
    plan = ParallelPlan(config_ceiling=width, measured_budget=width, n=width,
                        bound_by="config", free_ram_mb=99999.0, cpu_count=8)
    monkeypatch.setattr(routes, "plan_parallel_run", lambda *a, **kw: plan)
    _approve_demo_runs(scratch_root)
    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303, response.text
    observed = [value for kind, value in events if kind == "case"]
    assert observed[0] == cases[5].id
    assert set(observed[1:3]) == {cases[3].id, cases[4].id}
    assert observed[3] == cases[8].id
    assert set(observed[4:6]) == {cases[6].id, cases[7].id}
    assert observed[6] == cases[2].id
    assert set(observed[7:9]) == {cases[0].id, cases[1].id}
    run_id = _only_run_id(store)
    assert sorted(r.case_id for r in store.load_results(run_id)) == sorted(c.id for c in cases)
    assert sorted(v.case_id for v in store.load_verdicts(run_id)) == sorted(c.id for c in cases)
    run = store.load_run(run_id)
    assert run and sorted(run.case_ids) == sorted(c.id for c in cases)
    assert run.model_dump().get("catalog_runnable_counts") == {
        "static": 0, "behavioural": 0, "adversarial": 0}
    spans = [json.loads(line) for line in store.paths.run_trace(run_id).read_text().splitlines()]
    assert [s["stage"] for s in spans if s.get("kind") == "stage"] == ["execute"]


@pytest.mark.parametrize("width", [1, 2])
@pytest.mark.parametrize("deadline", [False, True])
@pytest.mark.parametrize("allowance", [1, 4])
@pytest.mark.parametrize("early_normal", [False, True])
def test_internal_execution_spends_one_budget_across_tiers_and_all_legs(
    client, scratch_root, monkeypatch, width, deadline, allowance, early_normal,
):
    """Internal bounded grant deliberately bypasses HTTP preflight only in this test."""
    from run_approval_fixture import grant_live_case_approval

    import autotester.stages.run_budget as budget_module
    from autotester.browser.secrets import SecretStore
    from autotester.core.paths import ProjectPaths
    from autotester.stages.parallel_run import ParallelPlan
    client.post("/onboard", data={"slug": "demo", "name": "Demo",
                                "base_url": "https://demo.test", "allowed_domains": "demo.test"})
    store = ProjectStore("demo", scratch_root)
    project = store.load_project()
    cases = _mixed_tier_cases()
    expected = [cases[i].id for i in (5, 3, 4, 8)][:1 if deadline else allowance]
    if deadline and early_normal:
        cases = [cases[i] for i in (3, 8, 6, 2, 0)]
        expected = [cases[0].id]
    for case in cases:
        store.add_case(case)
    events, clock = [], [0.0]
    routes, judge = _patch_tier_execution(monkeypatch, events, clock if deadline else None)
    monkeypatch.setattr(budget_module.time, "monotonic", lambda: clock[0])
    plan = ParallelPlan(config_ceiling=width, measured_budget=width, n=width,
                        bound_by="config", free_ram_mb=99999.0, cpu_count=8)
    monkeypatch.setattr(routes, "plan_parallel_run", lambda *a, **kw: plan)
    approval = grant_live_case_approval(store, max_actions=100 if deadline else allowance,
                                         wall_clock_s=10.0)
    paths = ProjectPaths("demo")
    routes._execute_with_trace(store, "limited", SecretStore.load(project, paths.env_file),
                              project, cases, [routes._is_entry_case(c, project) for c in cases],
                              paths.run_dir("limited"), paths, "demo", judge, approval)
    assert sorted(value for kind, value in events if kind == "case") == sorted(expected)
    results = {r.case_id: r for r in store.load_results("limited")}
    assert set(results) == {c.id for c in cases}  # never-skip: every case persisted
    reason = "wall_clock_s" if deadline else "max_actions"
    assert all(results[c.id].outcome is Outcome.ERRORED
               and f"run budget exhausted: {reason}" in results[c.id].error
               for c in cases if c.id not in expected)
    entry_ids = {c.id for c in cases if routes._is_entry_case(c, project)}
    normals = [c for c in cases if c.id in expected and c.id not in entry_ids]
    sessions = len(entry_ids & set(expected)) + (
        len({TIER_BY_CLASS[c.case_class] for c in normals}) if width == 1 else len(normals))
    assert len([e for e in events if e[0] == "session"]) == sessions
    assert sorted(value for kind, value in events if kind == "grade") == sorted(expected)
    assert len([e for e in events if e[0] == "wipe"]) == len(entry_ids)  # wipe precedes budget
    verdicts = {v.case_id: v.result for v in store.load_verdicts("limited")}
    assert set(verdicts) == set(results)
    assert all(verdicts[c.id] is Result.INCONCLUSIVE for c in cases if c.id not in expected)
    spans = map(json.loads, store.paths.run_trace("limited").read_text().splitlines())
    execute = [s for s in spans if s.get("kind") == "stage" and s["stage"] == "execute"]
    assert [(x["status"], reason in x["error"]) for x in execute] == [("failed", True)]


def test_real_trigger_undersized_grant_refuses_all_stored_costs_before_run(
    client, scratch_root, monkeypatch,
):
    from run_approval_fixture import grant_live_case_approval
    client.post("/onboard", data={"slug": "demo", "name": "Demo",
                                "base_url": "https://demo.test", "allowed_domains": "demo.test"})
    store = ProjectStore("demo", scratch_root)
    for case in _mixed_tier_cases():
        store.add_case(case)
    events = []
    routes, _ = _patch_tier_execution(monkeypatch, events)
    grant_live_case_approval(store, max_actions=5)
    monkeypatch.setattr(routes, "ulid", lambda: pytest.fail("refused run minted an id"))
    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 403, response.text
    assert "--max-actions 9" in response.text
    assert "--wall-clock 72" in response.text
    assert events == []
    assert not store.paths.runs_dir.exists() or not list(store.paths.runs_dir.iterdir())


def test_parallel_entry_only_rejects_mismatched_budget_before_any_effect(
    client, scratch_root, monkeypatch,
):
    from run_approval_fixture import grant_live_case_approval

    from autotester.browser.secrets import SecretStore
    from autotester.core.paths import ProjectPaths
    from autotester.stages.parallel_run import ParallelPlan
    from autotester.stages.run_budget import RunBudget
    from autotester.ui.run_execution import _run_cases_in_parallel
    client.post("/onboard", data={"slug": "demo", "name": "Demo",
                                "base_url": "https://demo.test", "allowed_domains": "demo.test"})
    store = ProjectStore("demo", scratch_root)
    project = store.load_project()
    events = []
    _, judge = _patch_tier_execution(monkeypatch, events)
    approval = grant_live_case_approval(store, max_actions=1)
    budget = RunBudget(approval)
    mismatched = approval.model_copy(update={"max_actions": 2})
    plan = ParallelPlan(config_ceiling=2, measured_budget=2, n=2,
                        bound_by="config", free_ram_mb=99999.0, cpu_count=8)
    paths = ProjectPaths("demo")
    with pytest.raises(ValueError, match="does not match"):
        _run_cases_in_parallel([_entry_case()], [True], plan, project,
                               SecretStore.load(project, paths.env_file), paths.run_dir("mismatch"),
                               "demo", judge, "mismatch", store, mismatched, budget=budget)
    assert events == [] and budget.actions_used == 0
    assert not paths.run_dir("mismatch").exists()
