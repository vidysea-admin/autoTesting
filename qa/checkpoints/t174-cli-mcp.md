# Checkpoint - t174-cli-mcp (coordinator A)

Evidence identity common to all rows: code SHA 742e9d8abe3ee527376e2305a04a9a8091b5c500 (product files identical to e5e7696f; 742e9d8a adds only the manifest), base 822dca2b, dependency lock = uv.lock at that SHA (mcp 2.3.0), environment = `git archive` copy on C: with `uv sync --frozen`, Python 3.11.15, Windows. Original checker: coordinator A (claude-sonnet-subagent), this file.

| Check | Command / scope | Collected | Result |
|---|---|---|---|
| CM1-CM5 test files | `pytest -p no:xdist -o addopts= tests/test_cli_mcp.py tests/test_cli_mcp_boundary.py -m "not harness"` | 69 | 69 passed |
| Affected set | `pytest ... tests/test_cli_*.py (minus the two above) tests/test_doctor.py tests/test_hosting_deploy.py tests/test_run_launcher.py tests/test_run_launcher_approval.py` | 208 | 208 passed (277 with the 69) |
| ruff / doctor / lock | `ruff check src tests scripts`; `autotester doctor`; `uv lock --check` | - | clean / clean / consistent |
| CLI end-to-end probe | real `autotester.exe` subprocess, 14 invocations (dry-run, refused, unknown project, secret-as-slug, traversal slug and run id, no runs, catalog, bad --output, extra arg) | - | as expected; held parser clause reproduced |
| MCP stdio probe | real stdio client: tools/list, dry-run, no-provider run, 5 hostile run_ids, secret-as-project, catalog | - | as expected, tree hash unchanged |
| Mutants (isolated copies, green before / red after) | M1 CM1, M2 CM2 stdout, M3 CM2 scrub, M4 catalog scrub, M5b/M5c CM3, M6 CM4 approval, M7 CM4 import, M8 CM5, M9 gate mapping | - | all red on the named assertion |
| Mutants that SURVIVED | M5 (dry run `mkdir`s an empty runs dir), M10 (ungraded case counted as PASS) | - | test gaps, product code correct (probe) |
| Full suite (one allowed, L security) | `shard_suite.py --shards 4` at SHA | - | NOT RUN: machine-wide suite lock held by PID 2844 (another repo) for >15 min on attempt 1 (BLOCKED after 902 s) |
