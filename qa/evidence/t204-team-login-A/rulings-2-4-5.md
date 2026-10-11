# t204-team-login seat A sub-check: rulings 2, 4, 5 (read-only; worktree head aa6fec2e, base 9c9a91f3)

## A. First admin (AU7, AU17): ruling HARDENING-ONLY (no documented start unmet)

Code read: auth/config.py:21-23 `hosted()`, :25-33 `bind_host()` (argv `--host`/`--host=`, else `UVICORN_HOST`, else 127.0.0.1), :36-40 `auth_disabled()`, :43-47 `public_facing()` = hosted OR secure cookie OR bind not loopback, :54-72 `check_startup()`; auth/accounts.py:50-63 `_becomes_first_admin` (unset + public_facing -> False; unset + loopback -> first user only; set -> only that address and only while no admin). ui/app.py:58 calls `check_startup()` in lifespan.

Documented start paths:
- docker/entrypoint.sh:27 `exec uv run uvicorn autotester.ui.app:app --host 0.0.0.0 --port 8000 --no-access-log` -> (b): `--host 0.0.0.0` is in argv, so bind_host() = 0.0.0.0, non-loopback; AU17 refuses AUTH_DISABLED and AU7 fails closed with FIRST_ADMIN unset. Used by both docker-compose.yml (dev, `build: .`, port 8010:8000 line 7; no HOSTED set, still non-loopback by argv) and docker/compose.prod.yml (env_file /etc/autotester/server.env line 13-14; builds the same Dockerfile, ENTRYPOINT Dockerfile:33).
- docker/compose.prod.yml + DEPLOY.md:81 `AUTOTESTER_HOSTED=1` in server.env -> (a) hosted rule applies regardless of bind_host; `check_startup` also demands ALLOWED_HOSTS/ORIGINS (config.py:68-72). `.env.example` documents HOSTED (key names only read).
- DEPLOY.md:170 NSSM `--host 127.0.0.1` (b, loopback, local rule), DEPLOY.md:185 loopback + reverse proxy: HTTPS proxy -> Secure cookie makes `public_facing(secure_cookie)` True (accounts.py:57, config.py:47), so first signup is not promoted even without HOSTED (the builder's AU7 gap fix). DEPLOY.md:165 dev `uvicorn ... --port 8000` -> no --host, uvicorn default 127.0.0.1 = bind_host default (b/default, correct).
- README.md / CLAUDE.md / AGENTS.md / target.md / scripts: no uvicorn run command found. No `uvicorn.run(`, `--uds`, `--fd` anywhere in src/.
- (c) "bound by a means bind_host cannot see": none documented. Only theoretical: programmatic `uvicorn.run(host=...)`, `--uds/--fd`, or a config file; none exist in repo or docs. bind_host also honours UVICORN_HOST.

Ruling: AU7 and AU17 are met for every documented start. The bind_host argv/UVICORN_HOST limitation is hardening only (an undocumented custom launcher binding non-loopback without argv, with HOSTED unset and no HTTPS proxy, would be read as loopback). Optional hardening: have check_startup warn when it cannot see a host. Not a contract gap.

## B. Dependency (ruling 4): CONFIRMED additions only

- pyproject.toml diff 9c9a91f3..aa6fec2e: one line added `"argon2-cffi==25.1.0",  # T-204 password hashing, authorized by D-072 ...` (pyproject.toml:36 area); nothing removed.
- uv.lock: numstat `61 0` (61 added, 0 removed). Added package entries: `argon2-cffi` 25.1.0 and `argon2-cffi-bindings` 26.1.0 (name/version lines are the only `+name`/`+version` in the diff). No `-` lines at all, so no existing version/hash line changed or was removed. cffi 2.1.1 and pycparser 3.0 were already on master (uv.lock:198 / :1480 at base; :259 / :1541 at head, same versions), so they are NOT new.
- `uv --project <worktree> lock --check` output: `Resolved 89 packages in 1ms` (exit clean, only a VIRTUAL_ENV warning).
- D-074 (c) (DECISIONS.md:2218 entry, line "(c) Password hashing uses `argon2-cffi==25.1.0` ... the new dependency for T-204 AU1") and its `Changes-authorized` names "the `argon2-cffi==25.1.0` dependency in `pyproject.toml` and `uv.lock`". Authorizes exactly this (the transitive argon2-cffi-bindings is a resolver consequence of the exact pin; not separately named but within "uv.lock").

## C. Carried modules (one job each; all read docstrings)

auth/__init__ pure storage/decision logic, never imports ui/. access.py (162): the one `authorize()` + project relation data (AU12). accounts.py (203): signup, first admin, password check, admin account actions. audit.py (33): audit JSONL (AU22). config.py (80): startup config AU3/AU17/AU20. context.py (15): current request principal contextvar. db.py (162): auth SQLite store, seeding, last-admin guard. defaults.py (45): four seeded groups. groups.py (130): group CRUD + permission ticks. passwords.py (48): argon2id hash/verify, only importer of the library. policy.py (107): central route policy table, default deny. ratelimit.py (73): login/signup rate limit. sessions.py (84): server-side sessions. schema/auth.py (157): permission catalogue and auth shapes. cli_auth.py (46): `autotester auth bootstrap-admin`. ui/auth_middleware.py (155): the login gate ASGI middleware. auth_view.py (75): sign-in/up/waiting markup. admin_view.py (118): admin users/groups markup. routers.py (61): the one router list. routes_admin.py (151): admin account/group routes. routes_auth.py (100): sign in/up/out/waiting routes. routes_project_access.py (77): owner/assignee/shared relation. ui/credential_guard.py (200) and ui/project_view.py (173): NOT new; they exist on master (git cat-file at 9c9a91f3) and are MODIFIED here (+38 and +68 lines). Their module docstrings describe their old jobs (credential-paste refusal; project action card + home cards moved from app.py).

Flag (manifest accuracy): manifest line 32 lists credential_guard.py and project_view.py under "New modules"; they are modified existing files. Not named in "What changed" otherwise (project_view.py absorbs the home-page card code moved out of app.py).

Duplicates: no duplicate class/function concept found. Minor: auth/config.py:14 `_LOOPBACK = {"127.0.0.1","localhost","::1"}` duplicates ui/helpers.py:192 `_LOOPBACK_HOSTS = {"localhost","127.0.0.1","::1"}` (same set, two places; hardening/cleanliness, auth/ cannot import ui/). `PROVIDER_KEYS` is now defined once (ui/credential_guard.py:26) and aliased at routes_settings.py:26 (a moved constant, not a copy). No other secrets/redact/rate-limit/authorize code exists outside auth/ (grep).

Size: no file over 300 lines (largest accounts.py 203, credential_guard.py 200); AST scan found no function over 50 lines in these modules. `uv --project <worktree> run autotester doctor` -> `doctor: clean`.

## D. Dual-trigger line (manifest line 14): all four real
- src/autotester/auth/accounts.py:96 `if not verify_password(stored, password) or row is None or row["disabled"]:` inside `authenticate()` (def at :86). It is the credential check.
- src/autotester/ui/auth_middleware.py:114 `class _AuthGate:` (the default-deny gate).
- src/autotester/auth/passwords.py:29 `def hash_password(password: str) -> str:`.
- src/autotester/auth/sessions.py:56 `def resolve_session(token: str | None) -> Principal | None:`.

## E. Step 4c diff-scope (`diff 9c9a91f3...aa6fec2e`)
No deleted or renamed files. 35 added, 21 modified. Modified: .dockerignore, .env.example, .gitignore, docker/DEPLOY.md, docker/entrypoint.sh, docs/MAP.md, pyproject.toml, src/autotester/{cli.py, ui/app.py, ui/credential_guard.py, ui/project_view.py, ui/routes_credentials.py, ui/routes_live.py, ui/routes_project_edit.py, ui/routes_settings.py, ui/theme.py}, tests/{conftest.py, test_ui_env_editor.py, test_ui_healthz.py, test_ui_project_intake.py}, uv.lock.

Named in manifest "What changed" (lines 18-33): app.py (and routers), cli.py, routes_live.py, .env.example, DEPLOY.md, MAP.md, the dependency line (pyproject/uv.lock), conftest, test_ui_env_editor, test_ui_healthz, test_ui_project_intake (line 72/74 test lists), .dockerignore/.gitignore (lines 20,70,104 / 70), entrypoint (line 119), routes_credentials (line 102), credential_guard/project_view only as "new modules" (line 32, inaccurate). NOT named anywhere: routes_project_edit.py, routes_settings.py, theme.py (all small, AU21/AU25 edits).

Removed lines (none removes a route, config key or test; all moved/rewritten):
- app.py: the 17 `app.include_router(...)` lines and router imports moved to ui/routers.py ROUTERS; `_latest_run_status`, `_project_card`, `_portfolio_stats` moved to ui/project_view.py:115 (`_latest_run_status` present); home-page `slugs = _project_slugs()` now permission-filtered; `app = FastAPI(..., middleware=origin_guard_middleware())` rewritten.
- cli.py: only a comment re-wrapped (AT-260 text identical) + auth typer added.
- credential_guard.py, project_view.py: no removed lines (additions only).
- routes_credentials.py: `_env_table` gained a `show` param (saved value rendered only for credentials.view); old unconditional `value='{escape(present...)}'` line removed (AU21 behaviour change).
- routes_settings.py: `_PROVIDER_KEYS` tuple moved to credential_guard.PROVIDER_KEYS and aliased; value rendering gated by `can_view_credentials()`.
- routes_project_edit.py: SecretRef builder now calls `refuse_foreign_key` (new rule: key must be the project's own namespaced key) - behavior change.
- routes_live.py: healthz docstring rewritten; unsigned caller gets `{"ok": true}` only (behavior change, AU16).
- theme.py: static `NAV` constant replaced by `_nav_html()`/`_NAV_LINKS` (permission-filtered); sidebar filtered by `visible_slugs`.
- entrypoint.sh: `--no-access-log` added; `--host 0.0.0.0 --port 8000` preserved.
- tests: test_ui_env_editor `ERP_TENANT_ID` -> `DEMO_ERP_TENANT_ID` (namespacing consequence, no test removed); test_ui_project_intake `SHARED_PASSWORD` -> `ALPHA_BETA_PASSWORD`, slug beta -> alpha-beta (same); test_ui_healthz `client()` fixture now takes tmp_path/monkeypatch, plus new unsigned-in test; conftest additions only (+42).

`git diff 3a9a5b02 5e0c4b0b --stat`: exactly one file, tests/test_ui_auth_escalation.py (5 insertions, 10 deletions). Tests-only: CONFIRMED. (The diff 5e0c4b0b..aa6fec2e is the qa manifest commit.)
