# Manifest - t199d-bug-wiring

**Unit:** T-199 gaps from the task-level check: (1) wire `process_run` into run completion, (2) TB12 and TB14. Internal tracker only (D-090): no live sheet write, no `SheetClient` in the run path.
**Branch / base:** wave/t199d-bug-wiring, master b2d42c9b.
Fix cycle: 1
Status: ready-for-check

## What changed
| Path | One job |
|---|---|
| `src/autotester/stages/bug_wiring.py` | `record_run_bugs(store, run_id)`: calls `bug_run.process_run` on the project's BugStore; idempotent per run (TB6); a fault is logged with the run id, returns None, never loses the saved run. |
| `src/autotester/stages/run_launcher.py` | `launch_run` calls `record_run_bugs` right after `store.save_run`. `launch_run` is the one launcher for the UI Run button and queue, the team Test press, the schedule tick and the CLI, so every graded-run path is covered once. File kept at 300 lines (two cosmetic compactions). |
| `src/autotester/schema/tracker_binding.py` | `TrackerBinding` (sheet, tab, columns, unmapped with candidates) and `SyncStatus` (ok/error, last_error, retry_at). |
| `src/autotester/stages/tracker_binding.py` | TB14: header-only synonym matching, per-project `projects/<slug>/tracker_binding.json`; two candidates or none = `unmapped`. |
| `src/autotester/stages/sheet_sync.py` | TB12: `try_sync` runs `write_confirmed_plan` (live still refused) and turns any exception into `sync_status=error` with scrubbed last error and retry time; BugStore untouched. |
| `src/autotester/ui/routes_tracker.py` | Tracker page shows sync status and scrubbed last error; removed a duplicate `_may_edit`. |
| `src/autotester/stages/tracker_export.py` | Docstring no longer names a project (TB14 grep). |
| `tests/test_bug_wiring.py`, `tests/test_sheet_sync_tb12_tb14.py` | Failing run creates a bug visible on the tracker page; re-run updates not duplicates; 2 evidenced passes fix, a later fail reopens; reprocess is a no-op; fault logged and run survives; TB12 outage then convergence; TB14 two layouts, per-project binding, unmapped, no project name in `tracker_*.py`. |

## Notes for the checker
- TB8 confirmation and TB9/TB13 remain export-time (D-090); `propose_binding` is proposal only, not a confirmed mapping.
- No sheet client is constructed anywhere in `src/`; `try_sync` takes one as a parameter (tests use the fake).
