# Verdict: t122-first-login-run

Cycle checked: 1
Date: 2026-10-07
Bound to: D:/autoTesting (worktree .worktrees/t122-first-login-run, branch wave/t122-first-login-run, tip 77c5e090)
Policy-Version: proportional-verification/2026-10-06.6 (pinned by the manifest; .7 rules apply at dispatch)
Checker: claude-sonnet-subagent (single coordinator, no fan-out; checks ran serially, SERIAL: shared worktree venv and uv lock)
Counter: none (first dispatch at cycle 1; no earlier verdict exists for this slug)

VERDICT: PASS

## Check plan (step 0)

Diff since the branch's last merge of master (642ab4bd..HEAD) = 52 files: `projects/pathlynks/cases.jsonl`, `projects/pathlynks/project.json`, the manifest, and `qa/evidence/t122-first-login-run-2026-10-07/**`. No product code, schema, config or test changed.

| Signal | Check | Done |
|---|---|---|
| Tracked project data changed (case re-authored) | store path + diff vs the manifest's claim | yes |
| Live-product result claimed (C2, C6) | re-judge from recorded run.json, case result, verdict JSON, screenshots; no new production login | yes |
| Secrets in evidence | `scripts/check_no_secrets.py` | yes |
| Logic changed | none; done_check and the manifest-named case/UI tests | yes |
| UI surface changed | none (no `src/` change): Mode D not applicable | n/a |
| Persona walk | not applicable (no UI flow change; internal tool, no user-type change) | n/a |

No criterion needed a new production login, so none was made (no PATHLYNKS_* use by the checker).

TIER: S (the diff is the manifest, evidence and two tracked project-data files; no product code, so no L trigger. Criticality raises nothing.)

## Per-criterion results

| # | Result | Evidence the checker itself produced or read |
|---|---|---|
| C1 done_check | MET | `uv run pytest tests/test_execute.py tests/test_run_case_pipeline.py` in the worktree: `20 passed in 1.23s`, EXIT=0 |
| C2 login case ran on production, visible browser, PATHLYNKS_USER_* | MET | `projects/pathlynks/project.json` still `"headed": true`. Run `run-01M4B13T7QH17156NNK2PWGEYS` and `run-01M4B2KP0PQQ2NZTGYBQ463YWW`: `run.json` `case_ids: [case_cfa40e6b95c2]`; case results `outcome: completed`, evidence shows `[REDACTED]:PATHLYNKS_USER_LOGIN_URL`, fills of `input[name="identifier"]` and `input[name="password"]` as `[secret]`, click of `button[type="submit"]:has-text("Login")`. Screenshot `04-step04-click.png` (both runs, opened by the checker): signed-in shell, sidebar Dashboard / My Space / Explore Careers / ... / Logout, toast "Logged in successfully", main pane "Loading your Career Quest..." (the dashboard body was still loading at capture; the signed-in shell and toast are what the assertions rest on). No 401 and no login error on screen. |
| C3 fail closed naming AT-529 if authentication not obtained | MET (not exercised; see Observation O1) | Authentication was obtained and was evidenced, not assumed: both step-4 assertions recorded `met` plus the "Logged in successfully" toast. The branch changes no code, and no src/tests/scripts file names AT-529 (Grep over the worktree: no match), so the AT-529 branch could not have fired; the criterion is conditional and its condition did not hold. |
| C4 D-068 account-derived LIVE_CASE row, signed, verified | MET | `cycle1/approval-rows-minted.jsonl`: `appr_d21f4d71de4d` (11:13:54Z, expires 11:14:26Z) and `appr_99fa67e64213` (11:40:03Z, expires 11:40:35Z); `granted_by: account-derived:D-068`, `run_kind: live_case`, `max_actions 4`, `max_probes 80`, `wall_clock_s 32.0`, scope = the two declared USER keys on `pathlynks.vidysea.com` only (`include_subdomains: false`). Each run's `run.json` `bounds.approval_id` matches its row. `core/consent.py:30` ("ADVERSARIAL is deliberately absent") and `:89 prepare_account_grant`. Cycle-0 falsification rows for C4 (adversarial refused, undeclared key refused) are reused: their code (`core/consent.py`) is unchanged since cycle 0 (diff since af8f3218 touches no `src/autotester/core`). |
| C5 no adversarial case, no counsellor key, no value printed | MET | Both cycle-1 `run.json` list exactly one case, `case_cfa40e6b95c2` (kind best); the wrong-password and empty-submit rows stay `proposed` and ran nowhere. Only `PATHLYNKS_USER_*` keys in the approval scope. Screenshot `03-step03-fill.png` (opened): email blurred, password masked. `check_no_secrets.py` over `qa/evidence/t122-first-login-run-2026-10-07` and `qa/manifests`: `scanned 328 file(s); 0 leak(s)`, EXIT=0. |
| C6 case verdicts PASS | MET | Re-judged from the record, not the manifest: for both runs the case result is `outcome: completed` with `assert visible_text: met (expected to contain 'Logout')` and `... 'Dashboard'` recorded at step 4; verdict JSON `result: PASS`, `Criteria 1/1 met`, `grader_provider: gemini`, `images_requested 4 / images_seen 4`, `failures: []`. The screenshot shows both strings on screen, so the PASS is correct on the evidence and is not a judge artefact. The retired case's cycle-0 FAIL (`run-01M4AV0R6AKHH1M7C77FW2SV22`) stays attached to the retired id. |

SCOREBOARD: 6/6 criteria met (C3 vacuously, see O1), 0 invariants failed.

## Re-authoring through the real store path

- `cycle1/reauthor_login_case.py` uses `Case(...)`, `store.add_case`, `store.update_case` (retire) and `store.save_project`. The recomputed id of the new row equals its stored id (`ProjectStore.list_cases()` then `compute_id()`: `case_cfa40e6b95c2 == case_cfa40e6b95c2`, checker run), so the id was not hand-edited.
- `cases.jsonl` vs master (checker diff by id): the old row `case_35b17ccece2d` changed `status proposed -> retired` and gained `pinned: false`; the two untouched rows (`case_a5ea57c0961a`, `case_b1cb019ebb56`) gained only `pinned: false`; one new row `case_cfa40e6b95c2` (step 4 expects `["Logout","Dashboard"]`, status `proposed`, otherwise identical to the old row). 3 rows -> 4 rows; the textual diff touches all rows because of the store's compact JSON. The manifest says only the retired flag and the new row differ in content; the `pinned: false` default on all three old rows is also a content change it did not mention (O2, low wording, never a FAIL).
- `project.json` diff: `login_case_id` repointed to `case_cfa40e6b95c2`, plus schema defaults `max_parallel: 1` and `permitted_surface: []`. Nothing else. `headed: true`, `write_policy: read_only`, secrets block unchanged. Matches the manifest.
- Diff scope (step 4c): no source or test file removed or renamed; every touched file is under the manifest's "What changed" (manifest, evidence dir, the two project-data files). The root-level `approvals.jsonl` modification is uncommitted by design and not part of the commit.
- Gate: `qa/gates/t122-stale-login-oracle.md` is "Answered: 2026-10-07 - A" (section removed on purpose; D-072 item 1), which is what this repair implements.

## Tests and lint (all run by the checker in the worktree)

| Command | Result |
|---|---|
| `uv run pytest tests/test_execute.py tests/test_run_case_pipeline.py` | 20 passed, EXIT=0 |
| `uv run pytest tests/test_run_pathlynks_first_cases.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_ui_runs_live_case_approval.py tests/test_ui_case_navigate_reachability.py` | 42 passed, EXIT=0 |
| `uv run ruff check src tests scripts` | All checks passed, EXIT=0 |
| `uv run autotester doctor` | `doctor: clean`, EXIT=0 |
| `uv run python scripts/check_no_secrets.py qa/evidence/t122-first-login-run-2026-10-07 qa/manifests` | 328 files, 0 leaks, EXIT=0 |

No full suite (no `full-suite trigger`: no code, conftest, fixture or config changed; S tier, policy .7).

## CAPABILITY-COVERAGE / falsification floor

Manifest rows reproduced by reading the recorded evidence, not by a new live run (a new live run would only have re-touched production):
- C6: the falsified case `case_a21fdc0059fe` (step-4 marker `Zzz Absent Marker 9931`, run `falsify-run-01M4B16YD6FQ0Q9YBHTCGTBJTX`): case result records `assert visible_text: unmet (expected to contain 'Zzz Absent Marker 9931')` (red at the execute layer, the assertion that fired is the one the case is named for), screenshot of the same login unchanged, verdict still `PASS` (see PROPOSED-ISSUE 1). The green-before half is the two real runs above, same flow, assertions `met`.
- C4: cycle-0 consent falsifications reused (code unchanged), see C4.
- Repeats: the C6 stale-oracle failure reproduced 2 of 2 at cycle 0, and the new case passed 2 of 2; deterministic claim, no flaky claim, so no repeat loop.

## Findings

### PROPOSED-ISSUE 1: the judge can PASS a run whose deterministic assertion failed (severity high; does NOT fail T-122)

Confirmed by reading the code myself:
- `src/autotester/stages/run_case_pipeline.py:49-56` `default_rubric` and `:37-46` `_rubric_for_claim`: the only criterion is `"The evidence is consistent with: {claim}."`, where `claim_of` (`:32-34`) is `case.rationale`. For the login case the rationale ("proves the credential boundary + execute/grade pipeline against a real product end to end") never mentions the step expectations. `_rubric_for` (`:90-101`) builds it for any case with no persisted rubric.
- `src/autotester/stages/grade.py:123-143` `_outcome_verdict` shortcuts only BLOCKED_HITL, ERRORED and NOT_RUN; its docstring (`:124-128`) says ASSERTION_FAILED is deliberately not one of them (D-032, `docs/DECISIONS.md:565-599`).
- `grade.py:26-31` `_render_evidence` hands the judge only `outcome: assertion_failed` plus the evidence path lines (the `assert ... unmet` label), as text.
- `grade.py:52-67` `_inconsistency` checks id and count consistency of the judge's own answer; nothing compares the verdict with `result.outcome`. So there is no code floor: D-032's own claim (`DECISIONS.md:578-581`: an assertion-failed result "can no longer be graded PASS without the grader contradicting recorded evidence") rests on the judge's choice, not on code.
- Measured evidence in the branch: falsified run verdict `PASS` / "Criteria 1/1 met" with an unmet assertion (`cycle1/falsify-run-01M4B16YD6FQ0Q9YBHTCGTBJTX/case_a21fdc0059fe.verdict.json`); `cycle1/regrade-tally.txt`: 6 of 6 offline re-grades PASS on that evidence, and the stale-oracle evidence re-graded FAIL only 4 of 6.

Severity high: a broken screen or a failed login can be reported PASS (the false negative the north star refuses), and in particular the AT-529 shape (a 401 leaves Logout absent, so the step-4 assertion goes unmet) is not guaranteed to fail closed (C3's stated intent). It does not fail T-122: both cycle-1 PASS verdicts are correct on their own evidence (assertions `met`, screenshots show the signed-in shell), so no T-122 criterion is wrong because of it. Fix direction (needs a human choice against D-032): carry the case's expected assertions into the criterion text, or make `assertion_failed` a floor (PASS downgraded to INCONCLUSIVE unless the judge cites evidence against the assertion).

PROPOSED-ISSUE: {"severity":"high","feature":"grade","type":"correctness","title":"Judge returns PASS when a deterministic step assertion failed: default_rubric grades only 'consistent with <case rationale>' and nothing forces a verdict floor on outcome=assertion_failed","where":"src/autotester/stages/run_case_pipeline.py:37-56,90-101; src/autotester/stages/grade.py:52-67,123-143,156-161; docs/DECISIONS.md:565-599 (D-032)","evidence":"qa/evidence/t122-first-login-run-2026-10-07/cycle1/falsify-run-01M4B16YD6FQ0Q9YBHTCGTBJTX (unmet 'Zzz Absent Marker 9931' -> verdict PASS) and cycle1/regrade-tally.txt (PASS 6/6)","fix_direction":"human choice against D-032: render the case's expected assertions into the criterion, or floor an assertion_failed outcome (PASS -> INCONCLUSIVE unless the judge cites evidence against the assertion)","gate":"human (D-032 reversal or amendment)"}

### PROPOSED-ISSUE 2: trigger_run still runs retired cases (severity medium; does NOT fail T-122)

Confirmed: `src/autotester/ui/routes_runs.py:143` `cases = store.list_cases()` feeds every row to `_require_declared_values`, `_require_live_case_approval` and `_execute_with_trace` (`:153-162`) and records them all in `Run.case_ids` (`:165`). `store/project_store.py:111-112` `list_cases` is a bare `read_jsonl`. `CaseStatus` (`schema/enums.py:102-105`, with `RETIRED`) has exactly one reference in `src/` (the default on `schema/case.py:32`): no code anywhere reads a case's status, so "retired" (and "proposed") is a label only. Effect on this project: a UI "Run" executes the retired stale-oracle case (a known false FAIL) plus the wrong-password and empty-submit rows, spending the approval's action and 32 s budget. D-068 gives adversarial kinds no automatic grant, so the wrong-password row would make the run refuse at the gate rather than run, but the retired row would run. The unit is safe because its driver was restricted to `login_case_id`, and the manifest said so. Severity medium: it wastes production logins and budget and creates false FAIL noise, but it neither passes a bad build nor breaks a T-122 criterion. Fix direction: filter `status is RETIRED` in `trigger_run` (and the report) at one seam in `ProjectStore`, with a test.

PROPOSED-ISSUE: {"severity":"medium","feature":"ui-runs","type":"correctness","title":"trigger_run runs every case row including status=retired; CaseStatus has no read site in src","where":"src/autotester/ui/routes_runs.py:143,153-165; src/autotester/store/project_store.py:111-112; src/autotester/schema/enums.py:102-105","evidence":"grep CaseStatus over src: only schema/case.py:32; projects/pathlynks/cases.jsonl row case_35b17ccece2d status retired","fix_direction":"exclude retired cases at one ProjectStore seam used by trigger_run and the report; add a test that a retired case is not executed or approved for","gate":"none"}

### PROPOSED-ISSUE 3: approval wall-clock headroom on a slow production hour (severity low-medium; does NOT fail T-122)

- Source of the 32 s: `src/autotester/stages/run_budget.py:141` `WALL_CLOCK_PER_ACTION_S = 8.0` times the case's step count (`:161-165`), so a 4-step login is granted 32 s. `RunBudget` starts its clock at construction (`:62`) and refuses at any budget check once `monotonic - start >= wall_clock_s` (`:80-83`); a browser launch plus navigation counts.
- Headroom measured from the traces and rows: run 1 stage 39.4 s total (`trace.jsonl`) but the case result was written 24.7 s after the approval was minted (11:13:54.9 -> 11:14:19.6, `expires_at` 11:14:26.9), about 7 s of margin on the action phase; run 2 stage 29.1 s, case result 11.1 s after minting. The manifest's "29.1 s of the 32 s" counts the judge call (8.2 s, after the last budget check), so the real margin on the run that passed was larger than the manifest implies: 7 s (run 1) to 21 s (run 2), not 3 s. Run 1's stage (39.4 s) passed even though it exceeds 32 s, because the clock gates actions, not grading.
- It still fails closed but fails: the manifest records four further scratch runs ending `errored: run budget exhausted: wall_clock_s` when production login took 22-44 s, which grades INCONCLUSIVE. So a slow hour turns the one live smoke into a spurious INCONCLUSIVE; it never produces a false PASS. Fix direction: size the request with a larger per-action allowance for navigate and login steps, or exclude browser launch from the clock.

PROPOSED-ISSUE: {"severity":"low","feature":"consent","type":"process","title":"A 4-step production login is granted a 32 s wall clock (8 s per action incl. browser launch); slow hours exhaust it and the run errors INCONCLUSIVE","where":"src/autotester/stages/run_budget.py:62,80-83,141-165","evidence":"cycle1 approval rows (32 s) and traces (stage 39.4 s and 29.1 s; case results 24.7 s and 11.1 s after minting); manifest reports 4 further wall_clock_s errored runs","fix_direction":"larger per-action allowance for navigate/login or start the clock after browser launch","gate":"none"}

## Observations (non-blocking)

- O1: C3's wording ("any unit on this path must FAIL CLOSED naming AT-529") is not implemented anywhere in code (no src/tests/scripts file names AT-529) and is not exercised here. Combined with PROPOSED-ISSUE 1, a real 401 would show Logout absent, an unmet assertion, and a judge that may still say PASS. T-122 is judged on what it evidences (authentication obtained and asserted twice); the fail-closed path belongs to the fix for PROPOSED-ISSUE 1.
- O2 (low, wording, no cycle): the manifest's "only the retired flag on the old row and the new row differ in content" omits the `pinned: false` default added to all three old rows. The row ids of `case_35b17ccece2d` (retired), `case_a5ea57c0961a` and `case_b1cb019ebb56` no longer equal `Case.compute_id()` on the current schema (checker run); that predates this unit (rows from 2026-09-03) and is not caused by it.
- O3 (low): the approval rows carry `production: false` although the target is production `pathlynks.vidysea.com`. That is the D-068 design and the manifest states it, so it is noted, not judged.
- O4 (low, evidence quality): the step-4 screenshot captures the dashboard while it still shows "Loading your Career Quest..."; the `Logout` and `Dashboard` markers are the persistent sidebar, so the oracle is stable but weaker than the old dashboard-content oracle. This is exactly the trade the human chose (D-072 item 1 = A).

LIVE-BROWSER: not-applicable (no UI source changed; production login evidence read from the recorded run, not re-driven, per the brief)
ISSUES-WRITTEN: none (single check; the maker mints ledger rows from the PROPOSED-ISSUE lines above and puts them in Candidates)
EXECUTOR: claude (main builder session) (checker: claude-sonnet-subagent)
EXPLANATION: The repair does what the answered gate asked: the new case `case_cfa40e6b95c2` was created through the store path, its id matches `compute_id`, the old case is retired, `login_case_id` is repointed, and the two live runs record both step-4 assertions met on a screenshot that visibly shows the signed-in shell, so the PASS verdicts are correct on the evidence. Judge-overrule (PROPOSED-ISSUE 1) is a real, high-severity defect in the grading stage, but it does not change any T-122 result, so it is filed, not failed. The git-tracked change is data and evidence only.

Metrics: start=2026-10-07T11:57:44Z end=2026-10-07T12:45:00Z wall_min=47 agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=0 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
