# Checkpoint - t215-consist (cycle 0)
- pytest tests/test_oracle_consistency.py tests/test_oracle_answer_key.py tests/test_oracle_registry.py | scope: 3 files, 85 collected | code: src/autotester/{schema/entity_reading,schema/answer_key,stages/oracle_consistency,stages/oracle_answer_key}.py @41847254 | tests blobs fb2e4da, a1aae17 | env: .venv python in the worktree, uv | result: 85 passed | checker: claude-sonnet-subagent, qa/verdicts/t215-consist.md
- falsify MP23: oracle_consistency.py `< 2` -> `< 3` in a copy: green 1 passed -> red (6 failed in file) | MP24: oracle_answer_key.py `==` -> `<=` : green 38 passed -> red (4 failed)
- ruff check src tests scripts: All checks passed | doctor: 2 stale-generated only
