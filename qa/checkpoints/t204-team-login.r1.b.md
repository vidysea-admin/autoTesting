# Checkpoint t204-team-login r1 seat B (own side only)
Attribution: checker seat B coordinator, cycle 1, verdict qa/verdicts/t204-team-login.r1.b.md
Code: wave/t204-team-login 6ea9b688 (product df1b0d57); repair base aa6fec2e. Environment: Windows, worktree .venv python, pytest -p no:xdist -o addopts=. Lock/deps: uv.lock unchanged by the repair.

| check | command/scope | result |
|---|---|---|
| env-key attack | qa/evidence/t204-team-login-r1-B/envkey_attack.py, envkey_attack2.py | 0 unexpected exports; side findings P2, P4, P5 |
| AU27 attacks | au27_probe.py | all branches audited, no secret, injection-safe |
| AU20 matrix + repro | au20_probe.py, au20_d1_repro.py | D1 reproduced (FAIL) |
| falsification | 4 rows in git-archive copies | all red on the named assertion |
| affected tests | 22 files, one process each | 412 passed, 1 skipped, 0 failed |
