# Verdict (coordinator B, blind) — t125-catalog, fix cycle 4

Cycle checked: 4
Verdict path: qa/verdicts/t125-catalog.b.md · Checkpoint: qa/checkpoints/t125-catalog.b.md
Date: 2026-10-07 · bound to `D:/autoTesting` · source `52bba0b7` (branch `codex/t125-cycle4`; base `bd2fe8f4`; checked in detached worktree `.worktrees/t125-b-check`)
Policy pin: proportional-verification/2026-10-06.6 (+ the .7 rules for an in-flight unit). Judged against `qa/contracts/catalog.md` plus the "Standard packs (AT-588, additive)" section read from `3da63550`. No contract file edited.
I did not read coordinator A's verdict, checkpoint, evidence or commits.

VERDICT: PASS

## Check plan (step 0)
| Signal in the diff | Check run |
|---|---|
| New stage/schema/UI route (catalog, packs) | affected tests + CT1-CT9 falsifications, all in isolated copies |
| `ui/routes_catalog.py` new page, `routes_report.py` failures section, `app.py` link | live browser check (Mode D), own browser |
| `run_budget.py`, `parallel_run.py`, `run_execution.py`, `routes_runs.py` (HMAC RunApproval budget, D-018/CN10) | L, security trigger, dual check; ONE checker full suite; CN10 + approval deep-copy falsified |
| `schema/run.py` new `catalog_runnable_counts` | CT6(3) schema falsification |

TIER: L (cited trigger: `src/autotester/stages/run_budget.py:49` `approval.model_copy(deep=True)` and `:55` `require_approval`, plus `ui/run_execution.py` entry/serial `budget.try_consume`; changed non-test files bound to the HMAC run-approval budget, CN10). Dual check required; this is the second coordinator.

## Criteria (each re-run by me)
| Id | Result | Evidence (my own run) |
|---|---|---|
| CT1 pure/deterministic | MET | `test_catalog_is_pure_same_inputs_same_output[absent/draft/approved]` green; `catalog()` imports no Provider and opens no file for write (`stages/catalog.py` read in full). Mutant E1 (`created_at=datetime.now()` on the approved branch) RED on `[approved]`. |
| CT2 one entry per CaseClass | MET | `test_every_case_class_gets_exactly_one_entry_*` green; E2 (drop first class) RED on `..._approved`. |
| CT3 closed BlockedReason, null iff runnable | MET | `test_blocked_entries_always_carry_a_closed_reason`, `test_runnable_entries_never_carry_a_reason` green; E3 (needs_write reason -> None) RED `test_read_only_blocks_double_submit_needs_write_policy`. |
| CT4 no FlowSpec -> every row no_flowspec, page says so | MET | tests green; E4 (entries use flowspec_not_approved) RED on 3 tests. Browser: project `nofs` page shows "NO FLOWSPEC YET" plus the INGEST action on every class row (18 occurrences in the page source). |
| CT5 names the KEY, never a value | MET | `test_missing_credential_names_the_key_never_a_value`, `..._action_never_contains_the_real_env_value` green; E5 (action without the key) RED on 3 tests. |
| CT6(1) dispatch order static->behavioural->adversarial | MET | `test_real_trigger_orders_tiers_and_persists_blocked_pinned_cases[1,2]` drives `POST /projects/demo/run` (serial and width 2) and asserts dispatch call order. B1 (`tiers_to_run` reversed) RED on 3 tests including both trigger params. |
| CT6(2) never skip, executed set == stored cases | MET | same test asserts results, verdicts and `run.case_ids` equal all 9 stored cases, including pinned and catalog-blocked. B2 (`tiers_to_run` filters on runnable count, the contract's named sabotage) RED; B3 (skip a zero-runnable tier inside `_execute_with_trace`) RED on both params. |
| CT6(3) per-tier runnable counts incl. zero | MET | trigger test asserts `{"static":0,"behavioural":0,"adversarial":0}`; `test_catalog_counts_reject_malformed_measurements`. B4 (omit zero tiers) RED; B5 (validator accepts partial) RED `[counts0]`,`[counts1]`. Browser: run page prints "Catalog runnable-class counts — static: 0, behavioural: 3, adversarial: 0". |
| CT6(4) failures first, prominent, before passes | MET | `test_run_view_lists_cheap_tier_failures_first_ahead_of_passes` green. A1 (rank constant), A2 (sort by case id, the contract's named sabotage), A3 (failures section after passes), A4 (failed() never true) all RED on that test. Browser offsets: Failures 238 < T c_static 247 < T b_adv 316 < Other results 382 < T a_pass 396, whereas case-id order would put b_adv first. |
| CT7 one Catalog / one BlockedReason | MET | `grep`: one `class Catalog` (schema/catalog.py:119) and one `class BlockedReason` (schema/catalog.py:21) in `src/`; E8 (second BlockedReason in `stages/expand.py`) and E9 (second Catalog in `schema/run.py`) RED on the CT7 tests. |
| CT8 page honest: reason + the one action | MET | `test_ui_catalog.py` green (incl. reserved-reasons parametrised). E7 (drop the action text) RED on 4+ tests. Browser: each blocked row shows the label and "set GOOGLE_SIGNUP_TOKEN in the repo-root .env" or the INGEST action. E6 survived: see WARN. |
| CT9(a)/(b)/(c) | MET | D2 (gate off) RED on 8+; D1 (union keys spec-wide) RED `test_an_oauth_only_unset_secret_blocks_the_pack_not_the_login_rows`; D3b (keyword rule in two hunks: "google" text feeds the auth class and contributes a key) RED `test_a_flow_with_no_auth_field_never_blocks_on_credential` and the oauth-only test. D3 alone (key-level keyword only) survives but is inert by design, because `applicable_classes` is structural. |
| Standard packs (AT-588) | MET | `tests/test_catalog_packs.py` 13 tests green; `PackEntry` reuses `BlockedReason`; not-applicable pack distinct from blocked (browser: "NOT APPLICABLE" for month/year and Excel packs, OAuth pack "MISSING CREDENTIAL"). |
| CN10 (HMAC run-approval budget) | MET | See below. Entry and serial legs now debit the one shared `RunBudget`; a mismatched approval is rejected before any effect. |

## CN10 / approval deep-copy falsification (copies only)
- C1 `RunBudget.__init__` `self._approval = approval` (no copy): RED `test_budget_owns_a_snapshot_of_its_approval_not_the_callers_live_object`.
- C1b shallow `model_copy()`: SURVIVED. Equivalent mutant: `RunApproval` has only scalar fields (`schema/approval.py:51-88`), so a shallow copy cannot alias anything. Not a gap.
- C2 `require_approval` -> `if False:`: RED `test_parallel_entry_only_rejects_mismatched_budget_before_any_effect`.
- C3 entry-case `try_consume` removed (`run_execution.py` `_run_entry_case`): RED on many params of `test_internal_execution_spends_one_budget_across_tiers_and_all_legs`.
- C4 serial normal-case `try_consume` removed: RED on the same test.
- C6 fresh `RunBudget(approval)` per tier (budget not shared across tiers): RED on the same test.
- C5 `budget.require_approval(approval)` removed in `parallel_run.run_cases`: SURVIVED. Redundant defence: the only production caller (`run_execution._run_cases_in_parallel`) calls `require_approval` first, and C2 shows that guard is pinned. WARN only.
- Approval verification itself is the unchanged `_require_live_case_approval` in `trigger_run`; I read the full `routes_runs.py` diff and this unit does not weaken HMAC verification.

CAPABILITY-COVERAGE: 29 isolated mutants run, each in its own copy with the 111-test affected set green in the copy before any edit. 25 RED for the named reason; 4 survivors explained (C1b equivalent, C5 redundant, D3 inert with D3b RED, E6 label WARN). Falsification floor met for CT1-CT9 and CN10.

## Diff scope (4c)
`git diff bd2fe8f4...52bba0b7 --stat`: 20 files, all inside the unit (catalog schema/stage/route, run-path budget, report failures section, app registration, tests, MAP). No function, class, route or config key removed; no test deleted (test counts: test_ui_report 12->14, serial_entry_order 1->5, test_schema 11->13, parallel_run_approval 9->10; the removed `def` lines in test diffs are signature reflows). Docstring shortening in `app.py`, `routes_report.py` and `run_execution.py` removes prose only. No assertion weakened.

## Verify commands
- Affected tests: all inside the one full suite below; plus the 111-test affected set in a copy: green.
- `ruff check src tests scripts`: All checks passed.
- `autotester doctor` at the committed head: 10 violations, none a product defect. Baseline (7, outside the T-125 diff): `ledger-row-missing T-171`, `stale-generated docs/SNAPSHOT.md`, D-061 dangling at `at733-entry-cleanup.md:41,47`, `at113-crawl-completion.b.md:209,281`, `SNAPSHOT.md:44`. T-125-owned (3): manifest prose citations of D-061 at `qa/manifests/t125-catalog.md:581,594,606`, a wording-level low row. No MAP drift.

## Full suite (ONE; PIDs 57780 pytest.exe -> 41116 -> 60612 python, in `.worktrees/t125-b-check`)
`uv run pytest` (no -q, no -x): **5 failed, 2274 passed, 6 skipped, 14 xfailed, 15 warnings in 3481.34s (0:58:01)**.
| Failure | Attribution |
|---|---|
| tests/test_citations.py::test_the_real_tree_has_no_dangling_citation | BASELINE: fails identically at `bd2fe8f4` (D-061 dangling). The T-125 manifest adds 3 more citations to the same already-red list (P1). |
| tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered (81 == 82) | BASELINE: red at `bd2fe8f4`; `.goal/goal.json` bookkeeping, not in the diff. |
| tests/test_goal_done_checks.py::...done_check_naming_a_file_that_does_not_exist (T-171 `tests/test_permission_surface.py`) | BASELINE: red at `bd2fe8f4`. |
| tests/test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus | LOAD/BASELINE timing (known AT-750/AT-757): failed alone at 24.6 s under machine load, and at `bd2fe8f4` alone at 3.22 s vs the 3.0 s bound. `core/redact` is untouched by this diff. |
| tests/test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild | LOAD timing: PASSED when re-run alone. Not T-125. |
T-125-owned failures: 0.

## LIVE-BROWSER
`D:/autoTesting/.work/t125-b-browser-evidence/` (report.json plus 4 screenshots). The Playwright MCP failed to connect and the claude-in-chrome extension was not connected, so I drove my own Chromium through the project's Playwright (python) against a uvicorn server I started (PID 19560, stopped by that PID) on a scratch root with seeded projects. Walked: project detail -> clicked the "Test catalog" link -> `/projects/demo/catalog` (16 class rows + 3 pack rows, reasons and actions rendered); `/projects/nofs/catalog` (no_flowspec on every row); `/projects/demo/runs/run_1` (failures-first order, counts line); `/projects/zzz/catalog` -> 404. Console errors: 1, "Failed to load resource: 404", which is the deliberate unknown-project navigation. Persona walk: skipped (internal-tool operator audience, per manifest). Disclosure: the instrument is a scripted Chromium, not the MCP browser.

## WARN (non-blocking) and PROPOSED-ISSUE
- WARN CT8 label: mutant E6 (`missing_credential` pill label rendered as the bare enum) survives; the row still carries the specific action text, so CT8's "reason and the one action" holds. That one label is not pinned by a test.
- WARN redundancy: C5 above.
- WARN CT6(2) fixture: the real-trigger no-skip test has all three tier counts at 0, not the contract's literal "blocked static + runnable adversarial". Every skip mutant I tried (B2, B3) still goes red, so no FAIL.
- WARN CT5 wording: `SecretStore.load` (via `stages/catalog.py::_missing_keys`) reads `.env` values into process memory to answer `has_value`; they are never serialized or rendered (tests pin this). Same pattern as other callers; the contract says "never read, held".
PROPOSED-ISSUE: {"severity":"low","feature":"catalog","title":"t125 manifest cites D-061 at lines 581/594/606 with no D-061 in docs/DECISIONS.md on this branch; adds to the already-red test_citations list","evidence":"autotester doctor and tests/test_citations.py on 52bba0b7","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"catalog","title":"No test pins the missing_credential pill label (mutant E6 survives); CT6(2) real-trigger fixture lacks a runnable adversarial case with a blocked static tier","evidence":"tests/test_ui_catalog.py; tests/test_ui_runs_serial_entry_order.py::test_real_trigger_orders_tiers_and_persists_blocked_pinned_cases counts all 0","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"process","title":"L unit full suite took 58 min under machine load; wall 74 min against the 45 min L deadline","evidence":"pytest 3481.34s with other suites running concurrently","found_by":"checker-unit"}

SCOREBOARD: 9/9 criteria met (CT1-CT9 incl. CT6(1)-(4)), CN10 holds, standard packs hold, 0 T-125-owned test failures.
EXECUTOR: claude-sonnet-subagent (manifest) · checker: claude-opus-5-5 coordinator B, fresh context, not the builder.
EXPLANATION: Every contract criterion was re-run through the real run endpoint, the report page and a real browser, and each was falsified in an isolated copy, with the contract's named sabotages going red for the named reason. CN10's shared budget and the approval deep-copy are pinned by tests that fail when the guard is removed. The five full-suite failures are baseline or load, confirmed by re-running at `bd2fe8f4` or alone. The wall overran the L deadline because the one required suite ran 58 min under load.

Metrics: start=2026-10-07T15:17:39+05:30 end=2026-10-07T16:35:00+05:30 wall_min=77 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=0 mutations=29 cycle=4 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6 slow: full suite 58 min
