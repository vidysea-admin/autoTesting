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


_NEGATION = re.compile(r"\b(?:not|never|no|without|n't|cannot|shouldn't|doesn't|won't)\b|n't\b",
                       re.IGNORECASE)


def expects_error(case: Case) -> bool:
    """True when a worst/edge case's own stated outcome is an error, validation message or
    rejection (its rationale, title or a step's expected visible text says so)."""
    if case.kind not in (CaseKind.WORST, CaseKind.EDGE):
        return False
    text = [case.rationale or "", case.title]
    text += [t for step in case.steps for t in step.expected.visible_text]
    return any(not _negated(m) for m in _ERROR_EXPECTED.finditer(" ".join(text)))


def _negated(match: re.Match[str]) -> bool:
    """True when the keyword is negated in its clause ("should not see an error")."""
    before = match.string[:match.start()]
    clause = re.split(r"[.;:!?\n]", before)[-1]
    return bool(_NEGATION.search(clause))
