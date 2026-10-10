# Manifest — at733-bounded
**Contract:** qa/contracts/ui-run.md RU5 (commit 057b6dbb)
**Goal task:** none (issue AT-733)
**Date:** 2026-10-11
**Fix cycle:** 0 of max 2
Fix cycle: 0
**Dual check:** no — no `security|auth|tenancy|prod-write <path:line>` trigger exists: the deleted directory is the gitignored scratch browser profile `profiles/<slug>-entry-test`; the defect is a verdict that can be wrong, not a credential or tenancy leak, and false-PASS prevention is not a policy trigger class (brief section 1).
**Persona walk:** skip (no visible UI change: the diff touches ui/run_execution.py and one test file only; checkable with git diff --name-only 057b6dbb, which lists no route, template or static file)
**Issues addressed:** AT-733
**Executor:** claude-sonnet-subagent
**Executor rationale:** one bounded behaviour change in one function plus its test, per qa/briefs/at733-bounded.md.

## What changed
- src/autotester/ui/run_execution.py:60-107 — new private `_wipe_entry_profile(profile)`: `shutil.rmtree` without `ignore_errors` (`FileNotFoundError` suppressed = already absent), then `profile.exists()`; any `OSError` from either, or a still-present directory, raises `OSError("entry profile not removed: <path> (<cause>)")`. `_run_entry_case` calls it inside its existing `try` (the `BrowserSession` construction moved into the `try`, `session = None` before it, `finally` closes only if started), so the existing `except Exception` builds the ERRORED `RawResult` (scrubbed) and `grade_errored_result` grades it. No new result or grade path. Both callers (`_run_cases_serially`, `_run_entry_cases`) share the one function.
- tests/test_ui_runs_serial_resilience.py:222-300 — appended helper `_run_entry_and_sibling` and 2 test functions (5 nodes): `test_an_entry_case_whose_profile_is_not_removed_is_errored_and_never_run` x {leaves-directory, raises-permission-error} x {width 1, width 2}, and the control `test_an_entry_case_with_a_healthy_wipe_still_runs`. Existing tests untouched except the added imports (`shutil`, `pytest`).
- Line counts: run_execution.py 214 (cap 300), test file 300 (cap 300). `_run_entry_and_sibling` is the longest new function, under 50 lines.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: M (shared module used by the serial and parallel paths + test file; no security/auth/tenancy/prod-write/concurrency/config surface)
Base / checked state: base 057b6dbb (branch wave/at733-bounded, worktree .worktrees/at733-bounded); code commit b07cc727d3d965b7f7a3040d12f29eaf3c4f832b
Gate answers: qa/gates/commit-before-verdict.md:60 (C, committed on wave/<slug> before check); qa/gates/plan-approved.md:13; approval to run qa/QUEUE.md:327 (D-081).
Affected tests / full-suite trigger: tests/test_ui_runs_serial_resilience.py (8 passed), tests/test_ui_runs_serial_entry_order.py (21 passed), tests/test_ui_runs_serial_entry_screenshot_namespace.py (1 passed); full-suite trigger: none. The builder ran no full suite.
Pre-check[RU5]: b07cc727d3d965b7f7a3040d12f29eaf3c4f832b uv --directory D:/autoTesting/.worktrees/at733-bounded run pytest -p no:xdist tests/test_ui_runs_serial_resilience.py -> 8 passed t=4 blobs=tests/test_ui_runs_serial_resilience.py:72bee8f,src/autotester/ui/run_execution.py:0f4c0c4
Pre-check: b07cc727d3d965b7f7a3040d12f29eaf3c4f832b uv --directory D:/autoTesting/.worktrees/at733-bounded run pytest -p no:xdist tests/test_ui_runs_serial_resilience.py -> 8 passed t=4 blobs=tests/test_ui_runs_serial_resilience.py:72bee8f,src/autotester/ui/run_execution.py:0f4c0c4   <- untagged duplicate: tick.mjs CRIT_RE only accepts C<n> tags, so the RU5-tagged line above is invisible to --lint-manifest
Metrics: start=unavailable end=2026-10-11 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=0 mutants=0 defects_unit=0 defects_6c=0

## Acceptance criterion RU5, verbatim from qa/contracts/ui-run.md (commit 057b6dbb)

- **RU5 — an entry-screen case never runs on a profile that was not removed (added 2026-10-11; issue
  AT-733; `core-invariants.md` C12(b)).** An entry-screen case (`_is_entry_case`) is meant to start
  from a genuinely logged-out state, which is why it gets a dedicated profile, `ProjectPaths(f"{slug}-entry-test").profile_dir`
  (`profiles/<slug>-entry-test`), wiped before its run (amendment log, 2026-09-04). The wipe is the
  only thing that makes that start state true, so it is a measurement and fails closed.
  - Before the case's browser starts, the profile directory is removed and then **positively
    established absent**. These are all failures: the removal raises (`OSError`, `PermissionError`),
    the directory is still present afterwards, or the presence check itself raises, so that absence
    cannot be determined. A directory that was already absent before the wipe is success. A
    presence test that reports "absent" when it errors (for example `os.path.lexists`) is the fail-open
    shape C12 forbids and does not satisfy this criterion.
  - On any such failure the case's `RawResult` is `ERRORED`, its error names the profile path and the
    cause (scrubbed like any other case error), and its verdict comes from `grade_errored_result`
    (the existing errored-result path, so never PASS and never FAIL). No `BrowserSession` is started
    for that case and the case is never executed. Every sibling case still runs and the Run record is
    still saved (RU3); the failure is one case's ERRORED, not a 500 and not an aborted run.
  - One behaviour on every path that runs an entry case: the serial path and the entry leg of a
    parallel run (both call `ui/run_execution.py::_run_entry_case`).
  - **Verify (by construction, C12(b)):** a test builds the unpopulated state and asserts the report
    says it. With the removal stubbed to leave the directory in place, and separately stubbed to
    raise `PermissionError`, a run containing one entry case and one sibling, once with a serial
    plan and once with a width-2 plan, ends with: the entry case `ERRORED`, its error containing the
    profile path, its verdict not PASS, the fake case runner never given the entry case id, no
    `BrowserSession` constructed for `<slug>-entry-test`, the sibling `COMPLETED` and the Run saved.
    The control: a healthy wipe of a directory holding a stale file leaves it absent and the entry
    case executes. Falsification (checker, throwaway copy, anchor matching once, copy green first):
    restore `shutil.rmtree(..., ignore_errors=True)` with no absence check; the stub-leaves-directory
    test must go red on its own named assertion. On Windows the checker may also hold a file open
    inside the profile (no share-delete) and expect `ERRORED`, not PASS; that probe is the checker's
    and is optional on POSIX, where deleting an open file succeeds.
  - **Does not require:** the reason a removal fails to be fixed, a retry, or a changed profile path.
    The criterion is that a case which cannot get its logged-out start refuses to run, not that the
    wipe always succeeds.

## How to verify (commands + expected)
- `uv run pytest -p no:xdist tests/test_ui_runs_serial_resilience.py` -> expected: 8 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed
- `uv run autotester doctor` -> expected: no violation caused by these files (see BLOCKED-PROCESS below)

## Actual outputs (from maker's own run)
- Test-first (TDD): fix stashed, new tests run on the unfixed source: `4 failed, 4 passed`. `[leaves-directory-1]` failed on `assert results[entry.id].outcome is Outcome.ERRORED` with `COMPLETED` (the entry case ran on the leftover profile and passed), the right reason. The raises modes failed because the exception escaped `_run_entry_case` outside its `try` (AT-574 shape).
- Fix restored: `8 passed` (pre-check above). One test-harness mistake was found and fixed on the way: the first fake grader returned PASS for every result, so an ERRORED entry result graded PASS; the fake now delegates non-COMPLETED results to the real `grade`, which shortcuts ERRORED deterministically (the real `grade_errored_result` path).
- Scoped neighbours on the final tree: entry_order `21 passed`, entry_screenshot_namespace `1 passed`.
- `uv run ruff check src tests scripts` -> All checks passed
- `uv run autotester map` -> docs/MAP.md regenerated, no diff (no module added).
- `uv run autotester doctor` -> 1 violation, `stale-generated: docs/SNAPSHOT.md differs from regeneration; run autotester snapshot`. Identical in a clean archive copy of this commit, so pre-existing and unrelated to the two files.

## BLOCKED-PROCESS (recorded per the brief stop rule, not diagnosed)
BLOCKED-PROCESS: `uv run autotester doctor`, exit 1, `stale-generated: docs/SNAPSHOT.md differs from regeneration; run autotester snapshot`. docs/SNAPSHOT.md is a generated file outside this unit's files and its committed copy is stale. Not touched. Whoever owns snapshot regeneration should run `autotester snapshot`.

## Capability coverage (each new claim -> its isolating falsification)
Falsify[RU5]: tests/test_ui_runs_serial_resilience.py::test_an_entry_case_whose_profile_is_not_removed_is_errored_and_never_run[leaves-directory-1] green@b07cc727d3d965b7f7a3040d12f29eaf3c4f832b (8 passed in a throwaway copy of this commit) red@same copy with the fix reverted (4 failed, 4 passed)

| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| RU5 | an entry case never runs on a profile that was not removed: ERRORED naming the path, not PASS, no BrowserSession, sibling and Run saved, both widths | tests/test_ui_runs_serial_resilience.py::test_an_entry_case_whose_profile_is_not_removed_is_errored_and_never_run (4 nodes) | in a throwaway copy under the session scratchpad (not this worktree) replace the `_wipe_entry_profile(entry_paths.profile_dir)` call by `shutil.rmtree(entry_paths.profile_dir, ignore_errors=True)` (anchor matched once, file changed, verified with cmp) | green before: `8 passed`; red after: `4 failed, 4 passed`, `AssertionError: assert <Outcome.COMPLETED: 'completed'> is <Outcome.ERRORED: 'errored'>` (leaves-directory-1 and -2) and `assert '<profile path>' in 'PermissionError: locked by another process'` (raises-permission-error-1 and -2); restored: `8 passed`. The control test stayed green in all three runs. |

## Browser
Not run (no UI change; brief section 9).

## Notes for the checker (things in the brief or RU5 that were not exact)
- The brief planned at most four new nodes; RU5's Verify clause requires both stub modes at both widths plus the control, so there are 5 nodes in 2 test functions.
- The raises-permission-error stub replaces `shutil.rmtree` itself, so it raises regardless of `ignore_errors`; on the unfixed source that exception escapes `_run_entry_case`. The real-world false PASS is the leaves-directory shape (ignore_errors swallowing a failed removal), which fails on the unfixed source with COMPLETED.
- `master` moved on (424f120a at build end) since base 057b6dbb; this branch is based on 057b6dbb. The pre-check sha is the code commit; the manifest commit after it changes only qa/manifests/at733-bounded.md.
- The optional Windows locked-file probe (hold a file open inside the profile with no share-delete) was not run by the builder; it is the checker's, optional under RU5.
- One `noqa: RUF018` on a walrus assert exists only to keep the test file at the 300-line cap.

Status: ready-for-check
