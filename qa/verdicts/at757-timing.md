# Verdict - at757-timing (AT-757 timing scale for load-sensitive tests)

Date: 2026-10-07 - bound to D:/autoTesting (worktree .worktrees/at757-timing, wave/at757-timing) - checker: fresh subagent, single checker
Cycle checked: 0
Policy: proportional-verification/2026-10-07.7
Reviewed: code c9832b19, manifest 9e9712c8, base 642ab4bd (verified: merge-base HEAD origin/master-at-dispatch = 642ab4bd, ancestor of HEAD)

## Check plan
Logic changed: no (tests only, 7 files + manifest). Plan: (1) read every diff hunk, (2) helper clamp read + 20-case test, (3) falsification in a throwaway copy (synthetic ~10x slower redact scan at scale 1, unset and 2), (4) touched test files, ruff, doctor, (5) importer grep for product code. No UI, no full suite (.7: not a security/prod-write unit). Persona/browser: not applicable.

TIER: L (protected test change: a bound is loosened via a multiplier, `tests/test_*_perf.py` etc.; no src/ file changed). One checker.

## Evidence per check
1. Default scale identical. Read all 5 hunks: crawl `240.0 * timing_scale()`, mc_sessionstart `timeout=60 * timing_scale()`, wrap_perf `bound = 3.0 * timing_scale()`, ignorable_perf `bound = 2.5 * timing_scale()`, video `_WAIT_S = 30.0 * timing_scale()`. At 1.0 each product is numerically equal to the original literal (240.0, 60, 3.0, 2.5, 30.0; `60 * 1.0` is 60.0, equal and valid as a subprocess timeout). Only message text and an import changed otherwise.
2. Clamp. `min(max(value, 1.0), 4.0)`; ValueError and non-finite (nan/inf) -> 1.0; unset/empty -> 1.0 (read tests/timing_scale.py:21-28; tests/test_timing_scale.py 20 passed in my run).
3. No assertion deleted or weakened beyond the multiplier. The wrap_perf superlinear guard `ratio < 3.0` (line ~210) and the ignorable_perf absolute `cjk_time < 15.0` ceiling are untouched; max_screens/max_actions and COMPLETED assertions untouched; `git diff` adds no skip/xfail/importorskip. Note (not a defect): the ignorable_perf 2.5x bound is a fifth bound beyond the four in the ruling text; it is the AT-771 flake, listed in the manifest and in the task brief.
4. Synthetic regression still caught (copy of src/tests/scripts in scratchpad; conftest imports scripts/regression_proof so scripts copied; module path verified as the copy). Mutation: `time.sleep(7.0)` in `Redactor.contains_folded` (~10x the idle scan time). Node: test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus. Mutated: scale unset -> RED `10.67 < 3.0`; scale 1 -> RED `10.50 < 3.0`; scale 2 -> RED `10.40 < 6.0`. Restored: scale 2 -> green (1 passed); scale 1 restored green flaked at 3.43 s and 3.69 s on this loaded host (timing-only, the case this unit exists for). Bound tree untouched.
5. Helper location. `tests/timing_scale.py` is a new tests helper, not conftest.py. `git grep timing_scale -- src scripts qa/hooks` finds no hit; only 5 test files, test_timing_scale.py and manifest/QUEUE/ledger text reference it. Product code never imports it.
6. Runs. Touched files at default scale (test_timing_scale, redact_wrap_perf, redact_ignorable_perf, mc_sessionstart_loop_status, video_parallel_sweep, crawl_inventory_live): all passed except the 500 KB wrap_perf scan (3.25 s vs 3 s, host load). Re-run of wrap_perf + ignorable_perf: scale 1 -> 1 failed (that same node), 29 passed; scale 2 -> 30 passed. `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: clean.
4c. Diff scope: 7 test files + manifest, all listed in the manifest "What changed". Nothing removed or renamed.

CAPABILITY-COVERAGE: 6/6 manifest rows reproduced or read (the 20-case helper test passed; the floor rows by test run, the scale-2 regression row by my own mutation above).
LIVE-BROWSER: not-applicable (no UI path changed)
ISSUES-WRITTEN: none
EXECUTOR: claude (checker: claude-sonnet-subagent)

VERDICT: PASS
SCOREBOARD: 4/4 ruling checks met (default identical, clamp, no weakening, synthetic regression), 3/3 invariants hold (no src import, no conftest edit, ratio guard + 15 s ceiling intact)
EXPLANATION: Every bound equals its original at scale 1.0, the clamp and fallback are as ruled, and nothing but a multiplier was added. A ~10x slower redact scan is red at scale 1, unset and 2 (10.4 s vs the 6 s scaled bound); timing-only flakes at scale 1 pass at scale 2. Full suite not run (policy .7); full-suite trigger: none, pre-push check covers the merged head.
Post-rebase run (head after rebase onto origin/master d4c369b0..6f351e11, scale 2, loaded host): 60 passed, 2 failed - test_mc_sessionstart_loop_status healthy/unhealthy hook tests, caused by the hook's own fixed 15 s loop-status timeout (qa/hooks/mc-sessionstart.ps1:137-141), not by any scaled bound; hook run directly printed 'loop-status: no gaps'. Timing-only host-load, not a FAIL; filed AT-772 (low).
Wording row (low, not a FAIL): the wrap_perf message prints `{bound:g}s`; no action.

Metrics: start=2026-10-07T11:23:00Z end=2026-10-07T11:52:00Z wall_min=29 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7
slow: loaded host, redact scan reruns and the 6-file run took about 20 of the 29 minutes
