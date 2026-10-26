# Manifest - d109-claim-admin (D-109 claim admin)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/auth.md (AU6, AU7, AU9, AU17; amended by D-109)
**Goal task:** none
**Authority:** D-109 (Approved-by: Umesh, chat 2026-10-26 "1 claim")
**Date:** 2026-10-26
**Dual check:** required
dual-trigger: auth src/autotester/auth/accounts.py:94
**Persona walk:** skip (internal-tool: one button on the existing waiting page, no new screen or navigation; checker Mode D validates live)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Executor rationale:** single-owner auth unit, four small source files; no external executor worthy
**Base SHA:** e3ff3f6e (worktree .worktrees/d109-claim-admin, branch wave/d109-claim-admin)
**Code SHA:** 4f26d490

## Criteria (gate answer D-109, from the brief)
- C1 - GET /auth/waiting for a signed-in account shows "Claim admin" (POST form to /auth/claim-admin; same Origin/CSRF middleware as every auth POST) while Admin/CEO has no member.
- C2 - The claim is ONE `db.transaction()`: re-check no member, insert membership; two concurrent claims yield exactly one admin; success redirects to `/`.
- C3 - Once Admin/CEO has a member: no button, POST refuses 403, no membership change; unauthenticated POST refused; a disabled account cannot claim.
- C4 - With AUTOTESTER_FIRST_ADMIN_EMAIL set only that (normalized) address may claim; unset: any signed-in account while no admin exists (hosted or local).
- C5 - Every claim attempt is written via `audit.record_action` (`admin.claim` / `admin.claim_refused`), no password; one SESSION row in `auth/policy.py`.

## What changed
- `src/autotester/auth/accounts.py:50-110` - `_becomes_first_admin` now reuses the new `_has_admin_member` (:64, same behaviour); new `_claim_refusal` (:71), `may_claim_admin` (:86, a read for the button) and `claim_admin` (:94, ONE `db.transaction()`: refusal check, membership insert, `ensure_an_admin_remains`). File is 246 lines.
- `src/autotester/ui/routes_auth.py:113` - new `POST /auth/claim-admin` (`auth_claim_admin`): calls `claim_admin`, audits `admin.claim` / `admin.claim_refused`, 303 to `/` on success, 403 waiting page with the reason on refusal.
- `src/autotester/ui/auth_view.py:83` - `waiting_page(email, notice="", can_claim=None)`; None looks up `may_claim_admin(email)` so both `/auth/waiting` and the middleware's 403 waiting page show the button without touching `auth_middleware.py`.
- `src/autotester/auth/policy.py:71` - `("POST", "/auth/claim-admin"): SESSION`.
- Tests: new `tests/test_ui_auth_claim_admin.py` (8 tests; a new file because adding them to `tests/test_ui_auth_accounts.py` took it to 320 lines, over the 300 cap), row added to `EXPECTED` in `tests/test_ui_auth_policy_table.py`.
- Not touched: `qa/contracts/`, `docs/DECISIONS.md`, `ui/auth_middleware.py`, `schema/`.
- Docstrings in `ui/` avoid the literal group name because `test_au12_no_route_compares_group_names` greps `src/autotester/ui` for it (caught by the wider run and fixed).

## Verification scope
Policy-Version: proportional-verification/2026-10-19.17
Tier: L - auth (security/auth trigger)
Round: 6 files, 5 criteria, est 40 min - four source files, two test files, TDD red then green
Owners: auth
Base / checked state: e3ff3f6e + 4f26d490 (clean tree for src and tests)
Gate answers: D-109 quoted in the brief; Changes-authorized: src/autotester/auth/, ui/routes_auth.py, ui/auth_view.py, auth/policy.py and their tests.
Affected tests / full-suite trigger: builder ran no full suite. Ran the touched files plus every git grep hit on waiting_page, auth/waiting, ROUTE_POLICY, accounts.signup in the auth tests (test_ui_auth_*, test_account_generation, acceptance ta02 and ta14, test_tracker_auth, test_role_accounts_routes): 151 passed, 1 failed (test_au12 docstring grep, then fixed and green). Trigger for the checker: the policy-table and route-enumerating tests (ta02, ta14).
Tests[C1]: tests/test_ui_auth_claim_admin.py::test_d109_c1_hosted_first_user_sees_claim_button_and_claims_admin, ::test_d109_c1_cross_site_claim_is_refused_like_every_auth_post - hosted server with no shell, first user sees the form and claims; a cross-origin POST is refused by the shared Origin guard
Tests[C2]: tests/test_ui_auth_claim_admin.py::test_d109_c2_two_simultaneous_claims_make_exactly_one_admin - Barrier(2) threads, exactly one wins
Tests[C3]: tests/test_ui_auth_claim_admin.py::test_d109_c3_once_an_admin_exists_there_is_no_button_and_no_claim, ::test_d109_c3_anonymous_and_disabled_accounts_cannot_claim
Tests[C4]: tests/test_ui_auth_claim_admin.py::test_d109_c4_with_first_admin_email_only_that_address_may_claim, ::test_d109_c4_local_server_unset_email_any_signed_in_account_may_claim
Tests[C5]: tests/test_ui_auth_claim_admin.py::test_d109_c5_every_claim_attempt_is_audited_without_secrets; tests/test_ui_auth_policy_table.py::test_au14_every_policy_row_requires_exactly_its_pinned_key (the new SESSION row)
Pre-check[C1]: 4f26d490 uv run pytest tests/test_ui_auth_claim_admin.py -k _c1_ -> 2 passed t=5 blobs=tests/test_ui_auth_claim_admin.py:98027a7
Pre-check[C2]: 4f26d490 uv run pytest tests/test_ui_auth_claim_admin.py -k _c2_ -> 1 passed t=6 blobs=tests/test_ui_auth_claim_admin.py:98027a7
Pre-check[C3]: 4f26d490 uv run pytest tests/test_ui_auth_claim_admin.py -k _c3_ -> 2 passed t=7 blobs=tests/test_ui_auth_claim_admin.py:98027a7
Pre-check[C4]: 4f26d490 uv run pytest tests/test_ui_auth_claim_admin.py -k _c4_ -> 2 passed t=8 blobs=tests/test_ui_auth_claim_admin.py:98027a7
Pre-check[C5]: 4f26d490 uv run pytest tests/test_ui_auth_claim_admin.py tests/test_ui_auth_policy_table.py tests/test_ui_auth_accounts.py -> 23 passed t=19 blobs=tests/test_ui_auth_claim_admin.py:98027a7,tests/test_ui_auth_policy_table.py:e60e5ae,tests/test_ui_auth_accounts.py:0bd5af0
Metrics: start=2026-10-26 end=2026-10-26 wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=0 mutants=5 defects_unit=1 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_ui_auth_claim_admin.py tests/test_ui_auth_accounts.py tests/test_ui_auth_policy_table.py` -> expected: 23 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- Red first (TDD), before the implementation: `8 failed, 15 passed` (`AttributeError: module 'autotester.auth.accounts' has no attribute 'claim_admin'`). The C1 cross-site test already passed because the Origin guard refuses it before routing, so it pins existing protection rather than new code.
- After: claim file `8 passed`; accounts + policy table `15 passed`; the 11 auth-related files `151 passed, 1 failed` (test_au12 docstring grep), fixed, then `tests/test_ui_auth_groups.py` + claim file `41 passed`.
- `uv run ruff check src tests scripts`: `All checks passed!`; `uv run autotester doctor`: `doctor: clean`.

## Capability coverage (each new claim -> its isolating falsification)
Falsifications ran in a throwaway copy (`git archive HEAD src tests pyproject.toml scripts`), never the worktree; src was restored from HEAD after each. Baseline in the copy: `8 passed`.

| Criterion | capability | the check that covers it | the falsifying edit | observed (pasted runner output) |
|---|---|---|---|---|
| C1 | Waiting page shows the Claim admin form | test_d109_c1_hosted_first_user_sees_claim_button_and_claims_admin (auth_view.py:83) | `waiting_page`: force `can_claim = False` | `tests\test_ui_auth_claim_admin.py:43: AssertionError`; `FAILED tests/test_ui_auth_claim_admin.py::test_d109_c1_hosted_first_user_sees_claim_button_and_claims_admin`; `3 failed, 5 passed` |
| C2 | One transaction, re-checked emptiness, exactly one winner | test_d109_c2_two_simultaneous_claims_make_exactly_one_admin (accounts.py:94) | drop `if _has_admin_member(conn):` refusal | `AssertionError: assert ['won', 'won'] == ['refused', 'won']`; `FAILED tests/test_ui_auth_claim_admin.py::test_d109_c2_two_simultaneous_claims_make_exactly_one_admin` |
| C3 | Disabled account cannot claim; admin-exists refusal | test_d109_c3_anonymous_and_disabled_accounts_cannot_claim | drop `or row["disabled"]` in `_claim_refusal` | `FAILED tests/test_ui_auth_claim_admin.py::test_d109_c3_anonymous_and_disabled_accounts_cannot_claim` (`pytest.raises(AccountError)` not raised); `1 failed, 7 passed`. The C2 edit also reddens `assert 303 == 403` in the admin-exists tests |
| C4 | Only AUTOTESTER_FIRST_ADMIN_EMAIL may claim | test_d109_c4_with_first_admin_email_only_that_address_may_claim | drop `if wanted and row["email"] != wanted:` | `AssertionError: assert 'Claim admin' not in '<!doctype h...'`; `FAILED tests/test_ui_auth_claim_admin.py::test_d109_c4_with_first_admin_email_only_that_address_may_claim`; `1 failed, 7 passed` |
| C5 | Refusal is audited | test_d109_c5_every_claim_attempt_is_audited_without_secrets | rename the `admin.claim_refused` action in routes_auth.py | `AssertionError: assert 'admin.claim_refused' in ['login', 'x']`; `FAILED ...::test_d109_c5_every_claim_attempt_is_audited_without_secrets`; `2 failed, 6 passed` |

## Live browser evidence
SKIP — builder smoke only; checker Mode D validates

## Status: checked-PASS (dual: qa/verdicts/d109-claim-admin.md PASS + qa/verdicts/d109-claim-admin.b.md PASS, cycle 0)
