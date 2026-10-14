# Manifest - TA16 recall.json producer

Unit: ta16-recall
Contract: qa/contracts/team-loop-acceptance.md TA16
Tier: M
Fix cycle: 5
Executor: maker
Status: checked-PASS
Branch: wave/ta16-recall

## Change

TA16 needed `qa/evidence/t206-review-live/recall.json` but nothing produced it. Added
`scripts/review_recall.py` (CLI), `stages/review_recall.py` (arithmetic; reuses `RECALL_BASIS`
from acceptance_comparison and `DENOMINATOR_PROVENANCE` from schema/bench), `schema/review_recall.py`,
`tests/test_review_recall.py` (fixtures only, no model, no browser). Runbook TA16 row updated
with the exact command. Output labels the basis "AI-assisted video review, not independent",
independent=false, no threshold, "measured on N videos".

## Limits

Item-to-oracle matching is a human judgement supplied as matches.json; the script does not
guess. The oracle corpus and the three stored VideoReview JSONs are owner-supplied. Not run
on live data. Doctor reports 1 violation; output is dominated by decision-citation lines, and I
could not attribute it to this change (no finding names these files). Checker to confirm
against master.
