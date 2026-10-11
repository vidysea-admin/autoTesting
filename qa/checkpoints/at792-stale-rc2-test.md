# Checkpoint: at792-stale-rc2-test (cycle 0, checker A)

Head e346c6d1; true unit base f96b136c; master 5da362ea. uv.lock unchanged by the diff. Env: Windows, Python 3.11.15, pytest 9.1.1, uv.

- Diff scope: `git diff f96b136c..HEAD --stat` -> manifest + tests/test_reconcile_schema.py. Result: in scope.
- Branch run: `uv run --directory <worktree> pytest -p no:xdist -o addopts= tests/test_reconcile_schema.py`, 19 collected, test file as at HEAD. Result: 19 passed. File: qa/evidence/at792-stale-rc2-test/branch-run.txt
- Master run: same command at 5da362ea in D:/autoTesting, 19 collected. Result: 1 failed, 18 passed (AT-792 message). File: qa/evidence/at792-stale-rc2-test/master-run.txt
- Falsification: ingest.py:171 narration and ingest.py:181 exit_screen, each in a `git archive e346c6d1` copy, node `tests/test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen`. Result: green before, red after, both. Files: falsify-green-before.txt, falsify-red-after.txt
- Attribution: claude-sonnet-subagent checker A; verdict qa/verdicts/at792-stale-rc2-test.md
