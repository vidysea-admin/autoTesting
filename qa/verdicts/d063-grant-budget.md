# Verdict A (dual-check coordinator A) — d063-grant-budget, cycle 2 (repair)

Date: 2026-10-07. Bound root: D:/autoTesting, worktree .worktrees/d063-grant-budget, branch wave/d063-grant-budget, tip 1fd229b1. Last checker-reviewed state 5201859a (ancestor of HEAD). Policy-Version: proportional-verification/2026-10-06.6.
Cycle checked: 2
Verdict path: qa/verdicts/d063-grant-budget.md (coordinator A). Checkpoint: qa/checkpoints/d063-grant-budget.md. Resume: none (first dispatch of cycle 2).

## Check plan (step 0)
Diff 5201859a..HEAD, product code: core/consent.py, stages/explore_consent.py, ui/helpers.py, ui/app.py, ui/routes_runs.py. Tests: test_consent.py (protected edit), new test_credential_run_approval.py (22) and test_ui_origin_guard.py (43). Everything else is master-merge docs/qa/goal files (.goal and test_goal_contract_registration.py come from master 8e1b1dc5/fe6eb98a, not this unit).
Plan: (1) one full suite; (2) ruff + doctor; (3) diff scope 4c; (4) protected-test judgement; (5) falsification for criteria 8-12 plus a changed-function row for 1, in copies; (6) sub-checker fan-out in one message: a mutation sweep (15 mutants) and a security/attack probe (Origin guard + approval derivation). Backend only, no screen changed: no Mode D, no persona walk (the manifest hint is skip and the plan agrees). No external data collected: 5c not applicable.
TIER: L (security/auth: ui/helpers.py origin_guard_middleware, stages/explore_consent.py::covering_approval auto-minting signed approvals; D-066/D-068). Dual check required, not raised.

## Evidence re-run by this coordinator
- `uv run pytest` (full, no -q/-x, bound worktree, ONE run): `1 failed, 2388 passed, 6 skipped, 14 xfailed in 2259.15s`. The one failure is tests/test_goal_done_checks.py::test_every_pending_task_actually_has_a_done_check ("pending tasks with no done_check: T-197..T-201"). Attribution: those rows come from master fe6eb98a (D-067 recorded them without a done_check; `git show fe6eb98a:.goal/goal.json` shows all five pending with no done_check) and `git diff fe6eb98a HEAD -- .goal` is empty, so this unit changed nothing the test reads. A master-state defect, not a defect of the changed files (cycle 0 had the same shape: one failure already red at master). PROPOSED-ISSUE P1.
- `uv run ruff check src tests scripts`: All checks passed!
- `uv run autotester doctor`: doctor: clean. ui/app.py = 300 lines (limit 300, held).
- 4c diff scope: product hunks are exactly the manifest's "What changed" list for fix cycle 2. The only removals are `prepare_account_live_case` (renamed in place to `prepare_account_grant(kind=...)`), the `case_ids` parameter of `validate_account_scope` (CN5/CN11 amended by D-068), and the inline mint in routes_runs moved into `covering_approval`. No unlisted file, no removed test (test_consent.py parametrization modes unchanged).
- Protected test change in tests/test_consent.py, `scope["cases"] == ["case-one"]` -> `"cases" not in scope`: JUSTIFIED, not a weakening. The old assertion pinned the case-set key that amended CN5/CN11 (commit 2aed300e, gate d063-cn5-vs-cn11 answered B, D-068) removes from `scope`. The same line still asserts `scope["keys"] == ["USER"]`; no parametrized refusal mode was dropped; `[scope]`, `[actions]`, `[valid]` still fire (see falsification); and test_credential_run_approval.py::test_declared_provisioned_credentials_mint_a_signed_row_with_no_human_step asserts the same absence plus the keys for all three kinds.

## Falsification (copies of HEAD under scratchpad A-fals/ and A-coord/, one single-line edit per copy, green-before on an untouched copy, red-after, untouched copy green)
Own rows (this coordinator):
- C1 scope: consent.py:59 `_host_matches(...) for d in ref.domains` -> `True for d in ref.domains`: test_consent.py::test_account_grant_is_new_exact_and_bounded[scope] FAILED.
- C9 mint and persist: explore_consent.py:92 `return store.add_approval(approval)` -> `return approval`: 3 failed (test_declared_provisioned_credentials_mint_a_signed_row_with_no_human_step[live_case|crawl|read]).
- C10 any-case-set reuse: explore_consent.py:84 reuse return -> `raise ApprovalRequired('x')`: test_a_row_covers_any_case_set_of_the_same_triple FAILED.
- C12 forged row: consent.py:165 `if not signed_and_verified:` -> `if False:`: test_a_forged_account_row_is_never_honoured FAILED. Expired row: consent.py:172 `if approval.is_expired(now):` -> `if False:`: test_an_expired_account_row_is_replaced_by_a_new_one FAILED.
Sub-checker mutation sweep (15 mutants in copies; findings only): KILLED 6: M1 helpers `_origin_allowed` always True (34 failed, first test_every_state_changing_route_refuses_a_cross_site_origin), M5 Sec-Fetch-Site check always passes (test_other_cross_site_shapes_are_refused[headers6]), M6 middleware `scope["type"] == "http"` made never true (35 failed), M7 ADVERSARIAL added to ACCOUNT_KINDS (test_adversarial_never_gets_an_automatic_grant), M8 `production=False` -> True (5 failed, [valid] first), M12 human-row fallback removed (4 failed). SURVIVED 9, listed below.
Floor: criteria 8 (M1, M5, M6), 9 (C9), 10 (C10), 11 (M7), 12 (forged, expired, M12, M8) and 1 each have a green/red/restored row. Criteria 3-7 keep their cycle-0/1 rows by evidence identity: the files those rows mutate are unchanged since cycle 1 except consent.py and routes_runs.py, whose defenders are green in the full suite and re-covered by rows C1 and M8.
CAPABILITY-COVERAGE: rows for 8, 9, 10, 11, 12 and 1 reproduced this cycle; 3-7 reused by identity.

Survivors judged, all non-blocking (PROPOSED-ISSUE lines below):
- M13 routes_runs.py:88 cross-project case guard: carried over unchanged from cycle 1, no test.
- M14 the `ensure_approval_key` call in `_credential_approval`: no test through covering_approval. I ran the real behaviour in a fresh root with no AUTOTESTER_APPROVAL_KEY: the key is created, the row is signed and verified, and `.env` gains only the key. The code is correct; only the pin is missing.
- M15 `_default_account_keys` login-case narrowing: unpinned.
- M9 human-first sort: unpinned.
- M2 DELETE not exercised through the middleware (the app has no DELETE route today).
- M3/M4 wildcard literal and userinfo/path clauses: hardening; browser Origins never carry them.
- M10/M11 redundant pre-validation (`prepare_account_grant` re-validates).
None is a wrong behaviour of the shipped code, so none is a FAIL (evidence-to-block not met).

## Security review (sub-checker attack probes via TestClient and covering_approval; I read the cited lines)
Correctly refused: Origin null, trailing-dot host, localhost.evil.com, evil#@localhost, localhost:80@evil, 127.0.0.1.evil.com, userinfo, path, IPv6-mapped forms, Referer-only attacker hosts and tricks, Sec-Fetch-Site cross-site/same-site, PUT/PATCH/DELETE, wildcard in AUTOTESTER_ALLOWED_ORIGINS, method-override headers (405). No mutating GET handler (28 scanned); no websocket or mount. Approval: ADVERSARIAL refused with 0 rows and no key; out-of-domain credential, lookalike host, userinfo base_url, forged and expired rows, lost signing key and nonpositive/inf bounds all refused with no row, key or crawl dir; no credential value or signing key in approvals.jsonl, 403 bodies or logs after a mint.
Findings, none FAIL:
- D1 GET /projects/{slug}/env embeds saved credential values and there is no Host allow-list, so a DNS-rebinding page can read them. Pre-existing GET route outside this diff and outside D-066's state-changing scope.
- D2 duplicate Origin headers: the last wins (helpers.py `_OriginGuard.__call__` builds a dict); only reachable behind a header-merging proxy.
- D3 a run that references no keys, on a project with no login case, is blocked by an unused provisioned out-of-scope key (`_default_account_keys` falls back to every provisioned key). It fails closed and was a 403 before this cycle too.
- D4 a human row with max_probes=0 is skipped for a credentialed project (consistent with D-068).
- D5 row growth across target edits and expiries.
- D6 `AUTOTESTER_ALLOWED_ORIGINS=null` allows Origin null (operator misconfiguration).

## Criteria scoreboard
C1 grant identity/scope: met. C2 selected keys only: met for runs that reference keys (D3 edge noted). C3 positive finite brakes: met (cycle-1 CLI tests green in the full suite). C4 key preparation: met (ensure_approval_key defenders green, real-root bootstrap run). C5-C7: met (defenders green, files unchanged). C8 D-066: met (43 tests, 3 killed mutants). C9 D-068 auto-mint at seam, CLI explore, UI explore and UI run: met. C10: met. C11: met. C12: met. Invariants (CN10 a bound never means unlimited; C5 no raw secret) hold.
SCOREBOARD: 12/12 criteria met, invariants hold; full suite 2388 passed with 1 failure attributed to master's goal.json (P1), not to this diff.

PROPOSED-ISSUE: {"sev":"medium","type":"master-state","title":"tests/test_goal_done_checks.py::test_every_pending_task_actually_has_a_done_check is red on master: T-197..T-201 have no done_check (recorded by fe6eb98a, D-067)","fix":"give each of T-197..T-201 a done_check cmd object in .goal/goal.json on master","evidence":"git show fe6eb98a:.goal/goal.json; uv run pytest tests/test_goal_done_checks.py"}
PROPOSED-ISSUE: {"sev":"medium","type":"security-adjacent","title":"GET /projects/{slug}/env ships saved credential values and no Host allow-list exists: a DNS-rebinding page can read them (D-066 guards only state-changing routes)","fix":"Host/TrustedHost allow-list (loopback plus AUTOTESTER_ALLOWED_ORIGINS hosts), or stop rendering raw values","evidence":"sub-checker probe: TestClient base_url=http://evil.example:8000 GET /projects/demo/env -> 200 with the raw value; ui/routes_credentials.py"}
PROPOSED-ISSUE: {"sev":"low","type":"test-gap","title":"Mutation survivors with no test: routes_runs.py:88 cross-project case guard (M13), explore_consent.py ensure_approval_key call (M14), _default_account_keys login-case narrowing (M15), human-first sort (M9), DELETE through the origin middleware (M2)","fix":"one test each; for M14: covering_approval on a root with no AUTOTESTER_APPROVAL_KEY creates the key and mints a verified row"}
PROPOSED-ISSUE: {"sev":"low","type":"hardening","title":"_OriginGuard builds a header dict so the last duplicate Origin wins (helpers.py:241-242)","fix":"refuse a request carrying more than one Origin header"}
PROPOSED-ISSUE: {"sev":"low","type":"consistency","title":"A run that references no credential keys and has no login case is blocked by an unused provisioned out-of-scope key (explore_consent.py _default_account_keys), contradicting routes_runs._require_declared_values 'unused roles never gate a run'","fix":"for a run referencing no keys, skip the key check or use only the keys the run would use"}
PROPOSED-ISSUE: {"sev":"low","type":"hygiene","title":"Expired and superseded account rows accumulate in approvals.jsonl (one per target edit and per expiry)","fix":"none required; consider compaction"}

VERDICT: PASS
TIER: L (security/auth; helpers.py origin_guard_middleware, explore_consent.py::covering_approval)
FAILURES: none
CAPABILITY-COVERAGE: rows for criteria 8, 9, 10, 11, 12, 1 reproduced this cycle; 3-7 reused by identity
LIVE-BROWSER: not-applicable (backend only: ui/helpers.py, ui/app.py middleware; no screen or template changed)
ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Fix cycle 2 adds the D-066 Origin/CSRF middleware and the D-068 credential-derived approval. Every acceptance criterion is evidenced by tests I ran and by green/red/restored falsifications in copies, lint and doctor are clean, and the protected test edit follows the amended contract. The single full-suite failure is a master-state goal.json defect (T-197..T-201 lack done_check) that this branch neither touches nor can fix; the surviving mutants are test gaps, not wrong behaviour.
Metrics: start=2026-10-07T08:08:26Z end=2026-10-07T08:49:29Z wall_min=41 agent_min=85 blocked_min=0 suite_runs=1 repeat_runs=0 mutations=20 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
