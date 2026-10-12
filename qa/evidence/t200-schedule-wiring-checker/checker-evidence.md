# Checker evidence - t200-schedule-wiring (cycle 0)

Copy: `git archive 8b67fb04` into a random folder under C:\Users\Lenovo\AppData\Local\Temp; `PYTHONPATH=<copy>/src`; `autotester.__file__` printed inside the copy. pytest `-o addopts= -p no:cacheprovider`.

## Re-run (parallel batches)
- tests/test_schedule_wiring.py test_schedule_tick.py test_cli_schedule.py test_run_launcher_approval.py: 64 passed
- test_schedule_marker / run_queue / run_queue_resilience / schedule_overlap / catchup / failures / gate: 93 passed
- test_cli_surface / cli_advice_resolves / cli_subapp_hook / ui_runs_queue / ui_runs / doctor: 145 passed
- importers of routes_runs and run_queue, plus marker and due: 178 passed, 1 skipped
- ruff check src tests scripts: All checks passed; autotester doctor: clean

## Independent end-to-end (real CLI `autotester schedule tick`, throwaway AUTOTESTER_ROOT, project with a fixed daily slot 2 min old, owner u1)
- `--dry-run`: `zz:fixed:...  would be blocked`, exit 2, nothing written besides project.json.
- real tick, no credentials: outcome blocked_no_credentials (detail names no_secretref), exit 2; no run directory, no `.work/run_queue.json`; claim, record and heartbeat written.
- real tick, gate allowed, launcher replaced by a recorder that sleeps 3 s: outcome catch_up, exit 0; the recorder saw trigger=schedule, requested_by=u1, slot_key=zz:fixed:...Z, run_id = the queue entry id; the process exited only after the recorder finished (non-daemon thread proven); a second tick of the same slot: no records, still 1 record line.
- two ticks started at the same moment on one slot: 1 record, 1 claim, exactly one process printed the outcome.
- server queue file holding a `running` entry for the project: skipped_overlap, nothing enqueued, the server file unchanged (status still running, no recover()).
- Backdating probe (ISS-1): schedule saved now with a slot 30 min earlier, heartbeat 3 days old -> the dry run lists that slot as would_fire.

## Falsification floor (each in its own copy of src + tests + scripts; green before, red after, restored green)
| criterion | edit | named node | before / after / restored | assertion that fired |
|---|---|---|---|---|
| TS6 | _run_queued drops `slot_key=entry.slot_key` | test_a_scheduler_entry_becomes_a_run_stamped_schedule_with_its_slot | 1 passed / 1 failed / 1 passed | ('u1', None) == ('u1', 'demo:...09:00Z') |
| HO23 | submit: `held = None` | test_one_slot_key_is_one_queue_entry_even_across_a_restart | pass / fail / pass | two different run ids |
| TS4 | _snapshots ignores persisted() | test_a_busy_project_in_the_servers_persisted_queue_is_a_skipped_overlap | pass / fail / pass | enqueued != skipped_overlap |
| TS3 | drop `min(since, heartbeat)` | test_an_edit_after_a_missed_slot_does_not_hide_it | pass / fail / pass | [] != [missed] |
| TS7 | tick_cmd passes dry_run=False | test_dry_run_claims_nothing_and_writes_no_heartbeat | pass / fail / pass | report.dry_run is False |
| TS5 | real_gate returns allow-all (the builder had no TS5 row) | test_a_scheduled_project_without_credentials_is_blocked_and_exits_2 | pass / fail / pass | exit_code 0 == 2 |
