# Checkpoint: t204-team-login cycle 2, coordinator B (verdict qa/verdicts/t204-team-login.r2.b.md)

Head 27a3a0a9, product f78c196f, repair base 6ea9b688. Tree D:/autoTesting/.worktrees/check-t204-r2-b. Python 3.11.15, pytest 9.1.1. uv.lock unchanged by the repair. Windows 11, LAN address 192.168.1.4.

| check | command + scope | code | result |
|---|---|---|---|
| affected tests | `uv run pytest -p no:xdist -o addopts= <10 files>` from cwd = tree, 288 collected | config.py, test_ui_auth_own_origin.py, test_ui_auth_surface.py, auth_harness.py, test_hosting_deploy.py at 27a3a0a9 | 287 passed, 1 failed (AT-920, schedule keys only) |
| real-server table | qa/evidence/t204-team-login-r2-B/drv.py, 78 rows, uvicorn on ports 18500-18577 | same | all rows meet expectation except w35-w37 (AU20 FAIL) |
| falsification A | own_origin tests in a copy, Origin half dropped | mutated config.py copy | 68 passed, then 4 failed |
| falsification B | own_origin tests in a copy, required=True to False | mutated config.py copy | 68 passed, then 2 failed |
| compose render | `docker compose config` on a scratch copy without env_file | docker/compose.prod.yml:20 | unset gives https://localhost; the fix form renders an empty string |
| doctor / ruff | in tree via `uv --directory` | | ruff clean; doctor 2 dangling D-082 citations (branch lacks D-082) |

Attribution: claude-sonnet-subagent, coordinator B. Result: FAIL (AU20).
