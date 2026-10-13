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

AT-998 widened the test beyond bare defect words: a defect lexicon (blocked, timed out, stuck, 500,
404, ...) plus negated-success phrases ("did not succeed", "not working as expected").
"""

from __future__ import annotations

import re

from autotester.schema.enums import Result

# Defect lexicon: a word or phrase that on its own says something went wrong (AT-998 widened it).
_DEFECT_LEXICON = re.compile(
    r"\b(bugs?|defects?|errors?|fail\w*|invalid|incorrect\w*|broken|unexpected\w*|wrong|"
    r"reproduc\w*|regress\w*|reject\w*|mismatch\w*|missing|unlabell?ed|seeded|issues?|"
    r"problems?|crash\w*|exceptions?|denied|unable|cannot|can't|doesn't|unresponsive|"
    r"unsuccessful\w*|block(?:ed|s)?|stuck|hang(?:s|ing)?|hung|freez\w*|could\s?n[o']t|"
    r"time[ds]?[ -]out|timeouts?|never\s+(?:appear|load|show|render|complet|finish)\w*)\b"
    r"|(?<![\w$.,])(?:500|404)(?![\w%])",
    re.IGNORECASE)
# Negated success: "did not / failed to / unable to / not" + a verb that names the expected outcome.
_NEGATED_SUCCESS = re.compile(
    r"\b(?:(?:did|does|do|was|were|is|are|has|have)(?:\s+not|n't)|failed\s+to|unable\s+to|not)"
    r"\s+(?:\w+ly\s+)?(?:succeed\w*|load\w*|appear\w*|work(?:s|ed|ing)?|open\w*|render\w*|"
    r"complet\w*|respond\w*|finish\w*|authenticat\w*|log(?:ged)?\s?in|sign(?:ed)?\s?in|"
    r"submit\w*|sav(?:e|ed|ing))\b",
    re.IGNORECASE)
_NEGATOR = re.compile(
    r"\b(no|not|without|zero|nor|never|none|nothing|neither|free of|absence of)\b|n't\b",
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
    hits = [m for rx in (_DEFECT_LEXICON, _NEGATED_SUCCESS) for m in rx.finditer(note)]
    found: list[str] = []
    for match in sorted(hits, key=lambda m: m.start()):
        words = re.findall(r"[\w']+", note[:match.start()])[-_LOOKBACK_WORDS:]
        if _NEGATOR.search(" ".join(words)):
            continue
        found.append(" ".join(match.group(0).lower().split()))
    return found


def note_guard(judged: Result, note: str | None) -> tuple[Result, str | None]:
    """Downgrade a PASS whose note describes a failure to INCONCLUSIVE; else pass through."""
    terms = failure_terms(note)
    if judged is Result.PASS and terms:
        return Result.INCONCLUSIVE, NOTE_DISAGREES.format(
            terms=", ".join(dict.fromkeys(terms)), note=note)
    return judged, note
