# Verdict: t200-advisories

Cycle checked: 1
Verdict: PASS

- (a) One lock definition: only core/file_lock.py uses msvcrt/flock; env_editor._env_lock delegates; env_editor tests pass.
- (b) Two-process append test spawns 2 real OS processes x 40 appends, asserts 80 intact lines; passes on Windows.
- (c) Sweep spares a run inside wall_clock_s + 30min (tests at 5h/7h and 20h/25h). Advisory: a bound above 24h is capped, so a run approved for more than 24h could be swept at 24h.
- (d) Rerun after rebase: schedule*, run_queue*, ui_env_editor 267 passed, 1 skipped; ruff clean; doctor clean; merge-tree vs master has no conflicts.
