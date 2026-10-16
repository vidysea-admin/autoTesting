# Verdict - docker-entrypoint-behaviour-test

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** f2abf907eb67ac1c1b6bea58971aeadab11839d0
**Base:** 7409a486

## Evidence (independently produced, worktree .work/chk, .work/chkmut)
- Diff `7409a486..f2abf907`: 3 files only (manifest, new tests/test_container_entrypoint_behaviour.py, tests/test_container_supervision.py). No docker/, Dockerfile or src/ change.
- `pytest tests/test_container_supervision.py tests/test_container_entrypoint_behaviour.py` (PYTHONPATH=worktree src, repo .venv): rc 0, 14 passed, 1 skipped (non-exec python on NTFS, pytest.skip with reason), 77 s.
- `ruff check src tests scripts`: rc 0. `autotester doctor`: "doctor: clean" (advisory warnings only, pre-existing).
- Mutations in a full scratch copy (.work/chkmut, --noconftest, baseline green first, restored byte-identical to Dockerfile afterwards):
  - final `USER root` -> test_deploy_is_self_diagnosing_and_honours_cloud_run_port FAILS.
  - wrapper `exec /entrypoint.sh` line deleted -> static test AND test_diagnostics_wrapper_execs_entrypoint_and_propagates_rc FAIL.
  - entrypoint.sh `exit 126` -> `exit 1` -> test_preflight_fails_126_when_python_missing FAILS.
- The missing-python test always runs, runs the real script under bash with paths rewritten, and asserts rc 126 plus PREFLIGHT FAIL and uid= on stderr: meaningful. No xfail; bash absence uses skipif with a reason.

## Limits
- Non-executable-python case is skipped on NTFS (not exercised here); covered only on POSIX filesystems.
- Static wrapper check takes the last single-quoted printf line in the Dockerfile; adequate for the current layout.
- Checker usage: tokens unknown; active time well over 120 s target because pytest startup is slow on this loaded machine.
