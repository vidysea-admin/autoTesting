"""The notes-vs-verdict cross-check: a judge PASS whose own note describes a defect is not a PASS.

One job (AT-997, found live in T-181: the default rubric returned PASS on a seeded broken login
while both judges' notes said "reproduced the expected bug ... invalid credentials error"). The
judge's `result` is one enum field; its `note` is the reasoning. When they disagree the stage
cannot know which is right, so it fails closed (core-invariants C12): the PASS is held as
INCONCLUSIVE for a human, never persisted as PASS. A FAIL/INCONCLUSIVE answer is untouched.

The test is deliberately conservative toward INCONCLUSIVE: a correct PASS whose note merely
mentions an expected error (a negative case) is also held. That is the cheaper error. A defect
word preceded within three words by a negator ("no errors", "without any bug", "did not fail")
does not count.
"""

from __future__ import annotations

import re

from autotester.schema.enums import Result

_FAILURE_TERMS = re.compile(
    r"\b(bugs?|defects?|errors?|fail\w*|invalid|incorrect\w*|broken|unexpected\w*|wrong|"
    r"reproduc\w*|regress\w*|reject\w*|mismatch\w*|missing|unlabell?ed|seeded|issues?|"
    r"problems?|crash\w*|exceptions?|denied|unable|cannot|can't|doesn't|unresponsive)\b",
    re.IGNORECASE)
_NEGATOR = re.compile(r"\b(no|not|without|zero|nor|never|none|n't|free of|absence of)\b|n't\b",
                      re.IGNORECASE)
_LOOKBACK_WORDS = 3

NOTE_DISAGREES = (
    "judge answered PASS but its own note describes a failure ({terms}): result and reasoning "
    "disagree, so the PASS is not trusted (fail closed, core-invariants C12). Held as "
    "INCONCLUSIVE for a human to look at; judge note: {note!r}."
)


def failure_terms(note: str | None) -> list[str]:
    """The un-negated defect words in `note`, in order; empty when it reads clean."""
    if not note:
        return []
    found: list[str] = []
    for match in _FAILURE_TERMS.finditer(note):
        words = re.findall(r"[\w']+", note[:match.start()])[-_LOOKBACK_WORDS:]
        window = " ".join(words)
        if _NEGATOR.search(window):
            continue
        found.append(match.group(0).lower())
    return found


def note_guard(judged: Result, note: str | None) -> tuple[Result, str | None]:
    """Downgrade a PASS whose note describes a failure to INCONCLUSIVE; else pass through."""
    terms = failure_terms(note)
    if judged is Result.PASS and terms:
        return Result.INCONCLUSIVE, NOTE_DISAGREES.format(
            terms=", ".join(dict.fromkeys(terms)), note=note)
    return judged, note
