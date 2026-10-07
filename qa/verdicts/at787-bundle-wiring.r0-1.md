# Verdict - at787-bundle-wiring (AT-787: failure bundle wired into the run pipeline)

Unit: `wave/at787-bundle-wiring` @ fe360bea · Contract `qa/contracts/failure-bundle.md` (FB1-FB3 as the gates W4 reuses) and manifest criteria W1-W4 · Policy proportional-verification/2026-10-07.7, tier M, single checker, no full suite.

## Check plan (written first)

1. Read the diff 981d765d..fe360bea (`failure_bundle.py`, `run_case_pipeline.py`, new test). Merge base with the T-177 branch is cb3000a8; the other 14 files in `origin/master...HEAD` are T-177's and are not judged here.
2. Run affected tests one process at a time (`-p no:xdist`, no `-q`): wiring, failure_bundle, run_case_pipeline(+resilient), agent_fallback, script_replay. Ruff and doctor.
3. Falsification: one sabotage per W in a throwaway copy under the scratchpad (PYTHONPATH on the copy, bound tree untouched).
4. Own probes for the weighed notes: step-N regex against error text with a number (b), disk-full and verdict identity (W3), planted secret / `{{SECRET:...}}` / password-field note (W4).

## Verdict: PASS

## Evidence

**W1** `bundle_if_failed` (`failure_bundle.py:~252`) returns None unless `verdict.result is FAIL or result.outcome is ERRORED`; called once at the end of both `run_and_grade_case` and `run_and_grade_case_resilient`. Tests: ERRORED and FAIL write one loadable bundle on both entry points; PASS, INCONCLUSIVE and grader-crash-after-COMPLETED write none. Sabotage (guard replaced by `if False`): 5 failed. Note (a) accepted: ERRORED grades INCONCLUSIVE by rule (grade.py), so the OR is the only way to bundle an errored run; it is stated in the docstring and manifest.

**W2** `recorded_failing_step` precedes the screenshot heuristic in `_failing_step`. The errored test names step 2 where the heuristic says 1; the unmet-assertion test names step 2 where the heuristic says 3. Sabotage (`_failing_step` skips it): 2 failed. Note (b) weighed: see AT-810, one real wrong-step case in the error-text signal.

**W3** Both the redactor fetch and the build are in `try/except Exception`; the log line goes through `redactor.scrub`, and the first except logs only the exception type. The function returns None and does not touch `verdict`/`result`. My probes: P3 `Path.write_text` raising `OSError(ENOSPC)` - run completes, verdict result and scoreboard equal the control, log says "not built: OSError: [Errno 28]"; P4 `verdict.model_dump()` identical before and after a successful build. Sabotages: except narrowed to ZeroDivisionError: 2 failed; log unredacted: 1 failed.

**W4** The builder's own gates are reused: `Redactor.scrub_obj` + `scrub` + `assert_clean` on every text part, masked-screenshot refusal (FB3). My probe P2: error text with the planted secret twice plus a case note "type {{SECRET:DEMO_PW}} into password field" - no byte of the secret in any bundle file, no `.partial` left behind. Existing test also covers the unmasked-screenshot refusal (no bundle, logged `UnmaskedScreenshotError`). Sabotage (`Redactor({})` handed to the builder): 1 failed (the manifest says 2; the log redaction one only fails under the separate log sabotage). No real masked password-field screenshot is exercised (fake page); see AT-811.

## Commands I ran (worktree, one process each, no xdist)

- `tests/test_failure_bundle_wiring.py` + `tests/test_failure_bundle.py` -> 27 passed
- `tests/test_run_case_pipeline.py` -> 11 passed; `tests/test_run_case_pipeline_resilient.py` -> 2 passed
- `tests/test_agent_fallback.py` -> 31 passed; `tests/test_script_replay.py` -> 15 passed (318 s, slow but green)
- `uv run ruff check src tests scripts` -> All checks passed
- `uv run autotester doctor` -> 1 violation: stale-generated `docs/SNAPSHOT.md`, as the manifest says; it is not caused by this unit (this diff touches no SNAPSHOT input).
- File sizes: `failure_bundle.py` 270, `run_case_pipeline.py` 272 (both <= 300).

## Findings

- AT-810 (medium): `_STEP_IN_ERROR = r"\bstep (\d+) \("` is unanchored. execute.py `_error_text` emits `Type: step N (action): ...` only for replays and LocatorNotFound; any other ERRORED error is `Type: message`, so the regex only matches by accident, e.g. a Playwright timeout on `text=step 3 (beta)` for a failure at step 2 named step 3 (probe P1: failing_step=3, real 2). A false bundle, which the contract calls worse than none. Anchor to `^\w+: step (\d+) \(` and add the case.
- AT-811 (low): process and coverage. Source was written before the tests (the builder says so; red evidence is sabotage only, same as T-178). No test drives a real masked password-field screenshot through the pipeline; W4 rests on the unit-level FB3 gates plus the planted-secret text tests.

Not blocking PASS: W2 holds in every case the tests and probes covered except one contrived-but-plausible error text, and the fix is one anchor.

## Merge note

Do not push from here. The branch contains the T-177 commits; merge T-177 first, then this.

Cycle checked: 0

Metrics: tier=M checker_runs=1 suite_runs=0 tests_run=86 mutations=5 (copy) probes=4 cycle=0 wall_min=~14 policy=proportional-verification/2026-10-07.7
