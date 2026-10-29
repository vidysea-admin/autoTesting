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
  no relaunch); an ERRORED one among them stops the lending, a poisoned entry case discards it.
* Relaunch. A lent session whose browser died is relaunched without its login (a session cookie
  is not in the profile); `relogin` replays the login case in it, or names why it could not, so no
  later case is graded as logged in on a logged-out page. If that reset itself fails, the browser
  is discarded and one fresh wiped one is launched for the replay (as `acquire` does), once per
  relogin and only while the tier's relaunch cap allows.
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
from autotester.schema.enums import CaseClass, Outcome, Result
from autotester.schema.project import Project
from autotester.schema.run import RawResult
from autotester.schema.verdict import Verdict
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


def _is_project_login(case: Case, project: Project) -> bool:
    return project.login_case_id is not None and case.id == project.login_case_id


def order_entry_cases(cases: list[Case], project: Project) -> list[Case]:
    """Logged-out cases first, login cases last, the project's own login case the very last (its
    account is the one lent); every other order is kept."""
    return sorted(cases, key=lambda c: (logs_in(c, project), _is_project_login(c, project)))


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
        self._login: Case | None = None  # the case that made it, replayed by `relogin`

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
        # a named project login is the only account lent (W1); else any passed happy login
        named = self.project.login_case_id is None or _is_project_login(case, self.project)
        self._logged_in = passed and named and logs_in(case, self.project)
        self._login = case if self._logged_in else None

    def lend(self) -> Any:
        """The logged-in session for the ordinary cases that follow a passed login, else None."""
        return self._session if self._logged_in and self._session is not None else None

    def live(self) -> Any:
        """The pool's current browser (None when it has none): `relogin` may replace it."""
        return self._session

    def relogin(self, grade: Callable[[Case, Any], Verdict], *,
                may_relaunch: Callable[[], bool] = lambda: True) -> str | None:
        """The lent browser was relaunched and its login is gone: reset it, replay the login case
        (`grade` runs and grades it) and keep lending it. None on success, else the named reason
        the rest of the tier stops with. The replay is not a second result for the login case.
        A reset that raises falls back the way `acquire` does (`_reset_or_replace`)."""
        session, login = self._session, self._login
        self._logged_in = False  # lendable again only once the replay has passed
        if session is None or login is None:
            return "browser relaunched and the login was lost: no login case to replay"
        shots = session.state.screenshots  # the ordinary cases' running count, not the replay's
        try:
            session = self._reset_or_replace(session, login, may_relaunch)
            _prime(session, login)
            session.state.evidence_prefix = f"{login.id}-relogin"
            replayed = grade(login, session).result is Result.PASS
            failure = None if replayed else "did not pass"
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"
        if session is self._session:
            # ordinary cases keep the shared-run layout and numbering: the replay's files sit under
            # `<id>-relogin/`, so restarting the count would overwrite earlier cases' screenshots
            session.state.evidence_prefix, session.state.screenshots = "", shots
        if failure is not None:
            return (f"browser relaunched and the login was lost: re-login ({login.id}) "
                    f"{failure}; remaining cases not run")
        self._logged_in = True
        return None

    def _reset_or_replace(self, session: Any, login: Case, may_relaunch: Callable[[], bool]) -> Any:
        """Reset the lent browser to logged out; if that raises (fail closed: never replay on state
        the reset could not clear), discard it and open ONE fresh wiped browser instead, provided
        the tier may still spend a relaunch. Otherwise the reset error propagates, named by the
        caller. The fresh browser is not reset and no second fallback follows: bounded."""
        try:
            self._reset(session, login)
            return session
        except Exception:
            if not may_relaunch():
                raise
        self._drop(session)
        self._session = self._open(login)
        self._key, self._login = context_key(login), login  # a later relogin replays it again
        return self._session

    def note_shared(self, result: RawResult) -> None:
        """An ordinary case ran in the lent session: an ERRORED one may have broken it, so stop
        lending it. It is NOT closed here: the tier loop is still running on it (and relaunches
        it itself if the browser died); `close()` ends it with the run (F1, checker B)."""
        if result.outcome is Outcome.ERRORED:
            self._logged_in = False

    def close(self) -> None:
        self._drop()

    def _drop(self, session: Any = None) -> None:
        target = session if session is not None else self._session
        if target is not None and target is self._session:
            self._session, self._key, self._logged_in, self._login = None, "", False, None
        if target is not None:
            with contextlib.suppress(Exception):  # the bounded teardown already traced it
                target.close()
