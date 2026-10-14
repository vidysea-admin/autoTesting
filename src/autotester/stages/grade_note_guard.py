"""The notes-vs-verdict cross-check: a judge PASS whose own note describes a defect is not a PASS.

One job (AT-997, found live in T-181: the default rubric returned PASS on a seeded broken login
while both judges' notes said "reproduced the expected bug ... invalid credentials error"). The
judge's `result` is one enum field; its `note` is the reasoning. When they disagree the stage
cannot know which is right, so it fails closed (core-invariants C12): the PASS is held as
INCONCLUSIVE for a human, never persisted as PASS. A FAIL/INCONCLUSIVE answer is untouched.

The test is deliberately conservative toward INCONCLUSIVE: a correct PASS whose note merely
mentions an expected error (a negative case) is also held. That is the cheaper error. A defect
word preceded in its own clause by a negator ("no errors", "without any bug", "did not fail")
does not count.

T-169 real run: negation now binds to the defect word it directly governs (see `_negated`) instead
of a 3-word lookback, which misfired on 7 of 8 held PASSes in the real PathLynks run. It does not
reach across "and", a verb or an unrelated noun, so "no spinner and an error is shown" is held.
The structured `Judgment.defect_observed`
field is the primary signal; this module is the backstop when it is absent.

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
# Negation binds only to the defect word it directly governs. Walking back from a defect term, the
# only tokens allowed between it and a negator are fillers ("an", "evidence of", "product"), list
# separators ("," / "or") and other defect words ("No error, rejection, wrong result, or missing
# element"). Anything else - "and", a verb, a noun that is not a defect ("no confirmation, error
# shown") - ends the scope, so the term counts as un-negated. When in doubt the term is flagged:
# a false INCONCLUSIVE is far cheaper than a false PASS (C12).
_NEGATORS = frozenset({"no", "not", "without", "zero", "nor", "never", "none", "nothing",
                       "neither"})
_PHRASE_NEGATORS = {"free": "of", "absence": "of", "rather": "than", "instead": "of",
                    "other": "than"}
_FILLERS = frozenset({"a", "an", "any", "the", "of", "evidence", "evidenced", "product", "observed",
                      "sign", "signs", "trace", "visible", "visibly", "apparent", "other", "than",
                      "result", "results", "element", "elements", "content", "message",
                      "messages", "or", ",", "is", "are", "was", "were", "be", "been",
                      "single", "such", "kind", "types", "type"})
_TOKEN = re.compile(r"[\w']+|,")
# A clause ends at sentence punctuation, so a negator never reaches into the next sentence.
_CLAUSE_BREAK = re.compile(r"[.;:!?\n]")

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
    spans = [m.span() for m in _NEGATED_SUCCESS.finditer(note)]
    found: list[str] = []
    for match in sorted(hits, key=lambda m: m.start()):
        if _negated(note, match.start(), match.end(), spans):
            continue
        found.append(" ".join(match.group(0).lower().split()))
    return found


def _list_closes(note: str, end: int) -> bool:
    """True when the list continues after `end` and closes with "or"/"nor" in the same clause.

    A comma extends a negation only inside such a list ("no error, rejection, or missing
    element"); "no error, broken layout" is two statements, so the second is un-negated."""
    stop = _CLAUSE_BREAK.search(note, end)
    for tok in _TOKEN.finditer(note, end, stop.start() if stop else len(note)):
        word = tok.group(0).lower()
        if word in ("or", "nor"):
            return True
        if word != "," and word not in _FILLERS and not _DEFECT_LEXICON.fullmatch(word):
            return False
    return False


def _negated(note: str, start: int, end: int, success_spans: list[tuple[int, int]]) -> bool:
    """True when a negator directly governs the term at `start` (see the scope rule above).

    A negator that is itself part of a negated-success phrase ("did not load") reports a
    defect, so it never negates a later term."""
    clause_start = max((m.end() for m in _CLAUSE_BREAK.finditer(note[:start])), default=0)
    toks = list(_TOKEN.finditer(note, clause_start, start))
    seen_or = False
    for i in range(len(toks) - 1, -1, -1):
        word = toks[i].group(0).lower()
        nxt = toks[i + 1].group(0).lower() if i + 1 < len(toks) else ""
        if (word in _NEGATORS or word.endswith("n't")
                or _PHRASE_NEGATORS.get(word) == nxt):
            return not any(a <= toks[i].start() < b for a, b in success_spans)
        seen_or = seen_or or word in ("or", "nor")
        if word == "," and not (seen_or or _list_closes(note, end)):
            return False
        if word not in _FILLERS and not _DEFECT_LEXICON.fullmatch(word):
            return False
    return False


def note_guard(judged: Result, note: str | None) -> tuple[Result, str | None]:
    """Downgrade a PASS whose note describes a failure to INCONCLUSIVE; else pass through.

    Backstop only: `grade()` consults it when the judge omitted the structured
    `defect_observed` field (when present, that field decides)."""
    terms = failure_terms(note)
    if judged is Result.PASS and terms:
        return Result.INCONCLUSIVE, NOTE_DISAGREES.format(
            terms=", ".join(dict.fromkeys(terms)), note=note)
    return judged, note
