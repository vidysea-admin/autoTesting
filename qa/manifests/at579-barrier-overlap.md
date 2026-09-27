# Manifest — at579-barrier-overlap
**Contract:** qa/contracts/parallel-run.md (PR2 — cases actually run concurrently when N > 1)
**Goal task:** none
**Date:** 2026-09-25
**Fix cycle:** 1 of max 3
**Dual check:** no
**Issues addressed:** AT-579 (low, open -> fixed)
**Executor:** claude-opus-5-5 (maker orchestrator, inline — one test function)
**Executor rationale:** a 12-line test-only change; RAM (3.0 GB) below the build-slot ceiling

## What changed
- tests/test_ui_runs_parallel_trace.py::test_with_max_parallel_2_two_cases_run_concurrently — the fake case body's `time.sleep(0.05)` is replaced by `threading.Barrier(2, timeout=10).wait()` inside try/finally; the decrement of the in-flight counter moved into the `finally`. The now-unused `import time` is removed. No source file changed.
  - Why a Barrier: it releases only when BOTH cases are in flight at once, so a loaded host can no longer make a real fan-out look serial (the sleep could — AT-579), and a serial run can no longer pass.
  - Why the finally matters (found while building the capability row): without it, a serial run's first case times out on the barrier, raises before decrementing, and the second case then reads 2 — the test PASSED with fan-out disabled. With the finally it goes red.

## How to verify (commands + expected)
- `uv run pytest tests/test_ui_runs_parallel_trace.py` -> 4 passed (repeat — no timing dependence)
- `uv run pytest tests/test_ui_runs_parallel_crash_recovery.py tests/test_ui_runs.py tests/test_ui_runs_serial_resilience.py tests/test_parallel_run.py` -> all pass
- `uv run ruff check src tests scripts` -> clean · `uv run autotester doctor` -> clean

## Actual outputs (maker's run, commit 6d8737f)
- test_ui_runs_parallel_trace.py x3: `4 passed, 1 warning in 0.96s` / `4 passed … 0.96s` / `4 passed … 1.13s`
- related run files: `21 passed, 1 warning in 3.52s`
- `All checks passed!` · `doctor: clean`
- Full non-browser suite: NOT RUN — test-only change to one function; RAM 3.0 GB. Declared gap.

## Capability coverage
| capability | check | falsifying edit | observed |
|---|---|---|---|
| the test proves real overlap: it fails when the live route runs the cases serially | test_ui_runs_parallel_trace.py::test_with_max_parallel_2_two_cases_run_concurrently | src/autotester/ui/routes_runs.py:79 `if plan.n > 1:` -> `if False and plan.n > 1:` (forces the serial path; the test fakes the plan, so the plan itself is not the seam) | Throwaway copy outside the root with its own `uv sync`'d .venv. Green before: `1 passed, 1 warning in 0.69s`. After: `E       assert 1 == 2` / `1 failed, 1 warning in 11.84s`. Reverted (copy's routes_runs.py byte-identical to the worktree): `1 passed, 1 warning in 0.53s`. |

Note: the first attempt (forcing `ParallelPlan.n = 1` in stages/parallel_run.py) SURVIVED — the test monkeypatches plan_parallel_run, so that edit never reaches the route. And the first barrier version (decrement outside finally) SURVIVED the route edit (see above). Both were fixed/re-aimed before this table was written.

## Live browser evidence
Not UI-touching — only tests/test_ui_runs_parallel_trace.py changed (no src/ file).

## Status: checked-PASS (qa/verdicts/at579-barrier-overlap.md, Cycle checked: 1, 092d5ef)
