# Checkpoint - schedule-purge-crash-safe (cycle 0, checker Mode A)
- code 238db25c (src d3c2e5f5), base 69ebfae7 = merge-base with master, worktree .venv py3.11.
- uv run pytest tests/test_schedule_marker.py -> 10 passed (110 s). tests/test_schedule_purge_crash.py -> 7 passed, 1 failed under 3-way load (child join 60 s timeout); that test alone rerun -> 1 passed (13 s).
- ruff src tests scripts -> All checks passed. autotester doctor -> clean.
- falsification (copy outside worktree, PYTHONPATH copy): test_a_purge_interrupted_by_systemexit_or_ctrl_c_... green (2 passed); `except BaseException` -> `except OSError` at schedule_store.py:238 -> red on the stage-dir/file list assertion (both cases); restored byte-identical.
- Result: PASS.
