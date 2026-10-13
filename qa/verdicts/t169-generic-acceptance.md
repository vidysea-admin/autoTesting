# Verdict — t169-generic-acceptance

**Verdict:** PASS (LOCAL criteria GA1-GA4, GA6). GA5 is an open gap owned by unit `proposal-review-ui`. REAL-TARGET GR1-GR4 not evaluated (need Pathlynks data, T-145, human list later; D-089/D-090).
**Cycle checked:** 1
**Contract:** qa/contracts/generic-acceptance.md (folded by this checker from the maker's GA1-GA4)

| Criterion | Result | Evidence |
|---|---|---|
| GA1 both modes via /onboard + orchestrator, other stage absent | PASS | `test_both_modes_end_to_end_without_cli[teaching|url_only]`, `test_entry_path_follows_the_supplied_material` |
| GA2 no duplicate scoring; recall unavailable, FP/time numeric | PASS | `generic_acceptance.py` only calls `bench_from_run`, `build_comparison`, `completeness_problems`; no scoring math; e2e asserts K10 text |
| GA3 slug-driven, seams only | PASS | new `test_harness_reuses_an_onboarded_project_by_slug` (no `/onboard` post on `onboard=False`); module imports no browser/provider |
| GA4 RUN_AUX_FILES fix | PASS | Logic correct: `load_results` skips exactly the two parked files, non-aux JSON still raises. `prune_old_videos` reads via `load_results`, so it is covered. New direct regression test `test_parked_proposals_never_break_load_results` (both directions) |
| GA5 proposal-review UI route | GAP | Required for "no CLI"; harness uses `ModeSeams.review_proposals`. Built separately as `proposal-review-ui` |
| GA6 design rules/neighbours | PASS | generic_acceptance.py 156 lines; ruff clean; doctor clean; 68 passed (generic, acceptance comparison, video retention, orchestrate, bench) |

**Checker additions:** the two tests above (tests/test_generic_acceptance.py), shared `_review` helper.
**Notes:** a second pass with a stub grader that reports no finding gives FP rate "unavailable" honestly; the test does not claim completeness there.
**Defects:** none blocking.
