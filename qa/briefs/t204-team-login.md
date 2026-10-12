# Brief - t204-team-login (team login by email and password, D-072)

Readiness pass written 2026-10-11 against master `3a16616c`. Self-contained: the builder needs nothing from the dispatching session. Items marked `unknown` are not stated anywhere in the repo.

## 1. Policy and tier

Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Dual check: required
Trigger: `auth` and `security`: `src/autotester/ui/auth_middleware.py:29-45` (`SESSION_COOKIES`, `session_token`, the `__Host-` cookie rule) and `src/autotester/ui/auth_middleware.py:117-153` (the default-deny gate `__call__` and `auth_middleware()`), plus `src/autotester/auth/passwords.py` (argon2id) and `src/autotester/auth/sessions.py`; line numbers are those of `wave/t204-auth-fix1` tip `886936ab` and the builder must refresh them in the manifest after the rebase. Tier L = security/auth/tenancy; two independent checkers (A and B); neither may read the other's verdict first.


## 2. Root and base

- Root: `D:/autoTesting`. Base: master `3a16616c`, and the unit lands AFTER `land-t203-hosting` (shared `core/env.py`, `tests/conftest.py`, `.env.example`, `docker/entrypoint.sh`, `ui/routes_live.py`), so rebase onto master once that has landed.
- Branch: **continue `wave/t204-auth-fix1`** (tip `886936ab`, code `cb54b2d5`, merge-base `c0f99ae1`, 56 files, status `ready-for-check` cycle 1). Create `wave/t204-team-login` from master and bring the fix1 code over (merge/cherry-pick `8a9ac0cd` then `cb54b2d5`; not the qa commits). Reason: fix1 already repairs the cycle-0 FAILs of both checkers (`qa/verdicts/t204-auth.a.md` `VERDICT: FAIL` 20/26 met, AU3 and AU21 failed; `qa/verdicts/t204-auth.b.md` `VERDICT: FAIL` AU21 and AU23 failed) and merges clean with master: master has no `ui/` file that fix1 lacks and the `ui/` diff between fix1's base and master is empty.
- No checker PASS exists for any T-204 commit. D-080 item 1 (re-land the exact PASSed commit) therefore does not apply: this is a build-to-cycle-1 unit, the checker must reach a PASS before it lands.

## 3. Acceptance criteria (verbatim from `qa/contracts/auth.md`, 295 lines, AU1-AU27)

The two D-074 follow-ups are binding and override the contract wording where they differ (the contract and `docs/plan.md` row 13 still say "first account becomes admin"; the checker rewords them, the maker never edits `qa/contracts/`): D-074(d) first admin only via `AUTOTESTER_FIRST_ADMIN_EMAIL` on a hosted server, an unset variable promotes nobody, local loopback dev keeps first-account-admin; D-074(e) `AUTOTESTER_COOKIE_SECURE=0` until HTTPS exists. The fix1 code already implements both (`test_d074_*`, 6 tests).

## Vocabulary (fixed here so criteria are falsifiable)

- **Permission** = a key from the closed catalogue below, optionally with a scope: `key@all`, `key@assigned`, `key@own`, `key@shared`.
  Unscoped keys (`users.manage`, ...) have no scope.
- **Effective permissions of a user** = the union of the permissions of every group the user belongs to. There is no deny. Additive only.
- **Resource** = `ResourceRef(project_slug, owner_email | None, assignees, shared_with, video_id | None)`.
  - `own`: `owner_email == user.email`. The creator of a project is its owner.
  - `assigned`: the user is in the project's `assignees`.
  - `shared`: the user is in the resource's `shared_with`.
  - `all`: no condition.
  - A project with no recorded owner (legacy, created before T-204) matches **only** `@all`. It fails closed.

### Permission catalogue (closed; a key not listed here cannot be saved into a group)

| key | scopes | what it gates |
|---|---|---|
| `project.view` | all, assigned, own, shared | see the project, its sources, flowspec, catalog, runs |
| `project.create` | (none) | onboard a new project; the creator becomes its owner |
| `project.edit` | all, assigned, own | edit project settings, sources, cases, models |
| `project.run` | all, assigned, own | press Run, enqueue a run |
| `project.assign` | all | assign sub-admins (assignees) to a project |
| `report.view` | all, assigned, own, shared | open a run report |
| `video.view` | all, assigned, own, shared | watch or open a recording |
| `video.upload` | all, assigned, own | upload a recording or give a Drive link |
| `video.share` | all, assigned, own | add or remove `shared_with` on a video or project |
| `access.approve` | all, assigned, own | approve an access request on a resource |
| `comment.create` | all, assigned, own, shared | add a comment |
| `credentials.view` | (none) | **see a saved credential value** (G4) |
| `credentials.edit` | all, assigned, own | write a new credential value (write-only) |
| `schedule.manage` | all, assigned, own | set a project's run schedule |
| `live.view` | (none) | open `/live` and the noVNC view |
| `live.control` | (none) | send input through noVNC (manual login, OTP) |
| `users.manage` | (none) | list, disable, enable, delete, reset any account; edit group membership |
| `groups.manage` | (none) | create, edit and delete groups and their permission ticks |
| `settings.manage` | (none) | server settings (run concurrency, upload limit, default model, SMTP view) |

Group 10 units may add keys to this catalogue through the registry in a later checker-approved amendment. A route or action that
needs a permission not listed here is a contract gap, not licence to invent one.

### Default groups (seeded once, idempotently; admins may edit them afterwards)

| group | permissions | meaning |
|---|---|---|
| **Admin/CEO** | every key above, every scope at `@all` | sees every project and video, approves anyone |
| **Sub-admin** | `project.view/edit/run`, `report.view`, `video.view/upload/share`, `access.approve`, `comment.create`, `credentials.edit`, `schedule.manage` all at `@assigned`; `live.view` | manages only the projects assigned to them |
| **Developer** | `project.create`; `project.view/edit/run`, `report.view`, `video.view/upload/share`, `access.approve`, `comment.create`, `credentials.edit`, `schedule.manage` at `@own`; `project.view`, `report.view`, `video.view`, `comment.create` at `@shared`; `live.view` | works on their own projects and videos; approves access requests for their own videos |
| **Tester** | `project.view`, `report.view`, `video.view`, `comment.create` at `@shared` only | sees only what was shared with them, and can comment |

`credentials.view` is held by **Admin/CEO only** by default (D-072 item 5). The Developer, Tester and Sub-admin default grants for
`credentials.edit`, `schedule.manage`, `live.view` and `project.create` are the checker's reading of Umesh's role answer, not stated in
D-072; they are editable by any admin, and a different answer from Umesh is a routine amendment of the table above.

### Criteria

- **AU1 — Passwords are hashed with argon2id (`argon2-cffi==25.1.0`), never stored or logged.** *(amended D-074, 2026-10-07)* The stored
  value is an argon2id hash with a per-user salt (memory >= 19 MiB and t >= 2). No plaintext password, and no reversible form, exists in
  the store, in any log line, the audit file, a response body, an error message or an exception text. Verification is constant-time.
  *Dependency:* D-074(c) authorizes `argon2-cffi==25.1.0` (pinned exactly) in `pyproject.toml` and `uv.lock`, and that is the only
  dependency change this unit may make. bcrypt and the stdlib `hashlib.scrypt` fallback are **not** used (D-074(c)).
  `serves:` D-074(c), D-072#3, O7. *Re-derive:* unit test reads the raw store after signup with a canary password and asserts the canary
  is absent from every file under the data root and from `caplog`; asserts the hash prefix is `$argon2id$`; `uv.lock` pins
  `argon2-cffi` at 25.1.0; mutation: store the password as given -> test fails.

- **AU2 — Login does not reveal which half was wrong.** `POST /auth/login` with an unknown email, a wrong password, and a disabled
  account all return the same status and the same body text, and take comparable work (the unknown-email path still computes a hash
  against a dummy). A correct email + password creates a session and redirects to a same-site relative `next` or `/`.
  `serves:` D-072#3. *Re-derive:* three requests, compare status+body byte for byte; mutation: return "no such user" -> fails.

- **AU3 — Session cookie and server-side session.**
  - The session id is >= 128 bits from `secrets`, a **new id is issued at every login** (no fixation), and the session is looked up
    server-side so a disable, delete, group change or password reset takes effect on the **next request** with an unexpired cookie.
  - Cookie flags: `HttpOnly`, `SameSite=Lax`, `Path=/`, no `Domain`. `Secure` is set whenever the request is HTTPS (or
    `X-Forwarded-Proto: https` from a configured proxy) or `AUTOTESTER_HOSTED=1`; with `Secure` it also carries the `__Host-` prefix.
    The only way to omit `Secure` in hosted mode is the explicit `AUTOTESTER_COOKIE_SECURE=0`, which the deploy guide documents as the
    pre-domain, private-network interim (see `hosting.md` HO13).
  - Absolute lifetime <= 12 h by default (configurable, never unlimited). A cookie that is tampered, truncated, unknown, or expired is
    refused (302/401) and creates nothing.
  `serves:` D-072#3. *Re-derive:* header assertions; parametrized bad-cookie test; test that disabling a user makes their next request
  with a live cookie fail.

- **AU4 — Logout.** `POST /auth/logout` (Origin-guarded) deletes the server-side session and clears the cookie; the old cookie value is
  refused afterwards. A GET to the logout path changes nothing. `serves:` D-072#3.

- **AU5 — Login rate limit.** After 5 failed attempts for one account, or 20 from one client address, inside 10 minutes, further login
  attempts for that scope are refused with 429 **even with the correct password** until the window passes. The constants are named in
  the module and documented in `.env.example`. A lock is time-based and never permanent, and the 429 body does not say whether the
  account exists. The counters survive a request, not necessarily a restart. `serves:` D-072#3.
  *Re-derive:* 6 bad logins then a good one -> 429; advance the injected clock -> allowed; mutation: remove the check -> fails.

### Signup, first admin, account management

- **AU6 — Open signup, zero permissions.** `GET/POST /auth/signup` is reachable unauthenticated. Email is trimmed, lowercased, and
  validated; password length 10..128 (the upper bound limits hashing cost); a duplicate email is refused without touching the existing
  account. A new account has **no group**, and an authenticated user with an empty effective-permission set can reach only the
  "waiting for an admin" page and logout; every other route returns 403. That page says which role to ask (an administrator) and lists
  no users. `serves:` D-072#3, D-072#4. *Re-derive:* signup as user 2, request every non-public route from `app.routes`, assert 403.

- **AU7 — First admin: a fixed email on a hosted server, first account only in local dev, atomically.** *(amended D-074, 2026-10-07)*
  "Hosted" is the AU17 test: `AUTOTESTER_HOSTED=1`, a non-loopback bind address, or a Secure session cookie in effect (AU3).
  - **Hosted, `AUTOTESTER_FIRST_ADMIN_EMAIL` set:** only the signup whose email (trimmed, lowercased, like every email, AU6) equals that
    value is placed in Admin/CEO, and only while Admin/CEO has no member. Every other signup gets no group, **including one that arrives
    first**. Two simultaneous signups for it yield exactly one admin.
  - **Hosted, `AUTOTESTER_FIRST_ADMIN_EMAIL` unset or empty:** nobody is auto-promoted, whatever the signup order. The server logs one
    startup warning that names the variable and says the admin must be created through the CLI, then keeps starting (this is a warning,
    not an AU17-style refusal). A CLI command (name fixed by the unit, listed in `docs/MAP.md`) creates or promotes an admin account
    and works while the server is stopped or running; it is the only bootstrap path in this state.
  - **Local development (loopback bind, not hosted):** unchanged: when the user store is empty the first signup is placed in Admin/CEO,
    two simultaneous first signups yield exactly one admin, and every later signup gets no group.
  - The warning and the CLI output never print a password or the email of any existing account other than the one just created.
  `serves:` D-074(d), D-072#4. *Re-derive:* hosted + variable set: sign up another email first -> no group, then the named email ->
  admin; hosted + unset: sign up first -> no group, startup log holds the warning, CLI creates an admin who can log in; local: the
  threaded double-signup test with a barrier. Mutations: treat hosted as local -> the hosted tests fail; grant admin to every signup ->
  fails; compare the email case-sensitively -> the case-variant test fails.

- **AU8 — The admin can act on any account.** A holder of `users.manage` can list accounts, disable, enable, **delete**, reset a
  password (sets a new hash and revokes that user's sessions), change the display name, and add or remove group membership, for any
  account. A disabled or deleted user's next request fails and their login is refused with the AU2 text. Deleting a user keeps the audit
  rows that name them and does not delete projects they owned: ownership of those becomes "no owner" (visible only at `@all`).
  A caller without `users.manage` gets 403 from every such route. Which targets and grants a `users.manage` holder may touch is further
  limited by AU27 *(amended D-074, 2026-10-07)*. `serves:` D-072#3.

- **AU9 — Last-admin protection.** The last enabled account in Admin/CEO cannot be disabled, deleted, removed from the group, or have
  the group's `users.manage` tick removed; the attempt is refused with a message and changes nothing. `serves:` D-072#3, D-072#4
  (checker-derived lockout guard). *Re-derive:* one admin, try each action; mutation: drop the guard -> fails.

- **AU10 — Groups with checkbox permissions, additive.** A holder of `groups.manage` can create, rename and delete groups and tick
  or untick any catalogue permission (with its allowed scopes) per group; a holder of `users.manage` adds users to groups. The
  permission form is rendered as labelled checkboxes grouped by area. The effective permissions are the union over groups; unticking
  a permission removes it from every member on their next request. Saving an unknown key, or a scope the key does not allow
  (`users.manage@own`), is refused and stores nothing. A group in use by users can be deleted only after the admin is told how many
  members lose access, and those members then have the permissions of their remaining groups only. `serves:` D-072#4.
  *Re-derive:* two groups, union test; untick -> member refused next request; unknown key -> 4xx and store unchanged.

- **AU11 — Default groups are seeded once and editable.** On first start the four default groups exist with exactly the grants in the
  table. Restarting the server does not reset an admin's edits and does not recreate a deleted default group. `serves:` D-072#4.

- **AU12 — One authorization function, scoping resolved by it.** Every route calls a single `authorize(user, key, resource)` (the
  one place that evaluates scopes); no route compares emails or group names itself (a grep of `ui/` for group-name literals, other than
  the seed table, finds nothing). The scope tests are: `all` always, `assigned` iff the user is an assignee, `own` iff the owner,
  `shared` iff in `shared_with`; a missing owner matches only `all`. `serves:` D-072#4.
  *Re-derive:* a table-driven test over (group, key, resource relation) for all four default groups and all four relations;
  mutation: treat `shared` as `all` -> fails.

- **AU13 — Visibility follows scope, and existence is not leaked.** Home, sidebar, project list, report lists and search list only
  resources the user may view. A direct URL for a project the user may not view returns the same 404 as a project that does not exist;
  a visible resource on which the user lacks the action returns 403. An Admin sees every project and video. A Sub-admin sees only assigned
  projects. A Developer sees their own projects plus anything shared with them. A Tester sees only shared items and can add comments.
  `serves:` D-072#4 and the Group 10 roles answer (2026-10-07). *Re-derive:* four users x two projects x list and direct URL.

- **AU14 — Default deny for routes.** A route-enumeration test walks `app.routes` and requires each route to be either in the closed
  public set (AU16) or to declare a required permission through the central policy table; a route added after import with neither is
  refused at request time (403) and fails the test. Applies to every method the route declares. `serves:` D-072#3.
  *Re-derive:* the enumeration test; mutation: add an undeclared route -> test fails.

- **AU15 — Approval and consent are not bypassed by a role.** Holding `project.run@all` never skips a `RunApproval`, `write_policy`, or
  model-spend gate: the existing `consent.md` behaviour is unchanged for every group, including Admin/CEO. `serves:` spec R17, D-072#4.
  *Re-derive:* admin triggers a run on a project whose approval is missing -> the same refusal a non-admin gets.

### Unauthenticated surface

- **AU16 — Unauthenticated users reach only login and signup.** The closed public set is exactly `GET/POST /auth/login`,
  `GET/POST /auth/signup`, and a minimal `GET /healthz` that returns only `{"ok": true}` (needed by the container health check; the
  current `/healthz` also prints process start time and source mtimes, so unauthenticated callers get the minimal form and the detailed
  freshness probe requires `settings.manage`). Any other path, any method, answers an unauthenticated request with 302 to
  `/auth/login?next=<same-site relative path>` for a browser (`Accept: text/html`) or 401 JSON otherwise; the body never echoes the
  input. A `next` that is an absolute URL, `//host`, or `javascript:` is dropped. No file under the data root changes on any refused
  request. `serves:` D-072#3. *Re-derive:* enumerate `app.routes` unauthenticated, diff the data root before/after.

- **AU17 — The gate cannot be switched off by accident.** Auth is on by default. `AUTOTESTER_AUTH_DISABLED=1` (for legacy tests and a
  single-user laptop) is refused at startup when `AUTOTESTER_HOSTED=1` or when the bind address is not loopback, and prints a one-line
  warning when honoured. `AUTOTESTER_HOSTED=1` with a missing required setting (`AUTOTESTER_ALLOWED_HOSTS` or `AUTOTESTER_ALLOWED_ORIGINS`
  naming the server, per AU20) makes the app refuse to start. The auth tests run with the gate ON. `serves:` D-072#3, D-072#12.
  *Re-derive:* startup tests for each combination.

### Guard layering

- **AU18 — Every state-changing route stays behind the D-066 Origin guard, including auth routes.** `POST /auth/login`, `/auth/signup`,
  `/auth/logout` and all admin routes are guarded. The guard runs **before** authentication: a cross-origin POST carrying a valid session
  cookie is 403. Two further gaps in the same code are closed because the hosted server exposes them: an `Origin` whose port part is
  not numeric (`http://localhost:8000.evil.com`, AT-760) is refused, and a request with more than one `Origin` header (AT-761) is refused.
  `*` in `AUTOTESTER_ALLOWED_ORIGINS` is ignored. `serves:` D-066, D-072#12, AT-760, AT-761.
  *Re-derive:* extend `tests/test_ui_origin_guard.py`; mutation: reorder middleware so auth runs first -> a 403 test fails.

- **AU19 — Host allow-list (AT-758).** Every request, GET included, has its `Host` header checked: it must be loopback
  (`localhost`, `127.0.0.1`, `::1`, any port), or the host of an origin in `AUTOTESTER_ALLOWED_ORIGINS`, or an exact entry of
  `AUTOTESTER_ALLOWED_HOSTS` (comma or space separated, no wildcard, case-insensitive, port compared when given). Anything else is refused
  (400/403) before routing, and in particular `GET /projects/{slug}/env` with `Host: evil.example` returns no body that contains a saved
  value. `serves:` D-072#12, AT-758. *Re-derive:* `Host: evil.example`, `Host: localhost.evil.com`, `Host: 127.0.0.1.evil.io`,
  and a listed host; mutation: skip the check -> the first three fail.

- **AU20 — Hosted configuration is explicit.** With `AUTOTESTER_HOSTED=1` at least one of `AUTOTESTER_ALLOWED_HOSTS` /
  `AUTOTESTER_ALLOWED_ORIGINS` must be set, and the server's own origin must be an allowed one; otherwise startup raises. Both keys are
  documented in `.env.example` (`hosting.md` HO9). `serves:` D-072#12.

### Secrets display

- **AU21 — Saved credential values are shown only to `credentials.view` (G4).** On `/settings/providers` and the per-project
  `/projects/{slug}/env` page, a viewer **without** `credentials.view` sees only "set" / "not set" per key: no value in the HTML,
  the `value=` attribute, inline script, a data attribute, a redirect URL, a flash message or any JSON/export, and no length or
  prefix hint. A viewer **with** it sees the D-034 show/hide behaviour unchanged. Writing a new value needs `credentials.edit` on that
  project (or `settings.manage` for the global keys) and works without `credentials.view`; the value is never echoed back after the
  POST. Provider keys present only in the server's process environment show as "set". By default only Admin/CEO holds
  `credentials.view`. `serves:` D-072#5, spec R16, O7, core-invariants C5 (amended 2026-10-07).
  *Re-derive:* seed a sentinel value, render both pages as Tester, Developer, Sub-admin and Admin, grep the HTML; mutation: render the
  value for everyone -> the non-admin tests fail.

### Observability and hygiene

- **AU22 — Audit without secrets.** Every state-changing request appends one line `{ts, email, method, path template, status}` to
  `<data>/.work/audit.jsonl`; admin actions (disable, delete, reset, group edit, setting change) add `{actor, target, action}`. Lines hold
  no body, query string, password, cookie or hash. A login failure line names the attempted email only after normalization and never
  the password. The uvicorn access log is disabled in `docker/entrypoint.sh` (cookies and `next` values travel in URLs and headers).
  `serves:` D-072#3, O7. *Re-derive:* canary password and cookie through login, grep logs and audit file.

- **AU23 — Auth data lives under the data root, never in git or the image.** Users, groups, sessions and settings are stored under
  `repo_root()` (which honours `AUTOTESTER_ROOT`), in a path that `git check-ignore` and `.dockerignore` both cover, with atomic writes
  and owner-only permissions where the platform supports them (best effort on Windows, asserted on Linux). New shapes are Pydantic
  models in `schema/` with `extra="forbid"`; no second `.env`-style store. `serves:` O7, docker.md D6, `core-invariants.md` C1-C5.

- **AU24 — Windows dev and Ubuntu prod.** Paths use `pathlib` / `core.paths`; no POSIX-only module (`fcntl`, `pwd`) is imported at
  module top level, and no Windows-only call is made without a guard. The concurrency-sensitive code (first-admin, session store, rate
  limit) is correct under both: it relies on the store's own atomicity or a portable lock, not on `flock` alone. The auth tests pass
  on Windows (the checker's host) **and** inside the project's Docker image on Linux; the Linux run is recorded as evidence
  (`qa/evidence/t204-linux-run.md`), and it may come from the T-203 rehearsal or any Linux host. `serves:` D-072#7.

- **AU25 — Existing UI behaviour is unchanged for an authorized user.** With the gate on and an Admin session, the existing UI
  contract suite (`tests/test_ui*.py`) passes; the shared layout (`theme.page`) gains only a signed-in identity chip, a logout control,
  and the admin links the user may use. `serves:` D-072#3, `ui.md` U1-U12.

### Human-facing walks (Mode D, interactive)

- **AU26 — Signup, login, pending and admin flows work in a real browser.** Mode D with the checker's own browser: sign up a first
  account (lands as admin), sign up a second (sees the waiting page), admin ticks a group for it (second account reaches its default
  page on its next click), disable it (next click returns to login), delete it. Zero unexplained console errors. Persona walks for the
  spec user types touching these flows: **tester** reaches the shared-with-me page in <= 2 clicks from login, **dev** reaches their own
  project, **lead** is not shown admin controls. Every form control has a visible label and is keyboard-operable. Evidence under
  `qa/evidence/browser-t204-*-checker/`. `serves:` D-072#3, D-072#4, spec user types.

- **AU27 — No privilege escalation: grant only what you hold; the admin set is admin-only.** *(added D-074 safe default, 2026-10-07; the
  rule comes from the dispatching brief, D-074's record states only a-e)* Row ID is new; AU8-AU10 keep theirs.
  - A caller can grant, through any route (group tick, add to group, new group, default-group edit), only permissions (key **and**
    scope) that the caller's own effective set already holds. A request that would grant more is refused (403), names the permission,
    and stores nothing.
  - **Only members of the Admin/CEO group** can: add or remove a member of Admin/CEO; tick `users.manage`, `groups.manage`,
    `settings.manage` or `credentials.view` on any group; or reset the password of an account that is in Admin/CEO. A `users.manage`,
    `groups.manage` or `settings.manage` holder who is not in Admin/CEO gets 403 on each of these, even for a permission they hold.
  - AU9 (last-admin protection) is unchanged and still applies to an Admin acting on Admin.
  - Each refused attempt is audited under AU22 (status 403, with `{actor, target, action}`) and holds no password or session value.
  `serves:` D-074 safe default, D-072#4. *Re-derive:* a custom group holding `users.manage` + `groups.manage`: try each refused action
  in turn and read the store before/after; an Admin does the same actions -> allowed; mutation: skip the held-permission check, or
  skip the Admin-membership check -> the matching test fails.

### Groups and permissions

## 4. What exists and what is missing

- Exists on `wave/t204-auth-fix1` (53 code/test/config files): `schema/auth.py` (157), `auth/{__init__,access,accounts,audit,config,context,db,defaults,groups,passwords,policy,ratelimit,sessions}.py` (4, 162, 202, 33, 79, 15, 159, 45, 130, 48, 107, 73, 84 lines), `cli_auth.py` (46) and `cli.py` +2, `ui/{auth_middleware,auth_view,admin_view,credential_guard,project_view,routers,routes_admin,routes_auth,routes_project_access}.py`, `ui/app.py` +126/-more (router registration moved to `ui/routers.py`, card helpers to `ui/project_view.py`; `app.py` goes from 300 to 220 lines), `ui/routes_live.py` +11, `ui/routes_project_edit.py`, `ui/routes_credentials.py`, `ui/routes_settings.py`, `ui/theme.py` +68, `.dockerignore` (`.auth/`, `**/.auth/`), `.gitignore`, `docker/entrypoint.sh` (`--no-access-log`), `.env.example` (+19 keys, no values), `pyproject.toml`+`uv.lock` (`argon2-cffi==25.1.0`), and 17 test files (`tests/test_ui_auth_*.py`, `tests/auth_harness.py`, `tests/auth_login_fixture.py`, `tests/test_auth_deploy_files.py`).
- Cycle 1 status (manifest `qa/manifests/t204-auth.md` on the branch, `Fix cycle: 1 of max 3`): ruff and doctor clean; affected set `1 failed, 702 passed, 1 skipped` (the failure, `test_au3_bad_cookie_is_refused_and_creates_nothing[expired]`, was relaxed after the purge fix: re-run it); 29 named mutations all RED; **no full suite** (the checker owes one, `tests/conftest.py` is a full-suite trigger).
- Verdict A cycle 0 (`qa/verdicts/t204-auth.a.md`): AU3 `__Host-` cookie defeated by a plain `at_session` fallback (`auth_middleware.py:27-38`, fixed in F2), AU21 `/env/add` key poisoning (F1, `ui/credential_guard.py::refuse_foreign_key`), group-title XSS (F3). Verdict B cycle 0 (`qa/verdicts/t204-auth.b.md`): AU21 and AU23 failed (`.auth/` not in `.dockerignore`, fixed in P4). Evidence dirs on master: `qa/evidence/browser-t204-auth-2026-10-07-checker-b/` (report.json + 22 PNG + persona folders).
- Missing before a PASS:
  1. **AU1 dependency gate is CLEARED** by D-074(c) (`docs/DECISIONS.md` line 2218, "Password hashing uses `argon2-cffi==25.1.0`... The scrypt fallback is not used" and `Changes-authorized` names the dependency); the fix1 manifest's "Merge prerequisite (not yet met)" text is stale: update it.
  2. **AU19 Host allow-list** is not on the branch: it lives on `wave/at758-759-security` (`ui/helpers.py` +57, `explore_consent.py` +12, `tests/test_ui_origin_guard.py` +76, `tests/conftest.py` +12) which has NO queue row and no PASS (both cycle-0 verdicts are CONTINUE-NEEDED: full suite aborted twice). It is a prerequisite of AU19/AU20 and of any LAN hosting. Decision needed from the dispatcher: queue `at758-759-land` as a parallel unit that lands before this one; if it does not, AU19 must be reported UNMET and the unit cannot PASS. The fix1 tests pass with and without it (`gate_on` sets `AUTOTESTER_ALLOWED_HOSTS=testserver`).
  3. **AU24** Linux run is owed (T-203 rehearsal, SERVER-GATED): report PARTIAL, windows-local evidence only.
  4. **Conflicts with T-205**: fix1 already creates `ui/routers.py` and moves the registration out of `ui/app.py`, which QUEUE assigns to T-205 (G1/TF5 `tests/test_routers_list.py`). The two must not both create it. Proposal: this unit owns `ui/routers.py` (it already exists here and is checked), T-205 then adds its stubs to `ROUTERS`; the QUEUE order "t204 after t205" must be reversed for this file (`qa/contracts/team-foundation.md` TF5 asks for `ROUTERS`; confirm it is acceptable that TF5's evidence file is T-205's).
  5. `core/paths.py` is exactly 300 lines on master; fix1 already moved `auth_db_path`/`ENV_AUTH_DIR` to `auth/db.py`: keep it so.
  6. New route policy rows: every route landed since `c0f99ae1` must have a `ROUTE_POLICY` row (`test_au14_every_route_has_a_policy_row` fails otherwise). Add rows for routes introduced by `land-t203-hosting` (queue/settings routes) after it lands.
  7. Not changed on purpose (open questions for the owner, section 8): whitespace/NUL passwords, SQLite WAL mode, trusting `X-Forwarded-For` behind a proxy, account-lockout denial of service; low items P10, P12, P13, P15, P16.
- Rebase base `850f4ccd` in the manifest; the real base now is master `3a16616c`.

## 5. Files the builder will touch

New (counts are on the branch, `wave/t204-auth-fix1`): `src/autotester/auth/*` (13 files listed above), `src/autotester/schema/auth.py` (157), `src/autotester/cli_auth.py` (46), `src/autotester/ui/auth_middleware.py` (155), `auth_view.py` (75), `admin_view.py` (118), `credential_guard.py` (38), `project_view.py` (68), `routers.py` (61), `routes_admin.py` (151), `routes_auth.py` (100), `routes_project_access.py` (77), `tests/auth_harness.py` (98), `tests/auth_login_fixture.py` (46), `tests/test_auth_deploy_files.py` (33), `tests/test_ui_auth_{accounts,cli_and_limits,escalation,groups,hardening,login,surface,survivors}.py`.
Existing on master (current counts): `src/autotester/ui/app.py` (300), `src/autotester/cli.py` (295, +2 lines fits), `src/autotester/ui/theme.py` (152), `src/autotester/ui/routes_settings.py` (98), `src/autotester/ui/routes_credentials.py` (221), `src/autotester/ui/routes_project_edit.py` (257), `src/autotester/ui/routes_live.py` (67), `tests/conftest.py` (140, protected: auto-login + audit redirect only), `tests/test_ui_env_editor.py` (270), `tests/test_ui_healthz.py` (79), `tests/test_ui_project_intake.py` (250), `.env.example` (38), `.dockerignore` (32), `.gitignore` (78), `docker/entrypoint.sh` (22), `pyproject.toml` (74), `uv.lock` (2435), `docs/MAP.md` (349).
Total 53 files (fix1 diff minus its 3 qa files). If `at758-759-land` is merged as part of this unit instead of separately, add `src/autotester/ui/helpers.py` (253), `src/autotester/stages/explore_consent.py`, `tests/test_ui_origin_guard.py`, `tests/test_credential_run_approval.py` (287).

## 6. Test scope

`uv run pytest tests/test_ui_auth_login.py tests/test_ui_auth_accounts.py tests/test_ui_auth_groups.py tests/test_ui_auth_surface.py tests/test_ui_auth_escalation.py tests/test_ui_auth_hardening.py tests/test_ui_auth_cli_and_limits.py tests/test_ui_auth_survivors.py tests/test_auth_deploy_files.py tests/test_ui.py tests/test_ui_healthz.py tests/test_ui_origin_guard.py tests/test_ui_error_pages.py tests/test_ui_env_editor.py tests/test_ui_project_intake.py tests/test_credential_run_approval.py tests/test_env_loading.py tests/test_permission_coverage.py`
Plus `uv run ruff check src tests scripts`, `uv run autotester doctor`, `uv lock --check`. The checker, not the builder, runs the full suite.

## 7. Reachable test cases per criterion (happy path first)

| Criterion | Happy path | Then |
|---|---|---|
| AU1 | sign-up stores an argon2id hash; a correct password verifies | length policy 10..128; needs-rehash; no plaintext anywhere (store, audit, log) |
| AU2/AU3 | login sets the session cookie; a wrong email and a wrong password give the same page/timing class | hosted: only `__Host-at_session`; plain HTTP dev uses `at_session`; expired/unknown cookie refused |
| AU4/AU5 | logout deletes the server session; 5 failures lock for the window | per-address and signup limiters, bounded table |
| AU6/AU7 | open signup gives zero permissions; first admin by D-074(d) | hosted unset promotes nobody; loopback dev first account is admin |
| AU8/AU9/AU27 | admin acts on any account; last admin protected | grant-only-what-you-hold escalation table |
| AU10-AU13 | groups additive; four defaults seeded once; one `authorize()`; scope hides existence | 403 vs 404 per scope |
| AU14-AU18 | every route has a policy row; unauthenticated reach only login/signup; gate cannot be disabled by accident; Origin guard before auth | |
| AU19/AU20 | Host allow-list on every request, hosted config explicit | needs `wave/at758-759-security` |
| AU21-AU25 | credential values shown only to `credentials.view`; audit has no secrets; `.auth/` ignored; paths portable; existing UI unchanged for an authorized user | |
| AU26 | signup, login, pending, admin flows work in a real browser (checker's Mode D, the builder does not run a browser) | |

## 8. Gate answers

- `docs/DECISIONS.md` D-074 (line 2218), verbatim: "(c) **Password hashing uses `argon2-cffi==25.1.0`.** It is the new dependency for T-204 AU1. The scrypt fallback is not used." and "(d) **The first admin is a fixed email**, set through `AUTOTESTER_FIRST_ADMIN_EMAIL`... With the variable unset, the hosted server must not auto-promote the first signup. Local dev keeps first-account-admin." and "(e) **Cookie Secure is off (`AUTOTESTER_COOKIE_SECURE=0`) only until the domain and HTTPS exist.**" `Approved-by: Umesh (chat, 2026-10-07)`.
- D-072 (line 2170) authorizes the auth modules and the login mechanism; QUEUE note: "the login mechanism is NOT a HUMAN_GATE (answered by D-072)".
- P5 escalation rule (Admin-only: Admin/CEO membership, `users.manage`, `groups.manage`, `settings.manage`, `credentials.view`): recorded in the manifest as a **default Umesh may change**; no `Answered:` line exists. Needs the owner's confirmation (section 9 of the dispatcher's report) but does not block the build.
- `qa/gates/write-policy-tier.md:4`: the account's rights are the boundary, not to be re-litigated (AU15).
- No gate file exists for the first admin's email value: Umesh sets `AUTOTESTER_FIRST_ADMIN_EMAIL` in the server's `.env`. unknown for this machine until he gives it (do not invent one; never print it).

## 9. UI surface and persona walk

- **AU26 — Signup, login, pending and admin flows work in a real browser.** Mode D with the checker's own browser: sign up a first
  account (lands as admin), sign up a second (sees the waiting page), admin ticks a group for it (second account reaches its default
  page on its next click), disable it (next click returns to login), delete it. Zero unexplained console errors. Persona walks for the
  spec user types touching these flows: **tester** reaches the shared-with-me page in <= 2 clicks from login, **dev** reaches their own
  project, **lead** is not shown admin controls. Every form control has a visible label and is keyboard-operable. Evidence under
  `qa/evidence/browser-t204-*-checker/`. `serves:` D-072#3, D-072#4, spec user types.

Persona walk: required (new signup with no group/pending, tester (`@shared` only), developer (`@own`), sub-admin (`@assigned`), Admin/CEO), per the contract table above; the sign-up, sign-in, pending-access page, admin users page, groups page with the 19 checkbox permissions, project access page and navigation per type. Browser lane (max 1); one checker, driven by the checker's Mode D on a scratch data root. Prior evidence to compare against: `qa/evidence/browser-t204-auth-2026-10-07-checker-b/`.

## 10. Dependencies and conflicts

- Must land first: `land-t203-hosting` (shared `core/env.py`, `tests/conftest.py`, `.env.example`, `docker/entrypoint.sh`, `ui/routes_live.py`) and the AT-758 Host allow-list unit (AU19). QUEUE also says `after: t205-g10-headroom`: see item 4 above, the dispatcher decides; the sequence that gets login fastest is `land-t203-hosting`, then this unit (it already contains the router-list move), then T-205 rebased on `ui/routers.py`.
- Shared files, proposed single owner:
  - `ui/routers.py`, `ui/app.py`: this unit (T-205 afterwards adds its stubs to `ROUTERS`, no second list).
  - `pyproject.toml`, `uv.lock`: `t202-litellm-provider` first, this unit runs `uv lock` on top (argon2 only), never hand-merged.
  - `tests/conftest.py`: `land-t203-hosting`, then this unit, then `at758-759-land`.
  - `.env.example`, `docker/entrypoint.sh`: `land-t203-hosting`, then this unit.
  - `ui/routes_project_edit.py`, `ui/routes_credentials.py`, `ui/routes_settings.py`, `ui/theme.py`: this unit; T-198 (zip/Drive intake), T-201b (test button) and T-206 (live view/settings) rebase on it and add their `ROUTE_POLICY` rows.
  - `auth/policy.py`: every later route-adding unit (T-197, T-198, T-199, T-200, T-201, T-206) appends a row for its routes; this unit owns the table.
  - `schema/project.py`: T-205 owns it; this unit adds nothing to `Project`.
  - `ui/routes_live.py` (+11): this unit after `land-t203-hosting`.
  - `docs/MAP.md`: regenerated, never hand-merged.

## 11. Budget and process rules

- Check budget for this tier: L = 45 min per checker (two checkers, A and B). The builder runs NO full suite (the checker owes it); it runs only the test files in section 6, `uv run ruff check src tests scripts` and `uv run autotester doctor` (no CLI `-q` on pytest, AT-503).
- Falsification (mutation) only in a throwaway copy of the tree under `.work/`, never in the bound tree; restore nothing by hand because nothing was changed.
- Kill only PIDs the builder itself started (record them). Never `taskkill`/`Stop-Process` by image name; a host-wide python/uv kill is AT-820.
- No `cd X && cmd`: use `git -C <dir>`, absolute paths or the tool's working directory.
- Design rules (CLAUDE.md, enforced by `autotester doctor`): file <= 300 lines, function <= 50 lines, one-job module docstring, every shape a Pydantic model in `schema/` with `extra="forbid"`, one concept one place, no `*_v2`/`*_new`, scratch and evidence under `.work/`, model calls only through `providers.base.Provider`, prompts are files.
- Credentials: values only in the one repo-root `.env` (gitignored); print key names, never values; never put a value in a test, fixture, log, screenshot or commit.
- The maker never edits `qa/contracts/`. Contract wording problems go verbatim into `qa/feedback-inbox.md`. Only `/checker` passes a unit.
- Commit before the verdict is requested (`qa/gates/commit-before-verdict.md`, C10): the manifest names the exact commit sha; `Status: ready-for-check` with `Fix cycle: N`; the checker answers in `qa/verdicts/<slug>.md` with `Cycle checked: N`.
- Issue ids: renumber any issue row to start after the max AT id on the branch you land on, re-read `qa/issues.jsonl` immediately before the commit (master max was AT-823 at 3a16616c); `qa/issues.jsonl` is `merge=union`, so a duplicate id is not caught by git. The checker owns issue status.
- `docs/MAP.md` is generated: never hand-merge it. After the final rebase run `uv run autotester map`, then `uv run autotester doctor`.
- Push: none by the builder. The checker pushes `origin master` after its PASS (D-007).
- The builder reports with: files changed, the exact commands run with their output lines, any criterion it could not evidence and why. A claim without a re-run is not done.
