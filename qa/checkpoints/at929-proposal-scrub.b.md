# Checkpoint b - at929-proposal-scrub (cycle 0)
- verify x4 (pytest redaction 27 passed; expand+cli 25 passed; ruff clean; doctor clean) · head 01797fdb · env: win32 py3.11 repo .venv · result green
- falsification C1 (scratch copy, `_scrub_proposals` -> return rows): 3 named nodes green then red · result as expected
- probe UI writer routes_learn.py:233 (TestClient, scratch copy): secret stored raw, 2/2 red -> FAIL C1
