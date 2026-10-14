"""Score stored video reviews against an oracle corpus into a `ReviewRecall` (TA16).

No model call. Which review item corresponds to which oracle row is a human judgement, so it
arrives as a `matches` mapping {oracle_id: [item_id, ...]}; this module only does the
arithmetic, validates the ids, and labels the basis via the acceptance-comparison table.
"""

from __future__ import annotations

import hashlib

from autotester.schema.bench import DENOMINATOR_PROVENANCE, BenchCorpus
from autotester.schema.review_recall import OracleRef, ReviewRecall
from autotester.schema.video_review import VideoReview
from autotester.stages.acceptance_comparison import RECALL_BASIS

HIGH = "S1"


class RecallInputError(ValueError):
    """The oracle, reviews or matches do not fit together; no number is produced."""


def score_reviews(
    reviews: list[VideoReview], oracle: BenchCorpus, oracle_bytes: bytes,
    matches: dict[str, list[str]], severity: str = HIGH,
) -> ReviewRecall:
    """Recall = rows at `severity` with >=1 matched item / rows at `severity`."""
    if not reviews:
        raise RecallInputError("no reviews supplied")
    rows = {b.id: b for b in oracle.seeded_bugs}
    item_ids = [i.id for r in reviews for i in r.items]
    if len(set(item_ids)) != len(item_ids):
        raise RecallInputError("duplicate review item ids across the supplied reviews")
    bad = [o for o in matches if o not in rows]
    bad_items = [i for ids in matches.values() for i in ids if i not in set(item_ids)]
    if bad or bad_items:
        raise RecallInputError(f"matches name unknown oracle ids {bad} / item ids {bad_items}")
    targets = sorted(b.id for b in oracle.seeded_bugs if b.severity.value == severity)
    found = [t for t in targets if matches.get(t)]
    matched_items = {i for ids in matches.values() for i in ids}
    unconfirmed = [i for i in item_ids if i not in matched_items]
    wanted = DENOMINATOR_PROVENANCE.get(oracle.mode)
    return ReviewRecall(
        id=f"recall_{oracle.id}",
        claim=f"measured on {len({r.source_id for r in reviews})} videos",
        oracle=OracleRef(
            corpus_id=oracle.id, mode=oracle.mode, provenance=wanted or "unknown",
            recall_basis=RECALL_BASIS.get(oracle.mode, "unknown"), severity=severity,
            file_sha256=hashlib.sha256(oracle_bytes).hexdigest(),
        ),
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
