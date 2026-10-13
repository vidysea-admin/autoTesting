# Manifest - t199e-tb2-retention

**Unit:** T-199 task-level gap: TB2 "a stored configuration value" (N kept with the project, t199a P6/G8). The contract text has no record-retention rule; "N" is the number of consecutive evidenced PASS verdicts that close a bug (default 2). It was only a constructor default.
**Branch / base:** wave/t199e-tb2-retention, master 208be7e0.
Fix cycle: 1
Status: checked-PASS

## What changed
| Path | One job |
|---|---|
| `src/autotester/schema/bug_run.py` | `BugLoopConfig(close_passes: 1..100, default 2)`, extra=forbid. |
| `src/autotester/store/bug_store.py` | `BugStore` reads N from `<project dir>/bug_loop_config.json` (absent = 2); explicit `close_passes=` overrides for that object only, never written; `set_close_passes(n)` stores it. Events are never pruned or deleted, so an open bug always keeps its full history. |
| `tests/test_bug_store.py` | stored N survives a new process; project A's N does not touch B; override not written; N=3 keeps 2 passes open, 3rd fixes; history intact; N<1 refused. |
| `docs/MAP.md` | regenerated. |

## Notes for the checker
- Changing N re-folds history (events are not rewritten), so a reported `fixed` can move; documented on `set_close_passes`, explicit call only. No contract line says otherwise.
- Tests run: test_bug_store, bug_loop, bug_run, bug_wiring, tracker_auth, tracker_page; ruff and doctor clean.
