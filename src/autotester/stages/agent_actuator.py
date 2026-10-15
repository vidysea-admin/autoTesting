"""AGENT_ACTUATOR: the guards, bounds and typed boundary around an agent that drives a page.

Contract: qa/contracts/agent-fallback.md AF1-AF4 (D-041, T-177). Playwright stays the
deterministic actuator; when a screen is unknown an agent backend (browser-use, in
`stages/browser_use_backend.py`) may drive the page -- and an agent that can click is the most
dangerous actuator, so this module is what makes it no more powerful than the deterministic one:

- every action the backend means to take is shown to `ActionGuard` BEFORE it runs: the D-016
  deny-list and never-click list, the X7 same-domain check (on the destination and on the page
  the action lands on), `write_policy`, and the run's `RunBudget` (an agent action is an action);
- the number of steps and the wall clock are bounded, and exhausting either is a named,
  non-passing outcome (O4);
- what comes back is a typed `ActuatorResult`, re-checked here: free text, a missing field or an
  action the guard never saw is refused, not passed through;
- there is no verdict anywhere in this module (C7) -- only `grade.py` writes one.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from pydantic import ValidationError

from autotester.browser.secrets import host_of
from autotester.browser.session import BrowserSession, NavigationRefused, check_destination
from autotester.schema.agent_fallback import (
    ActuatorResult,
    FallbackAction,
    FallbackActionKind,
    FallbackOutcome,
    FallbackStatus,
)
from autotester.schema.enums import EvidenceKind, WritePolicy
from autotester.schema.run import Evidence
from autotester.schema.screen_graph import ElementRef
from autotester.stages.account_destroy import DestroyContext
from autotester.stages.explore_safety import deny_reason, policy_for
from autotester.stages.run_budget import RunBudgetExceeded

DEFAULT_MAX_STEPS = 8
DEFAULT_WALL_CLOCK_S = 120.0
_WRITE_KINDS = frozenset({FallbackActionKind.FILL, FallbackActionKind.SELECT,
                          FallbackActionKind.UPLOAD})
_ELEMENT_KINDS = _WRITE_KINDS | {FallbackActionKind.CLICK}
_MODIFIERS = frozenset({"control", "ctrl", "shift", "alt", "meta", "command", "cmd",
                        "controlormeta"})
_SAFE_KEYS = frozenset({"tab", "escape", "esc", "arrowup", "arrowdown", "arrowleft",
                        "arrowright", "pageup", "pagedown", "home", "end"})
"""Under read_only an agent may press only these (after stripping modifiers): none can submit,
type or delete. An allow-list, not a deny-list of "enter": NumpadEnter, Control+Enter, a typed
string ending in a newline and the unknown-key-is-typed fallback all slip past a deny-list."""

Vet = Callable[[FallbackAction], None]


class ActuatorError(RuntimeError):
    """Base of the typed errors this adapter raises."""


class MalformedActuatorResult(ActuatorError):
    """A backend returned something that is not a well-formed `ActuatorResult` (AF2)."""


class ActionRefused(ActuatorError):
    """A guard refused an agent-chosen action (AF3); the action never ran."""


class BoundExhausted(ActuatorError):
    """The step or wall-clock bound was reached (AF4); the message names which."""


class ActuatorBackend(Protocol):
    """An agent that drives the page. It must call `vet(action)` before each action it takes."""

    def run(self, task: str, vet: Vet, *, max_steps: int, timeout_s: float) -> object: ...


def only_safe_keys(value: str | None) -> bool:
    """True when every key in `value` ('Shift+Tab', 'Tab Tab') is a navigation key."""
    keys = (value or "").split()
    mains = [[p for p in key.lower().split("+") if p not in _MODIFIERS] for key in keys]
    return bool(keys) and all(len(m) == 1 and m[0] in _SAFE_KEYS for m in mains)


def parse_result(raw: object) -> ActuatorResult:
    """`raw` as an `ActuatorResult`, or `MalformedActuatorResult` naming what is wrong."""
    if isinstance(raw, ActuatorResult):
        raw = raw.model_dump()
    if not isinstance(raw, dict):
        raise MalformedActuatorResult(
            f"actuator returned {type(raw).__name__}, not a typed result")
    try:
        return ActuatorResult.model_validate(raw)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"]) or "?" for e in exc.errors()})
        raise MalformedActuatorResult(f"malformed actuator result: {', '.join(fields)}") from exc


class ActionGuard:
    """The `vet` callable handed to a backend: bound check, refusal check, budget spend."""

    def __init__(self, session: BrowserSession, max_steps: int, wall_clock_s: float,
                 clock: Callable[[], float]) -> None:
        self.project = session.project
        self.budget = getattr(session, "budget", None)
        self.policy = policy_for(session.project)
        self.destroy_ctx = DestroyContext()
        self.max_steps, self.wall_clock_s, self.clock = max_steps, wall_clock_s, clock
        self.deadline = clock() + wall_clock_s
        self.vetted: list[FallbackAction] = []
        self.refusals: list[str] = []

    def over_time(self) -> bool:
        return self.clock() >= self.deadline

    def __call__(self, action: FallbackAction) -> None:
        if len(self.vetted) >= self.max_steps:
            raise BoundExhausted(f"max_steps={self.max_steps} reached")
        if self.over_time():
            raise BoundExhausted(f"wall_clock_s={self.wall_clock_s:g} reached")
        reason = self.refusal(action)
        if reason is None and self.budget is not None:
            try:
                self.budget.check(actions=1)
            except RunBudgetExceeded as exc:
                reason = str(exc)
        if reason is not None:
            self.refusals.append(f"{action.kind.value} {action.target!r}: {reason}")
            raise ActionRefused(reason)
        self.vetted.append(action)

    def landed(self, url: str | None) -> None:
        """X7: the page the agent is on NOW must be inside the allowed domains. Called after
        actions have run (redirects, open redirects, JS navigation, hrefless clicks); an
        off-scope page is a blocked step -- the agent stops here and the run says so."""
        try:
            check_destination(self.project, url or "")
        except NavigationRefused as exc:
            reason = f"landed outside allowed domains: {exc}"
            self.refusals.append(f"landed on {host_of(url or '') or 'an unparseable page'}: "
                                 f"{reason}")
            raise ActionRefused(reason) from exc

    def refusal(self, action: FallbackAction) -> str | None:
        """Why `action` must not run, or None. The order mirrors `explore_safety.deny_reason`."""
        if action.kind is FallbackActionKind.NAVIGATE and not action.url:
            return "navigate with no destination to check"
        if action.url:
            try:
                check_destination(self.project, action.url)
            except NavigationRefused as exc:
                return f"destination outside allowed domains: {exc}"
        read_only = self.policy.write_policy is WritePolicy.READ_ONLY
        if read_only and action.kind in _WRITE_KINDS:
            return f"{action.kind.value} is a write; refused under read_only"
        if (read_only and action.kind is FallbackActionKind.PRESS_KEY
                and not only_safe_keys(action.value)):
            return (f"key {action.value!r} is not a navigation key and could submit or type; "
                    "refused under read_only")
        if action.kind in _ELEMENT_KINDS:
            element = ElementRef(role=action.role, name=action.target, selector=action.target,
                                 is_form_submit=action.is_form_submit)
            return deny_reason(element, self.policy, page=action.url or "",
                               destroy_ctx=self.destroy_ctx)
        return None


def _landing_url(session: BrowserSession) -> str:
    """Where the shared page really is after the agent finished. `page.url` alone can be stale
    (the agent drove it over CDP while this thread was parked), so ask the page itself."""
    page = session.page
    try:
        return str(page.evaluate("location.href"))
    except Exception:
        return str(page.url)


class FallbackActuator:
    """Run one bounded, guarded agent attempt. `invoke` never raises: every ending is a
    `FallbackOutcome` whose `reason` names the bound, refusal or defect."""

    def __init__(self, backend: ActuatorBackend, *, max_steps: int = DEFAULT_MAX_STEPS,
                 wall_clock_s: float = DEFAULT_WALL_CLOCK_S,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.backend, self.max_steps = backend, max_steps
        self.wall_clock_s, self.clock = wall_clock_s, clock

    def invoke(self, session: BrowserSession, task: str) -> FallbackOutcome:
        budget = getattr(session, "budget", None)
        if budget is not None:
            try:
                budget.check()
            except RunBudgetExceeded as exc:
                return FallbackOutcome(status=FallbackStatus.REFUSED, reason=str(exc))
        guard = ActionGuard(session, self.max_steps, self.wall_clock_s, self.clock)
        try:
            raw = self.backend.run(task, guard, max_steps=self.max_steps,
                                   timeout_s=self.wall_clock_s)
            guard.landed(_landing_url(session))
            return self._finish(raw, guard)
        except BoundExhausted as exc:
            return self._ended(FallbackStatus.BOUND_EXHAUSTED, str(exc), guard)
        except ActionRefused as exc:
            return self._ended(FallbackStatus.REFUSED, str(exc), guard)
        except MalformedActuatorResult as exc:
            return self._ended(FallbackStatus.MALFORMED, str(exc), guard)
        except Exception as exc:  # a backend crash is an outcome, never a crash of the run
            text = session.secrets.scrub_optional(f"{type(exc).__name__}: {exc}") or ""
            return self._ended(FallbackStatus.FAILED, text, guard)

    def _finish(self, raw: object, guard: ActionGuard) -> FallbackOutcome:
        result = parse_result(raw)
        if guard.over_time():
            raise BoundExhausted(f"wall_clock_s={self.wall_clock_s:g} reached")
        unseen = [a for a in result.actions if a not in guard.vetted]
        if unseen:
            return self._ended(
                FallbackStatus.REFUSED,
                f"{len(unseen)} reported action(s) were never vetted by the guard", guard)
        status = FallbackStatus.RESOLVED if result.resolved else FallbackStatus.UNRESOLVED
        reason = "" if result.resolved else "the agent did not resolve the screen"
        return self._ended(status, reason, guard, result)

    @staticmethod
    def _ended(status: FallbackStatus, reason: str, guard: ActionGuard,
               result: ActuatorResult | None = None) -> FallbackOutcome:
        return FallbackOutcome(status=status, reason=reason, steps_used=len(guard.vetted),
                               result=result, vetted=list(guard.vetted),
                               refusals=list(guard.refusals))


def outcome_evidence(outcome: FallbackOutcome, scrub: Callable[[str], str]) -> Evidence:
    """One DOM-evidence line stating how the invocation ended. Evidence, never a verdict."""
    ref = f"; evidence {outcome.result.evidence_ref}" if outcome.result else ""
    why = f": {outcome.reason}" if outcome.reason else ""
    seen = f"; saw: {outcome.result.observed}" if outcome.result else ""
    text = (f"agent fallback {outcome.status.value} after {outcome.steps_used} step(s)"
            f"{why}{seen}{ref}")
    return Evidence(kind=EvidenceKind.DOM, path=scrub(text))
