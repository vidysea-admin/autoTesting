# Checkpoint t213-authz (coordinator A) - cycle 0, code b4fd754b, base cff3ffe6

- pytest over tests/test_oracle_tenant.py, test_oracle_privilege.py, test_authz_gate.py, test_authz_probe_schema.py, test_oracle_registry.py -> 67 passed. Identity: worktree .venv, synthetic AUTOTESTER_APPROVAL_KEY, code b4fd754b. Agent: checker-A. File: qa/evidence/t213-authz.a/pytest-affected.txt
- floor mutants MP18, MP19, MP20 (slice 3 to 4), A5: green-before in the copy, red-after on the named assertion. Runner: qa/evidence/t213-authz.a/mutate.py
- counterexamples: qa/evidence/t213-authz.a/probe_scope.py (scope escape reproduced; owner-401 silent clean reproduced; MPI1 scan clean)
- result: FAIL on MP20/A5 (scope)
