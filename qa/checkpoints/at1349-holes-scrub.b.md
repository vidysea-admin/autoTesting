# Checkpoint B - at1349-holes-scrub (cycle 0, head 0f1c79e6)
Completed (verdict PASS, nothing remaining):
- C1: pytest tests/test_crawl_holes_scrub.py (3 passed); probe base vs head (leak True -> False) | code hashes: explore_summary.py/explore.py/explore_node.py at 0f1c79e6 | env: py venv .venv, offline fake site | agent: checker coordinator B, qa/verdicts/at1349-holes-scrub.b.md
- C2: 15-file regression set 172 passed; 12 extra caller files 119 passed; ruff clean; doctor clean
- Falsification: 3 copy-mutants in .work/tmp/b-mut (coverage raw, _finish call site, heartbeat call site); first two red, heartbeat survived (defensive)
