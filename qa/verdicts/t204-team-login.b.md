# Verdict (seat B, blind dual check) - t204-team-login
Cycle checked: 0
Resume: 1 of 2 (the first dispatch ended before its sub-checker reports arrived; those reports were then collected from the sub-checkers' own transcripts)
Head checked: aa6fec2e (verified with `git rev-parse`; worktree clean) · product sha 5e0c4b0b · base 9c9a91f3
Policy-Version: proportional-verification/2026-10-10.9 · Dual check, seat B · Date: 2026-10-11
Seat A material was not read (no `t204-team-login.a.*`, no `t204-team-login-A`).

## Plan (step 0)
Tier L, auth class. Four read-only Sonnet sub-checkers, run in parallel, each in its own scratch data dir:
1. unauthenticated reach, CSRF/Origin/Host, open redirect, injection
2. session, password, rate limit, privilege, first admin, auth-disabled mode, audit
3. fresh re-run of AU1-AU25 and AU27 verify commands, plus falsification in copies
4. diff scope (4c), ruff/doctor/lock, deploy files, source read

I reproduced by hand every item I rule FAIL on (`qa/evidence/t204-team-login-B/own/`). Not run here (seat A's, or not mine): the full suite, the browser, AU24 (Linux run) and AU26 (browser walk).

VERDICT: FAIL
SCOREBOARD: 24/25 judged criteria met (AU24 and AU26 not mine). Not met: AU27. AU21 is met as worded, but see F1 below, which is a blocking security defect in the changed code.
TIER: L (security/auth/tenancy; dual-trigger auth, src/autotester/auth/accounts.py:96, src/autotester/ui/auth_middleware.py:114)

## FAILURES (blocking, each reproduced by me)
- [F1] sev: high · `src/autotester/ui/credential_guard.py:46-51` `refuse_foreign_key` admits any key that starts with the namespace derived from the project slug. The slug is the creator's free choice. The default Developer group holds `project.create` and `credentials.edit@own`, so a Developer can write server-wide environment keys into the shared `.env` without `settings.manage` or `credentials.view`.
  - Reproduction: `own/repro.py`, as a Developer (default group), `POST /onboard` with `credential_key`:
    - slug `anthropic` and key `ANTHROPIC_BASE_URL` -> 303, key present in `.env`
    - slug `http` and key `HTTP_PROXY` -> 303, written
    - slug `node` and key `NODE_OPTIONS` -> 303, written
    - slug `ld` and key `LD_PRELOAD` -> 303, written
    - control `ANTHROPIC_API_KEY` -> 403
  - Why it blocks: `core/env.py:64-68` `load_repo_env` copies unset `.env` keys into the process environment at the next start. A base-URL or proxy key pointed at an attacker sends the server's provider API key to them. That is a Developer extracting a credential only `credentials.view` (Admin) may see (D-072 #5, AU21 purpose, no-fire "no role that skips the credential boundary"). It also sidesteps AU21's "`settings.manage` for the global keys".
  - Why it is judged against the code and not a wording clause: the gate was added by this unit to stop exactly this class (its docstring: "must not be a server-wide key"), and its deny-list stops at `PROVIDER_KEYS` and `AUTOTESTER_*`.
  - Fix direction: stop relying on the slug-derived prefix alone. Reserve slugs that collide with provider or OS prefixes, or require a fixed marker such as `PROJECT_<NS>_`. Also add `*_BASE_URL`, `*_PROXY` and `NODE_*` style names to the refusal.
- [F2] AU27, last bullet · sev: medium · "Each refused attempt is audited under AU22 (status 403, with `{actor, target, action}`)". A refused escalation writes only the request line, with no `{actor, target, action}` line. `src/autotester/ui/routes_admin.py:76-78` (`except _REFUSED: return _users_page(...)`) returns before `audit.record_action` at line 79.
  - Reproduction: `own/repro_audit.py`. An `Ops` account holding `users.manage` and `groups.manage` tried (1) resetting the Admin's password and (2) ticking `settings.manage` into its own group. Both got 403. The new audit lines were exactly `{email: ops, method: POST, path: /admin/users/{user_id}/{action}, status: 403}` and `{... /admin/groups/{group_id}, status: 403}`. Lines carrying `action`/`target`: 0.
  - The verify sub-checker's probe agreed (`verify/probe_refused_audit.py`).
  - No test pins this clause.
  - Fix direction: record `actor`, `target` and `action` on the refusal path as well.

## Rulings requested by the coordinator
- (a) credential_guard slug prefix against AU21: FAIL ground F1. The wording of AU21 ("needs `credentials.edit` on that project") is met, so I do not fail AU21's criterion line. I fail it as a security defect in changed code under the reviewer-scope rule.
- (b) A `users.manage` non-admin resetting the password of a non-Admin account that holds more permissions:
  - Reproduced in `own/repro.py`. The Ops account with `users.manage` reset a `settings.manage` account's password (303) and then logged in as it, reaching `/settings/providers` (200) where Ops gets 403.
  - AU27 as worded protects only Admin/CEO targets ("reset the password of an account that is in Admin/CEO"). AU8 says a `users.manage` holder may reset any account, and an Admin chose to delegate that power. So it is NOT a FAIL against the contract text.
  - It does defeat the intent of "grant only what you hold". PROPOSED-ISSUE P1, medium: the owner may want "may touch only accounts whose effective set is a subset of yours".
- (c) AU27 refused-attempt audit: FAIL, F2.
- (d) The manifest's "150 passed" for the AU25 five-file command: those files hold 56 tests. 55 passed and 1 skipped (a POSIX permission-bit test on Windows). The count claim is wrong, but the check passes. A wrong test count in a manifest is wording or evidence hygiene, so a low row (P8), not a FAIL.
- (e) Pre-check lines labelled with sha 5e0c4b0b while runs were on 3a9a5b02: I reused none and re-ran every verify command (all green). Low row (P9), not a FAIL.

## Per-criterion (fresh re-run on aa6fec2e, one falsification each, all killed)
Re-run: 249 passed (10 auth files plus the origin-guard file, 342 s) · 46 passed (permission coverage, credential run approval, env loading) · 55 passed and 1 skipped (AU25 files). Every `-k` collected at least one test.

| AU | Result | Mutant that killed it |
|---|---|---|
| AU1 | met | `passwords.py:15` memory_cost lowered. `pyproject.toml` and `uv.lock` pin `argon2-cffi==25.1.0` (read directly). Stored hash is argon2id m=65536,t=3,p=4 with a per-user salt; canary absent from the store, DEBUG log capture, audit file and 27 responses. |
| AU2 | met | `accounts.py:96` disabled check dropped. Timing, n=25 each, median ms: unknown 113.3, wrong 112.6, disabled 112.1 / 110.7, invalid 113.1. Status and body identical. |
| AU3 | met | `routes_auth.py:36` HttpOnly off; `sessions.py:65` expiry check dropped. Flags, `__Host-` and Secure when hosted, fixation, tamper variants and revocation observed. |
| AU4 | met | `sessions.py:84` |
| AU5 | met | `routes_auth.py:53` check removed; `ratelimit.py:54` |
| AU6 | met | `passwords.py:23` |
| AU7 | met | `config.py:51` |
| AU8 | met | `routes_admin.py:67` |
| AU9 | met | `db.py:158` and `db.py:157` |
| AU10 | met | `sessions.py:76` |
| AU11 | met | `db.py:89` |
| AU12 | met | `access.py:29` |
| AU13 | met | `access.py:68` |
| AU14 | met | `policy.py:44` and `auth_middleware.py:91`. All 67 openapi routes have a policy row. |
| AU15 | met | `routes_crawls.py:255` |
| AU16 | met | `auth_middleware.py:81` and `:51` |
| AU17 | met | `config.py:40` |
| AU18 | met | `helpers.py:211` (non-numeric Origin port). The repeated-Origin mutant `helpers.py:279` is killed only by `tests/test_ui_origin_guard.py`. |
| AU19 | met | `helpers.py:231` |
| AU20 | met | `config.py:68` |
| AU21 | met as worded (see F1) | `routes_credentials.py:60`, `routes_settings.py:37` and `:41` |
| AU22 | met | `auth_middleware.py:149` |
| AU23 | met | `.dockerignore:23`. `.auth/` is in `.gitignore:7`; `check-ignore` ignores `.auth/*`. |
| AU24, AU26 | not judged (not mine) | |
| AU25 | met | `access.py:42` |
| AU27 | NOT MET | F2. Grants, admin-only set and last-admin protection all hold. `access.py:114` and `:159` killed. |

Survivors beyond the floor are test gaps, listed as low P5-P7:
- the AU3 session lifetime (`sessions.py:45`, x100)
- the AU5 literal limit (`ratelimit.py:18`, 5 -> 50)
- the AU11 default grant table (`defaults.py:17`)

## Attack families (what was run, what came back)
- Unauthenticated reach: PASS.
  - About 14,850 requests in loopback and hosted modes; 116 concrete paths x 8 methods x 2 Accept values.
  - Every non-public request got 302 `/auth/login?next=` or 401, with no leak.
  - About 70 path, header and Host variants (case, trailing slash, `//`, `%2f`, `%2e%2e`, `%00`, backslash, `;`, `.env`, `.auth` and video traversal) were refused the same way.
  - Refused requests changed no file under the data root.
  - Unauthenticated `/healthz` returns exactly `{"ok":true}`.
  - No Mount, StaticFiles or WebSocket route exists.
  - Routes missing a policy row: none, in either direction. A fuzz of 2,201 combinations found no template mismatch.
- Zero-permission account: only `/auth/waiting`, logout and the public set answer; every other route is 403, or 405 where no handler exists.
- CSRF/Origin/Host: PASS.
  - Across 31 unsafe routes in both modes, cross-site, null, double, non-numeric-port, `*`, Referer-only and text/plain Origin variants were all 403.
  - A foreign Host leaked no sentinel.
  - Missing Origin and Referer is allowed (O3, by `helpers.py:261-263`; SameSite=Lax). This is not a miss under AU18.
- Open redirect: PASS. 39 `next` values all ended as `/` or a same-site path.
- Injection: PASS. 240 page views; payloads escaped everywhere.
- Session: PASS.
  - Cookie flags correct.
  - Fixation: a preset id is never adopted, and each login issues a new one.
  - Logout deletes the server-side row; GET logout is 405.
  - Tampered, truncated, 100 KB and unicode cookies give 401.
  - Disable, group change and reset take effect on the next request.
  - Sessions survive a restart.
- Password handling: PASS.
  - A 1 MB field is bounded at 1024 KB per field by Starlette: +5 MB peak working set, 0.12 s.
  - A 50 MB field is rejected in 0.03 s.
  - Unicode lookalike emails create distinct accounts (P11, low).
  - A cheap legacy hash is a 16.5 ms timing oracle (P12, info; no such hashes exist today).
- Rate limit:
  - Constants are 5 per account, 20 per address, 10 signups per address, 600 s.
  - The limiter keys on `request.client.host`. Spoofed XFF/X-Real-IP/Forwarded is ignored by default.
  - Shipped entrypoint has no `--forwarded-allow-ips`, and Caddy forwards XFF without uvicorn trusting it. So behind compose every client shares the Caddy address. 21 failures by anyone return 429 for everyone, admin included, for about 10 minutes (the lock expires at t+599..601 s). Reproduced in-process with a fixed client address.
  - If a deployer sets `FORWARDED_ALLOW_IPS=*`, varied XFF bypasses the limit (40 failures, no 429).
  - Both are PROPOSED-ISSUE P2. AU5 as worded is met.
- Privilege: PASS for grants.
  - Admin routes as Sub-admin, Developer, Tester and no-group users: 403 or 404, nothing stored.
  - IDOR and slug probes were refused, and mass-assignment extras were ignored.
  - AU27 grant refusals all gave 403.
  - AU9 held in all seven forms.
  - Findings: F1, F2, P1, and P3 (a non-admin `users.manage` holder can rename an Admin's display name, `accounts.py:154-159`).
- First admin: PASS.
  - Local: the first signup is admin; 10 trials of 2 concurrent signups gave exactly one admin.
  - Hosted with the variable set: only that address is promoted; 6 trials of 4 concurrent signups gave exactly one admin. Case variants work.
  - Hosted and unset or blank: nobody promoted, and exactly one startup warning.
  - CLI: nothing printed that should not be; `--password X` is a usage error that does not echo.
  - Whoever signs up first with the fixed address becomes admin, with no email verification. This is by design (D-074 d); noted as P10.
- Auth-disabled mode AU17: refused for `HOSTED=1`, `UVICORN_HOST=0.0.0.0` and `--host` forms. The builder's `bind_host()` flag is confirmed: gunicorn-style, hypercorn or `uvicorn.run(host=)` binds look like loopback, and then `AUTOTESTER_AUTH_DISABLED=1` is honoured with anonymous 200 on admin pages. The shipped entrypoint passes `--host` in argv, so it is caught there (P4).
- Audit:
  - Unauthenticated state-changing requests wrote 0 lines (consistent with AU16).
  - Lines hold no query, body, cookie, password or hash.
  - Injection characters in emails are escaped; all 52 lines were valid JSON.
  - Login and signup POSTs write action lines only; 400 and 429 refusals leave no trace.
- Diff scope (4c): nothing required was deleted or renamed.
  - Moved: `_latest_run_status`, `_project_card`, `_portfolio_stats` and the router list into `ui/project_view.py` and `ui/routers.py`. No route dropped; exactly 15 auth/admin routes added.
  - No assertion weakened and no skip or xfail added.
  - `uv.lock` adds only argon2-cffi 25.1.0 and argon2-cffi-bindings 26.1.0 (transitive, unpinned).
  - `conftest.py` auto-login is switched off by `AUTOTESTER_TEST_NO_AUTO_LOGIN`; no `src` file reads it; no header or query bypass exists in `auth_middleware.py`.
  - Lint: `ruff` clean, `autotester doctor` clean, `uv lock --check` -> "Resolved 89 packages". Every schema model carries `extra="forbid"`.

## PROPOSED-ISSUE (no ledger rows written)
PROPOSED-ISSUE: {"severity":"high","type":"security","title":"credential_guard.refuse_foreign_key admits server-wide env keys via a slug-chosen prefix (slug 'anthropic' writes ANTHROPIC_BASE_URL, 'http' HTTP_PROXY, 'node' NODE_OPTIONS, 'ld' LD_PRELOAD into the shared .env); a Developer (project.create + credentials.edit@own) can redirect the provider key without credentials.view or settings.manage","file":"src/autotester/ui/credential_guard.py:46","fix":"reserve slugs or use a fixed marker prefix; deny *_BASE_URL, *_PROXY, NODE_*, LD_* and any key an existing process env var uses"}
PROPOSED-ISSUE: {"severity":"medium","type":"security","title":"AU27 refused attempts are audited only as a request line; no {actor,target,action} line (routes_admin.py:76-78 returns before audit.record_action)","file":"src/autotester/ui/routes_admin.py:76","fix":"record the refusal with actor, target, action and status 403; add a test that pins it"}
PROPOSED-ISSUE (P1): {"severity":"medium","type":"hardening","title":"A non-admin users.manage holder can reset the password of, then log in as, a non-Admin account that holds more permissions (settings.manage, credentials.edit); contract wording protects only Admin/CEO","file":"src/autotester/auth/accounts.py:147","fix":"owner decision: restrict reset/disable/delete to targets whose effective set is a subset of the caller's"}
PROPOSED-ISSUE (P2): {"severity":"medium","type":"hardening","title":"Per-address limits key on request.client.host; behind the compose Caddy proxy 21 failures by anyone return 429 for every user for 10 minutes, and 10 signups lock signup; FORWARDED_ALLOW_IPS=* would let a spoofed X-Forwarded-For bypass the limit","file":"src/autotester/ui/routes_auth.py:52","fix":"decide with the owner: trust the proxy hop only (set forwarded-allow-ips to the proxy network) and key on the forwarded client; document it in DEPLOY.md"}
PROPOSED-ISSUE (P3): {"severity":"low","type":"hardening","title":"A groups.manage holder who is not Admin can delete the default Tester group or untick every permission from Developer and Sub-admin (AU27 limits only additions); a users.manage holder can rename an Admin's display name","file":"src/autotester/auth/groups.py","fix":"owner decision: protect default groups from non-Admin edits"}
PROPOSED-ISSUE (P4): {"severity":"low","type":"hardening","title":"bind_host() reads sys.argv and UVICORN_HOST only (gunicorn, hypercorn, fastapi run, uvicorn.run(host=) look like loopback), so AUTH_DISABLED and first-signup-admin apply on a non-loopback bind","file":"src/autotester/auth/config.py:25","fix":"read the bound socket, or require AUTOTESTER_HOSTED=1 for any non-dev start"}
PROPOSED-ISSUE (P5): {"severity":"low","type":"test-gap","title":"AU3 absolute session lifetime and AU5 literal limits (5 per account, 20 per address) are not pinned by any test (mutants x100 and 5->50 survive)","file":"tests/test_ui_auth_login.py","fix":"assert expires_at - created_at <= 12 h by default and the literal limit values"}
PROPOSED-ISSUE (P6): {"severity":"low","type":"test-gap","title":"AU11 default grant table not asserted (dropping COMMENT_CREATE from the shared read set survives); AU18 repeated-Origin refusal is pinned only in tests/test_ui_origin_guard.py","file":"tests/test_ui_auth_groups.py","fix":"table-drive the four default groups against the contract table"}
PROPOSED-ISSUE (P7): {"severity":"low","type":"hardening","title":"Public-route templates compile with ^...$ (policy.py:87), so /auth/login%0a, /auth/signup%0a and /healthz%0a reach the public handlers (POST writes a login-failed audit line); AU16 says exactly","file":"src/autotester/auth/policy.py:87","fix":"use fullmatch or \\Z"}
PROPOSED-ISSUE (P8): {"severity":"low","type":"wording","title":"Manifest says 150 passed for the AU25 five-file command; the files hold 56 tests (55 passed, 1 skipped)","file":"qa/manifests/t204-team-login.md","fix":"correct the count"}
PROPOSED-ISSUE (P9): {"severity":"low","type":"wording","title":"Pre-check lines carry sha 5e0c4b0b but most runs were on 3a9a5b02","file":"qa/manifests/t204-team-login.md","fix":"stamp the sha actually run"}
PROPOSED-ISSUE (P10): {"severity":"low","type":"hardening","title":"Whoever first signs up with AUTOTESTER_FIRST_ADMIN_EMAIL becomes Admin with no proof of owning the address; also unicode-lookalike emails create distinct accounts, a 99999999999999999999 id on /admin returns 500, WebSocket scopes skip both middlewares (future noVNC route), the audit file is not owner-only, and HEAD on /healthz is 405","file":"src/autotester/auth/accounts.py","fix":"set the variable only to an address the owner controls; handle the id overflow; add a gate for any future WebSocket route"}

## Blockers and process
Not blocked. No process left running. Scratch dirs `t204b-*` deleted (own, audit, session, unauth, verify). The sub-checkers could not write their `summary.md` files; I extracted each final report from its transcript and saved it as `summary.md` in its evidence folder.

EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
Metrics: start=2026-10-11T00:58Z end=2026-10-11T01:28Z wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=38 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1800 mutants=38 defects_unit=2 defects_6c=0
