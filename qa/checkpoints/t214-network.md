# Checkpoint - t214-network (checker, cycle 0)
- 59 passed: `uv run --directory <worktree> pytest tests/test_network_oracles.py tests/test_oracle_registry.py`; code hashes: src/autotester/schema/request_budget.py, stages/oracle_api_error.py, stages/oracle_request_budget.py at d756b351; tests blobs test_network_oracles.py:dff1f54, network_oracle_fakes.py:e7806f8; no config/lock change; result PASS; checker claude-sonnet-subagent, qa/verdicts/t214-network.md.
- Falsify MP21: FIRST_ERROR_STATUS 400->500 -> red test_mp21_every_4xx_and_5xx_is_flagged (green in copy first).
- Falsify MP22: `<` -> `<=` at oracle_request_budget.py:131 -> red test_mp22_the_polling_boundary_is_the_declared_interval[1.0-False] (green in copy first).
