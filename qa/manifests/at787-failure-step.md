# Manifest - at787-failure-step

**Status:** ready-for-check
**Fix cycle:** 0
**Issues addressed:** AT-787

## What changed
- `schema/run.py`: `RawResult.failing_step` (optional int) records the step order the executor saw break.
- `stages/execute.py`: `_run_steps` returns the first unmet-assertion step order; ERRORED and BLOCKED_HITL results carry the raising step's order; `_result` takes `failing_step`.
- `stages/failure_bundle.py`: `_failing_step` prefers explicit arg, then `result.failing_step` (recorded), else the old max-evidence heuristic. Stage purity kept: reads only the RawResult artifact. `run_artifacts.py` is unchanged (it already passes the result).
- `schema/failure_bundle.py`: `BundleManifest.failing_step_source` = recorded | explicit | heuristic_fallback.

## Tests
`tests/test_failing_step_bundle.py` (new); regression: test_failure_bundle*, test_run_failure_artifacts, test_execute*.
