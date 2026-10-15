"""AT-888: a TargetClosedError in one serial case is that case's INCONCLUSIVE
("browser closed"), the session is relaunched, and later cases still run; the
relaunch count is bounded per run. Fake session only -- no browser."""

from __future__ import annotations

from types import SimpleNamespace
from typing import ClassVar

from autotester.schema.enums import Outcome, Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
from autotester.stages.browser_recovery import closed_verdict


class TargetClosedError(Exception):
    pass


class FakeSession:
    """Stands in for BrowserSession inside the real `_run_cases_serially`."""
    instances: ClassVar[list] = []

    def __init__(self, *a, **k) -> None:
        self.relaunched, self.budget = 0, None
        FakeSession.instances.append(self)

    def start(self):
        return self

    def close(self) -> None:
        pass

    def relaunch(self, cause: BaseException) -> None:
        self.relaunched += 1


class FakeStore:
    def __init__(self) -> None:
        self.results, self.verdicts = {}, {}

    def save_result(self, run_id, r) -> None:
        self.results[r.case_id] = r

    def save_verdict(self, run_id, v) -> None:
        self.verdicts[v.case_id] = v


def _drive(monkeypatch, closing: set[str], n: int = 4):
    import autotester.ui.run_execution as rx
    from autotester.stages import browser_recovery as br

    ran: list[str] = []

    def fake_pipeline(case, session, judge, run_id, store):
        ran.append(case.id)
        if case.id in closing:
            raise TargetClosedError("Target page, context or browser has been closed")
        return (RawResult(case_id=case.id, outcome=Outcome.COMPLETED),
                br.closed_verdict(RawResult(case_id=case.id, outcome=Outcome.COMPLETED), "r"))

    def fake_grade(case, result, judge, run_id, store):
        return Verdict(run_id=run_id, case_id=case.id, result=Result.INCONCLUSIVE,
                       grader_provider="rule", note=result.error)

    FakeSession.instances = []
    monkeypatch.setattr(rx, "BrowserSession", FakeSession)
    monkeypatch.setattr(rx, "run_and_grade_case_resilient", fake_pipeline)
    monkeypatch.setattr(rx, "grade_errored_result", fake_grade)
    cases = [SimpleNamespace(id=f"c{i}") for i in range(1, n + 1)]
    store = FakeStore()
    secrets = SimpleNamespace(redactor=lambda: SimpleNamespace(scrub=lambda t: t))
    budget = SimpleNamespace(check_start=lambda: None, check=lambda: None)
    rx._run_cases_serially(cases, [False] * n, None, secrets, None, None, "demo", None, "r",
                           store, budget=budget)
    return ran, store, FakeSession.instances[0]


def test_case_2_of_4_closed_later_cases_still_run(monkeypatch):
    ran, store, session = _drive(monkeypatch, {"c2"})
    assert ran == ["c1", "c2", "c3", "c4"]
    assert store.verdicts["c2"].result == Result.INCONCLUSIVE
    assert "browser closed" in store.verdicts["c2"].note
    assert session.relaunched == 1
    assert store.results["c3"].outcome == store.results["c4"].outcome == Outcome.COMPLETED


def test_relaunches_are_capped_then_named_stop(monkeypatch):
    ran, store, session = _drive(monkeypatch, {"c1", "c2", "c3", "c4"}, n=6)
    assert session.relaunched == 3 and ran == ["c1", "c2", "c3", "c4"]
    assert "relaunch limit" in store.results["c5"].error
    assert "relaunch limit" in store.results["c6"].error


def test_verdict_cause_is_browser_closed_never_fail():
    r = RawResult(case_id='c1', outcome=Outcome.ERRORED, error='TargetClosedError: x')
    v = closed_verdict(r, "run-x")
    assert v.result == Result.INCONCLUSIVE and "browser closed" in v.note


def test_session_cap_latches_restore_error():
    from autotester.browser.video import SessionRestoreError, VideoMixin
    m = SimpleNamespace(max_relaunches=0, secrets=SimpleNamespace(
        redactor=lambda: SimpleNamespace(scrub=lambda t: t)))
    m._scrubbed = lambda t: t
    try:
        VideoMixin._restart_session(m, RuntimeError("x"))
    except SessionRestoreError as e:
        assert "relaunch limit" in str(e)
    else:
        raise AssertionError
