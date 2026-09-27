"""EXECUTE: run one case's steps in a real browser, producing a RawResult.

No judgement here — PASS/FAIL belongs to GRADE (T-041). This stage only performs
the case's steps on an already-started `BrowserSession` and records what
happened: a screenshot after every step, and one of four outcomes —
COMPLETED, ERRORED (an exception mid-step), BLOCKED_HITL (a secret the
project does not have yet, the OTP/2FA case), or ASSERTION_FAILED (D-032/
AT-540: a step's declared expectation deterministically did not hold — an
observation, not a grade; the grader still owns the verdict).
Contract: qa/contracts/execute.md.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from autotester.browser import conditions
from autotester.browser.secrets import MissingSecret
from autotester.browser.session import BrowserSession
from autotester.schema.case import Case
from autotester.schema.crawl import SafetyPolicy
from autotester.schema.enums import Action, Outcome
from autotester.schema.flowspec import Step
from autotester.schema.run import RawResult
from autotester.stages import network_capture

_DEFAULT_WAIT_MS = 5000

StepHandler = Callable[[BrowserSession, Step], None]

_ACTIONS: dict[Action, StepHandler] = {
    Action.NAVIGATE: lambda session, step: session.goto(step.target),
    Action.CLICK: lambda session, step: session.click(step.target, step_order=step.order),
    Action.FILL: lambda session, step: session.fill(
        step.target, step.value, step_order=step.order
    ),
    Action.SELECT: lambda session, step: session.select_option(
        step.target, step.value, step_order=step.order
    ),
    Action.UPLOAD: lambda session, step: session.upload(
        step.target, step.value or "", step_order=step.order
    ),
    Action.WAIT: lambda session, step: session.wait_for(
        step.target or None,
        timeout_ms=int(step.value) if step.value else _DEFAULT_WAIT_MS,
        step_order=step.order,
    ),
    # D-032/AT-540: ASSERT evaluates the step's own declared expectation and
    # records the result as DOM evidence. A no-expected ASSERT records
    # nothing to evaluate and stays harmless (the screenshot below is still
    # taken). Raising nothing here is deliberate — the consequence is decided
    # in run_case, not in the dispatch table.
    Action.ASSERT: lambda session, step: session.assert_expected(
        step.expected, step_order=step.order
    ),
    Action.BACK: lambda session, step: session.go_back(step_order=step.order),
    Action.HOVER: lambda session, step: session.hover(step.target, step_order=step.order),
    Action.PRESS_KEY: lambda session, step: session.press_key(
        step.value or "Enter", step.target or None, step_order=step.order
    ),
    Action.SCROLL: lambda session, step: session.scroll(
        int(step.value) if step.value else 800, step_order=step.order
    ),
}


class StepNotExecutable(RuntimeError):
    """`step.action` has no `BrowserSession` handler yet (e.g. a Track B action
    added to the enum before its handler landed). Caught like any other
    execution failure — a run reports it, never crashes on it."""


_ASSERT_EVIDENCE_KINDS = ("dom", "network")  # T-170/NA3: network joins the deterministic set


def _assertions_unmet(session: BrowserSession, evidence_start: int) -> bool:
    """Whether any recorded assert evidence after `evidence_start` says unmet
    (D-032). Reads only the labels this system itself wrote
    (`browser/assertions.py`'s `assert <field>: met|unmet` shape)."""
    unmet = "assert "
    for item in session.state.evidence[evidence_start:]:
        if (item.kind.value in _ASSERT_EVIDENCE_KINDS and item.path.startswith(unmet)
                and "unmet" in item.path):
            return True
    return False


def _drain_network_evidence(session: BrowserSession) -> None:
    """T-170/NA1: fold every first-party response the observer saw since the
    last drain into NETWORK evidence -- called after every step so a
    same-step `expected.network` check (`assert_expected`) already sees it.
    A no-op when no observer is attached (session.observer is None), which
    keeps every pre-existing run_case call unaffected."""
    if session.observer is None:
        return
    responses = session.observer.drain_responses()
    if not responses:
        return
    policy = SafetyPolicy(write_policy=session.project.write_policy)
    session.state.evidence.extend(network_capture.first_party_evidence(
        responses, session.project, policy, session.secrets.redactor()))


def _run_steps(
    case: Case, session: BrowserSession, start: float, evidence_start: int
) -> RawResult | bool:
    """Run every step in order. Returns a terminal `RawResult` the moment a step is
    BLOCKED_HITL/ERRORED, else the `assertion_failed` bool for the caller to finish with
    (split out of `run_case` so both functions stay under the file's line cap)."""
    assertion_failed = False
    for step in sorted(case.steps, key=lambda s: s.order):
        try:
            handler = _ACTIONS.get(step.action)
            if handler is None:
                raise StepNotExecutable(f"{step.action.value} has no browser handler yet")
            if step.action is Action.ASSERT or _declares_expectation(step.expected):
                pre = len(session.state.evidence)
            else:
                pre = None
            handler(session, step)
            if step.action in (Action.CLICK, Action.NAVIGATE, Action.BACK):
                # AT-045/AT-053: settle before the screenshot, so the grader
                # sees what the action caused, never a mid-transition frame.
                session.settle(step.expected)
            _drain_network_evidence(session)  # T-170/NA1: before step's own assert_expected
            if pre is not None:
                if step.action is not Action.ASSERT:
                    session.assert_expected(step.expected, step_order=step.order)
                if _assertions_unmet(session, pre):
                    assertion_failed = True
            session.screenshot(f"step{step.order:02d}-{step.action}", step_order=step.order)
        except MissingSecret as exc:
            return _result(case, session, start, Outcome.BLOCKED_HITL,
                           evidence_start=evidence_start, hitl_prompt=str(exc))
        except Exception as exc:  # the executor reports, it never crashes the run
            return _result(case, session, start, Outcome.ERRORED, evidence_start=evidence_start,
                           error=f"{type(exc).__name__}: {exc}")
    return assertion_failed


def run_case(case: Case, session: BrowserSession) -> RawResult:
    """Execute `case.steps` in order on `session`. E1/E2/E3: observe, never judge.

    D-032/AT-540: after every step whose `expected` declares something the
    executor can check deterministically (url/visible_text/absent_text/
    dom_asserts/network — T-170), the expectation is evaluated and recorded
    as DOM/NETWORK evidence; an unmet one makes the run's outcome
    ASSERTION_FAILED — an observation that a declared expectation did not
    hold, never a grade. AT-577: `session` may already carry earlier cases'
    evidence (the serial route reuses one session across a run) --
    `evidence_start` pins where THIS case begins, so its `RawResult` never
    carries a sibling's screenshots. AT-578: also written onto `session.
    state.evidence_start`, so `assert_expected`'s `network` check reads only
    this case's own captured traffic, not an earlier case's.

    D-045/AT-581 (E6): a VIEWPORT_MOBILE/LOCALE_I18N case is enacted (`browser/
    conditions.py`) before its steps run, or reported `Outcome.NOT_RUN` instead
    of running at the wrong viewport/locale and coming back a false PASS."""
    start = time.monotonic()
    evidence_start = len(session.state.evidence)
    session.state.evidence_start = evidence_start
    not_run_reason = conditions.enact(session, case.case_class)
    if not_run_reason is not None:
        return _result(case, session, start, Outcome.NOT_RUN, evidence_start=evidence_start,
                       not_run_reason=not_run_reason)
    try:
        outcome = _run_steps(case, session, start, evidence_start)
    finally:
        # Undo enact() so a shared, reused session (AT-577) never leaves a later,
        # unrelated case running at the mobile viewport this case asked for.
        conditions.reset(session, case.case_class)
    if isinstance(outcome, RawResult):
        return outcome
    if outcome:  # assertion_failed
        return _result(case, session, start, Outcome.ASSERTION_FAILED,
                       evidence_start=evidence_start)
    return _result(case, session, start, Outcome.COMPLETED, evidence_start=evidence_start)


def _declares_expectation(expected: object) -> bool:
    """Whether an `ExpectedState` carries anything the executor can check
    deterministically (D-032). `network` joined this set at T-170/NA3
    (`_drain_network_evidence` folds the observed stream into evidence before
    `assert_expected` reads it); `visual_signal` remains the judge's."""
    return bool(expected.url or expected.visible_text or expected.absent_text
                or expected.dom_asserts or expected.network)


def _result(
    case: Case,
    session: BrowserSession,
    start: float,
    outcome: Outcome,
    *,
    evidence_start: int = 0,
    error: str | None = None,
    hitl_prompt: str | None = None,
    not_run_reason: str | None = None,
) -> RawResult:
    # AT-341: an exception's own message (any exception, not only a named one)
    # can embed a resolved secret — the same boundary `_record` already holds
    # for evidence paths applies here before this ever reaches disk.
    return RawResult(
        case_id=case.id,
        outcome=outcome,
        duration_s=round(time.monotonic() - start, 3),
        error=session.secrets.scrub_optional(error),
        hitl_prompt=session.secrets.scrub_optional(hitl_prompt),
        not_run_reason=session.secrets.scrub_optional(not_run_reason),
        # AT-577: only THIS case's own slice, never the shared session's full history.
        evidence=list(session.state.evidence[evidence_start:]),
    )
