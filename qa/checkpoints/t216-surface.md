# Checkpoint t216-surface (cycle 0, checker)
Env: win32, worktree .venv python, base cff3ffe6, code d601de49 (HEAD 2ffefb6a = manifest only), no lock file hashed.
- pytest tests/test_oracle_copy_lint.py tests/test_oracle_responsive.py tests/test_oracle_registry.py -> 41 passed (1.05 s). Scope: 3 files, 41 collected.
- ruff check src tests scripts -> All checks passed. doctor -> 3 violations (drift-filename oracle_copy_lint.py, stale-generated MAP/SNAPSHOT).
- Falsify MP25 (copy cp1 from git archive d601de49): test_every_cell_of_the_rule_matrix_is_reported green -> `key != shown` => `False` -> red (missing tz-display cells).
- Falsify MP26 (copy cp2): test_overflow_at_375_is_a_finding_with_a_masked_screenshot green -> `return False, off` -> red (assert 0 == 1).
- Probes: scratchpad probe216.py / probe216b.py (read-only against the bound tree).
