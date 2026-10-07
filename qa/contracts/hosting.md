# Contract — hosting: AutoTester as a website on Ubuntu (T-203), with the run queue, schedule, report-mail and video-intake rows (D-072)

**Covers:** goal task T-203 (hosting), plus the rows D-072 added around it (run queue and concurrency setting, schedule, reports by
email, video upload limit and Drive link). Each criterion names the unit that owns it. **Owner:** /checker. **Status:** ACTIVE (2026-10-07).
**Criticality:** CRITICAL for the secret and exposure rows (HO1-HO3, HO7, HO12, HO13); HIGH elsewhere. Tier L; the secret-handling rows
(HO1-HO3) and the exposure rows are judged by a **dual check**.
**Serves:** D-071 (6), D-072 items 6-10 and 12; intent O7; spec R16 and R17 must not regress; `docker.md` D6.
**Depends on:** `auth.md` (permissions `settings.manage`, `live.view`, `live.control`, `project.run`, `schedule.manage`, `report.view`,
`video.upload`), `consent.md`, `parallel-run.md`, `docker.md`.

## Unit ownership (the proposal split, resolved)

| unit | rows | note |
|---|---|---|
| **T-203** (hosting) | HO1-HO21, HO34-HO38 | image, deploy, `.env.example`, settings store, run queue and concurrency, rehearsal, backup |
| **Group 10 / T-200** (schedule) | HO22-HO24 | schedule model and scheduler; they enqueue through T-203's queue, so they cannot be built first |
| **Group 10 / T-201** (on-demand button, report to whoever clicked) | HO25-HO29 | website report scoping and the per-user email preference; SMTP transport (HO27, HO29) is built with the first mail row and is shared |
| **Group 10 / T-198** (video intake) | HO30-HO33 | the upload endpoint, Drive fetch and their limits; the **setting** itself lives in T-203's HO15 |

Unit ids follow `.goal/goal.json` at build time. A row binds to whichever unit builds that feature. A T-203 PASS never closes a
Group 10 row.

## Verification classes

`LOCAL` = the checker runs it on the dev host (Windows). `BUILD-HOST` = needs Docker; if Docker is unavailable to the checker the row is
`BLOCKED-CAPABILITY`, never PASS. `SERVER-GATED` = needs the real Ubuntu server, a domain or SMTP relay; judged at the go-live
rehearsal (a HUMAN_GATE, D-071), and it gates the **go-live**, not the unit's code PASS.

## Criteria

### A. Image, deploy, exposure (T-203)

- **HO1 — No secret in the image, and the guard cannot go vacuous.** (`docker.md` D6.)
  - *LOCAL:* a test evaluates the repo's real `.dockerignore` against the actual file tree plus planted canaries (`.env`, `.env.local`,
    `projects/x/runs/r1/secret.txt`, `profiles/x/Cookies`, `.work/auth/users.json`, `.work/audit.jsonl`) and asserts every one is excluded
    and `.env.example` is not. Mutation: delete the `**/.env` rule -> the test fails.
  - *BUILD-HOST:* build with the canaries in the context; `docker run --rm img` finds no `.env*` other than `.env.example`, no `profiles/`,
    `projects/`, auth store or audit file anywhere in the filesystem, and `grep -r <canary value>` over the exported image filesystem finds
    nothing. `docker history --no-trunc` shows no `ENV`/`ARG` carrying a key.
  `serves:` D-072#7, O7, docker.md D6.
- **HO2 — Runtime secrets enter only by `env_file` and the data volume.** The prod compose overlay has no inline secret value; secrets
  come from `env_file: /etc/autotester/server.env` (0600) and `/data/.env`; `scripts/check_no_secrets.py` (or the project's equivalent
  secret scan) passes over `docker/`; `docker inspect` of the *image* shows none; no secret appears in `docker logs` after a run
  (canary grep). *LOCAL* (scan) + *BUILD-HOST* (inspect, logs). `serves:` O7, R16.
- **HO3 — Data root is a volume; the app tree is read-only in practice.** The container starts with `AUTOTESTER_ROOT=/data`;
  `projects/`, `profiles/`, `.env`, `.work/` (audit, auth store, queue, settings) resolve under it; after a run `docker diff` shows nothing
  changed under `/app`; `/healthz` source-freshness reads the package path, not the data root. `serves:` D-072#7.
  *BUILD-HOST.*
- **HO4 — Persistence across restart and recreate.** Create a project, a user + group, a queued run, a setting change; then
  `docker compose restart` and `down && up`: projects, cases, reports, the logged-in browser profile, users, groups, settings and the
  queue are intact. *BUILD-HOST* (scripted before/after listing); the same check on the server at the rehearsal. `serves:` D-072#7.
- **HO5 — Supervision.** Killing Xvfb, x11vnc, websockify or uvicorn inside the container is followed by an automatic restart within
  15 s and a successful `/healthz`; a killed container is restarted by Docker; a rebooted host brings the stack back without a manual
  command. *BUILD-HOST* (process kills); reboot is *SERVER-GATED*. `serves:` D-072#7.
- **HO6 — Hardening.** The app runs as a non-root user (or the deviation and its reason are recorded), `no-new-privileges`, memory and
  cpu limits, log rotation. `--no-sandbox` is accepted only with this boundary. *BUILD-HOST.*
- **HO7 — Network exposure.** Only 22 (restricted), 80 and 443 are reachable from outside; 8000, 8010, 6080 and 5900 are not published
  by the prod overlay (the dev `docker-compose.yml` stays dev-only and must not be used on the server). *LOCAL* (overlay has no
  `ports:` for those) + *SERVER-GATED* (`nmap` from another host, `ss -ltn`). `serves:` D-072#7, O7.
- **HO8 — Sizing is measured, not asserted.** One real run (and one with two concurrent runs, HO17) records peak container RSS, peak
  CPU, wall-clock, `shm` use and the `ParallelPlan` (`n`, `bound_by`) into `qa/evidence/t203-sizing.md`. The default concurrency of 2
  stays unless that evidence shows it is unsafe on the real box. *SERVER-GATED.* `serves:` D-072#6.
- **HO9 — `.env.example` documents every knob and holds no value.** It lists, each with a one-line comment: `AUTOTESTER_ALLOWED_HOSTS`,
  `AUTOTESTER_ALLOWED_ORIGINS`, `AUTOTESTER_HOSTED`, `AUTOTESTER_COOKIE_SECURE`, `AUTOTESTER_FIRST_ADMIN_EMAIL`,
  `AUTOTESTER_AUTH_DISABLED` (marked dev-only), run concurrency, upload limit, the SMTP keys (`AUTOTESTER_SMTP_HOST`, `_PORT`, `_USER`,
  `_PASSWORD`, `_FROM`, `_TLS`), `AUTOTESTER_TIMEZONE`, and `AUTOTESTER_MODEL` (`providers-litellm.md`). A drift test greps `src/` for
  every `AUTOTESTER_[A-Z_]+` the code reads and fails if one is missing from the file; a second test fails if any non-comment line has a
  non-empty value that looks like a secret. Values in the settings store (concurrency, upload limit) are defaults documented here, and
  the admin page wins at runtime (HO15). *LOCAL.* `serves:` D-072#12, D-072#6.
- **HO10 — Cross-platform: Windows dev, Ubuntu prod.** New code uses `pathlib` / `core.paths`; no hardcoded `/data`, drive letter or
  separator outside `docker/`; no `fcntl`/`pwd` import at module level; subprocesses and signals have a Windows path. The new tests pass on
  Windows (the checker's host) and inside the image on Linux, the latter recorded in `qa/evidence/t203-linux-run.md`. *LOCAL* +
  *BUILD-HOST.* `serves:` D-072#7.
- **HO11 — The deploy guide exists and is exercised.** `docker/DEPLOY.md` (new path under the existing `docker/`) covers, in order: server
  prerequisites (Ubuntu LTS, Docker, UFW), the two env files, building on the server from a tag (the image never leaves the box; the repo
  is public), seeding `projects/`, **creating the admin account before the port is exposed to the team** (on the hosted server the first admin is the
  account whose email equals `AUTOTESTER_FIRST_ADMIN_EMAIL`, not the first account created; with it unset nobody is auto-promoted and
  the admin is created through the CLI, `auth.md` AU7; keep 80/443 closed until done), setting the Host/Origin keys, the interim without a domain
  (HO13), backup and restore (HO36), upgrade, and rollback. It holds no secret and no real hostname beyond what Umesh accepts publishing.
  A checker follows the guide literally on a fresh Ubuntu container or VM and records the transcript. *BUILD-HOST* (container follow-
  through) + *SERVER-GATED* (the real server). `serves:` D-072#7.
- **HO12 — The live browser view is gated.** With a proxy in front, `/live`, `/novnc/*` and its websocket require an authenticated
  session: unauthenticated requests get 401/302. Viewing needs `live.view`; sending input needs `live.control` (a view-only instance for
  the rest); `/live` embeds a same-origin URL (no `http://localhost:6080`). The proxy asks the app (`GET /auth/check`, an authenticated
  route that returns the identity or 401) rather than keeping its own list. A run is watchable: with `/live` open, a real case shows the
  Chromium window moving at an Xvfb size >= the viewport. `serves:` D-072#7, O7. *LOCAL* (route + permission tests), *SERVER-GATED*
  (curl/websocket probe, recording).
- **HO13 — HTTPS and the cookie.** Once a domain exists: `http://` redirects to `https://`, certificate valid, HSTS and the standard
  security headers present, TLS 1.2+ only; `AUTOTESTER_ALLOWED_ORIGINS=https://<host>` set and `*` refused. Until then (Umesh: "the
  domain comes later"), the guide describes the one allowed interim: private-network or tunnelled access with
  `AUTOTESTER_COOKIE_SECURE=0` set explicitly, never exposed to the public internet; startup logs which mode it is in. *LOCAL* (config
  tests) + *SERVER-GATED* (testssl / curl -I). `serves:` D-072#7, auth.md AU3.
- **HO14 — Playwright coupling.** The base image tag equals the Python `playwright` version locked in `uv.lock`; a script or test
  compares them. *LOCAL.*

### B. Settings, run queue, concurrency (T-203)

- **HO15 — Server settings are an admin setting, validated, audited.** A `ServerSettings` model (`schema/`, `extra="forbid"`) stored
  under the data root holds `max_concurrent_runs` (default **2**) and `max_upload_bytes` (default **2 GiB** = 2147483648). A page
  reachable only with `settings.manage` edits them. Validation: concurrency is an integer 1..64, upload limit an integer between 1 MiB and
  64 GiB; anything else (0, negative, text, float, empty, overflow) is refused with a message that does not echo secret data and stores
  nothing. A change applies to the next dispatch / next upload **without a restart**, and writes an audit line (`auth.md` AU22). Missing
  or corrupt settings fall back to the defaults and say so. `serves:` D-072#6, D-072#10. *LOCAL.*
  *Re-derive:* boundary-value tests (0, 1, 64, 65, "2", "x", 2^63); change 2 -> 1 with two queued runs and see the next start obey it.
- **HO16 — A run request is queued, not run in the web request.** `POST /projects/{slug}/run` creates a persisted queue entry
  (`{id, project, requested_by, trigger, status, enqueued_at, started_at, finished_at, reason}`) and returns at once (redirect to a run page
  showing `queued` with its position, then `running`, then `done`/`failed`/`refused`/`interrupted`). Entries start FIFO. Nothing is dropped
  silently: a documented per-project queue-depth cap returns 409/429 with the reason when hit. The queue survives a process restart.
  `serves:` D-072#6. *LOCAL.* *Re-derive:* enqueue 3, restart the app object, list; mutation: run inline -> the "returns at once" test fails.
- **HO17 — The server-wide cap and the per-project single flight.** At no time are more than `max_concurrent_runs` runs `running`, and at
  no time are two runs of the **same project** `running`; the rest wait `queued`. Verified with a fake runner that blocks on an event:
  start 3 projects with a cap of 2 -> exactly 2 `running`, 1 `queued`; start 2 runs of one project with a cap of 2 -> 1 `running`, 1
  `queued`; raising the cap to 3 starts the waiting one without a restart. Two simultaneous requests cannot both claim the last slot.
  `serves:` D-072#6. *LOCAL.* Mutation: allow two same-project -> fails; compare `>=` with `>` on the cap -> fails.
- **HO18 — A slot is always released.** The slot and the project's single flight are freed after a normal finish, after an exception
  in the runner, after cancellation, and after the worker process dies (a lease/heartbeat expiry, not a Linux-only `flock`). On startup, a
  queue entry left `running` by a dead process becomes `interrupted` with a reason; it is **not** re-executed automatically, and it frees
  its project. The mechanism works on Windows and Linux (HO10). `serves:` D-072#6. *LOCAL.*
- **HO19 — The queue is not a way around the gates.** A queued run executes through the same pipeline function and the same consent,
  `RunApproval`, `write_policy` and model-spend checks that a direct run used (`consent.md`, D-068). `project.run` is checked at
  enqueue **and again at start**; a user who was disabled or lost the permission in between gets `refused` with that reason and no
  browser is launched. A refusal never leaves a run that looks like a PASS. `serves:` D-072#6, spec R17, auth.md AU15. *LOCAL.*
- **HO20 — Concurrent runs do not oversubscribe the machine.** `ParallelPlan` (`parallel-run.md` PR1) sizes each run from the free
  RAM/CPU *at the moment it starts*, after subtracting what the other running runs are using or have been granted; runs that start at the
  same instant are planned one after the other under a planning lock (or the budget is divided by the cap). The sum of planned contexts
  across running runs never exceeds the measured budget. `project.max_parallel` still caps cases inside one run and is independent of
  the server cap. `serves:` D-072#6, R20. *LOCAL* with a faked RAM probe; real numbers at HO8.
- **HO21 — Who may see the queue.** The queue and run pages list only runs of projects the viewer may `project.view`; a user sees their
  own requests' status; `requested_by` and `trigger` (`button` | `schedule` | `api`) are recorded on every entry. `serves:` D-072#4,
  D-072#6, auth.md AU13. *LOCAL.*

### C. Schedule (Group 10 / T-200, with T-201 for the button)

- **HO22 — A per-project schedule with three modes.** A `ScheduleConfig` (`schema/`, `extra="forbid"`) per project has
  `mode` in `manual` (button only, the default), `fixed` (one preset daily time, a `HH:MM`), or `custom` (a time the user selects: a
  one-off date-time, or a weekly set of weekdays + `HH:MM`). Each schedule stores an IANA timezone (default `AUTOTESTER_TIMEZONE`, else
  UTC) and is DST-correct (a 02:30 slot on a spring-forward day fires once, not zero or twice). Invalid values (25:00, unknown zone,
  past one-off, empty weekday set) are refused and store nothing. Setting a schedule needs `schedule.manage` on that project.
  `serves:` D-072#9. *LOCAL.*
- **HO23 — The scheduler uses the queue and fires exactly once.** A due slot enqueues one entry (`trigger=schedule`,
  `requested_by` = the schedule's owner) through HO16/HO17, never starting a browser directly. Two scheduler instances, or a restart
  during the slot minute, produce one entry (idempotency key = project + slot). A slot missed while the server was down fires at most
  one catch-up within a documented grace window (default 60 min); otherwise it is recorded as `missed` and visible. `serves:` D-072#9.
  *LOCAL* with an injected clock.
- **HO24 — A schedule has no more rights than its owner.** A scheduled run passes the same approval and permission checks as a button
  run (HO19), evaluated with the owner's rights at fire time; if the owner is disabled, deleted, or lost `project.run`, the schedule is
  paused and the slot recorded `refused`, with the reason on the project page. Deleting the project removes its schedule.
  `serves:` D-072#9, auth.md AU8. *LOCAL.*

### D. Reports (Group 10 / T-201; transport shared)

- **HO25 — The report is on the website, scoped.** A finished run's report opens in the UI for users holding `report.view` on that
  project (`auth.md` AU13), and for nobody else (404 for a project they cannot view). This is the existing report route; the criterion is
  that auth scoping applies to it and to its Excel/HTML exports. `serves:` D-072#8. *LOCAL.*
- **HO26 — Email is a per-user checkbox.** The user profile page has an "Email me run reports" checkbox, stored per user, **default off**
  (checker choice; opt-in avoids unsolicited mail and data egress). The recipient of a run's report is the user who requested it
  (button) or the schedule's owner, only if their box is on **and** they still hold `report.view` on that project at send time. No other
  user receives it. Turning the box off stops the next mail. `serves:` D-072#8. *LOCAL.*
- **HO27 — SMTP is configured from the environment, and its absence is graceful.** `AUTOTESTER_SMTP_*` (HO9) configure the transport; the
  password lives only in the environment or `/data/.env`, is never displayed, logged or audited (it follows `auth.md` AU21 as a
  credential). With no SMTP configured the checkbox shows "email is not configured on this server", runs still finish, and nothing
  raises. TLS (STARTTLS or SSL) is used when `_TLS` is set and certificate verification is on by default. `serves:` D-072#8.
  *LOCAL* (fake SMTP server in-process) + *SERVER-GATED* (real relay).
- **HO28 — The mail carries a link and counts, not product data.** The body holds the project name, run id and time, pass/fail/
  inconclusive counts, the coverage line, and a link to the report on the website (sign-in required). It carries **no attachment, no
  screenshot, no video, no credential value, no page content**; the text passes `Redactor.scrub`. A canary secret and a canary page
  string planted in the run do not appear in the sent message. `serves:` D-072#8, O7, the Vidysea data-boundary rule. *LOCAL.*
- **HO29 — A mail failure never fails or delays a run.** A refused, timed-out or unreachable SMTP server is recorded on the run page
  with a redacted reason, retried a bounded number of times with backoff, and never changes the run's status or blocks the next queue
  entry. No test calls a real SMTP host. `serves:` D-072#8, D-070. *LOCAL.*

### E. Video intake (Group 10 / T-198; the limit is T-203's HO15)

- **HO30 — The upload limit is enforced while streaming.** The upload route reads the body in chunks to disk (memory does not grow with
  the file) and stops at `max_upload_bytes` read from the setting at request time: a file of exactly the limit succeeds; limit + 1 byte
  gets 413, leaves no partial file and no source row; a lying or missing `Content-Length` changes nothing. The upload page shows the
  current limit. Tested with a small limit (for example 5 MiB), not a 2 GiB file; one real >= 1 GiB upload through the proxy is
  *SERVER-GATED*. Requires `video.upload` on the project. `serves:` D-072#10. *LOCAL.* Mutation: trust `Content-Length` only -> fails.
- **HO31 — The proxy does not undercut the setting.** The prod proxy config takes its body-size ceiling from the same value (or a
  documented larger one) so a file within the admin's limit is not refused with 413 by Caddy/nginx; the guide says to raise both together.
  *LOCAL* (config test) + *SERVER-GATED.* `serves:` D-072#10.
- **HO32 — A Google Drive link is fetched by the server, and only Google hosts.** The user pastes a Drive link; the server resolves the
  file id and fetches it itself, as a queued background job, then registers it exactly as an upload (same limit, same ownership). The URL
  must be `https`, with a host exactly `drive.google.com` or `docs.google.com` (and the Google download host the API returns); each
  redirect hop is re-checked against the same rule and may not resolve to a loopback, private or link-local address. Refused, with a
  typed message that does not echo tokens: `http://127.0.0.1/x`, `file:///etc/passwd`, `https://drive.google.com.evil.io/file/d/x`,
  `https://evil.io/?u=https://drive.google.com/...`, a redirect to `169.254.169.254`, a non-Drive path. Requires `video.upload`.
  `serves:` D-072#10, O7. *LOCAL* with a fake HTTP transport (no real Google call in tests).
- **HO33 — The fetch is bounded and honest.** The fetch stops at the same `max_upload_bytes` (partial file removed), has a connect and a
  total timeout, accepts only a video content type, and surfaces its state on the page (`fetching`, `done`, or a typed failure). A link
  the server cannot read (private, deleted, quota page) gives a message saying how to make it viewable or share it with the server's
  Google identity, and never a stack trace. The credential the server uses for non-public files is a server-side secret under
  `auth.md` AU21 rules, never rendered. *Real* Drive fetch of an actual file is *SERVER-GATED* and needs an approved,
  synthetic, non-student video. `serves:` D-072#10. *LOCAL.*

### F. Gates, rehearsal, backup

- **HO34 — Team walkthrough (the T-203 done_check, SERVER-GATED).** A team member opens the server URL, signs up, an admin puts them in a
  group, they sign in, onboard a project, run a case from the queue, see the report; restart keeps the data; the Origin/Host guards
  are configured for the server origin; no secret is in the image (HO1). Checker Mode D, persona walks for **dev** and **tester**.
  `serves:` T-203 acceptance, D-072#7.
- **HO35 — Queue rehearsal on the server (SERVER-GATED).** Two projects started together run at once; a second request for the same
  project waits; changing the concurrency setting to 1 on the admin page makes the next start obey it. Evidence: screenshots and the
  queue listing. `serves:` D-072#6.
- **HO36 — Backup and restore drill (T-203 unit 5; SERVER-GATED).** `scripts/backup.sh` produces an encrypted snapshot of the data
  root; restoring it into a scratch directory and starting a second container on it lists the same projects, users and settings and
  opens a report; the snapshot is unreadable without its passphrase. `profiles/` live sessions are excluded unless Umesh says otherwise.
  The script itself passes `shellcheck`-style review and has no secret. `serves:` D-072#7.
- **HO37 — Design rules.** `uv run autotester doctor` and `uv run ruff check src tests scripts` pass; new files obey the design rules (<= 300
  lines, functions <= 50, one-job docstring, one concept one place, no `*_v2`/`*_new`); the only new top-level paths are under `docker/`,
  `scripts/` and `schema/`/`ui/`/`core/` modules authorized by D-072#2. *LOCAL.*
- **HO38 — No regression of what exists.** `docker.md` D1-D5 still hold for the dev compose; `parallel-run.md` PR1-PR7 and `consent.md`
  are unchanged in behaviour (the queue only changes *when* a run starts); the affected existing tests pass without edits to their
  assertions. *LOCAL.*

## Out of scope / ignore

- Choosing the cloud provider, buying or pointing the domain, creating the Workspace/SMTP/Drive credentials: HUMAN_GATE actions (D-071).
  The code and the guide are judged here; the real server is judged at HO34-HO36.
- Multi-server, high availability, autoscaling, a WAF, an egress allow-list, a separate display per run.
- Cancelling a running run from the UI, priorities between queue entries, per-user quotas.
- Changing `write_policy` semantics (D-053) or the approval mechanics (D-068/AT-570's own fix).
- Local Ollama on the server; sizing advice beyond the measured evidence in HO8.
- Tracker/sheet integration (T-199) and the access-request workflow (T-198 proper); comments.
- Wording and visual polish beyond the labelled, keyboard-operable controls checked by `auth.md` AU26.

## No-fire list (must NOT happen)

- No secret, signed approval, browser profile, run artifact or user store inside an image layer, `docker history`, a log, or an email.
- No port other than 80/443 (and restricted 22) reachable from outside; no unauthenticated noVNC.
- No run started outside the queue; no more than the configured number of concurrent runs; no two concurrent runs of one project.
- No email attachment, screenshot, video, or credential; no mail to a user who cannot view that report.
- No server-side fetch of a non-Google URL; no fetch that follows a redirect into a private address.
- No change to `stages/` beyond what the queue's call site needs; no change to credential-guard logic.
- No live SMTP, Google, or model call in the default test suite.

## Amendment log (append-only; git history is the version)

- 2026-10-07 · init · contract created for T-203 from D-071 (6) and D-072 (6-10, 12). It folds in the maker's HS1-HS19 proposal
  (`.work/plan-golive/T-203-contract-proposal.md`): HS1/HS2 -> HO1, HS3 -> HO2, HS4 -> HO3, HS5 -> HO4, HS6 -> HO5, HS7 -> HO13,
  HS8 -> HO7, HS9 -> `auth.md` AU18-AU20, HS10/HS11 -> HO12, HS12 (single run lock) -> HO16-HO18 as a queue with a configurable cap,
  HS13 -> HO30/HO31, HS14 -> HO36, HS15 -> HO8, HS16 -> HO6, HS17 -> HO14, HS18 -> HO37, HS19 -> HO34. Changed by D-072: the proposal's
  fixed "one run at a time, 409 for the second" became a queue with an admin-set cap (default 2) and one run per project; the Google
  sign-in assumption became email + password (`auth.md`); the schedule, report-mail and video rows are new.
