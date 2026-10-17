# Checkpoint - at335-tolerance-scope (cycle 0, PASS)
- cmd: uv run pytest tests/test_explore_return_determinism.py tests/test_explore_error_causes.py | code hash explore_return.py@e865e298, tests blob test_explore_return_determinism.py:f2179fe | result 12 passed | attribution: checker claude-sonnet-subagent, qa/verdicts/at335-tolerance-scope.md
- cmd: uv run pytest tests/test_explore_modal.py tests/test_explore_replay.py tests/test_explore_node_recovery.py tests/test_explore_traversal.py | head e865e298 | 28 passed
- cmd: ruff check src tests scripts / autotester doctor | head e865e298 | clean
- falsification C1: git apply -R of src diff in scratchpad copy | green 2 passed -> red 1 failed on "polled 3.3s on a rung that cannot recover" -> restored not needed (copy)
