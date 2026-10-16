# Manifest - docker-entrypoint-behaviour-test

**Status:** checked-PASS
**Fix cycle:** 0
**Follow-up of:** qa/verdicts/docker-deploy-hardening.md (advisory 5), qa/verdicts/dockerfile-merge-fix.md

## What changed
- New `tests/test_container_entrypoint_behaviour.py` (test-only; docker/ and Dockerfile untouched).
- Runs the real `docker/entrypoint.sh` with bash after a fixture rewrites only the hardcoded paths (`/opt/venv`, `/opt/uv-python`, `/app/docker`, `/tmp/.X`) to tmp_path; python is a stub, so no service starts.
  - missing python -> rc 126, stderr has `PREFLIGHT FAIL` and `uid=`.
  - non-executable python stub -> same (skipped with a reason if the filesystem reports a 644 file as executable; on this NTFS worktree it skips).
  - executable stub -> rc 0; reported port is `${PORT}` when set (9123) and 8000 when unset, in both the log line and the `tcp:` supervisor arg.
- Extracts the `/startup-diagnostics.sh` body from the Dockerfile `printf` block (the Dockerfile has no heredoc since 7409a486), rewrites its paths, stubs `namei`, and checks it reaches and execs `/entrypoint.sh` and propagates that script's rc 5. Run with CMD `bash -c "echo hi; exit 5"`.
- bash absent -> `pytest.skip` (module-level skipif with reason), never xfail.

## Finding to flag (not fixed)
The current Dockerfile wrapper ends in `exec /entrypoint.sh`, not `exec "$@"` (the dockerfile-merge-fix verdict described `exec "$@"`; commit 7409a486 "Update Dockerfile" changed it). CMD arguments are therefore ignored by the wrapper; the test pins the real behaviour (entrypoint exec'd, rc propagated). Also pre-existing and unrelated to this unit: `tests/test_container_supervision.py::test_deploy_is_self_diagnosing_and_honours_cloud_run_port` fails at HEAD (expects `import autotester` after `USER 10001:10001`, which 7409a486 removed).

## Mutation check (scratch copy under .work/mut, not committed)
- Removed the two preflight call lines from entrypoint.sh -> `test_preflight_fails_126_when_python_missing` FAILS (1 failed, 2 passed, 1 skipped). The non-exec test would also fail but is skipped here.
- Removed the `exec /entrypoint.sh` line from the Dockerfile wrapper -> `test_diagnostics_wrapper_execs_entrypoint_and_propagates_rc` FAILS (1 failed, 2 passed, 1 skipped).

## Widening (coordinator, same cycle 0)
- `tests/test_container_supervision.py::test_deploy_is_self_diagnosing_and_honours_cloud_run_port`: stale static assertion replaced with intent checks. A RUN after the first non-root USER imports `autotester` (any import list), the final effective USER is non-root, and the wrapper's last printf line is `exec "$@"` or `exec /entrypoint.sh`. The heredoc branch is dropped.
- The "finding" above (no `exec "$@"`) is resolved: `exec /entrypoint.sh` is the shipped, accepted shape; the behavioural test pins rc propagation for it.
- Mutations (scratch copy `.work/mut2`): final `USER root` -> 2 tests fail (including the rewritten one); removing the wrapper's `exec /entrypoint.sh` line -> rewritten test fails with "wrapper must exec".
- Combined run, both files: 14 passed, 1 skipped (non-exec python on NTFS), 0 failed.
