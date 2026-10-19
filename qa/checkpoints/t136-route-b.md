# Checkpoint - t136-route-b, cycle 0
Verdict: qa/verdicts/t136-route-b.md (PASS). Head 8f2f608b (code fcb97361), base 4ce91ea8. Attribution: checker claude-sonnet-subagent (this file's author).
Environment: Windows 11, worktree uv env (.venv); falsification copies used PYTHONPATH=<copy>/src with the worktree interpreter, autotester.__file__ confirmed inside each copy. uv.lock unchanged by the diff.

| Check | Command and scope | Code hashes | Result |
|---|---|---|---|
| Affected | `uv run pytest tests/test_crawl_findings.py tests/test_bench_from_run.py tests/test_acceptance_comparison.py tests/test_bench.py -p no:xdist -o addopts=` (66) | tree 8f2f608b | 66 passed |
| Consumers | same flags on test_agent_comparison, test_ceo_benchmark, test_generic_acceptance, test_review_recall, test_review_recall_auto (41) | tree 8f2f608b | 41 passed |
| Lint / design | `ruff check src tests scripts`; `autotester doctor` | tree 8f2f608b | clean / clean |
| Real data copy | bench_from_run.py --crawl all + check_acceptance_comparison.py on a scratchpad copy | run-01M58F744J7R3CB99CMH9S7FQ3, 13 crawls | 14 findings, exit 0, 0 missing evidence paths |
| Falsification | 4 single-hunk edits in copies f1,f2a,f2b,f3 (see verdict) | files at 8f2f608b | 1 green before, 1 red after each |
