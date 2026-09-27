"""PR6, a second cause: `session_factory` itself raising (AT-565). Split from
`test_parallel_run.py` at doctor's 300-line cap.

`_run_one` (stages/parallel_run.py) guards `run_fn` against a crash so one
case's failure never aborts its siblings (PR6). Before the AT-565 fix,
`session = session_factory(case)` sat OUTSIDE that guard -- a real
`BrowserSession.start()` failing under N-way concurrency raised straight out
of `run_cases`' `[f.result() for f in futures]`, discarding every sibling's
already-finished result instead of reporting just the one case as ERRORED.
Contract: qa/contracts/parallel-run.md PR6.
"""

from __future__ import annotations

from test_parallel_run import _case, _project

from autotester.schema.case import Case
from autotester.schema.enums import Outcome
from autotester.schema.run import RawResult
from autotester.stages.parallel_run import plan_parallel_run, run_cases


class _CrashingFactorySession:
    """Identity only -- this test never reaches a session's own storage."""

    def __init__(self, owner: str) -> None:
        self.owner = owner

    def close(self) -> None:
        pass


def test_pr6_a_session_factory_that_raises_for_one_case_does_not_abort_siblings() -> None:
    """AT-565: `session_factory(case)` itself can raise -- a real
    `BrowserSession.start()` failing under N-way concurrency, not just the
    `run_fn` body -- and that must be caught and reported as THAT case's own
    ERRORED outcome too, never propagated out of `run_cases`."""
    cases = [_case(i) for i in range(3)]

    def factory(case: Case) -> _CrashingFactorySession:
        if case.title == "case-1":
            raise RuntimeError("boom starting the session")
        return _CrashingFactorySession(case.id)

    def run_fn(case: Case, session: object) -> RawResult:
        return RawResult(case_id=case.id, outcome=Outcome.COMPLETED)

    plan = plan_parallel_run(_project(max_parallel=3), cpu_count=8, free_ram_mb=1e9)
    by_id = {r.case_id: r for r in run_cases(cases, plan, factory, run_fn)}

    crashed = by_id[cases[1].id]
    assert crashed.outcome is Outcome.ERRORED
    assert "RuntimeError" in (crashed.error or "")
    assert by_id[cases[0].id].outcome is Outcome.COMPLETED
    assert by_id[cases[2].id].outcome is Outcome.COMPLETED
