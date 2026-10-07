# Manifest - g5-schedule-core

**Unit:** G10/G5 `t200-schedule`, slice 1 of 2: the PURE CORE only (schedule model, `due()`, claim markers, catch-up, overlap, stale-scheduler detection). No login (T-204), no T-203 queue, no UI, no CLI.
**Contract:** `qa/contracts/team-schedule.md` TS1-TS4 and TS7 (pure parts); read with `hosting.md` HO22-HO24, `team-foundation.md` TF6/TF8, `docs/spec.md` R51-R55, D-072 item 9.
**Branch / base:** `wave/g5-schedule-core` on `origin/master` c09debd1.
**Policy-Version:** proportional-verification/2026-10-06.6 (pinned by the coordinator brief)
**Tier:** L, judged by me. The slice makes a timing/concurrency claim (one claim per slot across two OS processes, DST arithmetic, a 60-minute window edge), which is an L trigger under the policy. It is not a security/auth/tenancy or production-write unit, so one checker, no dual check, and no builder or checker full suite beyond the one the pre-push check (6c) runs. Wall budget 45 min.
**Fix cycle:** 0
**Dual check:** no
**Executor:** claude-sonnet-subagent (maker build subagent).
**Status:** ready-for-check
**Full-suite trigger:** none for this slice. No existing module was edited (`app.py`, `cli.py`, `schema/project.py`, `schema/enums.py` untouched); `docs/MAP.md` was regenerated with `autotester map`.

## What changed (all new files, plus the generated map)

| Path | One job |
|---|---|
| `src/autotester/core/localtime.py` (68 lines) | Zone lookup (`UTC` never needs a zone database) and DST-correct local-to-UTC resolution: a gap resolves to the clock jump, a repeated time to its first occurrence. |
| `src/autotester/schema/schedule.py` (243) | `ScheduleConfig` (+ `WeeklyRule`, `ScheduleInvalid`, `parse_for_save`), `SlotRecord`, `SlotClaim`, `slot_key`, and the closed vocabularies `ScheduleMode`, `SlotOutcome` (7 values), `SchedulerHealth`. |
| `src/autotester/stages/schedule_time.py` (45) | `slot_instants()`: the UTC instants a schedule means in a window. Pure. |
| `src/autotester/stages/schedule_store.py` (96) | `O_EXCL` claim, append-only records, atomic heartbeat. `os` only: no `fcntl`/`flock`/`pwd`/`fork`. |
| `src/autotester/stages/scheduler.py` (283) | `due()` (pure), `tick_project()` (claim, overlap check, injected enqueue, record, crash re-drive), `scheduler_health()`, env helpers. |
| `tests/schedule_fakes.py`, `tests/test_schedule_{model,due,marker,catchup,overlap,failures}.py` | The evidence (101 passed + 1 strict xfail). |
| `docs/MAP.md` | Regenerated (`autotester map`), required by doctor. |

## Design decisions the checker should know (each is my reading, flagged, not silent)

1. **Gap rule.** TS2 says a `02:30` rule on spring-forward "fires once, at the first valid instant". I read that literally as the instant the clocks jump (New York 2026-03-08: 07:00 UTC = 03:00 EDT), not 03:30. If the checker means 03:30, the change is one line in `core/localtime.py::resolve_local`.
2. **`since` is an argument.** A schedule needs a lower bound or "missed" would reach back forever. `due()`/`tick_project()` take `since` (the caller passes the save/resume time or the last tick) and also never look back more than `MAX_LOOKBACK` = 31 days. 31 days is my number, not the contract's.
3. **`catch_up` vs `enqueued` label.** A slot seen within `ON_TIME_S` = 120 s of its instant is `enqueued`; later (still inside the grace window) it is `catch_up`. The 120 s is my number.
4. **Grace edge is whole-minute.** `now` is floored to the minute for the window test, so exactly 60 min and 60 min 59 s fire, 61 min does not.
5. **Re-drive.** A claim with no slot record and older than `REDRIVE_AFTER_S` = 120 s is finished by the next tick. A claim file torn before its body was written is rebuilt from its key and file mtime (decision recomputed against grace). Two ticks re-driving the same orphan at the same instant could write two records for one slot, but the idempotent queue (HO23) still creates one entry; I did not add a second lock.
6. **Queue seam.** `QueueSnapshot(id, project, active, slot_key)` is built by the caller from the real queue; `active` = queued or running is decided there, so no queue status string is copied here (T-203's `QueueStatus` is not on master yet).
7. **Vocabulary home.** TF8 puts `SlotOutcome` in `schema/team_enums.py` (G1, not on master). They live in `schema/schedule.py` for now; moving them is a pure relocation. Merge-time note for G1.
8. **Manual is strict.** `mode=manual` with any time field is refused (a silent leftover would be inert but misleading). `one_offs` max 50 and duplicate weekdays refused are my bounds.
9. **TS7 staleness as written.** Daily rule: 48 h. Weekly or one-off: 2 x `AUTOTESTER_TICK_INTERVAL_S` (default 60 -> 120 s). Implemented verbatim, though a weekly schedule going "stale" after 2 minutes looks unintended; recorded as an observation for the checker, not changed.

## tzdata: STOPPED, owed to Umesh (not done on purpose)

TS2 wants `tzdata` declared in `pyproject.toml`. It is in neither `pyproject.toml` nor `uv.lock` (grep empty), and D-074 authorises only `argon2-cffi` as a new dependency. Per the brief I did NOT touch `pyproject.toml` / `uv.lock`. Consequences, measured here: on this Windows box `ZoneInfo("America/New_York")` raises `No time zone found` (no `tzdata` module, `TZPATH=()`), so only the DST/zone-name tests need a zone database. I ran them with `tzdata==2026.5` installed into a scratch directory on `PYTHONPATH` (not in the repo, not in the venv). `UTC` works without it (special-cased). `tests/test_schedule_due.py::test_tzdata_is_a_declared_dependency_for_windows` is a **strict xfail** that reads the manifest; it turns red the moment `tzdata` is added (verified, see falsification list), which forces removing the xfail. **Needed:** a D-entry from Umesh authorising `tzdata` in `pyproject.toml` + `uv.lock`; until then the DST rows can only be judged with a zone database on the path.

## Criteria, verbatim from the contract (this slice's share is marked)

**Slice coverage.** TS1: model + refusal table only (routes, `schedule.manage`, persistence in `Project.schedule`, delete-removes-markers are owed). TS2: `due()`, DST table, `O_EXCL` claim, two-process and crash tests (the `tzdata` declaration is owed). TS3: all of it. TS4: all of it, against a fake queue. TS7: failed-record, heartbeat, staleness (the CLI and the project-page/inbox display are owed). TS5 and TS6: not built.

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

## Owed (not in this slice; do not read the above as done)

- **TS5** credential-gate (`blocked_no_credentials`; needs the D-068 `covering_approval` from `d063-grant-budget`). `tick_project` has no gate seam yet; the wiring slice adds `deps.gate` before `enqueue`. Also HO24 owner-rights `refused`.
- **TS6** launcher + queue wiring: `deps.enqueue` must point at G1's `stages/run_launcher.py` and T-203's queue; the AST import test over `stages/scheduler.py`, `cli_schedule.py`, `ui/routes_schedule.py`; `trigger=SCHEDULE` and `slot_key` on `Run`.
- **TS1 rest:** `Project.schedule` field (G1), save/pause/resume/delete routes with `schedule.manage` (T-204), purge of claims and records on project delete, resume must bump `since`.
- **TS7 rest:** `autotester schedule tick [--project] [--dry-run] [--output json]` and exit codes 0/2/3, the heartbeat write at the end of a tick, schedule-card "stale since", inbox delivery of failures.
- **TF8:** relocate the three vocabularies to `schema/team_enums.py`; `ARCHITECTURE.md` rows (needs the Lab-protocol D-entry); `tzdata` D-entry (above).

## How to verify

| # | Command | Expected (maker run) |
|---|---|---|
| 1 | `PYTHONPATH=<dir with tzdata> uv run pytest tests/test_schedule_model.py tests/test_schedule_due.py tests/test_schedule_marker.py tests/test_schedule_catchup.py tests/test_schedule_overlap.py tests/test_schedule_failures.py` | `101 passed, 1 xfailed` |
| 2 | `uv run ruff check src tests scripts` | All checks passed |
| 3 | `uv run autotester doctor` | doctor: clean |
| 4 | `git grep -n "fcntl\|flock\|pwd\|fork" -- src/autotester/stages/schedule_*.py src/autotester/stages/scheduler.py` | no hits (also asserted by `test_new_modules_use_no_posix_only_primitive`) |

Removed/renamed names: none (every change is a new file), so no `git grep tests/` scope addition.

## Falsifications (green before, red after, restored: each in a throwaway copy under the scratchpad, run with the worktree venv, script `mutate.py`)

| Criterion | Edit in the copy | Red node |
|---|---|---|
| TS1 | `_HHMM` hour class `([01]\d|2[0-3])` -> `([0-2]\d)` | `test_invalid_schedule_is_refused_with_a_reason_naming_the_field[25:00]` |
| TS2 | `now` computed inside `due()` | `test_one_off_fires_at_or_after_its_instant_never_before[exactly-at]` |
| TS2 | `claim()` as `exists()` then open (check-then-act) | `test_two_processes_ticking_one_slot_enqueue_exactly_one_run` (red on the first try; it is a race, so a green run on another machine would not prove the claim) |
| TS2 | gap resolves without the transition search | `test_new_york_spring_forward_0230_fires_once_at_first_valid_instant` |
| TS2 | add `tzdata` to the copy's `pyproject.toml` | `test_tzdata_is_a_declared_dependency_for_windows` goes XPASS(strict) = red: the check reads the manifest |
| TS3 | window edge `<=` -> `<` | `test_the_60_minute_window_edge_is_inclusive[60-min]` |
| TS3 | earlier in-window slots not recorded superseded | `test_two_slots_inside_the_window_run_only_the_latest_and_the_earlier_is_superseded` |
| TS4 | overlap check disabled (`if False:`) | `test_slot_finding_a_running_entry_is_skipped_with_the_blocking_id` |
| TS7 | failed record drops its cause | `test_queue_down_when_the_slot_fires_is_recorded_failed_with_its_cause` |
| TS7 | stale limit `>` -> `>=` | `test_a_daily_rule_is_stale_after_two_intervals_of_48_hours[48h-exactly]` |

Not falsified, honestly: no mutant for the torn-claim rebuild; the `MAX_LOOKBACK` cap has no test. No repeat runs were done for the two-process race (no baseline p measured).

Metrics: start=2026-10-07T14:00:00Z end=2026-10-07T15:25:00Z wall_min=85 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=10 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
