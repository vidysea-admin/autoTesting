# Verdict - t200-schedule-wiring (T-200 wiring slice)

Cycle checked: 0
Head checked: 9647f0f7 (code 8b67fb04; base 822dca2b = git merge-base HEAD master), worktree .worktrees/t200-schedule-wiring, bound to D:/autoTesting/.worktrees/t200-schedule-wiring
Policy: proportional-verification/2026-10-10.9. Evidence: qa/evidence/t200-schedule-wiring-checker/checker-evidence.md. Checkpoint: qa/checkpoints/t200-schedule-wiring.md
Date: 2026-10-12. Single coordinator, no sub-checkers. SERIAL: the e2e probes share a temp root and queue file, so they ran one after another; the tests ran as 3 parallel batches. Lane check not applicable (L).

## Check plan
Logic and concurrency (queue idempotency, cross-process claim, overlap against the server file, tick-process threads): affected tests, independent e2e through the real CLI, one falsification per criterion. Security read of the gate wiring. Diff scope (step 4c) over 15 files. UI surface: none (no route, template or rendered output changed; ui/routes_runs.py only forwards trigger/slot_key and adds tick_queue), so no browser walk. No data artifact, no prompt change.

VERDICT: PASS
SCOREBOARD: 6/6 claimed criteria slices met (TS3, TS4, TS5, TS6, TS7 tick/CLI side, HO23); the HELD parts (routes, schedule.manage, HO24 refused, card, inbox) are not claimed and not judged; 0 invariants named by the manifest.
TIER: L (concurrency: schedule_wiring.py scheduled_projects/_snapshots, ui/run_queue.py submit idempotency key and persisted_entries, routes_runs.py tick_queue worker threads); no raise
DUAL-CHECK RULING: not required. The diff changes no approval-deciding code: run_launcher.py is untouched and its approval check does not read the trigger (run_launcher.py require_live_case_approval; trigger only stamps the Run), so forwarding trigger in routes_runs.py _run_queued is a stamp, not a gate. schedule_wiring.py real_gate only CALLS the merged credential_gate (dual-checked in t200b). The approval row it can mint is local to the project's file store, not a production write. The tick gate and the launcher gate are independent layers: the e2e showed the first refuses with zero trace, and test_run_launcher_approval.py covers the second. If Umesh wants the first reachability of the mint treated as a security trigger anyway, that is his call, not a defect found here.
FAILURES: none
CAPABILITY-COVERAGE: 6/6 rows reproduced (the builder's five plus my own TS5 row; the builder had no TS5 falsification)
LIVE-BROWSER: not-applicable (changed paths: ui/routes_runs.py, ui/run_queue.py, schema/run_queue.py, stages/*, cli_*; no route, template or rendered output)
ISSUES-WRITTEN: ISS-t200-schedule-wiring-1, ISS-t200-schedule-wiring-2, ISS-t200-schedule-wiring-3 (all low, none blocking)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
full-suite trigger: tests/golden/cli_commands.json (golden command listing) and the cli_subapps SUBAPPS registry changed; ui/run_queue.RunQueue.submit gained an optional kwarg. Not run here (L without security or prod-write); the 6c check owes the one full suite.

## Criteria (evidence is mine, from a git archive of 8b67fb04)
- TS6 (one launcher, origin stamped): MET. Real CLI tick with the launcher replaced by a recorder saw trigger=schedule, requested_by=owner, slot_key, run_id = entry id. The wiring imports no runner (transitive guard test, doctor clean). Falsified: drop slot_key forwarding -> test_a_scheduler_entry_becomes_a_run_stamped_schedule_with_its_slot red.
- HO23 (one entry per slot): MET. Same slot ticked twice and by two simultaneous processes -> 1 record, 1 claim, 1 entry. Falsified: submit `held = None` -> restart test red.
- TS4 (overlap, cross-process): MET. A server queue file with a running entry -> skipped_overlap, nothing enqueued, server file unchanged. Falsified: ignore persisted() -> red.
- TS3 (never silently dropped): MET for the wiring (since capped at the heartbeat). Falsified: drop the cap -> red. See ISS-1 for what that cap costs.
- TS7 (CLI): MET. Dry run claims nothing, writes no heartbeat, opens no queue; exit 2 on a blocked slot; JSON document on stdout. Falsified: dry_run=False -> red.
- TS5 (gate before the queue, zero trace): MET. No credentials -> blocked_no_credentials, no run dir, no queue file, exit 2. Falsified: allow-all real_gate -> test_cli_schedule blocked-exit test red.
- Diff scope (4c): additive. No deleted or renamed def, export, route, test or key (ui/run_queue.py submit was restructured with behaviour preserved, queue tests green); every changed file is in the manifest's What changed; test edits only widen expected sets (no weakened assertion, no skip/xfail). docs/MAP.md regenerated. Gates: ruff clean, doctor clean.

## Rulings on the manifest's owner questions
1. Cross-process queue: not a FAIL. The manifest states the cost plainly, and the contract (TS4/TS6) asks only that the scheduler goes through the queue and never starts anything itself. ISS-3 records the owner choice (a/b/c) and the fail-open on an unreadable queue file.
2. Dual check: no (ruling above).
3. "api" -> Trigger.CI: acceptable; nothing submits "api" today, and the [ASSUMPTION] tag stays.

## Notes
- Mutants beyond the floor: 0 (guidance only). My first isolated-copy run failed on a missing scripts/ import (my copy list, not a product defect) and was redone; not counted.
- Not claimed by this unit and not judged: TS1 routes and schedule.manage, HO24 refused, the schedule card, inbox/email, the persona walk (all HELD in the manifest, T-204 and T-201a).

Metrics: start=2026-10-12T06:59:42Z end=2026-10-12T07:23:30Z wall_min=24 agent_min=24 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=6 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1428 mutants=0 defects_unit=0 defects_6c=0
