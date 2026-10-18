"""T-211 (multi-role-platform.md MP13, MP14): role-tagged steps and timed cross-role assertions.

Fixture: teacher publishes at step `act`; the parent's view shows it 2 s later. The clock is a fake
that moves only on `sleep`, so every window below costs no wall time.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from cross_role_fakes import FakeClock, FrozenClock, ScriptedPort, make_scenario

from autotester.schema.cross_role_assertion import AssertVerdict
from autotester.schema.cross_role_scenario import CrossRoleScenario, ScenarioResult
from autotester.schema.multi_role_enums import AssertChannel, Expectation
from autotester.schema.role_step import StepState
from autotester.stages import cross_role_runner
from autotester.stages.cross_role_runner import SystemClock, run_scenario


def _run(scenario: CrossRoleScenario, port: ScriptedPort, clock: FakeClock) -> ScenarioResult:
    return run_scenario(scenario, port, clock, project_slug="demo", run_dir="runs/r1")


def test_mp13_view_updating_after_2s_passes_at_window_5_and_records_observed_time() -> None:
    clock = FakeClock()
    result = _run(make_scenario(within_s=5), ScriptedPort(clock, 2.0), clock)
    outcome = result.assertions[0]
    assert outcome.verdict is AssertVerdict.PASSED
    assert outcome.observed_s == pytest.approx(2.0)
    assert outcome.within_s == 5 and outcome.channel is AssertChannel.UI
    assert result.passed is True


def test_mp13_same_view_fails_at_window_1_with_window_and_last_observation() -> None:
    clock = FakeClock()
    result = _run(make_scenario(within_s=1), ScriptedPort(clock, 2.0), clock)
    outcome = result.assertions[0]
    assert outcome.verdict is AssertVerdict.FAILED
    assert outcome.within_s == 1 and outcome.observed_s is None
    assert outcome.last_observation == "row not shown"
    assert "1" in (outcome.reason or "")
    assert result.passed is False


def test_mp13_steps_run_in_order_each_tagged_with_its_role() -> None:
    clock = FakeClock()
    port = ScriptedPort(clock, 2.0)
    result = _run(make_scenario(within_s=5), port, clock)
    assert port.performed == ["login", "act"]
    assert [(s.step_id, s.role_id, s.state) for s in result.steps] == [
        ("login", "teacher", StepState.OK), ("act", "teacher", StepState.OK)]


def test_mp13_polls_until_the_window_not_sleeping_for_real() -> None:
    clock = FakeClock()
    port = ScriptedPort(clock, None)
    _run(make_scenario(within_s=3, poll_interval_s=1.0), port, clock)
    assert clock.t == pytest.approx(3.0)          # the full window elapsed on the fake clock
    assert port.observed == 4                      # t = 0, 1, 2, 3


def test_mp13_the_assertion_starts_after_its_named_step() -> None:
    clock = FakeClock()
    port = ScriptedPort(clock, 2.0)
    result = _run(make_scenario(within_s=5, after_step="act"), port, clock)
    assert result.assertions[0].verdict is AssertVerdict.PASSED


def test_mp14_absent_passes_only_after_the_full_window_with_no_match() -> None:
    clock = FakeClock()
    port = ScriptedPort(clock, None)
    result = _run(make_scenario(within_s=4, expectation=Expectation.ABSENT), port, clock)
    outcome = result.assertions[0]
    assert outcome.verdict is AssertVerdict.PASSED
    assert outcome.observed_s == pytest.approx(4.0)
    assert clock.t >= 4.0                          # not one poll short of the window


def test_mp14_absent_fails_when_the_thing_shows_up_inside_the_window() -> None:
    clock = FakeClock()
    result = _run(make_scenario(within_s=4, expectation=Expectation.ABSENT),
                  ScriptedPort(clock, 2.0), clock)
    outcome = result.assertions[0]
    assert outcome.verdict is AssertVerdict.FAILED
    assert outcome.observed_s == pytest.approx(2.0)


def test_mp14_absent_is_not_proven_by_an_observer_that_errored() -> None:
    clock = FakeClock()
    port = ScriptedPort(clock, None, observe_error=True)
    result = _run(make_scenario(within_s=2, expectation=Expectation.ABSENT), port, clock)
    outcome = result.assertions[0]
    assert outcome.verdict is AssertVerdict.FAILED
    assert "observation" in (outcome.reason or "")


def test_mp14_present_that_never_matched_fails_with_window_and_last_observation() -> None:
    clock = FakeClock()
    result = _run(make_scenario(within_s=2), ScriptedPort(clock, None), clock)
    outcome = result.assertions[0]
    assert outcome.verdict is AssertVerdict.FAILED
    assert (outcome.within_s, outcome.last_observation) == (2, "row not shown")


def test_a_failed_step_stops_the_scenario_and_marks_the_assertion_not_run() -> None:
    clock = FakeClock()
    port = ScriptedPort(clock, 2.0, failing_step="act")
    result = _run(make_scenario(within_s=5), port, clock)
    assert [s.state for s in result.steps] == [StepState.OK, StepState.FAILED]
    assert result.steps[1].error == "RuntimeError"        # type only, never the message
    assert result.assertions[0].verdict is AssertVerdict.NOT_RUN
    assert port.observed == 0 and result.passed is False


def test_a_clock_that_never_advances_cannot_pass_an_absent_assertion() -> None:
    clock = FrozenClock()
    result = _run(make_scenario(within_s=3, expectation=Expectation.ABSENT),
                  ScriptedPort(clock, None), clock)
    assert result.assertions[0].verdict is AssertVerdict.FAILED
    assert "window" in (result.assertions[0].reason or "")


def test_observation_text_that_looks_personal_is_withheld_from_the_outcome() -> None:
    clock = FakeClock()
    port = ScriptedPort(clock, None, detail="shown to jane.doe@example.com")
    result = _run(make_scenario(within_s=1), port, clock)
    assert "jane" not in (result.assertions[0].last_observation or "")
    assert "jane" not in result.model_dump_json()


def test_system_clock_is_monotonic_and_sleeps() -> None:
    clock = SystemClock()
    before = clock.now()
    clock.sleep(0.05)
    assert clock.now() >= before + 0.03


def test_the_runner_does_not_import_the_session_unit_built_in_parallel() -> None:
    source = Path(cross_role_runner.__file__).read_text(encoding="utf-8")
    assert "multi_role_session" not in source
