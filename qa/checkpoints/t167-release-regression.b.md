# Checkpoint B - t167-release-regression (coordinator B), cycle 0
Attribution: checker coordinator B (claude-sonnet-subagent) -> qa/verdicts/t167-release-regression.b.md. Result: FAIL (1 finding, RR2/security).
Environment: Windows 11, venv from `uv sync` in a git-archive copy of 667a0c64, langgraph 1.2.14, no model call. Blob hashes at 667a0c64: uv.lock 4882ef56, pyproject.toml 72a83bd9, orchestrate_gate.py fd08a71b, release.py 5223d2a3, release_compare.py 17507f9c, tests/test_regression_trigger.py b6015c41.

| check | command / scope | collected | result |
|---|---|---|---|
| RR1-RR6 + OR | pytest -p no:xdist tests/test_regression_trigger.py tests/test_cli_release.py tests/test_orchestrate.py | 29 | 29 passed |
| RR5 | grep -n langgraph pyproject.toml; autotester doctor; ruff check src tests scripts | - | line 17; doctor clean; ruff clean |
| regression set | pytest tests/test_orchestrate_runners.py tests/test_cli_orchestrate.py tests/test_cli_orchestrate_resume.py tests/test_schema.py tests/test_store.py tests/test_consent.py tests/test_parallel_run_approval.py | 105 | 105 passed |
| falsify RR1..RR6 | copies rr1..rr6, named node, green in a pristine copy first | 6 | all red on assertion |
| order mutants | m7 after _compile, m8 before save_release_scope, m9 after save | 3 | m7/m8 green (equivalent), m9 red |
| attacks | qa/evidence/t167-release-regression-b/attacks.py | - | A1b BREACH, rest held |

Full suite: not run by B (A owns it). full-suite trigger for 6c: dependency manifest (pyproject.toml, uv.lock).
