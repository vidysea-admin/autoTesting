"""Test doubles for the cross-role runner (T-211): a fake clock and a scripted two-role app.

`FakeClock` advances only when `sleep` is called, so a 5 s window costs no wall time. `ScriptedPort`
plays the role-session port: B's view shows the thing `appears_after_s` after the step that
triggers it (None = never), and can be told to raise on `observe` or on a chosen step. No browser,
no network, no product code (MPI2: the shapes are synthetic).
"""

from __future__ import annotations

from autotester.schema.cross_role_assertion import CrossRoleAssertion, Observation
from autotester.schema.cross_role_scenario import CrossRoleScenario
from autotester.schema.multi_role_enums import AssertChannel, Expectation
from autotester.schema.role_step import RoleStep


class FakeClock:
    """A clock whose time moves only through `sleep`."""

    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


class FrozenClock(FakeClock):
    """A broken clock: `sleep` is recorded but time never moves."""

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


class ScriptedPort:
    """Role A acts at the trigger step; role B's view shows it `appears_after_s` later."""

    def __init__(self, clock: FakeClock, appears_after_s: float | None, *, trigger: str = "act",
                 observe_error: bool = False, failing_step: str | None = None,
                 detail: str | None = None) -> None:
        self.clock = clock
        self.appears_after_s = appears_after_s
        self.trigger = trigger
        self.observe_error = observe_error
        self.failing_step = failing_step
        self.detail = detail
        self.acted_at: float | None = None
        self.performed: list[str] = []
        self.observed = 0

    def perform(self, step: RoleStep) -> None:
        self.performed.append(step.id)
        if step.id == self.failing_step:
            raise RuntimeError("boom with detail that must not be copied")
        if step.id == self.trigger:
            self.acted_at = self.clock.now()

    def observe(self, assertion: CrossRoleAssertion) -> Observation:
        self.observed += 1
        if self.observe_error:
            raise ConnectionError("observer lost the page")
        shown = (self.acted_at is not None and self.appears_after_s is not None
                 and self.clock.now() >= self.acted_at + self.appears_after_s)
        text = self.detail or ("row shown" if shown else "row not shown")
        return Observation(matched=shown, detail=text)


def make_scenario(*, within_s: float, expectation: Expectation = Expectation.PRESENT,
                  channel: AssertChannel = AssertChannel.UI, poll_interval_s: float = 0.5,
                  after_step: str | None = None) -> CrossRoleScenario:
    """Role `teacher` acts, role `parent` observes."""
    return CrossRoleScenario(
        id="grade-publish", title="Teacher publishes, parent sees it", roles=["teacher", "parent"],
        steps=[RoleStep(id="login", role_id="teacher", action="login teacher-portal"),
               RoleStep(id="act", role_id="teacher", action="click #publish")],
        assertions=[CrossRoleAssertion(
            id="parent-sees", observer_role_id="parent", channel=channel, expectation=expectation,
            target="#grades .row", within_s=within_s, poll_interval_s=poll_interval_s,
            after_step=after_step)])
