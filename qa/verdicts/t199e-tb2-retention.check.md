# Independent check - t199e-tb2-retention (head 803836bc), 2026-10-13

Verdict: PASS. Checker did not write the code; the maker also wrote the T-199 task verdict, so both were re-read here.

- TB2 re-read: "N = 2 consecutive passing verdicts, a stored configuration value with that default". N is the close-passes count, not
  record retention. The code is that: `BugLoopConfig.close_passes` (1..100, default 2, extra=forbid) in `<project>/bug_loop_config.json`;
  `BugStore` reads it (absent = 2); an explicit constructor value overrides for that object and is never written; `set_close_passes`
  stores it; N<1 refused. A corrupt config raises naming the path (fails loud, no silent default). `bug_wiring` and `routes_tracker` build
  `BugStore(project_dir)`, so the stored value governs real runs.
- Re-fold when N changes: events are never rewritten or deleted, and `fixed` is only ever derived from recorded evidenced PASS verdicts
  with no FAIL between (INCONCLUSIVE/BLOCKED/NOT_RUN never count), so a bug cannot become `fixed` without N such verdicts in its history.
  Lowering N can close a bug earlier and raising it can leave one open, both justified by the stored history and listed in its close
  lists (TB4). Nothing on the no-fire list is breached. `set_close_passes` has no UI caller, only an explicit call.
- T-199 task verdict (qa/verdicts/t-199-team-loop.md) covers TB1-TB7, TB10-TB12, TB14, TB15 and the G6 walks, with TB8, TB9, TB13 and
  HG-TB1 deferred (D-090); consistent with the sub-verdicts it cites. Accepted.
- Tests on the merged tree: bug_store, bug_loop, bug_run, bug_wiring, tracker_auth, tracker_page 188 passed; ruff and doctor clean.
- Ledger id: the branch's F-091 collided with master's (T-201); renumbered at merge.
