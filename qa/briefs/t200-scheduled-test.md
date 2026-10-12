# Brief - t200-scheduled-test (scheduled auto-test, G5, two phases)

Readiness pass written 2026-10-11 against master `3a16616c`. Self-contained: the builder needs nothing from the dispatching session. Items marked `unknown` are not stated anywhere in the repo.

## 1. Policy and tier

Policy-Version: proportional-verification/2026-10-10.9
Tier: L
Dual check: no
Trigger for L: timing/concurrency (one claim per slot across two OS processes with `O_EXCL` markers, the 60-minute catch-up window, `stages/scheduler.py`) and, in phase B, the credential-derived run approval (TS5) and a live-run launcher. Dual check is `no`: the schedule has no more rights than its owner (HO24), adds no auth or tenancy code of its own (T-204 owns `schedule.manage`), and writes nothing to production by itself; there is no `security|auth|tenancy|prod-write <path:line>` trigger. The manifest of the slice also records `Dual check: no` (`wave/g5-schedule-core:qa/manifests/g5-schedule-core.md:7`).


## 2. Root and base

- Root: `D:/autoTesting`. Base: master `3a16616c`.
- **This brief covers phase A only as dispatchable now** (TS1-TS4 and the pure part of TS7: model, `due()`, claim marker, catch-up, overlap). **Phase B** (TS5 credential gate, TS6 launcher and queue wiring, the TS1 routes with `schedule.manage`, the TS7 CLI/heartbeat/card, and the schedule screen) is NOT dispatchable yet: it needs `land-t203-hosting` (the queue), `t205-g10-headroom` (`stages/run_launcher.py`, `Project.schedule`), `t201a-report-delivery` (inbox/delivery for TS7 failures) and `t204-team-login` (`schedule.manage`), and the D-068 `covering_approval` (present on master at `src/autotester/stages/explore_consent.py:35`; the manifest claims it lives on `d063-grant-budget`, which is stale). Phase B gets its own brief after those land.
- Branch for phase A: **re-land `wave/g5-schedule-core`** (tip `29ce74e8`, merge-base `84e0b4b5`, 17 files, `Status: ready-for-check`, Fix cycle 0, no checker has seen it). New branch `wave/t200-schedule-core` from master, merge that branch (it already contains a merge of origin/master, `e4d8d469`, and the D-078 rework `b4719ad0`). Reason: 112 tests, zero existing modules edited, one conflict only. The checker's contract amendment `29ce74e8` ("schedule zones are UTC or IST only, no DST (D-078)") is a checker commit: the checker brings `qa/contracts/team-schedule.md`, `qa/contracts/hosting.md` and `docs/spec.md` R51 from it onto master; the builder never edits those three files.
- Conflict with master: `docs/MAP.md` only (regenerate with `uv run autotester map`). The manifest path `qa/manifests/g5-schedule-core.md` must be renamed to `qa/manifests/t200-schedule-core.md` with its `Status`, source sha and `Fix cycle: 0` updated for the new branch.

## 3. Acceptance criteria (verbatim from the AMENDED `qa/contracts/team-schedule.md` at `wave/g5-schedule-core` `29ce74e8`; master's copy is stale: it still says IANA zones and DST)

## Boundary with `hosting.md` (read first — those rows govern, this file adds only what they lack)

| `hosting.md` row | what it already states | what this contract does with it |
|---|---|---|
| **HO22** | three modes, UTC or IST only (D-078), no DST, invalid values refused and store nothing, `schedule.manage` to set | **Referenced, not repeated.** TS1 adds the model shape, persistence and the `schedule.manage` route policy; TS2 adds the pure `due()` function that makes HO22's zone claim (UTC or IST, no DST) checkable |
| **HO23** | enqueue through the queue, `trigger=schedule`, one entry per (project, slot) across two schedulers and a restart, one catch-up inside a 60 min grace window, else `missed` | **Referenced.** TS2 adds the marker mechanism, TS3 the catch-up arithmetic and its per-slot record, TS6 the "one launcher" proof |
| **HO24** | the schedule has no more rights than its owner; owner disabled, deleted or without `project.run` pauses the schedule and records `refused`; deleting the project removes the schedule | **Referenced.** TS5 adds the approval gate (a different check from owner rights); TS1 carries only the delete-removes-markers clause that HO24 leaves open |

The queue itself (FIFO, one run per project, server cap, slot release) is **T-203's**. No row here re-tests it; every row here asserts only
that the scheduler goes **through** it and never around it (TS6).

## Vocabulary (fixed so criteria are falsifiable)

- **Slot** = one concrete instant a schedule means to fire, in UTC, derived from the schedule and its timezone. `slot_key` =
  `<project>:<mode>:<slot instant, UTC, ISO-8601 to the minute>`; deterministic, never random, never wall-clock-at-tick.
- **Slot record** = one append-only line per slot decision, with `outcome` from the **closed** set `enqueued`, `catch_up`, `missed`,
  `skipped_overlap`, `blocked_no_credentials`, `refused`, `failed`. Nothing else may be written; an outcome outside the set fails the model.
- **Tick** = one stateless invocation of the scheduler (`autotester schedule tick`). It reads schedules and markers, writes markers and
  records, and enqueues; it never starts a browser.
- **Owner** = the user who last saved the schedule (`requested_by` of every run it enqueues). **Subscribers**: not built here. `docs/spec.md`
  R58 mentions "schedule owner and subscribers" and `hosting.md` HO26 says owner only; this contract follows HO26 (owner only) and treats a
  subscriber list as out of scope until Umesh asks for it.

### Phase A rows (this brief)

- **TS1 — A schedule is a typed, bounded, persisted setting, and only `schedule.manage` changes it (R51).**
  `schema/schedule.py` defines `ScheduleConfig` (`extra="forbid"`): `mode` in `manual | fixed | custom`; `fixed` = one daily `HH:MM`;
  `custom` = one or more **one-off date-times** (each fires once, then is marked consumed) **and/or** one weekly rule (a non-empty weekday
  set plus `HH:MM`), at least one of the two; `timezone` (closed set `UTC` | `IST`, D-078; IST is the fixed +05:30 offset with no DST; default `AUTOTESTER_TIMEZONE` when it is `UTC` or `IST`, else `UTC`; any other value, an IANA city name included, is refused); `owner`; `paused`.
  `manual` is the default and **produces no slot**: a `manual` project is never enqueued by a tick, however many ticks run. No mode can
  yield more than one slot per local calendar day for one rule (so the "interval floor" of the proposal is structural, not a setting).
  Invalid values are refused at save with a reason naming the field, and **nothing is stored** (HO22 states the list: `25:00`, a zone
  other than UTC or IST (D-078: `America/New_York`, `Asia/Kolkata`, `ist`, a list), past one-off, empty weekday set; add `24:00`, `9:5`, a weekday outside 0-6, a
  duplicate one-off). There is no DST in the supported zones, so there is no gap or fold to resolve (D-078). The value lives in `Project.schedule` (G1's field, `team-foundation.md` TF6); a `project.json` without it loads as
  `manual`. **The key:** `GET` of the schedule card needs `project.view`; every `POST` that creates, edits, pauses, resumes or deletes a
  schedule needs **`schedule.manage` on that project** (`auth.md` catalogue, scopes `all | assigned | own`), declared in this unit's
  route-policy dict (`team-foundation.md` TF4). No new permission key exists. A user without it gets 403 naming `schedule.manage`;
  a legacy project with no recorded owner matches only `@all` (fails closed, `auth.md` AU12); the Origin guard runs first (AU18).
  Deleting the project removes its schedule **and its slot markers and records** (HO24 leaves the markers open).
  `serves:` intent#O12, spec R51, R63, D-072#9, `hosting.md` HO22, `auth.md` AU12, AU14.
  *Evidence (LOCAL):* `tests/test_schedule_model.py` — a table of >= 20 valid and invalid configs (assert refused ones leave the stored
  `project.json` byte-identical); `tests/test_schedule_routes.py` — four default groups x `{own, assigned, other}` projects x
  `{GET, POST save, POST pause, DELETE}`, asserting status and that a refused POST changes nothing on disk; round-trip of a golden
  pre-change `project.json`. *Mutation:* drop the `schedule.manage` check from the save route -> the 403 case fails; let `manual` produce a
  slot -> the "manual fires nothing" count fails.

- **TS2 — `due()` is pure, timezone-correct on both OSes, and a slot fires exactly once (R51, R52, R65).**
  `due(schedule, now, markers)` (in `stages/scheduler.py`) is a **pure function**: the clock and the marker view are arguments, it opens no
  file and reads no environment. A table of cases returns the exact slot instants for: `UTC`; `IST` (+05:30 fixed, no DST: a `09:00` rule is `03:30` UTC on every day of the year, D-078); a weekly rule across midnight, including the local-day versus UTC-day boundary for IST; a one-off exactly at, one second before, and one second after
  `now`. An unsupported zone cannot reach `due()` (TS1 refused it). The two zones are fixed `datetime.timezone` offsets (D-078): no `zoneinfo`, no
  zone database and no `tzdata` dependency, so the same table runs green on Windows and Ubuntu with nothing installed. The **claim marker**
  for a slot is created atomically with `os.open(path, O_CREAT | O_EXCL | O_WRONLY)` under the data root (R65: no `fcntl`, no `flock`,
  no `pwd`); the file name is `slot_key` made path-safe, and it is written **before** the enqueue. Two concurrent ticks for one slot
  produce **exactly one** claim, hence one queue entry; the loser records nothing and exits 0. Crash safety: a marker whose
  queue entry does not exist (process died between claim and enqueue) is re-driven by the next tick, and the queue's idempotency key
  (`HO23`: project + slot) makes the re-drive create at most one entry. *Evidence (LOCAL):* `tests/test_schedule_due.py` (table, injected
  clock, no sleeping); `tests/test_schedule_marker.py` spawns **two OS processes** (`multiprocessing`, `spawn` context so it runs the same
  on Windows) against one project and counts queue entries == 1, then kills a tick between claim and enqueue (monkeypatched hook raising
  `SystemExit`) and re-ticks, counting still == 1. `serves:` intent#O12, spec R52, R65, `hosting.md` HO22, HO23.
  *Mutation:* create the marker with `exists()` then `write` (check-then-act) -> the two-process test fails; compute `now` inside `due()`
  -> the injected-clock table fails; change the IST offset from +05:30 to +05:00 -> the IST table fails; let a third zone into `ScheduleZone` -> the TS1 refusal table fails.

- **TS3 — A slot missed during downtime fires at most one catch-up, inside the grace window; the rest are recorded `missed`, never
  backfilled (R52).**
  Grace window = `AUTOTESTER_SCHEDULE_GRACE_MINUTES`, default **60**, an integer 1..1440 (anything else falls back to 60 and says so).
  On a tick after downtime, the slots found due and unclaimed are split: slots whose instant is within the grace window of `now` fire
  — **at most one run per project per tick** (when several fall inside the window, only the **latest** fires, labelled
  `catch_up`; the earlier ones are recorded `missed` with `superseded_by=<slot_key>`); every slot older than the window is recorded
  `missed` and **starts no run**. Three missed daily slots after a 3-day outage therefore produce **zero or one** run, never three.
  A missed slot is never re-examined by a later tick (its record is the marker). A one-off whose instant has passed outside the window is
  recorded `missed`, is shown as such on the project page, and is not silently deleted. *Evidence (LOCAL):* `tests/test_schedule_catchup.py`
  with an injected clock — outage of 30 min (one `catch_up`), 61 min (one `missed`, zero runs), 3 days on a daily rule (<= 1 run, 2 or 3
  `missed`), a restart mid-tick (kill and resume yields the same records, no duplicates). `serves:` intent#O12, O4, spec R52,
  `hosting.md` HO23. *Mutation:* backfill every missed slot -> the "<= 1 run" assertion fails; use `<` instead of `<=` at the window edge
  -> the 60-minute boundary case fails.

- **TS4 — A slot that finds its project still busy is skipped and says so (R52).**
  If the project already has a queue entry `queued` or `running` when its slot is claimed, the tick records `skipped_overlap` with the
  blocking entry's id, **enqueues nothing** (no second entry, no second browser; the queue's single flight HO17 stays untouched), and the
  record is visible on the project's schedule history. A skipped slot is **not** retried as a catch-up later. The next slot is judged
  fresh. `off`/paused schedules and a project in the middle of being deleted fire nothing and write no `skipped_overlap` line (a paused
  schedule records nothing; it is not a skipped slot). *Evidence (LOCAL):* `tests/test_schedule_overlap.py` with the fake queue
  (`team-foundation.md` TF1's launcher seam): a running entry at the slot -> `skipped_overlap` and `len(queue) == 1`; a finished entry ->
  `enqueued`; paused -> no record. `serves:` intent#O12, spec R52, `hosting.md` HO17.
  *Mutation:* enqueue anyway -> `len(queue) == 1` fails.

- **TS7 — Failures are loud, and a scheduler that stopped ticking says so (R55).**
  A scheduled run that crashes, is killed, or ends in a worker death ends `failed` (or `interrupted`, HO18) **with its cause** and appears
  on the project page, the schedule history and the owner's inbox; it is never absent. The tick records `failed` on its own slot record
  if enqueueing raises. The scheduler writes a heartbeat (`last_tick`) at the end of every tick, atomically; the schedule card shows
  **"scheduler stale since `<time>`"** when `now - last_tick` exceeds **two intervals** of the schedule (for a daily rule: 48 h; for a
  weekly or one-off schedule: two intervals of the tick timer, `AUTOTESTER_TICK_INTERVAL_S`, default 60, which T-203's timer unit
  uses), and never shows "healthy" for a schedule that has never ticked. `autotester schedule tick [--project X] [--dry-run]
  [--output json]` follows the T-174 conventions: exit 0 (nothing due, or all handled), 2 (a slot blocked or failed), 3 (config invalid);
  `--dry-run` prints what would fire, claims **no** marker and enqueues nothing; `--output json` is a valid document on stdout and logs go
  to stderr. The tick is **stateless and externally driven** (T-203's systemd timer on Ubuntu; Windows Task Scheduler or by hand in
  development); there is no in-app background loop. *Evidence (LOCAL):* `tests/test_schedule_failures.py` (fake runner that raises
  mid-case; clock advanced past two intervals; never-ticked state); `tests/test_cli_schedule.py` (each exit code, `--dry-run` leaves the
  marker directory empty, JSON parses). `serves:` intent#O12, O4, spec R55, `hosting.md` HO18, T-174 CLI conventions.
  *Mutation:* swallow the runner exception -> the "failed with cause" assertion fails; make `--dry-run` claim a marker -> the empty-directory
  assertion fails.

### HO22-HO24 (read with the rows above, amended copy)

- **HO22 — A per-project schedule with three modes.** A `ScheduleConfig` (`schema/`, `extra="forbid"`) per project has
  `mode` in `manual` (button only, the default), `fixed` (one preset daily time, a `HH:MM`), or `custom` (a time the user selects: a
  one-off date-time, or a weekly set of weekdays + `HH:MM`). Each schedule stores a timezone that is **UTC or IST only** (IST = fixed +05:30, no DST; D-078; default `AUTOTESTER_TIMEZONE` when it is
  UTC or IST, else UTC), so there is no DST to get wrong and no zone database is needed. Invalid values (25:00, a zone other than UTC or IST,
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

### Phase B rows (not in this brief; shown so the builder does not preclude them)

- **TS5 — A scheduled run needs the credential-derived approval, and a missing one is a blocked slot with no trace (R53, CRITICAL).**
  A scheduled run proceeds only when an approval covers (project, run_kind, target) under D-068's credential-derived rule. A project with
  **no declared credential pair**, or a pair whose values are unset, records the slot `blocked_no_credentials` naming which state refused
  it (no `SecretRef`; `SecretRef` with no value; value present but the target outside `allowed_domains`). In every refused state:
  **zero requests reach the network, asserted at the transport as in `consent.md` CN1**; no run directory is created; no queue entry is
  made; no browser factory is called; and the schedule owner sees the refusal on the project page and in their inbox (G4's delivery
  module; the email follows the owner's own preference, `team-test-button.md` TT8). This gate is **in addition to** HO24 (owner's rights):
  an admin-owned schedule on an uncredentialed project is still blocked (AU15: no role skips an approval). A run that proceeds uses the
  approval's own bounds (`max_actions`, `wall_clock_s`); hitting one ends the run and names what it left unreached (O4); no extra
  cooldown is built (gate `plan-approved-g10.md`). **Dependency:** the credential-derived `covering_approval` is the D-068 implementation
  (branch `d063-grant-budget`). Until it lands this row is `BLOCKED-CAPABILITY`, never PASS, and TS1-TS4, TS6 and TS7 are
  judged without it. *Evidence (LOCAL):* `tests/test_schedule_approval.py` — three fixtures (no `SecretRef`, `SecretRef` without a
  value, fully provisioned) through the real `tick` with a recording transport and a recording browser factory; assert the counters
  are 0 for the first two and the filesystem listing of the project's `runs/` is unchanged. `serves:` intent#O12, O7, spec R53,
  D-068, `consent.md` CN1, `hosting.md` HO24, `auth.md` AU15.
  *Mutation:* check approval after `enqueue` -> the "no queue entry" assertion fails; skip the check for an admin owner -> the admin case
  fails.

- **TS6 — One launcher, one queue: the tick never starts a browser (R54, CRITICAL).**
  The tick, the Test button (`team-test-button.md` TT4) and the UI's `trigger_run` all reach a run through the **single** function in
  `stages/run_launcher.py` (G1, `team-foundation.md` TF1); a scheduled run enters the **T-203 run queue**. The tick holds no import of
  `BrowserSession`, `run_and_grade_case`, `_execute_with_trace` or the pipeline modules (an AST import test over `stages/scheduler.py`,
  `cli_schedule.py`, `ui/routes_schedule.py`). The resulting `Run` carries `trigger=SCHEDULE`, `requested_by` = the owner, and `slot_key`
  (the new fields G1 adds, `team-foundation.md` TF2). A second function that builds a `Run` or starts a run is a `doctor` failure
  (one concept, one place). The server-wide cap and the per-project single flight are T-203's (HO17); this row asserts only that the
  scheduler cannot exceed them because it never starts anything itself. *Evidence (LOCAL):* `tests/test_schedule_launcher.py` patches
  the launcher and the queue enqueue function and drives all three entry points, asserting each hits the same patched callable with the
  right `trigger`; the AST import test; `uv run autotester doctor`. `serves:` intent#O12, spec R54, `hosting.md` HO16, HO17, HO23,
  `team-foundation.md` TF1. *Mutation:* import `BrowserSession` into `scheduler.py` -> the import test fails; add a second `Run(...)`
  construction site -> doctor or the grep test fails.

## 4. What exists and what is missing

- Exists, built and unchecked (`wave/g5-schedule-core`, `qa/manifests/g5-schedule-core.md`): `core/localtime.py` (36, fixed `datetime.timezone` offsets UTC and IST +05:30, no `zoneinfo`), `schema/schedule.py` (241: `ScheduleConfig`, `WeeklyRule`, `ScheduleInvalid`, `parse_for_save`, `SlotRecord`, `SlotClaim`, `slot_key`, `ScheduleMode`, `ScheduleZone` {UTC, IST}, `SlotOutcome` (7 values), `SchedulerHealth`), `stages/schedule_time.py` (46), `stages/schedule_store.py` (109), `stages/scheduler.py` (284), `tests/schedule_fakes.py` (86), and six test files `test_schedule_{model,due,marker,catchup,overlap,failures}.py` (157, 127, 142, 180, 70, 199): 112 passed, 0 skipped. Slice coverage: TS1 model and refusal table only; TS2 `due()`, the UTC/IST table, `O_EXCL` claim, two-process and crash tests; TS3 all; TS4 all; TS7 the pure parts.
- Design choices the checker must rule on (manifest items 1-9): `since` is an argument (`MAX_LOOKBACK` 31 days is the maker's number); `ON_TIME_S` 120 s separates `enqueued` from `catch_up`; TS7 staleness is kept verbatim from the contract.
- Missing (phase B, with the owning prerequisite): `Project.schedule` field (T-205/G1), save/pause/resume/delete routes with `schedule.manage` (T-204), purge of claims and records on project delete, `resume` bumping `since`, `deps.gate` (TS5) wired to `covering_approval`, `deps.enqueue` pointing at G1's `stages/run_launcher.py` and T-203's queue (TS6, with the AST import test over `stages/scheduler.py`, `cli_schedule.py`, `ui/routes_schedule.py`; `trigger=SCHEDULE` and `slot_key` on `Run`), `autotester schedule tick [--project] [--dry-run] [--output json]` with exit codes 0/2/3 and the heartbeat write (`cli_schedule.py`, new), the schedule card "stale since", and failure delivery to the inbox.
- Verdict: none (`qa/verdicts/` has no schedule file). Issues: none filed.
- Line-cap risk: `stages/scheduler.py` is 284 of 300; the phase-A rework must not grow it past 300 (move helpers to `stages/schedule_time.py`).

## 5. Files the builder will touch (phase A; all new except MAP.md, counts on the branch)

`src/autotester/core/localtime.py` (36), `src/autotester/schema/schedule.py` (241), `src/autotester/stages/schedule_time.py` (46), `src/autotester/stages/schedule_store.py` (109), `src/autotester/stages/scheduler.py` (284), `tests/schedule_fakes.py` (86), `tests/test_schedule_model.py`, `tests/test_schedule_due.py`, `tests/test_schedule_marker.py`, `tests/test_schedule_catchup.py`, `tests/test_schedule_overlap.py`, `tests/test_schedule_failures.py`, `docs/MAP.md` (349, regenerated), plus the manifest `qa/manifests/t200-schedule-core.md`. 13 files. Not touched: `schema/project.py` (194), `schema/enums.py`, `cli.py`, `ui/app.py`, `pyproject.toml`, `uv.lock` (D-078: no `tzdata`).
Phase B files (for planning only): `schema/project.py` (E, after T-205), `cli_schedule.py` (N), `ui/routes_schedule.py` (N), `stages/run_launcher.py` consumer, `tests/test_schedule_*` additions, `auth/policy.py` rows.

## 6. Test scope

`uv run pytest tests/test_schedule_model.py tests/test_schedule_due.py tests/test_schedule_marker.py tests/test_schedule_catchup.py tests/test_schedule_overlap.py tests/test_schedule_failures.py` plus `uv run ruff check src tests scripts` and `uv run autotester doctor`. Nothing else is affected (no existing module edited); add `tests/test_team_store.py`/`tests/test_team_enums_home.py` only if T-205 has landed and they exist.

## 7. Reachable test cases per criterion (happy path first)

| Criterion | Happy path | Then |
|---|---|---|
| TS1 | a valid fixed `09:00 IST` schedule saves | `25:00`, `24:00`, `9:5`, zone `America/New_York`/`Asia/Kolkata`/`ist`/a list, past one-off, empty weekday set, weekday outside 0-6, duplicate one-off are each refused with the field named and nothing stored |
| TS2 | `09:00 IST` is `03:30 UTC` every day of the year; weekly rule across midnight (IST vs UTC day) | one-off exactly at, 1 s before, 1 s after `now`; `now` never computed inside `due()` |
| TS2 claim | two processes ticking one slot enqueue exactly one run (`O_EXCL`) | crash between claim and record is re-driven |
| TS3 | a slot missed 30 min fires once as `catch_up` | window edge 60 min inclusive; older slots recorded `missed`; two slots in the window run only the latest, the earlier is `superseded`; `MAX_LOOKBACK` |
| TS4 | a slot finding a running entry is skipped and records the blocking id | |
| TS7 (pure) | queue-down at fire time records `failed` with its cause | stale limit `>` vs `>=` at 48 h; duplicate record line read back once |

## 8. Gate answers

- D-078 (`docs/DECISIONS.md` line 2291), verbatim: "Umesh decided (chat, 2026-10-07) not to add the `tzdata` package. Schedules ... support exactly two time zones: UTC and IST, the fixed +05:30 offset with no DST. Any other zone is refused with an error." `Approved-by: Umesh`.
- D-072 item 9 (line 2170): three modes manual / fixed / custom.
- D-068 credential-derived approval: implemented on master (`explore_consent.py:35` `covering_approval`); no open gate. TS5 is phase B.
- Email/inbox delivery of failures: `qa/gates/email-sender-credentials.md:10` `Answered: 2026-10-10 - A (credentials from d:/erp, AutoTester-prefixed keys) - D-081`; phase B only.
- No gate is open for phase A.

## 9. UI surface and persona walk

Phase A: Persona walk: skip (no screen, route or command; pure functions and file markers only).
Phase B: Persona walk: required (sub-admin sets and pauses a schedule; developer sees it only where `schedule.manage` is held at `@own`), from the contract:

## Persona walk (Mode D, the checker's own browser; judged once the schedule UI exists)

`subadmin` (assigned projects only): set a fixed daily schedule, then a custom one-off date-time; see the **next three fire times in the
project's timezone** before saving; save; open the history and find a skipped slot's reason. Pass = <= 3 steps for each task, an
unassigned project's schedule is not reachable (same 404 as a missing project), and a user without `schedule.manage` sees the card
read-only with no editable control. Negative walks: an invalid time (inline refusal, nothing saved); a project with no credentials
(the blocked reason names the Credentials page).

## 10. Dependencies and conflicts

- Phase A: `after: none`. Dispatchable now, in parallel with `t202-litellm-provider`, `land-t203-hosting` and `t204-team-login` (no shared file except the generated `docs/MAP.md`).
- Phase B must follow: `land-t203-hosting` (queue, `Run.trigger`), `t205-g10-headroom` (`run_launcher.py`, `Project.schedule`, `team_enums.py` vocabulary home: `SlotOutcome` etc. may need to move to `schema/team_enums.py` per TF8; the checker rules), `t204-team-login` (`schedule.manage`, `auth/policy.py` rows), `t201a-report-delivery` (failure delivery). QUEUE line ~135 lists `after: t205; t201a; land-t203-hosting`.
- Shared files, proposed owner: `schema/project.py`: T-205; `auth/policy.py`: T-204 owns the table, this unit adds rows; `stages/run_launcher.py`: T-205; `docs/MAP.md`: regenerated, never hand-merged; `qa/contracts/{team-schedule,hosting}.md`, `docs/spec.md`: checker only.
- Other units (T-197, T-198, T-199, T-201, T-202, T-206): none shared.

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
