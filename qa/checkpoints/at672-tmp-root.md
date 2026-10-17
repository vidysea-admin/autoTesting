# Checkpoint - at672-tmp-root (cycle 0, checker Mode A)
- tests/test_core.py + tests/test_ids.py via uv run pytest, code 6899f3df, conftest blob 88ec869, test_core blob 2728ae1, worktree .venv py3.11 -> 18 passed.
- sample of 8 other test files (conftest loads) -> 151 passed, 1 skipped.
- ruff src tests scripts -> clean; autotester doctor -> clean.
- falsification: base conftest fcedc9f4 red on named assertion, HEAD conftest green, in git-archive copy.
- prune probe: aged junction outside root not followed; outside files intact.
- Result: PASS.
