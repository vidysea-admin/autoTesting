# Checkpoint at889-login-session-race (cycle 0)
- 3 login test files -> 31 passed, head 05595c71, tests/test_explore_login_bypass.py blob a74b68a: PASS (checker run)
- ruff + doctor clean on 05595c71
- falsification C1, C2 vs base explore.py in copy: red on named assertions
- counterexample probe: FAIL evidence in qa/evidence/at889-login-session-race/probe-result.md

# Cycle 1 (checker repair check, head d655bb90, code head 97e918ae)
- 3 login test files (tests/test_explore_login_bypass.py blob e1a02648, test_explore_login_wall.py, test_explore_login_wall_bounds.py) -> 33 passed, 26.46s: PASS (checker run, uv run --no-sync pytest, worktree .venv, src hash = 97e918ae explore.py)
- ruff check src tests scripts -> All checks passed; autotester doctor -> clean (checker run)
- falsification C1 (copy chk889c1, explore.py := 0a88215b): 2 new tests green@97e918ae (2 passed), red@0a88215b on `COMPLETED is LOGIN_FAILED` (2 failed)
- repair diff 0a88215b..HEAD read in full; whole-unit diff 69ebfae7...HEAD --stat scanned
