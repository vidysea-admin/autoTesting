"""AT-574: the serial run route (`ui/routes_runs.py::_run_cases_serially`,
the default path, `max_parallel=1`) called `run_and_grade_case` with no
handling at all: one grader/provider exception, or one `run_case` crash,
propagated out of `trigger_run` -> 500, orphaning results and skipping siblings.

Tests fake execution/grading seams, not resilient wrappers or route callers.
Contracts: core-invariants C7; parallel-run PR6; ui-run entry-profile honesty.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_ui_runs import _approve_demo_runs
from test_ui_runs_parallel_trace import _non_entry_case, client, scratch_root

from autotester.core.paths import ProjectPaths
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.stages.parallel_run import ParallelPlan
from autotester.store.project_store import ProjectStore

__all__ = ["client", "scratch_root"]


def _onboard_with_serial_cases(client, scratch_root, n: int) -> tuple[ProjectStore, list[Case]]:
    """Onboard `demo` with `n` non-entry cases at the default `max_parallel`
    (1) -- the serial route."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    cases = [_non_entry_case(i) for i in range(n)]
    for case in cases:
        store.add_case(case)
    return store, cases


def _entry_case() -> Case:
    """A case `_is_entry_case` recognizes: its first step navigates to the
    project's own `base_url` (AT-044)."""
    return Case(
        project="demo", flow_id="flow-entry", kind=CaseKind.BEST, case_class=CaseClass.HAPPY,
        title="entry", steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test")],
    )


def _patch_common(monkeypatch, constructed=None):
    import autotester.ui.routes_runs as routes_runs_module
    from autotester.browser.session import BrowserSession

    if constructed is not None:
        original_init = BrowserSession.__init__

        def tracked_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            constructed.append(self.paths.slug)

        monkeypatch.setattr(BrowserSession, "__init__", tracked_init)
    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", _AvailableProvider)
    return routes_runs_module


def _only_run_id(store: ProjectStore) -> str:
    run_ids = sorted(p.name for p in store.paths.runs_dir.iterdir() if p.is_dir())
    assert len(run_ids) == 1
    return run_ids[0]


def test_a_grader_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run(
    client, scratch_root, monkeypatch,
) -> None:
    """A grading crash preserves the real result, siblings and Run."""
    store, cases = _onboard_with_serial_cases(client, scratch_root, n=3)
    crash_id = cases[1].id
    _patch_common(monkeypatch)

    import autotester.stages.run_case_pipeline as pipeline_module

    def fake_run_case(case_, session):
        return RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)

    def fake_grade(rubric, result, run_id, judge, run_dir=None, secrets=None):
        if result.case_id == crash_id:
            raise RuntimeError("boom grading")
        return Verdict(run_id=run_id, case_id=result.case_id, result=Result.PASS,
                       grader_provider="mock")

    monkeypatch.setattr(pipeline_module, "run_case", fake_run_case)
    monkeypatch.setattr(pipeline_module, "grade", fake_grade)

    _approve_demo_runs(scratch_root)  # AT-570: the live_case approval a run now needs
    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303, response.text
    run_id = _only_run_id(store)
    run = store.load_run(run_id)
    assert run is not None, "the Run record must be saved even though one case's grading crashed"

    results = {r.case_id: r for r in store.load_results(run_id)}
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    assert set(results) == {c.id for c in cases}
    assert set(verdicts) == {c.id for c in cases}

    assert results[crash_id].outcome is Outcome.COMPLETED  # AT-573: never discarded
    assert verdicts[crash_id].result is Result.INCONCLUSIVE
    for case in cases:
        if case.id != crash_id:
            assert results[case.id].outcome is Outcome.COMPLETED
            assert verdicts[case.id].result is Result.PASS


def test_a_run_case_crash_for_one_of_three_serial_cases_still_saves_every_case_and_the_run(
    client, scratch_root, monkeypatch,
) -> None:
    """A serial execution crash must preserve sibling results and the Run."""
    store, cases = _onboard_with_serial_cases(client, scratch_root, n=3)
    crash_id = cases[1].id
    _patch_common(monkeypatch)

    import autotester.stages.run_case_pipeline as pipeline_module

    def fake_run_case(case_, session):
        if case_.id == crash_id:
            raise RuntimeError("boom running the case")
        return RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)

    def fake_grade(rubric, result, run_id, judge, run_dir=None, secrets=None):
        return Verdict(run_id=run_id, case_id=result.case_id, result=Result.PASS,
                       grader_provider="mock")

    monkeypatch.setattr(pipeline_module, "run_case", fake_run_case)
    monkeypatch.setattr(pipeline_module, "grade", fake_grade)

    _approve_demo_runs(scratch_root)  # AT-570: the live_case approval a run now needs
    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303, response.text
    run_id = _only_run_id(store)
    run = store.load_run(run_id)
    assert run is not None, "the Run record must be saved even though one case crashed"

    results = {r.case_id: r for r in store.load_results(run_id)}
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    assert set(results) == {c.id for c in cases}
    assert set(verdicts) == {c.id for c in cases}

    assert results[crash_id].outcome is Outcome.ERRORED
    assert "boom running the case" in (results[crash_id].error or "")
    for case in cases:
        if case.id != crash_id:
            assert results[case.id].outcome is Outcome.COMPLETED
            assert verdicts[case.id].result is Result.PASS


def test_an_entry_case_crash_still_saves_every_case_and_the_run(
    client, scratch_root, monkeypatch,
) -> None:
    """The entry-case path (`_run_entry_case`, shared by both the serial and
    parallel routes) had the same unguarded shape as the old serial loop --
    AT-574's issue calls it out explicitly ("the entry cases have the same
    shape"). `run_case` crashes for the entry case; it must not take the
    non-entry case, or the Run, down with it."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    entry_case = store.add_case(_entry_case())
    other_case = store.add_case(_non_entry_case(0))
    _patch_common(monkeypatch)

    import autotester.stages.run_case_pipeline as pipeline_module

    def fake_run_case(case_, session):
        if case_.id == entry_case.id:
            raise RuntimeError("boom entering")
        return RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)

    def fake_grade(rubric, result, run_id, judge, run_dir=None, secrets=None):
        return Verdict(run_id=run_id, case_id=result.case_id, result=Result.PASS,
                       grader_provider="mock")

    monkeypatch.setattr(pipeline_module, "run_case", fake_run_case)
    monkeypatch.setattr(pipeline_module, "grade", fake_grade)

    _approve_demo_runs(scratch_root)  # AT-570: the live_case approval a run now needs
    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303, response.text
    run_id = _only_run_id(store)
    run = store.load_run(run_id)
    assert run is not None

    results = {r.case_id: r for r in store.load_results(run_id)}
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    assert results[entry_case.id].outcome is Outcome.ERRORED
    assert results[other_case.id].outcome is Outcome.COMPLETED
    assert verdicts[other_case.id].result is Result.PASS


def _entry_cleanup_fault(monkeypatch, profile, mode):
    """Sabotage only the independently bound fixture-owned entry profile."""
    import autotester.ui.run_execution as execution

    original_lstat, original_remove = Path.lstat, execution.shutil.rmtree
    inspections = []
    if mode != "absent":
        profile.mkdir(parents=True)

    def inspect(path, *args, **kwargs):
        if path == profile:
            inspections.append(path)
            if mode == "inspection" or (mode == "post-inspection" and len(inspections) > 1):
                raise PermissionError("fixture inspection denied")
        return original_lstat(path, *args, **kwargs)

    def remove(path, *args, **kwargs):
        if path == profile:
            if mode == "raising":
                raise PermissionError("fixture removal denied")
            if mode == "leftover":
                return None
        return original_remove(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", inspect)
    monkeypatch.setattr(execution.shutil, "rmtree", remove)
    operation = "removal" if mode == "raising" else "inspection"
    return "profile remains" if mode == "leftover" else f"fixture {operation} denied"


@pytest.mark.parametrize("width", [1, 2])
@pytest.mark.parametrize("mode", [
    "raising", "leftover", "inspection", "post-inspection", "healthy", "absent",
])
def test_entry_cleanup_truth_and_siblings(client, scratch_root, monkeypatch, width, mode):
    import autotester.stages.run_case_pipeline as pipeline
    client._transport.raise_server_exceptions = False
    store, siblings = _onboard_with_serial_cases(client, scratch_root, 2)
    entry = store.add_case(_entry_case())
    profile = ProjectPaths("demo-entry-test", scratch_root).profile_dir
    assert profile.resolve().is_relative_to(scratch_root.resolve())
    constructed, executed, callers = [], [], []
    routes = _patch_common(monkeypatch, constructed)
    selected = "_run_cases_serially" if width == 1 else "_run_cases_in_parallel"
    original_caller = getattr(routes, selected)
    def caller(*args, **kwargs):
        callers.append(selected)
        return original_caller(*args, **kwargs)
    def execute(case, session):
        executed.append(case.id)
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)
    def grade(rubric, result, run_id, judge, run_dir=None, secrets=None, saved=pipeline.grade):
        if result.outcome is Outcome.ERRORED:
            return saved(rubric, result, run_id, judge, run_dir=run_dir, secrets=secrets)
        return Verdict(run_id=run_id, case_id=result.case_id, result=Result.PASS,
                       grader_provider="mock")
    monkeypatch.setattr(routes, selected, caller)
    plan = ParallelPlan(width, width, width, "config", 99999, 8)
    monkeypatch.setattr(routes, "plan_parallel_run", lambda *a, **k: plan)
    monkeypatch.setattr(pipeline, "run_case", execute)
    monkeypatch.setattr(pipeline, "grade", grade)
    cause = _entry_cleanup_fault(monkeypatch, profile, mode)
    _approve_demo_runs(scratch_root)
    response = client.post("/projects/demo/run", follow_redirects=False)
    assert response.status_code == 303, response.text
    run_id = _only_run_id(store)
    assert store.load_run(run_id).parallel_n == width
    assert callers == [selected]
    results = {r.case_id: r for r in store.load_results(run_id)}
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    assert set(results) == set(verdicts) == {entry.id, *(c.id for c in siblings)}
    failed = mode not in {"healthy", "absent"}
    assert results[entry.id].outcome is (Outcome.ERRORED if failed else Outcome.COMPLETED)
    assert (verdicts[entry.id].result is Result.PASS) is not failed
    assert (entry.id in executed) is not failed
    assert ("demo-entry-test" in constructed) is not failed
    if failed:
        assert str(profile) in results[entry.id].error
        assert cause in results[entry.id].error
        assert verdicts[entry.id].note == results[entry.id].error
        assert verdicts[entry.id].result is Result.INCONCLUSIVE
        assert verdicts[entry.id].grader_provider == "rule"
    assert all(results[c.id].outcome is Outcome.COMPLETED for c in siblings)
    assert all(verdicts[c.id].result is Result.PASS for c in siblings)
