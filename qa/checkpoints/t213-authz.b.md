# Checkpoint B - t213-authz (coordinator B, cycle 0)

Evidence identity (all at code SHA b4fd754b, worktree .worktrees/t213-authz, deps = worktree .venv, uv.lock unchanged):
- verify: `uv run pytest tests/test_oracle_tenant.py tests/test_oracle_privilege.py tests/test_authz_gate.py tests/test_authz_probe_schema.py tests/test_oracle_registry.py tests/test_leak_evidence.py` -> 76 passed, collected 76. checker B (this file).
- diff scope: `git diff --numstat cff3ffe6..b4fd754b` -> 9 files, 0 deletions. checker B.
- lint: ruff All checks passed; doctor 4 violations (2 stale-generated, 2 run-duplicate, known). checker B.
- falsification: 14 isolated copies (control 55 passed), tool qa/evidence/t213-authz.b/mutate_b.py, results mutants-run1.json / mutants-run2.json. checker B.
Result: PASS. Remaining: none.

# Checkpoint B - cycle 1 (repair check, code SHA 4ebd8676, manifest 30114a9a)
Evidence identity (worktree .venv, uv.lock unchanged):
- verify: `uv run pytest tests/test_oracle_tenant.py tests/test_oracle_privilege.py tests/test_authz_gate.py tests/test_authz_probe_schema.py tests/test_oracle_registry.py tests/test_leak_evidence.py` -> 81 passed. checker B.
- diff scope: `git diff --name-only cff3ffe6..4ebd8676` -> 9 declared files; repair diff b4fd754b..4ebd8676 read in full. checker B.
- lint: ruff All checks passed; doctor 4 violations (known). checker B.
- falsification: control 60 passed; 4 isolated copies all red on named tests; tool qa/evidence/t213-authz.b/mutate_b_c1.py, results mutants-c1.json. checker B.
Result: PASS. Remaining: none.
