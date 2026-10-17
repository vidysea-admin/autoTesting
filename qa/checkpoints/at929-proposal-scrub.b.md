# Checkpoint b - at929-proposal-scrub (cycle 0)
- verify x4 (pytest redaction 27 passed; expand+cli 25 passed; ruff clean; doctor clean) · head 01797fdb · env: win32 py3.11 repo .venv · result green
- falsification C1 (scratch copy, `_scrub_proposals` -> return rows): 3 named nodes green then red · result as expected
- probe UI writer routes_learn.py:233 (TestClient, scratch copy): secret stored raw, 2/2 red -> FAIL C1

# Checkpoint b - at929-proposal-scrub (cycle 1)
- pytest 6 expand/ui files 99 passed; proposal_review_ui+vendor_echo 9 passed; ruff clean; doctor clean · head 4addd97e (code 2cb9e414) · env: win32 py3.11 worktree .venv · green
- falsification C1 repaired path (copy outside worktree, route reverted / stage unscrubbed): green 2 passed then red 2 failed (route) and 5 failed (stage unscrubbed) · as expected
- caller grep stage_case_proposals: only expand.py:182 via stage_scrubbed_proposals (callers expand.py:189, routes_learn.py:233) · verdict PASS
