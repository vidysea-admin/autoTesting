# Verdict - d109-claim-admin (coordinator A, dual check)

**Checker:** Mode A, fresh context, bound to D:/autoTesting/.worktrees/d109-claim-admin. **Cycle checked: 0** (manifest Fix cycle 0).
**Policy-Version:** proportional-verification/2026-10-19.17. **Base:** e3ff3f6e. **Checked:** code 4f26d490, head 304ccfc9 (manifest-only difference). Budget respected (target 15-20 min).

## Check plan
Auth diff (accounts.py, policy.py, auth_view.py, routes_auth.py) + UI surface (waiting page) -> scoped tests, one falsification per criterion in copies, security read of changed lines, Mode D in my own browser. No persona walk (internal-tool, one button, per manifest and spec).

## Evidence I produced
- `uv run pytest tests/test_ui_auth_claim_admin.py tests/test_ui_auth_accounts.py tests/test_ui_auth_policy_table.py` -> 23 passed. Affected set (test_ui_auth_*, account_generation, tracker_auth, role_accounts_routes, ta02, ta14; 19 files incl. the route-enumerating tests) -> 334 passed.
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean.
- Falsification, one per criterion, each in its own copy of `git archive 4f26d490` (baseline 8 passed), none in the bound tree:
  C1 remove the `{claim}` form from waiting_page -> 3 failed. C2 move the emptiness check out of the write transaction (read, sleep 0.3 s, insert) -> the two-simultaneous-claims test fails (1 failed). C3 refusal status 403 -> 200 -> 3 failed. C4 invert the `!= wanted` email test -> 1 failed. C5 rename the success audit action -> 1 failed.
- Security read (accounts.py:64-105, routes_auth.py:113-126, policy.py:71, auth_view.py:83-100): `claim_admin` runs inside `db.transaction()` = `BEGIN IMMEDIATE` (db.py:159-171), refusal re-checked and membership inserted under that lock, then `ensure_an_admin_remains`; refusal returns disabled/missing user, deleted admin group, admin already has a member, and non-matching normalized first-admin email; `who is None` gives 401; the POST row is SESSION so the shared Origin/CSRF middleware applies (cross-origin POST -> 403 test passes); notice text is `escape`d; audit rows carry actor/target/action only, no password. No defect found.

## Criteria
- C1 MET: waiting page shows Claim admin form (POST /auth/claim-admin) while no member; live in browser; cross-site POST refused.
- C2 MET: single transaction, 303 to /; race test passes and goes red when the check leaves the transaction.
- C3 MET: with an admin present no button, POST 403 and no membership change (live: second account; DB shows only first user in Admin/CEO); anonymous POST 401 (curl); disabled account refused (test).
- C4 MET: first-admin-email restriction and unset behaviour pass (tests, falsification).
- C5 MET: live audit shows `admin.claim` for the winner and `admin.claim_refused` for the second account, no password; policy row present (policy-table test).

VERDICT: PASS
SCOREBOARD: 5/5 criteria met, 0/0 invariants judged outside the criteria (AU6/AU7/AU9/AU17 paths covered by the 334-test affected set)
TIER: L (auth: src/autotester/auth/accounts.py:94 claim route and membership write)
FAILURES: none
PROPOSED-ISSUE: {"sev":"low","title":"Anonymous POST /auth/claim-admin is refused 401 by the gate but gets no admin.claim_refused audit row (only the request line)","area":"auth","note":"C5 says every attempt; anonymous attempts never reach the handler. Wording-level, not a FAIL."}
PROPOSED-ISSUE: {"sev":"low","title":"Public-facing server with AUTOTESTER_FIRST_ADMIN_EMAIL unset lets whoever signs up and claims first become admin","area":"auth","note":"This is D-109's stated rule (unset = any signed-in account); set the variable on any reachable server to narrow it. Awareness only."}
CAPABILITY-COVERAGE: 5/5 rows reproduced (own mutants, own copies)
LIVE-BROWSER: qa/evidence/browser-d109-claim-admin-2026-10-26-checker/report.json
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: All five D-109 criteria are evidenced by my own runs: scoped tests green, a falsification red for each criterion, and a real browser walk (sign up, Claim admin, land in the app; second account has no button and a forced POST gets 403). The claim is serialised by BEGIN IMMEDIATE and the security read of the changed lines found no defect. Console: 0 errors on page loads; the 2 logged errors are my own probe fetches returning the expected 403.
Metrics: start=2026-10-26 end=2026-10-26 wall_min=16 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=960 mutants=0 defects_unit=0 defects_6c=0
