# Manifest — t204-auth

**Unit:** T-204: team login with IAM-style groups. Covers email + password sign-in, open signup with zero access, a first-account admin, four seeded groups, one `authorize()`, a default-deny route policy, credential values gated on `credentials.view`, an audit file and a break-glass CLI.
**Contract:** `qa/contracts/auth.md` AU1–AU26 (on master since 6f351e11) · `core-invariants.md` C5 · `ui.md` (AU25)
**Goal task:** T-204 · **Decision:** D-072 items 3, 4, 5, 12 (new modules under `ui/`, `schema/`, a store)
**Date:** 2026-10-07
**Fix cycle:** 0 of max 3
**Tier:** L (security / auth / tenancy)
**Dual check:** required
**Policy-Version:** proportional-verification/2026-10-06.6
**Source:** branch `wave/t204-auth`, commit `d87b2181` (code), rebased onto origin/master `7782df41`

## Merge prerequisite (not yet met)

**AU1 dependency.** `argon2-cffi==25.1.0` was added to `pyproject.toml` and `uv.lock`. AU1 requires a DECISIONS entry whose `Changes-authorized` line names this library, and the coordinator will add it once Umesh confirms. **Do not merge before that entry exists.**

If Umesh declines the dependency, swap to stdlib `hashlib.scrypt` (N ≥ 2^15, r=8, p=1). The swap touches only `src/autotester/auth/passwords.py`, which is the only module that imports the library: `hash_password`, `verify_password` and `needs_rehash` sit behind one interface. The pyproject and lock lines would be reverted.

## What moved (coordinator request c)

- **Router registration.** Every `app.include_router(...)` call left `ui/app.py` and moved into `ui/routers.py`.
  - `ROUTERS` is the ordered tuple of all routers (unchanged order), with the three new ones appended: `routes_auth`, `routes_admin` and `routes_project_access`.
  - `include_all(app)` registers them.
  - `app.py` now calls `routers.include_all(app)` once. G1 should add its routers to `ROUTERS`.
- **Home-page card helpers.** `_latest_run_status`, `_project_card` and `_portfolio_stats` moved from `ui/app.py` into `ui/project_view.py`, renamed to `project_card` and `portfolio_stats`. Their imports (`valid_runs_newest_first`, `_run_counts`) moved with them.
- `ui/app.py` went from 300 to 220 lines.

## What changed

**New modules (`src/autotester/`):**

| Module | Job |
|---|---|
| `schema/auth.py` | The closed `PermissionKey` catalogue (19 keys), `Scope`, `CATALOGUE`, and the `User`, `Group`, `ProjectRelation`, `ResourceRef`, `Principal` and `RouteRule` models (all `extra="forbid"`) |
| `auth/passwords.py` | argon2id hashing behind one interface; length policy 10..128 |
| `auth/defaults.py` | The four default groups, exactly as in the contract table |
| `auth/db.py` | SQLite store at `<repo_root>/.auth/auth.sqlite3`; `BEGIN IMMEDIATE` transactions; seeds once via a meta row; posix modes 700/600; last-admin guard |
| `auth/accounts.py` | Signup, authenticate, disable, enable, delete, reset, rename, regroup, bootstrap |
| `auth/groups.py` | Group create, update and delete, with permission validation |
| `auth/sessions.py` | 256-bit tokens; only their sha256 is stored; 12 h default, clamped to 1..168 |
| `auth/access.py` | `authorize()`, `resource_for`, `visible_slugs`, `set_owner`, `set_relation` |
| `auth/ratelimit.py` | 5 failures per account or 20 per address, over 10 minutes |
| `auth/policy.py` | The central route policy table |
| `auth/audit.py` | Writes `.work/audit.jsonl` |
| `auth/context.py` | The request principal, held in a ContextVar |
| `auth/config.py` | Disabled, hosted and cookie-secure settings, and the startup checks |
| `ui/auth_middleware.py` | The gate |
| `ui/auth_view.py` | The login, signup and waiting pages |
| `ui/routes_auth.py` | The login and signup routes |
| `ui/admin_view.py` | The admin pages |
| `ui/routes_admin.py` | `/admin/users` and `/admin/groups` |
| `ui/routes_project_access.py` | Assign and share a project |
| `ui/routers.py` | Router registration (see What moved) |
| `cli_auth.py` | The `autotester auth bootstrap-admin` command |

**Edited files:**

| File | Change |
|---|---|
| `ui/app.py` | The middleware list is now the Origin guard **then** the auth gate. `check_startup()` runs in the lifespan. The home page filters by `visible_slugs`. Onboarding records the owner. |
| `ui/theme.py` | The sidebar filters by visibility. Adds an identity chip, a sign-out form and the admin links the user may use. |
| `ui/routes_credentials.py` | Adds `can_view_credentials()`. Without it the env page renders no value, no eye toggle and only a password-type input. |
| `ui/routes_settings.py` | The same rule. A key present only in the process environment shows "Set". |
| `ui/routes_live.py` | `/healthz` returns only `{"ok": true}` unless the caller holds `settings.manage`. |
| `core/paths.py` | Adds `auth_db_path()` and the `AUTOTESTER_AUTH_DIR` override (used only by the test fixture). |
| `cli.py` | Registers the `auth` sub-app. |
| `.gitignore` | Adds `.auth/`. |
| `pyproject.toml`, `uv.lock` | Add `argon2-cffi==25.1.0`. |

**Tests:**

- **New files:** `tests/auth_harness.py`, `tests/test_ui_auth_login.py`, `tests/test_ui_auth_accounts.py`, `tests/test_ui_auth_groups.py`, `tests/test_ui_auth_surface.py` (87 tests).
- **Protected change, a full-suite trigger:** `tests/conftest.py` and `tests/auth_login_fixture.py`. A session-scoped autouse patch of `TestClient.request` signs every pre-existing UI test in as a suite admin, inside that test's own scratch store. No existing assertion was weakened.
  - If a test has no scratch `AUTOTESTER_ROOT`, the patch points `AUTOTESTER_AUTH_DIR` at a suite temp directory for that request only, so the real repository's `.auth/` is never written.
  - `AUTOTESTER_TEST_NO_AUTO_LOGIN=1` turns it off. The auth tests set it, so they run with the gate ON (AU17).
- `tests/test_ui_healthz.py` uses a scratch root and adds the unauthenticated minimal-body test.

**Fixes found while testing:**

- **The last admin could be deleted.** The guard skipped an empty user table, so deleting the only account passed it. Fix: `ensure_an_admin_remains(after_delete=True)` in `delete_user`.
- **Some 404 and 405 responses became 403.** For a signed-in user, a path with no handler at all, or a wrong method, had turned into 403. Default deny now applies only when the app would actually run a handler (`_has_handler`), so 404 and 405 are unchanged (AU25). This repaired five existing UI tests without editing them.
- **`/favicon.ico` now requires a member.** Its rule changed from session-only to member, so a zero-permission account gets 403 on everything except waiting and logout (AU6).

## Permission keys (closed catalogue, `schema/auth.py`)

`project.view`, `project.create`, `project.edit`, `project.run`, `project.assign`, `report.view`, `video.view`, `video.upload`, `video.share`, `access.approve`, `comment.create`, `credentials.view`, `credentials.edit`, `schedule.manage`, `live.view`, `live.control`, `users.manage`, `groups.manage`, `settings.manage`

## Coverage

| AU | Evidence (tests) | Status |
|---|---|---|
| AU1 | `test_au1_password_is_argon2id_and_never_stored`: canary absent from every file under the root and the store, and from caplog; `$argon2id$` with m ≥ 19 MiB and t ≥ 2 | met; D-entry pending (see prerequisite) |
| AU2 | `test_au2_failures_are_identical` (unknown, wrong and disabled give the same bytes and 401); the unknown-email path verifies against a dummy hash; `test_au2_success_redirects_to_a_same_site_next` ×4 | met |
| AU3 | Cookie flags on http, https and hosted, plus the `COOKIE_SECURE=0` opt-out; a new id at every login; bad cookie ×4 (tampered, truncated, unknown, expired) refused and creates nothing; disable takes effect on the next request, both through the action and through the raw store flag; lifetime clamp | met |
| AU4 | `test_au4_logout_ends_the_session` (GET changes nothing; old cookie refused); `test_au4_logout_is_origin_guarded` | met |
| AU5 | 6 bad attempts then the correct password → 429 with no hint that the account exists; injected-clock window; per-address limit | met. The constants live in `auth/ratelimit.py`. **Documenting them in `.env.example` is out of file scope** (owned by the other builder) |
| AU6 | Normalize and validate; duplicate refused with the original password still working; a zero-permission account gets 403 on **every** enumerated route except waiting and logout; the waiting page says "administrator" and lists no users | met |
| AU7 | First signup is admin and later ones are not; a threaded barrier gives exactly one admin; the `AUTOTESTER_FIRST_ADMIN_EMAIL` variant | met |
| AU8 | Disable, enable, rename and regroup through HTTP; reset revokes sessions; delete keeps the audit rows and un-owns projects; a non-admin gets 403 on every action | met |
| AU9 | Last admin: disable, delete, regroup, untick `users.manage` and delete the group are all refused with nothing changed; a second admin lifts the guard | met |
| AU10 | Union and untick take effect on the next request; unknown key or scope ×3 refused with nothing stored; labelled checkboxes; deleting a group in use warns with its member count before the confirmed delete; group-edit escalation (developer, and a `groups.manage` holder without `users.manage`) refused | met |
| AU11 | Seeds equal the contract table; an edit and a deleted default survive a simulated restart | met |
| AU12 | `test_au12_scope_table`: 4 groups × 5 relations (including a legacy project with no owner) × view, edit and `credentials.view`; `git grep -w` of `ui/` (tracked and untracked) for group-name literals finds nothing | met |
| AU13 | Four users × two projects: the home list plus direct URLs. A project the user may not view returns a 404 byte-identical to a missing project, modulo the slug. Visible but without the action → 403 | met |
| AU14 | Every `(method, path)` the app serves has a policy row (more than 60 routes, enumerated through included routers); a route added at runtime without a row → 403 | met |
| AU15 | No consent, approval or write_policy code touched; the gate sits in front of the existing checks | unchanged by construction. **No dedicated test**; AT-570 (UI runs check no RunApproval) predates this unit and is still open |
| AU16 | Unauthenticated enumeration of every route: 401 for JSON, a 302 to `/auth/login?next=/…` for HTML, no input echoed, and the data-root tree byte-identical before and after; unsafe `next` ×4 dropped; `/healthz` minimal body | met |
| AU17 | Disabled flag on loopback is honoured; on 0.0.0.0 or hosted it is refused at startup; the gate is on by default | met |
| AU18 | A cross-origin POST with a valid admin cookie gets 403 on login, signup, logout, admin and onboard; the guard runs before the gate (unauthenticated cross-origin → 403, not 401) | met for ordering. **AT-760 and AT-761 (non-numeric port, duplicate Origin) live in `ui/helpers.py` on `wave/at758-759-security`**: integrate at merge |
| AU19 | — | **out of file scope**: the Host allow-list is in `ui/helpers.py` on the other branch (AT-758) |
| AU20 | Hosted without an allow-list raises; with `ALLOWED_ORIGINS` it starts | met for startup. The `.env.example` documentation is out of scope |
| AU21 | Sentinel on `/projects/vault/env` is hidden from Tester, Developer and Sub-admin and shown to Admin; a write without view works and is never echoed; settings page hides values from a `settings.manage`-only user, and an env-only provider key shows "Set" | met |
| AU22 | Audit has a login-failed line, user.password and the path template; no canary password, cookie or `$argon2` hash anywhere in the file | met for the app. **Disabling the uvicorn access log in `docker/entrypoint.sh` is out of file scope** |
| AU23 | Store under `repo_root()/.auth/`, gitignored; posix 700/600; models in `schema/` | met except **the `.dockerignore` `.auth/` entry, which is out of file scope** (docker files) |
| AU24 | `pathlib` only, no `fcntl` or `pwd`; atomicity comes from SQLite `BEGIN IMMEDIATE` | Windows run here. **Linux evidence is owed** (T-203 rehearsal → `qa/evidence/t204-linux-run.md`) |
| AU25 | The full affected UI set passes with the gate ON and an admin session | met (see Metrics) |
| AU26 | — | checker Mode D browser walk |

## Falsifications

Each mutant ran in a throwaway copy of `src/`, `tests/` and `scripts/` (temp dir, put first on `PYTHONPATH`). A control run of the unmutated copy was green. Runner: session scratchpad `t204_mutants.py`; log: `.work/t204-mutants.log`.

| # | Mutant | Test | Result |
|---|---|---|---|
| 0 | CONTROL: unmutated copy | `test_au1_…` | green (harness valid) |
| 1 | AU1: store the password as given | `test_au1_password_is_argon2id_and_never_stored` | RED |
| 2 | AU2: failure text includes the email | `test_au2_failures_are_identical` | RED |
| 3 | **AU3 session forgery**: the lookup ignores the token hash | `test_au3_bad_cookie_is_refused_and_creates_nothing` | RED |
| 4 | **Disabled user still logged in**: the session join drops `disabled = 0` | `test_au3_session_lookup_itself_refuses_a_disabled_account` | RED |
| 5 | AU4: logout does not delete the session | `test_au4_logout_ends_the_session` | RED |
| 6 | AU5: rate-limit check removed | `test_au5_lock_after_failures_…` | RED |
| 7 | AU6: zero-permission check removed | `test_au6_zero_permission_account_…` | RED |
| 8 | AU7: every signup becomes admin | `test_au7_first_signup_is_admin_…` | RED |
| 9 | **Privilege escalation via the group-edit route**: members editable without `users.manage` | `test_au10_group_edit_route_cannot_escalate` | RED |
| 10 | AU8: the policy row for user actions becomes member-level | `test_au8_non_admin_gets_403_…` | green: survived, because the handler's own `_require(users.manage)` still refuses (defence in depth) |
| 10b | AU8: both layers removed (policy member-level **and** the handler check) | `test_au8_non_admin_gets_403_…` | RED |
| 11 | AU9: last-admin guard dropped | `test_au9_last_admin_cannot_be_locked_out` | RED |
| 12 | AU10: any permission string accepted | `test_au10_unknown_key_or_scope_stores_nothing` | RED |
| 13 | AU11: re-seed on every start | `test_au11_seeded_once_edits_survive_restart` | RED |
| 14 | AU12: `shared` treated as `all` | `test_au12_scope_table` | RED |
| 15 | **Tester reads an unshared project**: the project-view check is skipped | `test_au13_four_users_two_projects` | RED |
| 16 | AU14: an unmatched route gets a member rule | `test_au14_an_undeclared_route_is_refused` | RED |
| 16b | AU14: the handler probe always says "no handler" | `test_au14_an_undeclared_route_is_refused` | RED |
| 17 | AU16: unauthenticated GET allowed | `test_au16_only_the_public_set_answers_unsigned_in` | RED |
| 18 | AU17: disabled flag honoured even when hosted | `test_au17_disabled_flag_is_refused_when_hosted` | RED |
| 19 | AU18: middleware reordered so auth runs first | `test_au18_guard_runs_before_the_login_gate` | RED |
| 20 | AU20: hosted check removed | `test_au20_hosted_needs_an_allow_list` | RED |
| 21 | **A non-admin reads credential values**: `can_view_credentials()` always true | `test_au21_values_only_for_credentials_view` | RED |
| 22 | AU22: audit writes the attempted password | `test_au22_audit_lines_hold_no_secret` | RED |

The first run of mutant 4 survived because `set_disabled` also purges sessions. A raw-store test was added (`…session_lookup_itself_refuses_a_disabled_account`), and the mutant was re-run RED. The first run of mutant 9 pointed at a test that had not been inserted. The test was added, and the mutant was re-run RED.

## Commands run (worktree, after the rebase onto 7782df41)

- `uv run ruff check src tests scripts` → `All checks passed!`
- `uv run autotester doctor` → `doctor: clean` (after `autotester map` regenerated `docs/MAP.md`)
- **Before the rebase, on 642ab4bd.** The affected set: every `tests/test_ui*.py`, plus test_coverage_wiring, test_crawl_coverage, test_crawl_coverage_bounds, test_crawl_status_surfaces, test_credential_run_approval, test_ensemble_honesty, test_explore_error_causes, test_permission_coverage and test_source_is_a_recording.
  - Result: `5 failed, 620 passed, 1 skipped in 771.78s`.
  - The 5 failures (404/405 turned into 403) were fixed by `_has_handler`. Their files then passed together with the auth files: `97 passed in 150.03s`.
- **After the rebase** (master's changes since 642ab4bd touch none of `ui/`, `core/`, conftest or the `test_ui*` files; only MAP.md overlapped and was regenerated):
  - `uv run pytest tests/test_ui_auth_login.py tests/test_ui_auth_accounts.py tests/test_ui_auth_groups.py tests/test_ui_auth_surface.py tests/test_ui.py tests/test_ui_healthz.py tests/test_ui_origin_guard.py tests/test_ui_dashboard.py tests/test_ui_error_pages.py tests/test_ui_error_page_headers.py tests/test_ui_crawls.py` → `200 passed in 151.70s`
- No full suite was run (RAM-limited, per the coordinator). **Full-suite trigger:** this unit changes `tests/conftest.py`, so the checker owes one full suite.

## Integration notes for merge

- **T-125.** Not yet on master at 7782df41. When it lands, add `routes_catalog.router` to `ui/routers.py` `ROUTERS`, and a `("GET", "/projects/{slug}/catalog…")` → `_VIEW` row in `auth/policy.py`. `test_au14_every_route_has_a_policy_row` fails until the row exists, so the gap cannot be missed.
- **`wave/at758-759-security`.** Owns `ui/helpers.py`: the Host allow-list for AU19, plus AT-760 and AT-761. `app.py` keeps `origin_guard_middleware()` first, so its Host check slots in there.
- **Docker and `.env.example` owner.** Needs the `.dockerignore` `.auth/` entry (AU23), access log off (AU22), the `AUTOTESTER_AUTH_*` / `HOSTED` / `COOKIE_SECURE` / `SESSION_HOURS` / `FIRST_ADMIN_EMAIL` keys and the rate-limit constants (AU5, AU20).

## Metrics

Metrics: files new 26 (21 src, 5 test) · files edited 13 · auth tests 87 · affected UI tests 625 (620 + 5 fixed) · falsifications 25 rows (23 killed, 1 survived by design, 1 control) · lines +3.1k / −0.1k · largest new file 192 lines.

## Status: ready-for-check
