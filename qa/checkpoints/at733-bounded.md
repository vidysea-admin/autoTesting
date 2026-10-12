# Checkpoint: at733-bounded (cycle 0, PASS)
Original checker attribution: coordinator subagent, qa/verdicts/at733-bounded.md
Code hash: src/autotester/ui/run_execution.py blob 0f4c0c4, tests/test_ui_runs_serial_resilience.py blob 72bee8f (b07cc727)
Config/fixtures/conftest hashes: unchanged vs base 057b6dbb; lock: uv.lock unchanged; env: Windows 11, worktree .venv python, pytest -p no:xdist
- affected tests: tests/test_ui_runs_serial_resilience.py + test_ui_runs_serial_entry_order.py + test_ui_runs_serial_entry_screenshot_namespace.py, collected 30 -> 30 passed
- falsification RU5: copy of b07cc727, ignore_errors=True with no check -> 4 failed 4 passed (green before 8 passed)
- locked-file probe (real handle) -> OSError; exists-raises probe -> OSError; ruff -> clean; doctor on master 354bd31f archive -> stale-generated SNAPSHOT only
