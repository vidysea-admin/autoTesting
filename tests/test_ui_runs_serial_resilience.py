"""AT-574: the serial run route (`ui/routes_runs.py::_run_cases_serially`,
the default path, `max_parallel=1`) called `run_and_grade_case` with no
handling at all: one grader/provider exception, or one `run_case` crash,
propagated out of `trigger_run` -> 500, the remaining cases never ran, the
`Run` record was never saved, and the results already saved were orphaned.
The shared `_run_entry_case` helper (used by both the serial and parallel
routes) had the exact same unguarded shape.

The parallel path already got `run_and_grade_case_resilient` in AT-573/
AT-568 (`test_ui_runs_parallel_crash_recovery.py`, `test_run_case_pipeline_
resilient.py`). These tests prove the serial loop and `_run_entry_case` now
go through the same resilient path -- by faking `run_case` and `grade` (the
two seams `run_and_grade_case_resilient` itself calls), never the resilient
wrapper, so a pass here is evidence about the ROUTE's wiring, not a
re-implementation of pipeline behaviour already covered elsewhere. Contract:
qa/contracts/core-invariants.md C7; qa/contracts/parallel-run.md PR6 (the
shape this generalizes to the serial path).
"""

from __future__ import annotations

from test_ui_runs_parallel_trace import _non_entry_case, client, scratch_root

from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
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


def _patch_common(monkeypatch):
    import autotester.ui.routes_runs as routes_runs_module
    from autotester.browser.session import BrowserSession

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
    """Variant 1: grading raises for the middle case only, AFTER `run_case`
    already produced a real COMPLETED result for it. All three cases must
    end up saved with a verdict, the crashed case's real COMPLETED result
    must survive with an INCONCLUSIVE verdict (AT-573's own behaviour,
    reached through the serial route for the first time here), its two
    siblings keep PASS, and the Run itself must be saved (no 500)."""
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
    """Variant 2: `run_case` itself raises for the middle case, before
    `run_and_grade_case_resilient` ever captures a result for it. That case
    must be reported as its own ERRORED result, graded through the same
    `grade_errored_result` path the parallel route uses (AT-568), the other
    two cases keep their real outcomes, and the Run must be saved (no 500)."""
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
