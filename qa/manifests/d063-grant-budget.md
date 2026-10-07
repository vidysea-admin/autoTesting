# Manifest — d063-grant-budget (account-derived LIVE_CASE grant + one aggregate run budget)

Contract: qa/contracts/consent.md CN1, CN5, CN11 as amended per D-068 (commit 2aed300e) plus CN1-CN10 (CN10: a bound never means unlimited); qa/contracts/parallel-run.md PR7; core-invariants C5/C12
Authority: D-063 (AT-674 Answer, 2026-10-06), D-066 (Origin/CSRF on state-changing UI routes, gate d063-self-grant-csrf = B) and D-068 (credentials = standing run approval, gate d063-cn5-vs-cn11 = B widened) — Approved-by: Umesh (docs/DECISIONS.md)
Goal task: T-122 prerequisite (the USER-account end-to-end run is a separate later step)
Policy-Version: proportional-verification/2026-10-06.6
Fix cycle: 2 of 2
Phase: READY
Tier: L — security/auth (approval grant + signing-key creation)
Dual check: required — approval grant and key creation are security/auth
Persona walk: skip (backend-only: no screen, navigation path or user-facing flow changed)
Issues addressed: AT-674; AT-570 (grant path); AT-651 credential-scope follow-through; D-066 CSRF (gate d063-self-grant-csrf); D-068 / gate d063-cn5-vs-cn11 (P5, P1); cycle-0 P2 (human-grant preflight asked for no probes) closed for credentialed projects
Executor: claude-sonnet-subagent (branch assembly of the uncommitted master work; the code was authored earlier by the root and its build workers)
Base: stacked on wave/pathlynks-exact-host tip 41ce907d (itself on bd2fe8f4)
Branch: wave/d063-grant-budget — commits f7adb2b9 (grant), 20594b23 (budget + fill receipt), 38f0f9bf (test setup), b90618c9 (fix cycle 1: CLI bound tests, scope row, production assertion; dual PASS recorded in 5201859a), then master fe6eb98a merged (524c2aaf) and the fix cycle 2 commit (the commit that carries this Status)
Cycle numbering: the maker dispatch called this "fix cycle 1"; the branch already holds cycle 1 (b90618c9, verdicts `Cycle checked: 1` PASS). This manifest therefore says `Fix cycle: 2`, so a checker reply of `Cycle checked: 2` cannot be confused with the stale cycle-1 verdict files. The cycle-0 failed criteria (C3 CLI path, capability row 1) were already closed by b90618c9; their defenders (tests/test_approve_cli_bounds.py, test_consent.py [scope]/[valid]) are re-run green below and unchanged in behaviour.

## Dependency on files that are NOT on this branch

None any more: master fe6eb98a (D-061..D-068, the amended consent.md, regenerated MAP/SNAPSHOT) is merged into this branch (524c2aaf). `autotester doctor` is clean at the fix-cycle-2 tip.

## What changed

Commit f7adb2b9 — account-derived grant:
- src/autotester/core/consent.py — validate_account_scope, validate_account_bounds, prepare_account_live_case (new signed row, verified through require_approval).
- src/autotester/core/ids.py — ensure_approval_key (explicit, create-if-absent, refuses when signed history lost its key).
- src/autotester/ui/env_editor.py — create_env_value_if_absent (serialized, owner-only atomic write).
- src/autotester/cli_crawl.py — approve: positive default bounds; nonpositive refused by typer `min=` (exit 2, before the body runs); nan/inf wall clock refused by the in-body `math.isfinite` check (exit 1).
- src/autotester/ui/routes_runs.py — _require_declared_values (only referenced keys gate), _require_live_case_approval (preflight before run id/dir/browser), trigger_run.
- tests: test_consent.py, test_core.py, test_ui_env_editor.py.

Commit 20594b23 — aggregate budget + fill receipt:
- src/autotester/stages/run_budget.py (RunBudgetExceeded, stop_reason, check/check_start/remaining_ms/matches), stages/parallel_run.py, stages/execute.py, ui/run_execution.py, ui/routes_runs.py::_execute_with_trace (one RunBudget; a stopped run is a failed EXECUTE span naming the brake).
- src/autotester/browser/session.py, assertions.py, evidence.py, video.py — budget-bounded timeouts; fill receipt (before/after, secret values never read).
- src/autotester/core/trace.py, schema/trace.py — optional StageSpan.error.
- tests: test_parallel_run_approval, test_browser_actions, test_browser_settle, test_execute_assertions, test_run_trace, test_ui_runs_parallel_crash_recovery, test_ui_runs_parallel_trace, test_ui_runs_serial_entry_screenshot_namespace.

Commit 38f0f9bf — setup-only test change (not a protected-oracle change; no assertion edited):
- tests/test_ui_runs_serial_entry_mix_live.py — `grant_live_case_approval(store, project="rd", target=project.base_url)` after the project is saved, like the sibling run tests. Without it the live test got 403 from the AT-570 gate.

## Fix cycle 1 (checker findings F1-F3)

- F1 (criterion 3 CLI path had no test): new tests/test_approve_cli_bounds.py (split from test_approve_cli.py at the 300-line cap) — 9 parametrized refusals (`--wall-clock` nan/inf/-inf/0/-1, `--max-actions` 0/-1, `--max-probes` 0/-1: exit != 0 and no approval row written) plus `test_approve_defaults_are_positive_finite_and_not_production`. No product code changed; approve_cmd already behaved as claimed.
- F2: capability row 1 re-derived. The earlier edit (clause -> `False`) kept `[scope]` green because `not any(False)` still refuses; the falsifying edit is clause -> `True`. Row replaced with real pasted output below.
- F3: tests/test_consent.py `[valid]` now also asserts `row.production is False` (optional item; one added assertion line; new row below). qa/manifests/pathlynks-exact-host.md re-pinned to proportional-verification/2026-10-06.6 and set ready-for-check (see that file's cycle-1 note); its claims are unchanged.

## Fix cycle 2 (D-066 CSRF, D-068 credentials = run approval)

Product edits, each in an existing file:
- src/autotester/ui/helpers.py — `_origin_allowed`, `origin_refusal`, `_OriginGuard`, `origin_guard_middleware` (D-066). Allowed origins are loopback (`localhost`, `127.0.0.1`, `::1`, any port) plus `AUTOTESTER_ALLOWED_ORIGINS` (comma/space separated, exact match, no wildcard; the server URL after go-live; read per request, so a value in the repo `.env` loaded at startup applies). Deliberately NOT "the Host header": a DNS-rebinding page has Origin == Host. A request whose `Origin` (or, absent that, `Referer`) is not allowed is refused 403 before any handler runs; no Origin/Referer and no cross-site `Sec-Fetch-Site` means a non-browser client and proceeds (CSRF is a browser attack, and a browser always sends Origin on a cross-site POST). Unparsable values are refused, never a 500.
- src/autotester/ui/app.py — `app = FastAPI(..., middleware=origin_guard_middleware())`: one guard for every POST/PUT/PATCH/DELETE route (24 today, walked from the OpenAPI schema by the test), so a future route is covered without anyone remembering. app.py is exactly 300 lines.
- src/autotester/core/consent.py — `ACCOUNT_KINDS` (LIVE_CASE, CRAWL, READ; ADVERSARIAL absent), `ACCOUNT_GRANTOR`, `is_account_derived`, `account_probe_budget`; `validate_account_scope` drops `case_ids` (scope = validated keys + domains, no case-set key; CN5 amended); `prepare_account_live_case` renamed in place to `prepare_account_grant(kind=...)`, which refuses ADVERSARIAL.
- src/autotester/stages/explore_consent.py::covering_approval (+ `_credential_approval`, `_default_account_keys`, `_approval_history`, `_require`) — the one gate every entry point already calls (`run_crawl` seam, CLI `explore`, UI `/explore`, UI `/run`). For LIVE_CASE/CRAWL/READ on a project that declares credentials: validate the selected keys (a refusal writes nothing), reuse any row of the same (project, kind, target) that covers the run including the probes it needs (human-granted first), else ensure the signing key (create-if-absent; refuses when signed history lost it) and mint ONE new signed row. Account-derived rows are never trusted by name: they pass the same intact/signature/expiry/production/bounds checks as a human row. If credentials are unavailable, the human-row path behaves exactly as before and the refusal message appends why the credential route was unavailable.
- src/autotester/ui/routes_runs.py::_require_live_case_approval — now a thin call to `covering_approval` (the inline mint, the `ensure_approval_key` lambda and the `except (SigningKeyMissing, ...)` moved into explore_consent). Behaviour change to flag: a covering human row now wins over minting, and a probe-less human row (the UI grant form cannot set probes, AT-675) no longer covers a credentialed run, so a fresh account row is minted. That closes cycle-0 P2 for credentialed projects.
- docs/MAP.md, docs/SNAPSHOT.md regenerated (`autotester map`, `autotester snapshot`): doctor was red on stale-generated after the master merge.

Tests (new unless stated):
- tests/test_ui_origin_guard.py — 43 tests: every state-changing route refuses a cross-site Origin (walked from OpenAPI, 24 routes), eight other cross-site shapes, same-origin accepted, Referer fallback, non-browser accepted, GETs unguarded, configurable origin, unparsable header, a refused credential edit writes nothing.
- tests/test_credential_run_approval.py — 22 tests: mint for each of LIVE_CASE/CRAWL/READ, reuse, any-case-set cover, exactness, wider run, expired row, forged row, ADVERSARIAL, the four remaining refusals leaving no trace, the seam, the CLI preflight, UI run, UI explore (with and without credentials), human-row precedence, probe-less human row.
- tests/test_consent.py (existing, edited, not a weakening): `prepare_account_live_case` -> `prepare_account_grant(kind=LIVE_CASE)`; the `[valid]` assertion `scope["cases"] == ["case-one"]` became `"cases" not in scope`, because amended CN5/CN11 say the scope is not a case-set key. One assertion changed because the contract changed; disclosed for the checker's protected-test review.

Not done, and why: no per-route Origin check inside handlers (the middleware is the single place); real authentication (role-based) is a stated follow-up in D-066, not built; `.env.example` and docs/ARCHITECTURE.md prose are untouched (ARCHITECTURE prose needs its own DECISIONS entry; `AUTOTESTER_ALLOWED_ORIGINS` is documented in helpers.py and here); no senior-engineer review agent and no checker was dispatched (instructed).

## Acceptance (each maps to a CN11 clause)

1. Grant identity/scope: a new grant derives only from declared, provisioned, in-scope credentials for the exact project/run kind/target (D-068: not bound to a case set); an out-of-scope key, wrong project or undeclared key refuses.
2. Selected credentials only: keys actually referenced by the requested case set gate the run; unused role keys do not.
3. Positive finite brakes: nonpositive or nonfinite actions, probes, wall clock refuse (grant path and CLI).
4. Key preparation: explicit, create-if-absent, preserves existing key/overrides/other entries, refuses without writing when signed history lost its key.
5. One aggregate RunBudget across serial, entry and parallel; a shared budget must match the approval; every brake is named.
6. A stopped/truncated run is reported failed with the named brake, never as completed E2E.
7. The fill receipt records before/after values redacted; secret values are never read.
8. D-066: every state-changing UI route refuses a cross-site Origin before its handler runs; a same-origin (loopback) POST is accepted; the allowed origin is configurable (`AUTOTESTER_ALLOWED_ORIGINS`) for the server URL.
9. D-068 (CN1/CN11): a project that declares credentials and has them provisioned gets an automatically minted, HMAC-signed approval row for LIVE_CASE, CRAWL and READ against its declared target, with no per-run human approval, at the seam, CLI explore, UI explore and UI run.
10. D-068 (CN5): one account-derived row covers any run of the same (project, run_kind, target) whatever case set minted it; exactness (slash/case/query, project, kind) is unchanged.
11. ADVERSARIAL never gets an automatic grant.
12. Still refused: no declared credentials, declared but not provisioned, a domain outside the declaration, a lost signing key, a forged or unsigned row, an expired row, a bound the row does not cover; a refusal leaves no row, key or crawl directory behind.

## Verification scope

Policy-Version: proportional-verification/2026-10-06.6
Tier: L (security/auth). Base / checked state: tip of wave/d063-grant-budget at the manifest commit (see git log).
Affected tests / full-suite trigger: affected files only; the builder ran no full suite. Full suite, two blind checkers (Dual check) and senior review are mandatory before PASS.
Metrics: start=2026-10-07 end=2026-10-07 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=17 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6

## How to verify (commands + expected)

- `uv run ruff check src tests scripts` -> All checks passed
- `uv run pytest tests/test_consent.py tests/test_core.py tests/test_ui_env_editor.py` -> 60 passed, 1 skipped (cycle 1: tests/test_approve_cli_bounds.py tests/test_approve_cli.py tests/test_consent.py -> 57 passed)
- `uv run pytest tests/test_parallel_run_approval.py tests/test_browser_actions.py tests/test_browser_settle.py tests/test_execute_assertions.py tests/test_run_trace.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_ui_runs_live_case_approval.py tests/test_ui_runs.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_resilience.py` -> all pass
- `uv run pytest tests/test_ui_runs_serial_entry_mix_live.py` -> NOTE: the test hard-codes `RAM_FLOOR_MB = 3584` and ignores the env var, so it SKIPs under low RAM (2767 MB free here). To run it, set that constant to 0.0 in a throwaway copy.
- `uv run autotester doctor` -> `doctor: clean`
- Fix cycle 2: `uv run pytest tests/test_ui_origin_guard.py tests/test_credential_run_approval.py tests/test_consent.py` -> 43 + 22 + the existing consent file all pass; affected set: see Actual outputs

## Actual outputs (maker's own run, 2026-10-07, worktree D:/autoTesting/.worktrees/d063-grant-budget)

- ruff at tip: `All checks passed!`
- commit 1 state: `60 passed, 1 skipped, 1 warning in 2.93s`.
- commit 2 state, 12 run/browser files plus mix_live: `110 passed, 1 failed in 6.53s`; the one failure was tests/test_ui_runs_serial_entry_mix_live.py (403 "no approval exists", the AT-570 gate), fixed by commit 3.
- mix_live on a throwaway copy with the floor at 0.0 and real Chromium: `1 passed, 1 warning in 14.84s`.
- doctor at tip (manifest included): 16 violations: ledger-row-missing T-171; stale-generated docs/MAP.md; stale-generated docs/SNAPSHOT.md; 13 decision-citation-dangling (D-061/D-063/D-064). The base bd2fe8f4 plus exact-host already shows 9 of them (T-171, MAP/SNAPSHOT, 6 dangling incl. D-063 in pathlynks-exact-host.md); this manifest adds 7 dangling citations of D-061/D-063/D-064. None is caused by product code on this branch: the DECISIONS.md entries and regenerated MAP/SNAPSHOT/FEATURES are uncommitted in the main tree and the dangling set clears when DECISIONS.md lands. Root-clutter (at113-fixture-*, pytest-of-unknown) is a main-tree-only pre-existing condition and does not appear in a fresh worktree.

- Fix cycle 2 (2026-10-07, same worktree): `uv run ruff check src tests scripts` -> `All checks passed!`; `uv run autotester doctor` -> `doctor: clean` (after `autotester map` and `autotester snapshot`; it was 2 stale-generated violations before regeneration).
- Fix cycle 2 affected set (consent, approval signing, approve CLI, explore consent/login, parallel-run approval, permission coverage, core, orchestrate-resume, the new origin and credential tests, and every `tests/test_ui_*.py`): `583 passed, 2 skipped, 1 failed in 323.84s; the one failure, tests/test_core.py::test_env_creation_is_coordinated_across_processes, is a 15 s child-process handshake timeout under machine load (files untouched by this branch: ids.py, env_editor.py, test_core.py), and passed on re-run: 1 passed in 14.85s`. A first pass of the same set had 1 failure, `test_ui_runs_parallel_trace.py::test_a_declared_fake_secret_never_appears_raw_in_the_trace[True]` (it granted a probe-less human row and asserted the last row is the account row); fixed in product code (a probe-less human row does not cover a credentialed run), not by editing the test.
- No full suite was run (instructed); line counts: app.py 300, helpers.py 250, consent.py 220, explore_consent.py 127, test_credential_run_approval.py 286, test_ui_origin_guard.py 133.

## Capability coverage (each new claim -> its isolating falsification)

Method: `git archive` of the branch tip into a throwaway copy outside the tree, one edit at a
time, original restored byte-identical after each, runner re-run before/after/restored. Neither
D:/autoTesting nor the worktree was mutated.

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| 1 | grant refuses a credential outside its domain scope | tests/test_consent.py::test_account_grant_is_new_exact_and_bounded[scope] | core/consent.py::validate_account_scope: `_host_matches(host, d, ref.include_subdomains) for d in ref.domains` -> `True for d in ref.domains` (cycle 0 used `False`, which still refuses, so it did not reproduce) | before `13 passed in 0.12s`; after `FAILED tests/test_consent.py::test_account_grant_is_new_exact_and_bounded[scope]`, `1 failed, 12 passed in 0.20s`; restored `13 passed in 0.08s` (byte-identical) |
| 3 | zero/negative actions refused | same test, `[actions]` | core/consent.py::validate_account_bounds: drop `actions <= 0 or` | before `36 passed in 0.15s`; after `FAILED ...[actions]`, `1 failed, 35 passed in 0.34s`; restored `36 passed in 0.16s` |
| 4 | lost verification key refuses instead of regenerating | tests/test_core.py::test_explicit_approval_key_preparation[lost] | core/ids.py::ensure_approval_key: `if any(row.signature ...)` -> `if False` | before `14 passed in 1.72s`; after `FAILED ...[new] ...[lost] ...[malformed]`, `3 failed, 11 passed in 1.75s`; restored `14 passed in 1.35s` |
| 5 | shared budget must match the approval | tests/test_parallel_run_approval.py::test_explicit_budget_has_no_reservation_and_must_match_approval | stages/parallel_run.py::run_cases: `if budget is not None and not budget.matches(approval)` -> `if False` | before `22 passed in 0.23s`; after `FAILED ...must_match_approval`, `1 failed, 21 passed in 0.32s`; restored `22 passed in 0.17s` |
| 5 | max_actions brake enforced | tests/test_parallel_run_approval.py::test_budget_spends_cannot_replenish_or_bypass | stages/run_budget.py::_consume: `if actions_after > approval.max_actions` -> `if False` | before `22 passed in 0.13s`; after `8 failed, 14 passed in 1.21s` (first `FAILED ...[nan-actions]`); restored `22 passed in 0.12s` |
| 7 | fill receipt never reads secret values | tests/test_browser_actions.py::test_fill_receipt_observes_values_but_never_reads_secrets | browser/evidence.py::_field_sample: `if secret or locator in ...secret_locators` -> `if False` | before `24 passed in 0.27s`; after `FAILED ...[placeholder] ...[previous]`, `2 failed, 22 passed in 0.45s`; restored `24 passed in 0.23s` |
| 2 | only referenced keys gate a run | tests/test_ui_runs_parallel_trace.py::test_a_declared_fake_secret_never_appears_raw_in_the_trace | ui/routes_runs.py::_require_declared_values: `if cases is None` -> `if True` (all declared keys gate) | before `29 passed, 1 warning in 4.39s` (6 UI run files); after `2 failed, 27 passed` (`...never_appears_raw_in_the_trace[False]`, `[True]`); restored `29 passed in 3.08s` |
| 6 | a stopped run is a failed EXECUTE span | tests/test_ui_runs_parallel_trace.py::test_a_real_run_writes_a_trace_with_at_least_one_span | ui/routes_runs.py::_execute_with_trace: `status="failed" if budget.stop_reason else "done"` -> `status="done"` | before `29 passed in 3.31s`; after `2 failed, 27 passed` (`...at_least_one_span[True-1]`, `[True-2]`); restored `29 passed in 3.27s` |
| 5 | serial path takes the shared budget | tests/test_ui_runs_serial_resilience.py | ui/routes_runs.py::_execute_with_trace: drop `budget=budget` from the serial call | before `29 passed`; after `12 failed, 17 passed` (first `test_a_grader_crash_for_one_of_three_serial_cases...`); restored `29 passed in 3.20s`. Caveat: this fails because the helper requires the budget, so it proves the wiring is required, not a numeric brake |
| 3 | CLI refuses nan/inf bounds, writes no row | tests/test_approve_cli_bounds.py (node `test_approve_refuses_a_nonpositive_or_nonfinite_bound_and_writes_nothing`) | cli_crawl.py::approve_cmd: `if not math.isfinite(wall_clock) or min(...) <= 0:` -> `if False:` | before `10 passed in 0.32s`; after `2 failed, 8 passed in 0.45s` (`FAILED ...[--wall-clock-nan]`, `FAILED ...[--wall-clock-inf]`); restored `10 passed in 0.34s` (byte-identical). The 0/negative cases stay green under this edit because typer's `min=` refuses them first (exit 2); they are tests of the CLI surface, not of this in-body check |
| 3 | CLI defaults are positive finite and not production | same file, `test_approve_defaults_are_positive_finite_and_not_production` | cli_crawl.py::approve_cmd: `production: bool = typer.Option(False, ...)` -> `True` | before `10 passed in 0.33s`; after `FAILED ...test_approve_defaults_are_positive_finite_and_not_production`, `1 failed, 9 passed in 0.43s`; restored `10 passed in 0.30s` (byte-identical) |
| 1 | a minted account grant is never production | tests/test_consent.py::test_account_grant_is_new_exact_and_bounded[valid] | core/consent.py::prepare_account_live_case: `production=False` -> `production=True` | before `13 passed in 0.06s`; after `FAILED ...[valid]`, `FAILED ...[unused]`, `2 failed, 11 passed in 0.20s`; restored `13 passed in 0.07s` (byte-identical) |

### Fix cycle 2 rows (D-066 / D-068)

Method: `git archive`-equivalent copy of the worktree (src, tests, scripts, pyproject.toml, uv.lock, .env.example) into a throwaway directory OUTSIDE the worktree (`%TEMP%/d063c1-falsify-*`), one single-hunk edit at a time, runner = the named node on the worktree venv with `PYTHONPATH=<copy>/src:<copy>/scripts`, original restored and sha256-compared after each. Runner: `scratchpad/d063c1/runner.py` (17 rows, run once end to end, output kept in the maker's scratchpad). The bound tree was never mutated. An earlier pass of the same runner showed rows D8/D9/D10 SURVIVING (the shortfall checks, not the signature/expiry/bound checks, were what the tests hit); the tests were tightened (forged row also widens `max_probes`; stale row has an equal wall clock; the bound row moved to `test_consent.py`), and the table below is the second, full pass.

| Criterion | capability | the check that covers it (defender) | the falsifying edit | observed |
|---|---|---|---|---|
| 8 | cross-site origin refused | tests/test_ui_origin_guard.py | ui/helpers.py::origin_refusal: `if _origin_allowed(origin):` -> `if True:` | `C1`: 43 passed -> 34 failed, 9 passed (first `test_every_state_changing_route_refuses_a_cross_site_origin[POST-/projects/x/cases]`) -> 43 passed; restored byte-identical (sha256) |
| 8 | guard covers every state-changing route | tests/test_ui_origin_guard.py (route walk over OpenAPI) | ui/app.py: `middleware=origin_guard_middleware()` -> `middleware=[]` | `C2`: 43 passed -> 35 failed, 8 passed -> 43 passed; restored byte-identical (sha256) |
| 8 | same-origin (loopback) accepted | tests/test_ui_origin_guard.py::test_a_same_origin_post_reaches_the_handler | ui/helpers.py: `_LOOPBACK_HOSTS = {...}` -> `set()` | `C3`: 4 passed -> 4 failed -> 4 passed; restored byte-identical (sha256) |
| 8 | allowed origin configurable | tests/test_ui_origin_guard.py::test_the_allowed_origin_is_configurable_for_the_server_url | ui/helpers.py::_origin_allowed: listed-origin clause -> `if False:` | `C4`: 1 passed -> 1 failed -> 1 passed; restored byte-identical (sha256) |
| 8 | Sec-Fetch-Site fallback | tests/test_ui_origin_guard.py::test_other_cross_site_shapes_are_refused | ui/helpers.py::origin_refusal: add `cross-site` to the allowed Sec-Fetch-Site set | `C5`: 8 passed -> 1 failed, 7 passed (`[headers6]`) -> 8 passed; restored byte-identical (sha256) |
| 8 | Referer fallback | tests/test_ui_origin_guard.py::test_other_cross_site_shapes_are_refused | ui/helpers.py::origin_refusal: referer branch -> `if False:` | `C6`: 8 passed -> 1 failed, 7 passed (`[headers5]`) -> 8 passed; restored byte-identical (sha256) |
| 9 | credentials mint a signed, persisted row, no human step | tests/test_credential_run_approval.py::test_declared_provisioned_credentials_mint_a_signed_row_with_no_human_step | stages/explore_consent.py::_credential_approval: `return store.add_approval(approval)` -> `return approval` | `D1`: 3 passed -> 3 failed -> 3 passed; restored byte-identical (sha256) |
| 9 | every shipped entry point uses it (seam, CLI preflight, UI run, UI explore) | tests/test_credential_run_approval.py (whole file) | stages/explore_consent.py::covering_approval: `if kind not in ACCOUNT_KINDS or not project.secrets:` -> `if True:` | `D2`: 22 passed -> 15 failed, 7 passed -> 22 passed; restored byte-identical (sha256) |
| 9 | probes the run needs are required of a covering row | tests/test_credential_run_approval.py::test_a_probe_less_human_row_does_not_cover_a_credentialed_run | stages/explore_consent.py::_credential_approval: reuse `_require(..., bounds, probes)` -> `_require(..., bounds)` | `D11`: 1 passed -> 1 failed -> 1 passed; restored byte-identical (sha256) |
| 10 | one row covers any case set of the same triple | tests/test_credential_run_approval.py::test_a_row_covers_any_case_set_of_the_same_triple | stages/explore_consent.py::_credential_approval: reuse return -> `raise ApprovalRequired('x')` | `D3`: 1 passed -> 1 failed -> 1 passed; restored byte-identical (sha256) |
| 11 | ADVERSARIAL never automatic | tests/test_credential_run_approval.py::test_adversarial_never_gets_an_automatic_grant | core/consent.py: add `ApprovalKind.ADVERSARIAL` to `ACCOUNT_KINDS` | `D4`: 1 passed -> 1 failed -> 1 passed; restored byte-identical (sha256) |
| 12 | no declared/provisioned credentials refused | tests/test_credential_run_approval.py::test_refusals_that_remain_leave_no_trace | core/consent.py::validate_account_scope: `if not account_keys:` -> `if False:` | `D5`: 4 passed -> 1 failed, 3 passed (`[declared-not-provisioned]`) -> 4 passed; restored byte-identical (sha256) |
| 12 | domain outside the declaration refused | tests/test_credential_run_approval.py::test_refusals_that_remain_leave_no_trace | core/consent.py::validate_account_scope: domain clause -> `not (True or any(...))` | `D6`: 4 passed -> 1 failed, 3 passed (`[domain-outside-the-declaration]`) -> 4 passed; restored byte-identical (sha256) |
| 12 | lost signing key refused, nothing written | tests/test_credential_run_approval.py::test_refusals_that_remain_leave_no_trace | core/ids.py::ensure_approval_key: `if any(row.signature ...)` -> `if False:` | `D7`: 4 passed -> 1 failed, 3 passed (`[lost-signing-key]`) -> 4 passed; restored byte-identical (sha256) |
| 12 | bad signature refused | tests/test_credential_run_approval.py::test_a_forged_account_row_is_never_honoured | core/consent.py::_reject_reason: `if not signed_and_verified:` -> `if False:` | `D8`: 1 passed -> 1 failed -> 1 passed; restored byte-identical (sha256) |
| 12 | expired row refused | tests/test_credential_run_approval.py::test_an_expired_account_row_is_replaced_by_a_new_one | core/consent.py::_reject_reason: `if approval.is_expired(now):` -> `if False:` | `D9`: 1 passed -> 1 failed -> 1 passed; restored byte-identical (sha256) |
| 12 | bound the row does not cover refused | tests/test_consent.py::test_every_rejection_reason_is_reported_not_just_the_first | core/consent.py::_shortfalls: `if actions > approval.max_actions:` -> `if False:` | `D10`: 1 passed -> 1 failed -> 1 passed; restored byte-identical (sha256) |

Defender of each acceptance criterion (fix cycle 2): 8 -> `tests/test_ui_origin_guard.py` (6 rows above); 9 -> `tests/test_credential_run_approval.py` (D1, D2, D11); 10 -> `tests/test_credential_run_approval.py::test_a_row_covers_any_case_set_of_the_same_triple` and `::test_exactness_survives_account_derived_rows`; 11 -> `tests/test_credential_run_approval.py::test_adversarial_never_gets_an_automatic_grant`; 12 -> `tests/test_credential_run_approval.py::test_refusals_that_remain_leave_no_trace`, `::test_a_forged_account_row_is_never_honoured`, `::test_an_expired_account_row_is_replaced_by_a_new_one`, `tests/test_consent.py`. Cycle-0 criteria 1-7 keep their cycle-0/1 defenders (rows above this subsection); the cycle-0 failed items are defended by `tests/test_approve_cli_bounds.py` (C3) and `tests/test_consent.py::test_account_grant_is_new_exact_and_bounded[scope]/[valid]` (row 1), green in the affected run below.

Gaps stated, not hidden: `exactness_survives_account_derived_rows` and `_default_account_keys` (login-case key selection) have no isolated falsification of their own; no real-Chromium or real-browser Origin test (the check is a header test through TestClient, as a browser would present it); no test that a deployed server URL works end to end, only the `AUTOTESTER_ALLOWED_ORIGINS` mechanism.

Cycle-1 method: same throwaway-copy procedure (copy of the worktree with the new tests, outside the tree, sha256-checked restore). Run counts for rows 1/3-new differ from cycle 0 (13 not 36) because only the named file(s) were run.

Gaps stated, not hidden: no isolated falsification for the typer `min=` bounds themselves, for
`create_env_value_if_absent` concurrency (covered by the cross-process test in test_core.py but
not mutated here), or the wall-clock brake in a real browser. These go on the checker's mutation list.

## Live browser evidence

SKIP — no screen, template or navigation path changed (backend run gate + budget). The route's
real-Chromium fixture test passed once on a throwaway copy with the RAM floor zeroed: `1 passed,
1 warning in 14.84s`. No live Pathlynks account run was performed; that is the later T-122
USER-account step and needs provisioned credentials.

## Status: checked-PASS
Verdicts (cycle 2, tip 1fd229b1): qa/verdicts/d063-grant-budget.md (coordinator A, PASS) and qa/verdicts/d063-grant-budget.b.md (coordinator B, PASS). Cycle-1 verdicts archived as *.r1-1.md. Follow-ups filed as AT-758..AT-764 (PROPOSED-ISSUEs from the dual check).
Ship gates open: qa/gates/d063-self-grant-csrf.md (answered B, built here), qa/gates/d063-cn5-vs-cn11.md (answered B widened, built here); real role-based auth stays a follow-up (D-066)
