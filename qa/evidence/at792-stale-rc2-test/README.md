Evidence for at792-stale-rc2-test (checker, 2026-10-11, head e346c6d1).
- branch-run.txt: `uv run --directory <worktree> pytest -p no:xdist -o addopts= tests/test_reconcile_schema.py` -> 19 passed.
  (A first attempt with `--project <worktree>` while the shell cwd was D:/autoTesting loaded the master tree's conftest and hit a missing-langgraph import; discarded and rerun from the worktree.)
- master-run.txt: same command on the master checkout 5da362ea -> 1 failed, 18 passed (assert None == 'type your email here', test line 125).
- falsify-green-before.txt / falsify-red-after.txt: two throwaway copies of `git archive e346c6d1` (outside the repo, deleted after): narration dropped at ingest.py:171, exit_screen dropped at ingest.py:181. The RC2 test is green before and red on the named assertion after, in each.
