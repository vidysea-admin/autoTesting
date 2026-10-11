# Brief - t201a-report-delivery (G4 / T-201: website inbox, per-user email, delivery record)

Readiness pass written 2026-10-11 against master `09828f2d` (master had moved to `cc58c988` by the end of the pass; the 09828f2d..cc58c988 diff touches only `qa/` files, re-verify at dispatch). Self-contained: the builder needs nothing from the dispatching session. Items marked `unknown` are not stated anywhere in the repo. Nothing for this unit exists on master or on any branch (checked: `git ls-tree -r` of master, `wave/t204-team-login`, `wave/t200b-scheduled-test`, `wave/t205-g10-headroom`, `wave/land-t203-hosting` has no `delivery/`, `schema/delivery.py`, `stages/report_delivery.py`, `ui/routes_inbox.py`, no `smtplib` import anywhere in `src/` or `tests/`; `src/autotester/sources/email.py` is the T-162 email *ingest* adapter, not delivery).

**Dispatch status: NOT dispatchable on today's master. Phase A is READY the moment `t205-g10-headroom` merges; phase B is HELD on `t204-team-login`; the one live send is HELD for the owner (sections 4 and 10).**

## 1. Policy and tier

Policy-Version: proportional-verification/2026-10-10.9
Tier: L (contract header: "Tier L (auth, outward-facing run, outward-facing email)").
Dual check: **required** (A and B; neither reads the other's verdict first). The contract names the dual check for TT8; this unit owns TT8.
Trigger: `security src/autotester/delivery/email.py` (new file: the only module that may import `smtplib`, holds the SMTP password in memory, opens the outward connection; line numbers do not exist until it is written, the builder records them in the manifest, anchor = the `smtplib` import line and the `send` function) and `auth src/autotester/ui/routes_profile.py` (new: a state-changing session route whose recipient must come from the session). The existing line the builder edits in place is `src/autotester/ui/run_queue.py:181` (`_finish`) with `:104` (`recover`).

## 2. Root and base

- Root: `D:/autoTesting`. Base: master `09828f2da345316f7d290069cf0a980c058b251e` at the time of writing (`git -C D:/autoTesting rev-parse master`). It will move; the builder re-reads it at dispatch and records the sha in the manifest.
- **Cut the branch only after `t205-g10-headroom` has merged to master** (QUEUE `t201a-report-delivery` `after: t205-g10-headroom`, `qa/QUEUE.md:133`). New branch `wave/t201a-report-delivery`, worktree `D:/autoTesting/.worktrees/t201a-report-delivery`. Reason: D-080 item 1 (origin/master is the one trunk; branches are inputs re-landed unit by unit). `wave/t205-g10-headroom` (tip `3ebd2fca`, 0 ahead / 1 behind master) holds the files this unit needs (`store/team_store.py`, `schema/team_enums.py`, `ui/routers.py`, `auth/policy.py`) but has no checker PASS; do not build on it.
- T-203's queue (`schema/run_queue.py`, `ui/run_queue.py`, `ui/run_queue_view.py`) is **already on master** (merge `82bc4954`, `qa/verdicts/land-t203-hosting.md`). Earlier briefs that say it is unmerged are stale.
- No existing branch holds usable work for this unit; start from nothing.

## 3. Acceptance criteria (verbatim from `qa/contracts/team-test-button.md` Status ACTIVE and `qa/contracts/hosting.md`)

Criticality: TT8 CRITICAL; TT7 and TT9 HIGH. Vocabulary the criteria rely on (verbatim from the contract): "**Report label** = one value computed **once** per run (`green` only when verdict counts and coverage support it; otherwise `failed`, `blocked`, `inconclusive` or `low coverage`, R22 carried). The page, the inbox and the message all read this stored value; none re-derives it." and "**Outbox adapter** = the dry-run delivery adapter that appends the would-be message to `<data>/.work/outbox/` and sends nothing. It is the default until the SMTP credentials exist (a HUMAN_GATE, `plan-approved-g10.md` open item 1)."

- **TT7 — The report appears in the website inbox, filtered to the viewer's scope, and the label is computed once (R58).**
  A finished, failed, refused or interrupted run produces **one inbox entry per entitled viewer's view**: `GET /inbox` ("My reports") requires
  a signed-in session (anonymous -> 302 to `/auth/login`, AU16) and lists **only** runs of projects on which the user holds
  **`report.view`** (any scope the user's groups grant, resolved by `authorize`, `auth.md` AU12/AU13). **No new permission key is added**:
  the inbox is gated by session plus the existing `report.view` scope, and the route is in this unit's route-policy dict as such
  (`team-foundation.md` TF4). A report the viewer may not view is absent from the list and its direct URL is the same 404 as a missing run
  (existence is not leaked); a `report.view@own` Developer sees reports of their own projects only; a Tester sees only `@shared` ones; an
  Admin sees all. Each entry shows project, run id, time, who started it (TT3) or "scheduled", the **report label** and a link to the report
  page. **The label is one stored value** computed once in `stages/report_delivery.py` and read by the inbox, the project report page and
  the message (TT8); a blocked, failed or low-coverage run appears with that label and an all-blocked run never reads green (R22 carried). The
  inbox entry is created whether or not any email is sent: the website is the system of record (`hosting.md` HO25). `serves:` intent#O13, O4,
  spec R58, R63, `auth.md` AU12, AU13, AU16, `hosting.md` HO25.
  *Evidence (LOCAL):* `tests/test_inbox_scope.py` — four default users x two projects x `{list, direct URL}` table, asserting list
  membership and 404 vs 200; a run that was `refused` and a low-coverage run appear with their labels; a grep test that `report_label` is
  defined once and the inbox, page and message modules import it. *Mutation:* list all runs without `authorize` -> the scope table fails;
  recompute the label in the message module -> the one-definition test fails.

- **TT8 — Email goes only to a user who ticked "Email me run reports", and the recipient is never request-supplied (R58, CRITICAL).**
  G4 builds the **profile page** (`GET/POST /profile`, session required, Origin-guarded): a per-user checkbox **"Email me run reports"**,
  stored per user, **default off** (`schema/delivery.py` `NotificationPref`, extra="forbid"; `hosting.md` HO26). A report is mailed
  **only** to the user who pressed the button (`requested_by`) or the schedule owner (`team-schedule.md`), **and only if** that user's box is
  ticked **and** they hold `report.view` on the project **at send time**; nobody else is ever a recipient. Turning the box off stops the
  next mail. A `to`, `email`, `recipient` or `cc` field in the POST body or query of the Test button, the profile page or any delivery route is
  **ignored**: the recipient is read from the authenticated identity on the queue entry. The message body is exactly `hosting.md` HO28's
  (project, run id and time, counts, coverage line, the same stored label, a link that requires sign-in; no attachment, screenshot, video,
  credential or page content). **The live SMTP send is gated on credentials** (`plan-approved-g10.md` open item 1, a HUMAN_GATE): until they
  exist the default adapter is the **outbox adapter** (dry-run, writes the would-be message under `<data>/.work/outbox/`, sends nothing),
  the profile page shows "email is not configured on this server" (HO27) beside the checkbox, and **no test and no default code path
  contacts a real SMTP host**. The SMTP adapter is exercised only against an in-process fake server (HO27), and its live use is
  `SERVER-GATED`. *Evidence (LOCAL):* `tests/test_report_email.py` — box off (default) -> outbox empty; box on -> exactly one outbox message
  to that user; box on but `report.view` revoked before send -> empty; two sessions -> the recipient follows the session; a forged
  `to=attacker@x` in the Test POST and in the profile POST -> never in the outbox; a canary secret and canary page string planted in
  the run -> absent from the message; the grep that no module outside `delivery/email.py` imports `smtplib`. `serves:` intent#O13, O7,
  spec R58, D-072#8, `hosting.md` HO26-HO28, `auth.md` AU12. *Mutation:* read the recipient from the form -> the forged-recipient test
  fails; default the box to on -> the default-off assertion fails; message module recomputes the label -> TT7's one-definition test fails.

- **TT9 — Delivery failure is recorded, visible and harmless; no message carries a secret or a link that works without sign-in (R59).**
  Every send attempt writes a `DeliveryRecord` (`schema/delivery.py`, extra="forbid": run id, channel `inbox | email`, recipient user id,
  `status` in `sent | outboxed | failed`, a **redacted** error, attempt count, next retry time). A failed email (refused, timed out,
  unreachable, a fake transport that raises) is **shown on the run page**, retried a **bounded** number of times with backoff (`hosting.md`
  HO29), and **never changes the run's verdict or status, never delays the next queue entry, and never fails the run**. The inbox entry
  (TT7) exists even when every email attempt fails. No message and no inbox row contains a password, token, cookie, API key or `.env`
  value, and every link in a message goes to a route that requires sign-in (an unauthenticated GET to it is 302 to login); the text passes
  `Redactor.scrub`. *Evidence (LOCAL):* `tests/test_delivery_failure.py` — a fake transport raising on every attempt: the run stays `done`,
  a `failed` record exists with a redacted error, attempts == the bound, the run page shows the failure, the inbox entry is present; a
  planted secret never appears in the outbox file or any record; the link's unauthenticated GET redirects. `serves:` intent#O13, O7,
  spec R59, `hosting.md` HO28, HO29. *Mutation:* let a transport exception propagate into the run -> the verdict-unchanged assertion fails;
  include the secret in the error text -> the redaction assertion fails.

### Hosting rows these three lean on (verbatim, `qa/contracts/hosting.md:152-170`)

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

### Delivery clauses other units' criteria hand to this unit (verbatim sentences, `qa/contracts/team-schedule.md`)

- TS5 (T-200 phase B): "...the schedule owner sees the refusal on the project page and in their inbox (G4's delivery module; the email follows the owner's own preference, `team-test-button.md` TT8)."
- TS7 (T-200 phase B): "A scheduled run that crashes, is killed, or ends in a worker death ends `failed` (or `interrupted`, HO18) **with its cause** and appears on the project page, the schedule history and the owner's inbox; it is never absent."

### Also binding (cited, not copied)
`team-foundation.md` TF4 (route-policy dict, no new key), TF7 (portable atomic team store, path-safe names), TF8 (vocabulary home `schema/team_enums.py`); `auth.md` AU12-AU16, AU18, AU21; `core-invariants.md` C1 (schema in `schema/`, `extra="forbid"`), C2 (300/50 lines), C3 (one concept one place), C5 (secrets).

### No criterion yet (checker to add; the builder neither invents nor silently decides these)
1. **A notice with no run.** TS5 (`blocked_no_credentials`, `refused`) and TS7 (`failed` at enqueue) say the schedule owner sees it "in their inbox", but TT7 defines inbox entries only for runs, and a blocked slot creates no run, no run directory and no queue entry. No criterion defines the entry's shape, its id, or whether email follows the preference for it. Same for a Test press refused before the queue: on master `trigger_run` raises HTTP 400/403 from `_prepare_run` before `get_queue().submit` (`src/autotester/ui/routes_runs.py:202-209`), so no queue entry exists. The plan row G7 says "blocked run still delivers" (`docs/plan.md:140`).
2. **Inbox model.** TT7 reads as one stored entry per run with visibility computed at read time (the listing "resolved by `authorize`"), TT9 reads as a `DeliveryRecord` per recipient with channel `inbox`. Proposed reading for the checker to confirm: one stored per-run `ReportEntry` (system of record, label stored once) plus one `inbox`-channel `DeliveryRecord` per entitled user at delivery time for audit; the list is filtered by `authorize(report.view)` at request time, so revoked access hides old entries and later-granted access shows them. Needs a model name in `schema/delivery.py`.
3. **Idempotency.** `_finish` can fire twice for one entry (a restart replays `recover`, `ui/run_queue.py:104`); no criterion says delivery for one run id happens once. Proposed: a marker per (run id, channel, recipient) created with `O_CREAT|O_EXCL` via `team_store.create_marker`.
4. **Retry bound, backoff and driver.** HO29/TT9 say "bounded", "backoff", "attempts == the bound" but name no number, schedule or driver. TS7 says there is no in-app background loop. Proposed: three attempts, delays 1, 5 and 30 minutes, constants named in `delivery/email.py`, driven by an externally run command or the existing timer; tests use an injected clock and never sleep. Checker fixes the numbers and the driver before dispatch.
5. **Report label thresholds.** TT7 says `green` "only when verdict counts and coverage support it" and names `low coverage`, but gives no threshold and no coverage source. Master has `Result` = PASS/FAIL/BLOCKED/INCONCLUSIVE (`schema/enums.py:130`), per-run verdict counts (`ui/routes_report.py` `_run_counts`) and `Run.bounds` / `Run.catalog_runnable_counts` (`schema/run.py:59,78`); no "coverage line" function exists for a run. Checker defines the rule (suggest an ordered precedence table in the contract).
6. **TLS mode.** HO27 says "STARTTLS or SSL ... when `_TLS` is set"; `.env.example:87-88` documents only `AUTOTESTER_SMTP_TLS` "1 = STARTTLS". How implicit SSL (port 465) is chosen is not stated.
7. **Link base URL.** HO28 needs an absolute link; no key for the site's public URL exists in `.env.example` (HO9 lists none). A new key needs a `.env.example` line (HO9's drift test) and a contract line. What the mail carries when it is unset is not stated.
8. **Principal for a user id.** TT8 needs "holds `report.view` at send time" for a user who is not in a request. `wave/t204-team-login` builds a `Principal` only from a session row (`auth/sessions.py:77`); there is no public function from a user id, and `authorize(principal, key, resource)` (`auth/access.py:35`) needs one. T-204 or a G4 seam must supply it. Also unstated: a disabled or deleted recipient gets no mail.
9. **Outbox path.** TT8 says `<data>/.work/outbox/`; `store/team_store.py` roots team data at `<data>/.work/team/` (`core/paths.py` `team_path` on the t205 branch). Proposed: follow the contract literally (`core.paths.work_dir(root)/"outbox"` with `core.safe_names` on every part). Checker confirms.
10. **Declaration of the mail keys.** D-081 item 5 says "declared as SecretRef keys". `SecretRef` (`schema/project.py:24`) is a per-project model with browser `domains`; server mail credentials belong to no project. HO27 treats them as environment variables. Proposed: the declaration is the `AUTOTESTER_SMTP_*` lines in `.env.example:82-88` plus the Redactor masking every `.env` value (C5); no `SecretRef` instance is created. Checker rules.

## 4. What exists and what is missing

Measured against master `09828f2d`.

- **Exists and is reused (read, not changed):** `core/redact.py:87` `Redactor`, `:113` `scrub`, `:155` `_mask_emails`, `:173` `mask_pii`; `core/env.py:41` `TEST_MARKER`, `:46` `load_repo_env` (loads nothing under pytest, `:58`, and returns key names only); `browser/secrets.py:93` `SecretStore`; `stages/report_export.py:68` `_load_redactor`; `ui/routes_report.py:163` run page, `:212` project report page, `:277,:290` exports; `.env.example:82-88` `AUTOTESTER_SMTP_HOST/PORT/USER/PASSWORD/FROM/TLS` (placeholders, no values).
- **Queue (T-203, on master):** `schema/run_queue.py:17` `QueueStatus` (queued/running/done/failed/refused/interrupted), `:29` `QueueEntry` (`id` is the run id; `requested_by: str | None`; `trigger: Literal["button","schedule","api"]`; no `via`, no `requested_at`); `ui/run_queue.py` (229 lines): `_work` `:166` maps `RunRefused` to `refused`, other exceptions to `failed` (reason = exception class only), `BaseException` to `interrupted`; `_finish` `:181`; `recover` `:104`; `KEEP_FINISHED = 20` (`:34`) prunes old finished entries, **so the inbox cannot be derived from the queue and needs its own store**; `set_runner` `:55` is the injection pattern to copy for a finish hook.
- **Missing (all of it):** `schema/delivery.py`, `stages/report_delivery.py`, `delivery/` package, `ui/routes_inbox.py`, the profile page and route, the stored report label (nothing computes a label today), any mail transport, any outbox, any `NotificationPref`. No `/inbox` or `/profile` route exists on master or on `wave/t204-team-login` (`git grep` for both: none).
- **Not on master (dependencies):** `store/team_store.py`, `schema/team_enums.py`, `ui/routers.py` (the `inbox` and `profile` stubs), `auth/policy.py` merge (all T-205, `wave/t205-g10-headroom` `3ebd2fca`); `auth/*`, `Principal`, `authorize`, sessions (T-204, `wave/t204-team-login` `6ea9b688`, unmerged; the cycle-0 verdicts of its predecessor branch were FAIL, see `qa/briefs/t204-team-login.md`).
- **Consumers waiting on this unit:** `t200-schedule` phase B (failure and blocked notices, `qa/briefs/t200-scheduled-test.md` section 2) and `t201b-test-button` (`qa/briefs/t201-test-button.md` section 10, item 4). Publish two stable entry points for them: one to deliver a finished queue entry, one to deliver a notice with no run (item 1 above). The names are the builder's; record them in the manifest.
- Verdict: none. Issues filed: none.

## 5. Files the builder will touch

Line counts as of master `09828f2d`. A new module is a gate in this repo (C3: "a new module requires a stated reason in the manifest"). D-072 item 2 ("the Group 10 split modules") and the plan row G4 (`docs/plan.md:137`) pre-authorise the first five; the last three are NOT named in the plan and need a stated reason and the checker's acceptance.

| Path | New / existing | What | Why no existing file can hold it (300-line cap, C1/C3) |
|---|---|---|---|
| `src/autotester/schema/delivery.py` | new (plan-named) | `DeliveryRecord`, `NotificationPref`, the per-run entry model (item 2), `extra="forbid"` | C1: one model family per file; `schema/enums.py` is at its 300-line cap and `schema/run.py` is the Run family |
| `src/autotester/stages/report_delivery.py` | new (plan-named) | the one `report_label` definition, the fan-out (inbox entry, recipient decision, email attempt), the two entry points | contract TT7 names this file; `ui/routes_report.py` is a route file and stages hold no HTML |
| `src/autotester/delivery/__init__.py`, `delivery/inbox.py` | new (plan-named) | inbox store over `store/team_store.py`; read side used by the route | no `delivery` package exists |
| `src/autotester/delivery/email.py` | new (plan-named) | the outbox adapter, the SMTP adapter, retry/backoff; the only importer of `smtplib` (TT8 grep) | the grep rule needs one isolated module; `sources/email.py` is ingest |
| `src/autotester/ui/routes_inbox.py` | new (plan-named) | `GET /inbox`, `ROUTE_POLICY` | stub `inbox` in `ui/routers.py` is empty by design (TF3) |
| `src/autotester/ui/routes_profile.py` | new (**not plan-named**) | `GET/POST /profile` and the preference checkbox | TF3 registers a separate empty `profile` stub; one file for both routes is acceptable if the checker prefers and it stays under 300 lines |
| `src/autotester/delivery/message.py` | new (**not plan-named**, proposed) | pure composition of the HO28 body (the "message module" the TT7/TT8 mutations name) | `delivery/email.py` would pass 300 lines holding two adapters, retry and composition; a separate pure module also keeps "no product data" testable alone |
| `tests/delivery_fakes.py` | new | fake SMTP client class, in-process loopback fake server, raising transport, fake identity | shared by three test files, 300-line cap |

Existing files edited in place (name the function before editing):
- `src/autotester/ui/run_queue.py` (229): add a `set_finish_hook` beside `set_runner` (`:55`) and call it from `_finish` (`:181`) and `recover` (`:104`) after the lock is released, with every exception caught and logged by class only (HO29: delivery never fails or delays a run). At most about 15 lines.
- `src/autotester/schema/team_enums.py` (exists after T-205): append the delivery channel, delivery status and report label vocabularies. Do not add them to `schema/enums.py` (TF8).
- `src/autotester/ui/routers.py` (exists after T-205): replace the `inbox` and `profile` entries of `STUBS` with the real routers; do not touch `ui/app.py`.
- `src/autotester/ui/routes_report.py` (`:163` run page, `:212` project report page): show the stored label, and on the run page the delivery failure (TT9). Read the label, never compute it.
- `src/autotester/ui/theme.py` (152): one sidebar link each to My reports and Profile. T-204's branch also edits this file, so this edit goes in after T-204 lands.
- `.env.example`: only if item 7 or 4 adds a key (HO9 drift test). Never a value.
- Generated or process files: `docs/MAP.md` (`uv run autotester map`, last step, never hand-merged), manifest `qa/manifests/t201a-report-delivery.md`. `docs/ARCHITECTURE.md` rows come from the orchestrator under a DECISIONS entry that names the section, not from the builder.

Shared with in-flight units, merge order: `ui/routers.py`, `schema/team_enums.py`, `auth/policy.py`, `store/team_store.py`: T-205 owns, merges first. `ui/theme.py`, the route-policy shape, `tests/conftest.py`: T-204 (policy rows are `RouteRule` objects on its branch, `str | (key, resolver)` on T-205's; whichever lands second reconciles, G4 must not pick a shape). `ui/run_queue.py`: no in-flight unit edits it today; `t201b` and `t200` phase B only call the new hook. `docs/MAP.md`: regenerated at merge. Not touched: `stages/run_launcher.py`, `schema/run.py`, `ui/routes_runs.py`, `ui/project_view.py` (t201b), `stages/scheduler.py` and `schema/schedule.py` (t200), `auth/*`, `.goal/goal.json`, any `qa/contracts/` or `qa/gates/` file.

## 6. Test scope

```
uv run pytest tests/test_inbox_scope.py tests/test_report_email.py tests/test_delivery_failure.py tests/test_delivery_smtp.py
uv run pytest tests/test_run_queue.py tests/test_run_queue_resilience.py      # the hook edit must leave these green, assertions unedited
uv run ruff check src tests scripts
uv run autotester doctor
```

The first three files are the contract's evidence. `tests/test_delivery_smtp.py` (new, proposed) holds the SMTP adapter against the in-process fake so `test_report_email.py` stays under 300 lines. No full suite (the checker owes it); no CLI `-q` on pytest (AT-503). After T-205 lands, add `tests/test_team_store.py` and `tests/test_team_enums_home.py` to the run (the second must still pass with the new enum values).

**What is faked.** No real email is sent by a builder or a test.
- `smtplib.SMTP` and `smtplib.SMTP_SSL` are monkeypatched to raise in an autouse fixture of `tests/delivery_fakes.py`; the SMTP adapter takes a client factory argument, and tests pass a fake class that records `starttls`, `login`, `send_message` and can raise per attempt. One protocol-level test may talk to a `socketserver` fake bound to `127.0.0.1` on an ephemeral port, in the test process. Do not use `smtpd` (removed in Python 3.12, `pyproject.toml:9` allows 3.11 and later) and add no dependency (`aiosmtpd` is not installed and no dependency change is authorised).
- Selection of the adapter under pytest: with `AUTOTESTER_SMTP_HOST` monkeypatched to a dummy value and no factory injected, the default is still never a real connection (test asserts the patched `smtplib.SMTP` was not called). `load_repo_env` already loads nothing under pytest (`core/env.py:58`), so a developer's `.env` cannot leak into a test.
- Identity is a small injected fake (users, groups, scopes) until T-204 lands, then the real `authorize`. The clock is injected; nothing sleeps.
- **The one live check held for the owner:** one message from the real adapter to Umesh's inbox, run after T-204 and the key check below, by pressing Test with the box ticked (no new command is needed), or by whatever command the checker approves. The builder does not run it, does not read `.env`, and does not ask for the values. The result is one line in the manifest: sent / not sent, no address, no header.

## 7. Reachable test cases (happy path first)

| Criterion | Happy path | Then |
|---|---|---|
| TT7 | a `done` run for a project owned by Developer A appears in A's `/inbox` with project, run id, time, "started by A", label, link | Developer B (other project) absent and direct URL 404 identical to a missing run; Tester sees only `@shared`; Admin sees all; anonymous 302 to `/auth/login`; `refused` and `low coverage` runs appear with their labels; an all-BLOCKED run is never `green`; `report_label` defined once (grep) |
| TT8 | box ticked, run done -> exactly one outbox message to that user | box off (default) -> none; revoked `report.view` before send -> none; two sessions -> recipient follows the session; forged `to`/`email`/`recipient`/`cc` in Test POST and profile POST -> never in the outbox; canary secret and canary page string absent; `smtplib` imported only in `delivery/email.py`; unconfigured -> profile shows "email is not configured on this server" |
| TT9 | transport raises on every attempt -> run stays `done`, one `failed` `DeliveryRecord` with redacted error, attempts == bound, run page shows it, inbox entry present | secret planted in the error is scrubbed; link GET without session is 302; the next queue entry starts on time; a hook that raises does not change the entry status |
| hook | `_finish` and `recover` each call the hook once | the hook raising leaves `QueueEntry.status` unchanged; replay delivers once (item 3) |

Mutations the checker will try in a throwaway copy (per contract): list all runs without `authorize`; recompute the label in the message module; read the recipient from the form; default the box to on; let a transport exception propagate into the run; put the secret in the error text.

## 8. Gate answers

- `qa/gates/email-sender-credentials.md:10` verbatim: "Answered: 2026-10-10 - A (credentials from d:/erp, AutoTester-prefixed keys) - D-081". Body (line 8): "take the credentials from d:/erp. The AWS SES SMTP values and sender identity used by d:/erp are copied into the gitignored repo-root `.env` under AutoTester-prefixed keys, never printed, never committed, and declared as SecretRef keys. This file holds key names only, never values." It gates only `delivery/email.py`, and it is answered, so the adapter is no longer held on a gate. Whether the keys have actually been written to `.env` is `unknown` and is not the builder's to check (never read `.env`).
- D-081 item 5, verbatim: "**Email sender: take the credentials from d:/erp.** The AWS SES SMTP values and sender identity used by d:/erp are copied into the repo-root .env under AutoTester-prefixed keys, never printed, never committed, and declared as SecretRef keys." `Approved-by: Umesh (chat, 2026-10-10)`.
- D-072 item 8, verbatim: "**Reports:** shown on the website, plus email **by user preference** (a per-user checkbox)." D-072 item 2: "**New modules: yes to all.** ... the Group 10 split modules."
- D-078 (UTC or IST only) does not apply: no schedule logic here. D-080 item 1 (single trunk) governs section 2.
- `qa/gates/plan-approved-g10.md` (verbatim): "Approved -- Umesh, 2026-10-07 (chat), recorded as D-074." and "Reports appear on the website and are emailed only to people who ticked the box." Assumption: "Email checkbox defaults off."
- `qa/gates/write-policy-tier.md`, `d063-cn5-vs-cn11.md`: not applicable (no run, no approval path is touched).
- Still open and NOT answered: `qa/gates/t203-host-and-dns.md` has "STILL OPEN: the real server host and the DNS name", which bears on the link in the message (item 7, owner question 3). No gate file is open for the build itself.

## 9. UI surface and persona walk

UI surface: yes (My reports page, profile page with the checkbox, label and failure on the report pages, two sidebar links).
Persona walk: required (dev), judged in the checker's own browser once the pages exist, from the contract: `dev`: from the project page press **Test**, watch the status page, open the report, in <= 3 steps; then open **My reports** and find it. Open the profile page, tick "Email me run reports", press Test again, and confirm the outbox (or, once credentials exist, the inbox of a test account) holds exactly one message. Negative walks: no credentials (the message names the Credentials page); press while the project is already queued (the existing request and its position are shown); a `tester` opens **My reports** and sees only shared ones. Note: the walk needs `t201b-test-button`; until it lands the checker presses the existing Run button, which on master already goes through the queue (`ui/routes_runs.py:202`).

## 10. Dependencies and conflicts

| Part | Needs | On master today? | Status |
|---|---|---|---|
| Queue finish hook, `recover` coverage, queue tests | T-203 queue | yes (`82bc4954`) | buildable now, but part of one branch cut after T-205 |
| `schema/delivery.py` models, report label, `stages/report_delivery.py`, `delivery/inbox.py`, `delivery/message.py`, outbox adapter, SMTP adapter against fakes, retry, the finish hook, TT9 and the pure parts of TT7/TT8 with a fake identity | `store/team_store.py`, `schema/team_enums.py` (T-205) | no | **HELD on T-205 merging** (phase A). Nothing in phase A needs T-204 |
| `GET /inbox`, `GET/POST /profile`, route-policy rows, `report.view` scope table (4 users x 2 projects), recipient-follows-session, send-time `report.view`, Origin guard on POST, sidebar links, persona walk | `ui/routers.py` stubs (T-205); `authorize`, sessions, groups, a principal-by-user-id function (T-204) | no | **HELD on T-204 merging** (phase B). Until then only a loopback single-user stub exists; `unknown` what it looks like |
| Notice with no run (item 1) | checker ruling; T-200 phase B and T-201b are the callers | n/a | **HELD on the checker** |
| Retry numbers and driver, label thresholds, TLS mode, base URL key (items 4-7) | checker ruling | n/a | **HELD on the checker**; the builder may stub with the proposed values only if the contract is amended first |
| One live message to Umesh | real keys in `.env`, owner action | unknown | **HELD for the owner** |

Order: `t205-g10-headroom` -> this unit phase A -> (`t204-team-login` -> this unit phase B). `t201b-test-button` and `t200-schedule` phase B follow this unit (QUEUE `after:` lines `qa/QUEUE.md:145,156`). `land-t203-hosting` is satisfied. Ship phase A and phase B as one unit with one verdict if T-204 has landed by dispatch; otherwise phase A first with `Status: ready-for-check` scoped to TT9 and the non-route parts of TT7/TT8, and the manifest says which rows are `BLOCKED-CAPABILITY`.

## 11. Credential and personal-data rules

- The mail credentials are `AUTOTESTER_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `_FROM`, `_TLS` (HO9; `.env.example:82-88`). Values live only in the gitignored repo-root `.env` (CLAUDE.md "Credentials"); the builder never reads `.env`, never prints a value, and never puts one in a test, fixture, log, screenshot, manifest, outbox sample or commit. Print key names only. `core/env.py::load_repo_env` returns key names, never values.
- The SMTP password is read at send time from the environment, held in no model field (C5: no schema model has a field holding a secret value), never in a `DeliveryRecord`, never in an exception text. Every logged line, every stored error and every message body passes `Redactor.scrub` (`core/redact.py:113`) built over the `.env` values, which `core-invariants.md` C5 says are all masked "declared or not".
- Recipient addresses are personal data. A `DeliveryRecord` stores the recipient **user id**, not the address; the address is resolved from the account store at send time and appears only in the outbox file (gitignored `.work/`, confirmed by `git check-ignore`) and the `To:` header of a sent message. Logs and error strings carry no address (use `core/redact.py` `mask_pii` / `_mask_emails` if one must be mentioned). Outbox sample files are never committed or pasted into a manifest.
- The recipient comes from the authenticated identity on the queue entry only; any `to`, `email`, `recipient`, `cc`, `requested_by`, `user`, `owner` in a body or query is ignored.
- The message carries project name, run id and time, counts, the coverage line, the label and a sign-in link. No attachment, screenshot, video, credential, token, cookie or page content (HO28).

## 12. Open questions only the owner can answer

1. **Mail keys and SES state.** Were the AWS SES SMTP values from `d:/erp` copied into the repo-root `.env`, under which exact key names (the contract and `.env.example` say `AUTOTESTER_SMTP_*`; D-081 says "AutoTester-prefixed")? Is the SES account out of the sandbox, or must each recipient address be verified first? Which port and TLS mode does the relay need (STARTTLS 587 or SSL 465)?
2. **Sender identity.** The `From:` is the `d:/erp` sender identity (D-081 item 5). Confirm recipients of AutoTester mail may see that sender.
3. **Link host.** The host and DNS are still open (`qa/gates/t203-host-and-dns.md`; D-081 item 4 hosts locally for now). Should the live message link to `http://localhost:<port>` (works only on this machine) or is the live send held until a real host exists?
4. **Live check recipient.** Which address receives the one live test message to you.
5. **Subscribers.** R58 says "the schedule owner and subscribers"; `hosting.md` HO26 and `team-schedule.md` say owner only. Confirm owner only stays, so no subscriber list is built.

## 13. Budget and process rules

- Check budget: Tier L = 45 min per checker. The builder runs NO full suite; only the commands in section 6 (no CLI `-q` on pytest, AT-503).
- Falsification (mutation) only in a throwaway copy outside the bound tree (`git archive` into the scratchpad, a unique directory per unit); never perturb the worktree. Kill only PIDs the builder itself started; no kill by image name or port.
- Edit in place; name the exact file and function before changing existing code. No `*_v2.py` / `*_new.py`. Files <= 300 lines, functions <= 50, one-job module docstring, `extra="forbid"` models, prompts as files, model calls only through `providers.base.Provider` (none needed here). A regression is reverted to the last good git state, not stacked.
- No `cd X && cmd`: use `git -C <dir>`, absolute paths or the tool's working directory.
- The builder never edits `qa/contracts/`, `docs/DECISIONS.md`, `qa/gates/`, `.goal/goal.json`, `.claude/hooks/*`, `qa/hooks/*`. Contract wording problems and the ten items in section 3 go verbatim into `qa/feedback-inbox.md`. Only `/checker` can PASS; the maker ends at `Status: ready-for-check` with `Fix cycle: N` in `qa/manifests/t201a-report-delivery.md`, with the Policy-Version line, the verbatim criteria and a stated reason for each new module.
- Commit before the verdict is requested (`qa/gates/commit-before-verdict.md`, C10); the manifest names the exact commit sha; the checker answers in `qa/verdicts/t201a-report-delivery.md` (and `.a` / `.b` for the dual check) with `Cycle checked: N`.
- Issue ids: renumber any issue row to start after the max AT id on the branch you land on; re-read `qa/issues.jsonl` immediately before the commit (`merge=union`, a duplicate id is not caught by git). The checker owns issue status.
- `docs/MAP.md` is generated: after the final rebase run `uv run autotester map`, then `uv run autotester doctor`.
- Push: none by the builder; the checker pushes `origin master` after its PASS (D-007).
- Ledger on PASS: T-201 is split across G4 and G7; the maker appends the `docs/FEATURES.jsonl` row (`autotester ledger add ... --unit T-201`) only when the checker has PASSed the unit that closes the task, with a prefilled reason shown to Umesh. Gap noted by `qa/briefs/t201-test-button.md` section 4: the done-check `qa/verdicts/t-201-team-loop.md` is produced by neither unit; the builder does not touch `.goal/goal.json`.
- The builder reports with: files changed, the exact commands run with their output lines, and any criterion it could not evidence and why. A claim without a re-run is not done.
