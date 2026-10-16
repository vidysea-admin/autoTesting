"""RUN_BUDGET: the consent budget one case run spends against (AT-570/AT-660).

Split out of `stages/parallel_run.py` when that module crossed the 300-line
design cap (core-invariants C2). The split is by responsibility, not by size:
`parallel_run.py` decides HOW MANY cases run at once and fans them out;
this module decides WHETHER a case may spend anything at all, which is a
consent question and shares its vocabulary with `core/consent.py` (the gate)
and `schema/approval.py` (the grant) rather than with the thread pool.

One concept, one place (C3): `RunBudget`, the per-case action cost, and the
wall-clock a run asks the gate for are all defined here and nowhere else.

Contract: qa/contracts/parallel-run.md PR7; qa/contracts/consent.md CN10.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from autotester.schema.approval import RunApproval
from autotester.schema.case import Case
from autotester.schema.enums import Action


class RunBudgetExceeded(RuntimeError):
    """A named aggregate brake, never swallowed as a browser observation."""


class RunBudget:
    """PR7: one shared, thread-safe consent budget for the whole run -- never
    one per worker, so N-way concurrency can never spend up to N times what
    `RunApproval` granted. The aggregate is checked-and-reserved atomically so
    two workers racing to spend the last few actions can never both succeed.

    AT-570/C12(b): a `RunApproval` is REQUIRED. This class used to accept
    `None` and read it as "unlimited", so a run with no human authorisation was
    not an unapproved run but an unbounded one -- the absence of permission
    granting permission.

    AT-660/CN10: every bound means the same thing here as it does at the gate
    (`core/consent.py::_shortfalls`), namely that ZERO GRANTS NOTHING. The
    truthiness guards this replaces (`if approval.max_actions and ...`) made
    `0` mean *unlimited* during the run while the gate read the same `0` as a
    zero budget -- one field, two opposite meanings, and the permissive one
    governed what actually happened."""

    def __init__(self, approval: RunApproval, judge_allowance_s: float = 0.0) -> None:
        if approval is None:
            raise ValueError(
                "RunBudget requires a RunApproval: a run with no approval is an unapproved "
                "run, never an unlimited one (AT-570, core-invariants C12(b))"
            )
        self._approval = approval.model_copy(deep=True)
        for name in ("max_actions", "max_probes", "wall_clock_s"):
            value = getattr(approval, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"invalid run budget {name}")
        if not math.isfinite(judge_allowance_s) or judge_allowance_s < 0:
            raise ValueError("invalid judge allowance")
        # Judge (model-grading) time is accounted SEPARATELY from the approval's clock:
        # the approval bounds the time the browser acts on the target; grading is bounded
        # by this allowance, and any grading beyond it is charged to the approval clock.
        self._judge_allowance_s = float(judge_allowance_s)
        self._judge_done_s = 0.0
        self._judge_active = 0
        self._judge_since = 0.0
        self._lock = threading.Lock()
        self._actions_used = 0
        self._probes_used = 0
        self._start = time.monotonic()
        self._stop_reason: str | None = None

    @classmethod
    def for_cases(cls, approval: RunApproval, cases: list[Case]) -> RunBudget:
        """The budget for a run of `cases`: the approval plus its bounded judge allowance."""
        return cls(approval, judge_allowance_s=judge_allowance_s(cases))

    @contextmanager
    def judging(self) -> Iterator[None]:
        """Time spent inside is judge time: excluded from the approval clock, up to the
        judge allowance. Overlapping judges (parallel workers) count their UNION once."""
        with self._lock:
            if self._judge_active == 0:
                self._judge_since = time.monotonic()
            self._judge_active += 1
        try:
            yield
        finally:
            with self._lock:
                self._judge_active -= 1
                if self._judge_active == 0:
                    self._judge_done_s += time.monotonic() - self._judge_since

    def _judge_excluded_locked(self, now: float) -> float:
        spent = self._judge_done_s + (now - self._judge_since if self._judge_active else 0.0)
        return min(spent, self._judge_allowance_s)

    def _browser_elapsed_locked(self) -> float:
        now = time.monotonic()
        return now - self._start - self._judge_excluded_locked(now)

    @property
    def judge_s_used(self) -> float:
        with self._lock:
            now = time.monotonic()
            return self._judge_done_s + (now - self._judge_since if self._judge_active else 0.0)

    @property
    def judge_allowance_s(self) -> float:
        return self._judge_allowance_s

    def try_consume(self, *, actions: int = 0, probes: int = 0) -> bool:
        return self._consume(actions=actions, probes=probes, require_running=False)

    def _consume(self, *, actions: int, probes: int, require_running: bool) -> bool:
        for value in (actions, probes):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("budget spends must be nonnegative integers")
        approval = self._approval
        with self._lock:
            if require_running and self._stop_reason is not None:
                return False
            # `<= 0` explicitly rather than `elapsed > granted`: `time.monotonic()`
            # has ~15ms resolution on Windows, so a strict comparison against 0.0
            # would refuse or allow depending on how fast the host is, and a
            # fail-closed rule that is only usually closed is not one.
            if (approval.wall_clock_s <= 0
                    or self._browser_elapsed_locked() >= approval.wall_clock_s):
                self._stop_reason = self._stop_reason or "wall_clock_s"
                return False
            actions_after = self._actions_used + actions
            probes_after = self._probes_used + probes
            if actions_after > approval.max_actions:
                self._stop_reason = self._stop_reason or "max_actions"
                return False
            if probes_after > approval.max_probes:
                self._stop_reason = self._stop_reason or "max_probes"
                return False
            self._actions_used = actions_after
            self._probes_used = probes_after
            return True

    def check(self, *, actions: int = 0, probes: int = 0) -> None:
        if not self._consume(actions=actions, probes=probes, require_running=True):
            raise RunBudgetExceeded(f"run budget exhausted: {self.stop_reason}")

    def check_start(self) -> None:
        self.check()
        with self._lock:
            if self._actions_used >= self._approval.max_actions:
                self._stop_reason = self._stop_reason or "max_actions"
        self.check()

    def matches(self, approval: RunApproval) -> bool:
        return self._approval == approval

    def remaining_ms(self, requested: float = 30000) -> int:
        self.check()
        with self._lock:
            remaining = (self._approval.wall_clock_s - self._browser_elapsed_locked()) * 1000
        if remaining < 1:
            with self._lock:
                self._stop_reason = self._stop_reason or "wall_clock_s"
            raise RunBudgetExceeded("run budget exhausted: wall_clock_s")
        if not math.isfinite(requested) or requested < 1:
            raise ValueError("browser timeout must be positive and finite")
        return max(1, int(min(requested, remaining)))

    @property
    def stop_reason(self) -> str | None:
        return self._stop_reason

    @property
    def probes_used(self) -> int:
        return self._probes_used

    @property
    def actions_used(self) -> int:
        return self._actions_used


def action_cost(case: Case) -> int:
    """One case's cost against the aggregate action budget -- one unit per
    declared step, the system's own vocabulary for "an action" (`Action` in
    `schema/enums.py`); a step-less case still costs at least 1."""
    return max(1, len(case.steps))


WALL_CLOCK_PER_ACTION_S = 8.0
"""How many seconds one case action may take, for sizing a run's wall-clock
REQUEST at the consent gate -- `BrowserSession.settle`'s own 8000 ms ceiling
(`browser/session.py:237`) in seconds.

Why this exists at all (AT-660): `RunBudget` now reads `wall_clock_s = 0` as
"no time granted", so a run must be covered by an approval with a positive wall
clock. If the preflight asked for `require_approval`'s default of `0.0`, a
zero-time approval would sail through the gate and then refuse every case
mid-run -- the worse place for a refusal. Asking for a real number moves that
refusal to preflight, before a browser opens.

Deliberately an OVER-estimate: a run refused for want of headroom is the
fail-closed direction, a run killed halfway through is not. It is NOT a policy
ceiling -- it bounds nothing and caps nothing; it only sizes the request (CN10:
a maximum is a gate decision, not a build's). Duplicated from
`browser/session.py`'s 8000 ms default rather than imported because that module
is at the 300-line design cap and cannot take an exported constant (AT-681)."""


def wall_clock_request_s(cases: list[Case]) -> float:
    """The wall clock this run asks the gate for: its own action total times
    the per-action ceiling. Derived from the run, never a constant, so the
    grant command the refusal prints carries bounds the run actually needs.

    Includes the bounded judge allowance (`judge_allowance_s`), so the grant covers the
    whole run's time; `RunBudget` holds that allowance outside the browser clock."""
    return (sum(action_cost(c) for c in cases) * WALL_CLOCK_PER_ACTION_S
            + judge_allowance_s(cases))


def probe_request(cases: list[Case]) -> int:
    """The probes this run is KNOWN to spend, for the human-grant preflight (ISS-d063-grant-
    budget-3): two field samples per fill and one observation pass per assertion. A floor, not
    a ceiling -- the runtime brake still decides the rest -- so a row granting fewer probes is
    refused before a browser opens instead of stopping the run at its first fill."""
    steps = [step for case in cases for step in case.steps]
    return (2 * sum(1 for st in steps if st.action is Action.FILL)
            + sum(1 for st in steps if st.action is Action.ASSERT))


JUDGE_ALLOWANCE_PER_CASE_S = 45.0
"""Seconds of serial judge (model grading) latency allowed per case, held OUTSIDE the
approval's wall clock. Measured on the real PathLynks run: 8-27 s per call plus image
handling, ~35 s per judged case; 45 s leaves headroom. Bounded, so total run time is
at most `wall_clock_s + judge_allowance_s(cases)` (grading beyond it is charged to the
approval clock instead)."""


def judge_allowance_s(cases: list[Case]) -> float:
    """The separate judge-time budget for a run: one per-case allowance per case."""
    return len(cases) * JUDGE_ALLOWANCE_PER_CASE_S
