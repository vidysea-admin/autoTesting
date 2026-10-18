# Checkpoint - t219-neginput (cycle 0, PASS)
- cmd: uv run --directory <worktree> pytest tests/test_negative_input_oracle.py | head bc6379e8 (code 62eba1e4), tests blob test_negative_input_oracle.py:97b5983, negative_input_fakes.py:e7c4aa1 | 15 passed (0.28 s)
- cmd: uv run ruff check src tests scripts | head bc6379e8 | All checks passed
- cmd: uv run autotester doctor | head bc6379e8 | 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md), none from the new files
- cmd: git diff --name-only cff3ffe6..HEAD | 5 unit files + the manifest; schema/multi_role_enums.py, stages/expand.py, schema/enums.py absent; 768 insertions, 0 deletions
- falsification MP32: scratchpad copy t219-fals (git archive HEAD src + 2 test files, PYTHONPATH on the copy, --noconftest) | green 15 passed -> `[:1]` on the per-role loop (oracle_negative_input.py:213) -> test_mp32_every_cell_of_the_rule_matrix_is_asserted_for_both_roles red on `assert 10 == 20`; full file 7 failed / 8 passed; worktree untouched
