# Checkpoint -- t171-goal-pin (cycle 0, single checker)

Env: win32, uv/pytest from worktree .venv, HEAD 6d1a826b, uv.lock 188681b3a300

| check | command + scope | code hashes | result | attribution |
|---|---|---|---|---|
| affected tests | pytest tests/test_goal_contract_registration.py tests/test_goal_done_checks.py tests/test_goal_done_check_shapes.py (10 collected) | goal.json aebab73f9670, registration test 678a754d5609 | 10 passed | checker t171-goal-pin c0 |
| T-171 real test | pytest tests/test_permission_coverage.py (15) | same | 15 passed | same |
| lint | ruff check src tests scripts | same | All checks passed | same |
| doctor | autotester doctor | same | 1 violation (docs/MAP.md stale, pre-existing) | same |
| full suite | uv run pytest (2208 collected incl. skips/xfail) | same | 1 failed (test_ui_runs_serial_entry_mix_live, pre-existing, ISS-t171-goal-pin-1), 2200 passed, 5 skipped, 14 xfailed, 1510s | same |
| falsification pin | copy: registration node, line 42 reverted | same | green 1 passed / red 1 failed / restored 1 passed | same |
| falsification cmd | copy: goal.json T-171 cmd reverted, nodes registration + done-check-file | same | green 2 passed / red 2 failed / restored 2 passed | same |
