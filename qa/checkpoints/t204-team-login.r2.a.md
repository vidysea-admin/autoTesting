# Checkpoint - t204-team-login, coordinator A, cycle 2 (repair)

Attribution: checker coordinator A, claude-sonnet-subagent; verdict qa/verdicts/t204-team-login.r2.a.md; evidence qa/evidence/t204-team-login-r2-A/.
Environment: Windows 11 (WSL2 Ubuntu for bind spellings), tree venv D:/autoTesting/.worktrees/t204-team-login/.venv, Python 3.11.15, pytest 9.1.1. Code identity: head 27a3a0a9ac2a, product f78c196f, repair base 6ea9b688. Docker Compose v5.2.0 (config render only, no daemon).

| check | command and scope | code hashes | result |
|---|---|---|---|
| AU20 differential | in-process harness, real app via TestClient, 3854 cases (bind x port x lists x PUBLIC_ORIGIN); fuzz/harness.py | src/autotester/auth/config.py, ui/helpers.py at 27a3a0a9 | dims A and E: 0 disagreements; wildcard spellings / UVICORN_HOST='' / +port / IDN: see verdict P2-P5 |
| AU20 docker path | uv --directory <tree> run python docker/compose_path.py; compose values from docker compose config | docker/compose.prod.yml:20, config.py | no vars + wrong lists: STARTS, 403 all (FAIL); DOMAIN only: agrees in 5 of 5 |
| affected tests | 21 files, pytest -p no:xdist -o addopts= --rootdir <tree> | tests/test_ui_auth*.py, test_hosting_deploy.py, test_ui_origin_guard.py and 11 more | 459 collected, 458 passed, 1 failed (AT-920, not this unit's; does not list PUBLIC_ORIGIN) |
| falsification | git archive copies M1..M6, cwd = copy, PYTHONPATH = copy/src | config.py single hunks | M2, M3, M4, M5, M6 killed on named ids; M1 killed on sibling ids |
| full suite | shard_suite --shards 4 --ref 27a3a0a9ac2a | - | BLOCKED lock busy 901 s (holder pid 13816, D:\hei-sweep); not run; owed on retry |

Reuse note for the next check: AU18/AU19 and HO9 keep their recorded results while helpers.py, .env.example are untouched. Re-run AU20 (the compose default), the compose test, DEPLOY.md claim, and the affected set for the new repair diff; the differential harness is fuzz/harness.py.
