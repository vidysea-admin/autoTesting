# Manifest — at758-759-host-allowlist (Host allow-list for the hosted UI; account-derived approvals only through the credential path)

## Status: ready-for-check

**Contract:** qa/contracts/hosting.md HO7, HO9, HO13 (Origin/Host keys), HO38 (no regression); qa/contracts/consent.md CN1, CN5, CN11 (as amended per D-068); qa/contracts/ui.md U3 unchanged (the env page still displays values, gate G4 is open)
**Goal task:** T-203 follow-up / prerequisite of T-204 (login builds on this guard)
**Authority:** D-066 (Origin/CSRF guard), D-068 (credentials = standing run approval); no new DECISIONS entry (re-land of an unchanged design); ARCHITECTURE.md prose untouched
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (security: request-host validation in front of the hosted UI; protected-file edit tests/conftest.py)
Fix cycle: 0
Branch: wave/at758-759-host-allowlist · Base: master 3d8f7d5a · Source: wave/at758-759-security product commit b9ce7983 (its two checkers stopped at CONTINUE-NEEDED, cycle 0, only because the one full suite never finished; every criterion was MET and 14 falsifications held). Its qa-only commits are not carried.
Code commit under check: 2e9b3bf8
Executor: claude-sonnet-subagent (maker build subagent)
Issues addressed: AT-758 (open), AT-759 (open). The same change also closes AT-760 (unparsable Origin port) and AT-761 (repeated Host/Origin header); statuses untouched, the checker owns them.
Dual check: required
dual-trigger: security src/autotester/ui/helpers.py:280
Persona walk: skip (backend-only: no screen, navigation path or user-facing flow changed; a refused Host gets an empty 403)
Round cap: SECURITY CLASS (request-host validation in front of the hosted UI; a missed Host or Origin case exposes saved credentials, so the 2-PASS cap for non-security seams does not apply)

## Acceptance criteria (verbatim from the earlier unit's brief, as carried by the coordinator)

C1. AT-758: a Host-header allow-list check in the existing origin guard (`ui/helpers.py` `origin_guard_middleware`, registered in `ui/app.py`). It runs on EVERY request, not only state-changing ones. The allowed hosts default to loopback (127.0.0.1, localhost, ::1, any port) plus the hosts of `AUTOTESTER_ALLOWED_ORIGINS`. An optional `AUTOTESTER_ALLOWED_HOSTS` env var, exact match, is for the hosted server. A disallowed Host gets 403 with no body detail.
C2. AT-760: reject unparsable ports (`http://localhost:8000.evil.com` is refused).
C3. AT-761: refuse when there is more than one Origin or Host header.
C4. AT-759: the human fallback of `covering_approval` considers only human-granted rows; account-derived rows count only through the credential path, which re-validates the current .env and declaration. Mint a CRAWL row, remove the credential: the run is refused. A human row still covers. ADVERSARIAL is still refused.
C5. Constraints: `ui/app.py` does not grow (exactly 300); `ui/helpers.py` stays <= 300; no new src modules; file <= 300 lines, function <= 50. The env page still displays values (G4 is an open human decision).

## What changed

- `src/autotester/ui/helpers.py` (292 lines; was 253 on master): new `_listed(name)` (env list reader shared by the Origin and Host checks; `*` is never a wildcard), new `_host_allowed(host)`, `_origin_allowed` reads `parts.port` inside its `try` (AT-760) and uses `_listed`; `_OriginGuard.__call__` runs the Host and duplicate-header check on every `http` request (lines 279-280), then the D-066 Origin check on POST/PUT/PATCH/DELETE as before. A refused Host or duplicate gets `Response(status_code=403)` with an empty body. `ui/app.py` untouched (300).
- `src/autotester/stages/explore_consent.py::covering_approval` (133 lines): `human = [row for row in rows if not is_account_derived(row)]` feeds both `_require` fallbacks. `_credential_approval` still gets every row, but only after `validate_account_scope` and `validate_account_bounds` pass on the current .env and declaration.
- `tests/conftest.py` (186): the session-scoped autouse `_ui_test_host` fixture (`AUTOTESTER_ALLOWED_HOSTS=testserver`, because `TestClient` names its Host `testserver`) added beside master's `_inline_run_queue` fixture; the only conflict, resolved by keeping both. No assertion edited.
- `tests/test_ui_origin_guard.py` (230): the 76 lines of the old unit plus two userinfo Host cases (`evil.example@localhost`, `x@127.0.0.1:8000`, the test gap checker B named) and `test_a_request_with_no_host_header_is_refused` (the missing-Host gap the old manifest stated). `tests/test_credential_run_approval.py` (300): +14 lines of the old unit.
- Doc and guide pin brought in line with the code (master had written them for a release without AT-758): `.env.example` comment, `docker/DEPLOY.md` (two paragraphs now say the allow-list answers an empty 403 and that one of the two keys must be set or the proxy is refused), and `tests/test_hosting_deploy.py::test_deploy_guide_claims_only_what_the_compose_file_does`, whose assertion `"ships with AT-758" in guide` pinned the old, now false, wording; it now asserts the guide no longer says that and says "empty 403". This is the one existing assertion edited, and only because the claim it guarded became false.
- Behaviour a reader of T-204 needs: the hosted server MUST set `AUTOTESTER_ALLOWED_HOSTS` (exact, port included) or list its URL in `AUTOTESTER_ALLOWED_ORIGINS`, or every request gets 403. The compose healthcheck uses `http://localhost:8000/healthz` and Caddy's `reverse_proxy` forwards the original Host, so both still pass. A request with no Host header, a repeated Host or Origin, userinfo, a path or an unparsable port in the Host is refused. Both env lists are read per request.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L. Base / checked state: master 3d8f7d5a + 2e9b3bf8.
Affected tests / full-suite trigger: scoped files only, no builder full suite (`tests/conftest.py` fixture touches every test: `full-suite trigger: conftest edit` for the checker).
Pre-check[C1]: 2e9b3bf8 uv run pytest -p no:xdist tests/test_ui_origin_guard.py -> 87 passed, 1 warning in 2.95s (Host allow-list on every method, empty 403, rebinding repro, env lists exact, no wildcard)
Pre-check[C2]: 2e9b3bf8 uv run pytest -p no:xdist tests/test_ui_origin_guard.py -> 87 passed, 1 warning in 2.95s (same run; `test_an_origin_with_an_unparsable_port_is_refused` x4 and the `localhost:8000.evil.com` Host row)
Pre-check[C3]: 2e9b3bf8 uv run pytest -p no:xdist tests/test_ui_origin_guard.py -> 87 passed, 1 warning in 2.95s (same run; `test_more_than_one_origin_or_host_header_is_refused` x4 and the no-Host test)
Pre-check[C4]: 2e9b3bf8 uv run pytest -p no:xdist tests/test_credential_run_approval.py tests/test_consent.py -> 61 passed, 1 warning in 2.95s (credential removed, domain changed, declaration dropped each refused; human row still covers; ADVERSARIAL refused)
Pre-check[C5]: 2e9b3bf8 uv run ruff check src tests scripts; uv run autotester doctor -> All checks passed!; doctor: clean (helpers.py 292, explore_consent.py 133, app.py 300 untouched, conftest.py 186, test_ui_origin_guard.py 230, test_credential_run_approval.py 300; no new src module so `autotester map` not re-run)
Pre-check: 2e9b3bf8 uv run pytest -p no:xdist tests/test_ui_origin_guard.py tests/test_credential_run_approval.py tests/test_consent.py tests/test_hosting_deploy.py tests/test_hosting_config.py tests/test_ui_healthz.py tests/test_ui_runs.py tests/test_ui_runs_queue.py tests/test_ui_credential_safety.py tests/test_ui_runs_live_case_approval.py tests/test_ui_report.py tests/test_env_loading.py -> 1 failed, 231 passed, 1 warning in 31.13s (the one failure is `tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads`: `.env.example` lacks AUTOTESTER_SCHEDULE_GRACE_MINUTES and AUTOTESTER_TICK_INTERVAL_S, read by `stages/scheduler.py` on master since 4662f250; not this unit's, see PROPOSED-ISSUE)
Metrics: start=2026-10-11 end=2026-10-11 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=6 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9

## Falsification (throwaway copy of `git archive 2e9b3bf8` under the scratchpad, outside the worktree, since deleted; run with the worktree venv and `PYTHONPATH=<copy>/src`; original bytes restored after each; the bound tree was never touched)

| Criterion | edit in the copy | defender | before | after | restored |
|---|---|---|---|---|---|
| C1 | helpers.py `or not _host_allowed(headers["host"])` -> `or False` | `test_the_rebinding_repro_cannot_read_a_saved_credential_but_loopback_can` | 1 passed | 1 failed | 1 passed |
| C1 | helpers.py `parts.username is not None` -> `False` | `test_a_host_outside_the_allow_list_gets_an_empty_403_on_every_method` (33 cases selected) | 33 passed | 6 failed, 27 passed | 33 passed |
| C2 | helpers.py `_ = parts.port  # AT-760` -> `_ = None  # AT-760` | `test_an_origin_with_an_unparsable_port_is_refused` | 4 passed | 4 failed | 4 passed |
| C3 | helpers.py `names.count("origin") > 1` -> `> 99` | `test_more_than_one_origin_or_host_header_is_refused` | 4 passed | 1 failed, 3 passed | 4 passed |
| C4 | explore_consent.py credential-unavailable fallback `_require(human, ...)` -> `_require(rows, ...)` | `test_an_account_row_stops_covering_when_its_credential_is_gone` | 3 passed | 2 failed, 1 passed | 3 passed |
| C5 | helpers.py + 12 lines (past 300) | `uv run autotester doctor` | doctor: clean | 1 violation(s) | doctor: clean |

The AT-758 repro as a test: `GET /projects/demo/env` with `Host: evil.example:8000` returned 200 with the raw saved value on the base; it now returns 403 with an empty body, and loopback Hosts still return 200 with the value (display unchanged, gate G4).

## How to verify
- `uv run pytest -p no:xdist tests/test_ui_origin_guard.py tests/test_credential_run_approval.py tests/test_consent.py tests/test_hosting_deploy.py` -> all pass except the one pre-existing `test_env_example_documents_every_key_the_code_reads`.
- `uv run ruff check src tests scripts` -> clean; `uv run autotester doctor` -> clean in the worktree (the three `root-clutter` violations exist only in the root checkout).

## Not claimed / gaps stated
- No real-browser DNS-rebinding run and no test behind a reverse proxy (the guard is driven through `TestClient`, which sends the Host a rebinding page would). The old unit's two checkers probed a real uvicorn socket on b9ce7983; the guard code here is the same.
- The full suite is owed by the checker (conftest edit trigger). The old branch's full runs died twice for load, not for a failing guard test.
- Any loopback port is allowed for Origin and Host by design.

PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":".env.example does not document AUTOTESTER_SCHEDULE_GRACE_MINUTES and AUTOTESTER_TICK_INTERVAL_S, so tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads fails on master","file":".env.example","fix":"add the two keys with a one-line comment each (HO9)"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"Duplicate Referer and Sec-Fetch-Site headers are still last-wins in origin_refusal (only Origin and Host are refused when repeated); browsers cannot send a duplicate Referer","file":"src/autotester/ui/helpers.py","fix":"extend the names.count check to referer and sec-fetch-site"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"The Host guard ignores an absolute-form request line and accepts a tab inside Host (urlparse strips it); neither is browser-reachable","file":"src/autotester/ui/helpers.py","fix":"compare the raw Host against a stricter pattern before urlparse"}
