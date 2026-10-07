# Contract — team-test-button: the Test button (G7) and report delivery (G4)

**Covers:** unit G7 `t201b-test-button` (TT1-TT6; R56, R57, R60, R64) and unit G4 `t201a-report-delivery` (TT7-TT9; R58, R59); goal task T-201.
**Owner:** /checker. **Status:** ACTIVE (2026-10-07); build starts only after `qa/gates/plan-approved-g10.md` is answered.
**Criticality:** CRITICAL for TT1, TT5, TT6 and TT8; HIGH elsewhere. Tier L (auth, outward-facing run, outward-facing email), so a **dual
check** applies to TT1, TT5, TT6 and TT8.
**Serves:** `docs/intent.md` O13 (a teammate presses Test and gets a report), O7 (credential and data boundary), O4 (report states what it
did not cover), O15 (permissions); D-072 items 4 and 8 (groups with checkbox permissions; reports on the website plus email by a per-user
checkbox); D-066 (Origin guard); D-068 (credential-derived approval).
**Depends on:** `auth.md` (identity, `authorize`, keys `project.run`, `report.view`; **no new key**), `hosting.md` (queue HO16-HO19, report
rows HO25-HO29), `consent.md`, `ui-run.md` (RU1 is amended by T-203, RU2-RU4 stay true), `team-schedule.md` TS5/TS6 (same gate, same
launcher), and unit **G1** (`team-foundation.md`).
**Source:** the maker's proposal `.work/plan-g10/contract-proposal-T-201.md`, reconciled with `docs/spec.md` R56-R60, R64 and `hosting.md`.

## Boundary with `hosting.md` (those rows govern; this file adds only what they lack)

| `hosting.md` row | what it already states | what this contract does with it |
|---|---|---|
| **HO16, HO17** | `POST /projects/{slug}/run` queues and returns at once; one run per project; server cap | **Referenced.** TT2 and TT5 assert only that the button goes **through** the queue and the unit never bypasses it |
| **HO19** | `project.run` checked at enqueue and again at start; queue is no way around approval or consent | **Referenced.** TT1 covers the route's own gate (anonymous, permission, Origin); TT6 covers the approval refusal and its no-trace guarantees |
| **HO21** | `requested_by` and `trigger` recorded on every queue entry | **Referenced.** TT3 adds the persisted attribution on `Run` and the report header |
| **HO25** | the report route is auth-scoped (`report.view`), exports included | **Referenced.** TT7 adds the **inbox** ("My reports") listing and the shared label; it does not re-test the route |
| **HO26** | per-user checkbox "Email me run reports", default off; recipient = requester or schedule owner, only if ticked **and** still holding `report.view` | **Referenced.** TT8 adds the profile page, the forged-recipient proof, the outbox adapter and the one-label rule |
| **HO27, HO28, HO29** | SMTP from the environment and graceful absence; body = link and counts, no product data; mail failure never fails a run | **Referenced.** TT8 and TT9 use them and add the delivery record and the page-level visibility of a failure |

## Vocabulary

- **RunRequest** = the persisted queue entry (`hosting.md` HO16), with `requested_by` = the signed-in user's id and email, `requested_at`,
  `trigger` (`manual` for this button; `schedule` for the tick), `via` (`team_button`).
- **Status** (HO16's closed vocabulary): `queued`, `running`, `done`, `failed`, `refused`, `interrupted`. `docs/spec.md` R56 says "finished"
  and "blocked": **`done` is "finished", and `refused` is "blocked"** (an approval or permission refusal). The page may display friendlier words;
  the stored values are HO16's.
- **Report label** = one value computed **once** per run (`green` only when verdict counts and coverage support it; otherwise
  `failed`, `blocked`, `inconclusive` or `low coverage`, R22 carried). The page, the inbox and the message all read this stored value;
  none re-derives it.
- **Outbox adapter** = the dry-run delivery adapter that appends the would-be message to `<data>/.work/outbox/` and sends nothing. It is the
  default until the SMTP credentials exist (a HUMAN_GATE, `plan-approved-g10.md` open item 1).

## Criteria — G7, the Test button

- **TT1 — Authenticated, authorised, Origin-checked, and no trace on refusal (R56, R64, CRITICAL).**
  `POST /projects/{slug}/test` (the route name is the maker's; the **behaviour** is the contract) is refused, **with no `RunRequest`, no run
  directory, no queue entry, no browser and no model call**, in each of: an anonymous request (302 to `/auth/login`, `auth.md` AU16); a
  signed-in user without **`project.run` on that project** (403 whose body names `project.run`); a signed-in user whose project is not
  visible to them (the same 404 as a project that does not exist, AU13); a cross-origin POST carrying a valid session cookie (403 from the
  D-066 guard, which runs **before** authentication, AU18); an unknown slug (404). The route is declared in this unit's route-policy dict as
  `project.run` with the project resource (`team-foundation.md` TF4); the AU14 enumeration test passes with it present. A GET to the route
  changes nothing. `serves:` intent#O13, O15, spec R56, R64, `auth.md` AU12-AU16, AU18, `hosting.md` HO19.
  *Evidence (LOCAL):* `tests/test_team_run_gate.py` — the five cases above, each asserting the data-root file listing is byte-identical
  before and after, the queue is empty, and the recording browser factory and recording provider were never called; plus the four default
  groups x `{own, assigned, other}` projects table for 200/303 vs 403/404. *Mutation:* check permission after enqueue -> the empty-queue
  assertion fails; drop the Origin guard from the route -> the cross-origin case fails.

- **TT2 — The button is a request, not a run (R56).**
  A permitted press returns `303` to the run status page **within 2 s** with the browser factory untouched on that request; the work is
  done by the queue worker. The status page shows the status and, while `queued`, the **position**; it moves
  `queued -> running -> done | failed | refused | interrupted`, and is **readable without the worker** (it reads the persisted entry, not a
  worker handle). The project page shows the button only to a viewer who may use it, and the route enforces the permission regardless of
  what the page shows (the page hiding a button is not enforcement). `serves:` intent#O13, spec R56, `hosting.md` HO16.
  *Evidence (LOCAL):* `tests/test_team_run_status.py` — a fake runner that blocks on an event; assert response time < 2 s, the status
  sequence, the position while queued, and that the status page renders after the app object is re-created (persistence). *Mutation:* run the
  case inline in the request -> the < 2 s assertion fails.

- **TT3 — The run is attributable to the person who pressed it (R56).**
  The `RunRequest` **and the resulting `Run`** record `requested_by` (user id and email taken from the **session**, never from the request),
  `requested_at`, `trigger=manual`, `via=team_button`; the run's report header names who started it. A request carrying `requested_by`,
  `user`, `email` or `owner` in its body or query ignores them (TT8 asserts the same for the recipient). The fields are optional on `Run`
  (a `run.json` written before this unit still loads, `team-foundation.md` TF2). `serves:` intent#O13, O15, spec R56, `hosting.md` HO21.
  *Evidence (LOCAL):* `tests/test_team_run_attribution.py` — two sessions press, assert two different `requested_by` values on queue entry,
  `Run` and report header; a forged `requested_by=other@x` is ignored; load a golden pre-change `run.json`. *Mutation:* read
  `requested_by` from the form -> the forged-value test fails.

- **TT4 — It reuses the one G1 launcher, and the existing run behaviour is unchanged (R56, R57).**
  The queue worker started by the button calls **the single function in `stages/run_launcher.py`** (`team-foundation.md` TF1) — the same one
  `trigger_run` and the scheduler's runs use. This unit adds **no** function that builds a `Run`, starts a `BrowserSession`, or calls the
  pipeline (`stages/run_case_pipeline.py` / `_execute_with_trace`); the AST import test over `ui/routes_team_run.py` finds none of them;
  `doctor` finds no duplicate concept. `ui-run.md` **RU2** (no cases or no provider -> 400 before any browser), **RU3** (every case result
  and verdict persisted, a `Run` saved) and **RU4** (`.env` visible to the process) hold on the button path exactly as on the old path; the
  existing RU tests pass **with their assertions unedited**. *(RU1's "synchronous" wording is T-203's amendment, not this unit's.)*
  `serves:` intent#O13, spec R54, R56, `ui-run.md` RU2-RU4, `team-foundation.md` TF1.
  *Evidence (LOCAL):* `tests/test_team_run_launcher.py` (patch the launcher; press the button; assert it is called once with
  `trigger=manual` and the user); the AST import test; the existing `tests/test_ui_run*.py` unchanged; `uv run autotester doctor`.
  *Mutation:* add a second `Run(` construction site in the button route -> doctor or the grep test fails.

- **TT5 — The queue seam: the button enqueues and never bypasses T-203's rules (R57, CRITICAL).**
  Group 10 does not own the queue. A second press while the project already has an entry `queued` or `running` returns **the existing
  request and its position** (303 to its page; no second entry), and the per-project single flight and server-wide cap stay `hosting.md`
  HO17's. This unit asserts only that it **never** starts a run except through the queue, and **never** calls the worker, the launcher or
  `BrowserSession` from the request thread. Until T-203's queue lands, the unit is built and tested against **a fake queue that
  implements HO16's interface** (enqueue, get by id, list by project, status values); the real-queue integration is judged when T-203
  PASSes and is `BLOCKED-CAPABILITY`, never PASS, before then. `serves:` intent#O13, spec R57, `hosting.md` HO16, HO17.
  *Evidence (LOCAL):* `tests/test_team_run_queue_seam.py` — two presses of one project -> one entry and the same id returned; three
  projects against a fake cap of 2 -> the fake runner's observed concurrency <= 2 and the button unit contains no cap logic (grep for
  `max_concurrent_runs` in this unit's files finds none). *Mutation:* create a second entry on the second press -> the one-entry
  assertion fails.

- **TT6 — The same gate as a schedule: a credential-derived approval, or a refusal that names the state and leaves no trace (R60, CRITICAL).**
  The run proceeds only on an approval that covers (project, run_kind, target) under D-068's credential-derived rule (`team-schedule.md` TS5
  is the same check; one implementation, `team-foundation.md` TF2). Otherwise the request ends `refused` with the reason shown to the person
  who pressed it, naming the state (e.g. "`PATHLYNKS_USER_EMAIL` has no value; enter it on the Credentials page"; "no credential pair is
  declared for this project"), and: **zero requests reach the network (asserted at the transport, `consent.md` CN1), no run directory exists,
  no browser factory is called.** The refusal text contains **no credential value** and passes `Redactor.scrub`. A role never skips it: an admin
  pressing Test on an uncredentialed project is refused the same way (`auth.md` AU15). The approval's own bounds (`max_actions`,
  `wall_clock_s`) cap the run and name what it left unreached; **no extra cooldown** is built (gate `plan-approved-g10.md`). AT-570 (a
  live case needs a covering approval) is re-verified through the launcher (`team-foundation.md` TF2). **Dependency:** the credential-derived
  `covering_approval` is the D-068 implementation; until it lands this row is `BLOCKED-CAPABILITY`, not PASS. `serves:` intent#O13, O7,
  spec R60, D-068, `consent.md` CN1, `auth.md` AU15, `hosting.md` HO19.
  *Evidence (LOCAL):* `tests/test_team_run_approval.py` — three fixtures (no `SecretRef`; `SecretRef` with no value; provisioned) pressed by a
  Developer and by an Admin; assert the transport and browser counters are 0 in the first two, the `runs/` listing is unchanged, and the
  message names the state. *Mutation:* skip the approval check on the admin path -> the admin case fails.

## Criteria — G4, report delivery (website inbox, then email by preference)

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

## Persona walk (Mode D, the checker's own browser; judged once the pages exist)

`dev`: from the project page press **Test**, watch the status page, open the report, in <= 3 steps; then open **My reports** and find it.
Open the profile page, tick "Email me run reports", press Test again, and confirm the outbox (or, once credentials exist, the inbox of a
test account) holds exactly one message. Negative walks: no credentials (the message names the Credentials page); press while the project
is already queued (the existing request and its position are shown); a `tester` opens **My reports** and sees only shared ones.

## Out of scope / ignore

- The queue, concurrency cap, settings page, tick timer and the Ubuntu deploy (T-203); sign-up, sessions, groups (T-204).
- The live virtual-display (noVNC) view: T-203 owns exposing it behind the login (`hosting.md`); not re-tested here.
- Slack or any channel other than the inbox and email; per-user quotas or a cooldown between presses.
- The SMTP sender address and credentials (HUMAN_GATE); the real relay is judged at the go-live rehearsal (`hosting.md` HO27, SERVER-GATED).
- Comment, share and access-request objects (G9); the tracker (G6, G8).

## No-fire list (must NOT happen)

- No run, run directory, queue entry, browser or model call from a refused press; no run started outside the queue.
- No recipient read from a request; no email to a user who has not ticked the box or who cannot view that report.
- No new permission key; no route without a declared permission (AU14).
- No real SMTP connection in the default test suite or the default adapter; no attachment, screenshot, video, credential or page content in a message.
- No second function that builds a `Run` or starts a browser (one launcher).

## Amendment log (append-only; git history is the version)

- 2026-10-07 · init · contract created for units G7 (TT1-TT6) and G4 (TT7-TT9) from the maker's proposal T-201 (TT1-TT12), `docs/spec.md` R56-R60,
  R64 and `hosting.md` HO25-HO29. Folded: proposal TT1 -> TT1; TT2 -> TT2 (status words aligned to HO16); TT3 -> TT3; TT4 -> TT4, restated
  as "reuses the G1 launcher"; TT5 -> TT5; TT6 -> TT6; TT7 (recipient) -> TT8, split from the new inbox row TT7; TT8 (message label) -> TT7 and
  TT8; TT9 -> TT9. Dropped: TT10 live watch (T-203's), TT11 persona walk (kept unnumbered), TT12 portability (cross-platform asserted per
  row; the delivery store uses `team-foundation.md` TF7's portable writes). Added: the outbox adapter and the "no live send until credentials
  exist" rule (open gate item 1), the profile page, and the no-new-key rule for the inbox.
