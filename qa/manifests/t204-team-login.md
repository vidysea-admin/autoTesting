# Manifest — t204-team-login (team login by email and password in front of the hosted UI, D-072)

**Unit:** T-204. Email + password sign-in, open signup with zero access, a fixed-email first admin on a hosted server, four seeded groups with checkbox permissions, one `authorize()`, a default-deny route policy, credential values gated on `credentials.view`, an audit file and a break-glass CLI.
**Contract:** `qa/contracts/auth.md` AU1-AU27 · `core-invariants.md` C5 · `ui.md` (AU25). Brief: `qa/briefs/t204-team-login.md` (untracked in the root checkout).
**Authority:** D-072 items 3, 4, 5, 12 · D-074 (c) argon2-cffi==25.1.0, (d) first admin by `AUTOTESTER_FIRST_ADMIN_EMAIL`, (e) `AUTOTESTER_COOKIE_SECURE=0` interim. The earlier manifest's "Merge prerequisite (not yet met)" text about the AU1 dependency is STALE and is not carried: D-074(c) authorizes the library and `Changes-authorized` names it.
**Goal task:** T-204
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (security / auth / tenancy)
Fix cycle: 0
Branch: `wave/t204-team-login` · Base: master `9c9a91f3` (contains T-203 hosting and the Host allow-list unit at758-759, merged `02c5f016`). Master has since moved only under `qa/` (tip `276cc2ec`); `git merge-tree` of the branch against that tip is clean.
Code commit under check: 5e0c4b0b (this manifest is a qa-only commit on top)
Executor: claude-sonnet-subagent (maker build subagent)
Dual check: required
dual-trigger: auth src/autotester/auth/accounts.py:96 (the credential check `verify_password`), src/autotester/ui/auth_middleware.py:114 (the default-deny gate `_AuthGate`), src/autotester/auth/passwords.py:29 (argon2id `hash_password`), src/autotester/auth/sessions.py:56 (`resolve_session`)
Persona walk: required, UI surface (login, signup, waiting page, admin users and groups pages with permission checkboxes, project access page, navigation per type). The checker's Mode D runs it; the builder ran no browser. Start: `AUTOTESTER_ROOT=<fresh scratch dir>` then, from `D:/autoTesting/.worktrees/t204-team-login`, `uv run uvicorn autotester.ui.app:app --host 127.0.0.1 --port 8765`. Open `http://127.0.0.1:8765/`. Accounts: none exist; on this loopback dev server the FIRST signup becomes Admin/CEO (AU7 local rule), so sign up your own scratch address with a 10+ character password, then a second one (waiting page), and use the admin pages to tick groups. Never use a real address or the repo-root `.env`. Hosted variant (AU7 hosted rule, AU3 cookies): add `AUTOTESTER_HOSTED=1 AUTOTESTER_ALLOWED_HOSTS=127.0.0.1:8765 AUTOTESTER_COOKIE_SECURE=0 AUTOTESTER_FIRST_ADMIN_EMAIL=<scratch address>`; only that address then becomes admin. Prior evidence to compare: `qa/evidence/browser-t204-auth-2026-10-07-checker-b/`.
Round cap: SECURITY CLASS (authentication, sessions, privilege escalation and the credential boundary in front of a hosted UI); the 2-PASS cap for non-security seams does not apply. Seam: `auth/` store and `ui/auth_middleware.py` gate.

## What changed since the earlier branch (carried vs rebuilt)

**Carried (cherry-picked, nothing re-derived):** `8a9ac0cd` and `cb54b2d5` from `wave/t204-auth-fix1` (the cycle-0 code and the fix cycle 1 code that repairs both cycle-0 FAILs: A's AU3 `__Host-` fallback, AU21 `/env/add` key poisoning and group-title XSS; B's AU21 and AU23 `.dockerignore`). Not carried: the qa commits and the old manifest. Two conflicts resolved by hand: `ui/app.py` (kept master's `routes_runs.get_queue()` in the lifespan and added `check_startup()`; `routes_runs` is imported again because the router list moved to `ui/routers.py`) and `ui/routes_live.py` (master's `import autotester` plus the auth imports); `.env.example` (master already held the auth key block from T-203: kept it and merged the T-204 comments, no duplicate keys).

**Rebuilt / changed here:**
- `auth_db_path` and `ENV_AUTH_DIR` moved from `core/paths.py` to `auth/db.py` (paths.py is again byte-identical to master and under 300 lines); tests import it from `autotester.auth.db`.
- `auth/policy.py::match` renamed `route_for` (doctor `duplicate-concept` against `stages/ai_catalog.py::match`); one caller in `ui/auth_middleware.py`.
- `cli.py` comment re-wrapped by one line to stay at 300 lines after the two-line `auth` registration (comment text unchanged).
- AU7 gap closed (test first, red then green): the contract counts "a Secure session cookie in effect" as hosted. `auth/config.py::public_facing(secure_cookie)` and `accounts.signup(..., secure_cookie)` now do; `routes_auth.py` passes `cookie_secure(request.url.scheme)`. A loopback bind behind an HTTPS proxy with `AUTOTESTER_HOSTED` unset no longer hands the first signup admin.
- AU19/AU18/AU15 against the merged Host guard: new `tests/test_ui_auth_host_and_consent.py` (13 tests): a foreign Host gets an empty 403 on `/auth/login` GET and POST and `/healthz`, creates no session and sets no cookie; a signed-in Admin cookie under `Host: evil.example` reads no saved credential; a listed host and the host of an allowed origin can sign in (with the `__Host-` cookie when hosted); non-numeric Origin port (AT-760), repeated Origin or Host header (AT-761) and a `*` origin are refused on the auth routes; Admin and Developer get the same "Crawl approval required" 403 on `/explore` with no approval (AU15, which had no dedicated test).
- AU27 gap closed: a test that a non-Admin who HOLDS `settings.manage`, `users.manage` and `credentials.view` still cannot hand them to a new group (the earlier suite let the `not admin` half of `require_may_grant` survive a mutation).
- Two stale assertions repaired: `test_au3_bad_cookie_is_refused_and_creates_nothing[expired]` (`== before` became `<= before`; a refused expired cookie purges its own row, nothing is ever added) and the pinned policy table gained `GET /projects/{slug}/catalog` (`project.view`).
- Docs and config: `docker/DEPLOY.md` step 5 now describes the real first-admin flow (fixed email, or `autotester auth bootstrap-admin`, rate limit, where accounts live); `.env.example` documents `AUTOTESTER_AUTH_DIR` (a hosting test pins every key the code reads) and the T-204 key comments; `tests/auth_harness.py` comment no longer refers to an unmerged branch; `docs/MAP.md` regenerated.

**New modules (list for owner confirmation; all but the last are carried from the earlier branch, all authorized by D-072 "new modules under `ui/`, `schema/`, a store"):** `src/autotester/schema/auth.py`; `src/autotester/auth/{__init__,access,accounts,audit,config,context,db,defaults,groups,passwords,policy,ratelimit,sessions}.py`; `src/autotester/cli_auth.py`; `src/autotester/ui/{auth_middleware,auth_view,admin_view,credential_guard,project_view,routers,routes_admin,routes_auth,routes_project_access}.py`; tests `tests/auth_harness.py`, `tests/auth_login_fixture.py`, `tests/test_auth_deploy_files.py`, `tests/test_ui_auth_{accounts,cli_and_limits,escalation,groups,hardening,login,surface,survivors}.py`. **New in this unit: `tests/test_ui_auth_host_and_consent.py`** (a test module, no src module). `ui/routers.py` takes the router list out of `ui/app.py` (app.py 300 -> 218 lines); T-205 then adds its stubs to `ROUTERS` (brief section 10).
**Dependency:** `argon2-cffi==25.1.0` in `pyproject.toml` and `uv.lock`, the one D-074(c) authorizes; `uv lock --check` -> `Resolved 89 packages`. No other dependency.

## Held on an owner answer or elsewhere (stated, not hidden)

- **AUTOTESTER_FIRST_ADMIN_EMAIL (open owner input).** Built to work when set and to fail closed when unset: hosted or non-loopback with the variable unset promotes nobody, startup prints one warning naming the variable and the CLI (`autotester auth bootstrap-admin --email <addr> --password-stdin`, listed in `docs/MAP.md`), and the server still starts. No account or address was invented or committed. Umesh sets the value in the server's `.env`.
- **AU24 Linux run: HELD / PARTIAL.** Windows-local only here (pathlib throughout, no POSIX-only top-level import; SQLite `BEGIN IMMEDIATE` carries the concurrency). The Linux run (`qa/evidence/t204-linux-run.md`) is owed from the T-203 rehearsal or any Linux host; not produced by the builder.
- **AU26** is the checker's Mode D walk (above); the builder ran no browser.
- **P5 escalation rule** (Admin-only: Admin/CEO membership, `users.manage`, `groups.manage`, `settings.manage`, `credentials.view`, grant only what you hold) is a default the owner may change; no `Answered:` line exists. It does not block the build.
- **Left as open owner questions, deliberately unchanged:** trusting `X-Forwarded-For` behind the Caddy proxy (the per-address limit of 20 failures reads `request.client.host`; behind the compose proxy every user shares the proxy's address unless uvicorn's `--forwarded-allow-ips` is set, so 20 failures from anyone can lock sign-in for everyone for 10 minutes; see PROPOSED-ISSUE), whitespace or NUL-only passwords, SQLite WAL mode, per-account lockout denial of service, and the earlier low items P10, P12, P13, P15, P16. `bind_host()` reads `sys.argv`/`UVICORN_HOST` only (P13).
- **Pre-existing failure, not this unit's:** `tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads` fails on master and here for `AUTOTESTER_SCHEDULE_GRACE_MINUTES` and `AUTOTESTER_TICK_INTERVAL_S` (read by `stages/scheduler.py`); this unit added `AUTOTESTER_AUTH_DIR` so it does not add to the list.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L. Base: master `9c9a91f3` + product commits up to 5e0c4b0b.
Affected tests / full-suite trigger: scoped files only, no builder full suite. `tests/conftest.py` carries the suite auto-login (a full-suite trigger for the checker): `full-suite trigger: conftest edit`.
Pre-check[AU1]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au1_ -> 2 passed (argon2id, canary absent from store, logs, audit; uv.lock pin)
Pre-check[AU2]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au2_ -> 7 passed
Pre-check[AU3]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au3_ -> 15 passed
Pre-check[AU4]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au4_ -> 2 passed
Pre-check[AU5]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au5_ -> 8 passed
Pre-check[AU6]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au6_ -> 3 passed
Pre-check[AU7]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k "test_au7_ or test_d074" -> 11 passed (hosted+set, hosted+unset, CLI, loopback, case, Secure cookie, warning)
Pre-check[AU8]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au8_ -> 4 passed
Pre-check[AU9]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au9_ -> 2 passed
Pre-check[AU10]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au10_ -> 7 passed
Pre-check[AU11]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au11_ -> 1 passed
Pre-check[AU12]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au12_ -> 21 passed
Pre-check[AU13]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au13_ -> 3 passed
Pre-check[AU14]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au14_ -> 3 passed (every route incl. T-203 queue and catalog has a pinned row)
Pre-check[AU15]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au15_ -> 1 passed
Pre-check[AU16]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au16_ -> 10 passed
Pre-check[AU17]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au17_ -> 2 passed
Pre-check[AU18]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au18_ -> 12 passed
Pre-check[AU19]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au19_ -> 6 passed (plus tests/test_ui_origin_guard.py in the aggregate)
Pre-check[AU20]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au20_ -> 1 passed
Pre-check[AU21]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au21_ -> 13 passed
Pre-check[AU22]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au22_ -> 4 passed
Pre-check[AU23]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_au23_ -> 1 passed (`.auth/` and `**/.auth/` in `.dockerignore`; the gitignore entry and posix modes are covered in the AU1/AU3 files)
Pre-check[AU24]: 5e0c4b0b uv run autotester doctor -> doctor: clean (Windows-local only; the Linux run is HELD, see above)
Pre-check[AU25]: 5e0c4b0b uv run pytest -p no:xdist tests/test_ui.py tests/test_ui_healthz.py tests/test_ui_error_pages.py tests/test_ui_env_editor.py tests/test_ui_project_intake.py -> 150 passed (the gate ON, Admin session; and 417-test wider set below)
Pre-check[AU27]: 5e0c4b0b uv run pytest -p no:xdist <the 10 auth test files> -k test_p5 -> 10 passed
Pre-check: 5e0c4b0b uv run pytest -p no:xdist tests/test_ui_auth_login.py tests/test_ui_auth_accounts.py tests/test_ui_auth_groups.py tests/test_ui_auth_surface.py tests/test_ui_auth_escalation.py tests/test_ui_auth_hardening.py tests/test_ui_auth_cli_and_limits.py tests/test_ui_auth_survivors.py tests/test_ui_auth_host_and_consent.py tests/test_auth_deploy_files.py tests/test_ui.py tests/test_ui_healthz.py tests/test_ui_origin_guard.py tests/test_ui_error_pages.py tests/test_ui_env_editor.py tests/test_ui_project_intake.py tests/test_credential_run_approval.py tests/test_env_loading.py tests/test_permission_coverage.py -> 350 passed, 1 skipped, 1 warning in 212.47s
Pre-check: 5e0c4b0b (one tests-only commit above 3a9a5b02: two escalation tests compacted to 300 lines; that file re-run -> 22 passed, the other 18 files unchanged) uv run ruff check src tests scripts; uv run autotester doctor; uv lock --check -> All checks passed!; doctor: clean; Resolved 89 packages
Wider set (run on 81d0e7f5, before the one added AU27 test; no src change between): every other `tests/test_ui*.py` (40 files) plus `test_hosting_config.py`, `test_hosting_deploy.py`, `test_run_queue.py`, `test_run_queue_resilience.py`, `test_core.py` -> 416 passed, 1 failed (the pre-existing `AUTOTESTER_SCHEDULE_GRACE_MINUTES`/`TICK_INTERVAL_S` documentation test; `AUTOTESTER_AUTH_DIR` was then documented).
mutant-cap-raise: security class with 27 contract criteria (AU1-AU27); one mutant per criterion is the minimum that proves each is tested, 2 criteria have none (AU24, AU26), and two criteria carry a second mutant (AU7b, AU27b) for a gap found during this run
Metrics: start=2026-10-11 end=2026-10-11 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=27 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9

## Falsification (one throwaway copy of `src/ tests/ scripts/ docs/ docker/` and the config files under the session scratchpad, OUTSIDE the worktree; run with the worktree venv and `PYTHONPATH=<copy>/src`; each row: the named test(s) green on the unmutated copy, one edit, red; the edit restored in a `finally`; the bound tree never touched). Runner: scratchpad `falsify_t204.py`. Two rows first came back BAD and were repaired: AU2 pointed at the wrong test file, and AU27b survived because no test exercised "held but admin-only" (test added, then RED).

Falsify[AU1]: `passwords.py` `hash_password` returns the password as given -> `test_au1_password_is_argon2id_and_never_stored` 1 passed before, 1 failed after
Falsify[AU2]: `passwords.py` unknown-email dummy hash replaced by `''` -> `test_au2_an_unknown_email_still_pays_one_verification` green before, red after
Falsify[AU3]: `auth_middleware.py` `session_token` accepts the plain cookie name when Secure -> `test_au3_hosted_accepts_only_the_host_prefixed_cookie` green, red
Falsify[AU4]: `sessions.py` `end_session` no longer deletes -> `test_au4_logout_ends_the_session` green, red
Falsify[AU5]: `ratelimit.py` per-account limit raised to 10**9 -> `test_au5_lock_after_failures_even_with_the_right_password` green, red
Falsify[AU6]: `auth_middleware.py` zero-permission check removed -> `test_au6_zero_permission_account_reaches_only_waiting_and_logout` green, red
Falsify[AU7]: `accounts.py` the fixed-email test dropped (any signup is admin while none exists) -> `test_d074_hosted_with_the_fixed_email_promotes_only_that_address` green, red; and `config.py` `public_facing` ignores the Secure cookie -> `test_d074_a_secure_cookie_in_effect_counts_as_hosted_for_the_first_admin` green, red
Falsify[AU8]: `accounts.py` password reset stops revoking sessions -> `test_au8_password_reset_revokes_sessions` green, red
Falsify[AU9]: `db.py` last-admin guard `if not ok` -> `if False` -> `test_au9_last_admin_cannot_be_locked_out` green, red
Falsify[AU10]: `groups.py` an unknown permission string is accepted -> 3 selected `test_au10_unknown_key_or_scope_stores_nothing` cases, 3 passed before, 3 failed after
Falsify[AU11]: `db.py` seeded-once check -> `if False` -> `test_au11_seeded_once_edits_survive_restart` green, red
Falsify[AU12]: `access.py` `shared` scope always true -> `test_au12_scope_table` 20 passed before, 7 failed after (selected with the file's other au12 tests)
Falsify[AU13]: `auth_middleware.py` project-view check skipped -> `test_au13_four_users_two_projects` green, red
Falsify[AU14]: `auth_middleware.py` unmatched route no longer refused -> `test_au14_an_undeclared_route_is_refused` green, red
Falsify[AU15]: `routes_crawls.py` a missing approval redirects instead of the 403 -> `test_au15_admin_and_developer_get_the_same_missing_approval_refusal` green, red
Falsify[AU16]: `auth_middleware.py` unauthenticated branch skipped -> `test_au16_only_the_public_set_answers_unsigned_in` green, red
Falsify[AU17]: `config.py` `auth_disabled()` always true -> `test_au17_disabled_flag_is_refused_when_hosted` green, red
Falsify[AU18]: `ui/app.py` middleware order reversed (auth before the Origin/Host guard) -> `test_au18_guard_runs_before_the_login_gate` green, red
Falsify[AU19]: `helpers.py` `or not _host_allowed(headers["host"])` -> `or False` -> `test_au19_a_foreign_host_gets_no_login_page_and_no_session` (3 hosts) 3 passed before, 3 failed after
Falsify[AU20]: `config.py` hosted allow-list check -> `if False` -> `test_au20_hosted_needs_an_allow_list` green, red
Falsify[AU21]: `routes_credentials.py` `can_view_credentials()` always true -> `test_au21_values_only_for_credentials_view` green, red
Falsify[AU22]: `routes_auth.py` the failed-login audit line records the password -> `test_au22_audit_lines_hold_no_secret` green, red
Falsify[AU23]: `.dockerignore` loses `.auth/` and `**/.auth/` -> `tests/test_auth_deploy_files.py` 3 passed before, 1 failed after
Falsify[AU24]: not falsifiable by a unit test (the Linux run is the evidence and it is HELD); no mutation claimed
Falsify[AU25]: `auth_middleware.py` `_has_handler` always true (404/405 turn into 403) -> `tests/test_ui_error_pages.py` 12 passed before, 2 failed after
Falsify[AU26]: not applicable to the builder (the checker's Mode D walk); no mutation claimed
Falsify[AU27]: `access.py` the held-permission check -> `if False` -> `test_p5_a_new_group_cannot_carry_more_than_its_creator_holds` green, red; and `and not admin` -> `and False` -> `test_p5_a_held_admin_only_key_is_still_admin_only_to_grant` green, red

## How to verify
- `uv run pytest -p no:xdist` on the Pre-check file list above (the checker owes the full suite: `tests/conftest.py` auto-login is a full-suite trigger).
- `uv run ruff check src tests scripts` ; `uv run autotester doctor` (the root-clutter violations exist only in the root checkout) ; `uv lock --check`.
- Mode D walk per `Persona walk:` above; compare with `qa/evidence/browser-t204-auth-2026-10-07-checker-b/`.

## Not claimed / gaps stated
- No real-browser run, no Linux run (AU24), no run behind the Caddy proxy; `Secure`/`__Host-` cookies are exercised through `TestClient` with an https base URL.
- AT-570 (UI runs check no `RunApproval`) is still open and not this unit's; AU15 is pinned only for the crawl/explore path, which does check approval.

PROPOSED-ISSUE: {"severity":"medium","type":"hardening","title":"Per-address sign-in limit (20 failures / 10 min) reads request.client.host; behind the compose Caddy proxy every user shares the proxy address, so 20 failed logins from anyone lock sign-in for everyone for 10 minutes unless uvicorn trusts the proxy's X-Forwarded-For","file":"src/autotester/ui/routes_auth.py","fix":"decide with the owner: set uvicorn --forwarded-allow-ips for the proxy network in docker/entrypoint.sh and document it, or key the address limit on the forwarded client only when the peer is the configured proxy"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"auth/config.py bind_host() reads sys.argv and UVICORN_HOST only, so a server started through a config file or a programmatic uvicorn.run bound to 0.0.0.0 is treated as loopback (AU7 local first-account-admin, AU17 auth-disabled allowed)","file":"src/autotester/auth/config.py","fix":"also read the socket the server actually bound, or require AUTOTESTER_HOSTED=1 for any non-dev start"}

Status: ready-for-check
