# Checkpoint A r1 - t178-failure-bundle-fb4-fb5 (coordinator A), cycle 1

Environment: Windows 11, Python 3.11 (worktree .venv python), pytest `-p no:xdist`, `PYTHONPATH=<git archive copy>/src` for every copy run.
Code identity: branch head 297207ff (product c142f8f1, master 8791b76b merged at 2587a7b1); repair base a7d3fa6c (ancestor of HEAD, verified). pyproject/uv.lock untouched by the repair.
Attribution: checker coordinator A, verdict qa/verdicts/t178-failure-bundle-fb4-fb5.r1.a.md, evidence qa/evidence/t178-failure-bundle-fb4-fb5-r1-A/.

| check | command / scope | result |
|---|---|---|
| FB4 | pytest tests/test_schema.py test_store.py test_pinned_regression.py test_ui_runs.py (worktree @297207ff) | 60 passed |
| FB5 | pytest tests/test_expand.py test_expand_cli.py test_ui_learn.py test_eval_compiler.py | 61 passed |
| ADVICE | pytest tests/test_cli_advice_resolves.py | 32 passed |
| CONTAIN | pytest tests/test_failure_bundle.py (files untouched by the repair; cycle-0 result kept) | 23 passed |
| lint | ruff check src tests scripts; autotester doctor | clean; clean |
| falsify FB5 (moved code) | m1 skip review loop; m3 drop preflight; copies of 297207ff | green 11 passed before; red on the named assertions |
| falsify ADVICE | m4 delete routes_learn entry from EXPECTED_SITES | red `new: [('ui/routes_learn.py', 'expand')]` |
| differential | diff_cli_move.py through `autotester expand` on a7d3fa6c vs 297207ff | identical modulo proposal ids |
| full suite | shard_suite --repo D:/autoTesting --ref 297207ff --shards 4 -- -o addopts= | 3457 passed, 4 failed (all baseline), 19 skipped; collect proof ok (3480) |
