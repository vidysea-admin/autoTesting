# Manifest — at758-759-security (Host allow-list for the UI; account-derived approvals only through the credential path)

Contract: qa/contracts/consent.md CN1, CN5, CN11 (as amended per D-068); qa/contracts/ui.md U3 (credential editor, unchanged: this unit does not change whether the env page displays values, go-live gate G4)
Authority: D-066 (Origin/CSRF on the UI; "role-based authentication is a follow-up") and D-068 (credentials = standing run approval) — Approved-by: Umesh (docs/DECISIONS.md). The Host allow-list is the rebinding half of D-066's guard; no new DECISIONS entry was written (not in the brief) and docs/ARCHITECTURE.md prose is untouched.
Goal task: T-122 / T-203 prerequisite (hosted go-live reads the same guard)
Policy-Version: proportional-verification/2026-10-06.6
Fix cycle: 0
Phase: READY
Tier: L — security/auth (Host/Origin guard on every UI request; approval coverage)
Dual check: required — security/auth trigger
Persona walk: skip (backend-only: no screen, navigation path or user-facing flow changed; a refused Host gets an empty 403)
Issues addressed: AT-758 (DNS rebinding, medium), AT-759 (account-derived row outlives its credential, medium), AT-760 (`http://localhost:8000.evil.com` accepted, low), AT-761 (duplicate Origin header, last wins, low). All four filed by the d063-grant-budget dual check (qa/verdicts/d063-grant-budget.md and .b.md).
Executor: claude-sonnet-subagent (maker role; no checker dispatched, no push, no merge)
Base: origin/master af8f3218
Branch: wave/at758-759-security (worktree D:/autoTesting/.worktrees/at758-759-security)

## Acceptance criteria (verbatim from the brief)

1. AT-758: a Host-header allow-list check in the existing origin guard (`ui/helpers.py` `origin_guard_middleware`, registered in `ui/app.py`). It runs on EVERY request, not only state-changing ones. The allowed hosts default to loopback (127.0.0.1, localhost, ::1, any port) plus the hosts of `AUTOTESTER_ALLOWED_ORIGINS`. An optional `AUTOTESTER_ALLOWED_HOSTS` env var, exact match, is for the hosted server. A disallowed Host gets 403 with no body detail.
2. AT-760: reject unparsable ports (`http://localhost:8000.evil.com` is refused).
3. AT-761: refuse when there is more than one Origin or Host header.
4. AT-759: the human fallback of `covering_approval` considers only human-granted rows; account-derived rows count only through the credential path, which re-validates the current .env and declaration. Mint a CRAWL row, remove the credential: the run is refused. A human row still covers. ADVERSARIAL is still refused.
5. Constraints: `ui/app.py` does not grow (exactly 300); `ui/helpers.py` stays <= 300; no new src modules; file <= 300 lines, function <= 50. The env page still displays values (G4 is an open human decision).

## What changed

- src/autotester/ui/helpers.py (292 lines): new `_listed(name)` (env list reader shared by the origin and host checks; `*` is never a wildcard), new `_host_allowed(host)`, `_origin_allowed` now reads `parts.port` inside its `try` (AT-760) and uses `_listed`, `_OriginGuard.__call__` runs the Host/duplicate check on every `http` request, then the D-066 Origin check on POST/PUT/PATCH/DELETE as before. A refused Host or duplicate gets `Response(status_code=403)` with an empty body. `origin_guard_middleware` keeps its name; `ui/app.py` is untouched.
- src/autotester/stages/explore_consent.py::covering_approval (133 lines): `human = [row for row in rows if not is_account_derived(row)]` feeds both `_require` fallbacks (credentials unavailable, and no declared credentials/ADVERSARIAL). `_credential_approval` still receives every row, so reuse of an account row happens only after `validate_account_scope` / `validate_account_bounds` pass against the current .env and declaration.
- tests/conftest.py (protected file: a conftest edit is an L change with a checker): one SESSION-scoped autouse fixture `_ui_test_host` sets `AUTOTESTER_ALLOWED_HOSTS=testserver` (setdefault, restored at exit), because `TestClient` names its Host `testserver` and the guard now applies to every request in the 52 test files that use it. No assertion anywhere was edited or weakened. The guard tests `monkeypatch.delenv` it to see the real default.
- tests/test_ui_origin_guard.py (209 lines, +76) and tests/test_credential_run_approval.py (300 lines, +14, exactly at the cap): new tests, written first and seen red (39 and 3 failures before the product edit).

Behaviour to know about:
- Host matching: loopback hostnames match at any port, in bare, `host:port` and `[::1]:port` forms; a Host with userinfo, a path/query/fragment, an unparsable port (`localhost:8000.evil.com`), a trailing dot, an empty value or a missing/duplicated header is refused. Hosts of `AUTOTESTER_ALLOWED_ORIGINS` (netloc, so a port in the origin must match the Host) and `AUTOTESTER_ALLOWED_HOSTS` entries match exactly after lower-casing; no wildcard. Both are read per request.
- A request with NO Host header is refused (fail closed); every browser and HTTP/1.1 client sends one.
- Only `http` scopes are guarded; the app has no websocket route (d063 verdict A scanned: none).
- The hosted server must set `AUTOTESTER_ALLOWED_HOSTS` (or list its URL in `AUTOTESTER_ALLOWED_ORIGINS`) or every request gets 403. `.env.example` and docs/plan.md row 26 (T-203) do not mention it yet.
- AT-759 consequence: an account-derived row now never covers a run the credential path refused, so a hand-written `approve` is needed to run an ADVERSARIAL kind or a project that dropped its declaration; this is what the issue asked for.

## Capability coverage (each claim -> its isolating falsification)

Method: a throwaway copy (src, tests, scripts, pyproject.toml, uv.lock) in `%TEMP%/at758-falsify-*`, OUTSIDE the worktree; one single-hunk edit per row; runner on the worktree venv with `PYTHONPATH=<copy>/src:<copy>/scripts`; original bytes restored and sha256-compared with the worktree file after each; green before, red after, green restored. Runner: scratchpad/f/runner.py (not committed; 14 rows, one pass for H/P/D rows and one for A rows after a CRLF fix in the runner itself). The worktree was never mutated.

| Criterion | capability | defender | falsifying edit | observed |
|---|---|---|---|---|
| 1 | Host check runs on every request | tests/test_ui_origin_guard.py::test_the_rebinding_repro_cannot_read_a_saved_credential_but_loopback_can | helpers.py `_OriginGuard.__call__`: `or not _host_allowed(headers["host"])` -> `or False` | before `1 passed`; after `1 failed` (the repro); restored `1 passed`, sha identical |
| 1 | loopback Host accepted | same test | `_host_allowed`: `if parts.hostname in _LOOPBACK_HOSTS:` -> `if False:` | `1 passed` -> `1 failed` -> `1 passed`, sha identical |
| 1 | hosts of AUTOTESTER_ALLOWED_ORIGINS admitted | tests/test_ui_origin_guard.py::test_hosts_of_the_allowed_origins_and_the_hosts_variable_are_added_exactly | `| set(origins)` -> `| set()` | `1 passed` -> `1 failed` -> `1 passed`, sha identical |
| 1 | AUTOTESTER_ALLOWED_HOSTS admitted, exact, no wildcard | same test | `_listed("AUTOTESTER_ALLOWED_HOSTS")` -> `set()` | `1 passed` -> `1 failed` -> `1 passed`, sha identical |
| 1 | a disallowed Host gets an empty 403 body | tests/test_ui_origin_guard.py::test_a_host_outside_the_allow_list_gets_an_empty_403_on_every_method (27 cases: 9 hosts x GET env, GET /, POST run) | `Response(status_code=403)` -> `JSONResponse({"detail": ...}, 403)` | `27 passed` -> `27 failed` -> `27 passed`, sha identical |
| 1 | userinfo / path / query Host refused | same test | the `parts.username ... or parts.path ...` clause -> `False` | `27 passed` -> `3 failed, 24 passed` (`localhost@evil.example`, `localhost/x`) -> `27 passed`, sha identical |
| 2 | Origin with an unparsable port refused | tests/test_ui_origin_guard.py::test_an_origin_with_an_unparsable_port_is_refused | `_origin_allowed`: `_ = parts.port` -> `_ = None` | `4 passed` -> `4 failed` -> `4 passed`, sha identical |
| 2 | Host with an unparsable port refused | the 27-case Host test (`localhost:8000.evil.com`) | `_host_allowed`: `_ = parts.port` -> `_ = None` | `27 passed` -> `3 failed, 24 passed` -> `27 passed`, sha identical |
| 3 | duplicate Origin refused | tests/test_ui_origin_guard.py::test_more_than_one_origin_or_host_header_is_refused | `names.count("origin") > 1` -> `> 99` | `4 passed` -> `1 failed, 3 passed` (`origin-pairs1`: evil first, loopback last, accepted before this fix) -> `4 passed`, sha identical |
| 3 | duplicate Host refused | same test | `names.count("host") != 1` -> `< 1` | `4 passed` -> `1 failed, 3 passed` (`host-pairs3`) -> `4 passed`, sha identical |
| 4 | credential removed or domain changed ends coverage | tests/test_credential_run_approval.py::test_an_account_row_stops_covering_when_its_credential_is_gone[env, domain] | explore_consent.py fallback `_require(human, ...)` -> `_require(rows, ...)` | `3 passed` -> `2 failed, 1 passed` (`[env]`, `[domain]`) -> `3 passed`, sha identical |
| 4 | declaration dropped ends coverage | same test `[declaration]` | the first-branch `_require(human, ...)` -> `_require(rows, ...)` | `3 passed` -> `1 failed` (`[declaration]`) -> `3 passed`, sha identical |
| 4 | a human row still covers | same test (final assertion) + tests/test_credential_run_approval.py::test_a_covering_human_row_wins_and_is_not_duplicated | `human = [... not is_account_derived(row)]` -> `human = []` | `4 passed` -> `3 failed, 1 passed` -> `4 passed`, sha identical |
| 4 | ADVERSARIAL still refused | tests/test_credential_run_approval.py::test_adversarial_never_gets_an_automatic_grant | core/consent.py `ACCOUNT_KINDS` gains `ApprovalKind.ADVERSARIAL` | `1 passed` -> `1 failed` -> `1 passed`, sha identical |

The AT-758 repro itself, recorded as a test: `GET /projects/demo/env` with `Host: evil.example:8000` returned 200 with the raw saved value on the base; it now returns 403 with an empty body, and loopback Hosts still return 200 with the value (unchanged display, gate G4).

Gaps stated, not hidden: no real-browser DNS-rebinding run (the guard is exercised through TestClient with the Host a rebinding page would send); no test of the middleware behind a reverse proxy; a missing Host header is refused but untested (httpx always sends one); `_listed` on a malformed `AUTOTESTER_ALLOWED_ORIGINS` entry is skipped, not tested. The two stated-by-design behaviours of AT-760 stay: any loopback port is allowed for Origin and Host.

## Verification scope

Policy-Version: proportional-verification/2026-10-06.6
Tier: L (security/auth, protected conftest edit). Base / checked state: tip of wave/at758-759-security at the manifest commit (see git log).
Affected tests / full-suite trigger: affected files only, no builder full suite. Full-suite trigger for the checker: `tests/conftest.py` (a session-scoped autouse fixture now affects every test), recorded as `full-suite trigger: conftest edit`; and the guard now applies to every UI request. Two blind checkers (Dual check) and a senior review are for the checker side; no checker was dispatched.
Metrics: start=2026-10-07 end=2026-10-07 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=14 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6

## How to verify (commands + expected)

- `uv run pytest tests/test_ui_origin_guard.py tests/test_credential_run_approval.py tests/test_consent.py` -> 141 passed
- Affected set (every `tests/test_ui_*.py`, `tests/test_ui.py`, test_coverage_wiring, test_crawl_coverage, test_crawl_coverage_bounds, test_crawl_status_surfaces, test_ensemble_honesty, test_env_loading, test_explore_error_causes, test_permission_coverage, test_source_is_a_recording, test_credential_run_approval, test_consent) -> `607 passed, 2 skipped, 1 warning in 338.62s`
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean` (before and after this manifest; run output pasted in the commit report)
- Line counts: helpers.py 292, explore_consent.py 133, app.py 300 (untouched), conftest.py 152, test_ui_origin_guard.py 209, test_credential_run_approval.py 300.

## Live browser evidence

SKIP — no screen, template or navigation path changed.

## Status: ready-for-check
Fix cycle 0. Not merged, not pushed. Dual check required (tier L, security/auth).
