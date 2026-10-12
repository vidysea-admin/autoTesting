# Manifest - t200-schedule-wiring

**Unit:** T-200 wiring slice: the scheduler's tick now reaches a run through the real run queue and the one launcher, with the run stamped with its origin, and `autotester schedule tick` starts it on this machine. **This unit does NOT close goal task T-200** (routes, `schedule.manage`, HO24 `refused`, the schedule card, inbox/email and the persona walk are HELD, list below).
**Brief:** `qa/briefs/t200-scheduled-test.md` (copied into this branch unchanged). Merged before this unit: `wave/t200a-schedule-core` (PASS) and `wave/t200b-scheduled-test` (PASS, `stages/schedule_gate.py`, `stages/schedule_tick.py`).
**Branch / base:** `wave/t200-schedule-wiring` on master 822dca2b (contains merge 09fc65a8 of t205-g10-headroom; `git merge-base --is-ancestor 09fc65a8 master` exit 0).
**Code commit (pre-check sha):** 8b67fb04. The commit after it adds this manifest only; no source file changes after 8b67fb04. First code commit dc2f75a8, reviewer findings folded in at 8b67fb04.
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (timing/concurrency: one queue entry per slot across processes and restarts, the cross-process overlap check, a tick process that executes queued runs on non-daemon threads; plus a data write: queue file reads, slot records, heartbeat, and the credential gate's approval mint now reachable from a command)
Dual check: no
Why no dual: this diff changes no auth, tenancy or approval-check code and writes nothing to production. It only CALLS `schedule_gate.credential_gate` (merged, dual-checked in t200b) and `launch_run` (unchanged; `run_launcher.py` is not in the diff). It does make the gate's approval mint reachable from a command for the first time, so the checker may rule otherwise; the line to look at is `src/autotester/stages/schedule_wiring.py:real_gate`.
Fix cycle: 0
Executor: claude-sonnet-subagent (maker build subagent)
Status: ready-for-check
Full-suite trigger: none run by the builder (the checker owes it). Existing modules edited: `ui/run_queue.py`, `schema/run_queue.py`, `ui/routes_runs.py`, `stages/schedule_tick.py`, `cli_subapps.py`; their test files and every importer I found by grep ran green (list below).
UI surface: none changed (no route, screen or card), persona walk: skip.

## What was already built and merged, and what was not (established from the brief, the contract and the code on master)

| Criterion | Before this unit (on master) | This unit |
|---|---|---|
| TS1 model, `parse_for_save`, `Project.schedule`, purge function | BUILT (t200a, T-205 field) | - |
| TS1 routes, `schedule.manage`, 403 | NOT built; `auth/policy.py` has only the merge mechanism, no user store | HELD (T-204 not merged) |
| TS2 `due()`, `O_EXCL` claim, two-process test, crash re-drive | BUILT (t200a) | queue-side idempotency key added (below) |
| TS3 catch-up, grace window, `missed` | BUILT (t200a); `grace_from_env` existed | now read by the command; also `.env.example` already documents `AUTOTESTER_SCHEDULE_GRACE_MINUTES` / `AUTOTESTER_TICK_INTERVAL_S` (AT-920 landed in t200b; `tests/test_env_loading.py` and `tests/test_hosting_deploy.py` are green), nothing to add |
| TS4 overlap | BUILT against an injected queue | now fed by the real queue plus the server's persisted queue file |
| TS5 credential gate | BUILT (t200b); "launch_run refuses without it" proven by `test_run_launcher_approval.py` for `trigger=schedule` | gate is wired as `TickDeps.gate`; I never mint or bypass an approval |
| TS6 one launcher, `Run.trigger/requested_by/slot_key` | `launch_run` + `Run` fields BUILT (T-205); `_run_queued` did NOT forward trigger/slot_key (a scheduler entry was stamped `manual`); `QueueEntry` had no `slot_key` | BUILT: `QueueEntry.slot_key`, idempotent `submit`, `_run_queued` forwards the origin |
| TS7 heartbeat, dry-run, exit codes, JSON, `scheduler_health` | BUILT as `run_tick` (t200b); no command | BUILT: `autotester schedule tick [--project] [--dry-run] [--output text|json]` |
| TS7 card "stale since", failures on the project page and in the inbox | NOT built | HELD (UI routes, T-201 delivery) |
| HO24 owner disabled/deleted/without `project.run` -> `refused` | NOT built | HELD (needs T-204 users) |
| TS5/TS7 owner inbox/email | NOT built | HELD (T-201a; no real email in this unit) |

## What changed

| Path | Lines | One job / change |
|---|---|---|
| `src/autotester/stages/schedule_wiring.py` (NEW) | 168 | `tick_all`: lists the scheduled projects, builds each `TickDeps` over a queue-shaped object (`submit`/`snapshot`) with `trigger="schedule"`, owner as `requested_by`, `slot_key`; also `NullQueue`, `LazyQueue`, `schedule_paths`, `scheduled_projects`, the real gate/preview/scrub. Imports no runner |
| `src/autotester/cli_schedule.py` (NEW) | 80 | `autotester schedule tick`; seams `_now`, `_open_queue`; warnings to stderr; exit = report exit code |
| `src/autotester/cli_subapps.py` | +2 | registers `("schedule", cli_schedule.app)`; `cli.py` untouched |
| `src/autotester/schema/run_queue.py` | 56 | `QueueEntry.slot_key: str | None` |
| `src/autotester/ui/run_queue.py` | 254 | `submit(slot_key=)` returns the existing entry for a repeated key (inside the lock, `_view` called after it is released); `set_queue`; `persisted_entries` (read-only view of the server's file, `[]` when absent or unreadable) |
| `src/autotester/ui/routes_runs.py` | 117 | `_run_queued` forwards `trigger` (button->MANUAL, schedule->SCHEDULE, api->CI [ASSUMPTION: "api" is never submitted today]) and `slot_key` to `launch_run`; `tick_runner` (stderr line for a refusal at start); `tick_queue` (in-memory queue, non-daemon worker threads, installed as the process queue) |
| `src/autotester/stages/schedule_tick.py` | 73 | `heartbeat_path` may be `None` (no heartbeat) |
| `tests/test_schedule_wiring.py` (NEW) | 299 | 16 tests: queue idempotency across a restart, one entry per slot, crash re-drive, overlap against the server's file, 3-day outage, gate refusal, dry run, `--project`, project listing, the executor stamping the Run, launcher refusal without approval, review-finding tests |
| `tests/test_cli_schedule.py` (NEW) | 185 | 11 tests: exit codes 0/2/3, JSON on stdout and warning on stderr, dry run, `--project`, lazy queue, private tick queue never touches the server file, direct-import guard |
| `tests/test_schedule_tick.py` | 252+ | the TS6 transitive guard now also covers `schedule_wiring` (+1 self-test) |
| `tests/test_cli_subapp_hook.py`, `tests/golden/cli_commands.json` | +1 / +4 | the command listing and registered group set now include `schedule` |
| `docs/MAP.md` | regenerated | `uv run autotester map` |
| `qa/briefs/t200-scheduled-test.md` | copy | the brief, unchanged |

`stages/run_launcher.py` is NOT in the diff (299 lines, untouched). `core/paths.py` untouched. `docs/ARCHITECTURE.md` untouched (doctor is clean without it).

## Design decisions for the checker to rule on

1. **Where a tick process's runs execute.** The T-203 queue is process-local in memory (the file only restores it after a restart). A separate `schedule tick` process cannot hand an entry to the server's queue, and `get_queue()` there would `recover()` and so mark the server's running runs `interrupted`. So the command opens its OWN in-memory queue (`tick_queue`, `path=None`, never `recover()`), runs the entries through the same `_run_queued` -> `launch_run`, and stays alive on non-daemon threads until they finish. TS4 sees the server's busy projects through `persisted_entries()` (read-only). **Cost, not hidden:** the server cap (HO17), the RAM ledger (HO20) and the project's single flight are NOT shared across the two processes (see open question 1).
2. `since` for a project = `project.json` mtime, but never later than the last heartbeat. Cause: a reviewer showed an unrelated project edit after a due slot would move the bound past it and the slot would vanish with no `missed` record. Exact fix needs `saved_at` on `ScheduleConfig`, set by the save route (HELD).
3. `--project X` writes no heartbeat (a pass over one project proves nothing about the others).
4. The gate still runs before the overlap check (merged t200b behaviour, TS5 "zero trace"); a slot recorded `skipped_overlap` may therefore have minted a covering approval row. Not changed.
5. The gate's bounds stay `CrawlBounds()` (t200b decision 5); `launch_run` computes the real case-derived bounds and re-checks, minting a second row if the first does not cover.
6. New modules: `stages/schedule_wiring.py` and `cli_schedule.py` are named by the brief by job ("deps.enqueue pointing at the launcher", "`cli_schedule.py`") and have one-job docstrings; doctor is clean; D-082 item 1 / D-085 item 3 apply, the checker lists them.

## Review (senior-software-engineer agent, sonnet, read-only, on dc2f75a8): Warning, no Block

Folded in at 8b67fb04: `since` capped at the heartbeat (finding 3); `--project` no heartbeat (finding 4); refusal at start printed to stderr (the visible part of finding 2). Not folded, recorded: (a) tick queue memory-only, so a later tick process or a button press cannot see a scheduled run still going, and a failure after enqueue leaves only the stderr line and a memory entry: a persisted/shared queue is the T-203 owner's design (open question 1); (b) gate-before-overlap ordering (decision 4, merged behaviour).

## Pre-check (code sha 8b67fb04, worktree clean; no full suite, file-scoped, `-o addopts=`)

Pre-check[TS6]: 8b67fb04 uv run pytest -o addopts= tests/test_schedule_wiring.py tests/test_schedule_tick.py tests/test_cli_schedule.py tests/test_run_launcher_approval.py -> 64 passed (tests ran under `autotester.__file__` = `D:\autoTesting\.worktrees\t200-schedule-wiring\src\autotester\__init__.py`)
Pre-check[HO23]: 8b67fb04 uv run pytest -o addopts= tests/test_schedule_wiring.py tests/test_schedule_marker.py tests/test_run_queue.py tests/test_run_queue_resilience.py -> 50 passed (one entry per slot across a queue restart; two ticks one entry; crash re-drive one entry)
Pre-check[TS4]: 8b67fb04 uv run pytest -o addopts= tests/test_schedule_wiring.py tests/test_schedule_overlap.py -> 22 passed
Pre-check[TS3]: 8b67fb04 uv run pytest -o addopts= tests/test_schedule_wiring.py tests/test_schedule_catchup.py -> 38 passed (3 days down: at most one run, the rest `missed`)
Pre-check[TS7]: 8b67fb04 uv run pytest -o addopts= tests/test_cli_schedule.py tests/test_schedule_tick.py tests/test_schedule_failures.py tests/test_cli_surface.py tests/test_cli_advice_resolves.py tests/test_cli_subapp_hook.py -> 138 passed
Pre-check[TS5]: 8b67fb04 uv run pytest -o addopts= tests/test_schedule_gate.py tests/test_run_launcher_approval.py tests/test_schedule_wiring.py -> 44 passed (gate unchanged; wiring test `test_a_scheduled_entry_without_an_approval_is_refused_by_the_launcher`)
Pre-check: 8b67fb04 uv run pytest -o addopts= tests/test_schedule_*.py tests/test_cli_schedule.py tests/test_cli_subapp_hook.py tests/test_run_launcher.py tests/test_run_launcher_approval.py tests/test_run_queue.py tests/test_run_queue_resilience.py tests/test_ui_runs_queue.py tests/test_ui_runs.py tests/test_ui_runs_live_case_approval.py tests/test_credential_run_approval.py tests/test_cli_advice_resolves.py tests/test_cli_surface.py tests/test_doctor.py tests/test_hosting_deploy.py tests/test_env_loading.py tests/test_ui.py tests/test_ui_credential_safety.py -> 444 passed
Pre-check: 8b67fb04 uv run pytest -o addopts= tests/test_coverage_wiring.py tests/test_execute_serial_evidence_scope.py tests/test_pinned_regression.py tests/test_provider_factory.py tests/test_provider_record_concurrency.py tests/test_ui_runs_parallel_crash_recovery.py tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_serial_entry_mix_live.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_ui_runs_serial_resilience.py -> 93 passed, 1 skipped (the other importers of routes_runs / run_queue)
Pre-check: 8b67fb04 uv run ruff check src tests scripts -> All checks passed
Pre-check: 8b67fb04 uv run autotester doctor -> doctor: clean (after `autotester map`)

## Falsifications (throwaway copy of the tree at 8b67fb04 under `C:\Users\Lenovo\AppData\Local\Temp\at200-fals-4417731`, `PYTHONPATH` = the copy's `src`, `autotester.__file__` printed inside the copy; green before, red after, restored and green again)

| Criterion | Edit in the copy | Red node after | Before / after / restored |
|---|---|---|---|
| TS6 origin stamped | `_run_queued`: drop `slot_key=entry.slot_key` | `test_a_scheduler_entry_becomes_a_run_stamped_schedule_with_its_slot` | 27 passed / 1 failed / 16 passed |
| HO23 queue key | `submit`: `held = None` | `test_one_slot_key_is_one_queue_entry_even_across_a_restart` | 16 / 1 failed / 16 |
| TS4 cross-process | `_snapshots`: ignore `persisted()` | `test_a_busy_project_in_the_servers_persisted_queue_is_a_skipped_overlap` | 16 / 1 failed / 16 |
| TS7 dry run | `tick_cmd`: `dry_run=dry_run` -> `dry_run=False` | `test_dry_run_claims_nothing_and_writes_no_heartbeat`, `test_project_option_limits_the_pass` | 11 / 2 failed / 11 |
| TS3 never dropped | `scheduled_projects`: drop `min(since, heartbeat)` | `test_an_edit_after_a_missed_slot_does_not_hide_it` | 16 / 1 failed / 16 |
| TS7 heartbeat | `tick_all`: always pass `paths.heartbeat` | `test_a_tick_for_one_project_does_not_refresh_the_global_heartbeat` | 16 / 1 failed / 16 |

Note: the first F5 attempt used a replacement text that matched three places and left the copy mutated; I re-extracted `schedule_wiring.py` from `git show HEAD:`, diffed IDENTICAL, and redid F5 and F6 cleanly. Not falsified (said plainly): the transitive guard line for `schedule_wiring` (its +1 self-test proves the guard catches a leak there); the `tick_runner` stderr line has a test but no dedicated mutation; the non-daemon-thread behaviour of `tick_queue` is not exercised by a test (no real thread is started in tests).

## HELD (not built), with the dependency each waits on

1. Routes `GET/POST/DELETE` schedule with `schedule.manage`, owner = `requested_by`, `resume` bumping `since` / a `saved_at` field: T-204 (not merged).
2. HO24 `refused` for a disabled/deleted/unauthorised owner: T-204 users.
3. Schedule card "scheduler stale since" (`scheduler_health` is ready), skipped-slot history on the project page, persona walk: need 1.
4. Inbox/email delivery of `failed`, `blocked_no_credentials`, refused-at-start: T-201a. No real email sent here.
5. Windows Task Scheduler / service / timer installation: not done (nothing outside the repo touched). The command is run by hand or by a timer the owner sets up.
6. Any live run against Pathlynks or any product: none made. Wiring `purge_project` to a project-delete path: still no delete path on master.
7. Wiring an `AUTOTESTER_TICK_INTERVAL_S` consumer: the key is read by `tick_interval_from_env` for the card (HELD with 3); the command has no loop, by contract.

## Owner questions

1. **Cross-process queue.** A scheduled run started by `schedule tick` runs in the tick process, outside the server's cap, RAM ledger and per-project single flight; a button press can overlap it, and the UI queue page will not list it. Options: (a) accept for the local deployment, (b) a shared queue file with a lock owned by T-203, (c) the tick calls the running server (needs T-204 identity). Which?
2. Is making the gate's approval mint reachable from `autotester schedule tick` a "security" trigger for a dual check? I said no (only calls).
3. `"api"` queue trigger mapped to `Trigger.CI`: confirm or name another value.

Metrics: start=2026-10-11T21:58:50Z end=2026-10-11T22:31:00Z wall_min=32 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=6 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=0 mutants=0 defects_unit=0 defects_6c=0
Metrics-note: start is the branch creation time (03:28:50 +05:30); the code commit dc2f75a8 landed 03:50:36 and the review-fix commit 8b67fb04 at 03:56:11 +05:30.
