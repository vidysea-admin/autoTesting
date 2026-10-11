t204-team-login blind sub-checker B report: diff scope, doctor/lint, deploy files, source read (worktree aa6fec2e vs base 9c9a91f3)

The summary file D:/autoTesting/qa/evidence/t204-team-login-B/diff/summary.md was NOT written. The Write tool refused ("subagents should return findings as text"). This message is the whole report. Nothing under the worktree or the root checkout was touched. My scratch files are only in the session scratchpad.

1. DIFF SCOPE
(a) Nothing required by the contract was lost. Removed or moved items:
- `ui/app.py`: removed `_latest_run_status`, `_project_card`, `_portfolio_stats`. They moved to `ui/project_view.py` as `_latest_run_status`, `project_card`, `portfolio_stats`. Grep of src and tests finds no other importer.
- `ui/app.py`: removed the 17 `app.include_router(...)` lines. They moved to `ui/routers.py` (`include_all`).
- `ui/theme.py`: removed the `NAV` constant. Grep finds no other user. `_nav_html()` replaces it.
- `ui/routes_settings.py`: `_PROVIDER_KEYS` is now an alias of `credential_guard.PROVIDER_KEYS`.
- `cli.py`: only a comment re-wrap (5 lines to 4) plus the `auth` registration.
(b) Touched files not named in the manifest's "What changed" are `ui/credential_guard.py` and `ui/project_view.py`. Both are pre-existing files (state M), but the manifest lists them under "New modules". `docs/MAP.md` is named (regenerated).
(c) Test changes:
- `tests/conftest.py`: +42/-0.
- `tests/test_ui_healthz.py`: +14/-1. The `client` fixture now takes `tmp_path` and sets `AUTOTESTER_ROOT`; one new test is added.
- `tests/test_ui_env_editor.py`: `ERP_TENANT_ID` became `DEMO_ERP_TENANT_ID` (5/5 lines).
- `tests/test_ui_project_intake.py`: `SHARED_PASSWORD` became `ALPHA_BETA_PASSWORD`, slug `beta` became `alpha-beta` (4/4 lines).
- Assertions are otherwise identical. No skip, xfail, timeout or threshold was added.
- The renames are forced by the new key-namespace gate. The intake test keeps its intent only because project `alpha` can declare a key in `alpha-beta`'s namespace (see F3).
(d) Route table, master vs HEAD (openapi plus walk of included routers, 60 vs 75): DROPPED none. ADDED exactly 15, all auth/admin:
- `/admin/groups` GET and POST
- `/admin/groups/{group_id}` GET and POST
- `/admin/groups/{group_id}/delete` POST
- `/admin/users` GET
- `/admin/users/{user_id}/{action}` POST
- `/auth/login` GET and POST
- `/auth/logout` POST
- `/auth/signup` GET and POST
- `/auth/waiting` GET
- `/projects/{slug}/access` GET and POST

All 67 openapi routes have a policy row. The 2 apparent misses are only the `:path` spelling.
(e) uv.lock is +61/-0 and pyproject.toml is +1. The lock adds `argon2-cffi 25.1.0` and `argon2-cffi-bindings 26.1.0`, plus the two project-metadata lines. Its dependency cffi 2.1.1 was already locked on master, and pycparser 3.0 was already locked too. pyproject adds only `"argon2-cffi==25.1.0"`. Nothing else changed. Bindings 26.1.0 is a transitive version, not pinned.
(f) conftest auto-login:
- A session-scoped autouse fixture replaces `TestClient.request`.
- Unless `AUTOTESTER_TEST_NO_AUTO_LOGIN == "1"` (`tests/auth_login_fixture.py:27`), it creates a suite admin plus a 1-hour session in the test's scratch store.
- With no `AUTOTESTER_ROOT`, it points `AUTOTESTER_AUTH_DIR` at a suite temp dir and redirects `audit.repo_root` for the duration of the request.
- It sets both cookie names on the client.
- No src file reads `AUTOTESTER_TEST_*` (grep of src is empty).
- The only gate switch in src is `AUTOTESTER_AUTH_DISABLED` (`auth/config.py:36`, `ui/auth_middleware.py:58`). It is refused when hosted or on a non-loopback bind.
- There is no header or query bypass in `auth_middleware.py`. It reads only `accept` (line 64) and the cookie.

2. DOCTOR / LINT (venv ruff; `uv --directory` for the other two)
- `ruff check src tests scripts`: `All checks passed!`
- `autotester doctor`: `doctor: clean`
- `uv lock --check`: `Resolved 89 packages`
- The doctor output shows no violations at all, including none in the root checkout.
- Every BaseModel in `schema/auth.py` carries `ConfigDict(extra="forbid")`: User:90, Group:103, ResourceRef:121, Principal:135, RouteRule:154. There are exactly 5 models.
- No changed .py file is over 300 lines (largest is 203).

3. DEPLOY FILES
- `docker/entrypoint.sh`: `--no-access-log` is present.
- There is no `--forwarded-allow-ips` or `--proxy-headers`, and no FORWARDED_ALLOW_IPS anywhere in docker/.
- `Caddyfile` uses `reverse_proxy autotester:8000`, which sends X-Forwarded-For and X-Forwarded-Proto.
- uvicorn trusts only 127.0.0.1 by default. So behind Caddy, `request.client.host` is Caddy's container IP, and the scheme stays http.
- The 20-failures-per-address limit and the 10-signups-per-address limit therefore become one bucket for the whole team. This matches the manifest's PROPOSED-ISSUE.
- Spoofing X-Forwarded-For is not possible, because it is untrusted.
- Cookie Secure still holds behind Caddy via `hosted()` (`config.py:73-76`).
- `docker/DEPLOY.md` step 5 covers FIRST_ADMIN_EMAIL (case-insensitive, only while no admin exists), the CLI bootstrap, the accounts path and the rate limits. It does not mention the shared-proxy-address caveat. Step 8 covers `AUTOTESTER_COOKIE_SECURE=0` as the interim.
- `.auth/` is in `.gitignore:7` and in `.dockerignore:22-23` (`.auth/` and `**/.auth/`).
- `git check-ignore -v` ignores `.auth/auth.sqlite3`, `subdir/.auth/auth.sqlite3` and `.auth/auth.sqlite3-wal`.
- The default auth dir is `<repo_root>/.auth/auth.sqlite3` (`auth/db.py:25-26`).

4. SOURCE FINDINGS (each at >80% confidence, file:line opened)
- F1 (medium, beyond the literal AU27):
  - `auth/access.py:142-149` `require_may_touch` guards only Admin/CEO members.
  - A non-admin `users.manage` holder can reset the password (`accounts.py:147-151`), disable or delete any non-Admin account. That includes an account in an Admin-created custom group that holds `credentials.view` or `settings.manage`.
  - They can then sign in as that account. This is a privilege-escalation path even though AU27's wording (Admin/CEO accounts only) is met.
- F2 (medium):
  - `ui/credential_guard.py:46-51` `refuse_foreign_key` accepts any key that starts with the slug-derived prefix.
  - The slug is the creator's free choice (`helpers.py:59`, `^[a-z][a-z0-9-]*$`). The default Developer group holds `project.create` plus `credentials.edit@own`.
  - I ran `key_namespace`: slug `anthropic` gives `ANTHROPIC_`, `http` gives `HTTP_`, `ld` gives `LD_`, `node` gives `NODE_`.
  - So `ANTHROPIC_BASE_URL`, `HTTP_PROXY`, `LD_PRELOAD` and `NODE_OPTIONS` pass the gate. Only `PROVIDER_KEYS` and `AUTOTESTER_*` are blocked.
  - `core/env.py:64-68` `load_repo_env` copies every .env key into `os.environ` at the next start. Result: the provider API key can be sent to an attacker URL, or code injected, after a restart.
- F3 (low): the same function lets hyphenated slugs overlap, e.g. `alpha` may claim `ALPHA_BETA_*`. Only keys already declared by another project are protected (lines 55-58).
- F4 (low):
  - `routes_auth.py:53-57`: `blocked()`, `authenticate()` and `record_failure()` are separate steps, and the handler runs in the threadpool.
  - Parallel requests can all pass the check, so the 5-per-account limit can be overshot by the in-flight count.
- F5 (low, AU22 literal):
  - `auth_middleware.py:148` audits only when `who is not None`.
  - Unauthenticated or refused POSTs, and the login/signup POSTs, get no `{email, method, path, status}` request line. Login does get action lines (`routes_auth.py:58,61`).
  - The login-failure line records the normalized attempted email. A password containing `@` and `.` typed into the email field would be logged.
- F6 (low): `auth/db.py:100-104,124` sets the `.auth` dir and file to 0700/0600 only after creation, so there is a tiny window. `.work/audit.jsonl` has no chmod.

No defect found in these areas:
- SQL is parameterised everywhere (grep for f-string SQL is empty).
- The session id is 256-bit `secrets.token_urlsafe(32)` and only its SHA-256 is stored. The lookup is by hash equality, so there is no timing issue. A new id is issued at every login.
- The password length is checked before hashing (`passwords.py:30`). An unknown email still pays one verify (`passwords.py:42`).
- First-admin signup and last-admin protection run inside `BEGIN IMMEDIATE`, with the guard inside the same transaction. Signup hashes outside the lock.
- A DB error in `resolve_session` raises and gives a 500, so it fails closed. A lifespan startup exception makes uvicorn exit.
- All handlers HTML-escape dynamic values.

Questions (not defects):
- Q1: should `POST /projects/{slug}/env/url` (project.edit) be able to widen the credential-typing domains without `credentials.edit`?
- Q2: argon2 is 64 MiB per hash with up to ~40 concurrent threads, and the limiter only applies after failures. Is that memory-DoS acceptable?
- Q3: the gate passes all non-http scopes (`auth_middleware.py:121`). There is no websocket route or mount today, but a future one would bypass it.

Not run: pytest (as instructed), the browser, the Linux run.