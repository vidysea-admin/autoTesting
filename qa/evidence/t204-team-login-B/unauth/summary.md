## t204-team-login blind security check B (unauth / CSRF / redirect / injection)

**Outcome: no High, Medium or contract-level finding. Families 1-6 all PASS.** There are seven INFO/LOW observations (O1-O7 below), and none breaks an AU criterion as written.

Code under test: worktree at `aa6fec2e`. I drove the app in-process over raw ASGI, with no browser, network or pytest. I ran every family in two modes, each with a fresh scratch data root:
- `loopback` (Host `localhost:8000`).
- `hosted`: `AUTOTESTER_HOSTED=1`, `ALLOWED_HOSTS=testserver`, `ALLOWED_ORIGINS=http://testserver,https://testserver`, `COOKIE_SECURE=0`, `FIRST_ADMIN_EMAIL` set (Host `testserver`).

Scratch accounts were admin, developer (owns `alpha`), tester, sub-admin and no-group. I saved sentinel credential values for `alpha` and `beta`, plus a sentinel case title and a sentinel video file in a run, so a leak could be found by grep.

**Request count:** about 7,400 HTTP-level requests per mode, about 14,850 in total. That is roughly F1 2,891, F2 1,986, F4 2,131, F5 147 and F6 270 per mode. Plus 7 websocket scopes, plus 2,201 route-vs-policy match computations per mode in F3 (not HTTP requests).

**`summary.md` was not written.** The Write tool refused it ("subagents should return findings as text"), so I did not route around the block; its content is this reply. The scripts and raw JSON results are in `D:/autoTesting/qa/evidence/t204-team-login-B/unauth/`: `common.py`, `f1_unauth.py`, `f2_nogroup.py`, `f3_router.py`, `f4_csrf.py`, `f5_redirect.py`, `f6_inject.py`, `f7_ws.py` and `f*-{loopback,hosted}.json`. Scratch data dirs are deleted.

### Family by family
1. **Unauthenticated reach: PASS.**
   - `app.routes` has 71 routes (classes `APIRoute` and `Route`). There is no Mount, StaticFiles or WebSocket route; docs, openapi, redoc and favicon are plain routes. I requested 116 concrete paths (plausible and real slug/run id) x 8 methods (GET POST PUT PATCH DELETE HEAD OPTIONS TRACE) x Accept html and json.
   - Every non-public request answered `302 /auth/login?next=...` for `Accept: text/html` and `401 {"detail":"authentication required"}` otherwise. No sentinel leaked.
   - About 70 path variants were refused the same way: case, trailing slash, `//`, `%2f`, `%2e%2e`, `/auth/login/../projects/...`, `%00`, backslash, `;`, `.env`, `.auth/auth.sqlite3` and video/frames traversal. So were the bypass headers (X-Original-URL, X-Rewrite-URL, X-Forwarded-*, method override, garbage/oversized/duplicate cookies, Origin/Referer) and the Host variants.
   - The body never echoes input. The `Location` carries only the percent-encoded request path, and a query `next=` never reaches it.
   - Data-root diff (files, sizes, sha256) before and after the whole refused window: the only change is `.work/audit.jsonl` added. It came from the `/auth/login%0a` variant (O1), a public handler writing its own `login-failed` line, not from a refused request.
   - Unauthenticated `GET /healthz` returns exactly `{"ok":true}` (200, application/json); a bad Host gets 403.
   - The public set matches AU16: GET `/auth/login` and `/auth/signup` return 200; POST with bad credentials returns 401 (login) or 400 (signup). A valid scratch signup returned 303, which is open signup by design.
2. **No-group user (zero permissions): PASS.**
   - Every route x 7 methods x 2 fills x 2 Accept, with an allowed Origin on unsafe methods. Status counts: 403 x520, 405 x1424, 200 x24, 400 x8, 401 x8.
   - The only non-403 answers were GET `/auth/waiting`, the public login/signup/healthz paths, and 405 on (method,path) pairs that have no handler. I checked all non-403 pairs against `app.routes`: none had a handler.
   - POST `/auth/logout` returned 303 and the old cookie was then refused. No sentinel appeared in any body.
3. **Router table vs policy table: PASS, no mismatch.**
   - Routes missing from `ROUTE_POLICY`: none. Policy rows with no route: none.
   - Fuzz: 2,201 (route, method, param value) combinations, including newline, CR, NUL, tab, `..`, `%`, `;`, unicode, slashes and empty. In 0 of them did the policy template differ from the template Starlette dispatches to.
   - Handlers I read: `routes_project_access.py:30-72` (GET /access policy `project.view`, handler needs `project.assign` or `access.approve`, so stricter), `routes_credentials.py:31-35,176-205` (values shown only with `credentials.view`), `routes_admin.py:50-150` (re-checks `_require`) and `routes_live.py:82-100` (healthz detail needs `settings.manage`). I found no weaker policy row than its handler.
4. **CSRF/Origin guard and Host header: PASS.**
   - Admin session, 31 unsafe routes, project `gamma` and dummy ids so nothing had a side effect. These variants got the guard 403 on 31 of 31 routes in both modes:
     - no state change: Origin evil, `Origin: null`, Referer-only cross-site, `Referer: not a url`;
     - evil Origin with text/plain or multipart bodies;
     - two Origin headers in both orders;
     - non-numeric port (`<origin>:80.evil.com`), `Origin: *`, empty Origin;
     - userinfo tricks, `localhost.evil.com`, `127.0.0.1.evil.io`, `0.0.0.0`, `127.1`;
     - ftp/file schemes and hash/backslash/tab tricks;
     - `Sec-Fetch-Site: cross-site` or `same-site` with no Origin.
   - PUT/PATCH/DELETE/POST on all 71 paths with evil or null Origin were also all guard-403. **No route accepted a cross-site state change.**
   - Missing Origin and Referer is allowed on all 31 routes (`ui/helpers.py:261-263`; O3). The session cookie is `HttpOnly; SameSite=Lax` (`ui/routes_auth.py:34-36`).
   - Host attacks as Admin on `GET /projects/alpha/env`: `evil.example`, `localhost.evil.com`, `127.0.0.1.evil.io`, `localhost:8000.evil.com`, `testserver.evil.com`, `testserver:8000`, userinfo/hash/slash variants, duplicate Host (both orders) and absent Host all returned 403 with no sentinel. A good Host shows the sentinel to Admin, which is correct for `credentials.view`. `X-Forwarded-Host`, `Forwarded`, `X-Host` and `X-Original-Host` are ignored.
   - Every GET route as Admin changed nothing under the data root except lazily creating `.work/run_queue.json` (O2).
5. **Open redirect: PASS.**
   - 39 `next` values were tried through a successful scratch login, covering the absolute URL, `//host`, `///host`, `/\host`, `\\host`, `javascript:`, `data:`, `%2f%2fhost`, tab/newline, CRLF+Set-Cookie, `https:evil`, `@`-tricks, a 3 kB value, unicode slashes and NUL.
   - Every `Location` was `/` or a same-site path. `/@evil.example`, `/%2f/evil.example` and `/projects/alpha` stay paths. No header injection.
   - The hidden `next` value on GET `/auth/login` (single and double-encoded, duplicate `next`, `next[]`, `NEXT`) behaves the same.
   - Unauthenticated redirects for hostile request paths give `/auth/login?next=/` or an encoded relative path.
6. **HTML/script injection: PASS.**
   - Six payload emails were accepted by validation, including `<script>alert(1)</script>@x.test`, `"><img/src=x/onerror=xss2>@x.test` and `<svg/onload=xss4>@x.test`.
   - Display name, two group titles and three project names (one via POST `/onboard`) also carried payloads.
   - 240 page views across 5 sessions (home, admin users/groups/group edit, project pages, access, env, settings, waiting page, login/signup with `next` payloads, 404 and invalid-slug pages) plus 8 error-echo POSTs. An HTML parser found 0 injected tags, attributes or script text. A synthetic unescaped sample is flagged by the same detector, so it is not blind.
   - 168 views show escaped output, for example `&lt;script&gt;alert(1)&lt;/script&gt;@x.test` in the identity chip, admin user list, access page and waiting page. Error pages escape their detail and the login error is a constant.

### Findings
No findings above INFO. In severity order, all INFO/LOW:
- **O1 (INFO/LOW, AU16 "exactly")**: `src/autotester/auth/policy.py:87` compiles templates with `"^...$"`. `$` also matches before a trailing newline, and Starlette's own matcher does the same. As a result `GET /auth/login%0a`, `/auth/signup%0a`, `/healthz%0a` and `POST /auth/login%0a` reach the public handlers, and the POST appended a `login-failed` audit line. No extra data is exposed, and the same trick on protected paths is refused. Using `fullmatch` or `\Z` would make the public set literally exact.
- **O2 (INFO)**: an Admin GET lazily creates `.work/run_queue.json` (`ui/run_queue.py:68`; `get_queue()` is called at `ui/routes_runs.py:112`). I did not pin down which GET triggers it. Unauthenticated requests never do.
- **O3 (INFO, CSRF design)**: missing Origin and Referer is allowed on every unsafe route (`ui/helpers.py:261-263`, `Sec-Fetch-Site` defaults to same-origin). It is acceptable because the cookie is SameSite=Lax and non-browser clients send neither. It is not a failure under AU18 as written.
- **O4 (INFO)**: websocket scopes skip both middlewares (`ui/auth_middleware.py:121`, `ui/helpers.py:274`). No websocket route is registered, and 7 probes with evil Host/Origin got no accept. A future noVNC or live proxy route (hosting HO12) would be unauthenticated and Host/Origin-unchecked unless it adds its own checks.
- **O5 (INFO)**: `safe_next` accepts DEL, 0x7f (`ui/auth_middleware.py:52`, only `ord(c) < 32` is rejected). It appears raw in the hidden `next` field and is percent-encoded in `Location`. Harmless.
- **O6 (INFO)**: the login page has no CSP, `X-Frame-Options`, `X-Content-Type-Options` or `Referrer-Policy` headers. No AU criterion covers them.
- **O7 (INFO)**: HEAD on `/healthz` and the login pages returns 405. A container health check that uses HEAD would fail; the contract names GET only.

### Method notes
- My first F1 pass flagged 34 rows. About half were my own false positives: the redirect `Location` legitimately carries the path, and one Origin test value had a path. I fixed the checks and reran both modes; the only remaining rows are the O1 trailing-newline variants.
- F3's "weaker than the handler" half is a read of the handlers above, not an exhaustive read of all 3,600 lines of route code.
- I did not test the `__Host-` cookie over HTTPS or a hosted run without `COOKIE_SECURE=0`, because they are outside the six families.
- A stray `copy.py` in the shared scratchpad dir shadows stdlib `copy` when a script runs from there. It also printed SMTP-presence lines when imported. It is not mine and I did not touch it; my scripts ran from the evidence folder.
- I opened no `.env` and used no real email or password.