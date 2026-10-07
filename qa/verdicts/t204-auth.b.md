# Verdict (coordinator B, blind) — t204-auth, cycle 0

Date: 2026-10-07 · Bound to D:/autoTesting · Branch wave/t204-auth, code d87b2181, manifest f7380803, base 7782df41
Policy-Version: proportional-verification/2026-10-06.6 · Cycle checked: 0 · Dual check: coordinator B (A not read)
Checked in a detached worktree `D:/autoTesting/.worktrees/t204-b` at f7380803 (removed at the end). Falsification copies under the session scratchpad, one per row.

```
VERDICT: FAIL
SCOREBOARD: 26 criteria = 20 met (AU2-AU18, AU20, AU22, AU26; AU5/AU22 doc and entrypoint clauses deferred legitimately) + 1 blocked on human gate (AU1) + 1 deferred (AU19) + 2 FAIL (AU21, AU23) + 2 pending evidence (AU24 Linux run, AU25 needs the full suite) · no-fire list: 1 of 6 violated (credential boundary), the rest hold
TIER: L (security/auth/tenancy: src/autotester/auth/*.py, ui/auth_middleware.py:100-143 gate, ui/routes_credentials.py:35 credentials.view) — dual check correct
FAILURES:
- [AU21 / no-fire "no role skips the credential boundary"] sev: high · A Developer (default group, credentials.edit@own) can write ANY key into the shared repo `.env` through `POST /projects/{own}/env/add`, including the global provider keys that AU21 reserves to settings.manage, another project's secret key, and `AUTOTESTER_APPROVAL_KEY` (the RunApproval HMAC key, R17). Reproduced by me (script `scratchpad/own/xtenant.py`): as `dev@team.test` on a project it owns, `/settings/providers` POST -> 403 but `/projects/devproj/env/add` with key=GEMINI_API_KEY -> 303 and `.env` then holds `GEMINI_API_KEY="ATTACKER"`; same for `VICTIM_PASSWORD` (a key the victim project uses) and `AUTOTESTER_APPROVAL_KEY`; `POST /projects/devproj/secrets` also declares a key that belongs to another project against the developer's own allowed domain (a later run types the victim's value into the developer's site). Cause: policy.py:72 maps `/env/add` and `/secrets` to `credentials.edit` on the project only, and `routes_credentials.py` env_add_credential/`routes_project_edit.py` build_secret_ref accept any `^[A-Z][A-Z0-9_]*$` key with no reserved or namespaced check. AU21 text: "Writing a new value needs credentials.edit on that project (or settings.manage for the global keys)". Fix direction: refuse a key outside the project's own namespace, and any key in the provider list or `AUTOTESTER_*`, from the project routes unless the caller holds settings.manage; add a test per refused class. · issue: P1
- [AU23] sev: medium · The unit creates `<root>/.auth/auth.sqlite3` (password hashes, session hashes) but `.dockerignore` has no `.auth/` rule (I read the file; it ends with the dev-session residue block and has no `auth` line) while `Dockerfile:24` is `COPY . .`. A build from a checkout that ever ran the server bakes the user store into the image. The deferral to the T-203 owner is not legitimate for this item: it is a one-line edit to a security surface this unit created, and T-203's HO1 canary names `.work/auth/users.json`, a path T-204 does not use, so that unit's test cannot catch it. · Fix: add `**/.auth/` to `.dockerignore` and a test that evaluates it (the HO1 style). · issue: P2
CAPABILITY-COVERAGE: 22/22 maker rows reproduced (21 RED with the named assertion; row 10 SURVIVES as declared; 10b RED). Rows 16 and 16b both RED. See "Falsification" for 12 extra mutants and 3 policy-row mutants that survive.
LIVE-BROWSER: D:/autoTesting/qa/evidence/browser-t204-auth-2026-10-07-checker-b/ (own browser, 127.0.0.1:8766, 4 contexts; JS errors 0; resource-load errors only for deliberate 401/403/404/400 and favicon 401)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines only, below)
EXECUTOR: claude-sonnet-subagent (manifest Executor not stated); checker: claude-sonnet-subagent
EXPLANATION: The gate, the policy table, sessions, hashing, audit and CLI all hold up under my own probes (74 routes, 19 keys, 0 mismatches, 32,550 matcher-vs-router cases, 0 disagreements). Two defects block: a role-escalation path through the project credential routes (a developer can overwrite global and cross-project credentials and the approval key), and the missing `.dockerignore` entry for the unit's own store. The full suite was NOT run in this cycle (see Full suite); it belongs to the repair check after the fix, because the fix changes the tree.
Metrics: start=2026-10-07T19:05:29+05:30 end=2026-10-07T19:50:00+05:30 wall_min=33 agent_min=140 blocked_min=12 suite_runs=0 repeat_runs=0 mutations=40 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
```

`slow:` the 45-min wall is not exceeded (blocked_min 12 = lock wait); agent_min is an estimate (four sub-checkers ran 21, 22, 30, 30 min in parallel plus the coordinator) and sits near the 135 ceiling. Mandatory checks are complete except the suite.

## 1. Check plan (derived from the contract, spec user types and the diff)

| Signal | Check | Done by |
|---|---|---|
| Auth/permissions changed (L) | authorization matrix: 19 keys x routes, holder / non-holder / unauthenticated / zero-permission | sub-checker 1 + my own probes |
| Data model: hash, session, audit, CLI | AU1-AU5, AU22-AU24 reproduced against the raw store and files | sub-checker 2 |
| Logic changed | affected tests + falsification floor + L mutants | sub-checker 3 (own copy per row) |
| UI changed, external-ui | Mode D browser walk + persona walks (admin, sub-admin/lead, developer, tester, zero-permission signup) | sub-checker 4 |
| Credential display and write paths | my own read of routes_credentials/routes_settings/routes_project_edit and a TestClient repro | me |
| Diff scope (4c) | diff 7782df41..f7380803 read; removals are the documented router and card-helper moves | me |
| Full suite (L, security/auth) | one `uv run pytest`, serialized through `.work/suite.lock` | blocked, see below |

SERIAL: the suite waits on `D:/autoTesting/.work/suite.lock`, held by `checker t203-hosting cycle 1 suite` since 19:29:29. Browser on 8766 was one sub-checker; no two ran the browser.

## 2. Per-criterion table

| AU | Verdict | Evidence (mine, re-run) |
|---|---|---|
| AU1 | BLOCKED on human gate (D-entry for argon2-cffi==25.1.0 pending Umesh); code meets the rest | raw store: `$argon2id$v=19$m=65536,t=3,p=4$`, 97 chars, distinct salts for equal passwords; canary absent from every file under the root and server logs; verify via library, dummy-hash path; median 20 unknown 0.0849 s vs 20 known-wrong 0.0861 s; 1 MB password -> 401 in 0.1 s. Row 1 RED. |
| AU2 | met | same status+body for unknown, wrong, disabled (browser and test); row 2 RED. Survivor E2 (low, below): no test pins the dummy hash. |
| AU3 | met | token_urlsafe(32), sha256 only stored, new id per login, 12 h default, clamp 1..168 (0 -> 1, -5 -> 1, abc -> 12, 100000 -> 168), disable/delete/reset/ungroup all refuse the old cookie next request; flags: HttpOnly, SameSite=Lax, Path=/, no Domain; https/hosted -> `__Host-` + Secure; XFP spoof over http gives no Secure. Rows 3, 4 RED; E3a, E3b RED. |
| AU4 | met | logout deletes the row, old cookie refused, GET -> 401/405. Row 5 RED. |
| AU5 | met in code (5/acct, 20/addr, 10 min, 429 with right password, identical 429 body, window edge 599 s blocked / 600.1 s free); `.env.example` clause deferred, legitimate (see section 4). Row 6 RED. |
| AU6 | met | zero-permission account: 403 on every one of 74 routes except waiting/logout; waiting page names an administrator, lists no users. Rows 7 RED. |
| AU7 | met | 8-thread Barrier x5 rounds: exactly one admin each; FIRST_ADMIN_EMAIL variant correct. Row 8 RED. |
| AU8 | met | actions, session revoke, audit kept, 403 for non-holders. Row 10 survives, judged below; 10b RED; E8 RED. |
| AU9 | met | all six lock-out paths return 400 and change nothing. Rows 11, E9 RED. |
| AU10 | met | union, untick, unknown key/scope refused, labelled fieldset checkboxes (browser). Rows 9, 12, E10 RED. Note: groups.manage alone reaches every permission (PROPOSED-ISSUE P5). |
| AU11 | met | seeds equal the table; edit and deletion survive restart. Row 13 RED. |
| AU12 | met | 4 groups x 5 relations. Row 14 RED. |
| AU13 | met | direct URL for an unviewable project is the 404 of a missing one (17012 vs 17020 bytes, slug only). Rows 15, E13 RED. |
| AU14 | met | 74 (method, path) pairs all have a row; an undeclared runtime route -> 403. Rows 16, 16b RED. Matcher vs router: 32,550 cases, 0 disagreements (HEAD, //, trailing slash, %2F, `..`, case). |
| AU15 | met, evidenced by me; no named test | admin and developer get the identical refusal on `/explore` (403 crawl-approval-required) and on `/run` (400 no cases); E15 (a role skipping the approval -> 202) turns the existing AT-570 test RED. Manifest says "no dedicated test": PROPOSED-ISSUE P8 (low). |
| AU16 | met | 302 with `next` / 401 JSON for every route unauthenticated; data root unchanged; `next` of `//evil`, `/\evil`, `%2F%2F`, `javascript:`, tab/newline all dropped. Rows 17, E16 RED. |
| AU17 | met | disabled flag refused hosted/non-loopback (bind read from `--host` / `UVICORN_HOST`). Row 18 RED. |
| AU18 | met for ordering; AT-760/761 deferred to the at758 branch | cross-origin POST with a valid cookie -> 403 on login, signup, logout, admin, onboard. Row 19 RED. |
| AU19 | deferred, legitimate with a condition (section 4) | not in this tree. |
| AU20 | met for startup; `.env.example` text deferred, legitimate | row 20 RED. |
| AU21 | **FAIL (write path, P1)**; display path met | display: with a sentinel in `.env`, no GET body or header holds a value for any user without credentials.view (matrix `secret_leak.py`, browser: dev/tester/lead); POSTs never echo it; settings variant RED for `show = True` (E21s). Write path: see FAILURES. Row 21 RED. |
| AU22 | met for the app; entrypoint access-log item has no owner (section 4) | 18 audit lines, two key shapes only, no canary password, cookie, query string, hash; newline/quote injection JSON-escaped. Row 22 RED; E22 survives (low). |
| AU23 | **FAIL (P2)** | store location, git-ignore (`.gitignore:7`), pydantic models, 700/600 on posix all fine; `.dockerignore` lacks `.auth/`. |
| AU24 | pending evidence (Linux run owed by the T-203 rehearsal), code half met | no top-level fcntl/pwd/grp/termios; one posix-guarded chmod (db.py:76-78); every write inside `BEGIN IMMEDIATE`; all SQL parameterised. |
| AU25 | not evidenced by a suite in this cycle | the manifest's 200 affected UI tests are the maker's; I ran the 87 auth tests inside the mutation runs (all green before each edit) but no full suite. Owed to the repair check. |
| AU26 | met | browser walk on 127.0.0.1:8766: first signup -> admin; second -> waiting page; group tick -> next click reaches home; disable -> next click is login with the same text as a wrong password; delete -> login refused; only admin cannot be disabled/deleted/demoted; HttpOnly cookie. Console: no JS errors. Persona walks written for tester, developer, lead. |

## 3. Falsification

Per-row copy, green before, red after, `autotester.__file__` confirmed to be the copy's file. All 22 maker rows reproduce as described. Row 10 (policy row for user actions made member-level) survives.

**Row 10 ruling: acceptable.** I read routes_admin.py myself: every one of the 7 handlers under `/admin/*` calls `_require(...)` as its first statement, before reading the form or touching the store (lines 46, 52, 78, 84, 105, 115, 134), so a downgraded policy row for those routes changes no behaviour (an equivalent mutant at HTTP level), and 10b with both layers removed is RED at accounts.py:152. The acceptance has a condition: other routes have ONE layer only, so their policy rows are the whole defence and no test asserts a row's key.

Extra mutants of mine (copy per mutant):
- RED: E15 AU15, E21s settings variant, E13, E9, E3a expiry, E3b lifetime, E8 reset revokes, E10 union->intersection, E16 safe_next, P4 `/run` -> project.view (caught by `test_au13_visible_without_the_action_is_403`).
- SURVIVE: **P1** POST /onboard -> member; **P2** GET /openapi.json -> member; **P3** the credentials-edit POST group -> project.view (87 auth tests green; other suites not run); **E2** skip the dummy hash; **E22** append the query string to the audit line. PROPOSED-ISSUE P3 (policy-row assertion test), P6 (E2, E22).

## 4. Rulings on the declared deferrals

| Item | Ruling | Reason |
|---|---|---|
| AU19 Host allow-list | legitimate | `ui/helpers.py` is owned by `wave/at758-759-security` (b9ce7983, AT-758/760/761, itself under check); outside this unit's files. Condition: AU19 and AU18's AT-760/761 stay OPEN, not MET, until verified on the merged head, and the Host check must run before the auth gate (`app.py` keeps the guard first). The gate alone limits the DNS-rebinding risk because the session cookie is host-scoped. |
| AU20 `.env.example` text | legitimate | HO9 lists the keys and carries a drift test over every `AUTOTESTER_*` the code reads. |
| AU5 `.env.example` constants | legitimate, low orphan | the limits are module constants, not env vars, and HO9 does not list them: amend the AU5 clause (PROPOSED-ISSUE P9). |
| AU22 `--no-access-log` in `docker/entrypoint.sh` | legitimate ownership (docker files), but ORPHAN: no HO criterion in `hosting.md` names it, master's entrypoint has no flag, and the uvicorn access log records `next` values and URLs. Needs a named owner (PROPOSED-ISSUE P4). |
| AU23 `.dockerignore` `.auth/` | **not legitimate** | see FAIL P2. |
| AU24 Linux evidence | legitimate, still pending | needs a Linux host; owner T-203 rehearsal. |

## 5. Full suite

`suite_runs=0`. Lock `D:/autoTesting/.work/suite.lock` was held from 19:29:29 by `checker t203-hosting cycle 1 suite` and still held when I stopped waiting (12+ min, `blocked_min=12`). Because the verdict is FAIL and the fix changes `routes_credentials.py`, `routes_project_edit.py`, `.dockerignore` and tests, a suite on this tree would be wasted; the repair check owes the one full suite, on the fixed tree. Deselect when it runs: `tests/test_crawl_inventory_live.py` (pre-existing hang, dispatch instruction). Full-suite trigger recorded: the unit edits `tests/conftest.py` (session-scoped autouse patch of `TestClient.request`, a protected change).

## 6. Persona walks (summary; files in the evidence directory)

- Tester: lands on the project list showing only the shared project in 1 click; no dedicated shared-with-me page exists (spec assigns it to T-197+); unshared project -> same 404 as a missing one; admin, settings, onboard, live -> 403; crafted POSTs to access/env/env-add/env-url/edit -> 403; no secret value on the env page.
- Developer: reaches its own project; env page shows "SET" only, no Show toggle, sentinel absent from source.
- Lead (sub-admin): no project assigned -> empty list, no admin links; after assignment sees exactly that project.
- Fresh signup: waiting page only, lists no users.
- No persona finding of severity high.

## 7. PROPOSED-ISSUEs (the maker mints the ids at reconcile)

```
PROPOSED-ISSUE: {"id":"P1","sev":"high","type":"security","unit":"t204-auth","criterion":"AU21","title":"A Developer can write any .env key (global provider keys, other projects' secrets, AUTOTESTER_APPROVAL_KEY) through /projects/{slug}/env/add and /secrets","evidence":"scratchpad/own/xtenant.py: dev@team.test, own project, POST /env/add key=GEMINI_API_KEY -> 303, .env has GEMINI_API_KEY=\"ATTACKER\"; /settings/providers -> 403; AUTOTESTER_APPROVAL_KEY and VICTIM_PASSWORD likewise","files":["src/autotester/auth/policy.py:72","src/autotester/ui/routes_credentials.py","src/autotester/ui/routes_project_edit.py:45"],"fix":"project routes refuse provider keys, AUTOTESTER_* and keys outside the project namespace unless settings.manage; tests per class","blocking":true}
PROPOSED-ISSUE: {"id":"P2","sev":"medium","type":"security","unit":"t204-auth","criterion":"AU23","title":".dockerignore has no .auth/ rule while Dockerfile does COPY . .","evidence":".dockerignore (no 'auth' line), Dockerfile:24","fix":"add **/.auth/ and a test evaluating the file against a planted .auth/auth.sqlite3; align the T-203 HO1 canary path (it names .work/auth/users.json)","blocking":true}
PROPOSED-ISSUE: {"id":"P3","sev":"medium","type":"test-gap","unit":"t204-auth","criterion":"AU14","title":"No test asserts a policy row's required key; policy-row mutants P1 (/onboard), P2 (/openapi.json), P3 (credentials-edit group) survive 87 auth tests","fix":"table test: for each (method, path) the rule kind and key equals an expected table","blocking":false}
PROPOSED-ISSUE: {"id":"P4","sev":"medium","type":"orphan","unit":"t203-hosting","criterion":"AU22","title":"Nobody owns disabling the uvicorn access log in docker/entrypoint.sh (hosting.md has no criterion; master has no --no-access-log)","fix":"add to HO criteria or to the T-203 brief","blocking":false}
PROPOSED-ISSUE: {"id":"P5","sev":"medium","type":"design","unit":"t204-auth","criterion":"AU10","title":"groups.manage alone, and users.manage alone, each reach every permission (self-edit a group, or self-add to Admin/CEO), though the catalogue lists them as separate keys","evidence":"matrix/escalation.py reproduces both","fix":"document as admin-equivalent in the contract, or restrict ticking a key the actor does not hold","blocking":false}
PROPOSED-ISSUE: {"id":"P6","sev":"low","type":"test-gap","unit":"t204-auth","criterion":"AU2/AU22","title":"E2 (unknown email skips the dummy hash) and E22 (audit appends the query string) survive all auth tests","fix":"call-count test on the dummy verify; a state-changing request with a query string in the audit test","blocking":false}
PROPOSED-ISSUE: {"id":"P7","sev":"medium","type":"ux-security","unit":"t204-auth","criterion":"AU25/AU26","title":"Authenticated HTML has no Cache-Control: no-store, so Back after logout re-renders signed-in content; no X-Frame-Options/CSP/nosniff; tester and lead see New project, Live view and Settings links that 403; tester can read /projects/{slug}/access (lists owner, assignee, shared-with emails) and the read-only env/edit/access pages","fix":"no-store on authenticated responses; nav filtered by authorize(); access page needs project.assign or video.share","blocking":false}
PROPOSED-ISSUE: {"id":"P8","sev":"low","type":"test-gap","unit":"t204-auth","criterion":"AU15","title":"No test named for AU15 (admin gets the same approval refusal as a developer)","fix":"parity test","blocking":false}
PROPOSED-ISSUE: {"id":"P9","sev":"low","type":"contract","unit":"t204-auth","criterion":"AU5","title":"AU5 asks for the rate-limit constants in .env.example but they are module constants and HO9 does not list them","fix":"amend AU5 to 'named in the module and documented in the deploy guide'","blocking":false}
PROPOSED-ISSUE: {"id":"P10","sev":"low","type":"robustness","unit":"t204-auth","criterion":"AU5/AU3","title":"Rate limiter keeps one empty deque per distinct unknown email forever (20,000 emails left 20,001 entries); signup has no rate limit; an expired session row is refused but not purged on that request; `next` has no length cap","fix":"evict empty keys; cap next at 2 KB; purge on refuse","blocking":false}
PROPOSED-ISSUE: {"id":"P11","sev":"low","type":"cli","unit":"t204-auth","criterion":"AU8","title":"`autotester auth bootstrap-admin` writes no audit row though it promotes an existing (possibly disabled) account to Admin/CEO and resets its password; without --password-stdin it hangs on Windows with stdin at /dev/null; an unwritable store gives a raw traceback","fix":"audit.record_action; non-tty guard","blocking":false}
PROPOSED-ISSUE: {"id":"P12","sev":"low","type":"a11y","unit":"t204-auth","criterion":"AU26","title":"Permission checkboxes are named only on/all/assigned/own/shared (the permission name sits in an unassociated <code>); credential, onboarding and project-edit inputs have no label association; Disable/Delete buttons identical across rows; 400 refusal pages render at the POST URL so refresh re-submits; favicon.ico gives 401/403 on every unauthenticated page (console noise)","fix":"aria-label per checkbox, label for=, post-redirect-get","blocking":false}
PROPOSED-ISSUE: {"id":"P13","sev":"low","type":"pre-existing","unit":"none","criterion":"-","title":"credential_guard refuses a case containing a real .env value, which is a guess oracle for a user without credentials.view; GET /projects/{slug}/crawls/{id}/report.xlsx returns 500 for an unknown crawl (stages/crawl_report.py:217)","fix":"separate units","blocking":false}
```

## 8. Evidence index

- Browser: `D:/autoTesting/qa/evidence/browser-t204-auth-2026-10-07-checker-b/` (report.json, 22 screenshots, persona-tester/, persona-developer/, persona-lead/).
- Scripts (session scratchpad): `own/xtenant.py`, `own/au15.py`, `matrix/{enum_routes,fuzz_match,matrix,secret_leak,escalation}.py`, `data/sc_*.py`, `t204_falsify_b.py` with `mut/row*/`.
