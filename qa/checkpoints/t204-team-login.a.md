# Checkpoint - t204-team-login seat A (cycle 0, head aa6fec2e)

Verdict: FAIL (qa/verdicts/t204-team-login.a.md). Resume 1 of 2 used. Full suite not run, owed on the repair cycle.
Environment: Windows, worktree venv D:/autoTesting/.worktrees/t204-team-login/.venv, uv.lock hash unchanged since base + 61 added lines; argon2-cffi 25.1.0.
Attribution: seat A coordinator with read-only sub-checkers; evidence in qa/evidence/t204-team-login-A/.

| check | command / scope | code identity | result |
|---|---|---|---|
| AU1-AU23, AU27 | pytest -p no:xdist -o addopts= -rA, 10 auth files (154 collected) | aa6fec2e worktree | 154 passed, counts match manifest |
| AU25 | tests/test_ui.py test_ui_healthz test_ui_error_pages test_ui_env_editor test_ui_project_intake | aa6fec2e | 55 passed, 1 skipped |
| advice sites | tests/test_cli_advice_resolves.py (own run 31 tests; node re-run by me) | aa6fec2e | 1 failed (auth/config.py 'auth bootstrap-admin'); master 9c9a91f3: passed |
| origin guard / permission coverage / credential approval / env loading | single files | aa6fec2e | passed |
| ruff, doctor, uv lock --check | worktree | aa6fec2e | clean, clean, Resolved 89 packages |
| falsification | 41 rows, isolated copies, autotester.__file__ printed | aa6fec2e | 36 red, 5 survivors (listed in verdict) |
| AU26 browser | Playwright headless, loopback 8791, scratch accounts | aa6fec2e | partial: disable/delete leg and tester/dev/lead personas not walked |
| AU20 own-origin repro | check_startup with hosted + unrelated allow-list | aa6fec2e | no raise |
Remaining for repair checker: failed criteria AU20, AU27, the advice-site red; AU26 disable/delete/persona leg; the one full suite (shard_suite.py --shards 4); AU24 owner-held.
