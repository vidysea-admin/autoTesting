# Checkpoint A - at929-proposal-scrub (cycle 0)
- pytest redaction+expand+expand_cli @ b5d83803: 52 passed. ruff clean. doctor clean.
- falsification C1 in copy outside worktree: green 4 passed -> red 3 failed (named asserts) .
- bypass repro of routes_learn.py:233 on HEAD b5d83803 archive copy: FAIL (secret stored raw).
Result: FAIL, 1 blocking finding.
