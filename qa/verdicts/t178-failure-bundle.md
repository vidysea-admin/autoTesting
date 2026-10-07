# Verdict - t178-failure-bundle (T-178 slice FB1-FB3)

Checker: fresh context, tier M (proportional-verification/2026-10-07.7): single checker, no full suite.
Branch wave/t178-failure-bundle, head d01e5d61, base 7782df41.
Contract: qa/contracts/failure-bundle.md (FB1-FB3 judged; FB4-FB5 deferred).
Cycle checked: 0

## Check plan (stated before running)
1. Read the diff and the code lines behind FB1, FB2, FB3 end to end (stages/failure_bundle.py, schema/failure_bundle.py).
2. Affected tests: tests/test_failure_bundle.py, tests/test_doctor.py, tests that import core/paths.py (test_*path*.py: only test_onboard_pathlynks / test_run_pathlynks_first_cases match by name; ProjectPaths is imported by 29 test files but the diff only ADDS a method). Then ruff and doctor.
3. Falsification floor of 1 per capability in a throwaway copy (scratchpad/chk), never the worktree.
4. Security: scrub + assert_clean gate; masked-flag trust vs the FB3 wording.
5. paths.py edit minimal and non-altering.
6. Is wiring into the run pipeline required by any FB1-FB3 criterion?
7. Is the FB4/FB5 deferral stated honestly?

## Verdict: PASS (FB1, FB2, FB3). T-178 itself stays pending: FB4 and FB5 are unbuilt.

## Evidence
### 1. Code read
- FB1: `build_failure_bundle` (stages/failure_bundle.py:155-188) writes every part into `<id>.partial/`, `manifest.json` LAST (line 186), then `partial.rename(final)` (187). `load_bundle` (191-209) refuses a `.partial` name, a missing manifest, a missing or hash-mismatched file, a file stamped with another run, and a bundle lacking case/verdict/result/error/trace. `_window` (108-114) gives the failing step plus `neighbours` (default 1) each side, clipped at the ends.
- FB2: `_check_one_run` (83-95) compares verdict.run_id, each screenshot source run_id and each span trace_id to the run id, raising `RunMixError` before any byte is written; the loader re-checks per-file run_id.
- FB3: every text part passes `Redactor.scrub`/`scrub_obj` then `assert_clean` (70-80, 143, 151, 186); the manifest is scrubbed too; screenshots with `masked=False` inside the window raise `UnmaskedScreenshotError` before writing (170-171).
### 2. Commands (run in the worktree)
```
uv run --project .worktrees/t178 pytest tests/test_failure_bundle.py tests/test_doctor.py <test_*path*.py>   -> 62 passed in 26.64s
uv run --project .worktrees/t178 ruff check src tests scripts                                               -> All checks passed!
uv run --project .worktrees/t178 autotester doctor                                                          -> doctor: clean
```
### 3. Falsification (throwaway copy, PYTHONPATH on the copy; baseline 12 passed)
| sabotage | result |
|---|---|
| FB1: write straight into the final dir, no rename | 3 failed, incl. test_a_write_that_dies_mid_bundle_leaves_only_the_partial_and_the_loader_refuses |
| FB1: neighbours default 0 | 5 failed |
| FB2: `if stray:` -> `if False:` | 3 failed (planted screenshot, out-of-window screenshot, verdict/trace span) |
| FB3: drop the masked refusal | 1 failed (test_an_unmasked_screenshot_is_refused...) |
| FB3: scrub no-op + gate removed | 2 failed (planted secret test, residual-secret backstop) |
Worktree untouched (`git status` clean).
### 4. Security
Planted-secret test reads the bytes of every file and every file name, and runs `check_no_secrets.scan` over the bundle files; value absent, `[REDACTED]` present. The gate backstop test shows a broken `scrub` still cannot persist a secret (`assert_clean` aborts, only a `.partial` remains). The builder trusts `Evidence.masked` (set True by browser/evidence.py:90 after masking at capture) and never inspects pixels. That matches the contract text ("masked secret inputs in screenshots": masking is a capture-time act, the bundle refuses anything not so marked). It is a trust boundary, not a defect; see PROPOSED-ISSUE 2.
### 5. paths.py
Diff is +4 lines, one new method `bundles_dir(run_id)`; no existing path changed.
### 6. Wiring
FB1-FB3 criteria and Verify clauses are all stated at the builder/loader level with fixtures ("a fixture whose writer raises", "plant one artifact ... assembly raises", "run a fixture case"). None says the bundle is produced by a live failing run, so nothing in FB1-FB3 FAILs for lack of a caller. The contract's "Why it exists" implies a consumer; that is unmet and untracked, so it is raised as a finding rather than a FAIL. Grep confirms `build_failure_bundle` and `bundles_dir` have no caller in src/.
### 7. Deferral honesty
Manifest header, "What was built", and "Open items" state FB4 (needs Case.priority in schema/case.py) and FB5 (needs expand.py and T-125) are deferred, that T-178 stays pending and "should not close on this slice". Honest. Process note: contract goes ACTIVE on "T-178's first checker PASS"; this partial PASS should not flip it, the maker/orchestrator should keep it DRAFT until FB4/FB5 land.

## Findings
- PROPOSED-ISSUE 1 (medium): nothing calls `build_failure_bundle`/`ProjectPaths.bundles_dir`; no run/report path produces a bundle on a failing run, so O3 "every finding carries evidence" is not yet served by this unit. Add a wiring criterion (or a T-178 sub-task) before T-178 closes; the failing-step default (highest screenshot step_order) is a heuristic that the wiring must replace with the real failing step.
- PROPOSED-ISSUE 2 (low): FB3 screenshot safety rests wholly on the `Evidence.masked` flag; a test of the real capture path (browser/evidence.py -> sources_from_result -> bundle) with a planted secret in a masked input would close the end-to-end gap.
- PROPOSED-ISSUE 3 (low, process): the implementation was drafted before its tests; red evidence comes only from sabotage runs. Not a FAIL.
- PROPOSED-ISSUE 4 (low): docs/ARCHITECTURE.md concept-map row for the bundle is owed under a DECISIONS entry (manifest says so).
- PROPOSED-ISSUE 5 (low): contract status line says ACTIVE on first PASS; keep DRAFT until FB4/FB5 are checked.

Metrics: tier=M checker_runs=1 suite_runs=0 tests_run=62 mutations=5 (copy) wall_min~8 cycle=0 policy=proportional-verification/2026-10-07.7
