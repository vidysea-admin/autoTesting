# Verdict — at580-score-cli-diagnosable

**Date:** 2026-09-25 · **Head checked:** 1cd0ba9 (fix 00ad321, base master 19f4f9b) · **Cycle checked: 1** (manifest Fix cycle: 1 of 3) · **Issues addressed (claimed):** AT-580

```
VERDICT: PASS
SCOREBOARD: AT-580 expected clause met (the subprocess returncode is asserted with stderr and stdout in the message before json.loads; a 180 s timeout; a test proves a failing child is named, not hidden); core invariants hold
FAILURES: none
CAPABILITY-COVERAGE: 1/1 row reproduced (own-venv copy): the returncode assertion removed -> the new test fails with the bare JSONDecodeError, the exact AT-580 symptom
LIVE-BROWSER: not-applicable (changed paths: tests/test_score_cli.py only)
ISSUES-WRITTEN: none
EXECUTOR: maker orchestrator inline (checker: claude-opus-session, checker seat)
EXPLANATION: A starved or crashed score CLI now fails with its own exit code and stderr instead of an unexplained JSON parse error. As the manifest says, this makes the flake diagnosable; it doesn't remove whatever starves the child under load.
```

## What I re-ran

- `ruff` clean · `doctor` clean · `tests/test_score_cli.py` -> `10 passed` (copy).
- Row: removing the `assert result.returncode == 0, (...)` in `run_json` -> `1 failed, 9 passed`; the failure is `JSONDecodeError` in `test_a_failing_child_is_reported_with_its_stderr_not_as_a_json_error`.
- **Every non-browser test file** (copy): `1 failed, 1576 passed, 5 skipped`; the one failure is the `.git`-only `test_uploaded_recordings_are_gitignored`. Net: all green.
- Diff scope 19f4f9b..00ad321: 1 test file; removed lines are the 5 `json.loads(run(...).stdout)` sites replaced by `run_json(...)` and the old `subprocess.run` call line (now with `timeout=180`). No test deleted.
- Every `run_json` site is on the script's exit-0 path (all were green before and after). `--no-such-flag` exits 2 from argparse before any I/O.

## Status: PASS
