# Verdict (coordinator A, blind) — t204-auth, cycle 0

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-06.6
Bound to: D:/autoTesting (worktree .worktrees/t204-auth, branch wave/t204-auth, code d87b2181, manifest f7380803, base 7782df41)
Dual check: coordinator A. Coordinator B's verdict, checkpoint and evidence were not read. A PASS or FAIL here has no side effects (no ledger rows, no goal change, no merge, no push).

VERDICT: FAIL
SCOREBOARD: 20/26 criteria met in this unit's file scope (AU2 AU4-AU18 AU20 AU22 AU23 AU26 plus AU5 code); 2 FAIL (AU3, AU21); 1 blocked on human gate (AU1); 2 owned elsewhere and still open (AU19, AU24); 1 not run by A (AU25, suite pending). 0 invariants violated except as listed under the No-fire list below.
TIER: L (security/auth/tenancy; dual check). Cited: src/autotester/ui/auth_middleware.py:29-38 (session cookie), src/autotester/auth/sessions.py, src/autotester/auth/passwords.py; tests/conftest.py:143-176 is a protected change.

## 0. Check plan (built from the diff, contract, spec user types)

| Signal | Check | How |
|---|---|---|
| Auth/session/permissions changed (L) | adversarial security review | 4 read-only Sonnet sub-checkers fanned out in one message, plus my own reads and PoCs |
| Logic changed | falsification floor, one copy per mutant | sub-checker, 22 floor rows plus 4 extra mutants |
| UI changed (login, signup, waiting, admin) | Mode D live browser, AU26 | sub-checker, Playwright MCP, own server on 127.0.0.1:8765, temp data root |
| Protected test change (conftest) | protected-change review, merge interaction with wave/at758-759-security | sub-checker |
| 4c diff scope | `git diff 7782df41..HEAD` | sub-checker plus me |
| Full suite (L security/auth, once) | one `uv run pytest` under the suite lock | NOT RUN, see section 4 |

SERIAL: full suite waits on D:/autoTesting/.work/suite.lock (held by t190-ux from before 18:34 until 19:29; re-taken by another holder at once). Not needed to reach FAIL, see section 4.

## 1. Findings that block (each carries a reproduction)

### F1. [AU21 / AU10 / No-fire: credential boundary] sev HIGH — a Developer can write ANY `.env` key through `POST /projects/{slug}/env/add`

- Code read by me: `src/autotester/ui/routes_credentials.py:136-165` (`env_add_credential`). The only checks are `build_secret_ref` (key shape), "already declared on THIS project" and `_refuse_unsafe_submission`. There is no check against keys declared by other projects, keys already in the shared repo-root `.env`, provider keys or the `AUTOTESTER_` namespace. The policy row (`auth/policy.py`, `POST /projects/{slug}/env/add` -> `_CRED` = `credentials.edit` on the project) is satisfied by a Developer on their own project.
- Reproduction (sub-checker, `scratchpad/s2/poc6.py`, output `scratchpad/s2/poc6.out`): Developer owning project `vault` POSTs `env/add` with keys `ANTHROPIC_API_KEY`, `AUTOTESTER_APPROVAL_KEY`, `AUTOTESTER_ALLOWED_ORIGINS`, `AUTOTESTER_AUTH_DISABLED`, `BETA_TOKEN` (another project's key). All five return 303 and the repo `.env` then holds `ATTACKER-<key>` for each. The same Developer on `POST /settings/providers` with the same key gets 403, so the `settings.manage` gate is bypassed.
- Why it matters: AU21 says a write needs `credentials.edit` on that project, or `settings.manage` for the global keys. A Developer can overwrite global provider keys and another project's secret, declare them as their own `SecretRef`, and (via `/env/url` allowed domains they control) send `{{SECRET:KEY}}` of another project to a host they choose. Control keys written to `.env` are loaded on the next restart by `load_repo_env`: approval key (D-018), allowed origins, and `AUTOTESTER_AUTH_DISABLED=1` (laptop case).
- Fix direction: in `/env/add` (and `/projects/{slug}/secrets`) refuse a key that is declared by another project, present in `.env` but not declared by this project, in the provider key list, or prefixed `AUTOTESTER_`; or require a per-project key prefix. Add a test (Developer writes `ANTHROPIC_API_KEY` -> 4xx and `.env` unchanged).
- Confidence: high (code line read, PoC output read, behaviour reproduced by the sub-checker; not re-run by me because it needs the full project fixture).

### F2. [AU3 / security] sev MEDIUM — the `__Host-` prefix is defeated: the plain `at_session` cookie is accepted in hosted/Secure mode

- Code read by me: `src/autotester/ui/auth_middleware.py:27-38`. `SESSION_COOKIES = ("__Host-at_session", "at_session")` and `session_token()` falls back to the plain name whenever the `__Host-` one is absent, with no check of `cookie_secure()`.
- Reproduction (sub-checker `scratchpad/s1/tests/test_poc.py::test_p8_cookie_tossing`): with `AUTOTESTER_HOSTED=1`, login sets only `__Host-at_session`. Replaying the same token under the plain `at_session` name on a fresh client returns 200.
- AU3 requires `__Host-` with `Secure`. The point of the prefix is that a sibling subdomain or a plain-HTTP injected cookie cannot plant a session (cookie tossing / forced login as the attacker). Accepting the unprefixed name removes that protection.
- Fix direction: when `cookie_secure()` is true read only the `__Host-` name (and clear the plain one); accept the plain name only in the non-Secure interim. Add a test replaying the token under the plain name in hosted mode.

### F3. [AU16 / security] sev MEDIUM — stored XSS: a group name is written unescaped into the page `<title>`

- Code read by me: `src/autotester/ui/routes_admin.py:109` and `:126` call `theme.page(group.name, body)`; `ui/theme.py` `page()` documents that the caller must pre-escape the title and writes it raw into `<title>{title} — AutoTester</title>`. `groups._clean_name` (`auth/groups.py`) rejects only control characters and length over 64.
- Reproduced by me (`scratchpad/own/poc_title_xss.py`, run against the worktree source with a temp root): an admin created a group named `</title><script>alert(1)</script>`; `GET /admin/groups/<id>` returned `<title></title><script>alert(1)</script> — AutoTester</title>` (raw script injected: True). An independent reproduction from the HTTP-surface sub-checker matches.
- Impact: script runs in the browser of any user who opens that group page, including an Admin; a `groups.manage` holder can plant it against an Admin. All other emails, display names and group names in bodies are escaped (read and probed).
- Fix direction: `escape(group.name)` in both calls. Add a test with a hostile group name.

Under the policy a security defect in changed code FAILs even when no criterion names it. F1 and F2 map to AU21 and AU3 directly. Per criterion: AU3 FAIL (F2), AU21 FAIL (F1). F3 is a security defect against the No-fire list ("no stored value / script from user input" is not listed, so it is cited as a security defect in changed code).

## 2. Per-criterion table

| AU | Result | Evidence (mine or sub-checker, falsification row in section 3) |
|---|---|---|
| AU1 | BLOCKED on human gate (D-entry naming argon2-cffi==25.1.0 pending Umesh). Code evidence MET: `$argon2id$ v=19 m=65536,t=3,p=4`, per-hash salt, canary absent from store, audit and caplog (sub-checker raw-bytes grep), length policy 10..128, needs_rehash wired | m01 RED |
| AU2 | MET. Unknown, wrong, disabled and malformed email: 401 with identical body (16,785 bytes, same hash); dummy hash verified; interleaved timing 52.4 ms known vs 54.0 ms unknown | m02 RED |
| AU3 | FAIL (F2). Everything else held: 256-bit token, only sha256 stored, bad cookie x9 refused, new id per login, disable/delete/reset/regroup effective next request, lifetime clamp 1..168 h, Secure rule | m03, m04 RED |
| AU4 | MET (POST deletes session, GET changes nothing) | m05 RED |
| AU5 | MET in code (6th attempt 429, identical body for known and unknown accounts). `.env.example` documentation of the constants is not carried by any branch, see ruling R3 | m06 RED |
| AU6 | MET. Zero-permission account: 403 on every route except waiting/logout/public (sub-checker enumerated every route, fresh login per route) | m07 RED |
| AU7 | MET. 6 threads on a barrier -> exactly one admin; env override variants (case, whitespace, plus, fullwidth) held. Design note: with the env override, anyone who knows the address and signs up first is the admin (P4-note below) | m08 RED |
| AU8 | MET per contract text (disable, enable, delete, reset, rename, regroup; audit kept; owner un-set). Note: `users.manage` can reset the last admin's password and add self to Admin (design, P5) | m09 RED (delete path) |
| AU9 | MET. Disable, delete, regroup, untick `users.manage`, delete group, `update_group(member_ids=[])`: all LastAdmin; cross-disable race with two admins -> one ok, one refused, inside one `BEGIN IMMEDIATE` | m09, m10 RED |
| AU10 | MET per contract text; unknown key or scope x3 stores nothing; labelled checkboxes in 5 fieldsets. Design: `groups.manage` can tick any key into its own group (P5) | m11, m12 RED |
| AU11 | MET (seeded once, edits and deleted default survive restart) | m13 RED |
| AU12 | MET (scope table 4 groups x 5 relations; shared != all) | m14 RED |
| AU13 | MET: 10 GET and 13 POST suffix paths byte-identical 404 for unviewable vs missing slug, HTML and JSON (sub-checker, 0 LEAK); browser walk agrees. Low: `POST /onboard` with an existing slug the caller cannot view returns 400 (P10) | m15 RED |
| AU14 | MET: policy template equals route template for every route and method, no gaps, no orphan rows; odd paths (trailing slash, `//`, `%61`, `;x`, HEAD/OPTIONS) show no bypass (mine `poc_paths.py`, S1, S2) | m16 RED |
| AU15 | MET by construction (diff touches no consent, approval or `write_policy` code; every existing consent test runs as Admin). No dedicated test, as the manifest admits (P11, low) | no row |
| AU16 | MET: public set exactly GET/POST login, GET/POST signup, GET `/healthz` (minimal body); 26 `next` payloads dropped or kept same-site; data root unchanged after refused requests | m17 RED |
| AU17 | MET (startup combinations). Note: bind detection reads `sys.argv` only (P13, low) | m18 RED |
| AU18 | MET for ordering (cross-origin POST with a valid admin cookie 403 on login, signup, logout, admin, onboard; evil Origin, `null`, evil Referer, cross-site Sec-Fetch all 403). AT-760 and AT-761 are not on this branch: reproduced here that `Origin: http://localhost:8000.evil.com` passes (203/303). Owned by wave/at758-759-security, see ruling R1 | m19 RED |
| AU19 | NOT MET in this unit; legitimate deferral, see ruling R1. Merge hazard P6 | no row |
| AU20 | MET for startup raise; docs partly on wave/t203-hosting, see ruling R3 | m20 RED |
| AU21 | FAIL (F1). Display side held: sentinel absent from 88 requests per role x 3 roles, HTML and JSON, headers included; admin sees values; env-only provider key shows Set | m21 RED |
| AU22 | MET for the app: audit holds no password, cookie, hash or query; no newline injection. Gaps: unauthenticated state-changing requests get no request line, bootstrap CLI writes no audit line (P15). Access-log disable owed, see ruling R2 | m22 RED |
| AU23 | MET for store path, gitignore, models, 700/600 on posix. `.dockerignore` entry owed, see ruling R2 | no row |
| AU24 | no POSIX-only import at module level (grep: only `ui/env_editor.py` guarded msvcrt/fcntl, pre-existing). Linux run owed to the T-203 rehearsal, see ruling R4 | no row |
| AU25 | NOT RUN by A (full suite pending, section 4). Maker's own post-rebase run: 200 passed in the 11-file UI set | no row |
| AU26 | MET with findings. Real browser (Playwright MCP, own server 127.0.0.1:8765, temp root): first signup is admin, second sees the waiting page, group tick takes effect on the next click, last-admin refusals, disable -> next click to login, enable, delete -> session dead, login refused with the AU2 text, identical failure text, Tester/Dev/Sub-admin personas, keyboard Tab/Space/Enter on checkboxes and save. 0 JS errors; non-zero console counts are provoked 401/403/404/400 and the unauthenticated `/favicon.ico` 401. Findings P8, P12 | n/a |

LIVE-BROWSER: qa/evidence not written (the bound tree is read-only for sub-checkers); evidence at C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/a2bbaa41-59b6-48f1-8ec7-8aa0d97b8a5a/scratchpad/s5/evidence/ (29 PNGs plus report.json). The uvicorn PIDs (35892 launcher, 12460 server) were started by the sub-checker and killed by PID.

## 3. Capability coverage (falsification floor, one throwaway copy per mutant)

Copies under `scratchpad/s4/m01..m22`, each green-before then red-after, single-hunk edit to a single product file, named test node only. 22 of 22 rows reproduced RED (AU1 AU2 AU3 x2 AU4 AU5 AU6 AU7 AU8/9 x2 AU10 x2 AU11 AU12 AU13 AU14 AU16 AU17 AU18 AU20 AU21 AU22). No row for AU15, AU19, AU23, AU24, AU25 (not built by this unit, or owed elsewhere) and AU26 (browser). Survival of the manifest's own row 10 is by design (second layer refuses).
Extra mutants x1-x4 (all green-before): x1 session lookup by raw token SURVIVED (87 passed; test gap), x2 rate limiter keyed on X-Forwarded-For SURVIVED (87 passed; test gap), x3 last-admin guard counting disabled admins RED (test_au9_last_admin_cannot_be_locked_out), x4 password reset not revoking sessions RED (test_au8_password_reset_revokes_sessions). The two survivors are test gaps listed under P11, not blockers on their own.
CAPABILITY-COVERAGE: 22/22 rows reproduced; 5 criteria without a row listed above.

## 4. Full suite

NOT RUN by A. Reason: `D:/autoTesting/.work/suite.lock` was held by t190-ux through 19:29 and re-taken at once; with three FAIL findings that need a code change, a suite on this tree (d87b2181) would be stale as soon as F1-F3 are fixed. Policy .7 allows one L-security suite "at most once per evidence identity": the repair checker runs it on the fixed tree. A conftest edit is a full-suite trigger: `full-suite trigger: tests/conftest.py (protected change) + wave/at758-759-security conftest interaction (P6)`. Static review of the conftest patch: no weakened assertion, restored on teardown, real `.auth/` never written, but the real repo `.work/audit.jsonl` IS written by any existing UI test that POSTs without a scratch root (P7, reproduced: the worktree already holds `.work/audit.jsonl` with 4 `suite-admin@autotester.test` lines). The caller asked for CONTINUE-NEEDED when the lock is held; I return FAIL instead because the verdict already stands on reproduced defects and the suite cannot change it. If the maker disagrees, it can re-dispatch A for the suite only after the fix.
`tests/test_crawl_inventory_live.py` was never run (nothing deselected because no suite ran).

## 5. Rulings on the declared deferrals

- R1 AU19 (and AT-760/761 inside AU18): LEGITIMATE. The Host allow-list lives in `ui/helpers.py`, which `wave/at758-759-security` owns; that branch carries `_host_allowed` and the AT-760 numeric-port fix (read from `git show wave/at758-759-security:src/autotester/ui/helpers.py`). The criterion stays open until that branch merges. Risk until then is reduced because a session cookie is host-bound, but not removed (reproduced: non-numeric-port Origin passes on this branch). Merge hazard recorded as P6: the t204 `tests/auth_harness.py:22-24` `_CLEARED` list deletes `AUTOTESTER_ALLOWED_HOSTS` in `gate_on()`; after merging with at758's session-wide `AUTOTESTER_ALLOWED_HOSTS=testserver`, 51 of the 87 new tests fail with 403 (sub-checker simulated the merge in a scratch tree; conftest textually merges clean). Removing the name from `_CLEARED` and adding a `delenv` inside `test_au20_hosted_needs_an_allow_list` makes 86 of 87 plus that one pass.
- R2 AU22 access-log disable, AU23 `.dockerignore` `.auth/`: LEGITIMATE BY FILE SCOPE (docker files belong to the hosting unit), BUT UNOWNED IN PRACTICE. I read `wave/t203-hosting` and `wave/dockerignore-secrets`: neither adds `.auth/` to `.dockerignore`, and `docker/entrypoint.sh` on `wave/t203-hosting` still runs `uvicorn ... --host 0.0.0.0 --port 8000` without an access-log flag. The Dockerfile copies the context, so `.auth/auth.sqlite3` (password hashes, live session hashes) would ship in an image built from a dev checkout. This is a merge/deploy prerequisite, not a defect in T-204's code. P7-priority issue below.
- R3 AU5 constants and AU20 documentation in `.env.example`: PARTLY. `wave/t203-hosting` documents `AUTOTESTER_HOSTED`, `_COOKIE_SECURE`, `_FIRST_ADMIN_EMAIL`, `_AUTH_DISABLED`, `_ALLOWED_HOSTS`, `_ALLOWED_ORIGINS`. It does not document the rate-limit constants (AU5) or `AUTOTESTER_SESSION_HOURS`. LEGITIMATE deferral of the file; the missing lines stay owed.
- R4 AU24 Linux run: LEGITIMATE deferral (needs the T-203 image), but AU24 cannot be MET until `qa/evidence/t204-linux-run.md` exists.

## 6. 4c diff scope

All 43 changed files are listed in the manifest or are the regenerated `docs/MAP.md`. No function, class, route, export, test or config key is deleted or renamed except the declared moves (`_latest_run_status`, `_project_card`, `_portfolio_stats` -> `ui/project_view.py`, no stale references). `uv.lock` adds only `argon2-cffi 25.1.0` and `argon2-cffi-bindings 26.1.0`; `pyproject.toml` adds exactly `argon2-cffi==25.1.0`. `ruff check src tests scripts` clean (my run, `--no-cache`). `autotester doctor` clean (my run). Manifest wording slips (low): two new routers are prepended to `ROUTERS`, not appended; `/openapi.json`, `/docs`, `/redoc` now require `settings.manage` and that is not listed; `core/paths.py` is exactly 300 lines (no headroom).

## 7. PROPOSED-ISSUE lines (the maker mints ids at reconcile; none written by A)

PROPOSED-ISSUE: {"p":"P1","sev":"high","type":"security","criterion":"AU21","title":"POST /projects/{slug}/env/add lets a credentials.edit holder write any .env key (global provider keys, other projects' keys, AUTOTESTER_* control keys)","evidence":"routes_credentials.py:136-165; poc6.out: 5 keys 303, .env poisoned; /settings/providers same key 403","fix":"refuse keys declared elsewhere, present in .env undeclared, provider keys, AUTOTESTER_ prefix; add test"}
PROPOSED-ISSUE: {"p":"P2","sev":"medium","type":"security","criterion":"AU3","title":"__Host- session cookie prefix defeated: plain at_session accepted in hosted mode","evidence":"auth_middleware.py:27-38; test_p8_cookie_tossing","fix":"hosted/Secure: read only __Host- name"}
PROPOSED-ISSUE: {"p":"P3","sev":"medium","type":"security","criterion":"AU16","title":"stored XSS: group name unescaped in page title","evidence":"routes_admin.py:109,126; poc_title_xss.py","fix":"escape(group.name); test"}
PROPOSED-ISSUE: {"p":"P4","sev":"high","type":"security","priority":"S1/S2|security","title":"deploy/merge prerequisite with no owner: .dockerignore lacks .auth/; entrypoint keeps uvicorn access log; AU5 constants and SESSION_HOURS undocumented in .env.example","evidence":"wave/t203-hosting and wave/dockerignore-secrets read; Dockerfile COPY context","fix":"assign to T-203 or a dockerignore unit; hold deploy until present"}
PROPOSED-ISSUE: {"p":"P5","sev":"medium","type":"design","criterion":"AU8/AU10","title":"users.manage and groups.manage are admin-equivalent: groups.manage can tick users.manage, settings.manage and credentials.view into its own group; users.manage can add self to Admin/CEO and reset the last admin's password (reproduced by me and two sub-checkers)","decision":"Umesh: declare them admin-equivalent in the contract, or forbid granting or touching what the actor does not hold (store functions need the actor)"}
PROPOSED-ISSUE: {"p":"P6","sev":"medium","type":"integration","title":"merge with wave/at758-759-security fails 51 of 87 auth tests: auth_harness._CLEARED removes AUTOTESTER_ALLOWED_HOSTS; test_au20 then needs its own delenv","fix":"whichever branch merges second owes the one-line fix; add to the manifest integration notes"}
PROPOSED-ISSUE: {"p":"P7","sev":"medium","type":"test-infra","title":"conftest auto-login patch redirects AUTOTESTER_AUTH_DIR but not the audit file: any existing UI test that POSTs without a scratch root appends to the real repo .work/audit.jsonl (reproduced; the worktree already has 4 lines)","fix":"honour AUTOTESTER_AUTH_DIR in audit._append, or patch the audit path in the fixture"}
PROPOSED-ISSUE: {"p":"P8","sev":"low","type":"security","title":"authenticated pages send no Cache-Control: after Sign out, Back re-renders the previous page including the admin user list","fix":"Cache-Control: no-store on authenticated responses"}
PROPOSED-ISSUE: {"p":"P9","sev":"low","type":"security","title":"open signup has no rate limit and each signup costs a 64 MiB 4-lane argon2 hash (40 signups from one client all 303); limiter dict grows without bound (200,002 keys after 200,000 unique emails); dummy hash computed lazily (first unknown-email login 0.36 s vs 0.05 s)","fix":"apply the per-address limiter to signup, drop empty deques, warm the dummy hash at startup"}
PROPOSED-ISSUE: {"p":"P10","sev":"low","type":"security","criterion":"AU13","title":"existence and key-name oracles for a Developer: POST /onboard with an existing unviewable slug returns 400; _guard_intake names keys used by other projects; /access names unknown accounts; signup duplicate message","fix":"same message and status for exists and not-visible"}
PROPOSED-ISSUE: {"p":"P11","sev":"low","type":"test-gap","title":"weak or vacuous tests: test_ui_auth_groups.py:116 asserts '1' in text; :64-68 git grep ignores return code; test_ui_auth_surface.py:157 'set' in text; :65-72 '//evil.example/' collapses to '/'; AU21 does not check prefix/length hints; AU11 compares production to its own constant; mutants x1 (raw-token session lookup) and x2 (limiter keyed on X-Forwarded-For) survive the suite; AU3 real login lifetime, AU8 project dir survives, AU9 route-level untick, AU13 sub-routes, AU15 admin-gets-same-refusal and AU22 line shape have no test","fix":"strengthen as listed"}
PROPOSED-ISSUE: {"p":"P12","sev":"low","type":"ux-a11y","criterion":"AU26","title":"Delete user has no confirmation; permission checkbox accessible names are 'on'/scope words; raw keys as labels; sidebar shows Settings/New project/Live links that 403; unauthenticated /favicon.ico 401 logs a console error; onboard form controls have no labels (pre-existing); no shared-with-me page exists yet (Group 10)","fix":"as listed"}
PROPOSED-ISSUE: {"p":"P13","sev":"low","type":"hardening","title":"AUTOTESTER_AUTH_DISABLED bind check reads sys.argv only (gunicorn -b, fastapi run, uvicorn.run(host=) would look loopback); gate passes non-http scopes through (a future noVNC websocket proxy would be ungated); login address key is request.client.host (all users share it behind a proxy without trusted forwarded headers)","fix":"document in the deploy guide; gate websocket scope when HO12 lands"}
PROPOSED-ISSUE: {"p":"P14","sev":"low","type":"wording","title":"manifest: router order wording, /docs /openapi.json /redoc gating not listed, claim '.auth/ never written' true but .work/audit.jsonl is (P7); core/paths.py exactly 300 lines","fix":"amend manifest"}
PROPOSED-ISSUE: {"p":"P15","sev":"low","type":"audit","criterion":"AU22","title":"unauthenticated state-changing requests and the bootstrap CLI write no request/audit line","fix":"record_request also for anonymous POSTs; audit line in bootstrap_admin"}
PROPOSED-ISSUE: {"p":"P16","sev":"low","type":"race","title":"authenticate reads outside a transaction: a concurrent admin reset can leave a session created before the reset surviving, and the rehash UPDATE can overwrite a freshly reset hash; login does not revoke the browser's previous session","fix":"one transaction for verify + session; rehash only if the hash is unchanged"}

## 8. Needs a human (not decided by A)

HUMAN_GATE-REQUEST: AU1 argon2-cffi==25.1.0 D-entry pending Umesh (judged "blocked on human gate"; the code passes everything else for AU1).
HUMAN_GATE-REQUEST: P5 - are `users.manage` and `groups.manage` meant to be admin-equivalent (contract text allows it), or must the store forbid granting what the actor does not hold?

EXECUTOR: manifest executor (maker); checker: claude-sonnet-subagent coordinator A (4 sub-checkers: auth core, HTTP surface, test infrastructure, browser walk, plus a falsification runner)
EXPLANATION: The code is largely sound: session forgery, fixation, disabled-user sessions, last-admin removal, the first-admin race, enumeration, timing, default-deny, the public surface and the display side of credential hiding all held under attack, and 22 of 22 falsification rows go red. It fails on three reproduced defects in the changed code: a Developer can write any `.env` key through `/env/add` (F1), the `__Host-` cookie prefix is defeated by a plain-cookie fallback (F2), and a group name is injected unescaped into a page title (F3). The full suite was not run (lock held; stale after the fixes), so the conftest change is judged by static review only.
Metrics: start=2026-10-07T19:05:37+05:30 end=2026-10-07T19:45:00+05:30 wall_min=39 agent_min=130 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=26 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
