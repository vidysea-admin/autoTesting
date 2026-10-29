"""One browser per run for the entry (login-type) cases, with isolation where identity differs.

One job (D-115 (1)): decide, per entry case, whether it reuses the browser the previous entry case
used or needs its own launch, and keep that browser clean between cases. At most ONE entry
browser is live at a time (they share the `{slug}-entry-test` profile, and a second sync-Playwright
driver on the thread is the AT-576 defect), so "its own context" means: close the shared browser,
launch a fresh wiped one for this case, and close that one straight after.

Reuse rule. A case reuses the live browser unless it is isolated (`context_key` is None: a
logged-out visitor or an adversarial-tier case) or it serves a different identity (a different set
of `{{SECRET:KEY}}` credentials; a case with none fits any identity). Every reuse is preceded by
`reset` (logged out, single tab, start URL), so a login case after a logged-in case still logs in
and proves it. Why a reset rather than keeping the login across cases: entry cases are by
definition the ones that start logged out, so clearing is the safer reading of "login cases still
prove login", and it keeps the pre-D-115 guarantee while still dropping the per-case launch and
Chromium teardown that stalled run-01M617NCNB8RBBME2RSH9ZQ87P.

The pool never launches or resets a browser itself (`open_session`, `reset` are injected by
`ui/run_execution.py`, which owns the wipe, budget and trace phases). A browser is discarded, not
reused, after an ERRORED case, a latched restore error, or a failed reset.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any

from autotester.core.redact import placeholder_keys
from autotester.schema.case import Case
from autotester.schema.catalog import TIER_BY_CLASS, Tier
from autotester.schema.enums import Outcome
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.stages.entry_precondition import requires_unauthenticated

__all__ = ["EntryBrowserPool", "context_key"]


def context_key(case: Case) -> str | None:
    """None when the case needs its own browser (logged-out or adversarial); else the sorted
    credential keys it uses ('' for none), the identity it serves."""
    if requires_unauthenticated(case) or TIER_BY_CLASS[case.case_class] is Tier.ADVERSARIAL:
        return None
    keys = {key for step in case.steps for text in (step.target, step.value or "")
            for key in placeholder_keys(text)}
    return ",".join(sorted(keys))


def _prime(session: Any, case: Case) -> None:
    """Per-case session state: evidence nests under the case and numbers from 01 (as a fresh
    entry browser did); nothing a previous case masked or paused on carries over."""
    state = session.state
    state.evidence_prefix, state.screenshots = case.id, 0
    state.secret_locators, state.hitl = [], None


class EntryBrowserPool:
    """Hand each entry case a clean browser; launch and close as few as isolation allows."""

    def __init__(self, project: Project, *, open_session: Callable[[Case], Any],
                 reset: Callable[[Any, Case], None]) -> None:
        self.project = project
        self._open, self._reset = open_session, reset
        self._session: Any = None
        self._key = ""  # the identity the live browser serves; '' = none yet

    def _fits(self, key: str | None) -> bool:
        return key is not None and (not key or not self._key or key == self._key)

    def acquire(self, case: Case) -> Any:
        key = context_key(case)
        if self._session is not None and not self._fits(key):
            self._drop()
        if self._session is not None:
            try:
                self._reset(self._session, case)
            except Exception:  # fail closed: never run on state the reset could not clear
                self._drop()
        if self._session is None:
            self._session = self._open(case)
            self._key = ""
        self._key = self._key or key or ""
        _prime(self._session, case)
        return self._session

    def release(self, case: Case, session: Any, result: RawResult | None) -> None:
        """The case is done (and already saved): keep the browser for the next case, or close it."""
        poisoned = (result is None or result.outcome is Outcome.ERRORED
                    or bool(getattr(session, "_restore_error", None)))
        if poisoned or context_key(case) is None or session is not self._session:
            self._drop(session)

    def close(self) -> None:
        self._drop()

    def _drop(self, session: Any = None) -> None:
        target = session if session is not None else self._session
        if target is not None and target is self._session:
            self._session, self._key = None, ""
        if target is not None:
            with contextlib.suppress(Exception):  # the bounded teardown already traced it
                target.close()
