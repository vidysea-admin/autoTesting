# Verdict - ta16-recall

Cycle checked: 1
Branch: wave/ta16-recall @ ddf68906
Verdict: FAIL (one mechanical fix, plus one flagged design issue)

## Findings
1. BLOCKING - doctor: branch reports 1 violation `stale-generated: docs/MAP.md`; master a172f38a is clean. The branch introduces it (new schema/stage modules not in the generated map). Fix: run `autotester map` and commit docs/MAP.md.
2. DESIGN (should fix) - matches.json is a hand-made item-to-oracle judgement. TA16 does not require a human to do it; it asks for k re-derivable from listed ids and the unconfirmed count. Existing code already carries the oracle-row link as `Finding.matched_bug_id` (schema/bench.py, used by acceptance_comparison._bug_rows and BenchTrial scoring). Review items should be turned into Findings and matched automatically (route/screen/timestamp + text against SeededBug.location/detect_hint, no model call or a provider-judged match), with matches.json kept only as an optional human override. Minimise human dependency.
3. Reuse: PASS. RECALL_BASIS and DENOMINATOR_PROVENANCE are imported, not copied. ReviewRecall/OracleRef are `extra="forbid"`-compatible: OracleRef explicit; ReviewRecall inherits Artifact - confirm Artifact base forbids extras.
4. Shape vs TA16: PASS. k of n (S1), missed_ids, unconfirmed_count, redaction_windows, not_reviewed, "measured on N videos", threshold "none", independent=false with "not independent" basis label. Minor: n is derived from the oracle severity filter; if the oracle's S1 count is not 13 nothing flags it.
5. Checks: tests/test_review_recall.py + acceptance comparison tests 18 passed; ruff clean; merge-tree with master clean.
