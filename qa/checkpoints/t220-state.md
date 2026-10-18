# Checkpoint - t220-state, cycle 0
Verdict: qa/verdicts/t220-state.md (PASS). Head 31cbde82 (manifest commit b9a3f34a), base cff3ffe6. Attribution: checker claude-sonnet-subagent (this file's author).

Environment: Windows 11, worktree uv env; falsification copy used PYTHONPATH to the git-archive copy and `autotester.__file__` pointed into the copy. Lock: uv.lock unchanged by the diff (5 new files only).

| Check | Command and scope | Code hashes | Result |
|---|---|---|---|
| Affected tests | `uv run --directory <worktree> pytest tests/test_state_probe_schema.py tests/test_oracle_state_after.py tests/test_oracle_registry.py` (44 collected) | tree 31cbde82 | 44 passed |
| Lint | `ruff check src tests scripts` | tree 31cbde82 | clean |
| Design | `autotester doctor` | tree 31cbde82 and base cff3ffe6 | 2 stale-generated violations on both (pre-existing) |
| MPI3 | `git diff --name-only cff3ffe6..31cbde82` | n/a | 5 files, no schema/multi_role_enums.py |
| Falsification | 2 mutants of oracle_state_after.py in a copy (persistence branch off; actor-only readers) | file at 31cbde82 | 13 green before, 5 red each, 13 green restored |
