# Checkpoint - fix6c-r4-routeword coordinator B, cycle 0 (complete)
Head 3045e909 / base 58e13d6b. All checks done, verdict PASS at qa/verdicts/fix6c-r4-routeword.b.md.
- affected set: 15 test files, 376 passed (qa/evidence/fix6c-r4-routeword.b/affected-run.txt); command `uv run --directory <wt> pytest <15 files>`; code hashes = git tree of 3045e909; deps = uv.lock at 3045e909; env = Windows, Tesseract present at WINDOWS_TESSERACT.
- F1 mutant (11 words removed): 39 failed. F2 base tests vs HEAD src: 2 failed (named). F3 mutant (names added): 4 failed.
- probes: qa/evidence/fix6c-r4-routeword.b/probe.py. ruff clean, doctor clean.
