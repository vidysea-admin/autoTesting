"""AT-888: a TargetClosedError in one serial case is that case's INCONCLUSIVE
("browser closed"), the session is relaunched, and later cases still run; the
relaunch count is bounded per run. Fake session only -- no browser."""

from __future__ import annotations

from types import SimpleNamespace

from autotester.schema.enums import Outcome, Result
from autotester.schema.run import RawResult
from autotester.stages.browser_recovery import BrowserRecovery, closed_verdict, is_browser_closed


class TargetClosedError(Exception):
    pass


class FakeSession:
    def __init__(self, closing: set[int]) -> None:
        self.closing, self.ran, self.relaunched = closing, [], 0

    def relaunch(self, cause: BaseException) -> None:
        self.relaunched += 1

    def run(self, i: int) -> RawResult:
        self.ran.append(i)
        if i in self.closing:
            return RawResult(case_id=f"c{i}", outcome=Outcome.ERRORED,
                             error="TargetClosedError: browser has been closed")
        return RawResult(case_id=f"c{i}", outcome=Outcome.COMPLETED)


def _loop(session: FakeSession, n: int = 4, cap: int = 3):
    rec, out = BrowserRecovery(session, cap), []
    for i in range(1, n + 1):
        if rec.stop_reason:
            out.append((i, "stopped", rec.stop_reason))
            continue
        r = session.run(i)
        if is_browser_closed(r):
            out.append((i, closed_verdict(r, "run-x").result, "closed"))
            rec.recover()
        else:
            out.append((i, r.outcome, None))
    return out


def test_case_2_of_4_closed_later_cases_still_run():
    s = FakeSession({2})
    out = _loop(s)
    assert s.ran == [1, 2, 3, 4]
    assert out[1][1] == Result.INCONCLUSIVE and s.relaunched == 1
    assert out[2][1] == out[3][1] == Outcome.COMPLETED


def test_relaunches_are_bounded_then_named_stop():
    s = FakeSession({1, 2, 3})
    out = _loop(s, n=5, cap=2)
    assert s.relaunched == 2 and s.ran == [1, 2, 3]
    assert "relaunch limit" in out[3][2] and out[4][1] == "stopped"


def test_verdict_cause_is_browser_closed_never_fail():
    r = FakeSession({1}).run(1)
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
