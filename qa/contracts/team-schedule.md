# Contract — team-schedule: per-project scheduled auto-test (G5, `t200-schedule`)

**Covers:** unit G5 `t200-schedule` (goal task T-200), requirements R51-R55 (and R65 where a row touches paths, locks or markers).
**Owner:** /checker. **Status:** ACTIVE (2026-10-07); build starts only after `qa/gates/plan-approved-g10.md` is answered.
**Criticality:** CRITICAL for TS5 and TS6; HIGH elsewhere. Tier L (concurrency/timing, auth, outward-facing run), so a **dual check**
applies to TS2-TS6.
**Serves:** `docs/intent.md` O12 (schedule), O7 (credential boundary), O4 (no silent skips); D-072 item 9 (a button press, a fixed time,
or a custom time the user selects, per project); D-068 (credential-derived approval); D-071.
**Depends on:** `hosting.md` (T-203's queue HO16-HO19, schedule rows HO22-HO24), `auth.md` (permission engine, `schedule.manage`),
`consent.md` (CN1 no-trace refusal), `parallel-run.md`, `run-trace.md`, and unit **G1** (`team-foundation.md`: the one run launcher, the
router list, the policy seam, the schema fields).
**Source:** the maker's proposal `.work/plan-g10/contract-proposal-T-200.md`, reconciled with `docs/spec.md` R51-R55 and `hosting.md`.

## Boundary with `hosting.md` (read first — those rows govern, this file adds only what they lack)

| `hosting.md` row | what it already states | what this contract does with it |
|---|---|---|
| **HO22** | three modes, IANA timezone, DST-correct, invalid values refused and store nothing, `schedule.manage` to set | **Referenced, not repeated.** TS1 adds the model shape, persistence and the `schedule.manage` route policy; TS2 adds the pure `due()` function that makes HO22's DST claim checkable |
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

## Criteria

- **TS1 — A schedule is a typed, bounded, persisted setting, and only `schedule.manage` changes it (R51).**
  `schema/schedule.py` defines `ScheduleConfig` (`extra="forbid"`): `mode` in `manual | fixed | custom`; `fixed` = one daily `HH:MM`;
  `custom` = one or more **one-off date-times** (each fires once, then is marked consumed) **and/or** one weekly rule (a non-empty weekday
  set plus `HH:MM`), at least one of the two; `timezone` (IANA name; default `AUTOTESTER_TIMEZONE`, else `UTC`); `owner`; `paused`.
  `manual` is the default and **produces no slot**: a `manual` project is never enqueued by a tick, however many ticks run. No mode can
  yield more than one slot per local calendar day for one rule (so the "interval floor" of the proposal is structural, not a setting).
  Invalid values are refused at save with a reason naming the field, and **nothing is stored** (HO22 states the list: `25:00`, unknown
  zone, past one-off, empty weekday set; add `24:00`, `9:5`, a one-off in a DST gap with no resolution rule, a weekday outside 0-6, a
  duplicate one-off). The value lives in `Project.schedule` (G1's field, `team-foundation.md` TF6); a `project.json` without it loads as
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
  file and reads no environment. A table of cases returns the exact slot instants for: `UTC`; `Asia/Kolkata` (no DST); one DST zone
  (`America/New_York`) across the **spring-forward day** (a `02:30` rule fires once, at the first valid instant) and the **fall-back day**
  (a `01:30` rule fires once, not twice); a weekly rule across midnight; a one-off exactly at, one second before, and one second after
  `now`. An unknown zone cannot reach `due()` (TS1 refused it). The zone database is available on Windows and Ubuntu: `tzdata` is
  a declared dependency in `pyproject.toml` (Windows has no system zone data), and the same table runs green on both. The **claim marker**
  for a slot is created atomically with `os.open(path, O_CREAT | O_EXCL | O_WRONLY)` under the data root (R65: no `fcntl`, no `flock`,
  no `pwd`); the file name is `slot_key` made path-safe, and it is written **before** the enqueue. Two concurrent ticks for one slot
  produce **exactly one** claim, hence one queue entry; the loser records nothing and exits 0. Crash safety: a marker whose
  queue entry does not exist (process died between claim and enqueue) is re-driven by the next tick, and the queue's idempotency key
  (`HO23`: project + slot) makes the re-drive create at most one entry. *Evidence (LOCAL):* `tests/test_schedule_due.py` (table, injected
  clock, no sleeping); `tests/test_schedule_marker.py` spawns **two OS processes** (`multiprocessing`, `spawn` context so it runs the same
  on Windows) against one project and counts queue entries == 1, then kills a tick between claim and enqueue (monkeypatched hook raising
  `SystemExit`) and re-ticks, counting still == 1. `serves:` intent#O12, spec R52, R65, `hosting.md` HO22, HO23.
  *Mutation:* create the marker with `exists()` then `write` (check-then-act) -> the two-process test fails; compute `now` inside `due()`
  -> the injected-clock table fails; remove `tzdata` from `pyproject.toml` -> the Windows zone case fails (the check reads the manifest).

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

## Persona walk (Mode D, the checker's own browser; judged once the schedule UI exists)

`subadmin` (assigned projects only): set a fixed daily schedule, then a custom one-off date-time; see the **next three fire times in the
project's timezone** before saving; save; open the history and find a skipped slot's reason. Pass = <= 3 steps for each task, an
unassigned project's schedule is not reachable (same 404 as a missing project), and a user without `schedule.manage` sees the card
read-only with no editable control. Negative walks: an invalid time (inline refusal, nothing saved); a project with no credentials
(the blocked reason names the Credentials page).

## Out of scope / ignore

- The queue, concurrency cap and slot release (T-203, HO16-HO20); the tick's systemd unit and deploy guide (T-203).
- The baseline comparison between runs (T-167, `release-regression.md`); this contract only starts a run.
- Report delivery content and the inbox (`team-test-button.md` TT7-TT9); recurring subscribers beyond the owner; per-user cooldowns.
- Cron expressions, sub-daily intervals, holiday calendars.

## No-fire list (must NOT happen)

- No browser, `Run`, run directory or network request from the tick, `schedule` CLI or schedule routes except through the one launcher and queue.
- No second run for one slot; no run for a `manual`, paused, or deleted schedule; no backfill of missed slots.
- No schedule change without `schedule.manage`; no secret value in a slot record, a heartbeat, a log line or a CLI output.
- No POSIX-only primitive (`fcntl`, `flock`, `pwd`, `os.fork`) in the new modules.

## Amendment log (append-only; git history is the version)

- 2026-10-07 · init · contract created for unit G5 from the maker's proposal T-200 (TS1-TS12), `docs/spec.md` R51-R55 and `hosting.md`
  HO22-HO24. Folded: proposal TS1 (typed schedule) -> TS1, reshaped to the spec's R51 modes (fixed = one daily `HH:MM`; custom = one-offs or a
  weekly weekday set, the "interval floor" became structural); TS2 -> TS2; TS3 -> TS3, changed from "after 3 missed slots, one catch-up" to
  the spec's R52 grace window (default 60 min, `HO23`); TS4 -> TS4; TS5 -> TS5; TS6 -> TS6; TS7 + the proposal's TS11 CLI -> TS7.
  Dropped as duplicates of governing rows or other contracts: proposal TS8 "off means off" (TS1/TS4 and HO24), TS9 report delivery
  (-> `team-test-button.md` TT7-TT9, `hosting.md` HO25-HO29), TS10 bounded spend (folded into TS5), TS12 persona walk (kept as the unnumbered
  walk above). Subscribers dropped (HO26: owner only).
