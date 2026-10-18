"""The cross-role runner: role-tagged steps, then timed assertions polled to a window (MP13, MP14).

One job: run a `CrossRoleScenario` against a `RoleSessionPort` (`schema/oracle_context.py`) with an
injectable clock, and return a `ScenarioResult`. T-210's multi-role session plugs in as the port
later; nothing here imports it, and no browser, network or sleep is needed to test the runner.

Time rules, all measured on the injected clock:
  * Each assertion has its own window, starting when it is first looked at (after its `after_step`,
    or after the last step) and lasting `within_s`. The last look is at the window's end, inclusive,
    so a view that updates at exactly `within_s` still counts as in time.
  * `present`: poll until it matches (pass, `observed_s` = seconds into the window) or the window
    ends (fail, recording the window and the last observation).
  * `absent`: poll the whole window. It passes only when the full window elapsed with no match; a
    match at any point fails with the time it appeared. An observation that raised proves nothing,
    so it fails the assertion instead of counting as "not there".
  * A step that raises stops the scenario (later steps are `not_run`) and its assertions are
    `not_run`; only the exception type is recorded.
The poll count is bounded, so a clock that never advances ends in a failure, never a hang.
"""

from __future__ import annotations

import importlib
import math
import time
from collections.abc import Iterable, Sequence
from typing import Protocol

from autotester.schema.cross_role_assertion import (
    DETAIL_MAX,
    AssertionOutcome,
    AssertVerdict,
    CrossRoleAssertion,
    Observation,
)
from autotester.schema.cross_role_scenario import CrossRoleScenario, ScenarioResult
from autotester.schema.leak_evidence import contains_personal_shape
from autotester.schema.multi_role_enums import Expectation, OracleName
from autotester.schema.oracle_context import OracleContext, RoleSessionPort
from autotester.schema.role_step import RoleStep, StepOutcome, StepState
from autotester.stages.oracle_registry import Importer, run_oracles

WITHHELD = "[withheld: looks like personal data]"
_POLL_SLACK = 10


class Clock(Protocol):
    """Time source and sleeper; tests pass a fake that advances only when slept."""

    def now(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    """Real time: `time.perf_counter` (monotonic, finer than `time.monotonic` on Windows)."""

    def now(self) -> float:
        return time.perf_counter()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def _safe(text: str | None) -> str | None:
    """Observation text kept short and never personal-shaped (MPI1)."""
    if text is None:
        return None
    return WITHHELD if contains_personal_shape(text) else text[:DETAIL_MAX]


def _look(port: RoleSessionPort, assertion: CrossRoleAssertion) -> Observation | None:
    try:
        return port.observe(assertion)
    except Exception:
        return None


def _verdict(a: CrossRoleAssertion, last: Observation | None, elapsed: float,
             matched: bool, errored: bool) -> AssertionOutcome:
    seen = _safe(last.detail if last else None)
    done = {"assertion_id": a.id, "observer_role_id": a.observer_role_id, "channel": a.channel,
            "expectation": a.expectation, "within_s": a.within_s, "last_observation": seen}
    at = round(elapsed, 3)
    window = f"{a.within_s:g}s window"
    if a.expectation is Expectation.PRESENT:
        if matched:
            return AssertionOutcome(**done, verdict=AssertVerdict.PASSED, observed_s=at)
        return AssertionOutcome(**done, verdict=AssertVerdict.FAILED,
                                reason=f"never matched within the {window}")
    if matched:
        return AssertionOutcome(**done, verdict=AssertVerdict.FAILED, observed_s=at,
                                reason=f"appeared at {at:g}s, inside the {window}")
    if errored:
        return AssertionOutcome(**done, verdict=AssertVerdict.FAILED,
                                reason="observation failed, so absence is not proven")
    if elapsed < a.within_s:
        return AssertionOutcome(**done, verdict=AssertVerdict.FAILED,
                                reason=f"the {window} did not elapse")
    return AssertionOutcome(**done, verdict=AssertVerdict.PASSED, observed_s=at)


def poll_assertion(a: CrossRoleAssertion, port: RoleSessionPort, clock: Clock) -> AssertionOutcome:
    """Look at the channel until the assertion is decided or its window has elapsed."""
    start = clock.now()
    last: Observation | None = None
    elapsed, matched, errored = 0.0, False, False
    for _ in range(math.ceil(a.within_s / a.poll_interval_s) + _POLL_SLACK):
        seen = _look(port, a)
        elapsed = clock.now() - start
        errored = errored or seen is None
        last = seen or last
        matched = bool(seen and seen.matched)
        if matched or elapsed >= a.within_s:
            break
        clock.sleep(min(a.poll_interval_s, a.within_s - elapsed))
    return _verdict(a, last, elapsed, matched, errored)


def _not_run(a: CrossRoleAssertion, why: str) -> AssertionOutcome:
    return AssertionOutcome(
        assertion_id=a.id, observer_role_id=a.observer_role_id, channel=a.channel,
        expectation=a.expectation, within_s=a.within_s, verdict=AssertVerdict.NOT_RUN, reason=why)


def _perform(step: RoleStep, port: RoleSessionPort) -> StepOutcome:
    try:
        port.perform(step)
    except Exception as exc:
        return StepOutcome(step_id=step.id, role_id=step.role_id, state=StepState.FAILED,
                           error=type(exc).__name__)
    return StepOutcome(step_id=step.id, role_id=step.role_id, state=StepState.OK)


def _drive(scenario: CrossRoleScenario, port: RoleSessionPort, clock: Clock,
           ) -> tuple[list[StepOutcome], dict[str, AssertionOutcome]]:
    steps: list[StepOutcome] = []
    outcomes: dict[str, AssertionOutcome] = {}
    failed: str | None = None
    for step in scenario.steps:
        if failed is not None:
            steps.append(StepOutcome(step_id=step.id, role_id=step.role_id,
                                     state=StepState.NOT_RUN))
            continue
        steps.append(_perform(step, port))
        if steps[-1].state is StepState.FAILED:
            failed = step.id
            continue
        for a in scenario.assertions:
            if a.after_step == step.id:
                outcomes[a.id] = poll_assertion(a, port, clock)
    for a in scenario.assertions:
        if a.id in outcomes:
            continue
        if failed is not None:
            outcomes[a.id] = _not_run(a, f"step {failed} failed first")
        else:
            outcomes[a.id] = poll_assertion(a, port, clock)
    return steps, outcomes


def run_scenario(scenario: CrossRoleScenario, port: RoleSessionPort, clock: Clock | None = None,
                 *, project_slug: str, run_dir: str, platform_ids: Sequence[str] = (),
                 oracles: Iterable[OracleName] = (),
                 importer: Importer = importlib.import_module) -> ScenarioResult:
    """Run the steps, decide every assertion, then run the selected oracles and summarise all."""
    steps, by_id = _drive(scenario, port, clock or SystemClock())
    ordered = [by_id[a.id] for a in scenario.assertions]
    context = OracleContext(
        project_slug=project_slug, run_dir=run_dir, scenario_id=scenario.id,
        role_ids=list(scenario.roles), platform_ids=list(platform_ids), steps=list(scenario.steps),
        assertion_outcomes=ordered, port=port)
    summary, findings = run_oracles(context, oracles, importer)
    return ScenarioResult(scenario_id=scenario.id, steps=steps, assertions=ordered,
                          oracle_summary=summary, findings=findings)
