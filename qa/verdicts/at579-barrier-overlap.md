# Verdict — at579-barrier-overlap

**Date:** 2026-09-25 · **Head checked:** 1318a61 (fix 6d8737f, base master 4b35639) · **Cycle checked: 1** (manifest Fix cycle: 1 of 3) · **Issues addressed (claimed):** AT-579

```
VERDICT: PASS
SCOREBOARD: AT-579 expected clause met (the overlap is forced by threading.Barrier(2, timeout=10), keeping the peak == 2 assertion); core invariants hold
FAILURES: none
CAPABILITY-COVERAGE: 1/1 claimed row reproduced (forced serial -> red on the named assertion), plus the checker's own second falsification showing the `finally` is load-bearing
LIVE-BROWSER: not-applicable (changed paths: tests/test_ui_runs_parallel_trace.py only)
ISSUES-WRITTEN: AT-580 (low, unrelated flaky test found by the full-suite run)
EXECUTOR: maker orchestrator inline (checker: claude-opus-session, checker seat)
EXPLANATION: The test now proves real overlap instead of assuming it from a 50 ms sleep, and it still fails for a serial run. 8/8 back-to-back runs passed while the full suite ran alongside as load.
```

## What I re-ran

- `ruff` clean · `doctor` clean (copy).
- **Row (forced serial)**, own-venv copy, `routes_runs.py` `if plan.n > 1:` -> `if False and plan.n > 1:` (my own edit; the unit changes no src, so the natural falsification breaks the code the test guards): `1 passed` -> `1 failed`, `assert 1 == 2` (after the 10 s barrier timeout).
- **The `finally` is load-bearing** (the maker's note 2, reproduced): in the same forced-serial copy, moving the decrement out of `finally` makes the test PASS on a serial run (the timed-out first case never decrements, so the second reads 2). The shipped version, with the decrement inside `finally`, is required.
- **Flake resistance:** the named test 8/8 passed back to back in the worktree while the full suite ran concurrently as load.
- **Every non-browser test file** (copy): `2 failed, 1574 passed, 5 skipped`. Neither failure is caused by this unit.
  - `test_uploaded_recordings_are_gitignored` needs `.git`, which copies lack.
  - `test_score_cli.py::test_the_declared_bounds_are_honoured_not_ignored[--threshold-0.99]` got `JSONDecodeError` on an empty subprocess stdout under load; it passes 3/3 in the worktree. Filed as **AT-580** (low).
- Diff scope 4b35639..6d8737f: 1 test file; removed lines are the `time.sleep(0.05)`, the out-of-finally decrement and the now-unused `import time`.

## Status: PASS
