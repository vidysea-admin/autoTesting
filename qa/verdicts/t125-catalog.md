# Verdict - t125-catalog - integration re-check - coordinator A

Cycle checked: 4-integration
Verdict path: qa/verdicts/t125-catalog.md (coordinator A of a dual check; blind to B; no `*.b.md` newer than d49ec0f5 was read)
Bound to: D:/autoTesting/.worktrees/t125-integrate (branch integrate/t125)
Heads judged: manifest 51a84edd, merge 6c0d57a1 (d49ec0f5 onto origin d4c369b0), my contract commit 0cce70ac (HEAD for all code; the later B commit touches only qa/verdicts). Base for the diff: origin d4c369b0 (an ancestor of HEAD and the merge base with master).
Policy: proportional-verification/2026-10-06.6 (pin) with the .7 rules for an in-flight unit. Cycle-4 evidence identities: qa/checkpoints/t125-catalog.md (HEAD 778b5f86 there).
Previous cycle-4 verdict of mine archived to qa/verdicts/t125-catalog.r4-1.md (not re-read for this judgement).

## Check plan (step 0)

| Signal | Check | Done |
|---|---|---|
| Merge diff `git diff d4c369b0 HEAD` (23 files) + conflict resolutions | diff-scope read (4c) | yes |
| d063 / D-066 / D-068 guards | compare `stages/run_budget.py`, `stages/parallel_run.py`, `ui/run_execution.py` against d4c369b0 | yes |
| Inputs changed since the cycle-4 identity: `ui/routes_runs.py`, `ui/run_execution.py`, `stages/run_budget.py`, `stages/parallel_run.py`, `ui/app.py` (docstring), `tests/test_ui_runs_serial_entry_order.py`, `tests/test_parallel_run_approval.py`, `tests/test_ui_runs_parallel_crash_recovery.py` | re-run CT6(1)-(4), CN10, consent "One aggregate budget" with isolated falsification | yes (24 mutants) |
| Protected test change (`test_ui_runs_serial_entry_order.py` rewritten to d063 semantics) | claim-by-claim pin audit + 7 mutants | yes |
| Run-approval/budget plumbing (L trigger, dual) | the unit's ONE full suite | yes, suite_runs=2 (one died silently, see Metrics) |
| UI surface (`ui/routes_runs.py`, project page link) | live browser walk of the touched screens | yes |
| Data / prompt / persona | none | not applicable |

TIER: L - `src/autotester/ui/run_execution.py:158-159` (the added `budget.matches(approval)` guard on the CN10 run-approval path, D-018) and the budget plumbing in `ui/routes_runs.py:112-130`. Dual check; this verdict is A only.

## Diff-scope (4c) and guard comparison (read by me)

- `git diff d4c369b0 HEAD --stat` = 23 files (T-125's own files, `docs/MAP.md`, the merged qa records). No function, class, route, export or config key of origin is removed.
- `stages/run_budget.py` and `stages/parallel_run.py`: `git diff d4c369b0 HEAD` is empty. Byte-identical to origin (blobs a4abf08f4a06, 3c79a9d74320). Finite/non-negative limit validation, `_stop_reason`, `check_start()`, `matches()`, `reserve = budget is None` all intact. No d063 / D-066 / D-068 guard weakened.
- `ui/run_execution.py`: the only delta against d4c369b0 is the docstring (1 line to 4) and ONE added guard at `_run_cases_in_parallel` (run_execution.py:158-159): `if not budget.matches(approval): raise ValueError("shared budget does not match approval")`. Nothing else. This is the allowed delta.
- `ui/app.py`: delta against origin = the router include, the "Test catalog" link, and the module docstring (3 lines joined). File is 300 lines. No behaviour change in the docstring.
- `ui/routes_runs.py:112-130`: one `RunBudget(approval)` built once before the tier loop; each tier calls `_run_cases_in_parallel`/`_run_cases_serially` with `budget=budget`; EXECUTE stage recorded `failed` when `budget.stop_reason` is set (`routes_runs.py:131-135`); `_require_live_case_approval` keeps origin's 5-arg form. `RunBudget.require_approval()` is gone (duplicated `matches()`); CN10's no-op mutant is replaced by the `matches()` guard mutant below.
- Unchanged since the cycle-4 identity (same blob): `stages/catalog.py` 41283e8e40, `ui/routes_catalog.py` 9ed4f8bcec, `ui/routes_report.py` bef0ec2382, `schema/catalog.py` d6a16e6b4a, `schema/run.py` 444687afc2, `tests/test_catalog.py`, `tests/test_catalog_packs.py`, `tests/test_ui_catalog.py`, `tests/test_ui_report.py`, `tests/test_schema.py`. Their cycle-4 results are kept by identity (and the new full suite re-ran them green).

## Results per criterion

Method: each mutant = a `git archive HEAD` copy, `autotester.__file__` asserted inside the copy, named node(s) green in the copy first, ONE single-hunk edit, red for the named reason, copy discarded. Bound tree never edited. Run by two read-only Sonnet sub-checkers and read back by me; 24 mutants, all green-before / red-after.

| Crit | Result | Evidence |
|---|---|---|
| CT1-CT5, CT7-CT9, AT-588 packs | MET (kept by identity) | inputs identical to cycle 4 (blobs above); all their tests green in this full suite; cycle-4 mutants m10-m18, m22, m07-m09 stand. |
| CT6(1) dispatch order | MET | `tiers_to_run` returns reversed -> RED `test_real_trigger_orders_tiers_and_persists_blocked_pinned_cases[1,2]` at test_ui_runs_serial_entry_order.py:176 (`observed[0] == cases[5].id`) and test_catalog.py:211/:218; same reversal in the routes_runs loop -> RED at :176. |
| CT6(2) never skip | MET | loop skips tiers with no runnable class -> RED at :176 (IndexError, no case dispatched); `tiers_to_run` drops empty tier -> RED test_catalog.py:211 plus the trigger test. Test-pin mutant (b): drop later-tier cases once `stop_reason` set -> RED 16 params at :232 (results set == cases set). |
| CT6(3) per-tier counts incl. 0 | MET | omit zero tiers -> RED via Run validator (`ValidationError`, routes_runs.py:173); validator disabled -> RED test_schema.py:38 `DID NOT RAISE`; both together -> RED at :187 `assert {} == {static:0,behavioural:0,adversarial:0}`. Browser: run page reads "static: 0, behavioural: 2, adversarial: 5". |
| CT6(4) failures first | MET | `failures_first` sorted by case id -> RED test_ui_report.py:297 `17356 < 17125`; sections swapped -> RED :298. Browser: h2 order Failures, `T c_static`, `T b_adv`, Other results, `T a_pass`. |
| CN10 one meaning at gate and run | MET | `matches()` guard removed (run_execution.py:158-159) -> RED `test_parallel_entry_only_rejects_mismatched_budget_before_any_effect` at :295 `DID NOT RAISE ValueError`; zero `max_actions` as unlimited -> RED test_parallel_run_approval.py:91; zero `wall_clock_s` as unlimited -> RED :106 and :127; zero `max_probes` as unlimited -> RED :96. `run_budget.py` (byte-identical to origin) has no truthiness guard on any bound. |
| consent.md CN11 "One aggregate budget" | MET | `RunBudget(approval)` rebuilt inside the tier loop -> RED 16/16 `test_internal_execution_spends_one_budget_across_tiers_and_all_legs` at :230; `session.budget = budget` removed in the entry path -> RED 8/16; in the serial path -> RED 2/16; a fresh budget handed to the serial entry call -> RED 8/16. Brake named: wall clock and max_actions exercised by the 16 params (`max_probes` is covered by test_parallel_run_approval.py, not by this family). |

## Protected test change: `tests/test_ui_runs_serial_entry_order.py`

Judged against both d49ec0f5 (cycle-4) and d4c369b0. Origin's version holds only `test_entry_cases_start_before_the_shared_session_starts`; it is unchanged. The four tests that changed are T-125's. Each behavioural claim and whether it is still pinned at HEAD (all line numbers in that file):

| Claim | Pinned? | Where / falsified by |
|---|---|---|
| One shared budget across tiers and legs | yes | :230 (admitted set == expected). Mutant: `RunBudget` rebuilt in the loop -> 16 RED. |
| Never skip: every case persisted with a result and a verdict | yes | :232, :245 (verdict set == result set). Mutant: drop later-tier cases at brake -> 16 RED; `save_verdict` skipping INCONCLUSIVE -> 16 RED at :245. |
| Tier order | yes, unchanged | :176-181. Mutant: reversed `tiers_to_run` -> 18 RED. |
| Refused case: ERRORED result, error names the brake | yes, reworded on purpose | :234-236 now `run budget exhausted: <reason>` substring with a per-param reason (max_actions / wall_clock_s) instead of the retired reservation string. Mutant: `check()` error text changed -> 16 RED. |
| Refused cases INCONCLUSIVE | yes | :246. Mutant: `grade_errored_result` forces FAIL -> 16 RED. |
| EXECUTE stage marked failed on a brake | yes, ADDED | :247-249. Mutant: status always "done" -> 16 RED at :249. |
| Session count | yes, weaker form | :239-241 derived from the admitted set (I checked it by hand on the allowance-4 case: 3 and 4). d063 starts no browser for a refused case, so the old literals no longer hold. |
| Wipe count | changed, not dropped | :243 is now `len(entry_ids)`; d063's `_run_entry_case` wipes the profile (run_execution.py:73) before `check_start` (:78). Still pinned, for the merged behaviour; harmless (profile is wiped before every entry run anyway). |
| Old case-level reservation `try_consume(actions=action_cost(case))` | intentionally gone | d063 spends per executed step (`budget.check(actions=1)` in the mocked `run()`); `parallel_run.py:196` `reserve = budget is None`. Re-adding it would double-spend against `trigger_run`'s `max_actions = sum(action_cost)` grant. |

Justification of the protected change (written, per rule): no assertion was deleted without a d063-accurate replacement; the expected admitted set, order, never-skip and verdict set were unchanged; one claim (EXECUTE `failed`) was added. 7 of 7 named mutants turn the file red for the named reason.

## Contract amendment (mine)

Appended at qa/contracts/consent.md "One aggregate budget" (CN11) plus a log line, dated 2026-10-07, committed alone as 0cce70ac. Checked against the merged code: a refused case persists ERRORED + INCONCLUSIVE (:234-246), error contains `run budget exhausted: <stop_reason>` (parallel path `parallel_run.py:160` stores it bare; entry/serial-startup paths store `RunBudgetExceeded: run budget exhausted: ...`, so the text says "contains"), no case skipped, EXECUTE `failed` (`routes_runs.py:131-135`). Wording note (low, not a FAIL): `check_start()` (`run_budget.py:100-105`) also marks `max_actions` exhausted when the allowance is already fully spent, before any step.

## Other steps

- `ruff check src tests scripts` = "All checks passed!"; `autotester doctor` = `doctor: clean` (run by me at 0cce70ac, tree 8b097a92... after B's qa-only commit).
- Persona walk: skip (operator diagnostic page, no spec user type maps to it).
- full-suite trigger: none beyond L security (run approval path); nothing deferred to 6c.

## Full suite (the unit's ONE; PID 37804 `uv run pytest`, python child 43428, started 2026-10-07T18:56, no -q, no -x)

An earlier run (uv 36192, python 36600, started 18:12) died silently with no summary and its process tree gone by 18:56 (cause not established; the machine was running 3-4 other suites at about 3 GB free); it produced no result and is not counted as a result. The coordinator's rule: a suite that died silently is BLOCKED-PROCESS, rerun once, which I did. The shared lock `D:/autoTesting/.work/suite.lock` was held by t190-ux (since 18:34) when I learned of it; my rerun was already in progress (started 18:56 before the instruction), so I left that file untouched and used `suite.lock.t125-A` while running, removed after.

Result line: `3 failed, 2621 passed, 5 skipped, 14 xfailed, 15 warnings in 3038.99s (0:50:38)`

Attribution of the 3 failures (none T-125-owned; none of their files is in the 23-file diff):
1. `tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered` - BASELINE (known; goal.json bookkeeping, failed identically at bd2fe8f4 in cycle 4).
2. `tests/test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus` - BASELINE/LOAD (known; 3.13 s vs 3 s bound; `core/redact*` untouched).
3. `tests/test_crawl_inventory_live.py::test_a_logged_in_crawl_maps_every_route_and_names_the_one_it_refused` - `load-flake: tests/test_crawl_inventory_live.py::test_a_logged_in_crawl_maps_every_route_and_names_the_one_it_refused`. Failure: `CrawlStatus.STOPPED_BOUND`, stop reason `wall_clock_s` (the crawl's own timing bound, test_crawl_inventory_live.py:115). It is not in the known-baseline list, so I confirmed it: the file alone PASSES on a clean d4c369b0 tree (`2 passed in 357.95s`, clean `git worktree` at d4c369b0, venv python with PYTHONPATH to it, worktree then removed) and PASSES alone on the bound HEAD (`2 passed in 278.73s`). All three load-flake conditions hold: absent when run alone; it asserts a wall-clock deadline; no T-125 file touches it (`stages/explore*` and the test are not in the diff). Filed as a low PROPOSED-ISSUE, never a HOLD. (Not a hang here; the test ran 5 min under load.)

## LIVE-BROWSER

`qa/evidence/browser-t125-integration-2026-10-07-checker-a/` (report.json, 4 PNGs, left uncommitted). Instrument: Playwright MCP and claude-in-chrome unavailable; headless Chromium 151 through the worktree venv's Playwright library, driven by a sub-checker against uvicorn from a `git archive HEAD` copy (port 8793, PID 44788 stopped by that PID), seeded scratch root. Real interactions: project page (one "Test catalog" link, 0 console errors), clicked it and landed on /projects/demo/catalog (15 class rows, blocked rows show a label plus "set GOOGLE_SIGNUP_TOKEN in the repo-root .env", 3 pack rows, 0 console errors), the run page (Failures section before Other results, static failure before adversarial, counts line `static: 0, behavioural: 2, adversarial: 5`, 0 console errors), unknown project 404 (1 expected console error). Disclosed as library-driven headless, not an MCP browser tool. Only the missing-credential block reason was seeded.

## PROPOSED-ISSUE lines (no ledger rows written; a PASS has no side effects)

PROPOSED-ISSUE: {"severity":"low","feature":"t125-catalog","title":"load-flake: tests/test_crawl_inventory_live.py::test_a_logged_in_crawl_maps_every_route_and_names_the_one_it_refused fails with stop reason wall_clock_s in a loaded full suite, passes alone on d4c369b0 (358 s) and on HEAD (279 s)","evidence":"suite log line 486; isolated reruns both green","type":"load-flake"}
PROPOSED-ISSUE: {"severity":"low","feature":"consent","title":"CN10: a zero max_actions treated as unlimited is caught by exactly one test (test_an_approval_granting_zero_actions_bounds_the_run_to_zero); the origin gate-and-budget-agree test stays green because it only spends a non-zero cost","evidence":"mutant run_budget.py:86 `if approval.max_actions and ...`: 1 of 23 tests in test_parallel_run_approval.py red; origin test, not T-125's","type":"coverage-note"}
PROPOSED-ISSUE: {"severity":"low","feature":"t125-catalog","title":"test_ui_runs_serial_entry_order.py pins the budget with a flat 1 action per mocked step; the real per-step action cost is not pinned in that file, and max_probes is not exercised by the 16-param family","evidence":"_patch_tier_execution.run spends budget.check(actions=1); BUD params cover max_actions and wall_clock_s only","type":"coverage-note"}
PROPOSED-ISSUE: {"severity":"low","feature":"process","title":"Full suite took 50.6 min and a first run died silently under 3-4 concurrent suites at ~3 GB free RAM; L wall budget (45 min) exceeded","evidence":"3038.99 s; uv 36192 tree gone without a summary; suite.lock held by t190-ux during the rerun","type":"process"}
PROPOSED-ISSUE: {"severity":"low","feature":"consent","title":"CN11 amendment wording: check_start() also refuses a case when the max_actions allowance is already fully spent, before any executed step","evidence":"stages/run_budget.py:100-105","type":"wording"}

VERDICT: PASS
SCOREBOARD: 12/12 criteria re-evidenced or kept by identity (CT1-CT9, CN10, AT-588 packs, CN11 "One aggregate budget"), 0 invariants violated
TIER: L (run-approval/budget plumbing: run_execution.py:158-159 `matches(approval)` guard, routes_runs.py:112-130; dual check, coordinator A)
FAILURES: none
CAPABILITY-COVERAGE: 24/24 mutants reproduced green-before (in a copy) / red-after / discarded; every re-run criterion has at least one named falsification; the protected test change has 7 mutants, one per behavioural claim
LIVE-BROWSER: qa/evidence/browser-t125-integration-2026-10-07-checker-a/ (headless Playwright library, disclosed)
ISSUES-WRITTEN: none (PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: fresh coordinator A, independent of the builder)
EXPLANATION: The merge diff holds: run_budget.py and parallel_run.py are byte-identical to origin d4c369b0, run_execution.py differs by a docstring and the single added matches(approval) guard (falsified), so no d063/D-066/D-068 guard is weakened. The rewritten serial-entry-order test still pins one shared budget, never-skip, tier order and the EXECUTE `failed` stage, each turned red by its own mutant, and the one full suite shows only three failures, two known baseline and one wall-clock load flake that passes alone on both d4c369b0 and HEAD. B must also PASS. slow: full suite 51 min under machine-wide contention (process signal, not a product defect).
Metrics: start=2026-10-07T12:10:00Z end=2026-10-07T14:40:00Z wall_min=150 agent_min=unavailable blocked_min=25 suite_runs=2 repeat_runs=2 mutations=24 cycle=4 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
