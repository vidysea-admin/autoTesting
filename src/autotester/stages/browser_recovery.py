"""Bounded recovery from a closed browser between serial cases (AT-888).

One job: when a case dies because its page, context or browser was closed
(Playwright `TargetClosedError`), mark ONLY that case INCONCLUSIVE with cause
"browser closed" (never FAIL: the target was not observed), relaunch the shared
session from the same persistent profile (login continues from saved cookies --
the repo has no separate login-case pattern to replay), and let the next case
run. Relaunches are capped per run; past the cap the remaining cases are
reported with that named reason instead of cascading one TargetClosedError each.
"""

from __future__ import annotations

from autotester.schema.enums import Outcome, Result
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict

DEFAULT_MAX_RELAUNCHES = 3
CAUSE = "browser closed"
_MARKERS = ("TargetClosedError", "has been closed", "browser has been closed")


def is_browser_closed(result: RawResult) -> bool:
    """Whether this case's own error is a closed page/context/browser."""
    return result.outcome == Outcome.ERRORED and any(m in (result.error or "") for m in _MARKERS)


def closed_verdict(result: RawResult, run_id: str) -> Verdict:
    """INCONCLUSIVE, cause "browser closed" -- the case tested nothing."""
    return Verdict(
        run_id=run_id, case_id=result.case_id, result=Result.INCONCLUSIVE,
        scoreboard=f"not judged: {CAUSE}", grader_provider="rule",
        note=f"{CAUSE}: {result.error}",
    )


class BrowserRecovery:
    """Counts relaunches for one serial tier and performs them."""

    def __init__(self, session: object, max_relaunches: int = DEFAULT_MAX_RELAUNCHES) -> None:
        self.session, self.max_relaunches, self.relaunches = session, max_relaunches, 0
        self.stop_reason: str | None = None

    def spend(self) -> bool:
        """Charge one relaunch to the tier's cap; False (nothing charged) once it is spent. Also
        used by whoever else relaunches in the tier (the pool's login fallback), so every launch
        is counted in one place."""
        if self.relaunches >= self.max_relaunches:
            return False
        self.relaunches += 1
        return True

    def recover(self) -> bool:
        """Relaunch after a closed-browser case. False (and `stop_reason` set) when the
        bound is spent or the relaunch itself fails; the caller stops the tier."""
        if not self.spend():
            self.stop_reason = (f"{CAUSE}: relaunch limit reached "
                                f"({self.max_relaunches} per run); remaining cases not run")
            return False
        try:
            self.session.relaunch(RuntimeError(CAUSE))
        except Exception as exc:
            self.stop_reason = f"{CAUSE}: relaunch failed ({type(exc).__name__}: {exc})"
            return False
        return True
