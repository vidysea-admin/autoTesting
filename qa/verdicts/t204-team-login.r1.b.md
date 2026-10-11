# Verdict: t204-team-login (seat B, repair check)
Cycle checked: 1
Date: 2026-10-11 · bound to D:/autoTesting · branch wave/t204-team-login head 6ea9b688 (product df1b0d57) · Repair base aa6fec2e (ancestor, verified) · Policy-Version: proportional-verification/2026-10-10.9 · Dual check: seat B

## Plan
Repair check, seat B (attack angle). Failed list: env-key class, AU27 refused-admin-action audit, advice-site guard, AU20 own origin. Read the repair diff aa6fec2e..6ea9b688 in full (6 src files, 4 test files; the master merge 0b8a26b2 brought qa/ only). Whole-unit scan: docker/entrypoint.sh and three older test files are outside the manifest "What changed" list but untouched by the repair (low). Fan-out: AU27 attacks, AU20 matrix, affected tests (one process at a time), four falsification rows; I ran the env-key attack myself. Evidence: qa/evidence/t204-team-login-r1-B/ (scripts, .out files, sub-checker notes, falsification.md, affected-tests.md).

VERDICT: FAIL
SCOREBOARD: repaired items 3/4 met (env-key class, AU27 audit, advice-site guard); AU20 not met. Untouched criteria keep their cycle-0 results.
TIER: L (security/auth/tenancy: src/autotester/core/env.py:104-114, src/autotester/ui/credential_guard.py:35-58)

FAILURES:
- [AU20] sev: medium · "the server's own origin must be an allowed one; otherwise startup raises" is not enforced for a concrete bind on a non-default port when only the bare host is listed. `auth/config.py::_check_own_origin` (read in this check) ORs `_host_allowed(name)` with `_host_allowed(name:port)`, but AU19 matches the whole Host string including the port, so the bare entry never admits the Host a client sends. Repro: `D:/autoTesting/.worktrees/t204-team-login/.venv/Scripts/python.exe qa/evidence/t204-team-login-r1-B/au20_d1_repro.py` (output au20_d1_repro.out): `--host 10.0.0.5 --port 8443` with AUTOTESTER_ALLOWED_HOSTS=10.0.0.5 gives "startup ok" while `_host_allowed('10.0.0.5:8443')` is False (same with ALLOWED_ORIGINS=https://10.0.0.5, and for the default port 8000). Every real request then gets 403. Fix direction: test only `name:port`, and the bare form only when the port is 80 or 443 (what a browser omits). issue: P1

HUMAN_GATE-REQUEST: AU20, wildcard bind. The builder does not check own origin for `0.0.0.0`, `::`, `''`, `*` (the shipped container). Clause 1 (one list key set) holds; clause 2 has no definable meaning there, and neither AU20 nor hosting HO9 names a public-origin key. The owner must pick: (1) accept "own origin is checked only when the bind names one address" and amend AU20, no new key; (2) on a wildcard bind require at least one non-loopback entry in AUTOTESTER_ALLOWED_HOSTS or an ALLOWED_ORIGINS netloc; (3) add a key such as AUTOTESTER_PUBLIC_ORIGIN that must itself be allowed, documented in .env.example. Ruling on the wildcard alone: HUMAN_GATE-REQUEST, not NOT MET. A wrong list there only locks users out (AU19 on every request, AU18, login gate and Secure cookie stay on).

## Per repaired item
- Env-key class: MET. 30 slug/key pairs through /onboard, /env/add, /secrets, /env and the delete route, plus 20 value variants (\x0b \x0c \x1c-\x1e U+0085 U+2028/9, backslash, quotes, `=`, `${}`, `export`, NUL, `#`), each followed by a second write (forces the splitlines rewrite) and a restart in a fresh subprocess: no Developer-written key or value reached os.environ. Provider keys and AUTOTESTER_* are still exported; hyphen, digit and trailing-hyphen slugs and nested namespaces (alpha / alpha-beta) are refused or contained; a corrupt project.json still reserves its namespace by directory name. Falsification row 1 red.
- AU27 last bullet: MET on every branch (user actions, group create/update/delete, last-admin 400s, held-permission and Admin-only 403s). Each writes `{ts, actor, target, action:"<x>.refused"}` plus the AU22 request line with the status. No canary password, hash, cookie or body in the file or log. Hostile targets (quote, backslash, CR, LF, U+2028, NUL, 100000 chars) stay one JSON line that parses back; max 597 bytes measured. A route-policy 403 (account lacks the route key) and a 401 write only the request line: outside the AU27 sentence ("Each refused attempt is audited under AU22 (status 403, with {actor, target, action})" sits under the grant and Admin-only rules; a missing route key is AU13/AU14). Flood: about 254 bytes per refusal (two lines), double the old 128; no rotation, low. Falsification row 2 red.
- Advice-site guard: MET. `test_no_advice_site_can_vanish_unnoticed` green; reverting the test edit goes red, and deleting the `bootstrap-admin` advice text goes red (row 3 and its converse).
- AU20: NOT MET (above). Falsification row 4: removing the call turns 3 of 8 own-origin cases red, but no case covers a bare host at a custom port.

## Attack table (env key; restart simulated; unexpected exports)
| Input | Outcome |
|---|---|
| slugs http/node/ld/ssl/requests/no/all/git/uv/litellm/bash/pythonpath/a/a1/b-/c--d + own-namespace dangerous key | accepted, key written, never exported |
| slugs anthropic/openai/gemini/google/ollama/autotester/autotester-x; a key already present in .env | 400, nothing written |
| key lowercase / fullwidth / newline / `=` / NUL / space / `export ` / bare prefix on /env/add | 400 |
| AUTOTESTER_X or ANTHROPIC_API_KEY on /env/add; provider key on /settings/providers as Developer | 403 |
| value with \x0b \x0c \x1c \x1d \x1e U+0085 U+2028 U+2029 NUL `=` `${}` `export` `#` quotes | no second key parsed, none exported |
| project.json corrupt | namespace kept, not exported |
| project.json removed (dir kept) or project dir deleted by an operator | orphan key IS exported (needs filesystem access; low) |
| value `x\` followed by a later provider-key write | later key silently not loaded (P2, pre-existing) |
| legacy hand-written out-of-namespace declaration, Developer overwrites then undeclares | value exported (P4; no route can create the declaration, E4 returned 400) |
| operator var added to .env after start under an existing project's prefix (LITELLM_*, SSL_*) | silently not exported (P5) |

## Env keys the code reads, and whether a project namespace can mask them
- AUTOTESTER_* (HOSTED, AUTH_DISABLED, COOKIE_SECURE, FIRST_ADMIN_EMAIL, AUTH_DIR, SESSION_HOURS, ALLOWED_HOSTS, ALLOWED_ORIGINS, APPROVAL_KEY, TIMEZONE, SCHEDULE_GRACE_MINUTES, TICK_INTERVAL_S, MAX_CONCURRENT_RUNS, MAX_UPLOAD_BYTES, NOVNC_URL, SLOW_MO_MS, ROOT, TEST_NO_AUTO_LOGIN): never masked (always exported; slug autotester* refused).
- ANTHROPIC_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, OLLAMA_BASE_URL, OLLAMA_MODEL, OPENAI_API_KEY: never masked; slugs refused.
- PYTEST_CURRENT_TEST: set by pytest, not from .env.
- UVICORN_HOST (auth/config.py:41): can be masked by slug `uvicorn` when set only in .env after start.
- Library variables the process may need from .env (HTTP(S)_PROXY, SSL_CERT_FILE, PLAYWRIGHT_*, *_BASE_URL, LITELLM_*): can be masked; protected only if already in the process, or already in .env when the key is written.

## Not run
Browser, network and full suite (seat A owns them). SecretStore resolution is covered by the affected tests (`browser/secrets.py` reads the file, never os.environ; test_credential_run_approval and test_ui_env_editor green). The disk-error path inside `_audit_refusal` was not triggered. POSIX env behaviour not run (Windows only).

## Affected tests
22 files, one process at a time: 412 passed, 1 skipped (POSIX permission bit), 0 failed. ruff on the changed files clean; `autotester doctor` clean. Table: affected-tests.md.

PROPOSED-ISSUE: {"severity":"medium","feature":"auth","title":"AU20 own-origin check accepts a bare host at a non-default port that no client Host can match","evidence":"auth/config.py::_check_own_origin; qa/evidence/t204-team-login-r1-B/au20_d1_repro.out"}
PROPOSED-ISSUE: {"severity":"medium","feature":"auth","title":"A project value ending in a backslash makes python-dotenv swallow every later .env line, so a provider key written afterwards is silently not loaded while Settings shows it set (env_editor._render_value round-trips only the app's own parser). Pre-existing, not in the repair diff","evidence":"qa/evidence/t204-team-login-r1-B/envkey_attack2.out E2"}
PROPOSED-ISSUE: {"severity":"low","feature":"auth","title":"AU20 'at least one set' is a raw non-empty test: ALLOWED_HOSTS='*' or ',' counts as set though _listed drops it (check_startup, pre-existing)","evidence":"au20-subchecker.md D2"}
PROPOSED-ISSUE: {"severity":"low","feature":"auth","title":"Un-declaring a legacy out-of-namespace key makes its .env value exportable again, and /env overwrites an operator value of that key. No route creates such a declaration and none exists in the repo","evidence":"envkey_attack2.out E3, E4"}
PROPOSED-ISSUE: {"severity":"low","feature":"auth","title":"A project namespace silently masks any non-server operator variable added to .env later (UVICORN_HOST, proxy, SSL_*, LITELLM_*) and a removed project.json exports its keys; document in .env.example and DEPLOY.md or warn at start. When T-202 merges, its new provider keys must join PROVIDER_KEYS","evidence":"envkey_attack.out F, C"}
PROPOSED-ISSUE: {"severity":"low","feature":"auth","title":"Refusal audit adds one 120-byte line per refusal with no rotation or cap; the AU27 line carries no status (it is on the adjacent AU22 line); raw U+2028/2029/0085 confuse a splitlines() reader (cannot forge)","evidence":"au27-subchecker.md notes 1-3"}
PROPOSED-ISSUE: {"severity":"low","feature":"auth","title":"auth/config.py::_option takes the first --host/--port while uvicorn takes the last; UVICORN_PORT is ignored","evidence":"au20-subchecker.md D3"}

CAPABILITY-COVERAGE: 4/4 repaired rows reproduced (falsification.md)
LIVE-BROWSER: not-applicable (seat A owns the browser; the changed paths are auth and env code with no rendered output)
ISSUES-WRITTEN: none (dual check)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Three of the four repaired items hold under attack: no Developer-controlled value reached the environment on any route or value shape, and the AU27 refusal audit is complete and injection-safe. AU20 is not met for a concrete bind on a non-default port with a bare-host list (reproduced), and the wildcard case needs an owner decision. The three held items show no new failure beyond cycle 0, and AU20 fails in a new way, so the no-progress stop does not apply.
Metrics: start=2026-10-11T02:18:07Z end=2026-10-11T03:08:05Z wall_min=50 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=2998 mutants=0 defects_unit=1 defects_6c=0 slow: sub-checker fan-out and affected tests 40 min
