# Verdict B — d063-grant-budget (stacked: pathlynks-exact-host)

Date: 2026-10-07 · Coordinator B (second blind coordinator) · Bound root: D:/autoTesting/.worktrees/d063-grant-budget
Cycle checked: 0
Policy-Version: proportional-verification/2026-10-06.6
Base: bd2fe8f4 · HEAD checked: a4bd0a60 (branch merged master e633bc69, docs/qa only)

## Check plan (step 0)

TIER: L — security/auth: account-derived LIVE_CASE approval grant (src/autotester/core/consent.py::prepare_account_live_case), signing-key creation (core/ids.py::ensure_approval_key, ui/env_editor.py::create_env_value_if_absent), credential exact-host scope (browser/secrets.py::_host_matches); also concurrency (RunBudget, env lock). Dual check.

| Signal | Check | Done by |
|---|---|---|
| logic + security | manifest verify commands, ONE full suite | coordinator |
| capability rows | Capability coverage table, 9 rows, green/red/restored in throwaway copies | sub-checker 1 (rows 1-5), sub-checker 2 (rows 6-9 + gap mutants) |
| security/auth | adversarial probe of grant path, key creation, scope, leakage | sub-checker 3 (senior-software-engineer, fresh) |
| correctness | aggregate budget wiring, brake-swallowing, fill receipt, exact-host slice | sub-checker 4 (senior-software-engineer, fresh) |
| diff scope (4c) | removed/renamed symbols, test-assertion deletions | coordinator |
| UI | none: no screen/template/route-visible change (UI routes are backend gate/budget) -> Mode D not applicable; fixture-Chromium test ran inside the full suite | n/a |

SERIAL: none shared a port/DB; sub-checkers ran one pytest at a time in separate copies under C:/Users/Lenovo/AppData/Local/Temp/d063-checkerB. A second coordinator started its own full suite in the same worktree within the same second as mine (both uv processes created 01:29:33/34), so two suites overlapped in one clone; the one failure below is deterministic (assertion on goal.json content) and not a concurrency artefact.

## Evidence re-run

- `uv run ruff check src tests scripts` -> All checks passed.
- `uv run autotester doctor` -> exit 1, ONE violation: stale-generated docs/MAP.md (the manifest-reported 13 dangling D-06x citations and T-171 row are gone after the master merge). Low row P11.
- Full suite, `uv --directory <root> run pytest` (no -q), 01:29:34-01:56: `1 failed, 2314 passed, 5 skipped, 14 xfailed in 1589.00s`. The one failure is tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered: `.goal/goal.json` T-171 done_check is `tests/test_permission_coverage.py`, the test expects `tests/test_permission_surface.py`. Neither file is in this feature's diff (goal.json came with merge commit e633bc69; the test file is unchanged since bd2fe8f4), so it is not caused by the unit; filed as P12.
- Manifest "How to verify" pytest groups are covered by the same suite (all green apart from the item above); real-Chromium mix_live test is inside the suite (RAM was above its floor), no failure.
- 4c diff scope: 31 files, all in the manifests' "What changed" (session.py/evidence.py/video.py/assertions.py, etc.). No function/class/export/route/config key deleted or renamed; `set_env_values` refactored in place and still exported. Test edits: only docstrings removed and assertions added/parametrised (test_ui_runs_parallel_trace `status == "done"` became `("failed" if stopped else "done")`, same assertion kept for stopped=False); no assertion weakened, no skip/xfail added, not a protected change. Several pre-existing explanatory docstrings in session.py/run_execution.py were deleted to meet the 300-line cap (wording only).

## Criteria (manifest Acceptance 1-7 / CN11 clauses)

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | grant identity/scope exact | sub-checker probes: look-alike, trailing dot, userinfo, homoglyph, wildcard, wrong project/scheme, duplicate cases all refused; row bound to project.base_url/LIVE_CASE; R1b falsification red on `[scope]` | MET |
| 2 | selected keys only | unused COUNSELLOR key irrelevant (probe + test); R7 reproduced red | MET |
| 3 | positive finite brakes, grant path AND CLI | grant path: R2 reproduced; 0/neg/nan/inf/bool/1e30 refused. CLI half: no test exercises `approve` bounds; my mutation `if not math.isfinite(...) <= 0:` -> `if False:` in a throwaway copy leaves tests/test_approve_cli.py + test_approval_signing.py + test_consent.py at `59 passed` | NOT EVIDENCED for the CLI claim (see FAILURES P1) |
| 4 | key preparation | R3 reproduced; race (8 threads), override/stored/other entries preserved, lost-history refuses without touching .env/approvals | MET (low: `.env.lock` side file created on refusal, P9) |
| 5 | one aggregate RunBudget, matches approval, brakes named | R4, R5, G3, G4 reproduced; every BrowserSession construction path sets session.budget (serial entry, serial shared, parallel) | MET |
| 6 | stopped run reported failed with named brake | R8 reproduced (route-level EXECUTE span failed + named error) | MET |
| 7 | fill receipt, secrets never read | R6 reproduced; secret/password/masked fields never read (value_reads == 0); gaps low (P8) | MET |
| exact-host slice 1-4 | equality/child/sibling/parent/look-alike, strict bool, roundtrip, project.json narrowing | probe + diff of project.json (only 4 secret refs; allowed_domains, mask, write policy untouched); all `_host_matches` callers pass the flag | MET |

I1-I? (core-invariants C5/C12 as applied): no credential value in grant/scope/error/trace (probes); a stopped run never reports completed (all swallow sites re-raise or are followed by budget.check; sole exception P7 mislabels, still INCONCLUSIVE).

## Capability coverage

Reproduced in throwaway copies (green before from the copy, red after, restored):
R1 as written does NOT reproduce: replacing the `_host_matches(...)` clause with `False` keeps `[scope]` green (every key refused, which is what `[scope]` expects); red with `True` (`DID NOT RAISE`, the intended assertion) and with literal `False` on `[valid]`. Capability is falsifiable, the manifest cell is imprecise (P2). R2 red (`DID NOT RAISE` actions=0) · R3 red (`DID NOT RAISE SigningKeyMissing`) · R4 red (`DID NOT RAISE ValueError` match approval) · R5 red 5/10 `[*-actions]` · R6 red 2/11 at test_browser_actions.py:198 `value_reads == 0` · R7 red 2/2 (status 400 precondition; pinned only by setup) · R8 red 2/4 at :104 status == failed · R9 red 3/3 `TypeError ... missing keyword-only argument 'budget'` (wiring, not numeric brake, as the builder caveat says). Gap mutants: G2 red (incidental test), G3 red, G4 red 7 tests. G1 (CLI bound guard) SURVIVES, no covering test. M1 (drop `.sign()`) killed, M3 (wrong target) killed, M2 (`production=True` on the minted row) SURVIVES (50 passed).

CAPABILITY-COVERAGE: 8/9 table rows reproduced (R1 reproduced only with the corrected edit); 1 claimed guard (CLI bound validation, acceptance 3) has no row and survives mutation; 1 non-table mutant survives (M2).

## FAILURES

- [C3] sev: medium · acceptance 3 / CN11 "Operational brakes" and CN11 Verify ("each claimed guard has an isolated green-before/red-after/restored falsification"): the manifest claims the CLI refuses nonpositive/nonfinite bounds and defaults to positive values (cli_crawl.py approve_cmd, `min=1` options and the `math.isfinite` guard), lists it as an acknowledged gap, and no test covers it. Reproducible: copy the tree, set `if False:` at cli_crawl.py `if not math.isfinite(wall_clock) or min(max_actions, max_probes, wall_clock) <= 0:`, `pytest tests/test_approve_cli.py tests/test_approval_signing.py tests/test_consent.py` -> 59 passed (also unguarded: `min=1`, defaults 200/200/600). Fix: add tests that `approve` refuses `--wall-clock nan/inf/0`, `--max-actions 0/-1`, `--max-probes 0`, and that bare defaults mint a positive-bound row; record the red/green rows. · issue: P1

No other FAIL: remaining findings are below the evidence-to-block bar or are design decisions.

## Findings (non-blocking) and gate requests

PROPOSED-ISSUE: {"id":"P1","sev":"medium","criterion":"C3","title":"CLI approve bound guard (min=1 defaults, nan/inf refusal) has no test","evidence":"mutation `if False:` at cli_crawl.py approve_cmd bound check -> 59 passed in tests/test_approve_cli.py+test_approval_signing.py+test_consent.py","fix":"add CLI tests for nan/inf/0/negative refusal and positive defaults; add falsification row"}
PROPOSED-ISSUE: {"id":"P2","sev":"low","title":"Capability row 1 cell not reproducible as written","evidence":"replacing the _host_matches clause with False keeps test_account_grant_is_new_exact_and_bounded[scope] green; red only with True or on [valid]","fix":"correct the row's edit to True (or name [valid])"}
PROPOSED-ISSUE: {"id":"P3","sev":"low","title":"Minted grant pins production=False in no test","evidence":"core/consent.py::prepare_account_live_case production=False -> True: 50 passed (tests/test_consent.py + tests/test_core.py)","fix":"assert row.production is False and that production verification still applies"}
PROPOSED-ISSUE: {"id":"P4","sev":"medium","title":"Human-granted LIVE_CASE path: preflight asks for no probes but the run now spends them","evidence":"ui/routes_runs.py fallback covering_approval(...) passes only actions and wall_clock_s; evidence.py::_field_sample (2 probes per fill) and assertions._probe (1 per poll) spend probes; UI grant form cannot set max_probes (AT-675) so such a row stops at first fill/assert after a browser opened (fail-closed, named brake); sub-checker finding, not independently reproduced by coordinator","fix":"derive a probe request in the human-grant preflight like the account path (actions*20) or refuse in preflight"}
PROPOSED-ISSUE: {"id":"P5","sev":"medium","title":"Account-derived LIVE_CASE row can cover a later credential-less run (scope ignored by covering_approval)","evidence":"routes_runs.py fall-through to explore_consent.py::covering_approval matches project/kind/target only (CN5); sub-checker probe showed a no-secret run covered by granted_by account-derived:D-063 row; window is ~8s*actions from the row's expiry; CN11 says no transfer across scopes but CN5 defines the match key without scope","fix":"ignore account-derived rows in the human fall-through, or require scope equality for them; amend CN5/CN11 wording"}
PROPOSED-ISSUE: {"id":"P6","sev":"medium","priority":"security","title":"Unauthenticated UI can alter the inputs the self-grant derives from, then trigger a run","evidence":"ui/app.py has no auth/Origin/CSRF check; routes_project_edit.py edit/declare/undeclare secret and credentials routes can change base_url, allowed_domains and credential domains; POST /projects/{slug}/run now mints its own grant (routes_runs.py _require_live_case_approval) instead of needing a human-signed row; sub-checker finding from code reading, chain not run end to end","fix":"Origin/Host check on state-changing routes or a one-time human confirmation per target/scope; accepting the risk is a D-063 decision"}
PROPOSED-ISSUE: {"id":"P7","sev":"low","title":"conditions.enact swallows RunBudgetExceeded and reports NOT_RUN 'could not set mobile viewport'","evidence":"browser/conditions.py:48 except Exception around session.page.set_viewport_size; sub-checker probe printed not_run could not set mobile viewport: RunBudgetExceeded; grade stays INCONCLUSIVE and EXECUTE span stays failed","fix":"re-raise RunBudgetExceeded in enact, map to ERRORED in run_case"}
PROPOSED-ISSUE: {"id":"P8","sev":"low","title":"Fill receipt classification gaps and failure window","evidence":"sub-checker probes: type=text with autocomplete=current-password and a case-folded secret are copied into before=; sample length unbounded; a fill that raises leaves no receipt (try/finally starts after target.fill, session.py ~160-166); before-sample on a missing locator doubles the wait","fix":"classify by autocomplete/name patterns, cap sample length, wrap fill itself in the finally"}
PROPOSED-ISSUE: {"id":"P9","sev":"low","title":"Refused first use leaves .env.lock; credential rewrite temp file not gitignored","evidence":"env_editor.py::_env_lock creates .env.lock before the factory runs, lost-history refusal leaves the file (sub-checker probe); .env-*.tmp not matched by git check-ignore","fix":"take the lock only after cheap pre-checks, add **/.env-*.tmp to .gitignore, name the remedy (restore the key) in the 403 text"}
PROPOSED-ISSUE: {"id":"P10","sev":"low","title":"Shared budget is opt-in; a sticky stop can demote a case that finished all steps","evidence":"run_cases(budget=None) and default_session_factory(budget=None) fall back to reservation-only metering; unbudgeted callers in scripts/run_pathlynks_first_cases.py, scripts/regression_proof.py, scripts/bench_trial.py; parallel check_start sticky stop vs trailing budget.check (only when cap < sum of case costs, impossible for a derived grant)","fix":"make budget required for case runs; document or fix the demotion"}
PROPOSED-ISSUE: {"id":"P11","sev":"low","title":"docs/MAP.md stale after product edits (doctor exit 1, 1 violation)","evidence":"uv run autotester doctor -> stale-generated: docs/MAP.md","fix":"run autotester map before the PASS commit"}
PROPOSED-ISSUE: {"id":"P12","sev":"medium","title":"Full suite red on master-merge goal.json drift: test_revised_goal_contract_is_registered","evidence":"tests/test_goal_contract_registration.py expects T-171 done_check tests/test_permission_surface.py, .goal/goal.json (from merge e633bc69) has tests/test_permission_coverage.py; test file unchanged since bd2fe8f4; not in this feature's diff","fix":"checker/maker reconcile goal.json and the test on master (not this unit's files)"}
PROPOSED-ISSUE: {"id":"P13","sev":"low","title":"Exact-host mode is opt-in; UI-declared secrets default include_subdomains=True","evidence":"schema/project.py default True; routes_project_edit build_secret_ref never sets false; a credential scoped to vidysea.com would be granted for pathlynks.vidysea.com (recorded transparently in scope)","fix":"decide whether CN11 'no widening' wants exact-host as the grant default"}

HUMAN_GATE-REQUEST: D-063 risk acceptance - the account-derived self-grant plus an unauthenticated local UI (P6) lets any page that can POST to the UI edit credential domains and trigger a run that types a credential; does Umesh accept this for the local-only tool, or require an Origin/CSRF check or first-use human confirmation before the first account-derived grant per target?
HUMAN_GATE-REQUEST: CN5 vs CN11 (P5) - may a human-style LIVE_CASE match (project, kind, target) cover a run using an account-derived row minted for a different case set, or must account-derived rows be excluded from the human fall-through?

## Verdict

VERDICT: FAIL
SCOREBOARD: 6/7 criteria met (criterion 3 CLI half unevidenced), invariants C5/C12 hold
TIER: L (security/auth: core/consent.py::prepare_account_live_case, core/ids.py::ensure_approval_key; concurrency: stages/run_budget.py)
CAPABILITY-COVERAGE: 8/9 reproduced (R1 with corrected edit); CLI bound guard no row, survives
LIVE-BROWSER: not-applicable (no UI screen/template/navigation changed; fixture-Chromium test passed inside the full suite)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE P1-P13 above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Grant scope/identity, key preparation, aggregate budget and fill receipt are correct and falsified with 8 of 9 table rows reproduced; the exact-host slice is correct. The unit fails the floor only because the CLI bound guard claimed under acceptance 3 / CN11 has no test and survives a direct mutation (P1); the security design questions (P5, P6) need Umesh. The suite is green apart from a goal.json/test drift that comes from the merged master, not this diff.
Metrics: start=2026-10-07T01:29:11+05:30 end=2026-10-07T01:57:40+05:30 wall_min=28 agent_min=67 blocked_min=0 suite_runs=1 repeat_runs=0 mutations=19 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
