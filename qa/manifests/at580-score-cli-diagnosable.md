# Manifest — at580-score-cli-diagnosable
**Contract:** qa/contracts/core-invariants.md (tests fail for the named reason)
**Goal task:** none
**Date:** 2026-09-25
**Fix cycle:** 1 of max 3
**Dual check:** no
**Issues addressed:** AT-580 (low, open -> fixed)
**Executor:** claude-opus-5-5 (maker orchestrator, inline — test-only)
**Executor rationale:** a small test-helper change; RAM 3.1 GB below the build-slot ceiling

## What changed
- tests/test_score_cli.py — `run()` gains `timeout=180`; new `run_json(truth, root, *extra)` asserts `returncode == 0` with the child's stderr and stdout in the message, then `json.loads`. All 5 former `json.loads(run(...).stdout)` call sites (the partial/complete analysis tests, the no-analysis test, and both sides of `test_the_declared_bounds_are_honoured_not_ignored`) now use `run_json`. New test `test_a_failing_child_is_reported_with_its_stderr_not_as_a_json_error`. No source file changed.

## How to verify
- `uv run pytest tests/test_score_cli.py` -> all pass
- `uv run ruff check src tests scripts` -> clean · `uv run autotester doctor` -> clean

## Actual outputs (maker's run, 00ad321)
- `10 passed in 21.07s` · `All checks passed!` · `doctor: clean`
- Full non-browser suite: NOT RUN (test-only change to one file; RAM 3.1 GB). Declared gap. Note: the AT-580 symptom itself (a starved child under load) can only be reproduced by load; this unit makes it DIAGNOSABLE and bounded, it does not claim to remove the starvation.

## Capability coverage
| capability | check | falsifying edit | observed |
|---|---|---|---|
| a failing child surfaces as an AssertionError naming its exit code + stderr, not a JSONDecodeError | tests/test_score_cli.py::test_a_failing_child_is_reported_with_its_stderr_not_as_a_json_error | remove the `assert result.returncode == 0, (...)` block from `run_json` | throwaway copy outside the root, own `uv sync`'d .venv. Before: `1 passed in 1.44s`. After: `E json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` / `1 failed in 2.44s` — exactly the AT-580 symptom returns. Copy deleted after. |

## Live browser evidence
Not UI-touching — only tests/test_score_cli.py changed.

## Status: checked-PASS (qa/verdicts/at580-score-cli-diagnosable.md, Cycle checked: 1, c9ebe24)
