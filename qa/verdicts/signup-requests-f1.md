# Verdict - signup-requests-f1 (Mode A, coordinator A, security trigger: auth)

**Verdict:** PASS
**Cycle checked:** 0
**Unit:** `fix/signup-requests-f1` @ bd7dcc59 (off bd56f8c5), worktree `.claude/worktrees/signup-requests-f1`
**Judged against:** `qa/contracts/auth.md`, `qa/contracts/core-invariants.md`, CLAUDE.md design rules.
Read-only toward the artifact; nothing committed, merged or pushed.

## Commands re-run by the checker (in the worktree)

1. `uv run pytest tests/test_ui_auth_*.py tests/test_ui_origin_guard.py tests/test_ui_signup_requests.py tests/test_ui_signup_requests_f1.py tests/test_portal_requests.py tests/test_portal_access.py`
   -> `463 passed, 1 warning in 640.62s (0:10:40)` (matches the maker's 463; log `.work/check-f1-A-pytest.txt`; slower wall time only because another checker ran concurrently)
2. `uv run ruff check src tests scripts` -> `All checks passed!`
3. `uv run autotester doctor` -> `doctor: clean` (only the pre-existing advisory decision-citation warnings, D-087, non-blocking)

## Checks requested

- **No duplicate parser; old `_ints` callers intact.** `grep _ints|parse_ids` over src/tests/scripts: `_ints` has zero remaining references. `parse_ids` is defined once (`src/autotester/ui/routes_admin.py:53`) and used at `routes_admin.py:76` (user groups), `routes_admin.py:138` (group members) and imported, not copied, at `routes_access_requests.py:33,124`. Both former call sites keep working (auth suites pass; probe: `POST /admin/users/{id}/groups` with no boxes -> 303, valid ids -> 303).
- **Malformed / huge ids -> 400/422, never 500 on the unit's routes.** `routes_admin.py:50` `[0-9]{1,18}` with `fullmatch` (no trailing-newline slip, ASCII only, always < int64). Checker probe: `group_id=" 1"` -> 400; valid group -> 303. Path ids: `Annotated[int, Path(ge=1, le=2**63-1)]` (`routes_access_requests.py:37`) -> 422 outside range. Refusal still audited as `signup.approve.refused` (`routes_access_requests.py:124-127`, test `test_f1_the_refusal_is_audited_like_any_other`).
- **`user_managers()` mail set == people who can act on a signup.** `GET /access-requests` is gated by `_key(K.ACCESS_APPROVE)` (`auth/policy.py:59`), evaluated by `authorize(..., resource=None)` = any catalogue scope (`auth/access.py:43`), and the New accounts section/POSTs need `users.manage` (`routes_access_requests.py:92`, `policy.py:62`). `accounts.py:157-163` requires an enabled user holding `users.manage` AND `access.approve@%` (catalogue scopes all/shared/own only, `schema/auth.py:56`). Permissions come from the same `memberships JOIN group_permissions` join as `auth/sessions.py:75`, so the mail set equals the principals that pass both gates. Seeded Admin/CEO holds every key (`defaults.py:26`) so admins are still mailed. Test `test_f2_the_mailed_link_opens_for_every_recipient` opens `/access-requests` as each recipient (200).
- **No regression to `/admin/users` group editing.** Same behaviour for valid input; stricter (400) for signs/blanks/`1_0`/non-ASCII/too-long values which previously 500'd or were silently accepted (`-1`, ` 5`). Covered by `test_f1_the_admin_users_page_shares_the_same_bounded_parser` and the 400+ auth tests.
- **Sizes.** `accounts.py` 294, `routes_access_requests.py` 165, `routes_admin.py` 166, new test 171: all <= 300 (manifest said 164/168, off by 1-2, cosmetic). Functions all well under 50 lines. Docstrings present; no `_v2`/`_new` files.
- **Credentials/secrets:** no `.env` read; no credential, redaction or origin-guard path touched.

## Findings (numbered)

1. **Non-blocking, pre-existing, out of unit scope (already disclosed).** `POST /admin/users/{user_id}/{action}` (`routes_admin.py:68`, `user_id: int` unbounded) still returns a server error for a 30-digit or 2**63 id: checker probe shows `OverflowError` from `auth/accounts.py:168` (`get_user`). The manifest names only the user route; the same applies to `POST /admin/groups/{group_id}` (`routes_admin.py:131`, `admin_group_update(group_id: int, ...)`, checker probe `OverflowError`). Both need `users.manage`/`groups.manage` so exposure is an authenticated admin hitting a 500, not a bypass. Recommend a follow-up unit applying the same `Path(ge=1, le=2**63-1)` alias to the admin routes (the `UserId` alias could move next to `parse_ids`).
2. **Non-blocking, behaviour note.** `parse_ids` is a public helper imported across route modules (`routes_access_requests.py:33` imports from `routes_admin`). Acceptable (one concept, one place), but a shared home (e.g. a small ui helper module) would avoid a route-to-route import if a third caller appears.
3. **Non-blocking, documented limit confirmed.** A `users.manage`-only holder is no longer mailed and cannot open `/access-requests` (403); they act via `/admin/users` (Waiting pill). Pinned by `test_f2_a_users_manage_only_holder_can_still_decide_but_is_not_mailed`. Product choice, not a defect.
4. **Cosmetic.** Manifest line counts for `routes_access_requests.py` (164) and `routes_admin.py` (168) are 165 and 166 on disk.
5. **Process note.** The maker did not dispatch an independent senior-engineer review (stated in the manifest); this verdict is the independent check. Test additions include behaviour-pinning races (approve/approve, approve/decline) that passed before the change, correctly labelled as regression guards, not red-then-green.

## Result

All requested checks hold; verify commands reproduce. No blocking finding. **PASS**, cycle 0.
