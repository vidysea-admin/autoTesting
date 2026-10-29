"""run-teardown-stall residuals R1 and R2 (qa/verdicts/run-teardown-stall.b.md:35-36).

R1: the shared exclusion clock also pauses while another parallel worker is ACTING on the target.
That is bounded by design (D-112), so it is made observable -- never turned into a different rule:
the run record counts the spends made while an excluded scope was open.
R2: a teardown step the cancel cannot reach (no Playwright loop) used to block the caller for as
long as it wished; it is now abandoned on time, and a cancel that did not take is re-sent.
Fakes only -- no browser, no network."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from test_parallel_run import _approval

from autotester.browser import teardown
from autotester.core.redact import Redactor
from autotester.core.trace import TraceWriter, read_spans
from autotester.schema.trace import PhaseSpan
from autotester.stages.run_budget import RunBudget


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _budget(monkeypatch) -> tuple[RunBudget, _Clock]:
    clock = _Clock()  # a stand-in for run_budget's own `time` only: nothing else sees it
    monkeypatch.setattr("autotester.stages.run_budget.time", SimpleNamespace(monotonic=clock))
    return RunBudget(_approval(max_actions=100, max_probes=100, wall_clock_s=100.0),
                     judge_allowance_s=50.0, housekeeping_allowance_s=50.0), clock


# --- R1: the overlap leak is recorded, the semantics are unchanged --------------------------

def test_a_serial_run_records_no_spend_inside_an_excluded_scope(monkeypatch) -> None:
    budget, clock = _budget(monkeypatch)
    budget.check(actions=1)
    with budget.housekeeping():
        clock.now += 30
    with budget.judging():
        clock.now += 10
    budget.check(actions=2, probes=1)
    assert budget.excluded_report()["acted_during_exclusion"] == 0.0


def test_spends_made_while_a_scope_is_open_are_counted_once_each(monkeypatch) -> None:
    budget, clock = _budget(monkeypatch)
    with budget.housekeeping():  # another worker's teardown...
        budget.check(actions=1)  # ...while this one acts: the clock is paused for it
        budget.try_consume(probes=1)
        budget.check()  # a bare consult spends nothing and is not counted
        clock.now += 20
    budget.check(actions=1)  # outside any scope
    assert budget.excluded_report()["acted_during_exclusion"] == 2.0


def test_a_refused_spend_is_not_counted_and_the_clock_rule_is_unchanged(monkeypatch) -> None:
    budget, clock = _budget(monkeypatch)
    with budget.housekeeping():
        assert budget.try_consume(actions=1000) is False  # over max_actions: refused
        clock.now += 20
    assert budget.excluded_report() == {"judging": 0.0, "housekeeping": 20.0, "total": 20.0,
                                        "acted_during_exclusion": 0.0}
    clock.now += 99  # 99 s acting + 20 s housekeeping (excluded) against wall_clock_s=100
    assert budget.try_consume(actions=1) is True
    clock.now += 2
    assert budget.try_consume(actions=1) is False  # 101 s of acting: still fail-closed


# --- R2: an unreachable teardown step is abandoned, an ineffective cancel is re-sent --------

def _trace(tmp_path: Path) -> TraceWriter:
    return TraceWriter(tmp_path / "trace.jsonl", "run-1", Redactor({}))


def test_a_step_the_cancel_cannot_reach_is_abandoned_not_waited_for(tmp_path: Path) -> None:
    release = threading.Event()  # the wedge: only the test ends it
    trace, order, returned = _trace(tmp_path), [], []
    context = SimpleNamespace(  # no `_loop`: nothing to cancel
        close=lambda: (release.wait(20), returned.append("close")))
    driver = SimpleNamespace(stop=lambda: order.append("driver"))
    try:
        teardown.close_session(context, driver, trace=trace, case_id="c1", timeout_s=0.2,
                               sweep=lambda: order.append("sweep"))
        assert returned == []  # close_session came back while the step was still wedged
        assert order == ["driver", "sweep"]
        rows = {s.phase: s for s in read_spans(trace.path, include_phases=True)
                if isinstance(s, PhaseSpan)}
        assert rows["session_close.context"].ok is False
        assert "abandoned" in (rows["session_close.context"].note or "")
        assert rows["session_close.driver"].ok
    finally:
        release.set()


def test_a_detached_step_that_finishes_in_time_returns_true_and_raises_like_any_step() -> None:
    assert teardown.bounded_call(lambda: None, timeout_s=5, abort=lambda: None, detach=True)

    def boom() -> None:
        raise RuntimeError("ctx")

    try:
        teardown.bounded_call(boom, timeout_s=5, abort=lambda: None, detach=True)
    except RuntimeError as exc:
        assert str(exc) == "ctx"
    else:
        raise AssertionError("an ordinary failure inside the window must propagate")


def test_an_abort_that_did_not_take_is_re_sent_until_the_step_ends() -> None:
    ended, sent = threading.Event(), []

    def abort() -> None:
        sent.append(1)
        if len(sent) == 3:  # the third cancel is the one that takes
            ended.set()

    finished = teardown.bounded_call(lambda: ended.wait(20), timeout_s=0.05, abort=abort)
    assert finished is False and len(sent) == 3


def test_a_playwright_owner_still_runs_in_the_calling_thread(tmp_path: Path) -> None:
    """Sync-API objects are thread-bound: a reachable loop keeps the in-thread step."""
    loop = asyncio.new_event_loop()
    seen: list[threading.Thread] = []
    owner = SimpleNamespace(_loop=loop, close=lambda: seen.append(threading.current_thread()))
    try:
        teardown.close_session(owner, None, trace=_trace(tmp_path), timeout_s=5)
    finally:
        loop.close()
    assert seen == [threading.current_thread()]


def test_a_detached_step_does_not_hold_the_caller_past_the_timeout() -> None:
    release = threading.Event()
    started = time.monotonic()
    try:
        assert teardown.bounded_call(lambda: release.wait(20), timeout_s=0.1,
                                     abort=lambda: None, detach=True) is False
        assert time.monotonic() - started < 15
    finally:
        release.set()
