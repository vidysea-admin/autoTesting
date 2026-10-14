"""Does a case's own expected outcome say an error is the correct result? (grader-expected-error)

One job: feed `Rubric.expects_error`, so the grade note guard can accept expected-error wording in
a worst/edge case without relaxing for anything else.
"""

from __future__ import annotations

import re

from autotester.schema.case import Case
from autotester.schema.enums import CaseKind

_ERROR_EXPECTED = re.compile(
    r"\b(?:errors?|invalid|reject\w*|validation|denied|refus\w*|not\s+allowed|warning)\b",
    re.IGNORECASE)


def expects_error(case: Case) -> bool:
    """True when a worst/edge case's own stated outcome is an error, validation message or
    rejection (its rationale, title or a step's expected visible text says so)."""
    if case.kind not in (CaseKind.WORST, CaseKind.EDGE):
        return False
    text = [case.rationale or "", case.title]
    text += [t for step in case.steps for t in step.expected.visible_text]
    return bool(_ERROR_EXPECTED.search(" ".join(text)))
