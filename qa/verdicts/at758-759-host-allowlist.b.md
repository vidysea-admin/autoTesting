# Verdict B (blind dual coordinator) - at758-759-host-allowlist
Cycle checked: 0 · Commit c642dcb5 (product 2e9b3bf8) · Policy-Version: proportional-verification/2026-10-10.9 · Resume: 1 of 2 (session-limit cut; work resumed, nothing needed re-running)

## Plan
Tier L, security. All work in `git archive c642dcb5` copies under the scratchpad (a fresh extraction is identical, `diff -rq` clean); the bound worktree was never touched. Checks: 5 criteria end to end, one or more falsifications per criterion each in its own copy, raw-ASGI plus approval-path adversarial pass, step 4c diff read, affected tests, ruff, doctor. No full suite (coordinator A owns it).

VERDICT: PASS
SCOREBOARD: 5/5 criteria met, invariants not applicable (hosting HO7/HO9/HO13/HO38 and consent CN1/CN5/CN11 spot-read, hold)
TIER: L (security: request-host validation in front of the hosted UI, src/autotester/ui/helpers.py:280; protected edit tests/conftest.py)
DUAL-TRIGGER: `dual-trigger: security src/autotester/ui/helpers.py:280` is real: lines 279-282 are the Host and duplicate-header refusal.

CRITERIA (own runs, copy of c642dcb5)
- C1 MET: affected set (origin guard, credential approval, consent, hosting deploy/config, healthz) 170 passed, 1 pre-existing red (below). GET /projects/demo/env with Host evil.example:8000 -> 403, empty body; loopback -> 200. Default = loopback + hosts of ALLOWED_ORIGINS + exact ALLOWED_HOSTS; `*` is never a wildcard (test passes with the env var deleted).
- C2 MET: Origin `http://localhost:8000.evil.com` and Host `localhost:8000.evil.com` refused (4 + 3 cases).
- C3 MET: repeated Host or Origin in both orders, and a missing Host, refused (also via raw ASGI).
- C4 MET: a derived CRAWL / LIVE_CASE / READ row stops covering when the .env credential is removed, the domain re-scoped or the declaration dropped; a human row still covers; ADVERSARIAL refused (own script, 15/15 OK).
- C5 MET: ruff clean, `autotester doctor` clean (helpers.py 292, app.py 300 untouched, explore_consent.py 133), no new src module.
Wider run in the copy: tests/test_ui_*.py + test_env_loading.py = 495 passed, 1 skipped, 1 failed: `test_ui_sources.py::test_uploaded_recordings_are_gitignored` (`git check-ignore` rc 128, a git-archive copy has no .git; file untouched by the diff; environment artefact). `test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads` is red, and I reproduced it red on master 3d8f7d5a (SCHEDULE_GRACE_MINUTES and TICK_INTERVAL_S missing from .env.example): pre-existing, not this unit's.

FALSIFICATION (own copy each; green before, red after on the named assertion, no import error). Evidence: qa/evidence/at758-759-host-allowlist-b/falsify-out.txt
C1a Host check `or False` -> rebinding repro failed · C1b allow-list tail `return True` -> hosts test failed · C1c Host check only on unsafe methods -> 22 failed (GET rows) · C2a Origin `parts.port` removed -> 4 failed · C2b Host `parts.port` removed -> 3 failed · C3a `origin > 2` -> 1 failed · C3b `host == 0` -> 1 failed · C4a fallback `_require(rows` -> 2 failed · C4b no-secrets path `_require(rows` -> 1 failed · C5 helpers.py +12 lines -> doctor "file-too-long 304 > 300" (clean before).

ADVERSARIAL (question each time: can a disallowed Host or Origin read credentials or project data, or change state?). Evidence: asgi-attack-out.txt, approval-attack-out.txt in the evidence dir.
- 65 raw-ASGI cases against the real app holding a canary credential, none leaked: Host with userinfo, `#@`, `?@`, backslash, NUL, non-ASCII bytes, bracket or IPv6 forms, `127.1`, `0.0.0.0`, comma or space lists, absolute URL, `//evil`, port overflow or negative, empty, missing, duplicates (same and different value), raw `Host` casing, `:authority`, X-Forwarded-Host, Forwarded; methods GET HEAD OPTIONS TRACE PUT DELETE PATCH POST CONNECT PROPFIND; routes /healthz /docs /redoc /openapi.json / /nonexistent //, env, run and runs routes. Every bad Host got 403, empty body, no Location header.
- A websocket scope passes the guard unchecked by design, but the app has no WebSocketRoute or Mount (walked `app.routes`) and answers `websocket.close`; lifespan passes through. `user_middleware` is `[_OriginGuard]` only, so health and run-queue routes are covered, and the guard sits outside ExceptionMiddleware so error pages cannot be reached from a bad Host.
- Origin attacks from an allowed Host on POST run (port suffix, null, userinfo, backslash, non-ASCII, empty, repeated, Sec-Fetch-Site cross-site): all 403.
- Approval path: stale derived row, another project's derived row copied in, narrowed account_keys, tampered row, narrow human row beside a derived one: all refused when the credential path refuses.
- `127.0.0.1\r` and `local\thost` are accepted (strip and urlparse remove the control char); both normalise to loopback, so nothing a non-allowed host can use. Noted, not a finding.
- Fixture `_ui_test_host` does not hide default-deny: the guard tests `monkeypatch.delenv("AUTOTESTER_ALLOWED_HOSTS")` and assert 403 for `testserver`, evil hosts and the rebinding repro; C1a/C1b/C1c go red with that fixture active. `grep testserver src` is empty, so no production default.

STEP 4c: 9 files, all in the manifest "What changed". Removed lines in helpers.py are only the inlined origin-list reader and the old guard body, rebuilt with the same unsafe-method Origin gate. The one edited existing assertion (`"ships with AT-758" in guide`) was made false by this unit and is replaced by stronger asserts. Settings are read per request from process env; `ui/app.py:17` loads the repo `.env` into it. Nothing weakened.

CAPABILITY-COVERAGE: 10/10 falsifications reproduced
LIVE-BROWSER: not-applicable (no screen changed; a refused Host gets an empty 403)
ISSUES-WRITTEN: none (dual coordinator)
PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":".env.example lacks AUTOTESTER_SCHEDULE_GRACE_MINUTES and AUTOTESTER_TICK_INTERVAL_S; test_env_example_documents_every_key_the_code_reads is red on master 3d8f7d5a too (reproduced)","file":".env.example"}
PROPOSED-ISSUE: {"severity":"low","type":"hardening","title":"Duplicate Referer and Sec-Fetch-Site headers are still last-wins in origin_refusal; Host and Origin are covered","file":"src/autotester/ui/helpers.py"}
PROPOSED-ISSUE: {"severity":"low","type":"test-gap","title":"tests/test_ui_sources.py::test_uploaded_recordings_are_gitignored needs a .git and fails (rc 128) in any git-archive copy","file":"tests/test_ui_sources.py:140"}
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Every criterion held under my own runs and ten falsifications, the raw-ASGI and approval attacks found no way for a disallowed Host or Origin to read a credential or change state, and the diff removes nothing it should keep.
Metrics: start=2026-10-10T20:44Z end=2026-10-10T23:42Z wall_min=unavailable agent_min=unavailable blocked_min=unavailable suite_runs=0 repeat_runs=0 mutations=10 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
