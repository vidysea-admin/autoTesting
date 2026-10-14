# Task-level verdict r2 - T-200 scheduled auto-test (independent, code SHA 26e68661)

VERDICT: FAIL (not closed; the done_check file qa/verdicts/t-200-team-loop.md is deliberately NOT written; T-200 stays pending; no ledger row)

Method: own detached worktree of master, PYTHONPATH bound to it. Tests: 239 passed (test_schedule_*, test_cli_schedule, test_inbox_*). ruff clean. doctor clean (2 advisory D-069 items). done_check: exit 1 (file missing). No browsers run.
Email: deferred to production (D-092 item 1, team-schedule.md amendment 2026-10-13); not built or judged. Website project page, schedule history and inbox remain required.

| Row | Result |
|---|---|
| TS1 | PASS (t200c, t200-walk) |
| TS2 | PASS |
| TS3 | PASS |
| TS4 | GAP: skipped_overlap record carries blocking_entry_id (scheduler.py:166) but ui/schedule_view.py::_history renders only `detail`, so the history shows no reason or blocking entry id (contract: record visible on schedule history with the blocker's id) |
| TS5 | PASS (blocked/refused slots reach inbox, t200-ts5) |
| TS6 | PASS |
| TS7 | GAPS: (a) card shows only "stale"; SchedulerStatus.since is dropped (schedule_view.py::_status) though contract requires "scheduler stale since <time>" (only the unit test asserts h.since); (b) enqueue-raised slot is recorded FAILED (scheduler.py:169) but report_delivery._BLOCKED_SLOTS = blocked_no_credentials, refused only, so no inbox row; (c) tick queue is memory-only (routes_runs.tick_queue) so a private scheduled worker's failure/cause is not durable on the history (slot record stays `enqueued`); inbox relies on a DeliveryRecord, verify it covers worker death/interruption |

Also open, unwaived by D-088: run_queue.persisted_entries returns [] for an unreadable queue file, so the overlap check fails open. Dry-run preview (schedule_gate.refusal_for) does not check production approval or owner run permission, so it can predict would_fire where the real gate refuses.

Untracked qa/verdicts/t-200-team-loop.b.md (FAIL, static-only) was not trusted; its findings 2, 3, 4, 5 were re-verified in code above. Finding 1 only partly (DeliveryRecord path exists).

Fix needed: render blocking id/reason and stale-since time in the card; add FAILED to inbox rows; make unreadable queue refuse safely; add mutation tests; then recheck.
