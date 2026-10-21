# Checkpoint A - at1349-holes-scrub (cycle 0)

Final: verdict PASS written to qa/verdicts/at1349-holes-scrub.md. Remaining: none.

| Check | Command / scope | Code identity | Result |
|---|---|---|---|
| C1 tests | `.venv python -m pytest tests/test_crawl_holes_scrub.py` (3 tests) | product tree 1d3b9798 (HEAD 47e4b8ad adds only the manifest); tests/test_crawl_holes_scrub.py sha256 f7112c1d..; explore_summary.py sha256 3b6cdb0b.. | 3 passed |
| C2 regression | the 15 files of Tests[C2], 172 collected, no -x | same; pyproject and uv.lock unchanged vs base; Windows, .venv python in the worktree | 172 passed in 412 s |
| Lint | `ruff check src tests scripts` | 1d3b9798 | All checks passed |
| Falsification C1/C2 | copy D:/autoTesting/.work/tmp/at1349-A-mut1 (git archive 1d3b9798), PYTHONPATH to the copy | coverage unscrubbed -> 3 failed; _finish call-site reverted -> 1 failed; restored -> 3 passed | floor met |
| Probe | D:/autoTesting/.work/tmp/at1349-A-probe/probe.py (encoded secret, node_id planted) | 1d3b9798 | encoded forms masked; node_id raw (synthetic; hash-only in real runs) |

Attribution: coordinator A (this agent), no sub-checkers.
