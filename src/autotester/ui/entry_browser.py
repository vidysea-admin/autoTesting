"""One browser per run for the entry (login-type) cases, and the login it leaves behind.

One job (D-115 (1), Umesh 2026-10-29: "login huaa use kro, baar baar logout kyu hi krna"): launch
the entry browser once, run the cases that need a logged-out page first, log in once, and lend that
logged-in session to the logged-in cases that follow, instead of a wiped launch per case.

* Reuse. An entry case starts at the sign-in page, so before it runs on a browser that has already
  run something, `reset` returns it to logged out (cookies, web storage, one tab, start URL).
  Nothing resets a session being lent, so no case logs in twice.
* Order. `order_entry_cases` runs the logged-out cases (wrong password, empty submit, any
  "logged out" precondition) first and the login case(s) last, so the login survives the entry leg.
* Hand-off. After a PASSED login case `lend()` gives its session to the ordinary cases (no reset,
  no relaunch); an ERRORED one among them, or any poisoned entry case, discards it.
* Identity. A `{{SECRET:KEY}}` credential set that is neither within nor around the browser's
  (another account) gets its own launch (one browser is
  live at a time: they share the `{slug}-entry-test` profile and a second sync-Playwright driver
  on the thread is the AT-576 defect). A case with no credentials fits any identity.

The pool never launches or resets a browser itself (`open_session`, `reset` are injected by
`ui/run_execution.py`, which owns the wipe, budget and trace phases).
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any

from autotester.core.redact import placeholder_keys
from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, Outcome
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.stages.entry_precondition import requires_unauthenticated

__all__ = ["EntryBrowserPool", "context_key", "logs_in", "order_entry_cases"]


def context_key(case: Case) -> str:
    """The identity a case serves: its sorted credential keys ('' for none)."""
    keys = {key for step in case.steps for text in (step.target, step.value or "")
            for key in placeholder_keys(text)}
    return ",".join(sorted(keys))


def logs_in(case: Case, project: Project) -> bool:
    """Whether the case signs in for real and so leaves the browser logged in: the project's login
    case, or a happy-path credentialed case that is not itself a logged-out check."""
    if project.login_case_id is not None and case.id == project.login_case_id:
        return True
    return (case.case_class is CaseClass.HAPPY and bool(context_key(case))
            and not requires_unauthenticated(case))


def order_entry_cases(cases: list[Case], project: Project) -> list[Case]:
    """Logged-out cases first, login cases last; every other order is kept."""
    return sorted(cases, key=lambda case: logs_in(case, project))


def _prime(session: Any, case: Case) -> None:
    """Per-case session state: evidence nests under the case and numbers from 01 (as a fresh
    entry browser did); nothing a previous case masked or paused on carries over."""
    state = session.state
    state.evidence_prefix, state.screenshots = case.id, 0
    state.secret_locators, state.hitl = [], None


class EntryBrowserPool:
    """Hand each entry case a logged-out browser; launch as few as identity allows."""

    def __init__(self, project: Project, *, open_session: Callable[[Case], Any],
                 reset: Callable[[Any, Case], None]) -> None:
        self.project = project
        self._open, self._reset = open_session, reset
        self._session: Any = None
        self._key = ""  # the identity the live browser serves; '' = none yet
        self._logged_in = False  # the live browser holds a login a passed case just made

    def _fits(self, key: str) -> bool:
        """Same account: either credential set contains the other (a wrong-password case uses
        only the email secret, the happy login email and password); none fits any."""
        mine, theirs = set(key.split(",")) - {""}, set(self._key.split(",")) - {""}
        return mine <= theirs or theirs <= mine

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
        merged = (set(self._key.split(",")) | set(key.split(","))) - {""}
        self._key, self._logged_in = ",".join(sorted(merged)), False
        _prime(self._session, case)
        return self._session

    def release(self, case: Case, session: Any, result: RawResult | None, *,
                passed: bool = False) -> None:
        """The case is done (and already saved): keep the browser, or discard it if poisoned.
        `passed` + a login case marks the session as logged in, to `lend`."""
        if (result is None or result.outcome is Outcome.ERRORED
                or getattr(session, "_restore_error", None) or session is not self._session):
            self._drop(session)
            return
        self._logged_in = passed and logs_in(case, self.project)

    def lend(self) -> Any:
        """The logged-in session for the ordinary cases that follow a passed login, else None."""
        return self._session if self._logged_in and self._session is not None else None

    def note_shared(self, result: RawResult) -> None:
        """An ordinary case ran in the lent session: an ERRORED one may have broken it."""
        if result.outcome is Outcome.ERRORED:
            self._drop()

    def close(self) -> None:
        self._drop()

    def _drop(self, session: Any = None) -> None:
        target = session if session is not None else self._session
        if target is not None and target is self._session:
            self._session, self._key, self._logged_in = None, "", False
        if target is not None:
            with contextlib.suppress(Exception):  # the bounded teardown already traced it
                target.close()
