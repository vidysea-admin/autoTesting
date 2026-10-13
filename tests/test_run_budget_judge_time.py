"""RUN_BUDGET judge-time accounting: serial model grading no longer starves later cases.

The approval's `wall_clock_s` bounds time the BROWSER acts on the target; judge latency is
held in a separate, bounded allowance (real PathLynks run: 13 of 30 cases never launched
because grading ate the 600 s clock). Browser time stays capped, total stays bounded, and
unrun cases still fail closed with reason `wall_clock_s` (INCONCLUSIVE upstream).

Fakes and a patched monotonic clock only -- no browser, no sleeping.
"""

from __future__ import annotations

import pytest
from test_parallel_run import _approval, _case

from autotester.stages import run_budget as rb
from autotester.stages.run_budget import RunBudget, RunBudgetExceeded, wall_clock_request_s


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch):
    c = _Clock()
    monkeypatch.setattr(rb.time, "monotonic", c)
    return c


def _budget(clock, wall: float, allowance: float) -> RunBudget:
    return RunBudget(_approval(max_actions=1000, wall_clock_s=wall), judge_allowance_s=allowance)


def test_judge_latency_does_not_starve_later_cases(clock):
    budget = _budget(clock, wall=100.0, allowance=500.0)
    for _ in range(10):  # 10 cases: 5 s browser + 30 s judge each = 350 s total > 100 s
        budget.check_start()
        clock.now += 5
        with budget.judging():
            clock.now += 30
    budget.check()  # 50 s of browser time against 100 s: still running
    assert budget.judge_s_used == pytest.approx(300.0)


def test_browser_time_is_still_capped(clock):
    budget = _budget(clock, wall=100.0, allowance=500.0)
    with budget.judging():
        clock.now += 200
    clock.now += 100  # browser time reaches the grant
    with pytest.raises(RunBudgetExceeded, match="wall_clock_s"):
        budget.check()
    assert budget.stop_reason == "wall_clock_s"


def test_judge_time_beyond_allowance_is_charged_to_the_clock(clock):
    budget = _budget(clock, wall=100.0, allowance=40.0)
    with budget.judging():
        clock.now += 150  # 40 s excluded, 110 s charged -> over the 100 s grant
    with pytest.raises(RunBudgetExceeded, match="wall_clock_s"):
        budget.check()
    # total real time is bounded by wall_clock_s + allowance
    assert clock.now - 1000.0 < 100.0 + 40.0 + 11.0


def test_in_flight_judge_time_is_excluded_and_overlap_counts_once(clock):
    budget = _budget(clock, wall=100.0, allowance=500.0)
    with budget.judging(), budget.judging():  # two parallel workers grading at once
        clock.now += 60
        budget.check()  # excluded while in flight
    assert budget.judge_s_used == pytest.approx(60.0)


def test_no_allowance_keeps_the_old_total_semantics(clock):
    budget = RunBudget(_approval(max_actions=10, wall_clock_s=100.0))
    with budget.judging():
        clock.now += 100
    with pytest.raises(RunBudgetExceeded):
        budget.check()


def test_request_includes_bounded_judge_allowance():
    cases = [_case(1), _case(2)]
    assert wall_clock_request_s(cases) == (
        sum(rb.action_cost(c) for c in cases) * rb.WALL_CLOCK_PER_ACTION_S
        + rb.judge_allowance_s(cases))
    assert rb.judge_allowance_s(cases) == 2 * rb.JUDGE_ALLOWANCE_PER_CASE_S


def test_negative_allowance_rejected():
    with pytest.raises(ValueError):
        RunBudget(_approval(max_actions=1, wall_clock_s=1.0), judge_allowance_s=-1.0)


def test_pipeline_grades_inside_the_judging_scope(monkeypatch):
    from autotester.stages import run_case_pipeline as rcp

    events: list[str] = []

    class _B:
        def judging(self):
            from contextlib import contextmanager

            @contextmanager
            def cm():
                events.append("enter")
                yield
                events.append("exit")
            return cm()

    class _S:
        budget = _B()

    with rcp._judging(_S()):
        events.append("grade")
    assert events == ["enter", "grade", "exit"]
    with rcp._judging(object()):  # no budget: a no-op, never an error
        pass
