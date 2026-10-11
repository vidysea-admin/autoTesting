# Verdict - t125-catalog - fix cycle 4 - coordinator A

Cycle checked: 4
Verdict path: qa/verdicts/t125-catalog.md (coordinator A of a dual check; blind to B)
Bound to: D:/autoTesting/.worktrees/t125-cycle4 (branch codex/t125-cycle4)
Heads judged: source 62a45c6a, manifest 1e6cd1e0, app.py registration 52bba0b7, contract fold 778b5f86 (mine). Base bd2fe8f4.
Policy: proportional-verification/2026-10-06.6 (pin) with the .7 rules for an in-flight unit.
Contract judged: qa/contracts/catalog.md CT1-CT9 + CN10 (consent.md) + the "Standard packs (AT-588, additive)" section, folded verbatim from 3da63550 by me in 778b5f86 (verify command now lists tests/test_catalog_packs.py).

## Check plan (step 0)

| Signal | Check | Done |
|---|---|---|
| Logic changed (catalog stage, run path, budget) | affected tests via the one full suite + falsification floor | yes |
| UI changed (`ui/routes_catalog.py`, `routes_report.py`, project page link) | live browser walk of the touched screens | yes (see LIVE-BROWSER) |
| Security trigger: `stages/run_budget.py`, `ui/run_execution.py`, `stages/parallel_run.py` (CN10 run approval, D-018) | dual check (this is A) + ONE full suite | yes, suite_runs=1 |
| Data artifact / prompt change | none | not applicable |
| external-ui persona walk | operator diagnostic page; no spec user type maps to it | skip |

TIER: L - `src/autotester/stages/run_budget.py:49` (approval snapshot) and `:55` (`require_approval`), plus the budget debit in `ui/run_execution.py`, sit on the HMAC run-approval path (CN10/D-018). Dual check required; this verdict is A only.

## Results per criterion (each re-run by me)

Falsification method: a `git archive HEAD` copy per mutant (scratchpad `mut/mNN`), the named node(s) run green in the COPY first, then one single-hunk edit, red run, restore, green run. The bound tree was never edited. 22 mutants, all green-before / red-after / restored-green.

| Crit | Result | Evidence |
|---|---|---|
| CT1 pure, deterministic | MET | `test_catalog_is_pure_same_inputs_same_output[...]` in the suite. m10 (`created_at` = now() on the approved branch) RED at `[approved]`. |
| CT2 one entry per class | MET | `test_every_case_class_gets_exactly_one_entry_*`. m11 (drop first class) RED `assert 14 == 15`. |
| CT3 closed BlockedReason | MET | m12 (blocked entry with `blocked_reason=None`) RED `assert None is not None` in `test_blocked_entries_always_carry_a_closed_reason`. |
| CT4 no FlowSpec, page says so | MET | m13 (wrong reason) RED `test_no_flowspec_blocks_every_class_no_flowspec`; m14 (page label dropped) RED `test_no_flowspec_page_renders_the_reason_on_every_row...`. |
| CT5 key named, never the value | MET | m15 (action omits key) RED in stage and UI tests. Browser: seeded `.env` value absent from the served catalog HTML (`leaks_env_value: false`). |
| CT6(1) dispatch order | MET | m01 (tiers reversed) RED: `test_tiers_to_run_runs_static_then_behavioural_in_order`, `..._observed_via_call_order...`, `test_real_trigger_orders_tiers_...[1]` (`assert 'case_8bb0..' == 'case_5b06..'`). |
| CT6(2) never skip | MET | m03 (dispatch gated on the tier's runnable count, the old rule) RED `test_real_trigger_orders_tiers_and_persists_blocked_pinned_cases[1,2]`; m02 (`tiers_to_run` drops the empty tier) RED `test_tiers_to_run_keeps_all_tiers_when_static_is_blocked`. Code read: `routes_runs.py::_execute_with_trace` partitions every case by `TIER_BY_CLASS` (a total map), so the executed set equals the stored cases. |
| CT6(3) per-tier counts incl. 0 | MET | m04 (counts omit zero tiers) RED via the `Run` validator's ValidationError in the real-trigger test; m05 (validator off) RED `DID NOT RAISE` in `test_catalog_counts_reject_malformed_measurements`. Browser: run page shows `static: 0, behavioural: 2, adversarial: 5`. |
| CT6(4) failures first | MET | m06 (rank -> 0) RED `assert 17356 < 17125` in `test_run_view_lists_cheap_tier_failures_first_ahead_of_passes`. Browser: `Failures` heading, then `T c_static` (static), `T b_adv` (adversarial), then `Other results`/`T a_pass`. |
| CT7 one Catalog / BlockedReason | MET | `grep -rn "class Catalog\b" src` = 1 and `^class BlockedReason` = 1. m16 (second `class BlockedReason`) RED in both guard tests. |
| CT8 page honest | MET | m17 (bare enum) RED `'no_ground_truth' == 'no ground truth'`; m18 (action text dropped) RED. Browser: 15 class rows, blocked rows show label plus "set GOOGLE_SIGNUP_TOKEN in the repo-root .env". |
| CT9(a) no under-block | MET | m08 (gate disabled) RED `None is MISSING_CREDENTIAL` in `test_same_class_union_includes_secret_fills_with_arbitrary_field_names`. |
| CT9(b) no cross-flow leak | MET | m07 (union keys spec-wide) RED `login blocked on a signup token` in `test_an_oauth_only_unset_secret_blocks_the_pack_not_the_login_rows`. Browser: DEMO_PASSWORD set, GOOGLE_SIGNUP_TOKEN unset: `auth_wrong_creds` and `auth_expired_session` render RUNNABLE and name neither key. |
| CT9(c) declared, never inferred | MET | m09 (keyword rule adds a key for a "Google" step) RED `assert False is True` in `test_a_flow_with_no_auth_field_never_blocks_on_credential`. Code read: `_auth_secret_keys` (catalog.py:36) uses only `PLACEHOLDER_RE` matches over step target/value/note. |
| Packs (AT-588 section) | MET | `tests/test_catalog_packs.py` green in the suite; m22 (OAuth credential check removed) RED in `test_oauth_signup_pack_blocked_missing_credential_names_the_key`. `PackEntry` reuses `BlockedReason` (CT7 guard m16 covers it). |
| CN10 run approval | MET | m19 (`require_approval` no-op) RED `DID NOT RAISE ValueError`; m20 (entry-case budget debit removed) RED across `test_internal_execution_spends_one_budget_across_tiers_and_all_legs[...]`; m21 (approval not deep-copied) RED `assert True is False` in `test_budget_owns_a_snapshot_of_its_approval_not_the_callers_live_object`. No HMAC signing or verification code is in the diff, only budget plumbing; the diff tightens the serial path, which now debits the shared approval-bound budget. |

## Other steps

- Contract verify command: `ruff check src tests scripts` = "All checks passed!" (run by me); `autotester doctor` = `doctor: clean` (run by me in the bound worktree, which carries uncommitted T-171/AT-113 bookkeeping in `.goal/goal.json`, `docs/DECISIONS.md` D-061, `docs/FEATURES.jsonl` F-067, `docs/SNAPSHOT.md`; other units' files, not committed by me). The three catalog test files ran inside the full suite.
- Step 4c diff scope: `git diff bd2fe8f4..HEAD` touches 20 files, all named in the cycle-4 close-out or "What changed" text, plus regenerated `docs/MAP.md`. No function, class, route, export or config key is removed. The removed `def` lines in `tests/test_ui_report.py` are signature compactions; all four tests/helpers are still defined. No assertion removed, no skip/xfail added. Docstrings in `ui/app.py`, `routes_report.py`, `run_execution.py` were shortened (line cap), comment-only.
- Persona walk: skip (operator diagnostic page, no spec user type maps to it).

## Full suite (exactly one; PID 39436 `uv run pytest`, python child 40436, bound worktree, no -q, no -x)

Started 2026-10-07T15:18:34+05:30 (IST). Result line:

`3 failed, 2276 passed, 6 skipped, 14 xfailed, 17 warnings in 3667.39s (1:01:07)`

Attribution (all three BASELINE/LOAD, none T-125-owned; none of their files is in the T-125 diff):
1. `tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered` - BASELINE. In the bound worktree it reads the uncommitted `.goal/goal.json` edit (T-171 `done_check` now `test_permission_coverage.py`, another unit's bookkeeping). On a pristine `git archive bd2fe8f4` it also fails, differently (`assert 81 == 82` task count).
2. `tests/test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus` - BASELINE/LOAD (AT-750/AT-757 class). Re-run alone: 3.71 s and 3.49 s in the bound tree; 3.94 s and 3.39 s on a pristine bd2fe8f4 copy. Same failure on the base. `core/redact*` is not in the diff.
3. `tests/test_video_parallel_sweep.py::test_two_sessions_sharing_a_run_dir_do_not_lose_each_others_video` - LOAD. Re-run alone with `tests/test_redact_wrap_perf.py`: this test passed (the single failure in that run was the perf test).

## LIVE-BROWSER

`qa/evidence/browser-t125-catalog-2026-10-07-checker-a/` (report.json, catalog.png, run.png), written by me, left uncommitted. Instrument: the claude-in-chrome extension was not connected and the Playwright MCP failed to connect, so I drove headless Chromium through the venv's Playwright library against a uvicorn server started from the bound worktree (`PYTHONPATH=<worktree>/src`, seeded scratch root, port 8791, PIDs 11072/43356, stopped by those PIDs). Real interactions: opened the project page, clicked the "Test catalog" link (1 link; landed on /projects/demo/catalog), read 15 class rows and 3 pack rows, opened the run page, asserted failure ordering and counts, requested an unknown project (404). Console errors: 1, the intentional 404 resource load for `/projects/nope/catalog`; none on the real pages. This is a library-driven headless walk, not an MCP browser tool; disclosed as such.

## PROPOSED-ISSUE lines (no ledger rows written; a PASS has no side effects)

PROPOSED-ISSUE: {"severity":"low","feature":"t125-catalog","title":"CT6(3): a missing zero tier in the run's counts is caught only by the Run schema validator (ValidationError in the real trigger), not by a direct assertion that 0 is recorded","evidence":"falsification m04 RED only via ValidationError at routes_runs.py:168; guard test_catalog_counts_reject_malformed_measurements exists (m05 RED when validator off)","type":"coverage-note"}
PROPOSED-ISSUE: {"severity":"low","feature":"process","title":"Full suite took 61 min under 4-way CPU contention; L wall budget (45 min) exceeded and a single pytest process cannot be resumed","evidence":"3667.39s; concurrent pytest in at113-integrate, t125-b-check, at758-759-security worktrees","type":"process"}
PROPOSED-ISSUE: {"severity":"low","feature":"goal-bookkeeping","title":"tests/test_goal_contract_registration.py fails at base bd2fe8f4 (81 vs 82 tasks) and again with the uncommitted T-171 goal.json edit","evidence":"pristine git archive bd2fe8f4: assert 81 == 82; bound worktree: T-171 done_check mismatch","type":"baseline"}
PROPOSED-ISSUE: {"severity":"low","feature":"t125-catalog","title":"Manifest admits no Policy-Version pin existed; its doctor-clean claim holds only with other units' uncommitted bookkeeping present","evidence":"manifest line 8; autotester doctor clean here only with uncommitted .goal/docs files","type":"wording"}

VERDICT: PASS
SCOREBOARD: 11/11 criteria met (CT1-CT9, CN10, AT-588 packs), 0 invariants violated
TIER: L (security trigger: run_budget.py:49/:55 CN10 run-approval path; dual check, coordinator A)
FAILURES: none
CAPABILITY-COVERAGE: 22/22 mutants reproduced green-before (in copy) / red-after / restored-green; every acceptance criterion has at least one named falsification
LIVE-BROWSER: qa/evidence/browser-t125-catalog-2026-10-07-checker-a/ (headless Playwright library, disclosed)
ISSUES-WRITTEN: none (PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: fresh coordinator A, independent of the builder)
EXPLANATION: Every criterion held under my own re-runs: one full suite with 3 failures, all attributable to the base or to load (two identical on pristine bd2fe8f4, one green alone), lint and doctor clean, 22 isolated single-hunk mutants all red for the named reason and green after restore, and a real browser walk of the catalog and run pages. slow: full suite 61 min under 4-way CPU load (process signal, not a product defect). B must also PASS.
Metrics: start=2026-10-07T09:47:39Z end=2026-10-07T11:12:00Z wall_min=84 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=4 mutations=22 cycle=4 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
