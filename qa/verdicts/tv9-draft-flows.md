# Verdict — tv9-draft-flows

**Cycle checked:** 1
**Verdict:** FAIL (TV9 partially met; unit as scoped by its own manifest is clean)
**Commit checked:** a5b7621b (merge-tree vs master 26e68661: clean, no conflicts)

## TV9 clauses
- MET: flows written to FlowSpec as DRAFT with source_id and provenance (test 1).
- MET: pointer/analyze path never edits an APPROVED spec (bytes identical test; propose_draft_flows returns None).
- MET: no weakening of require_reviewed; no new model call, prompt or approval bypass; reuses flowspec_from_observation, verify_narration, merge_flowspec.
- PARTIAL: "every flow retained, none dropped as duplicate" - code dedups by flow id (flow_id(name, source_id)), so two same-named flows from one source collapse to one. No test covers ideal/narrated/variant retention.
- UNMET: "expand over a DRAFT-only spec generates cases" - not tested here.
- UNMET: "no baseline to compare" phrase on the run_review path - not touched.
- UNMET (partly): re-run with a hand-approved individual flow inside a DRAFT spec is untested (only spec-level APPROVED).
The maker's caveat therefore matters: two of TV9's three Verify steps are not exercised.

## Other checks
- (b) PASS. (c) PASS. (d) PASS: stages/analysis_flows.py imports no ui/; ui -> stages only.
- (e) Tests meaningful for what they cover: 3 new tests, 37 passed across test_analysis_flows, test_ui_sources, test_merge_flowspec, test_analyze_video.
- (f) doctor in my worktree and on master both printed "doctor: clean" (only advisory known-disputed D-000/D-005 warnings); could not reproduce the maker's "1 violation". This branch adds none.
- (g) ruff: all checks passed.

---

# Cycle 2

**Cycle checked:** 2
**Commit checked:** 1b81a133 (merge-tree vs master 2f6d9c6a: clean)
**Verdict:** FAIL-on-gate for TV9 clause 2 only; HUMAN_GATE. Clauses 1, 3, 4 PASS. Nothing else blocks.

## Clauses
- Clause 1 (retain every flow): PASS. `retain_distinct` keeps same-named variants under a content id; byte-identical repeats collapse; re-run idempotent (test asserts no third row).
- Clause 3 ("no baseline"): PASS by existing code, `video_review_render.BASELINE_NOTE`, covered by existing guard tests. Not this unit's work.
- Clause 4 (hand-corrected flow untouched): PASS, test added; APPROVED-spec bytes test retained.
- Clause 2 (expand over a DRAFT-only spec generates cases): NOT met, strict xfail.

## Did the maker misread TV9?
No. TV9 says expand "runs over a spec made only of these flows without a human approval and generates cases", and its Verify says run expand over a DRAFT-only spec and assert cases exist. It does not mean "after review" or "expand refuses". review-gate R5 (amended 2026-10-11 on D-070 item 2) and expand X1 state the same intent: a reconciled DRAFT expands exactly as APPROVED. So there is no contract conflict with R5; the contract wants this.

The block is authorization, not contract:
1. D-073 (Umesh): changing `require_reviewed` "is NOT authorized here; it is a separate L unit". The R5 build note says the maker must first append a D-entry whose Changes-authorized names `stages/expand.py`, `stages/eval_compiler.py`, `stages/review.py` (and `ui/routes_learn.py` per X6).
2. R5(b): a spec with any `kind=None` flow still refuses even then. Flows from the analyze route have `kind` unset (unreconciled), so the gate would still raise until reconcile sets `kind`, or Umesh answers R5 open question (ii) ("should an unreconciled DRAFT spec generate too?").

A test that expand works after approving the DRAFT through the existing review route is a useful addition, but it satisfies the old gate, not TV9's "without a human approval", so it does not close clause 2.

## Decision Umesh must make
(1) Authorize the L unit (D-entry naming expand.py, eval_compiler.py, review.py, routes_learn.py), and (2) answer R5 (ii): either let unreconciled DRAFT specs generate, or require the analyze route/reconcile to set `kind` on video flows first. Until then keep the strict xfail; it is the correct honest state.

## Gates
pytest 62 passed, 1 xfailed (analysis_flows, ui_sources, merge_flowspec, analyze_video, reconcile); ruff clean; doctor clean; stages/ imports no ui/; no new model call, prompt or approval bypass.
Recommend: merge as partial delivery of TV9 (clauses 1, 3, 4) with clause 2 held on the HUMAN_GATE above.
