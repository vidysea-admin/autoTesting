"""Whether a case needs a logged-out visitor (so it must not share the signed-in profile)."""

from __future__ import annotations

import re

from autotester.schema.case import Case
from autotester.schema.enums import CaseClass

__all__ = ["requires_unauthenticated"]

_UNAUTH_RE = re.compile(
    r"(?<!\w)(unauthenticated|unauthorized|unauth|logged[- ]?out|signed[- ]?out|"
    r"(not|never) (logged|signed) in|without (being )?(authenticated|logged in|signed in)|"
    r"no (active )?session)(?!\w)", re.I)


def requires_unauthenticated(case: Case) -> bool:
    """True for a case whose precondition is a logged-out visitor (a `deeplink_unauth` class, or
    a precondition saying so). It must run in a fresh, wiped profile -- never the shared
    signed-in one, where the guard it tests would never trigger (T-169 real run, false FAIL)."""
    return case.case_class is CaseClass.DEEPLINK_UNAUTH or any(
        _UNAUTH_RE.search(text) for text in case.preconditions)
