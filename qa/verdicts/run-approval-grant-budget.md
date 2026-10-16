# Verdict - run-approval-grant-budget

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 1
**Reviewed SHA:** 0e544ba907ec89da52818d3750899708f1587110 (base c4d48ad109f1ef77f73ee9172866cc5feeca7063, branch worktree-agent-a70bbe56d22416ba9)

## Scope
Fix cycle 1 for the cycle-0 FAIL (verdict commit a80c2b21): `probe_request` undercounted the probes a
LIVE_CASE run really spends (ISS-d063-grant-budget-3). The verdict also re-confirms that the areas that
passed at cycle 0 have not regressed: ISS-d063-grant-budget-1 and -2, AT-570, consent CN5/CN10/CN11 and
core-invariants C12.

Cycle-1 diff (a80c2b21..0e544ba9, verified with git):
- stages/execute.py gains `step_probe_floor` and `probe_request` (261 lines).
- stages/run_budget.py loses the old `probe_request`.
- stages/run_launcher.py now imports `probe_request` from execute (300 lines).
- tests/test_probe_floor_matches_runtime.py is new.
- tests/test_run_approval_grant_budget.py: one expected count changes from 3 to 4.

explore_consent.py, core/consent.py and ui/routes_crawl_approval.py are byte-unchanged since cycle 0. Scope
match, max_probes validation, schedule/release gating and legacy rows are therefore unchanged and were
re-run green.

## Independent checks (outputs and exit codes in .work/checker-rab-c1/)
- **Preflight.** Main .venv python 3.11.16 with PYTHONPATH set to the worktree src: PREFLIGHT_OK, and the
  import comes from the worktree src (preflight.txt).
- **Runtime-spend audit (by reading the code).** Probes are charged only in browser/assertions.py: `_probe`,
  called from `settle` (url or visible_text polling), `met` and the final pass of `assert_expected`, and from
  evidence.py `_field_sample`, which session.fill calls twice. No other session handler charges a probe:
  goto, click (click_recovery trial-clicks are not budget probes), select, upload, wait, hover, press_key,
  scroll, back and screenshot. There are no case retries (run_case_pipeline), and session start, entry
  cases and the serial or parallel paths spend no probes outside case.steps.
- **Independent enumeration probe (probe_enum.py / probe_enum.out, exit 0).**
  - It enumerates every `Action` member (11) and every subset of `ExpectedState.model_fields`. The 6 fields
    are url, visible_text, absent_text, dom_asserts, visual_signal and network, taken from the schema.
  - Lists hold several values. FILL is tried with both a plain and a `{{SECRET:K}}` value.
  - It runs the REAL `execute._run_steps` with the REAL `BrowserSession.fill`, `_field_sample`, `settle`,
    `_met` and `assert_expected` bound onto a stub, which is stronger than the maker's stubbed fill.
  - Results: 768 rows, 0 errors. Spend at the all-met minimum equals the floor in every row (0 under, 0 over).
    On an all-unmet (polling) page, spend is never below the floor.
  - All 11 actions in one case: spend 27, floor 27. A grant one probe short (26) stops with
    `RunBudgetExceeded ... max_probes`.
- **Mutation of the equality test (isolated full copies under .work/checker-rab-c1/mut_*; the candidate was
  not touched).**
  - Note: `scripts/regression_proof.py` (imported by tests/conftest.py) prepends the repo `src`, which defeats
    a PYTHONPATH-only mutation. The first attempt was invalid for that reason, so I made complete
    src/tests/scripts/pyproject copies.
  - The baseline copy passed 17 of 17. Each mutation was killed:
    - fill 2 -> 1: 3 failed.
    - ASSERT/expectation 2 -> 1: 11 failed.
    - settle +1 dropped: 7 failed.
  - Logs are in mutrun2_*.out, with the import origin confirmed per copy.
- **pytest (26 files, without -q).**
  - Files: the new file, grant_budget, run_budget_judge_time, run_launcher (plus _approval,
    _priorities_approval, _retired), execute (plus _assertions, _new_actions, _serial_evidence_scope),
    ui_crawl_approval (plus _list), consent, explore_consent, ui_auth_host_and_consent,
    credential_run_approval, ui_runs (plus _live_case_approval, _queue, _serial_entry_mix_live,
    _serial_entry_order), schedule_wiring, regression_trigger, approval_prod_gate_paths and team_run_launcher.
  - Result: 329 passed, rc 0, 333 s (pytest_scoped.out, pytest_scoped.exit).
- **ruff check** on the 8 changed paths: clean, rc 0 (ruff.out).
- **doctor:** clean, rc 0 (doctor.out).

## Findings
1. **Floor vs runtime: no undercount found.** This holds for any step kind, expectation combination, secret
   fill or polling wait. Polling only ever spends more, which the runtime brake decides.
2. **The equality test is real.** Lowering any of the floor's three terms by 1 fails it.
3. **One concept, one place: holds.** The old run_budget.py copy is removed. `grep probe_request|step_probe_floor`
   finds only execute.py (definition) and run_launcher.py (the single caller). The table sits beside
   `_run_steps`/`_declares_expectation` and reuses `_declares_expectation`; it does not duplicate it.
4. **The Pathlynks `>=` assertion is adequate.** Exact equality is pinned per kind by the parametrized test and
   by my 768-row enumeration. The Pathlynks test adds `floor > 20`, which guards the cycle-0 regression.
5. **Advisory, non-blocking.**
   - run_launcher.py is at exactly 300/300 lines. ux-advisory-wiring also edits it and merges later, so it will
     need to extract code or it will trip the C2 cap.
   - tests/run_approval_fixture.py's docstring still says "a case run spends actions, never probes", which is
     stale.
   - The maker's FakeSession.fill stubs two probes rather than running the real `session.fill`. My probe covers
     the real path.

## Remaining gates
- Full combined suite after merge (repository release/integration gate).
- Push and close-out are the maker's or orchestrator's, per D-007. This checker does not push.

## Accounting
- Wall time about 1,870 s (launch to pre-verdict), including 333 s of pytest and about 30 s of mutation runs.
  This is over the 400 s focus target and over the 10% target. **Overrun recorded, not waived.**
- Checker tokens (actual_total) are not measured by this host: null. Maker cycle-1 usage is unknown, so the
  ratio is unverified.
- No review_budget.py assess gate was run per phase. This is a process miss; it is recorded, and it does not
  affect the verification evidence.
