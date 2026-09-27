"""AT-568 (fix cycle 2): the live parallel route must survive a case crash.

Split from `test_ui_runs_parallel_trace.py` (which already covers AT-562/
AT-564's happy-path wiring) to keep each file under doctor's 300-line cap.

`_run_cases_in_parallel` used to index its verdict-capture dict blindly
(`verdicts[result.case_id]`), but a verdict is only ever captured when
`run_and_grade_case_resilient` (AT-573's own resilient wrapper, cycle 3;
was `run_and_grade_case` in cycle 2) runs to completion inside
`_run_and_grade`. Two things can stop that from happening for one case out
of N without stopping the others (PR6's whole point): the case's own
`session_factory` call can raise (the AT-565 shape, now caught INSIDE
`run_cases`), or `run_and_grade_case_resilient` itself can raise
unexpectedly. Either way, `run_cases` still reports that case as its own
ERRORED `RawResult` (PR6), but the route's blind dict index then raised
`KeyError`, which lost every later case's save and the `Run` itself, and
500'd the whole request. A genuine grader/provider failure AFTER a
COMPLETED execution is `run_and_grade_case_resilient`'s own concern
(AT-573, tested in `test_run_case_pipeline.py` and
`test_ui_runs_parallel_grader_failure.py`) — it no longer reaches this
fallback at all, since it is caught and turned into an INCONCLUSIVE verdict
before this file's `_run_and_grade` ever returns. Contract:
qa/contracts/parallel-run.md PR6.
"""

from __future__ import annotations

from test_ui_runs_parallel_trace import _non_entry_case, client, scratch_root

from autotester.schema.enums import Outcome, Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.stages.parallel_run import ParallelPlan
from autotester.store.project_store import ProjectStore

__all__ = ["client", "scratch_root"]


def _onboard_with_parallel_cases(client, scratch_root, n: int, max_parallel: int):
    """Onboard `demo` with `n` non-entry cases and `max_parallel` configured."""
    client.post("/onboard", data={
        "slug": "demo", "name": "Demo", "base_url": "https://demo.test",
        "allowed_domains": "demo.test",
    })
    store = ProjectStore("demo", scratch_root)
    project = store.load_project()
    assert project is not None
    store.save_project(project.model_copy(update={"max_parallel": max_parallel}))
    cases = [_non_entry_case(i) for i in range(n)]
    for case in cases:
        store.add_case(case)
    return store, cases


def _patch_common(monkeypatch, fake_plan: ParallelPlan):
    import autotester.ui.routes_runs as routes_runs_module
    import autotester.ui.run_execution as run_execution_module
    from autotester.browser.session import BrowserSession

    monkeypatch.setattr(BrowserSession, "start", lambda self: self)
    monkeypatch.setattr(BrowserSession, "close", lambda self: None)

    class _AvailableProvider:
        def available(self) -> bool:
            return True

    monkeypatch.setattr(routes_runs_module, "LangChainFallbackProvider", _AvailableProvider)
    monkeypatch.setattr(routes_runs_module, "plan_parallel_run", lambda project_: fake_plan)
    # AT-567: _run_cases_in_parallel/_run_and_grade_resilient now live in
    # ui/run_execution.py, so `default_session_factory`/`run_and_grade_case_
    # resilient` must be patched there -- that is where those names are
    # actually looked up at call time. Callers patch those two on the
    # returned module; `routes_runs_module` is returned for the two names
    # above, which stay in `routes_runs.py` unmoved.
    return run_execution_module


def test_a_session_factory_crash_for_one_case_still_saves_every_case_and_the_run(
    client, scratch_root, monkeypatch,
) -> None:
    """The AT-565 shape at the route level: `default_session_factory`'s own
    session construction raises for one of three cases. All three must end
    up with a saved result and verdict, the Run must be saved (no 500), the
    crashed case must be ERRORED, and its two siblings must keep their real
    COMPLETED outcome."""
    store, cases = _onboard_with_parallel_cases(client, scratch_root, n=3, max_parallel=2)
    crash_id = cases[1].id
    fake_plan = ParallelPlan(config_ceiling=2, measured_budget=2, n=2, bound_by="config",
                             free_ram_mb=99999.0, cpu_count=8)
    run_execution_module = _patch_common(monkeypatch, fake_plan)

    def fake_default_session_factory(project_, secrets_, run_dir_):
        def factory(case):
            if case.id == crash_id:
                raise RuntimeError("boom starting the session")
            return object()
        return factory

    def fake_run_and_grade_case_resilient(case_, session, judge_, run_id, store_):
        result = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)
        verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                           grader_provider="mock")
        return result, verdict

    monkeypatch.setattr(run_execution_module, "default_session_factory",
                        fake_default_session_factory)
    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        fake_run_and_grade_case_resilient)

    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303, response.text
    run_ids = sorted(p.name for p in store.paths.runs_dir.iterdir() if p.is_dir())
    assert len(run_ids) == 1
    run_id = run_ids[0]

    run = store.load_run(run_id)
    assert run is not None, "the Run record must be saved even though one case crashed"

    results = {r.case_id: r for r in store.load_results(run_id)}
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    assert set(results) == {c.id for c in cases}
    assert set(verdicts) == {c.id for c in cases}

    assert results[crash_id].outcome is Outcome.ERRORED
    assert "boom starting the session" in (results[crash_id].error or "")
    for case in cases:
        if case.id != crash_id:
            assert results[case.id].outcome is Outcome.COMPLETED
            assert verdicts[case.id].result is Result.PASS


def test_run_and_grade_case_resilient_itself_raising_still_saves_every_case_and_the_run(
    client, scratch_root, monkeypatch,
) -> None:
    """Defense in depth for the AT-568 fallback: even if the resilient
    wrapper itself raises unexpectedly for one case (a bug in it, not the
    grader-after-COMPLETED shape AT-573 already handles inside it) -- never
    a `session_factory` crash -- every case must still be saved, the Run
    must be saved, no 500. AT-573's own "grader fails, real result kept"
    behavior is tested directly in `test_run_case_pipeline.py`
    (`run_and_grade_case_resilient` unit tests) and
    `test_ui_runs_parallel_grader_failure.py` (route level)."""
    store, cases = _onboard_with_parallel_cases(client, scratch_root, n=3, max_parallel=2)
    crash_id = cases[2].id
    fake_plan = ParallelPlan(config_ceiling=2, measured_budget=2, n=2, bound_by="config",
                             free_ram_mb=99999.0, cpu_count=8)
    run_execution_module = _patch_common(monkeypatch, fake_plan)

    def fake_run_and_grade_case_resilient(case_, session, judge_, run_id, store_):
        if case_.id == crash_id:
            raise RuntimeError("boom inside the resilient wrapper itself")
        result = RawResult(case_id=case_.id, outcome=Outcome.COMPLETED)
        verdict = Verdict(run_id=run_id, case_id=case_.id, result=Result.PASS,
                           grader_provider="mock")
        return result, verdict

    monkeypatch.setattr(run_execution_module, "run_and_grade_case_resilient",
                        fake_run_and_grade_case_resilient)

    response = client.post("/projects/demo/run", follow_redirects=False)

    assert response.status_code == 303, response.text
    run_ids = sorted(p.name for p in store.paths.runs_dir.iterdir() if p.is_dir())
    assert len(run_ids) == 1
    run_id = run_ids[0]

    run = store.load_run(run_id)
    assert run is not None

    results = {r.case_id: r for r in store.load_results(run_id)}
    verdicts = {v.case_id: v for v in store.load_verdicts(run_id)}
    assert set(results) == {c.id for c in cases}
    assert set(verdicts) == {c.id for c in cases}

    assert results[crash_id].outcome is Outcome.ERRORED
    assert "boom inside the resilient wrapper itself" in (results[crash_id].error or "")
    # the synthetic grade_errored_result path never calls the judge, so this
    # is graded deterministically -- INCONCLUSIVE, not a guess at PASS/FAIL
    assert verdicts[crash_id].result is Result.INCONCLUSIVE
    for case in cases:
        if case.id != crash_id:
            assert results[case.id].outcome is Outcome.COMPLETED
            assert verdicts[case.id].result is Result.PASS
