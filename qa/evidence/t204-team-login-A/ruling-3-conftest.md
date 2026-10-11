# Ruling 3 - does the tests/conftest.py auto-login hide an auth regression? (t204-team-login, seat A sub-checker)

Method: static only (no pytest run). Worktree .worktrees/t204-team-login at aa6fec2e, base 9c9a91f3.
Verdict: SAFE (with two minor observations, no finding of severity).

## 1. What the conftest diff does
`git diff 9c9a91f3 aa6fec2e --numstat -- tests/conftest.py` = `42 0` : additions only, zero removed/changed lines.
No existing guard/fixture in conftest was weakened.

Added (tests/conftest.py:198-228): session-scoped autouse fixture `_signed_in_test_clients`.
- Monkeypatches `starlette.testclient.TestClient.request` GLOBALLY (conftest.py:226; restored at :228).
  Every TestClient verb funnels through `.request`, so this covers `TestClient(app)` built directly in a test,
  not only clients from a conftest fixture.
- At request time (conftest.py:209) it calls `auth_login_fixture.enabled()`; if False it is a pure pass-through
  (`return original(...)`). Otherwise it ensures a session for `suite-admin@autotester.test` (admin group) in the
  current store (tests/auth_login_fixture.py:30-46) and sets both cookie names (`__Host-at_session`, `at_session`)
  on the client jar (conftest.py:218-220) before delegating.
- If a test has no AUTOTESTER_ROOT / AUTOTESTER_AUTH_DIR, it redirects the store and audit file to a suite temp dir
  for that request only (conftest.py:210-213, 222-225): never the real repo's `.auth` / `.work/audit.jsonl`.
- Opt-out: env var `AUTOTESTER_TEST_NO_AUTO_LOGIN=1`, read per request (auth_login_fixture.py:26-27), so a
  monkeypatch.setenv inside a test takes effect. The gate is ON in the app by default (AU17,
  test_ui_auth_surface.py:111-113); the auto-login does not switch the gate off, it supplies a valid session.

## 2. Who opts out
- `tests/auth_harness.py:26-31` `gate_on()` sets the env var, clears AUTH_DISABLED/HOSTED/etc, sets
  AUTOTESTER_ALLOWED_HOSTS=testserver.
- Every test in the 9 new files test_ui_auth_*.py uses `root` fixture -> `gate_on`, EXCEPT these (AST check,
  scratchpad chk.py), all of which I opened and which are pure unit/static tests that make no HTTP request:
  - test_ui_auth_cli_and_limits.py:33 (limiter unit)
  - test_ui_auth_escalation.py:294 (compares policy.ROUTE_POLICY to EXPECTED)
  - test_ui_auth_groups.py:56, :64, :187 (scope table / route-vs-policy static)
  - test_ui_auth_hardening.py:205, :220 (limiter table, dummy hash)
  - test_ui_auth_login.py:186, :197 (limiter unit)
  - test_ui_auth_survivors.py:59 (deliberately re-enables auto-login to prove it leaves the real audit file alone)
- test_ui_healthz.py: the old `client` fixture is signed in (needs settings.manage) and a NEW test
  `test_healthz_unsigned_in_gets_only_ok` (:~31-38) sets NO_AUTO_LOGIN=1 and asserts the unsigned body is exactly
  {"ok": true}.
- Pre-existing test files (everything else using TestClient: test_ui*.py, test_permission_coverage.py, etc.)
  do NOT opt out, correctly: none of them asserted the app's own login gate, because the gate did not exist
  before T-204. Grep of non-auth test files for `/auth/`, `at_session`, `AUTH_DISABLED`, `auth_middleware` finds only
  test_explore_login_bypass.py:138 (a target-site 401 fixture string) and test_hosting_deploy.py:111 (a file-list
  string): unrelated. The only 401 assertion outside the new auth tests is test_ui_error_page_headers.py:92 on a
  throwaway FastAPI app (not the real app): unaffected.

So every test that asserts an unauthenticated refusal of THIS app's gate lives in a new test_ui_auth_* file (or the
new healthz test) and opts out through gate_on / the env var. Nothing that "should require 401/302/403" was
pre-existing, so nothing can have been silently turned green by the login.

## 3. Host / Origin guards and test_permission_coverage
- Order: the D-066 Origin guard (and Host allow-list) runs BEFORE the login gate (auth_middleware.py docstring
  lines 1-6; asserted by test_ui_auth_surface.py:131-135 `test_au18_guard_runs_before_the_login_gate`, unsigned client).
- tests/test_ui_origin_guard.py and tests/test_ui_auth_host_and_consent.py: the former is unchanged by the diff
  (not in `--stat`); its 403 assertions (:60, :75, :105-136, :163-210) are guard refusals. With a valid session
  cookie injected, a 403 can only come from the guard, never from the gate: the auto-login makes those tests
  STRICTER (it removes the possibility that a gate 401/redirect satisfies the assertion), and the positive
  branches (e.g. :172-173 loopback 200 + credential visible, :183-191 allowed host 200) need the session.
  The raw-ASGI test at :219-230 does not use TestClient. They remain red if the guard is removed.
  The Host/Origin guards are independent of the cookie, so injecting one cannot mask a guard regression.
- test_ui_auth_host_and_consent.py uses gate_on via `root` and its own `_at()` helper (TestClient with base_url,
  :30); auto-login is off there, and it logs in via the real route, e.g. :52-65 compares signed-in cookie under
  listed vs foreign Host.
- tests/test_permission_coverage.py: unchanged, and it is a coverage-arithmetic test (compute_coverage,
  coverage_rows, export_crawl_excel) over schema objects; its one TestClient use is a UI report page and
  asserts nothing about login. Not affected.

## 4. Falsification by reasoning (gate disabled for non-logged-in clients)
Would turn red (opt-out clients, unsigned):
1. test_ui_auth_surface.py:48-63 `test_au16_only_the_public_set_answers_unsigned_in`: loops every non-public route,
   asserts 401 JSON / 302 to /auth/login?next=/ for an unsigned client; with the gate gone it gets 200 -> red.
2. test_ui_auth_surface.py:111-113 `test_au17_gate_is_on_by_default`: `client().get("/")` must be 401 -> red.
3. test_ui_healthz.py new unsigned test + test_ui_auth_surface.py:131-135 (guard-before-gate): the first asserts the
   exact body {"ok": true}; the detail is for settings.manage only, so a gateless app would leak the detail -> red.
Would a refusal-named test stay green with the gate removed? Searched: none found. Tests that stay green
without the gate are the guard tests (they test the guard) and tests that mean to be signed in.

The one place auto-login could in principle shadow a refusal is a NEW auth test that forgets gate_on: the AST check
above shows the only gate_on-less functions are pure unit tests, so none.

## 5. Policy: is the conftest edit "protected"/weakening?
Additions only (0 deletions). No removed or weakened guard line to quote. The new fixture is test-support; it does
not touch any conftest guard. It is session-autouse and global, so new TestClient-based tests added LATER without
`gate_on` silently run as admin: a standing hazard, not a present defect. Suggested hardening (optional): assert in
a meta-test that every test_ui_auth_* test requiring a refusal declares `root`.

## Side observations (not conftest)
- test_ui_env_editor.py and test_ui_project_intake.py were edited (5/5 and 4/4 lines): key/slug renames
  (ERP_TENANT_ID -> DEMO_ERP_TENANT_ID; SHARED_PASSWORD -> ALPHA_BETA_PASSWORD with slug beta -> alpha-beta).
  Cause: new AU21 `refuse_foreign_key` (src/autotester/ui/routes_project_edit.py diff: `refuse_foreign_key(project,
  ref.key)`). Assertions unchanged in meaning; the intake test still proves "an unset key owned by another project
  cannot be redeclared" because ALPHA_BETA_ is a legitimate prefix for alpha too. Not weakening, not a conftest issue.
- test_ui_healthz.py `client` fixture now sets AUTOTESTER_ROOT to a scratch dir (isolation, fine).
