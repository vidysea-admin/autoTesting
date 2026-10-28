# Verdict - signup-requests-f1 (checker B, Mode A, security trigger: auth)

**Verdict:** PASS
**Cycle checked:** 0
**Artifact:** worktree `D:/autoTesting/.claude/worktrees/signup-requests-f1`, branch `fix/signup-requests-f1`, commit bd7dcc59 (off bd56f8c5). Read-only toward source; nothing committed, merged or pushed.

## Commands re-run (in the worktree)
1. `uv run pytest tests/test_ui_auth_*.py tests/test_ui_origin_guard.py tests/test_ui_signup_requests.py tests/test_ui_signup_requests_f1.py tests/test_portal_requests.py tests/test_portal_access.py`
   -> `463 passed, 1 warning in 645.77s (0:10:45)`, EXIT=0 (log: `.work/adv_f1_B/pytest_required_set.txt`). Same count as the manifest.
2. `uv run ruff check src tests scripts` -> `All checks passed!`
3. `uv run autotester doctor` -> `doctor: clean` (only the pre-existing advisory decision-citation warnings, non-blocking per D-087).
4. Sizes (`wc -l`): accounts.py 294, routes_access_requests.py 165, routes_admin.py 166, tests/test_ui_signup_requests_f1.py 171; all <= 300. `user_managers` is ~10 lines, `_decide_account` < 30 (function limit 50 holds).

## Adversarial throwaway tests (`.work/adv_f1_B/test_adv_f1_B.py`, run with `PYTHONPATH=tests`, not in tests/)
Result: 46 passed, 1 failed (the deliberate probe of the disclosed known limit, finding 1). Covered:
- `parse_ids` unit: rejects `"1\n"`, `"1\r\n"`, `"\n1"`, fullwidth digits, Arabic-Indic digit, `" 1"`, `"1 "`, `"+1"`, `"-1"`, `""`, 19-digit strings, NUL, zero-width space, mathematical-digit U+1D7D9, `"1,2"`, `None`, float, bytes, list, dict -> all HTTP 400. Accepts `"0"`, `"007"`, 18 nines, int `5`. Mixed good+bad list -> 400. `re.fullmatch` is used, so no trailing-newline hole (unlike `$`).
- Approve route, group_id edge values (`0`, 18x`1`, 18x`9`, `"1\n"`, missing field, multipart file upload in place of text, JSON body, repeated field) -> only 303/400/415/422, never 500.
- Approve and decline with path ids `abc`, `1.5`, `-1`, `0`, 19 and 400 digits, `1e3`, 2**63-1, 2**63, U+0663, U+00B2 -> only 400/404/422. Unauthenticated -> 401, non-manager (developer) -> 403 for both a 30-digit and a valid id (the gate still runs).
- `/admin/users/{id}/groups` regression: multi-group set (2 groups), single, empty list (clears), bad values `x`, `²`, 30 digits, unknown group 999999 -> 400; mixed good+bad -> 400 and state unchanged. `/admin/groups/{id}` member update valid -> 303; bad `member_id` -> 400.
- F2 differential: 40+ accounts built from every 0-3 combination of {users.manage, access.approve@all/@own/@assigned, groups.manage, video.view@all}, plus a user whose two permissions come from two different groups, plus a disabled holder, plus the seeded admin. For each, logged in through the real login and checked `GET /access-requests` == 200 AND `GET /admin/users` == 200. `user_managers()` set == that set exactly (14 == 14); disabled holder excluded; split-group user included; admin included; result sorted and de-duplicated.

## Checks asked for
- No duplicate parser: `grep _ints|parse_ids` over src/tests/scripts shows `_ints` gone; `parse_ids` defined once at `src/autotester/ui/routes_admin.py:53`, called at routes_admin.py:76 (user groups), :138 (group members) and imported (not copied) at `routes_access_requests.py:33` / used at :124. All three old call sites work (tests above).
- Malformed/huge ids: 400 (form values) or 422 (path, via `UserId = Path(ge=1, le=2**63-1)` at `routes_access_requests.py:36`), 404 for an in-range unknown id; never 500 on the new routes.
- `user_managers()` (`auth/accounts.py:153`) mail set equals the people who can open `/access-requests` (policy `auth/policy.py:59` needs access.approve in some scope) AND can act (`policy.py:63` users.manage). Proven by the differential. SQL is parameter-free string composition from two constant templates; no user input reaches it.
- No regression to `/admin/users` group editing (above) and the audit of refusals (`signup.approve.refused`) is kept.

## Findings (numbered)
1. **Non-blocking, pre-existing, disclosed in the manifest as out of scope:** `src/autotester/ui/routes_admin.py:68` `admin_user_action(user_id: int, ...)` still has an unbounded path int; `POST /admin/users/<30 digits>/groups` reaches `accounts.get_user` (`auth/accounts.py:168`) and raises `OverflowError: Python int too large to convert to SQLite INTEGER` (unhandled, 500). Same class for `admin_group_view/update/delete` (`routes_admin.py:123,132,152`, `_group_or_404` at :115). Requires an authenticated `users.manage`/`groups.manage` holder, so impact is a noisy 500, not a bypass. Not a regression from this commit (identical before). Recommend a follow-up that reuses the bounded `UserId` annotation (move it next to `parse_ids`) on these four routes.
2. **Info, behaviour change:** `parse_ids` is stricter than the old `_ints` (`int(str(v))` accepted `" 3"`, `"+3"`, `"-1"`). `/admin/users/{id}/groups` with `-1` previously reached `set_user_groups` and produced the audited "unknown group" page (400 + audit row); now it is a bare `HTTPException(400, "invalid id")` and not audited (`routes_admin.py:76` sits outside the `_REFUSED` handler path). No real browser form sends these values, and the unaudited-malformed-id behaviour is the same as before for non-numeric text, so not blocking.
3. **Info:** `user_managers()` uses `LIKE 'access.approve@%'`; stored permission strings are validated by `groups.validate_permissions`, and `_`/`%` are not in the pattern, so no false match. A users.manage-only holder is no longer mailed (intended F2, documented in the docstring and pinned by `test_f2_a_users_manage_only_holder_can_still_decide_but_is_not_mailed`).
4. **Info:** the manifest notes no independent senior-engineer review was dispatched by the maker; this checker did not substitute for it (code read in full: the 3 src hunks are ~50 changed lines and match the manifest's description).
5. **Hygiene:** scratch lives only in `.work/adv_f1_B/` (gitignored); the pytest log was moved there from the worktree root. `qa/verdicts/signup-requests-f1.md` (untracked) belongs to the other checker and was not touched.

## Result
All manifest claims reproduced; contract/design rules (file <= 300, function <= 50, one parser in one place, edit in place, no `*_v2`) hold; security-sensitive id handling is bounded on every route this unit touches. Finding 1 is a disclosed pre-existing limit outside the unit's stated scope and does not block PASS.
