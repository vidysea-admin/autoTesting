# Checkpoint B - t174-cli-mcp (cycle 0)

Environment fingerprint: Windows 11, CPython 3.11.15, pytest 9.1.1, mcp 2.3.0 (uv sync --frozen), copy C:/Users/Lenovo/AppData/Local/Temp/t174b-205110586.
Code identity: commit 742e9d8abe3ee527376e2305a04a9a8091b5c500, tree 401e532e076ae5f755e6a1761775798e6ad1228f; uv.lock blob d2e758db03e1b2e53dd7c5bd8b70ca2e22462801; pyproject.toml blob f61263b1dae75d01e5f127aac80f8e33679009a2. The unit changes no conftest or fixture file except tests/cli_walk.py (+3).
Attribution: coordinator B (claude-sonnet-subagent), verdict qa/verdicts/t174-cli-mcp.b.md.

| Check | Command / scope | Result |
|---|---|---|
| CM1 | pytest tests/test_cli_mcp.py -k "every_code or each_code or timeout or help_documents or doctors_own" | 10 passed |
| CM2 | pytest tests/test_cli_mcp.py tests/test_cli_mcp_boundary.py -k "json_stdout or printed_human or planted_secret or text_output or report_show or catalog_json or machine_error or unreadable_masking or text_catalog or credential_matching or unsafe_slug or unsafe_run_id" | 31 passed |
| CM3 | pytest tests/test_cli_mcp.py -k dry_run | 3 passed |
| CM4 | pytest tests/test_cli_mcp.py tests/test_cli_mcp_boundary.py -k "exactly_three or run_tool or server_calls or only_ever_started or attributed or sdk or rpc" | 23 passed |
| CM5 | pytest tests/test_cli_mcp.py -k "stdio or declared_dependency" | 2 passed |
| affected set | tests/test_cli_*.py test_doctor test_hosting_deploy test_run_launcher test_run_launcher_approval | 277 passed |
| ruff / doctor | ruff check src tests scripts; autotester doctor | clean / clean |
| own probes | tests/test_probe_b.py (throwaway copy only, not committed) and a stdio child script | 33 passed; stdio probe as expected |
| falsification | 10 edits, one fresh archive copy each | see verdict |
| diff scope 4c | git diff 822dca2b...742e9d8a | 1 removed line (import), no unlisted file |
| full suite | shard_suite --shards 4 --ref 742e9d8a | NOT RUN: lock held by PID 2844, 3 waits x 900 s, exit 3 |

Reuse rule: every row above except the full suite is reusable at the same code identity.
