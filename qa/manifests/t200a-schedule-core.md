# Manifest - t200a-schedule-core

**Unit:** T-200 phase A: the PURE schedule core (model, `due()`, `O_EXCL` claim marker, catch-up, overlap, heartbeat staleness). Zones are UTC and IST only (D-078). Re-land of `wave/g5-schedule-core` (tip 29ce74e8) onto master 3a16616c, source files copied unchanged.
**This unit does NOT close goal task T-200.** Phase B (TS5, TS6, routes with `schedule.manage`, `autotester schedule tick` CLI, the schedule screen, failure delivery, `Project.schedule`) is not built and needs its own brief after `land-t203-hosting`, `t205-g10-headroom`, `t201a-report-delivery` and `t204-team-login`.
**Brief:** `qa/briefs/t200-scheduled-test.md` (phase A).
**Branch / base:** `wave/t200a-schedule-core` on master 3a16616c.
**Code commit (pre-check sha):** 4662f250 (the manifest commit after it adds only this file).
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (timing/concurrency: one claim per slot across two OS processes, the 60-minute window edge)
Dual check: no (the schedule has no more rights than its owner, adds no auth or tenancy code, writes nothing to production; no `dual-trigger` applies)
Fix cycle: 0
Executor: claude-sonnet-subagent (maker build subagent)
Status: ready-for-check
Full-suite trigger: none for this slice. No existing module is edited (`schema/project.py`, `schema/enums.py`, `cli.py`, `ui/app.py`, `pyproject.toml`, `uv.lock` untouched).

## CONTRACT AMENDMENT THE CHECKER MUST BRING (maker never edits `qa/contracts/`)

`qa/contracts/team-schedule.md` on master is STALE against D-078 (it still says IANA zones, DST rows, `tzdata`). I did NOT bring the contract change over: `qa/contracts/team-schedule.md`, `qa/contracts/hosting.md` and `docs/spec.md` R51 are exactly as on master. The code was built against the amended criteria text (TS1-TS4, TS7, HO22-HO24 as quoted in the brief, from `wave/g5-schedule-core` commit 29ce74e8). **The checker must bring the D-078 amendment onto master (from 29ce74e8: `qa/contracts/team-schedule.md`, `qa/contracts/hosting.md`, `docs/spec.md` R51) before or as part of its check**, and judge this unit against the amended text. A separate checker agent was asked to do that in the root checkout.

## What changed (all new files, plus the generated map)

| Path | Lines | One job |
|---|---|---|
| `src/autotester/core/localtime.py` | 36 | The two supported zones as `datetime.timezone` fixed offsets (UTC, IST = +05:30); no `zoneinfo`, no `tzdata`. |
| `src/autotester/schema/schedule.py` | 241 | `ScheduleConfig`, `WeeklyRule`, `ScheduleInvalid`, `parse_for_save`, `SlotRecord`, `SlotClaim`, `slot_key`, closed vocabularies `ScheduleMode`, `ScheduleZone`, `SlotOutcome`, `SchedulerHealth`. |
| `src/autotester/stages/schedule_time.py` | 46 | `slot_instants()`, pure. |
| `src/autotester/stages/schedule_store.py` | 109 | `O_EXCL` claim, append-only records (idempotent per slot), atomic heartbeat; `os` only. |
| `src/autotester/stages/scheduler.py` | 284 | `due()` (pure), `tick_project()`, `scheduler_health()`, env helpers. |
| `tests/schedule_fakes.py` + `tests/test_schedule_{model,due,marker,catchup,overlap,failures}.py` | 86 + 157, 127, 142, 180, 70, 199 | Evidence: 112 tests. |
| `docs/MAP.md` | regenerated | `uv run autotester map`. |

## Design decisions the checker must rule on (carried from the source manifest, unchanged)

1. `since` is an argument; `MAX_LOOKBACK` = 31 days is the maker's number (tested).
2. `ON_TIME_S` = 120 s separates `enqueued` from `catch_up` (maker's number).
3. Grace edge is whole-minute: `now` floored to the minute for the window test.
4. Re-drive is idempotent per slot (`REDRIVE_AFTER_S` = 120 s); `append_record` writes nothing when the slot already has a record.
5. Queue seam: `QueueSnapshot` is built by the caller; no queue status string is copied here.
6. `SlotOutcome` etc. live in `schema/schedule.py`; TF8 would move them to `schema/team_enums.py` (pure relocation, phase B / T-205).
7. TS7 staleness is kept verbatim from the contract: a daily rule is stale after 48 h, a weekly or one-off schedule after two tick-timer intervals (120 s by default). That looks unintended for weekly rules; the change is one line in `scheduler_health`, and the contract is the checker's to amend if Umesh wants it.

## Owed (phase B and others; not read as done)

TS5 (credential gate), TS6 (launcher/queue wiring, AST import test), TS1 rest (`Project.schedule`, routes, `schedule.manage`, purge on project delete), TS7 rest (CLI `autotester schedule tick`, heartbeat write at tick end, card "stale since", inbox delivery), HO24 `refused`.

## Pre-check (final code commit 4662f250, worktree clean; no full suite, no directory-wide run)

Pre-check: 4662f250 uv run pytest tests/test_schedule_model.py tests/test_schedule_due.py tests/test_schedule_marker.py tests/test_schedule_catchup.py tests/test_schedule_overlap.py tests/test_schedule_failures.py t=75s -> 112 passed
Pre-check[TS1]: 4662f250 uv run pytest tests/test_schedule_model.py t=3s -> 45 passed
Pre-check[TS2]: 4662f250 uv run pytest tests/test_schedule_due.py tests/test_schedule_marker.py t=8s -> 20 passed
Pre-check[TS3]: 4662f250 uv run pytest tests/test_schedule_catchup.py t=9s -> 22 passed
Pre-check[TS4]: 4662f250 uv run pytest tests/test_schedule_overlap.py t=3s -> 6 passed
Pre-check[TS7]: 4662f250 uv run pytest tests/test_schedule_failures.py t=18s -> 19 passed

The untagged `Pre-check:` line above is the six brief-section-6 files together on 4662f250 (the tool's lint recognises only `C<n>` criterion ids, so the per-criterion `TS<n>` lines, which the brief asks for, are accompanied by this untagged aggregate line). `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> one violation, `stale-generated: docs/SNAPSHOT.md`, which is pre-existing (SNAPSHOT.md is untouched by this unit and is regenerated by `autotester snapshot`, not part of the brief's file list); no violation names a file of this unit.

## Falsifications (one per criterion; green before, red after, restored; each in a throwaway copy under the scratchpad, never the worktree)

| Criterion | Edit in the copy | Red node(s) after |
|---|---|---|
| TS1 | `_HHMM` hour class `([01]\d|2[0-3])` -> `([0-2]\d)` | `test_invalid_schedule_is_refused_with_a_reason_naming_the_field[25:00]` and `[24:00]` (45 passed before, 43 after, 45 restored) |
| TS2 | IST offset `timedelta(hours=5, minutes=30)` -> `timedelta(hours=5)` | `test_ist_nine_oclock_is_0330_utc_every_day_of_the_year` (+4 more; 14 passed before, 9 after, 14 restored) |
| TS3 | window edge `clock - s.instant <= grace` -> `<` | `test_the_60_minute_window_edge_is_inclusive[60-min]` (22 passed before, 20 after, 22 restored) |
| TS4 | overlap check `if blocker is not None:` -> `if False and ...` | `test_slot_finding_a_running_entry_is_skipped_with_the_blocking_id` (+2; 6 before, 3 after, 6 restored) |
| TS7 | failed record drops its cause (`detail=cause` -> `detail=None`) | `test_queue_down_when_the_slot_fires_is_recorded_failed_with_its_cause` (+1; 19 before, 17 after, 19 restored) |

Not falsified in this cycle (floor is one per criterion): the `exists()`-then-write claim race, the stale limit `>` vs `>=`, the torn-claim rebuild. The source manifest records red runs for the first two on the pre-merge head.

## Brief points that turned out wrong or different

- The brief says to merge `wave/g5-schedule-core`; I copied the 12 code/test files from it with `git checkout <branch> -- <paths>` instead, so no contract file change and no source manifest enter the history. Result: master's contract files stay untouched.
- The brief says `docs/MAP.md` conflicts; with a copy-based re-land there was no conflict, MAP was just regenerated.
- The suite wait: `tick.mjs --ceilings` showed `lane=code cap=0` from 00:35 to 01:04, so tests started only then.

Metrics: start=2026-10-11T00:15:00Z end=2026-10-11T01:20:00Z wall_min=65 agent_min=unavailable blocked_min=30 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=0 mutants=0 defects_unit=0 defects_6c=0
