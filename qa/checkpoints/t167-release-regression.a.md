# Checkpoint A — t167-release-regression (cycle 0)
Attribution: /checker coordinator A (claude-sonnet-subagent); verdict qa/verdicts/t167-release-regression.a.md. Environment: Windows, worktree .venv python (langgraph 1.2.14, checkpoint 4.2.0), `git archive 667a0c64` copies under the scratchpad.
Code hashes (blob, 667a0c64): orchestrate.py 8040c74236 · orchestrate_gate.py fd08a71b46 · orchestrate_checkpoint.py 837c0f81ad · release.py 5223d2a3b8 · release_compare.py 17507f9c5f · schema/release.py 023bbeaf14 · cli_release.py 7075508628 · tests/test_regression_trigger.py b6015c41b2 · tests/test_cli_release.py c16ea56525.
Config/lock: pyproject.toml 72a83bd9e4 · uv.lock 4882ef560a. No conftest/fixture change in the diff.

| check | command / scope | result |
|---|---|---|
| RR1-RR6 + CLI | pytest tests/test_regression_trigger.py tests/test_cli_release.py (22 collected) | 22 passed |
| regression set | test_orchestrate, _runners, cli_orchestrate, cli_orchestrate_resume, schema, store, consent, parallel_run_approval | 112 passed |
| falsification rr1,rr2a,rr3,rr4,rr4b,rr5,rr6 | single-hunk edits, scripts in qa/evidence/t167-release-regression-a/mutate.py | each red for the named reason |
| gate order rr2b,rr2c | preflight after _compile / after check_lineage | tests green; probe p1 green (equivalent) |
| gate order rr2d | preflight just before invoke | red (forged scope test) |
| probes p1-p6 | qa/evidence/t167-release-regression-a/test_probe_t167.py | 6 passed in m-g, m-rr2b, m-rr2c |
| doctor / ruff / uv lock --check --offline | worktree venv | clean / clean / resolves unchanged |
| persona walk | release manager, CLI | persona-walk-release-manager.md |
| full suite | shard_suite --shards 1 | NOT RUN by maker instruction; stopped my own tree; owed on the later sha |
