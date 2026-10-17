# Checkpoint - t207-multirole-schema (checker, cycle 0)

Evidence identity: code a9d07602 (HEAD 722bf3df, bookkeeping only after), base 4df66032, worktree .venv python 3.11, uv.lock unchanged, checker claude-sonnet-subagent.
- `pytest tests/test_multi_role_schema.py` -> 63 passed (collected 63).
- related set (12 existing files + new) -> 225 passed, 1 skipped.
- own probe scratchpad/t207chk/probe_mp3.py on tests/golden/pre_g11_project.json (blob 5f7d233): byte-identical on base src and HEAD src.
- falsification copies scratchpad/t207chk/row1_MP1..row4_MPI3: green then red (see verdict).
- ruff clean; doctor 2 stale-generated only.
- full-suite trigger: conftest-import (for pre-push 6c); not run.
