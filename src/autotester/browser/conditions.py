"""Enact a case's execution condition, or say why it cannot be (D-045/AT-581, E6).

`stages/expand.py` generates VIEWPORT_MOBILE and LOCALE_I18N cases, but nothing used to
enact them: every case ran at the desktop viewport in the default locale, so a PASS on one
of these cases was false (AT-581). This module is the enactment seam `stages/execute.py::
run_case` calls before running a case's steps: it either changes the live page/context to
match the class, or returns a reason the caller must report as `Outcome.NOT_RUN` instead of
letting the case run under the wrong condition and possibly PASS.

VIEWPORT_MOBILE is always enactable: `page.set_viewport_size()` works on an already-launched
context. LOCALE_I18N is NOT enactable here: Playwright's `locale` (and the `Accept-Language`
header it drives) is fixed at `launch_persistent_context()` time (`browser/launch.py`), and
this session's context is already running in the project's default locale by the time a case
reaches this seam — there is no live API to change it. Recreating the context per LOCALE_I18N
case would lose the persistent login state B5 exists to keep, which is a larger change than
this unit's scope; E6 explicitly allows reporting not-run instead of a false enactment.
"""

from __future__ import annotations

import contextlib
from typing import Any

from autotester.browser.launch import DEFAULT_VIEWPORT
from autotester.schema.enums import CaseClass

MOBILE_VIEWPORT = {"width": 390, "height": 844}
"""An iPhone-12-class mobile viewport -- small enough that a desktop layout served at this
size is visibly wrong, which is the point of a VIEWPORT_MOBILE case."""

LOCALE_NOT_ENACTABLE_REASON = (
    "locale is fixed at browser-context launch (Playwright persistent-context limitation); "
    "this session's context already launched in the project's default locale"
)


def enact(session: Any, case_class: CaseClass) -> str | None:
    """Enact `case_class`'s execution condition on `session`'s live page.

    Returns `None` when the condition was enacted (or `case_class` names no condition this
    module knows about — every other class runs unaffected). Returns a reason string when the
    condition could NOT be enacted; the caller (`run_case`) must then report the case as
    `Outcome.NOT_RUN` with that reason and never run its steps under the wrong condition.
    """
    if case_class is CaseClass.VIEWPORT_MOBILE:
        try:
            session.page.set_viewport_size(MOBILE_VIEWPORT)
        except Exception as exc:  # pragma: no cover - defensive; report rather than crash
            return f"could not set mobile viewport: {type(exc).__name__}: {exc}"
        return None
    if case_class is CaseClass.LOCALE_I18N:
        return LOCALE_NOT_ENACTABLE_REASON
    return None


def reset(session: Any, case_class: CaseClass) -> None:
    """Undo `enact()` after the case finishes, so a shared session (the serial route reuses
    one context across cases, AT-577) never leaves a later, unrelated case running at the
    mobile viewport. Best-effort and silent on failure, same as `BrowserSession.settle()` --
    a reset that can't happen is not this case's failure to report."""
    if case_class is CaseClass.VIEWPORT_MOBILE:
        with contextlib.suppress(Exception):  # mirrors settle()'s own suppression
            session.page.set_viewport_size(dict(DEFAULT_VIEWPORT))
