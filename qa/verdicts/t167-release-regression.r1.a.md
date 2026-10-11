# Verdict — t167-release-regression, repair coordinator A, cycle 1

Cycle checked: 1 · Resume: 0 of 2 · Retry: 0 · Policy-Version: proportional-verification/2026-10-10.9
Bound to D:/autoTesting. Checked sha 102a4b91 (repair range 667a0c64..102a4b91, product commit 00f25489). Dual check, side A: no ledger rows, no goal close, no merge, no push.

## Plan
Tier L (dependency bump + approval gate; dual-trigger src/autotester/core/consent.py:182). Repair touched stages/orchestrate_gate.py and stages/release.py, so RR1..RR6 were all re-run (RR1/RR3/RR4/RR6 import or scan those files). Own RR2 reproduction, one falsification, repair diff in full, whole-unit scope scan, the owed checker full suite.

VERDICT: FAIL
SCOREBOARD: 6/6 criteria met on their own commands; the owed full suite is red on a unit-owned test (below)
TIER: L (dependency bump + approval gate; security trigger src/autotester/core/consent.py:182)

FAILURES:
- [suite] sev: medium · the unit's new `autotester release` / `release-log` commands register two advice sites that `tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed` does not list (`EXPECTED_SITES`, test file line ~159; `EXPECTED_SITE_COUNT = 19` at line 192). · I ran `python -m pytest tests/test_cli_advice_resolves.py` in a git-archive copy of 102a4b91: `AssertionError: advice sites changed. gone: []  new: [('cli_release.py','release'), ('cli_release.py','release-log')]`; the same file on a git-archive of master: 28 passed. It also failed alone in the suite's isolated re-run. The red is owned by this unit's cli_release.py and is not in the baseline-red list. It is not a cycle-1 repair defect (the repair diff never touches cli_release.py): it is a cycle-0 leftover that no earlier check could see because the unit's one owed full suite had not run. · fix direction: add the two `("cli_release.py", ...)` pairs to `EXPECTED_SITES` and raise `EXPECTED_SITE_COUNT` to 21 (test-only edit; read the test's own instruction first). · PROPOSED-ISSUE index: P1

## RR2 reproduction (own script, throwaway copy, real multi-step Cases, signed approval)
Cycle-0 failure re-built: scope.json written by hand, real plans (3 cases x 5 steps = cost 15), declared max_actions=3, wall 24 s, approval of 3 actions. Result: REFUSED with `ApprovalRequired` ("narrower than this run"), also with a human yes; 0 EXECUTE calls; the run directory holds only the forged scope.json (no checkpoint.json, state.json, trace). Honest scope: pauses at CONFIRM, a yes completes it, so an honestly frozen scope stays resumable. Further probes, all fail closed or harmless: approval one action short (refused); declared 1e9 (refused); cases grown in the store after an honest freeze (refused on resume: the cost is re-derived from the store every call, so a stale freeze cannot be widened by editing cases); plans naming cases absent from the store (each costs 1, refused); empty plan list (accepted, executes zero cases, harmless); wall-clock under-declared (refused); on-disk bool/str max_actions (refused), negative/zero/float (schema ValueError at load, nothing ran). Order: release_preflight is the first line of run_or_resume (orchestrate.py:273); StageContext construction and `_frozen_or_new` write nothing (tree unchanged around each refusal).
Re-costing basis equals what runs: EXECUTE iterates `scope.case_ids` (deduped plan cases) and `plans_cost` dedupes the same set.

## Falsification (RR2, mine, copy fals1, green before / red after)
`actions = max(scope.max_actions, plans_cost(...))` -> `actions = scope.max_actions` in a copy: my repro S1 turns red by assertion (forged scope accepted); `tests/test_release_gate.py` 1 failed (under_declared...), 2 passed. Extra mutant (copy fals2): `wall_clock_s=max(scope.wall_clock_s, actions*8)` -> `scope.wall_clock_s`: my S8 accepts the forged wall-clock scope (red) but the repo tests (25) stay green: the wall-clock clause is correct but pinned by no test. PROPOSED-ISSUE P2 (low).

## Other criteria
RR1-RR6: manifest pre-check set (11 files, 137 tests) re-run in a copy: 137 passed. RR5: langgraph==1.2.14 at pyproject.toml:17, `autotester doctor` clean, `ruff check src tests scripts` clean. Step 4c: repair diff read in full; the only removal is `_plan_cost` (created in this unit, moved to `plans_cost`, one place); whole-unit diff (19 files) lists no file outside the manifest's What changed.

## Full suite (checker-owned, one run, sha 102a4b91, never partial)
`shard_suite.py --repo ...t167-release-regression --ref 102a4b91 --shards 1` (ceilings: code cap 1; the dispatch later suggested 4 but the complete result already existed on disk, so it was used). Collect proof ok (2889 = 2889). 2865 passed, 19 skipped, 5 failed (2106 s; lock wait about 7 min).
- test_cli_advice_resolves::test_no_advice_site_can_vanish_unnoticed: red alone, passes on master: NEW, unit-owned (F above).
- test_reconcile_schema::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen: red alone, same assertion as the ledgered AT-792 (`None == 'type your email here'`); baseline red.
- test_redact_wrap_perf::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus: 3.30 s vs 3 s bound, passed alone: ledgered AT-725 load flake.
- test_mc_sessionstart_loop_status::test_hook_prints_the_report_and_exits_zero_on_a_healthy_log: passed alone: ledgered AT-858.
- test_explore_modal::test_a_replay_that_lands_elsewhere_is_a_failure_not_a_near_miss: `net::ERR_NO_BUFFER_SPACE` (machine resources), passed alone, and the unit does not touch the explorer: load flake, low row.
Evidence: suite directory in the scratchpad (summary.json, shard-0.log).

PROPOSED-ISSUE: {"severity":"medium","feature":"release-regression","title":"EXPECTED_SITES in tests/test_cli_advice_resolves.py omits cli_release.py release and release-log","evidence":"pytest tests/test_cli_advice_resolves.py on 102a4b91: new [('cli_release.py','release'),('cli_release.py','release-log')]; master passes","regression_check":"scenario or: uv run pytest tests/test_cli_advice_resolves.py"}
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"the wall-clock max() clause in release_preflight (orchestrate_gate.py:46-49) is not pinned by any test; removing it keeps 25 tests green while a forged wall-clock under-declaration passes","evidence":"coordinator A mutant fals2"}
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"tests/test_release_gate.py imports helpers from another test module (test_regression_trigger); fragile under a different import mode","evidence":"tests/test_release_gate.py:12"}

CAPABILITY-COVERAGE: RR2 cycle-1 row reproduced (fals1); RR2 wall-clock clause unpinned (P2)
LIVE-BROWSER: not-applicable (CLI-only, no UI file in the diff)
ISSUES-WRITTEN: none (dual coordinator)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The cycle-0 RR2 failure is repaired: the approval check now covers the larger of the declared and re-costed bounds, an honest scope still resumes, and nothing is written or invoked before the check passes. The unit fails only because the one owed full suite shows a unit-owned red (new advice sites not registered in a guard test), which cycle 0 could not see; the fix is a two-line test edit. No new evidenced RR2 failure, so this is progress, not a no-progress repeat.
Metrics: start=2026-10-10T20:21:44Z end=2026-10-10T23:50:00Z wall_min=unavailable agent_min=unavailable blocked_min=7 suite_runs=1 repeat_runs=0 mutations=2 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=1 defects_unit=1 defects_6c=0
slow: full suite 35 min (L, owed checker suite; plus a session cut-off not counted)
