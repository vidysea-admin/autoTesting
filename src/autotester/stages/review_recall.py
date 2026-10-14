"""Score stored video reviews against an oracle corpus into a `ReviewRecall` (TA16).

No model call. Review items become `Finding`s whose `matched_bug_id` is set by deterministic
lexical overlap with the oracle rows (the same `Finding.matched_bug_id` link that
`acceptance_comparison` reads); a human `matches` mapping may override it.
"""

from __future__ import annotations

import hashlib
import re

from autotester.schema.bench import DENOMINATOR_PROVENANCE, BenchCorpus, Finding
from autotester.schema.review_recall import OracleRef, ReviewRecall
from autotester.schema.video_review import VideoReview
from autotester.stages.acceptance_comparison import RECALL_BASIS

HIGH = "S1"
EXPECTED_HIGH = 13
MIN_DISTINCT = 2
MIN_COVER = 0.6
MAX_ROW_FRACTION = 0.2
MATCH_METHOD = (
    "automatic lexical: screen match + >=2 distinctive tokens, conservative, untuned")
_GENERIC = frozenset({
    "error", "toast", "duplicate", "shown", "shows", "showing", "failed", "fail", "wrong",
    "incorrect", "missing", "broken", "displayed", "issue", "bug", "button", "after", "before",
    "text", "message", "click", "user", "form", "submit", "entry", "data", "list", "listed",
})
_NEGATING = frozenset({"correct", "correctly", "works", "working", "successfully", "fine", "ok",
                       "expected", "properly"})
_STOP = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "are", "was", "for", "with",
    "from", "at", "as", "by", "it", "this", "that", "not", "be", "has", "have", "page", "screen",
    "when",
})


class RecallInputError(ValueError):
    """The oracle, reviews or matches do not fit together; no number is produced."""


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", text.lower()) if t not in _STOP}


def _screen(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _distinctive(rows: dict[str, set[str]]) -> set[str]:
    """Hint tokens that are not generic defect words and occur in few oracle rows (IDF-style)."""
    cap = max(1, int(MAX_ROW_FRACTION * len(rows)))
    counts: dict[str, int] = {}
    for hint in rows.values():
        for t in hint:
            counts[t] = counts.get(t, 0) + 1
    return {t for t, c in counts.items() if c <= cap and t not in _GENERIC}


def review_findings(reviews: list[VideoReview], oracle: BenchCorpus) -> list[tuple[str, Finding]]:
    """(item id, Finding) per review item; `matched_bug_id` set conservatively, no model.

    A pair matches only when the item's screen equals the row's location (normalised; either
    side empty means no match) AND the item's `seen` shares >= MIN_DISTINCT distinctive
    tokens with the row's `detect_hint` AND covers >= MIN_COVER of the hint tokens. An item
    that reads as "works correctly" never matches. One item takes at most one row and one row
    at most one item (best first). Doubt leaves the item unmatched: unconfirmed, the row
    missed (D-094)."""
    rows = {b.id: _tokens(b.detect_hint) - _tokens(b.location) for b in oracle.seeded_bugs}
    where = {b.id: _screen(b.location) for b in oracle.seeded_bugs}
    distinct = _distinctive(rows)
    items = [i for r in reviews for i in r.items]
    scored = []
    for k, item in enumerate(items):
        toks = _tokens(item.seen)
        screen = _screen(item.screen)
        if toks & _NEGATING or not screen:
            continue
        for bug_id, hint in rows.items():
            shared = toks & hint
            if (where[bug_id] == screen and hint and len(shared & distinct) >= MIN_DISTINCT
                    and len(shared) / len(hint) >= MIN_COVER):
                scored.append((len(shared) / len(hint), len(shared), k, bug_id))
    chosen: dict[int, str] = {}
    used: set[str] = set()
    for _, _, k, bug_id in sorted(scored, key=lambda t: (-t[0], -t[1], t[2], t[3])):
        if k not in chosen and bug_id not in used:
            chosen[k] = bug_id
            used.add(bug_id)
    return [(item.id, Finding(text=f"{item.screen}: {item.seen}", matched_bug_id=chosen.get(k),
                              reported_at_s=item.time_s))
            for k, item in enumerate(items)]


def _auto_matches(reviews: list[VideoReview], oracle: BenchCorpus) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for item_id, finding in review_findings(reviews, oracle):
        if finding.matched_bug_id:
            matches.setdefault(finding.matched_bug_id, []).append(item_id)
    return matches


def score_reviews(
    reviews: list[VideoReview], oracle: BenchCorpus, oracle_bytes: bytes,
    matches: dict[str, list[str]] | None = None, severity: str = HIGH,
    expected_n: int | None = EXPECTED_HIGH,
) -> ReviewRecall:
    """Recall = rows at `severity` with >=1 matched item / rows at `severity`.

    `matches` is an optional human override of the automatic matching."""
    if not reviews:
        raise RecallInputError("no reviews supplied")
    rows = {b.id: b for b in oracle.seeded_bugs}
    targets = sorted(b.id for b in oracle.seeded_bugs if b.severity.value == severity)
    if expected_n is not None and len(targets) != expected_n:
        raise RecallInputError(
            f"oracle has {len(targets)} {severity} rows, TA16 expects {expected_n}")
    item_ids = [i.id for r in reviews for i in r.items]
    if len(set(item_ids)) != len(item_ids):
        raise RecallInputError("duplicate review item ids across the supplied reviews")
    method = "human override" if matches is not None else MATCH_METHOD
    if matches is None:
        matches = _auto_matches(reviews, oracle)
    bad = [o for o in matches if o not in rows]
    bad_items = [i for ids in matches.values() for i in ids if i not in set(item_ids)]
    if bad or bad_items:
        raise RecallInputError(f"matches name unknown oracle ids {bad} / item ids {bad_items}")
    found = [t for t in targets if matches.get(t)]
    matched_items = {i for ids in matches.values() for i in ids}
    unconfirmed = [i for i in item_ids if i not in matched_items]
    return ReviewRecall(
        id=f"recall_{oracle.id}",
        claim=f"measured on {len({r.source_id for r in reviews})} videos",
        oracle=OracleRef(
            corpus_id=oracle.id, mode=oracle.mode,
            provenance=DENOMINATOR_PROVENANCE.get(oracle.mode, "unknown"),
            recall_basis=RECALL_BASIS.get(oracle.mode, "unknown"), severity=severity,
            file_sha256=hashlib.sha256(oracle_bytes).hexdigest(),
        ),
        match_method=method,
        match_thresholds={"min_distinctive_tokens": MIN_DISTINCT, "min_hint_coverage": MIN_COVER,
                          "max_row_fraction": MAX_ROW_FRACTION},
        n=len(targets), k=len(found), recall=len(found) / len(targets) if targets else None,
        found_ids=found, missed_ids=[t for t in targets if t not in found],
        matches={k: v for k, v in sorted(matches.items()) if v},
        items_total=len(item_ids), unconfirmed_ids=unconfirmed,
        unconfirmed_count=len(unconfirmed),
        sources=sorted({r.source_id for r in reviews}), review_ids=[r.id for r in reviews],
        redaction_windows={r.source_id: [(w.start_s, w.end_s) for w in r.redaction_windows]
                           for r in reviews},
        not_reviewed={r.source_id: list(r.not_reviewed) for r in reviews},
        review_status={r.source_id: r.status for r in reviews},
        calls=sum(r.calls for r in reviews), cost_usd=sum(r.cost_usd for r in reviews),
    )
