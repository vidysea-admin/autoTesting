# t204-team-login (seat A) — guard order, route table, earlier-FAIL recheck, round-cap count

Read-only sub-checker. Worktree `D:/autoTesting/.worktrees/t204-team-login`, HEAD `aa6fec2e`. Contract `qa/contracts/auth.md`.
Method: read the files cited below; one import-only Python run (scratchpad, `AUTOTESTER_ROOT` = fresh dir, `-I`, `PYTHONPATH=<worktree>/src`) that walks `app.routes` and calls `policy.route_for`. No pytest, no repo write, no env values printed.

## 1. Order of guards (outermost first)

Request-time stack, built by `FastAPI.build_middleware_stack` (`.venv/Lib/site-packages/fastapi/applications.py:1020-1062`; Starlette's twin is `starlette/applications.py:74-78`): the first entry of `user_middleware` is the outermost user layer.

1. `ServerErrorMiddleware` (framework; turns an unhandled exception into a plain 500, so a crash inside a guard fails closed, nothing is served)
2. `_OriginGuard` — `ui/helpers.py:266-287`, registered by `origin_guard_middleware()` `ui/helpers.py:290-292`
3. `_AuthGate` — `ui/auth_middleware.py:114-150`, registered by `auth_middleware()` `ui/auth_middleware.py:153-155`
4. `ExceptionMiddleware` (framework; the themed HTTPException handler `ui/error_pages.py:108-123` lives here)
5. `AsyncExitStackMiddleware` (framework) -> router -> handler

Proof the Host/Origin guard precedes the login gate:
- `ui/app.py:63-65`: `FastAPI(..., middleware=[*origin_guard_middleware(), *auth_middleware()])` — Origin guard listed first, so outermost. `ui/auth_middleware.py:4` and `:154` say the same.
- Runtime introspection: `app.user_middleware` -> `['_OriginGuard', '_AuthGate']`.
- Behaviour: `_OriginGuard.__call__` (`helpers.py:273-287`) returns a bare 403 for a repeated/absent Host, a repeated Origin, or `not _host_allowed(host)` (any method, GET included) before `self.app(...)` is reached, and a JSON 403 for a cross-site state-changing request; `_AuthGate` is only reached via `self.app` at `helpers.py:287`. A cross-origin POST with a valid cookie therefore never reaches `resolve_session` (`auth_middleware.py:127`).

Reachability questions:
- `/healthz`: passes both guards (Host check applies; foreign Host -> empty 403). Public by policy (`policy.py:39`). Handler returns only `{"ok": true}` for anonymous (`routes_live.py:92-94`); detailed form only with `settings.manage` (`:93,:95-100`). Matches AU16.
- WebSocket / SSE / static: none exist. Introspection of all `app.routes` found only `APIRoute` and the 4 framework `Route`s (openapi, docs, docs/oauth2-redirect, redoc); no `WebSocketRoute`, no `Mount`, no `StaticFiles`; grep of `src/autotester/ui` for `mount(`, `websocket`, `StaticFiles`, `StreamingResponse`, `EventSourceResponse` finds none. Latent (not reachable today): both middlewares pass any non-`http` scope straight through (`helpers.py:274` guard is `if scope["type"] == "http"`; `auth_middleware.py:121-123`). The old P13 note (a future noVNC websocket proxy would be ungated) is STILL PRESENT as a latent hazard; `hosting.md` HO12 must gate it when it lands.
- 404 / 405: unauthenticated callers never see them for an unknown path or wrong method: `_refusal` (`auth_middleware.py:78-87`) answers 302 (browser) or 401 JSON first, because `rule is None` and `who is None` falls to line 83. Signed-in callers on a path with no handler keep the plain 404/405 (`:88-90`, `_has_handler` `:71-75`, FULL-match only); a path with a handler but no policy row gets 403 (`:91`).
- 500: raised after both guards, or inside them; either way only `ServerErrorMiddleware` answers.
- Errors raised by a handler pass back out through `_AuthGate._send` (`auth_middleware.py:131-138`), so a signed-in error page also gets `Cache-Control: no-store`.
- `/favicon.ico`: gated (`MEMBER`, `policy.py:42`), so an anonymous favicon fetch gets 302/401 (console noise only, old P12).

Differential (policy template vs the handler Starlette would run): 32,515 probes (every route template x 13 tricky parameter values x GET/POST/PUT/DELETE/PATCH, including `new`, `upload`, `report`, `edit`, `access`, `a.xlsx`). Result: 0 cases where the policy template differs from the template of the route that actually handles the request, and no public row without a handler. So the gate cannot be steered to a weaker row by a path shape.

## 2. Route table (71 method+path pairs; HEAD excluded)

Legend: PUBLIC = answers an unauthenticated request. SESSION = any signed-in account, even with zero permissions. MEMBER = signed in and at least one permission. KEY = needs that unscoped key. PROJ = project route; unviewable project -> 404, viewable without the key -> 403 (`auth_middleware.py:105-110`); the key is checked with `resource_for(slug)` so scope (`@all/@assigned/@own/@shared`) applies.

| Method | Path | Policy row | Handler |
|---|---|---|---|
| GET | /auth/login | PUBLIC | routes_auth.auth_login_form |
| POST | /auth/login | PUBLIC | routes_auth.auth_login_submit |
| GET | /auth/signup | PUBLIC | routes_auth.auth_signup_form |
| POST | /auth/signup | PUBLIC | routes_auth.auth_signup_submit |
| GET | /healthz | PUBLIC (minimal body for anon) | routes_live.healthz |
| POST | /auth/logout | SESSION | routes_auth.auth_logout |
| GET | /auth/waiting | SESSION | routes_auth.auth_waiting |
| GET | / | MEMBER | app.index (list filtered by `visible_slugs`, `app.py:77-78`) |
| GET | /favicon.ico | MEMBER | app.favicon |
| GET | /onboard | KEY project.create | app.onboard_form |
| POST | /onboard | KEY project.create | app.onboard_submit (creator becomes owner `app.py:185-187`) |
| GET | /live | KEY live.view | routes_live.live_view |
| GET, POST | /settings/providers | KEY settings.manage | routes_settings |
| GET | /openapi.json, /docs, /docs/oauth2-redirect, /redoc | KEY settings.manage | FastAPI framework routes |
| GET | /admin/users | KEY users.manage | routes_admin.admin_users |
| POST | /admin/users/{user_id}/{action} | KEY users.manage | routes_admin.admin_user_action (AU27 admin-only checks in the store: `accounts._update` -> `access.require_may_touch`) |
| GET, POST | /admin/groups | KEY groups.manage | admin_groups / admin_group_create |
| GET, POST | /admin/groups/{group_id} | KEY groups.manage | admin_group_view / admin_group_update |
| POST | /admin/groups/{group_id}/delete | KEY groups.manage | admin_group_delete |
| GET | /projects/{slug} | PROJ project.view | app.project_detail |
| GET | /projects/{slug}/cases/new, /cases, /edit, /flowspec, /requests, /sources, /product-map, /flow-diagram, /crawls, /crawls/{crawl_id}, /crawls/{crawl_id}/report.xlsx, /issues, /issues.xlsx, /issues/{issue_id}/pin, /env, /access, /catalog | PROJ project.view | routes_cases, routes_project_edit, routes_learn, routes_sources, routes_product_map, routes_flow_diagram, routes_crawls, routes_issues, routes_credentials, routes_project_access, routes_catalog |
| GET | /projects/{slug}/runs/{run_id}, /report, /report.xlsx, /report.html | PROJ report.view | routes_report |
| GET | /projects/{slug}/runs/{run_id}/videos/{video_path:path} | PROJ video.view | routes_video.serve_run_video |
| GET | /projects/{slug}/frames/{source_id}/{name:path} | PROJ video.view | routes_product_map.learned_frame |
| POST | /projects/{slug}/cases, /cases/{case_id}/rename, /cases/{case_id}/delete, /edit, /login-case, /flowspec/approve, /flowspec/request-edit, /cases/generate, /crawls/{crawl_id}/merge, /issues/{issue_id}/pin, /sources, /sources/{source_id}/analyze, /env/url | PROJ project.edit | routes_cases, routes_project_edit, routes_crawl_login, routes_learn, routes_crawls, routes_issues, routes_sources, routes_credentials |
| POST | /projects/{slug}/sources/upload | PROJ video.upload | routes_sources.upload_source |
| POST | /projects/{slug}/run, /explore, /crawl-approval | PROJ project.run | routes_runs.trigger_run, routes_crawls.start_crawl, routes_crawl_approval |
| POST | /projects/{slug}/secrets, /secrets/{key}/delete, /env, /env/add | PROJ credentials.edit | routes_project_edit, routes_credentials |
| POST | /projects/{slug}/access | PROJ project.view at the gate; handler then requires project.assign (assigned) or video.share (shared) | routes_project_access.project_access_submit (`routes_project_access.py:65-70`) |

Checks against the contract and `policy.py`:
- Every one of the 71 pairs has a policy row, and every `ROUTE_POLICY` key (`policy.py:35-75`) maps to a real route (the script printed no "POLICY ROW NO ROUTE" and no pair with `None`). Routes with no policy row: NONE. Rows with no route: NONE.
- Public set in code = exactly `GET/POST /auth/login`, `GET/POST /auth/signup`, `GET /healthz` (`policy.py:37-39`). That equals AU16 (`auth.md:182-183`). Public routes not listed in auth.md: NONE. So no unlisted-public FAIL ground.
- Rows more permissive than the contract: none at the route level. Two rows are intentionally looser at the gate than the action: `POST /projects/{slug}/access` (`policy.py:74`, comment says the handler checks `project.assign` or `video.share`; handler does, `routes_project_access.py:69-70`; the GET page also demands `project.assign` or `access.approve`, `:35-37`, which closes the old "tester can read the access page" finding) and the env page GET (`project.view`; AU21 value hiding is the handler's `can_view_credentials()` `routes_credentials.py:185`, outside this question).
- Rows stricter than the contract needs: `/favicon.ico`, `/` (MEMBER), `/docs` family and `/openapi.json` (`settings.manage`; the contract lists neither). Not a defect.
- AU6/AU14 behaviour: SESSION rows are the only product-adjacent pages a zero-permission account reaches (`auth_middleware.py:92-98`); everything else returns the waiting 403.
- Observation (not a contract failure): `auth_middleware.py:148-150` audits state-changing requests only when `who is not None`, so a refused anonymous POST on a non-auth path is not written to `audit.jsonl`; login/signup success and failure are audited by `routes_auth.py:58,61,81` in the `{actor,target,action}` shape. AU22 says "every state-changing request"; see old P15 below.

## 3. Earlier FAIL findings (old `t204-auth.a` and `t204-auth.b`, both cycle 0 FAIL; no other t204-auth verdict exists in history: commits efefbbe2, c1e6a7e2, 32c7e48a; there is no t204-auth fix-cycle verdict)

Sources: `git show efefbbe2:qa/verdicts/t204-auth.a.md`, `git show 32c7e48a:qa/verdicts/t204-auth.b.md`. Code checked at `aa6fec2e`.

| Old finding | Criterion | Status at aa6fec2e | Evidence |
|---|---|---|---|
| A-F1 / B-P1 (high): a `credentials.edit` holder can write any `.env` key through `POST /projects/{slug}/env/add` and `/secrets` (provider keys, `AUTOTESTER_*`, another project's key) | AU21 | FIXED | `build_secret_ref` calls `refuse_foreign_key` before anything is saved (`ui/routes_project_edit.py:65`); `env_add_credential` calls `build_secret_ref` first (`ui/routes_credentials.py:159`) and writes only `ref.key` (`:170`). `refuse_foreign_key` (`ui/credential_guard.py:38-58`) refuses `PROVIDER_KEYS` and the `AUTOTESTER_` prefix (403, `:46-48`), any key outside `key_namespace(slug)` (400, `:49-51`), and a key another project declared (`:55-58`). Onboarding rows also pass through it (`routes_project_edit.py:84`). Residual to note, not a regression of the old finding: the namespace is derived from the slug, so a project whose slug equals a server-key prefix (for example slug `openai` -> `OPENAI_`) could declare a key in that prefix other than the four listed in `PROVIDER_KEYS`; the listed provider keys themselves are blocked wherever they appear. When T-202's LiteLLM keys land they must be added to `PROVIDER_KEYS` (`credential_guard.py:26-29`). |
| A-F2 (medium): `__Host-` cookie prefix defeated, plain `at_session` accepted in hosted/Secure mode | AU3 | FIXED | `session_token` (`ui/auth_middleware.py:34-42`) reads only `SESSION_COOKIES[:1]` (`__Host-at_session`) whenever `cookie_secure(request.url.scheme)` is true. |
| A-F3 (medium): stored XSS, group name unescaped in page `<title>` | AU16 / security | FIXED | `theme.page` writes `title` raw (`ui/theme.py:182`), and the group pages now pass `escape(group.name)` (`ui/routes_admin.py:115,132`); the other `theme.page` calls there pass literals (`:40,85,97,144,149`). |
| B-P2 (medium): `.dockerignore` has no `.auth/` rule while the Dockerfile does `COPY . .` | AU23 | FIXED | `.dockerignore:22-23` has `.auth/` and `**/.auth/`. |
| P5 (A, B): `users.manage` / `groups.manage` admin-equivalent (self-grant, self-add to Admin/CEO, reset last admin) | AU8/AU10 -> AU27 | FIXED in code, by contract AU27 | `access.require_may_grant` (`auth/access.py:117-`) and `access.require_may_touch` called inside the store transaction (`auth/accounts.py:127`); judging their completeness is another sub-checker's job, not this question. |
| A-P8 / B-P7 (low): signed-in pages carry no `Cache-Control: no-store` | AU25 | FIXED | `auth_middleware.py:134-137`. |
| B-P7 (low): a Tester can read `/projects/{slug}/access` (lists owner, assignee, shared-with emails) | AU13 | FIXED | `routes_project_access.py:35-37`. |
| B-P10 (low): `next` has no length cap | AU16 | FIXED | `MAX_NEXT_LENGTH = 2048` and the check at `auth_middleware.py:45-54`. |
| A-P9 / B-P10 (low): open signup has no rate limit; empty limiter keys never evicted; dummy hash computed lazily | AU5 | FIXED | `signup_limiter` used at `routes_auth.py:74-76`; `del self._failures[key]` at `auth/ratelimit.py:44`; `_DUMMY_HASH` built at import `auth/passwords.py:35`. |
| A-P15 (low): unauthenticated state-changing requests write no request/audit line | AU22 | STILL PRESENT (partly) | `auth_middleware.py:148` records the request line only `if who is not None`. Anonymous login/signup are covered by `record_action` lines (`routes_auth.py:58,61,81`) but they carry the `{actor,target,action}` shape rather than `{ts,email,method,template,status}`, and any other refused anonymous POST is not logged. Low; a reading question for AU22. |
| A-P13 (low): the gate passes non-http scopes through (a future noVNC websocket would be ungated) | AU16 / HO12 | STILL PRESENT, latent | `auth_middleware.py:121-123`, `helpers.py:274`. No websocket route exists today (introspection above). |
| A-P16 (low): `authenticate` reads outside the transaction; the rehash UPDATE can overwrite a freshly reset hash; a session can be created after a concurrent reset | AU3/AU8 | STILL PRESENT | `auth/accounts.py:90-104`: the read happens in `db.reading()`, then the `UPDATE users SET password_hash` at `:101-103` runs in a separate transaction without checking the stored hash is unchanged. It only bites when `needs_rehash(stored)` is true and a reset lands in that window. Low. |
| Others (A-P4/P6/P7/P11/P12/P14, B-P3/P4/P6/P8/P9/P11/P12/P13): deploy-file, merge-harness, test-gap, wording and a11y notes | various | NOT RE-CHECKED here | Outside the four questions put to this sub-checker; the manifest says several were repaired (`.env.example`, `docker/DEPLOY.md`, the harness env list, the pinned policy table test). |

## 4. D-014 round cap per seam

- The manifest line (`.worktrees/t204-team-login/qa/manifests/t204-team-login.md:16`) cites "D-014" and says: security class, the 2-PASS cap for non-security seams does not apply; seam = `auth/` store and `ui/auth_middleware.py` gate.
- What D-014 actually says: **`docs/DECISIONS.md:208` (autoTesting D-014) is a different subject** — "Additive schema amendments for Track A (learn from recordings)". It says nothing about a round cap. The cap is the AIOS delivery-gate rule also called D-014 (named "D-014 round cap (AIOS delivery gate)" at `qa/gates/at673-round-cap.md:3`; the feedback inbox at `qa/feedback-inbox.md:4867-4868` and `:5477` records that the local D-014 is wrong-subject for it). The rule's text, as restated in the shared log (`D:/ai_os/decisions/log.md:1852-1861`): the cap is **class-based, never count-based**, because the count-based form let ISS-078, a cross-tenant disclosure, first surface at round 5 after four PASSes; a unit must write its class on a `Round cap:` line (security class, a cited waiver, or withdraw). `qa/gates/at673-round-cap.md:17-18` states security class as "tenancy, auth, cross-tenant reads, data writes or credential handling" where "the cap never applies". Login, sessions and the credential boundary in front of the hosted UI are in that class, so the manifest's reading is correct; the only wrinkle is that its "D-014" label points to a rule that lives in the AIOS log and gate file, not in `docs/DECISIONS.md` D-014 (same label the accepted precedents use: `qa/manifests/at758-759-host-allowlist.md:18`, `qa/verdicts/t202-any-model-provider.a.md:38`).
- Count of checker PASS verdicts for the two seams, by history (`git log --all -S"auth_middleware" -- qa/verdicts qa/manifests` lists only `t204-auth` (A and B) and `t204-team-login`; the tree holds no other verdict naming `auth_middleware`, `autotester/auth/` or "auth/ store"): **`auth/` store = 0 PASS; `ui/auth_middleware.py` gate = 0 PASS.** Both earlier verdicts are FAIL (`efefbbe2`/`c1e6a7e2` coordinator A, `32c7e48a` coordinator B), and the fix-cycle branch (`wave/t204-auth-fix1`, commit `886936ab`) never received a verdict. Nothing from this unit's own verdicts counted. Even at 0 PASS the cap would not bind (limit is 2), and as a security-class seam it does not apply in any case. Cap applies: NO.

## Verdict for the four questions

1. Order: ServerError -> `_OriginGuard` -> `_AuthGate` -> ExceptionMiddleware -> router. Host/Origin first, proven at `app.py:63-65` and `helpers.py:273-287`. No ws/SSE/static mounts; 404/405/500 and `/healthz` are behind the Host guard, `/healthz` is public by design and minimal.
2. 71 routes, all with a policy row, no orphan rows, public set exactly AU16's five method+path pairs; no unlisted public route; no row looser than the contract (two gate-level loose rows are enforced in the handler).
3. Old blocking FAILs (env/add key poisoning, `__Host-` fallback, title XSS, `.dockerignore .auth/`) are FIXED. Low leftovers still present: anonymous refused POSTs not audited in request-line shape (AU22 reading), latent non-http passthrough, an `authenticate` rehash race.
4. 0 PASS for both seams; security class; cap does not apply; note the "D-014" cite resolves to the AIOS rule, not to `docs/DECISIONS.md` D-014.
