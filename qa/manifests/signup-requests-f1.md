# Manifest - signup-requests-f1

**Status:** ready-for-check
**Fix cycle:** 0
**Issues addressed:** follow-up F1 and F2 from the signup-requests senior review / checker (manifest `qa/manifests/signup-requests.md`, checked-PASS, non-blocking findings).
**Branch:** `fix/signup-requests-f1` (worktree `D:/autoTesting/.claude/worktrees/signup-requests-f1`, off bd56f8c5). Not merged, not pushed.

## What changed
- F1 `ui/routes_admin.py`: the id parser `_ints` is now the one public, bounded `parse_ids` (ASCII digits only, 1-18 of them, so always inside SQLite int64; `\u00b2`, `\u0663`, signs, blanks, `1_0`, `1.5`, `0x1`, `1e3`, > int64 all give 400). Its two existing call sites in the same file use it. Before: `\u00b2` passed `str.isdigit()` then `int()` raised (500) in the new route; a 30-digit id reached SQLite and raised OverflowError (500).
- F1 `ui/routes_access_requests.py`: `group_id` is parsed by `parse_ids` (imported, not copied); a bad value is the same "choose a group" refusal as before (400 page, audited as `signup.approve.refused`). The path `user_id` on approve/decline is `Annotated[int, Path(ge=1, le=2**63-1)]` (out of range is 422, never 500).
- F2 `auth/accounts.py::user_managers()`: mails only enabled accounts holding `users.manage` AND `access.approve` in some scope (what `GET /access-requests` needs). A users.manage-only holder is not mailed a link that 403s; they use `/admin/users`, where the Waiting pill is shown (documented in the docstring and pinned by a test).
- `tests/test_ui_signup_requests.py` SR9: the "People" group now also holds `access.approve@all` (it must, to be mailed). New `tests/test_ui_signup_requests_f1.py` (25 cases): malformed group ids (12), audit of the refusal, malformed path ids (5), same parser on `/admin/users/{id}/groups`, F2 mail set (users.manage-only excluded; both, and users.manage + access.approve@own included; approve-only excluded), every mailed recipient can open `/access-requests`, threaded races (two admins approving into different groups: exactly one 303 and one 400, one group; approve vs decline: one 303 + one 400, approved xor declined), a declined account's existing session stops working (`/auth/waiting` 200 -> 302, `/auth/check` -> 401).

## Red then green
`uv run pytest tests/test_ui_signup_requests_f1.py` BEFORE the src change:
```
FAILED ...malformed_group_id...[\xb2]  [\u0663]  [999999999999999999999999999999]  [9223372036854775808]  [18446744073709551616]
FAILED ...test_f1_the_refusal_is_audited_like_any_other
FAILED ...test_f1_a_malformed_user_id_in_the_path_is_never_a_500[99..9 (30 digits)]  [9223372036854775808]
FAILED ...test_f1_the_admin_users_page_shares_the_same_bounded_parser
FAILED ...test_f2_a_users_manage_only_holder_is_not_mailed
FAILED ...test_a_declined_account_s_existing_session_stops_working   (test bug: used /auth/check, which 403s a waiting account; corrected before the src change)
11 failed, 14 passed
```
The two race tests and the decline-session test (once corrected) passed before the change: they pin behaviour the first unit already had (transactional re-check in `approve_waiting`/`decline_waiting`; `decline_waiting` deletes sessions), so they are regression guards, not red-then-green.

AFTER, `uv run pytest tests/test_ui_signup_requests_f1.py tests/test_ui_signup_requests.py`:
```
39 passed, 1 warning in 19.98s
```

## Verify (run in the worktree)
`uv run pytest tests/test_ui_auth_*.py tests/test_ui_origin_guard.py tests/test_ui_signup_requests.py tests/test_ui_signup_requests_f1.py tests/test_portal_requests.py tests/test_portal_access.py`:
```
463 passed, 1 warning in 191.05s (0:03:11)
```
`uv run ruff check src tests scripts`:
```
All checks passed!
```
`uv run autotester doctor`:
```
doctor: clean
```
(advisory decision-citation warnings pre-exist, non-blocking per D-087.) File sizes: accounts.py 294, routes_access_requests.py 164, routes_admin.py 168 (all <= 300).

## Known limits (for the checker)
- `/admin/users/{user_id}/{action}` still types `user_id: int` unbounded in the path (a 30-digit id there reaches SQLite): out of this unit's scope, not touched. Its `group_id` form values now go through the bounded parser.
- The `user_managers()` LIKE `access.approve@%` matches any scope; the catalogue only admits valid scopes (`validate_permissions`), so no invalid string can be stored.
- Independent senior-engineer review was not dispatched by the maker in this seat; left for `/checker`.
