# Checkpoint A - t178-failure-bundle-fb4-fb5 (coordinator A), cycle 0

Environment fingerprint: Windows 11, Python 3.11.15 (D:/autoTesting/.venv), pytest with `-p no:xdist`, `PYTHONPATH=<git archive copy>/src`.
Code identity: commit a7d3fa6c7b25f39c737edb8b8297c43636f1409d, tree 826cbdeeb9c71af39f1ef0e5277a1158bfe1f495. Dependency lock: uv.lock blob e9bfb8868a57dfc95ee37fc12243eb3efdc61c78; pyproject blob 3cd649dfb048d568b45f2299bc99b49204cc7818 (unchanged by the unit). Config/fixtures/conftest: unchanged by the unit except tests/eval_compiler_fixtures.py (helper `approved_store`).
Attribution: checker coordinator A, verdict qa/verdicts/t178-failure-bundle-fb4-fb5.a.md.

| check | command / scope | result |
|---|---|---|
| FB4+containment nodes | pytest tests/test_schema.py test_store.py test_pinned_regression.py test_failure_bundle.py | 75 passed |
| FB5 + callers | pytest tests/test_expand.py test_expand_cli.py test_eval_compiler.py test_cli_issues.py test_regression_proof.py | 78 passed |
| UI + queue | pytest tests/test_ui_learn.py test_ui_runs.py test_run_queue.py test_run_queue_resilience.py test_ui_runs_queue.py | 55 passed |
| lint | ruff check src tests scripts; autotester doctor | clean; clean |
| falsification | falsify-runner.py FB4, FB5, CONTAIN, QUEUE (separate copies) | all green before, red after on the named assertion |
| secrets | secrets-probes/*.py (fake secret, throwaway root) | see verdict; PROPOSED-ISSUE P1-P3 |
| browser | headless Chromium vs 127.0.0.1:8791, copy of a7d3fa6c, throwaway AUTOTESTER_ROOT | evidence dir browser-t178-...-checker-a |
| seam counts | git log per file + verdict scan | see verdict ruling |
| full suite | shard_suite --shards 4 | NOT RUN: lock busy 901 s, exit 3 (REMAINING) |

Resume point: run only the full suite on a7d3fa6c (`--shards 4`), check `test_env_example_documents_every_key_the_code_reads` on master if it is red, then convert the verdict. Every other row above keeps its result while a7d3fa6c and the files above are unchanged.
