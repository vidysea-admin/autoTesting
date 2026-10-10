# Verdict (coordinator B, blind) — t125-catalog, integration-rework re-check

Cycle checked: 4-integration
Verdict path: qa/verdicts/t125-catalog.b.md · Checkpoint: qa/checkpoints/t125-catalog.b.md
Date: 2026-10-07 · bound to `D:/autoTesting` · source `integrate/t125` head `51a84edd` (merge `6c0d57a1` = `d49ec0f5` into origin/master `d4c369b0`), checked in detached worktree `.worktrees/t125-int-b` (own `uv sync` venv)
Policy pin: proportional-verification/2026-10-06.6 (+ the .7 rules). Tier L, dual check (coordinator B).
I did not read coordinator A's verdict, checkpoint, evidence or commits. The earlier cycle-4 B verdict is archived as `qa/verdicts/t125-catalog.b.r4-1.md` and was not reused as evidence.

VERDICT: PASS

## Check plan (step 0)
| Signal | Check run |
|---|---|
| Merge diff vs `d4c369b0`, incl. conflict resolutions | `git diff d4c369b0 HEAD` on routes_runs / run_execution / run_budget / parallel_run / app / schema / routes_report / test_parallel_run_approval; app.py also vs `d49ec0f5` and vs the common base `bd2fe8f4` |
| CT6(1)-(4), CN10, consent.md:255 "One aggregate budget" | affected tests through the real run endpoint, plus 11 isolated falsification copies |
| d063 / D-066 / D-068 guards | empty diffs of `stages/run_budget.py` and `stages/parallel_run.py`; one-hunk diff of `ui/run_execution.py`; guard falsified |
| Protected test change `tests/test_ui_runs_serial_entry_order.py` | line diff vs `d49ec0f5` and vs `d4c369b0`, full read of the new file, a falsification per pin |
| app.py shape | diffs, `wc -l` |
| Affected tests, ruff, doctor | section 6. No full suite (policy .7: coordinator A runs the one L suite) |

TIER: L (concurrency/timing: the `RunBudget` brake path, the guard added at `src/autotester/ui/run_execution.py:154-159`, and a protected test change in `tests/test_ui_runs_serial_entry_order.py`).

## 1. Merge diff against d4c369b0
Only T-125's own surface differs from origin: schema (`catalog.py`, `run.py` field + validator), `stages/catalog.py`, `ui/routes_catalog.py`, `routes_report.py` (failures-first, counts line), `routes_runs.py` (tier loop), `app.py`, one guard in `run_execution.py`, tests, qa and docs.
I read the `routes_runs.py` hunks. `RunBudget(approval)` is built once in `_execute_with_trace`, before `for tier in tiers_to_run(cat):`. Origin's `budget=` keyword, `account_keys`, the 5-arg `_require_live_case_approval` and `status="failed" if budget.stop_reason else "done"` are all intact. `trigger_run` persists `catalog_runnable_counts` for all three tiers.
No origin function or test is deleted or renamed; the deletions in `git diff d4c369b0 HEAD` are docstring compressions in `routes_report.py` and `app.py`.

## 2. d063 / D-066 / D-068 guards: not weakened
- `git diff d4c369b0 HEAD -- stages/run_budget.py stages/parallel_run.py` is empty (verbatim origin).
- `ui/run_execution.py`: the only delta is the docstring plus `if not budget.matches(approval): raise ValueError("shared budget does not match approval")` at the top of `_run_cases_in_parallel` (`run_execution.py:154-159`, read in this check). `RunBudget.matches` (`run_budget.py:107`) is origin's own method. The guard only adds a refusal; it removes none.
- Falsified (copy M5): deleting the guard turns `test_parallel_entry_only_rejects_mismatched_budget_before_any_effect` RED with `Failed: DID NOT RAISE ValueError` (green before).
- Snapshot (copy M10): `self._approval = approval.model_copy(deep=True)` changed to `approval` turns `test_budget_owns_a_snapshot_of_its_approval_not_the_callers_live_object` RED at `test_parallel_run_approval.py:235` (green before).

## 3. Re-run criteria (through the real trigger or the real executor, not only helpers)
All green in the checked tree (section 6). Each has an isolated falsification: green before in the copy, red after for the named reason.

| Criterion | Test (in `tests/test_ui_runs_serial_entry_order.py` unless stated) | Falsification, red line |
|---|---|---|
| CT6(1) tier order, observed by dispatch call order, width 1 and 2 | `test_real_trigger_orders_tiers_and_persists_blocked_pinned_cases` (asserts `observed[0..8]` tier by tier) | M4 `reversed(tiers_to_run(cat))`: RED at `:176`, `'case_8bb0..' == 'case_5b06..'` |
| CT6(2) never skip; executed set equals `store.list_cases()`; pinned and blocked still run | same test (`:183-186`: results, verdicts, `run.case_ids`) and `test_internal_execution_...` (`:232`, every case persisted) | M8 gate dispatch on the runnable count (the old rule): RED at `:176` `IndexError`. M2 `break` after a brake so later tiers do not run: RED at `:232`, result set != all cases |
| CT6(3) per-tier count recorded, empty tier is `0` not absent | `:187-188`, `catalog_runnable_counts == {static:0, behavioural:0, adversarial:0}` | M6 counts `None`: RED `assert None == {...0}`. M6b non-zero counts: RED `{...1} == {...0}` |
| CT6(4) failures first, cheap tier first | `tests/test_ui_report.py::test_run_view_lists_cheap_tier_failures_first_ahead_of_passes` | M7 sort failures by case id: RED at `test_ui_report.py:297` |
| CN10 one bound, snapshot, mismatch refused before any effect | `test_parallel_entry_only_rejects_mismatched_budget_before_any_effect` (asserts `events == []`, `budget.actions_used == 0`, run dir absent); the snapshot test in `test_parallel_run_approval.py`; `test_approve_cli_bounds.py` | M5 (guard removed) RED; M10 (snapshot aliased) RED |
| consent.md:255 "One aggregate budget": shared across tiers and legs, nothing resets, stop on a brake, name it, record truth | `test_internal_execution_spends_one_budget_across_tiers_and_all_legs` (16 params: width x deadline x allowance x early_normal) | M1 `RunBudget(approval)` rebuilt inside the tier loop: RED at `:230`, the executed set grows past the single admitted case. M3 EXECUTE always `"done"`: RED at `:249`, `[('done', True)] == [('failed', True)]`. M9 `check_start()` removed from `_run_entry_case`: RED at `:241`, `3 == 1` (an extra browser session for a refused case) |

The brake text asserted is `run budget exhausted: max_actions|wall_clock_s` in each refused case's ERRORED error, every refused case persisted INCONCLUSIVE, and exactly one `execute` stage span with `status == "failed"` whose error names the brake. That satisfies consent.md:255-258 as written. The manifest's proposed append to consent.md:255 is a clarification for the checker to amend, not a condition of this PASS.

The per-case `action_cost` reservation is not re-expressed. That loses no single-spend protection: the mocked step charges one action through `budget.check(actions=1)`, so a re-introduced case-level pre-charge would admit about half the cases and turn `:230` RED (`allowance=4` expects 4 admitted). Real runs are charged per executed step in `stages/execute.py`, and `trigger_run` grants `sum(action_cost)` (`test_real_trigger_undersized_grant_refuses_all_stored_costs_before_run`, green).

## 4. Protected test change `tests/test_ui_runs_serial_entry_order.py` (L, justified)
Compared with `git show d49ec0f5:tests/test_ui_runs_serial_entry_order.py`. The origin version (`d4c369b0`) holds only `test_entry_cases_start_before_the_shared_session_starts`, unchanged here except an import.

The four required pins still hold, each shown by a falsification above:
- one shared budget across tiers and legs (M1);
- every case persisted with a verdict (M2, M8);
- the EXECUTE stage `failed` on a brake (M3; this assertion is new, not carried over);
- tier order (M4, test unchanged).

The helper edit (`session.budget.check(actions=1)` per mocked step) is the minimal change that lets a mock spend the real d063 budget. The file is 300 lines.

Lost or relaxed pins, reported explicitly:
1. **Refused entry case does not wipe the entry profile: LOST (deliberate).** Old: `wipes = 0 if deadline and early_normal else (1 if deadline or allowance==1 else 2)`, so a budget-refused entry case never touched the profile dir. New: `wipes == len(entry_ids)` (`:243`). Origin's `_run_entry_case` calls `shutil.rmtree(entry_paths.profile_dir)` before `budget.check_start()` (`run_execution.py:76-79`, unchanged from `d4c369b0`). A run refused by its own brake can still delete the dedicated logged-out entry profile, which is wiped before every run by design. It is not a contract criterion, and the behaviour is d063's, not introduced by the merge. Filed as low (P1), not a FAIL.
2. **Exact error string: LOST, strengthened.** Old `error == "run budget exhausted before this case could start"`; new `f"run budget exhausted: {reason}" in error`. Equality became containment, but the new text names which brake fired, which the old one did not.
3. **Absolute session counts: RELAXED.** Old fixed table `1 if deadline or allowance==1 else (3 if width==1 else 4)`; new count is derived from the admitted set (admitted entries + distinct admitted tiers at width 1, admitted normals at width 2). It still pins "no browser for a refused case" (M9 RED, `3 == 1`) and "one shared session per tier at width 1", but it is a model of the code, not a literal table. Accepted: the table was a property of the reservation implementation.
4. Everything else the old file pinned is carried over unchanged: admitted set and order, every case persisted, grade events == admitted, verdict set == result set, refused cases INCONCLUSIVE, and the mismatched-budget refusal (only the call changed from positional to `budget=budget`).
Net: no case-level behaviour pin is lost except item 1, which follows from d063's own ordering.

## 5. ui/app.py
`src/autotester/ui/app.py` is 300 lines (`wc -l`). Against `d49ec0f5` it differs only by the module docstring's last two lines joined into one, plus origin's `origin_guard_middleware` import and `FastAPI(..., middleware=origin_guard_middleware())` call (origin's own change since `bd2fe8f4`, identical in `d4c369b0`). Against `d4c369b0` the only differences are T-125's `routes_catalog` import and `include_router`, the "Test catalog" link, and the same docstring. No behaviour change from the join.

## 6. Affected tests, ruff, doctor
- `pytest -m "not harness"`, no `-x`, bare, in the t125-int-b venv. 38 files matching catalog*, ui_catalog, report_export*, execute*, parallel_run*, ui_runs*, consent, approval*/approve*, explore_consent, schema*, ui_report*: `390 passed, 1 skipped`.
- 12 more files that import the changed modules (test_browser_actions, test_browser_settle, test_coverage_wiring, test_goal_contract_registration, test_grade_evidence, test_pinned_regression, test_provider_record_concurrency, test_run_trace, test_ui, test_ui_credential_safety, test_ui_video_route, test_video_evidence): `105 passed, 1 failed`. The failure is `tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered`. It reads `.goal/goal.json`; the file and the test are byte-identical to `d4c369b0` (`git diff d4c369b0 HEAD -- .goal tests/test_goal_contract_registration.py` is empty), so it is red on origin too and not T-125-owned.
- The brief names 44 files; my name patterns match 38 plus the 12 importers. I report my own counts, and could not reproduce the maker's `498 passed, 1 skipped` figure by name list.
- `ruff check src tests scripts`: All checks passed.
- `autotester doctor`: clean.
- `full-suite trigger`: none beyond A's one L suite (policy .7).

## 7. Mutants
11 isolated copies (src + tests + scripts + pyproject, run with the t125-int-b interpreter and `PYTHONPATH` pointing at the copy; each copy resolved its own `autotester.__file__` and was green before the edit): M1, M2, M3, M4, M5, M6, M6b, M7, M8, M9, M10. All RED for the named reason. Nothing was run in or edited in the bound worktrees.

PROPOSED-ISSUE: {"severity":"low","feature":"consent","title":"A budget-refused entry case still wipes the dedicated entry profile (wipe precedes budget.check_start in _run_entry_case)","evidence":"src/autotester/ui/run_execution.py:76-79; tests/test_ui_runs_serial_entry_order.py:243","type":"lost-pin","status":"open"}
PROPOSED-ISSUE: {"severity":"low","feature":"consent","title":"The consent.md:255 clarification proposed in the manifest (actions spent per executed step; a refused case persists ERRORED/INCONCLUSIVE naming the brake; EXECUTE recorded failed) is not yet in the contract","evidence":"qa/manifests/t125-catalog.md, section 'Integration rework (2026-10-07)'","type":"contract-maintenance","status":"open"}

VERDICT: PASS
SCOREBOARD: CT6(1)-(4), CN10 and consent.md "One aggregate budget" all evidenced; 0 FAIL, 2 low PROPOSED-ISSUE
TIER: L (see above)
CAPABILITY-COVERAGE: 11/11 falsification copies reproduced (green before, red for the named reason)
LIVE-BROWSER: not-applicable (merge re-check; the changed UI paths `ui/routes_report.py` and `ui/routes_catalog.py` were browser-checked in the cycle-4 B verdict and the merge adds no UI surface)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-opus-5-5)
EXPLANATION: The merge keeps d063's `RunBudget`, `parallel_run.py` and `run_execution.py` guards intact (two files byte-identical, one added `matches()` guard that I falsified). T-125's tier loop shares the single budget, every refused case is persisted INCONCLUSIVE, the EXECUTE stage is recorded failed on a brake, and tier order, zero-count and failures-first reporting hold through the real run endpoint. The rewritten protected test still pins all four required properties; the one lost pin (wipe of a refused entry profile) is d063's own ordering and is filed low.
Metrics: start=2026-10-07T12:10Z end=2026-10-07T13:05Z wall_min=55 agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=11 cycle=4-integration resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
slow: 12 importer test files 8.5 min (a browser-driven file in the extra set), uv sync 1.5 min, and a rate-limit 429 interruption mid-check of unknown length that is counted in wall_min. Wall passed the L 45 min deadline because of that stall; process row proposed.
