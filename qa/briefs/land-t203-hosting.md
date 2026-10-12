# Brief - land-t203-hosting (re-land of the hosting slice as a local deployment, D-081 item 4)

Readiness pass written 2026-10-11 against master `3a16616c`. Self-contained: the builder needs nothing from the dispatching session. Items marked `unknown` are not stated anywhere in the repo.

## 1. Policy and tier

Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Dual check: no
Trigger for L: concurrency (`src/autotester/ui/run_queue.py` slot accounting and the lock, AT-785/AT-787), config (`docker/compose.prod.yml`, `.env.example`), env loading (`src/autotester/core/env.py`) and a protected-file edit (`tests/conftest.py`). Dual check is `no`: no `security|auth|tenancy|prod-write <path:line>` trigger (the prior verdict was a single checker, `qa/verdicts/t203-hosting.md`). The auth/tenancy half of hosting is T-204.


## 2. Root and base

- Root: `D:/autoTesting`. Base: master `3a16616c`.
- Branch: **re-land `wave/t203-hosting`** as a new branch `wave/land-t203-hosting` from master. Source: the exact code commit a checker PASS reviewed, `9a644597` (checker PASS at `66f8b98c`, cycle 1, `qa/verdicts/t203-hosting.md`; branch tip `66f8b98c`; merge-base with master `7782df41`). D-080 item 1: merge only that commit's code, not the qa-only commits. Reason: the slice is built, fixed and PASSed; it only conflicts with master. Worktrees and `integrate/*` are inputs only.
- A fresh checker cycle on the re-landed commit is required (queue row `land-t203-hosting`, `qa/QUEUE.md` line ~31: "doctor, ruff and the affected tests must be clean").

## 3. Acceptance criteria (verbatim from `qa/contracts/hosting.md`)

Scope of this unit: the rows the slice PASS covered or deferred legitimately. HO4, HO5, HO6, HO8, HO12, HO34, HO35, HO36 and HO22-HO33 are NOT in this unit (the PASS left them open: BLOCKED-CAPABILITY because Docker is down on this machine, SERVER-GATED, or owned by T-204/Group 10). HO15 (page), HO19 (`project.run`) and HO21 (per-user scoping) are in scope only for what needs no login; their login-dependent halves wait for T-204 and must be stated as PARTIAL, never claimed.

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

- **HO7 — Network exposure.** Only 22 (restricted), 80 and 443 are reachable from outside; 8000, 8010, 6080 and 5900 are not published
  by the prod overlay (the dev `docker-compose.yml` stays dev-only and must not be used on the server). *LOCAL* (overlay has no
  `ports:` for those) + *SERVER-GATED* (`nmap` from another host, `ss -ltn`). `serves:` D-072#7, O7.

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

- **HO37 — Design rules.** `uv run autotester doctor` and `uv run ruff check src tests scripts` pass; new files obey the design rules (<= 300
  lines, functions <= 50, one-job docstring, one concept one place, no `*_v2`/`*_new`); the only new top-level paths are under `docker/`,
  `scripts/` and `schema/`/`ui/`/`core/` modules authorized by D-072#2. *LOCAL.*

- **HO38 — No regression of what exists.** `docker.md` D1-D5 still hold for the dev compose; `parallel-run.md` PR1-PR7 and `consent.md`
  are unchanged in behaviour (the queue only changes *when* a run starts); the affected existing tests pass without edits to their
  assertions. *LOCAL.*

## 4. What exists and what is missing

- Exists (slice PASS, `qa/verdicts/t203-hosting.md`, cycle 1 PASS; cycle 0 `qa/verdicts/t203-hosting.r0-1.md`): run queue (`ui/run_queue.py` 228 lines, `ui/run_queue_view.py` 48, `schema/run_queue.py` 49), server settings (`schema/server_settings.py` 33, `store/server_settings.py` 71), `core/env.py` empty-value fix, compose/Dockerfile/Caddyfile/DEPLOY.md/entrypoint, `.env.example` keys, 8 test files (51+ tests). Evidence: `qa/evidence/browser-t203-hosting-2026-10-07-checker/` (report.json plus 7 PNG: queue panel only; queued and running states were seen only in an in-process render).
- Last recorded run: affected set 228 passed, 1 skipped; full suite `1 failed, 2707 passed, 5 skipped, 2 deselected, 14 xfailed` (the failure was not caused by this unit and passed alone).
- Docker daemon is down on this machine: `docker build`, compose up, HTTPS and every BUILD-HOST row are BLOCKED-CAPABILITY. The Docker image and compose are deliverables, not deployed (QUEUE note, D-081 item 4). The contract has no Windows-local row; the owner's wish ("host on this machine for now") is the next unit `t203-local-deploy` (after this unit and T-204), not this one.
- Conflicts against master `3a16616c` (from `git merge-tree`): (1) `src/autotester/ui/routes_runs.py` content conflict: master added `cat = catalog(...)` and passes `cat` into the run; the branch moved execution into the queued call (`_run_queued`) and the request only enqueues (HO16). Resolution: take master's `cat` plumbing and keep the branch's queue-only request; `cat` must be computed where the queued runner needs it. (2) `docs/MAP.md`: regenerate with `uv run autotester map`, do not hand-merge. `ui/app.py` is at the 300-line cap on master and the branch adds 10 lines: take master's `app.py` plus only the minimum lines the queue needs (lifespan `get_queue()` recovery at `ui/app.py:70` of the branch); move anything else out so `doctor` stays clean, and leave the router-list move to T-205 (QUEUE note). `ui/routes_report.py` is 299 lines on master and the branch adds 8: relocate code to `ui/run_queue_view.py` to stay <= 300.
- Issue renumbering: the branch's issue rows AT-782..AT-793 (12 rows) collide with master (`qa/issues.jsonl` max is AT-823 at `3a16616c`; AT-782..AT-793 already exist there). Renumber these 12 rows to AT-824..AT-835 (reserved for this unit; `t202-litellm-provider` takes AT-836..AT-842), and update every reference in the manifest, the checkpoint and test docstrings/comments that cites the old ids (AT-782 canaries, AT-783 empty env, AT-784 compose domain, AT-785 slot release, AT-786 conftest re-raise, AT-787 low items, AT-788 open rows, AT-789 RU1 wording, AT-790 restart misreport). Re-read `qa/issues.jsonl` immediately before the commit.
- Still open on purpose, record in the manifest and do not hide: AT-788 rows (HO4/5/6/8/10 Linux/12/15 page/19 `project.run`/21 scoping/34-36), AT-789 (`qa/contracts/ui-run.md` RU1 wording, the checker amends), AT-787 remainder, AT-790 (restart after a failed queue write may re-run an entry).

## 5. Files the builder will touch (current line counts on master `3a16616c`; branch-side counts in the second list)

Existing on master: `src/autotester/ui/routes_runs.py` (204), `src/autotester/ui/app.py` (300, AT CAP), `src/autotester/ui/routes_report.py` (299, near cap), `src/autotester/ui/routes_live.py` (67), `src/autotester/ui/routes_sources.py` (261), `src/autotester/core/env.py` (87), `tests/conftest.py` (140, protected file), `tests/test_env_loading.py`, `.env.example` (38), `Dockerfile` (33), `docker/entrypoint.sh` (22), `docs/MAP.md` (349), `.gitattributes`, `qa/issues.jsonl` (854).
New (from the branch): `src/autotester/ui/run_queue.py` (228), `src/autotester/ui/run_queue_view.py` (48), `src/autotester/schema/run_queue.py` (49), `src/autotester/schema/server_settings.py` (33), `src/autotester/store/server_settings.py` (71), `docker/Caddyfile` (27), `docker/DEPLOY.md` (174), `docker/compose.prod.yml` (74), `tests/test_hosting_config.py` (80), `tests/test_hosting_deploy.py` (152), `tests/test_run_queue.py` (287), `tests/test_run_queue_resilience.py` (93), `tests/test_server_settings.py` (109), `tests/test_ui_runs_queue.py` (196).
Total 27 code/test/config files (+ the unit's own manifest/checkpoint). `tests/conftest.py` is protected: the edit is the `_inline_run_queue` fixture only (AT-786), nothing else.

## 6. Test scope

`uv run pytest tests/test_run_queue.py tests/test_run_queue_resilience.py tests/test_ui_runs_queue.py tests/test_server_settings.py tests/test_hosting_config.py tests/test_hosting_deploy.py tests/test_env_loading.py tests/test_ui_runs.py tests/test_ui_runs_live_case_approval.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_serial_entry_mix_live.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_ui_runs_serial_resilience.py tests/test_credential_run_approval.py tests/test_coverage_wiring.py tests/test_ui_credential_safety.py tests/test_ui_origin_guard.py tests/test_ui_healthz.py tests/test_ui.py tests/test_ui_error_pages.py tests/test_ui_credential_exemption_scope.py`
Plus `uv run ruff check src tests scripts`, `uv run autotester doctor`. Any test that drives `/run` is affected (the request now only enqueues): `git grep` the importers of `core/env.py` and of `run_queue` and add exactly those files.

## 7. Reachable test cases per criterion (happy path first)

| Criterion | Happy path | Then |
|---|---|---|
| HO16 | pressing Test returns the redirect before the run executed (`test_pressing_test_returns_the_redirect_before_the_run_has_executed`); a persisted queue entry exists | restart recovers `running` rows to `interrupted` at startup |
| HO17 | two members pressing in the same instant cannot both claim the last slot | per-project single flight; cap from `max_concurrent_runs` (default 2) |
| HO18 | a finished run releases its slot and the next waiter starts | full disk (`_persist` logs, never raises), `SystemExit`, `CancelledError` still free the slot |
| HO20 | two runs do not oversubscribe RAM/browsers | cap honoured |
| HO15 | settings validate, audit, precedence env vs file | page and `settings.manage` need T-204: report PARTIAL |
| HO19 | queued run re-checks credentials/provider/consent exactly as before | `project.run` needs T-204: PARTIAL |
| HO21 | queue panel on the report page shows `requested_by` and `trigger` | per-user scoping needs T-204: PARTIAL |
| HO1 | `.dockerignore` keeps the six canaries out | a dropped rule is noticed by the test itself |
| HO2 | empty inherited env value does not shadow `<data>/.env` | |
| HO3/HO10/HO14 | healthz source root is the package; no module-level `fcntl`/`pwd`, no drive letter; Playwright tag equals `uv.lock` | |
| HO7/HO9/HO11/HO13 | compose publishes 8000 on 127.0.0.1 only; `.env.example` has every key and no value; DEPLOY.md steps match code; `AUTOTESTER_DOMAIN` defaults to `localhost` | |
| HO37/HO38 | doctor and ruff clean; no existing assertion edited; the three named tests keep their detection power | |

## 8. Gate answers

- `qa/gates/t203-host-and-dns.md:13`: `Answered (local-machine part only): 2026-10-10 - host locally for now - D-081`. Line 11: `STILL OPEN: the real server host and the DNS name. No Answered line for this part. Owed by Umesh.` The open part blocks only the hosted check (HO34-HO36), not this unit.
- `docs/DECISIONS.md` D-081 line 2332 item 4: "T-203 proceeds as a local deployment on the dev machine."
- D-072 (line 2170) authorizes the Group 10 split modules; `qa/gates/write-policy-tier.md:4` (account permissions are the boundary) is not touched.
- Docker-dependent rows (HO1 BUILD-HOST half, HO4, HO5, HO6): no answer needed; they stay BLOCKED-CAPABILITY while the daemon is down.

## 9. UI surface and persona walk

Persona walk: required (tester: presses Run/Test, sees the queued and running state and the cap message; developer/sub-admin: reads the queue panel on the report page). Browser lane (max 1). No login exists yet, so all walks are anonymous on loopback with a scratch data root (`AUTOTESTER_ROOT` under `.work/`), no real run started. Seed a queued and a running entry to see both states (the prior check saw them only in an in-process render). The page must also be re-walked after T-204 lands (login redirect), by that unit.

## 10. Dependencies and conflicts

- Must land first: none (`after: none`; it must land BEFORE `t205-g10-headroom` so `ui/routes_runs.py` and `ui/app.py` are resolved once).
- Shared files, proposed single owner:
  - `src/autotester/ui/routes_runs.py`, `src/autotester/ui/app.py`, `src/autotester/core/env.py`: this unit first, then T-205, then T-204 (QUEUE `owner:` line).
  - `tests/conftest.py`: this unit, then T-204 (adds the auto-login fixture and the audit redirect), then `at758-759-security` (adds an Origin/Host fixture).
  - `.env.example`, `docker/entrypoint.sh`: this unit first, then T-204 (adds `AUTOTESTER_FIRST_ADMIN_EMAIL`, `_COOKIE_SECURE`, `_HOSTED`, `_SESSION_HOURS` and `--no-access-log` on the uvicorn line).
  - `ui/routes_sources.py`, `ui/routes_report.py`, `ui/routes_live.py`: this unit first; T-198 (routes_sources) and T-204 (routes_live +11) after.
  - `src/autotester/ui/routes_runs.py` is also edited by `t202-litellm-provider` (one factory call); this unit lands first.
  - `docs/MAP.md`: regenerated, never hand-merged.
- Exclusive: T-197, T-199, T-201, T-206, T-200: no direct file overlap; T-200 reads the run queue this unit creates (`after: land-t203-hosting` for its enqueue seam).

## 11. Budget and process rules

- Check budget for this tier: L = 45 min. The builder runs NO full suite (the checker owes it); it runs only the test files in section 6, `uv run ruff check src tests scripts` and `uv run autotester doctor` (no CLI `-q` on pytest, AT-503).
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
