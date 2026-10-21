# Verdict - at1390-log-scrub (coordinator B)

**Verdict:** PASS
**Cycle checked:** 0
**Policy-Version:** proportional-verification/2026-10-19.17
**Reviewed:** base c437d3a5, head aae034d2 (code 1994f61a); bound to D:/autoTesting/.worktrees/at1390-log-scrub
**Checkpoint:** qa/checkpoints/at1390-log-scrub.b.md

## Check plan (step 0)
Tier L (security: access-log scrub of share tokens and query strings; dual-trigger cited at src/autotester/ui/access_log_scrub.py:33). Logic changed -> criterion tests + falsification floor; security -> read of the changed lines + a real-uvicorn probe; no UI markup changed -> Mode D not applicable. No full suite (unit check; 6c owns it). Contract: qa/gates/entrypoint-access-log.md (Answered B), AU22 (qa/contracts/auth.md:227-231, amendment line 299), AT-1390.

## Evidence (my own runs)
- C1 verify: pytest tests/test_access_log_scrub.py tests/test_container_supervision.py tests/test_auth_deploy_files.py -> 17 passed. ruff check src tests scripts -> All checks passed.
- Deployed form: started the entrypoint form `python -m uvicorn autotester.ui.app:app --host 127.0.0.1 --port 18931` (default uvicorn log config, my PID only, stopped) and sent 9 requests. Every access line came out scrubbed with method, status and path kept: `GET /auth/login?<redacted> HTTP/1.1 200`, `GET /v/<redacted>?<redacted> 401`, `POST /v/<redacted>/request-access?<redacted> 401`, `HEAD /v/<redacted>?<redacted> 401`, `GET //v/<redacted>?<redacted> 401`, `GET /projects?<redacted> 401`, `GET /healthz? -> /healthz 200`. No request or status lost (9 requests, 9 lines).
- Install order: importing the app first, then `logging.config.dictConfig(uvicorn LOGGING_CONFIG)` keeps the filter (filters = [AccessLogScrub]), so it holds if uvicorn configures logging after import; the entrypoint form configures first, then imports (shown above).
- uvicorn 0.52.4 source read: h11/httptools/zttp impls all log `'%s - "%s %s HTTP/%s" %d'` with the target at args[2], the argument the filter rewrites.
- docker/entrypoint.sh: `git diff c437d3a5..HEAD -- docker` is empty (unchanged; launch line is `uv run uvicorn autotester.ui.app:app`).
- Diff scope (4c): 5 files, all additive (174 insertions, 0 deletions): access_log_scrub.py, app.py (+import, +1 call), test file, MAP.md row, manifest. All named in What changed. Nothing removed.
- Falsification floor (throwaway copies in D:/autoTesting/.work/tmp/at1390b; green-before in the base copy: 3 passed): (a) install call in app.py replaced by `pass` -> headline test red at test line 56 (next=/x in log); (b) `/v/` substitution removed -> headline and readability tests red; (c) query mask replaced by the raw query -> headline and readability tests red (`'/a?token=zzz&b=1' == '/a?<redacted>'`). Each fired on the named assertion, not an import error. Bound tree untouched.

## C2 judgement (reuse of core/redact.py)
Read `core/redact_escaped.py:186` `scrub_url_credentials` (re-exported by core/redact.py): it masks only credential-named params (token key secret password sig session auth code) in free text. I ran it: `/auth/login?next=/x` unchanged, `/a?token=zzz&b=1` -> `?token=[REDACTED]&b=1`, `/v/abc123` unchanged. It cannot satisfy C1 (whole query, path token), so reuse "does not fit", which C2 allows. `scrub_target` is a request-target rewrite (different rule, different input), not a second secret-redaction function; I judge it a justified separate function, not a duplicated concept. Residual design note in P2.

## Security read of the changed lines
The filter mutates record.args in place (every handler and propagated stream sees the scrubbed copy), never returns False (no record dropped), and guards tuple type and str target. uvicorn quotes the path, so `?`, `#` and `%3F` inside the path cannot smuggle a query: the first `?` is the query boundary (probe: `/nope%3Fq=1?a=b` -> `/nope%3Fq%3D1?<redacted>`). The regex searches anywhere in the path, so `//v/<tok>` and prefixed forms are covered. `/v/a%2Fb/c` leaves `/b/c` visible, but a real token cannot contain `/` (route `/v/{token}` matches one segment), so no real token leaks. No defect in the changed code.

## PROPOSED-ISSUE lines (non-blocking; no ledger rows in a dual check)
PROPOSED-ISSUE: {"sev":"low","type":"security-residual","title":"uvicorn WebSocket lines still carry the query string","detail":"uvicorn.error logs 'WebSocket /websockify?token=WSSECRET1 403' (uvicorn websockets_impl.py:280-310) on logger uvicorn.error, which the AT-1390 filter (uvicorn.access only) does not cover. Reproduced with a WS handshake carrying a query string. The app has no WebSocket routes and noVNC goes through the reverse proxy, so only a scanner or attacker supplying its own query triggers it; the line existed before D-107 too (--no-access-log never silenced it). Not part of C1 (access-log lines).","fix_direction":"also attach the filter (target at args[1]) to uvicorn.error, or log at WARNING"}
PROPOSED-ISSUE: {"sev":"low","type":"design-drift","title":"/v/ token route is hardcoded in the scrub, separate from ROUTE_POLICY","detail":"access_log_scrub.py:14 hardcodes /v/; auth/policy.py:50-51 owns the route templates. A future token-in-path route added to ROUTE_POLICY would reach the log unscrubbed.","fix_direction":"derive token-bearing segments from the route templates, or add a test that fails when a new {token} route appears"}

## Scoreboard
C1 met, C2 met. Invariants: entrypoint.sh unchanged; tests/test_container_supervision.py and tests/test_auth_deploy_files.py green; one-concept-one-place judged OK. No FAIL finding. Full suite not run (unit check; the .13-2 L-security 6c step is the maker's integration step).

VERDICT: PASS
SCOREBOARD: 2/2 criteria met, 3/3 invariants hold
TIER: L (security log redaction, src/autotester/ui/access_log_scrub.py:33)
CAPABILITY-COVERAGE: 3/3 falsifications reproduced (floor met)
LIVE-BROWSER: not-applicable (no UI markup or template changed; real-uvicorn HTTP probe run instead)
ISSUES-WRITTEN: none (dual check; 2 PROPOSED-ISSUE lines above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The filter scrubs every uvicorn access line in the CLI/entrypoint launch form and survives a later dictConfig; method, status and path are intact and all three falsifications turn the named tests red. The WebSocket line on uvicorn.error is a pre-existing, attacker-triggered residual outside the access log, recorded as a low proposal.
Metrics: start=2026-10-21T14:11:00Z end=2026-10-21T14:23:00Z wall_min=12 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=720 mutants=0 defects_unit=0 defects_6c=0
slow: falsification copies 6 min (128 MB tree copies on Windows)
