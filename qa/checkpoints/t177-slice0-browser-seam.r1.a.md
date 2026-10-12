# Checkpoint - t177-slice0-browser-seam r1 A (cycle 1). Evidence identities (all on 0a4859a1, copy on C:)

Code: launch.py blob 22d999a14f53, session.py blob 431ea9da20eb, test_browser_session_cdp.py blob 07ab5898779f; uv.lock sha256 de23568d86e1246c; env: Windows 11, venv in the copy, Chromium headless 151 (machine-wide Playwright); no deploy or data id.
Attribution: repair checker A, qa/verdicts/t177-slice0-browser-seam.r1.a.md

1. pytest cdp_live + navigation_secrets + browser + settle + cdp (-o addopts= -p no:cacheprovider), 118 collected, passed.
2. ruff check src tests scripts clean; autotester doctor clean (clean archive copy; an earlier copy folder had stray files and was discarded).
3. Hostile loopback listener probes (hostile.py, hostile2.py): F1a NOT met (drip hang, RecursionError).
4. Live headless probes (live.py, livedrip.py): F1b met; drip hang with a real browser open reproduced.
5. loop.py: a timeout hides a full-backlog wildcard listener.
6. falsify.py: 5 repaired-item falsifications green / red / restored.

Result: FAIL (F1a). Full suite owed, not run (no lock taken).
