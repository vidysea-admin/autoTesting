# Checkpoint A - at929-proposal-scrub (cycle 0)
- pytest redaction+expand+expand_cli @ b5d83803: 52 passed. ruff clean. doctor clean.
- falsification C1 in copy outside worktree: green 4 passed -> red 3 failed (named asserts) .
- bypass repro of routes_learn.py:233 on HEAD b5d83803 archive copy: FAIL (secret stored raw).
Result: FAIL, 1 blocking finding.

# Checkpoint A - cycle 1 (repair check @ 4addd97e, product 2cb9e414)
- pytest redaction+expand+expand_cli+ui_learn+ui_learn_guard: 68 passed. ruff clean. doctor clean.
- grep stage_case_proposals src: single caller expand.py:182 inside stage_scrubbed_proposals.
- falsification C1 in git-archive copies (scratchpad f1/f2): route hunk reverted -> green 2 passed then red on secret-in-file; scrub removed -> 5 failed.
Result: PASS.
