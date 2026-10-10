# Checkpoint — t136-bench-foundation cycle 0 (checker)
Code: HEAD 484353e6 (schema/bench.py, stages/bench.py, scripts/bench_trial.py, tests/test_bench.py). Lock: uv.lock not in diff. Env: win32, worktree .venv python.
- ruff src tests scripts -> All checks passed
- autotester doctor -> clean
- pytest tests/test_bench.py tests/test_regression_proof.py tests/test_core.py tests/test_schema_video.py tests/test_ledger.py -> 98 passed (scoped; full suite withheld by t125 gate)
- 15 falsification rows in isolated copies -> 15/15 green-before red-after
Attribution: claude-sonnet-subagent checker; verdict qa/verdicts/t136-bench-foundation.md
