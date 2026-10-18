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
    r"unsuccessful\w*|fro(?:ze|zen)|no\s+longer\s+works?|stopped\s+working|"
    r"(?:does\s+not|doesn't)\s+work|block(?:ed|s)?|stuck|hang(?:s|ing)?|hung|freez\w*|could\s?n[o']t|"
    r"time[ds]?[ -]out|timeouts?|never\s+(?:appear|load|show|render|complet|finish)\w*|"
    r"leak\w*|expos(?:ed|es?|ing)|duplicat\w*|lost|data\s+loss|loss\s+of\s+data|"
    r"blank\s+(?:page|screen)|went\s+blank|(?:another|other)\s+user'?s|someone\s+else'?s|"
    r"nothing\s+works?|stop(?:s|ped)?\s+responding|won.t\s+load|"
    r"nothing\s+happened(?!\s+to\b)|did\s+nothing|spinner\s+never\s+stops?)\b"
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
# After "or" these start a new clause ("no crash, or the error banner appeared"), not a list item.
_NEW_CLAUSE = frozenset({"the", "this", "that", "these", "those", "it", "they", "there", "we"})
_TOKEN = re.compile(r"[\w']+|,")
# A clause ends at sentence punctuation, so a negator never reaches into the next sentence.
_CLAUSE_BREAK = re.compile(r"[.;:!?\n]")


NOTE_DISAGREES = (
    "judge answered PASS but its own note describes a failure ({terms}): result and reasoning "
    "disagree, so the PASS is not trusted (fail closed, core-invariants C12). Held as "
    "INCONCLUSIVE for a human to look at; judge note: {note!r}."
)

# Expected-error exemption (deliberately conservative, grader-expected-error cycle 3). It applies
# only to a WHOLE note that states the outcome was expected ("as expected" / "as intended" /
# "as designed") and contains no contrary marker anywhere. Otherwise nothing is exempted and the
# note is held as usual: a false INCONCLUSIVE is acceptable, a false PASS is not.
# T-136 G3: "correctly rejected" / "appropriately blocked" state that the rejection was the right
# outcome; the adverb counts only when it sits directly on a rejection verb, never on its own
# ("invalid total shown correctly formatted" stays held).
_EXPECTED_CUE = re.compile(
    r"\bas\s+(?:expected|intended|designed)\b|"
    r"\b(?:correctly|properly|appropriately|rightly)\s+"
    r"(?:rejected|blocked|prevented|denied|refused)\b", re.IGNORECASE)
_CONTRARY = re.compile(
    r"\b(?:but|however|also|anyway|although|yet|instead|not|never|no|missing|absent|without|"
    r"generic|unexpected\w*|deleted|submitted|saved|charged|leaked|other|wrong|incorrect|crash\w*|"
    r"froze|valid)\b|\b500\b|n't\b", re.IGNORECASE)
_EXEMPT_TERMS = frozenset({"error", "errors", "denied", "reject", "rejects", "rejected",
                           "rejection", "rejections", "invalid", "incorrect", "wrong",
                           "block", "blocks", "blocked"})
# "invalid" / "incorrect" / "wrong" are exempt only when they qualify an input ("invalid email",
# "incorrect password"), not a result ("wrong amount", "invalid total").
_INPUT_QUALIFIERS = frozenset({"invalid", "incorrect", "wrong"})
_INVALID_INPUTS = frozenset({"email", "password", "input", "credentials", "username", "format",
                             "entry", "phone", "date", "login", "characters", "address", "code"})
_QUALIFIED_INPUT = re.compile(
    r"\b(?:wrong|incorrect)\s+(?:" + "|".join(sorted(_INVALID_INPUTS)) + r")\b", re.IGNORECASE)


def _exemptible(note: str) -> bool:
    """True when the whole note says the error was expected and nothing contradicts it."""
    # "wrong/incorrect <input>" names the bad input the case sent, not a contrary outcome
    return (bool(_EXPECTED_CUE.search(note))
            and not _CONTRARY.search(_QUALIFIED_INPUT.sub("", note)))


def _exempt(note: str, end: int, term: str) -> bool:
    if term not in _EXEMPT_TERMS:
        return False
    if term in _INPUT_QUALIFIERS:
        following = re.match(r"\s*(\w+)", note[end:])
        return bool(following) and following.group(1).lower() in _INVALID_INPUTS
    return True


def failure_terms(note: str | None, expects_error: bool = False) -> list[str]:
    """The un-negated defect words in `note`, in order; empty when it reads clean.

    `expects_error`: the case expects an error AND the judge said defect_observed=false; the
    expected-error terms are then dropped from a note that passes `_exemptible`."""
    if not note:
        return []
    expects_error = expects_error and _exemptible(note)
    hits = [m for rx in (_DEFECT_LEXICON, _NEGATED_SUCCESS) for m in rx.finditer(note)]
    spans = [m.span() for m in _NEGATED_SUCCESS.finditer(note)]
    found: list[str] = []
    for match in sorted(hits, key=lambda m: m.start()):
        if _negated(note, match.start(), match.end(), spans):
            continue
        term = " ".join(match.group(0).lower().split())
        if expects_error and _exempt(note, match.end(), term):
            continue
        found.append(term)
    return found


def _defect_follows(note: str, start: int, stop: int) -> bool:
    """True when the item after "or"/"nor" is a defect word, not "two" / "not" / a new clause."""
    for tok in _TOKEN.finditer(note, start, stop):
        word = tok.group(0).lower()
        if word in _NEW_CLAUSE:
            return False
        if word not in _FILLERS:
            return bool(_DEFECT_LEXICON.match(note, tok.start()))
    return False


def _list_closes(note: str, end: int) -> bool:
    """True when the list continues after `end` and closes with "or"/"nor" in the same clause.

    A comma extends a negation only inside such a list ("no error, rejection, or missing
    element"); "no error, broken layout" is two statements, so the second is un-negated."""
    stop = _CLAUSE_BREAK.search(note, end)
    for tok in _TOKEN.finditer(note, end, stop.start() if stop else len(note)):
        word = tok.group(0).lower()
        if word in ("or", "nor"):
            return _defect_follows(note, tok.end(), stop.start() if stop else len(note))
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
        if word in ("or", "nor") and nxt in _NEW_CLAUSE:
            return False
        seen_or = seen_or or word in ("or", "nor")
        if word == "," and not (seen_or or _list_closes(note, end)):
            return False
        if word not in _FILLERS and not _DEFECT_LEXICON.fullmatch(word):
            return False
    return False


def note_guard(judged: Result, note: str | None, expects_error: bool = False
               ) -> tuple[Result, str | None]:
    """Downgrade a PASS whose note describes a failure to INCONCLUSIVE; else pass through.

    Backstop only: `grade()` consults it when the judge omitted the structured
    `defect_observed` field (when present, that field decides)."""
    terms = failure_terms(note, expects_error)
    if judged is Result.PASS and terms:
        return Result.INCONCLUSIVE, NOTE_DISAGREES.format(
            terms=", ".join(dict.fromkeys(terms)), note=note)
    return judged, note
