# Checkpoint - bug-loop-replay-legacy (cycle 0)
- affected six-file pytest @ code afe6d4f5, env uv .venv: 89 passed (checker run, result PASS)
- ruff src tests scripts: pass; doctor: clean
- falsify C1: blr-c1 copy, bug_run.py@69ebfae7 -> red on count/last_seen; green copy 3 passed
- falsify C2: blr-c2 copy, bug_store.py@69ebfae7 -> red on BadEventFile; green copy 3 passed
