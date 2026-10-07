# Checkpoint — at758-759-security (coordinator A)

Bound: D:/autoTesting/.worktrees/at758-759-security, branch wave/at758-759-security, tip b9ce7983, base af8f3218. Cycle 0. Policy-Version: proportional-verification/2026-10-06.6.

## Completed checks (evidence identity)
Code hashes (git hash-object): ui/helpers.py 1cee1c72, stages/explore_consent.py 2de6550f, tests/conftest.py 3b174caf. uv.lock e9bfb886. Env: Windows 11, CPython 3.11.15, worktree .venv (uv sync: 80 packages checked).

1. `uv run ruff check src tests scripts` -> All checks passed. PASS.
2. `uv run autotester doctor` -> doctor: clean. PASS.
3. Line counts: helpers.py 292, explore_consent.py 133, app.py 300 (untouched), conftest.py 152, test_ui_origin_guard.py 209, test_credential_run_approval.py 300. Longest changed-file functions: helpers.py 36, explore_consent.py 32. PASS.
4. Host allow-list probes, `_host_allowed` called directly under the worktree src (about 60 inputs, with and without env lists). No bypass found.
5. Real uvicorn (127.0.0.1:18758, throwaway AUTOTESTER_ROOT with a saved credential; PID found by port and stopped), 24 raw-socket requests. No bypass found.
6. Falsification, one single-hunk edit per throwaway copy (copy confirmed real: autotester.__file__ resolved into the copy; green before in the copy, red after). Six rows, all red as expected. The worktree was never edited.
7. Isolated runs: test_flake_probe_real_process 2 passed; test_mc_sessionstart_loop_status 9 passed.

## Incomplete (mandatory) — Remaining
- ONE COMPLETE full suite run. The single run started 16:19:23 and died silently at 56% (1422 of 2541 collected tests) at 17:08:11, exit=1, no summary line, after about 49 min on a loaded machine (another coordinator was running). Four F at positions 525 (tests/test_crawl_inventory_live.py), 1027 (tests/test_flake_probe_real_process.py), 1301 and 1302 (tests/test_mc_sessionstart_loop_status.py).
  - test_crawl_inventory_live fails and then HANGS on this branch and on base af8f3218 alike (both runs ended by `timeout`), so it is pre-existing and not caused by this unit.
  - The other three passed when run alone, so they look load-related; unconfirmed in a full run.
- Items 1-7 need no re-run while the code hashes above are unchanged.
