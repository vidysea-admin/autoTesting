# Verdict (coordinator b) - d109-claim-admin

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-19.17
Bound root: D:/autoTesting/.worktrees/d109-claim-admin · Base e3ff3f6e (git merge-base HEAD master) · Head 304ccfc9 (code 4f26d490)

## Check plan (step 0)
Diff: auth/accounts.py, auth/policy.py, ui/auth_view.py, ui/routes_auth.py + 2 test files. Signals: logic changed (affected tests + floor), UI changed (Mode D, own browser), auth changed (security read of changed lines). Persona walk: skip (one button on an existing screen; Mode D covers both user states). SERIAL: none needed; falsifications ran in 5 isolated copies, the browser run used its own port (39517) and temp root.

## Evidence (all re-run by this checker)
- `uv run pytest tests/test_ui_auth_claim_admin.py tests/test_ui_auth_accounts.py tests/test_ui_auth_policy_table.py` -> 23 passed (matches manifest).
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean.
- Test selection reviewed against the diff: each criterion has a named test (manifest Tests[C1..C5]); the policy-table row is pinned in test_ui_auth_policy_table. No missing coverage found.
- Falsification floor, one per criterion, each in its own copy of `git archive HEAD` outside the bound root (baseline 8 passed):

| C | edit (copy only) | result |
|---|---|---|
| C1 | `waiting_page`: force `can_claim = False` | red: c1 + 2 c4 tests (3 failed) |
| C2 | `_claim_refusal`: `if False and _has_admin_member(conn)` | red: c2 two-claims test (`won/won`), c3, c5 (3 failed) |
| C3 | drop `or row["disabled"]` | red: c3 disabled test (1 failed) |
| C4 | drop the `wanted` email check | red: c4 first-admin-email test (1 failed) |
| C5 | rename `admin.claim_refused` action | red: c3 + c5 (2 failed) |

## Security read of the changed lines
- CSRF: `("POST","/auth/claim-admin"): SESSION` (policy.py:71); the D-066 Origin guard runs before the auth middleware (auth_middleware.py docstring :4); test c1b shows a cross-origin POST gets 403 and no membership change. Session cookie is SameSite=lax (observed Set-Cookie).
- Race: `claim_admin` (accounts.py:94-105) runs refusal check, membership insert and `ensure_an_admin_remains` inside one `db.transaction()`, which is `BEGIN IMMEDIATE` (db.py:159-171), so concurrent claims serialize on the store lock; the check is re-done inside the write lock, not trusted from the button read. Test c2 (Barrier(2)) gives exactly one winner; falsification C2 reproduces the 2-winner failure when the re-check is removed.
- Refusal once an admin exists: `_has_admin_member` (:64). Observed live: second account POST -> 403 "an administrator already exists", no membership change.
- `AUTOTESTER_FIRST_ADMIN_EMAIL`: `first_admin_email()` is trimmed and lowercased (config.py:39-40), compared to the stored (normalized) email; test c4 sets `" Boss@Team.TEST "`.
- Disabled / unauthenticated: `_claim_refusal` refuses a disabled or missing row; the route returns 401 when no principal; anonymous POST is refused by the gate (test c3b: 401).
- Audit: both outcomes call `audit.record_action` with actor/target email only; live audit log held `admin.claim` and `admin.claim_refused` plus the middleware request rows; 0 occurrences of the password in the log. Refusal text shown to the user is a fixed string (no data from other accounts).
- No new file over 300 lines (accounts.py 246). `LastAdmin` is caught and audited as a refusal.

## Mode D (own browser, Playwright MCP, loopback, temp AUTOTESTER_ROOT; real .auth untouched)
Server: uvicorn from the bound worktree, `AUTOTESTER_HOSTED=1`, `AUTOTESTER_COOKIE_SECURE=0`, FIRST_ADMIN_EMAIL unset; it was stopped after the run (launcher + listener PIDs I started).
1. Sign up alice in the form -> /auth/waiting with a "Claim admin" button (POST form to /auth/claim-admin).
2. Click it -> 303 to `/`, Projects page with Users / Groups nav; `/admin/users` loads (200).
3. Sign up bob -> waiting page with no button; direct same-origin POST -> 403 "an administrator already exists"; `/admin/users` -> 403 waiting page.
Console errors: 0 in alice's flow; 2 in bob's (the expected 403s). Screenshots and report.json in the evidence dir.

## Result
VERDICT: PASS
SCOREBOARD: 5/5 criteria met (C1-C5), AU6/AU9/AU17 invariants touched by the diff hold
TIER: L (auth: first-admin claim route and membership write, accounts.py:94)
FAILURES: none
CAPABILITY-COVERAGE: 5/5 rows reproduced
LIVE-BROWSER: qa/evidence/browser-d109-claim-admin-2026-10-26-checker-b/
ISSUES-WRITTEN: none (dual coordinator: findings below are proposals only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The claim is one BEGIN IMMEDIATE transaction that re-checks emptiness before inserting, so two claims give one admin; once an admin exists the button is gone and the route returns 403; the email restriction, disabled and anonymous refusals and the audit rows all hold on tests, five isolated falsifications and a live browser run. The accepted public-server race of D-109 (whoever signs in first on an unclaimed server can claim) is stated in D-109 and is not a defect of the code.

PROPOSED-ISSUE: {"sev":"low","area":"contract","text":"qa/contracts/auth.md AU7 still describes hosted+unset as 'nobody is auto-promoted ... CLI is the only bootstrap path' (lines 116-119); D-109 says the checker amends AU7 after the unit closes. Amend once both coordinators PASS; also HO11 and docs/spec.md:140 wording already flagged in the contract history."}
PROPOSED-ISSUE: {"sev":"low","area":"audit","text":"A claim POST that the gate refuses before the handler (anonymous 401, or a cross-origin 403 from the Origin guard) writes only the middleware request row, not an admin.claim_refused action; C5 as written covers attempts that reach the handler. Optional hardening, not a criterion failure."}
PROPOSED-ISSUE: {"sev":"low","area":"ops","text":"Mode D note: after a server restart a stale at_session cookie from a previous process made the first browser logins appear to fail (redirected back to /auth/login); clearing cookies fixed it. Looks like a pre-existing UX edge, not part of D-109."}

Metrics: start=2026-10-26T05:03Z end=2026-10-26T05:27Z wall_min=24 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=1440 mutants=0 defects_unit=0 defects_6c=0
slow: n/a (L tier; wall target 45 min)
