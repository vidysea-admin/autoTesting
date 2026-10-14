# Manifest — tv9-draft-flows

**Unit:** TV9 — the analyze route writes the adjudicated video flows into the FlowSpec as DRAFT (unblocks the strict xfail on T-206 TA4).
**Contract:** `qa/contracts/team-video-review.md` TV9 (R37); `review-gate.md`; `reconcile.md` RC3.
**Goal task:** T-206 / T-169
**Status:** ready-for-check
**Fix cycle:** 2
**Branch:** wave/tv9-draft-flows

## Built
- `src/autotester/stages/analysis_flows.py::propose_draft_flows` — `VideoAnalysis` -> `flowspec_from_observation` -> narration verified (RC3) -> `merge_flowspec` -> save. No new model call, no prompt, no approval step. One flow id, one row. An APPROVED spec is returned untouched (None).
- `src/autotester/ui/routes_sources.py::_save_analysis_outputs` calls it before the screen-map refresh.
- `tests/test_analysis_flows.py` — DRAFT flows carry source_id; re-run idempotent and keeps a hand-made flow; APPROVED spec bytes unchanged.

## Evidence
- pytest: test_analysis_flows, test_ui_sources, test_merge_flowspec, test_analyze_video, ingest neighbours: 88 passed. ruff clean. doctor: same 1 violation as master.

## Not in this unit
- T-206 TA4 xfail removal: lives on `wave/t206-rig`; its rig needs a `media.json` and a fake vision provider on the analyze route (the test as written uploads unprepared fake mp4s, so the route still refuses with "run prep on the HOST"). `expand` over a DRAFT-only spec and the "no baseline" phrase for the run_review path are not touched here.

## Fix cycle 2 (checker FAIL cycle 1)
- Every flow retained: `retain_distinct` collapses only byte-identical repeats; same-name/different-steps flows get a stable content id (test_same_named_flows_with_different_steps_are_all_retained, idempotent re-run).
- Hand-corrected flow in a DRAFT spec untouched on re-run: test_a_hand_corrected_flow_inside_a_draft_spec_is_untouched.
- "No baseline to compare" on the run_review path already exists on master (`video_review_render.BASELINE_NOTE`, md+html+view): tests/test_video_review_guards.py::test_tv9_review_says_no_baseline_to_compare_and_never_matches_the_product. No change needed.
- expand over a DRAFT-only spec: NOT buildable here. `expand`/`propose_cases` call `require_reviewed`; review-gate R5 says relaxing it is a separate L unit (D-073) and video flows are kind=None (unreconciled). Recorded as strict xfail test_expand_over_a_draft_only_spec_generates_cases; needs Umesh to authorize that unit.
