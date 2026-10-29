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
from contextlib import AbstractContextManager, contextmanager

from autotester.schema.approval import RunApproval
from autotester.schema.case import Case


class RunBudgetExceeded(RuntimeError):
    """A named aggregate brake, never swallowed as a browser observation."""


class _ExcludedClock:
    """Seconds spent inside `measure()` blocks, overlapping blocks counted as their UNION once,
    with `allowance_s` capping how much of it the owner may subtract from the approval clock.
    Not locked itself: `RunBudget` calls it only while holding its own lock."""

    def __init__(self, allowance_s: float) -> None:
        self.allowance_s, self.done_s, self.active, self.since = float(allowance_s), 0.0, 0, 0.0

    def enter(self) -> None:
        if self.active == 0:
            self.since = time.monotonic()
        self.active += 1

    def leave(self) -> None:
        self.active -= 1
        if self.active == 0:
            self.done_s += time.monotonic() - self.since

    def spent(self, now: float) -> float:
        return self.done_s + (now - self.since if self.active else 0.0)

    def excluded(self, now: float) -> float:
        return min(self.spent(now), self.allowance_s)


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

    def __init__(self, approval: RunApproval, judge_allowance_s: float = 0.0,
                 housekeeping_allowance_s: float = 0.0) -> None:
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
        for allowance in (judge_allowance_s, housekeeping_allowance_s):
            if not math.isfinite(allowance) or allowance < 0:
                raise ValueError("invalid judge allowance")
        # The approval's clock bounds only the time the browser ACTS on the target (D-112).
        # Judge (model grading) and housekeeping (Chromium exit, profile wipe, OCR, bundle
        # assembly) time is held off it by ONE shared exclusion clock (`_excluded`), so a second
        # spent inside both scopes is subtracted once. Its combined allowance is the two
        # allowances; anything beyond it is charged to the approval clock. `_judge` and
        # `_housekeeping` only MEASURE each kind for the run record -- they exclude nothing.
        self._excluded = _ExcludedClock(judge_allowance_s + housekeeping_allowance_s)
        self._judge = _ExcludedClock(judge_allowance_s)
        self._housekeeping = _ExcludedClock(housekeeping_allowance_s)
        self._lock = threading.Lock()
        self._actions_used = 0
        self._probes_used = 0
        self._overlapped = 0  # spends made while an excluded scope was open (R1, see report)
        self._start = time.monotonic()
        self._stop_reason: str | None = None

    @classmethod
    def for_cases(cls, approval: RunApproval, cases: list[Case]) -> RunBudget:
        """The budget for a run of `cases`: the approval plus its bounded judge and
        housekeeping allowances."""
        return cls(approval, judge_allowance_s=judge_allowance_s(cases),
                   housekeeping_allowance_s=housekeeping_allowance_s(cases))

    @contextmanager
    def _excluding(self, kind: _ExcludedClock) -> Iterator[None]:
        with self._lock:
            self._excluded.enter()
            kind.enter()
        try:
            yield
        finally:
            with self._lock:
                kind.leave()
                self._excluded.leave()

    def judging(self) -> AbstractContextManager[None]:
        """Time spent inside is judge time: excluded from the approval clock, up to the
        judge allowance. Overlapping judges (parallel workers) count their UNION once."""
        return self._excluding(self._judge)

    def housekeeping(self) -> AbstractContextManager[None]:
        """Time spent inside is browser teardown / profile wipe / OCR / bundle time: excluded
        from the approval clock (once, even when it overlaps judging) up to the combined
        allowance; beyond it, charged."""
        return self._excluding(self._housekeeping)

    def _browser_elapsed_locked(self) -> float:
        now = time.monotonic()
        return now - self._start - self._excluded.excluded(now)

    def excluded_report(self) -> dict[str, float]:
        """Seconds held off the approval clock, for the run record: each kind as measured and
        the `total` actually subtracted (the union, capped at the combined allowance).
        `acted_during_exclusion` makes the by-design overlap (R1) visible: how many spends
        (actions / probes) were made while a scope was open, i.e. while the shared clock was
        paused for every worker. 0 in a serial run, where the one thread in a scope cannot act."""
        with self._lock:
            now = time.monotonic()
            return {"judging": self._judge.spent(now),
                    "housekeeping": self._housekeeping.spent(now),
                    "total": self._excluded.excluded(now),
                    "acted_during_exclusion": float(self._overlapped)}

    @property
    def judge_s_used(self) -> float:
        with self._lock:
            return self._judge.spent(time.monotonic())

    @property
    def judge_allowance_s(self) -> float:
        return self._judge.allowance_s

    @property
    def housekeeping_s_used(self) -> float:
        with self._lock:
            return self._housekeeping.spent(time.monotonic())

    @property
    def housekeeping_allowance_s(self) -> float:
        return self._housekeeping.allowance_s

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
            self._actions_used, self._probes_used = actions_after, probes_after
            if (actions or probes) and self._excluded.active:
                self._overlapped += 1
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

Why (AT-660): `RunBudget` reads `wall_clock_s = 0` as "no time granted", so a run
needs an approval with a positive wall clock; asking for `require_approval`'s default
`0.0` would pass the gate and then refuse every case mid-run. A real number moves that
refusal to preflight, before a browser opens.

Deliberately an OVER-estimate (a run refused for headroom is the fail-closed direction).
NOT a policy ceiling: it only sizes the request (CN10: a maximum is a gate decision).
Duplicated from `browser/session.py`'s 8000 ms default because that module is at the
300-line cap and cannot take an exported constant (AT-681)."""


def wall_clock_request_s(cases: list[Case]) -> float:
    """The wall clock this run asks the gate for: its own action total times
    the per-action ceiling. Derived from the run, never a constant, so the
    grant command the refusal prints carries bounds the run actually needs.

    Includes the bounded judge allowance (`judge_allowance_s`), so the grant covers the
    whole run's time; `RunBudget` holds that allowance outside the browser clock."""
    return (sum(action_cost(c) for c in cases) * WALL_CLOCK_PER_ACTION_S
            + judge_allowance_s(cases))


JUDGE_ALLOWANCE_PER_CASE_S = 45.0
"""Seconds of serial judge (model grading) latency allowed per case, held OUTSIDE the
approval's wall clock. Measured on the real PathLynks run: 8-27 s per call plus image
handling, ~35 s per judged case; 45 s leaves headroom. Bounded, so total run time is
at most `wall_clock_s + judge_allowance_s(cases)` (grading beyond it is charged to the
approval clock instead)."""


def judge_allowance_s(cases: list[Case]) -> float:
    """The separate judge-time budget for a run: one per-case allowance per case."""
    return len(cases) * JUDGE_ALLOWANCE_PER_CASE_S


HOUSEKEEPING_ALLOWANCE_PER_CASE_S = 60.0
"""Seconds per case of non-browser housekeeping held OUTSIDE the approval's wall clock: waiting for
Chromium to exit (two bounded teardown calls of ~20 s), the entry-profile wipe, OCR and bundle
assembly. Measured stalls of 224-887 s per entry case were this time being charged to the clock
(stall-diagnosis 2026-10-28). Bounded: housekeeping beyond it IS charged, so a runaway teardown
still ends the run."""


def housekeeping_allowance_s(cases: list[Case]) -> float:
    """The separate housekeeping budget for a run: one per-case allowance per case."""
    return len(cases) * HOUSEKEEPING_ALLOWANCE_PER_CASE_S
