# Task-level verdict r4 - T-200 scheduled auto-test (independent, master a172f38a)

VERDICT: PASS

Supersedes the untracked qa/manifests/t-200-team-loop.md and qa/verdicts/t-200-team-loop.b.md (another session; left untracked) and the r2 FAIL (t-200-team-loop.task-check.r2.md).

Method: own detached worktree of master, PYTHONPATH bound to it (autotester.__file__ verified inside the worktree), no uv, no browsers.
Tests: test_schedule*, test_inbox*, test_run_queue*, test_report*, test_cli_schedule*: 346 passed, 1 skipped. The earlier 8 test_schedule_tick guard failures and 3 ruff errors did not reproduce (polluted checkout). ruff clean. doctor clean (2 advisory D-069 items). done_check (file exists) satisfied by this file.

r2 gaps, re-verified in code on master:
- TS4: ui/schedule_view.py::_why renders "project busy: blocked by run <id>" in the history. PASS.
- TS7(a): card shows "scheduler stale since <time> UTC" (schedule_view.py:151). PASS.
- TS7(b)/(c): report_delivery._BLOCKED_SLOTS includes FAILED and INTERRUPTED; schedule_sweep amends open slots via append-only amend_record (t200-ts4-ts7 cycle 2 PASS). PASS.
- Unreadable queue fails closed; dry-run checks approval and owner rights (t200-ts4-ts7). PASS.
- TS5 inbox row for blocked/refused slots (t200-ts5 PASS). TS1-TS3, TS6 unchanged PASS.
Email half DEFERRED TO PRODUCTION (D-092 item 1); not judged.

Advisories (non-blocking): cross-process lock for slot-file appends; the 3h sweep threshold could mark a legitimate longer run interrupted; inbox row visible to any report.view holder, not owner only.
