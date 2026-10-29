"""Run-teardown stall (stall diagnosis 2026-10-28): phase spans, bounded teardown, save before
close, and housekeeping time held off the approval clock. Fakes only -- no browser, no network."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_parallel_run import _approval, _case

import autotester.ui.run_execution as run_execution
from autotester.browser import teardown
from autotester.core.redact import Redactor
from autotester.core.trace import TraceWriter, phase_summary, read_spans, traced_phase
from autotester.schema.enums import Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.trace import PhaseSpan
from autotester.schema.verdict import Verdict
from autotester.stages import run_budget as rb
from autotester.stages.run_budget import RunBudget


def _trace(tmp_path: Path) -> TraceWriter:
    return TraceWriter(tmp_path / "trace.jsonl", "run-1", Redactor({}))


def _phases(trace: TraceWriter) -> list[PhaseSpan]:
    return [s for s in read_spans(trace.path, include_phases=True) if isinstance(s, PhaseSpan)]


# --- (a) phase rows -------------------------------------------------------------------------

def test_traced_phase_writes_a_row_and_marks_a_raise_not_ok(tmp_path) -> None:
    trace = _trace(tmp_path)
    with traced_phase(trace, "c1", "save_result"):
        pass
    with pytest.raises(ValueError), traced_phase(trace, "c1", "boom", nested=True):
        raise ValueError("x")
    rows = _phases(trace)
    assert [(r.phase, r.ok, r.nested, r.case_id) for r in rows] == [
        ("save_result", True, False, "c1"), ("boom", False, True, "c1")]
    assert all(r.duration_s >= 0 and r.trace_id == "run-1" for r in rows)


def test_traced_phase_without_a_trace_is_a_no_op() -> None:
    with traced_phase(None, None, "anything"):
        pass


def test_read_spans_hides_phases_unless_asked(tmp_path) -> None:
    trace = _trace(tmp_path)
    with traced_phase(trace, None, "p"):
        pass
    assert read_spans(trace.path) == []
    assert len(read_spans(trace.path, include_phases=True)) == 1


def test_phase_summary_totals_by_name_and_unaccounted_ignores_nested(tmp_path) -> None:
    trace = _trace(tmp_path)
    t = time.monotonic()
    trace.record_phase(phase="session_start", started_mono=t - 10)
    trace.record_phase(phase="case_pipeline", started_mono=t - 30)
    trace.record_phase(phase="ocr_sanitize", started_mono=t - 5, nested=True)
    totals, unaccounted = phase_summary(trace.path, wall_s=100.0)
    assert set(totals) == {"session_start", "case_pipeline", "ocr_sanitize"}
    assert totals["case_pipeline"] == pytest.approx(30.0, abs=0.5)
    assert unaccounted == pytest.approx(60.0, abs=1.0)  # 100 - (10 + 30); nested not subtracted
    assert phase_summary(trace.path, wall_s=1.0)[1] == 0.0  # overlap clamps at zero


def test_phase_notes_are_scrubbed(tmp_path) -> None:
    trace = TraceWriter(tmp_path / "t.jsonl", "run-1", Redactor({"K": "hunter2secret"}))
    trace.record_phase(phase="p", started_mono=time.monotonic(), note="hunter2secret leaked")
    assert "hunter2secret" not in trace.path.read_text("utf-8")


# --- (b) bounded teardown -------------------------------------------------------------------

def test_bounded_call_aborts_a_hung_step_and_reports_it() -> None:
    gate = threading.Event()
    started = time.monotonic()
    ok = teardown.bounded_call(lambda: gate.wait(30), timeout_s=0.2, abort=gate.set)
    assert ok is False and time.monotonic() - started < 5


def test_bounded_call_lets_a_fast_step_finish_and_a_real_error_propagate() -> None:
    aborted: list[int] = []
    assert teardown.bounded_call(lambda: None, timeout_s=5, abort=lambda: aborted.append(1)) is True
    assert aborted == []  # a step that finished in time is never aborted

    def boom() -> None:
        raise RuntimeError("real")

    with pytest.raises(RuntimeError, match="real"):
        teardown.bounded_call(boom, timeout_s=5, abort=lambda: None)


def test_cancel_inflight_cancels_the_pending_request_on_a_real_loop() -> None:
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()

    async def request() -> None:
        await asyncio.sleep(30)

    future = asyncio.run_coroutine_threadsafe(request(), loop)
    time.sleep(0.1)
    teardown.cancel_inflight(SimpleNamespace(_loop=loop))
    with pytest.raises(BaseException) as raised:  # concurrent.futures.CancelledError
        future.result(timeout=5)
    assert "Cancelled" in type(raised.value).__name__
    loop.call_soon_threadsafe(loop.stop)


def test_cancel_inflight_ignores_an_owner_with_no_loop() -> None:
    teardown.cancel_inflight(SimpleNamespace())  # a fake context: nothing to cancel, no error


def test_a_hung_context_close_is_abandoned_traced_and_teardown_continues(tmp_path, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(teardown, "cancel_inflight", lambda owner: gate.set())
    swept: list[str] = []
    trace = _trace(tmp_path)
    context = SimpleNamespace(close=lambda: gate.wait(30))  # the idle-Chromium hang
    driver = SimpleNamespace(stop=lambda: swept.append("driver"))
    started = time.monotonic()
    teardown.close_session(context, driver, trace=trace, case_id="c1", timeout_s=0.2,
                           sweep=lambda: swept.append("sweep"))
    assert time.monotonic() - started < 5
    assert swept == ["driver", "sweep"]
    rows = {r.phase: r for r in _phases(trace)}
    assert rows["session_close.context"].ok is False
    assert "abandoned" in (rows["session_close.context"].note or "")
    assert rows["session_close.driver"].ok and rows["session_close.sweep"].ok


def test_a_failing_close_step_is_traced_and_skips_nothing(tmp_path) -> None:
    trace = _trace(tmp_path)
    calls: list[str] = []

    def boom() -> None:
        raise RuntimeError("ctx")

    teardown.close_session(SimpleNamespace(close=boom),
                           SimpleNamespace(stop=lambda: calls.append("stop")), trace=trace)
    assert calls == ["stop"]
    assert {r.phase: r.ok for r in _phases(trace)} == {
        "session_close.context": False, "session_close.driver": True}


# --- (d) housekeeping is not browser time ---------------------------------------------------

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


def test_housekeeping_time_is_not_charged_to_wall_clock(clock) -> None:
    budget = RunBudget(_approval(max_actions=100, wall_clock_s=100.0),
                       housekeeping_allowance_s=1000.0)
    with budget.housekeeping():
        clock.now += 900  # a 900 s Chromium exit
    budget.check()  # still running: 0 s of browser time against 100 s
    assert budget.housekeeping_s_used == pytest.approx(900.0)


def test_housekeeping_beyond_its_allowance_is_charged(clock) -> None:
    budget = RunBudget(_approval(max_actions=100, wall_clock_s=100.0),
                       housekeeping_allowance_s=50.0)
    with budget.housekeeping():
        clock.now += 200  # 150 s over the allowance
    with pytest.raises(rb.RunBudgetExceeded, match="wall_clock_s"):
        budget.check()


def test_overlapping_judge_and_housekeeping_subtract_their_union_once(clock) -> None:
    budget = RunBudget(_approval(max_actions=100, wall_clock_s=100.0),
                       judge_allowance_s=100.0, housekeeping_allowance_s=100.0)
    with budget.judging(), budget.housekeeping():
        clock.now += 60  # one real minute inside BOTH scopes: subtracted once, not twice
    clock.now += 99
    budget.check()  # 99 s acting against 100 s
    clock.now += 2
    with pytest.raises(rb.RunBudgetExceeded, match="wall_clock_s"):  # 101 s acting
        budget.check()


def test_excluded_seconds_report_each_kind_and_the_union(clock) -> None:
    budget = RunBudget(_approval(max_actions=100, wall_clock_s=100.0),
                       judge_allowance_s=100.0, housekeeping_allowance_s=100.0)
    with budget.judging():
        clock.now += 20
        with budget.housekeeping():
            clock.now += 10
        clock.now += 0
    with budget.housekeeping():
        clock.now += 10
    assert budget.excluded_report() == pytest.approx(
        {"judging": 30.0, "housekeeping": 20.0, "total": 40.0})


def test_excluded_total_is_capped_at_the_combined_allowance(clock) -> None:
    budget = RunBudget(_approval(max_actions=100, wall_clock_s=100.0),
                       judge_allowance_s=10.0, housekeeping_allowance_s=10.0)
    with budget.judging():
        clock.now += 50
    report = budget.excluded_report()
    assert report["judging"] == pytest.approx(50.0) and report["total"] == pytest.approx(20.0)


def test_for_cases_sizes_a_housekeeping_allowance_per_case() -> None:
    budget = RunBudget.for_cases(_approval(max_actions=100, wall_clock_s=10.0),
                                 [_case("a"), _case("b")])
    assert budget.housekeeping_allowance_s == 2 * rb.HOUSEKEEPING_ALLOWANCE_PER_CASE_S


# --- (c) entry case saves before teardown ---------------------------------------------------

def test_an_entry_case_is_saved_before_a_slow_close_and_the_close_costs_no_budget(
    tmp_path, monkeypatch,
) -> None:
    events: list[str] = []
    trace = _trace(tmp_path)

    class SlowCloseSession:
        def __init__(self, *_a, **_k) -> None:
            self.state = SimpleNamespace(evidence_prefix=None)
            self.budget = None
            self.trace = None

        def start(self) -> None:
            pass

        def close(self) -> None:
            events.append("close_start")
            context = SimpleNamespace(close=lambda: time.sleep(0.5))  # the slow Chromium exit
            teardown.close_session(context, None, trace=self.trace, budget=self.budget)
            events.append("close_end")

    case = _case(1)  # a real Case: the entry pool reads its class and credentials
    result = RawResult(case_id=case.id, outcome=Outcome.COMPLETED)
    verdict = Verdict(run_id="r1", case_id=case.id, result=Result.PASS, grader_provider="mock")

    class Store:
        def save_result(self, run_id, res) -> None:
            events.append("save_result")

        def save_verdict(self, run_id, ver) -> None:
            events.append("save_verdict")

    monkeypatch.setattr(run_execution, "BrowserSession", SlowCloseSession)
    monkeypatch.setattr(run_execution, "_wipe_entry_profile", lambda _p: None)
    monkeypatch.setattr(run_execution, "_run_and_grade_resilient", lambda *_a: (result, verdict))
    # 0.25 s of approval clock: the 0.5 s close would exhaust it if it were charged
    budget = RunBudget(_approval(max_actions=100, wall_clock_s=0.25),
                       housekeeping_allowance_s=60.0)
    secrets = SimpleNamespace(redactor=lambda: Redactor({}))
    project = Project(slug="p", name="P", base_url="https://p.test", allowed_domains=["p.test"])

    got = run_execution._run_entry_case(case, project, secrets, tmp_path, "p",
                                        SimpleNamespace(trace=trace), "r1", Store(),
                                        budget=budget)

    assert events == ["save_result", "save_verdict", "close_start", "close_end"]
    assert got == (result, verdict)
    budget.check()  # the 0.5 s close consumed none of the 0.25 s clock
    assert budget.stop_reason is None and budget.housekeeping_s_used >= 0.45
    names = {r.phase for r in _phases(trace)}
    assert {"entry_profile_wipe", "session_start", "save_result",
            "session_close.context"} <= names
    totals, unaccounted = phase_summary(trace.path, wall_s=5.0)
    assert totals["session_close.context"] >= 0.45 and 0 <= unaccounted <= 5.0
