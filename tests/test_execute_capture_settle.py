"""AT-1305: a step screenshot is taken only after the page settles. Contract: execute.md E1-E5.

Live T-136 r3: after the login click, the step-4 frame showed the transient "Logging in..."
button because network-idle had already fired and the SPA was still rendering. The fake page
here reports a pending state for a stretch of (virtual) time, so every test names a scenario.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_execute import FakePage, make_case, session_with_fake_page
from test_parallel_run import _approval

from autotester.browser import evidence
from autotester.schema.enums import Action, EvidenceKind, Outcome
from autotester.schema.flowspec import Step
from autotester.stages.execute import run_case
from autotester.stages.run_budget import RunBudget, RunBudgetExceeded

CLICK = Step(order=1, action=Action.CLICK, target="button[type=submit]")


class PendingPage(FakePage):
    """A page whose DOM reports 'pending' until `pending_ms` of virtual time has elapsed."""

    def __init__(self, url: str, pending_ms: float) -> None:
        super().__init__(url)
        self.pending_ms, self.now, self.events = pending_ms, 0.0, []
        self.evaluated = 0

    def evaluate(self, script: str) -> bool:
        self.evaluated += 1
        return self.now < self.pending_ms

    def wait_for_timeout(self, timeout: int) -> None:
        self.now += timeout
        self.events.append("wait")
        super().wait_for_timeout(timeout)

    def add_style_tag(self, content: str) -> None:
        self.events.append("mask")
        super().add_style_tag(content)

    def screenshot(self, path: str, full_page: bool = False) -> None:
        self.events.append("shot")
        self.shot_pending = self.now < self.pending_ms
        super().screenshot(path, full_page)


def run_click(tmp_path: Path, page: FakePage):
    session = session_with_fake_page(tmp_path)
    session._page = page
    return session, run_case(make_case([CLICK]), session)


def test_login_button_shows_logging_in_for_2s_the_shot_waits_for_it_to_clear(
    tmp_path: Path,
) -> None:
    page = PendingPage("https://app.pathlynks.test/login", pending_ms=2000)
    _, result = run_click(tmp_path, page)

    assert result.outcome is Outcome.COMPLETED
    assert page.shot_pending is False  # the screenshot is of the settled page
    assert sum(page.timeouts) >= 2000
    assert not [e for e in result.evidence if "did not settle" in e.path]


def test_page_that_never_settles_is_still_captured_and_the_step_says_so(tmp_path: Path) -> None:
    page = PendingPage("https://app.pathlynks.test/login", pending_ms=10**9)
    _, result = run_click(tmp_path, page)

    assert result.outcome is Outcome.COMPLETED
    assert page.shots, "an unsettled page must still be captured"
    # hard upper bound: settle()'s own 500 ms grace plus at most CAPTURE_SETTLE_MS of waiting
    assert sum(page.timeouts) == 500 + evidence.CAPTURE_SETTLE_MS
    notes = [e for e in result.evidence if "did not settle" in e.path]
    assert len(notes) == 1 and notes[0].kind is EvidenceKind.DOM and notes[0].step_order == 1
    assert not notes[0].path.startswith("assert ")  # an observation, never a verdict input


def test_already_settled_page_is_captured_with_no_added_wait(tmp_path: Path) -> None:
    page = PendingPage("https://app.pathlynks.test/dashboard", pending_ms=0)
    _, result = run_click(tmp_path, page)

    assert result.outcome is Outcome.COMPLETED
    assert page.evaluated >= 1  # the bound check ran
    # settle()'s own 500 ms grace is the only wait; the capture check adds no sleep and no
    # extra load-state wait before masking and shooting
    assert page.events == ["wait", "mask", "shot"]
    assert page.timeouts == [500]
    assert len(page.settled) == 1


def test_secret_inputs_are_masked_after_the_settle_wait_and_right_before_the_shot(
    tmp_path: Path,
) -> None:
    page = PendingPage("https://app.pathlynks.test/login", pending_ms=1000)
    run_click(tmp_path, page)

    assert page.events[-2:] == ["mask", "shot"]
    assert page.events.index("mask") > max(i for i, e in enumerate(page.events) if e == "wait")
    assert page.styles and "data-autotester-secret" in page.styles[-1]


def test_page_whose_dom_cannot_be_probed_is_captured_without_waiting(tmp_path: Path) -> None:
    """A page without a working evaluate (closed frame, navigation race) never blocks capture."""
    page = FakePage("https://app.pathlynks.test/login")
    page.evaluate = lambda script: (_ for _ in ()).throw(RuntimeError("context destroyed"))
    _, result = run_click(tmp_path, page)

    assert result.outcome is Outcome.COMPLETED
    assert page.shots and not [e for e in result.evidence if "did not settle" in e.path]


def test_typing_into_a_field_does_not_pay_the_capture_settle_check(tmp_path: Path) -> None:
    page = PendingPage("https://app.pathlynks.test/login", pending_ms=10**9)
    session = session_with_fake_page(tmp_path)
    session._page = page
    fill = Step(order=1, action=Action.FILL, target="input[name=email]", value="a@b.com")
    run_case(make_case([fill]), session)

    assert page.evaluated == 0 and sum(page.timeouts) == 0


def test_capture_settle_never_swallows_the_run_budget_deadline(tmp_path: Path, monkeypatch) -> None:
    from autotester.stages import run_budget

    clock = [0.0]
    monkeypatch.setattr(run_budget.time, "monotonic", lambda: clock[0])
    page = PendingPage("https://app.pathlynks.test/login", pending_ms=10**9)
    session = session_with_fake_page(tmp_path)
    session._page = page
    session.budget = RunBudget(_approval(wall_clock_s=1, max_probes=100))

    def expire(ms: int) -> None:
        assert 0 < ms <= 1000
        clock[0] = 1.0

    page.wait_for_timeout = expire
    with pytest.raises(RunBudgetExceeded, match="wall_clock_s"):
        evidence.settle_for_capture(session, "step01-click", 1)
