# Checkpoint — at1381-fp-coverage (cycle 0, head 8f23e561)
| check | command / scope | code hash | result |
|---|---|---|---|
| affected | uv run pytest tests/test_bench_marks.py tests/test_acceptance_comparison.py tests/test_ui_bench_inputs.py tests/test_bench_from_run.py tests/test_crawl_findings.py tests/test_generic_acceptance.py | head 8f23e561 (code 92421187) | 80 passed |
| lint | uv run ruff check src tests scripts | head 8f23e561 | All checks passed |
| falsify C1 | schema/bench.py adjudicated_findings=reported, copy, tests/test_bench_marks.py | 92421187 | 5 red, 16 green pristine |
| falsify C2 label | script label="" | 92421187 | 2 red |
| falsify C2 exit | script if False and args.claim | 92421187 | 2 red |
| extra | acceptance.py fp_rate_provisional False | 92421187 | 3 red |
Attribution: checker-at1381 (this file). Lock/dependency identity: uv.lock at head; env win32 py venv of the bound tree.
