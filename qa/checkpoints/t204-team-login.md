# Checkpoint — t204-team-login, coordinator A, cycle 3, merge-reconcile 1
Head 17c1422d (code 997c842b), base 2344c045, repair base 37a1d211. Environment: Windows, worktree venv (python 3.11), argon2-cffi 25.1.0, archive copy on C: (PYTHONPATH=<copy>/src).

| check | scope | code hash | result | evidence |
|---|---|---|---|---|
| route surface walk | `tests/auth_harness`-style walk, 74 pairs | git tree 17c1422d | 0 unpoliced, 0 orphan rows, undeclared route 401 | qa/evidence/t204-team-login-r3-mr1-A/walk.py |
| zero-permission probe | 73 non-public pairs | 17c1422d | all 403, waiting 200 | probe2.py |
| F1 PUBLIC_RULE | surface au16 login + test_ui_auth_login.py | policy.py @17c1422d | 25 green -> 17 red | falsify_g1b/r1b.log |
| F2 routers | 3 au13/au14 tests | routers.py @17c1422d | 3 green -> 1 red | falsify_g2/r2.log |
| F3 cli_subapps | test_cli_subapp_hook.py | cli_subapps.py @17c1422d | 2 green -> 2 red | falsify_g3/r3.log |
| full suite | shard_suite 4 shards, `-o addopts=`, 5412 tests | tree 17c1422d (no lock change vs 997c842b) | 5384 passed, 20 skipped, 6 red alone (all red on master 2344c045 or runner artifact) | suite.log, suite-summary.json, baseline-reds-2344c045.txt |
| ruff / doctor | src tests scripts | 17c1422d | clean | verdict |
Attribution: coordinator A, claude-sonnet-subagent, file qa/verdicts/t204-team-login.r3-mr1.a.md.
