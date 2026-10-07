"""The deterministic assertion layer (D-032/AT-540).

Split from `test_execute.py` at the 300-line cap. What it pins:
- a step whose declared expectation (url/visible_text/absent_text/dom_asserts)
  never holds makes `run_case` return `Outcome.ASSERTION_FAILED` — an
  observation, never a silent COMPLETED, and never a grade (C7: the grader
  still owns the verdict);
- each evaluated field records an explicit `assert <field>: met|unmet` DOM
  evidence item, so the grader has deterministic facts to weigh;
- a bare `Action.ASSERT` with nothing declared is harmless;
- an ERRORED mid-step exception still outranks an earlier unmet assertion.

Contract: qa/contracts/execute.md (E1 as amended by D-032, checker pending).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_execute import LOGIN, make_case, session_with_fake_page
from test_parallel_run import _approval

from autotester.browser import assertions
from autotester.schema.enums import Action, EvidenceKind, Outcome
from autotester.schema.flowspec import ExpectedState, Step
from autotester.stages.execute import run_case
from autotester.stages.run_budget import RunBudget


@pytest.mark.parametrize("brake", ["actions", "empty", "capture", "wait", "probes"])
def test_executor_shared_brakes_stop_real_actions_and_final_completion(
    tmp_path, monkeypatch, brake,
):
    from autotester.stages import run_budget

    clock = [0.0]
    monkeypatch.setattr(run_budget.time, "monotonic", lambda: clock[0])
    session = session_with_fake_page(tmp_path)
    session.budget = RunBudget(_approval(max_actions=1, max_probes=0, wall_clock_s=1))
    page = session.page
    shot = page.screenshot
    def capture(**kwargs):
        assert 0 < kwargs.pop("timeout") <= 1000
        shot(**kwargs)
        if brake == "capture":
            clock[0] = 1.0
    page.screenshot = capture
    def wait(ms):
        assert 0 < ms <= 1000
        if brake == "wait":
            clock[0] = 1.0
    page.wait_for_timeout = wait
    steps = [Step(order=1, action=Action.WAIT, target="", value="5000")]
    if brake == "actions":
        steps.append(Step(order=2, action=Action.WAIT, target="", value="5000"))
    if brake == "probes":
        steps = [Step(order=1, action=Action.ASSERT, target="", expected={"url": "login"})]
    case = make_case([] if brake == "empty" else steps)
    result = run_case(case, session)
    if brake == "empty":
        assert result.outcome is Outcome.COMPLETED and session.budget.actions_used == 1
        result = run_case(case, session)
    assert result.outcome is Outcome.ERRORED
    reason = "max_probes" if brake == "probes" else (
        "max_actions" if brake in ("actions", "empty") else "wall_clock_s")
    assert reason in result.error and session.budget.actions_used == 1


def test_an_unmet_declared_expectation_is_assertion_failed_with_evidence(
    tmp_path: Path,
) -> None:
    """D-032/AT-540: a step whose expected.visible_text never appears is an
    ASSERTION_FAILED observation with the unmet assert recorded as DOM
    evidence — never a silent COMPLETED (the old `settle`-returns-either-way
    behaviour), and never a grade (the grader still owns the verdict)."""
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.CLICK, target="button[type=submit]",
             expected={"visible_text": ["Dashboard"]}),
    ]
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Invalid credentials"  # the declared text never arrives

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.ASSERTION_FAILED
    unmet = [e for e in result.evidence
             if e.kind is EvidenceKind.DOM and e.path.startswith("assert ")
             and "unmet" in e.path]
    assert unmet, "the unmet expectation was never recorded as evidence"
    assert "Dashboard" in unmet[0].path


def test_absent_text_and_dom_asserts_are_evaluated(tmp_path: Path) -> None:
    """`absent_text` must be met only when the text is truly absent;
    `dom_asserts` must be met only when the selector exists."""
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.CLICK, target="button[type=submit]",
             expected={"absent_text": ["Invalid credentials"],
                       "dom_asserts": ["div.error-banner"]}),
    ]
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Invalid credentials"  # the absent_text IS present
    # the dom_asserts selector genuinely exists here -- this test's own
    # dom_asserts row must read met, or it isn't isolating anything (AT-548)
    result = run_case(make_case(steps), session)
    assert result.outcome is Outcome.ASSERTION_FAILED  # absent_text alone fails the run
    assert any("absent_text: unmet" in e.path for e in result.evidence
               if e.kind is EvidenceKind.DOM)
    assert any("dom_asserts: met" in e.path for e in result.evidence
               if e.kind is EvidenceKind.DOM)


def test_dom_asserts_is_met_only_when_the_selector_genuinely_exists(tmp_path: Path) -> None:
    """AT-548: the checker's cycle-1 finding -- the fixture had no `count()`,
    so `selector_exists` could only ever read False (unmet) and this
    capability had no met path at all. `FakeLocator.count()` now reports a
    selector present unless the test marks it `missing_selectors`, so both
    directions are reachable: forcing `selector_exists` to always return
    True (the cycle-1 falsifying edit) must redden the second case below."""
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.CLICK, target="button[type=submit]",
             expected={"dom_asserts": ["div.success-banner"]}),
    ]
    session = session_with_fake_page(tmp_path)  # div.success-banner exists (default)

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    assert any("dom_asserts: met" in e.path for e in result.evidence
               if e.kind is EvidenceKind.DOM)


def test_dom_asserts_is_unmet_when_the_selector_is_absent(tmp_path: Path) -> None:
    """The other half of AT-548: a genuinely-missing selector must flip the
    run to ASSERTION_FAILED, not read as met by default."""
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.CLICK, target="button[type=submit]",
             expected={"dom_asserts": ["div.error-banner"]}),
    ]
    session = session_with_fake_page(tmp_path)
    session.page.missing_selectors.add("div.error-banner")

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.ASSERTION_FAILED
    assert any("dom_asserts: unmet" in e.path for e in result.evidence
               if e.kind is EvidenceKind.DOM)


def test_absent_text_on_an_unreadable_page_fails_safe_not_silently_met(tmp_path: Path) -> None:
    """AT-551: `body_text` raising (a crashed page) used to collapse to "",
    and an absent_text expectation reads "the text is absent from ''" as
    met -- the executor would report a clean pass on a page it never
    actually saw. It must fail safe: unmet, never a silent COMPLETED.
    Crashes only the body read (not the click) -- a locator override local
    to this test, no shared-fixture change needed for a single scenario."""
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.CLICK, target="button[type=submit]",
             expected={"absent_text": ["Invalid credentials"]}),
    ]
    session = session_with_fake_page(tmp_path)
    real_locator = session.page.locator

    def crashing_body_locator(selector: str):
        if selector == "body":
            raise RuntimeError("page crashed mid-read")
        return real_locator(selector)

    session.page.locator = crashing_body_locator

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.ASSERTION_FAILED
    assert any("absent_text: unmet (page unreadable)" in e.path for e in result.evidence
               if e.kind is EvidenceKind.DOM)


def test_met_url_branch_fails_safe_on_an_unreadable_page(tmp_path: Path) -> None:
    """AT-555: `met()`'s url branch used to read `session.page.url` raw,
    INSIDE the outer `with contextlib.suppress(Exception):`. On a crashed
    page that read raises, the suppress swallowed it and execution fell
    through to the final `return True` -- a url-bearing expectation on an
    unreadable page recorded SATISFIED instead of failing safe. Twin of
    AT-551's body_text fix: `_page_url` now returns None on a read failure
    and `met()` treats None as unmet, never met.

    Probes `met()` directly rather than through `run_case`: `assert_expected`
    records each field's evidence via its OWN independently-guarded reader
    (`_url_label`/`_text_label`, both already fixed pre-AT-555 for their own
    incidents), so a `met()`-only regression does not flip the run's final
    Outcome or evidence text -- it only changes how many times the poll
    loop retries before falling back to that evidence. The actual contract
    `met()` makes (and that `session._met()` / any future direct caller
    relies on) has to be pinned at `met()` itself."""
    session = session_with_fake_page(tmp_path)
    real_page = session.page

    class PageWithUnreadableUrl:
        """Delegates everything to the real fake page except `.url`, whose
        read raises -- mirrors test_execute.py's crashing_body_locator
        pattern but for the url property instead of a locator method."""

        def __getattr__(self, name: str):
            return getattr(real_page, name)

        @property
        def url(self) -> str:
            raise RuntimeError("page crashed mid-read")

    session._page = PageWithUnreadableUrl()

    assert assertions.met(session, ExpectedState(url="/success")) is False


def test_a_met_expectation_keeps_the_run_completed(tmp_path: Path) -> None:
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN + "/success",
             expected={"url": "/success", "visible_text": ["Welcome"]}),
    ]
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Welcome"

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    met_asserts = [e for e in result.evidence
                   if e.kind is EvidenceKind.DOM and e.path.startswith("assert ")
                   and ": met" in e.path]
    assert len(met_asserts) == 2  # url + visible_text


def test_an_assert_step_with_no_expectation_is_harmless(tmp_path: Path) -> None:
    """A bare ASSERT (nothing declared) records no unmet evidence and does
    not fail the run — D-032's no-expected case."""
    steps = [Step(order=1, action=Action.ASSERT, target="")]
    session = session_with_fake_page(tmp_path)

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.COMPLETED
    assert not [e for e in result.evidence if e.kind is EvidenceKind.DOM
                and "assert " in e.path]


def test_errored_still_beats_assertion_failed(tmp_path: Path) -> None:
    """A mid-step exception still wins even when an EARLIER step's own
    assertion was unmet -- real precedence between two different steps, not
    just 'exception -> ERRORED' re-pinned under this name (AT-550: cycle-1's
    version made the raising step the SAME step as the expectation, so it
    only proved the single-step case test_step_exception_is_errored_not_a_crash
    already covers)."""
    steps = [
        Step(order=1, action=Action.CLICK, target="button[type=submit]",
             expected={"visible_text": ["Never arrives"]}),
        Step(order=2, action=Action.CLICK, target="button.broken"),
    ]
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "something else entirely"  # step 1's expectation never arrives

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.ERRORED
