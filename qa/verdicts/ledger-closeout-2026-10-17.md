# Verdict - ledger-closeout-2026-10-17

**Verdict:** PARTIAL - 5 of 8 CONFIRMED-FIXED (rows flipped); 3 NOT-FIXED (left open)
**Cycle checked:** 0
Bound to: D:/autoTesting, master fcedc9f4. Mode A-style ledger close-out, read-only toward code. The maker fact files (.work/facts-c1.md, .work/facts-c2.md) were treated as claims; every line below was read or run by the checker.
Policy-Version: proportional-verification/2026-10-15.12

## Verification run
- `uv run pytest tests/test_run_approval_grant_budget.py tests/test_explore_consent.py tests/test_citations.py tests/test_bench.py tests/test_permission_coverage.py tests/test_acceptance_comparison.py` -> 138 passed (one pass, no full suite).
- `uv run autotester doctor` -> 3 violations (root clutter only); citation findings are advisory (D-087).
- Falsification floor: 1 per claimed-fixed code issue, each in a throwaway copy of `git archive HEAD` under the scratchpad (outside the repo), green before, red after, copy deleted.

## Per issue
| id | verdict | evidence |
|---|---|---|
| AT-653 | CONFIRMED-FIXED | schema/bench.py:36,49 provenance; :16-20 per-mode denominator; score() returns recall/detection `None` + `*_unavailable_reason`, plus `ordering` in the scorecard. Falsify: recall else-branch `None`->`0.0` -> 5 red in tests/test_bench.py (test_unknown_truth_prevents_independent_recall_even_with_known_subset). Artifact side scripts/check_acceptance_comparison.py + tests/test_acceptance_comparison.py green. |
| AT-663 | CONFIRMED-FIXED | qa/contracts/coverage.md:133 V9; .goal T-171 `done`; stages/crawl_coverage.py::_permitted_coverage (denominator = permitted surface, holes listed with closed-set reasons, screens-reached disclosure when no surface). Falsify: `permitted_total = len(permitted)`->`done` -> 5 red (test_the_denominator_is_the_permitted_surface_not_the_screens_reached). |
| AT-654 | CONFIRMED (resolved by owner decision, no code owed) | The row's expected is a HUMAN_GATE. Answered: docs/DECISIONS.md D-088 item 3 (Umesh 2026-10-12), production stays refused for typing. Code matches: stages/explore_consent.py:160-164; projects/pathlynks/project.json:11 `production: true`. Falsify: `and approval.production`->`and False` -> test_typing_is_refused_against_a_production_approval red. |
| ISS-d063-grant-budget-1 | CONFIRMED-FIXED | 1dc74b2b (`usable` filtered by `r.scope == scope`) and 2e9b3bf8/AT-759 (non-credential paths see human rows only). Falsify (2): usable->all rows reds test_an_account_row_is_not_reused_for_a_different_credential_scope; human->all rows reds test_a_credential_free_run_cannot_reuse_an_account_derived_row. consent.md CN5 already carries the D-068 option-B amendment, so the wording agrees. |
| ISS-d063-grant-budget-3 | CONFIRMED-FIXED | 1dc74b2b: `probes` flows covering_approval -> `_require`; core/consent.py refuses "probes N > approved M"; grant form exposes max_probes. Falsify: `probes=probes`->`probes=0` -> 3 red (test_a_probe_less_human_row_is_refused_before_a_fill_run). |
| AT-710 | NOT-FIXED | Code half is real: ledger/citations.py wired at doctor.py:270,283-284; falsify: drop `check_decision_citations` from the doctor tuple -> test_doctor_run_includes_the_citation_check red (the copy also shows test_the_real_tree_has_no_dangling_citation red, which needs docs/ and is red in the copy before the edit too). But the row's `expected` part (1) is a real appended write-policy entry, and no such entry exists: D-053 sets the ALLOW_WRITES ceiling only and states no project is flipped, while projects/pathlynks/project.json:10 is `allow_writes`. Human-gated (classifier blocked the append, row text). Left open. |
| AT-718 | NOT-FIXED | A placeholder does not satisfy the row as written. The citations now read `WP-DECISION (NOT YET WRITTEN ...)` (qa/gates/at654-...:16, pathlynks-user-account-first.md:39,43,46,75, write-policy-tier.md:103-111), so they no longer resolve to the wrong entry and L10 now guards the recurrence. But `expected` (1) (write the entry) is undone, and (2) also says living-ledger.md exemption (a) "D-056 did not exist" must be rewritten: qa/contracts/living-ledger.md:159 is unchanged. That file is checker-owned, so the checker should amend it (separate contract-maintenance step, not done here). Left open. |
| AT-740 | NOT-FIXED | `expected` is "write the write-policy entry FIRST, then re-point the seven citations to that number in one commit". Neither happened; the seven citations were turned into unnumbered placeholders. This is a stable interim state, not the fix. AT-710's citations.py is the durable guard and is in place. Left open, human-gated with AT-710/AT-718. |

## Residual (low, non-blocking, no row filed)
- qa/gates/at654-d029-dev-only-vs-production-pathlynks.md still reads `Status: OPEN` although D-088 item 3 answered it.
- AT-710/718/740 close together once Umesh appends (or permits) the Pathlynks write-policy entry and the placeholders are replaced with its D-number.

## Ledger
Five rows appended to qa/issues.jsonl (latest row per id wins; `status: verified`, `verified_by: checker`, `verified_date: 2026-10-17`): AT-653, AT-663, AT-654, ISS-d063-grant-budget-1, ISS-d063-grant-budget-3. No row for AT-710/718/740. No code, contract or bench file touched.

Metrics: start=2026-10-17T00:00:00 end=2026-10-17T00:00:00 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=7 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
