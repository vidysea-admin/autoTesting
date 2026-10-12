# Checkpoint - t177-slice0-browser-seam - coordinator B - cycle 1 (head 0a4859a1)

Env: Windows 11, Playwright Chromium 151 (headless shell and headed chrome), uv venv on C: from uv.lock of 0a4859a1 (pyproject and uv.lock unchanged by the unit). Code: launch.py, session.py as `git archive 0a4859a1`. Attribution: coordinator B, verdict qa/verdicts/t177-slice0-browser-seam.r1.b.md.

| Check | Command / scope | Result |
|---|---|---|
| F1 real-browser matrix | `h1.py` (9 cases head, 6 base) + `h1b.py` drip | head clean, base leaks |
| happy path | `h2.py` head and base | identical, loopback only |
| _reaches_past_loopback | `h3.py`, `h3b.py` N=100 x2 | measured, see verdict |
| headed | `h4.py`, one attempt | started, close 13 s |
| affected tests | 5 files, `-p no:xdist -o addopts=`, 118 collected | 118 passed |
| lint | ruff check src tests scripts; autotester doctor | clean |
| falsification | 4 copies under scratchpad r1b2/fal | all green-before red-after |

Data: no data checks. Browser/live id: local servers on 127.0.0.1 only. Complete; no CONTINUE-NEEDED.
