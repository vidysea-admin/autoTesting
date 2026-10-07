# Verdict - at787-bundle-wiring, fix cycle 1 (AT-810 repair)

Unit: `wave/at787-bundle-wiring` @ d06dcadd · Contract `qa/contracts/failure-bundle.md` and manifest criteria W1-W4 · Policy proportional-verification/2026-10-07.7, tier S, 10-minute wall, no full suite. Earlier evidence identity: cycle-0 verdict (`qa/verdicts/at787-bundle-wiring.r0-1.md`) at af2d0050. Diff checked: `af2d0050..d06dcadd` (failure_bundle.py, test_failure_bundle_wiring.py, manifest, one issues.jsonl row).

## Verdict: PASS

## Evidence

**W2 (re-checked, was the failed criterion).**
- Read the regex and `recorded_failing_step` myself. `_STEP_IN_ERROR = re.compile(r"\w+: step (\d+) \(")`, applied with `.match`, so only a leading `Type: step N (` names a step.
- It matches exactly what `execute.py:151` `_error_text` writes: `f"{type(exc).__name__}: step {step.order} ({step.action.value}): {exc}"` (only for a replay or `LocatorNotFound`). `type(exc).__name__` is a bare class name, never dotted, so `\w+` at the start cannot miss a real prefix. Every other error is `Type: message`, which no longer names a step.
- New test `test_a_step_number_inside_the_message_is_not_the_failing_step`: a step-2 failure whose error is `timeout waiting for locator('text=step 3 (beta)')` gives failing_step 2 end to end and via `recorded_failing_step`; a genuine `LocatorNotFound: step 2 (click): ...` still gives 2; a prefix-less error with step 1 shot falls back to 2. The existing `LocatorNotFound: step 3 (click): gone` case still gives 3.
- Falsification in a throwaway copy (scratchpad, PYTHONPATH on the copy): regex reverted to `\bstep (\d+) \(` with `.search` -> the new test FAILED (`assert 3 == 2`), 15 passed. The fix is what makes it green. (My first revert attempt dropped the `\b` and instead broke the older test; I redid it with the exact original and got the AT-810 failure above.)

**W1, W3, W4: reused from cycle 0 (unchanged by this diff).** The diff touches only the step regex, its `.match` call, one test and bookkeeping; `bundle_if_failed`, the try/except isolation, the redaction gates and the masked-screenshot refusal are untouched. Cycle-0 results stand: W1 sabotage 5 failed; W3 except-narrowing 2 failed, log-unredacted 1 failed, ENOSPC probe left the verdict identical; W4 `Redactor({})` 1 failed, planted-secret probe clean.

**issues.jsonl.** Every line of `qa/issues.jsonl` parses with `json.loads` (the cycle-0 file had 1 bad line). `git diff af2d0050 d06dcadd -U0 -- qa/issues.jsonl` shows exactly one line changed, the AT-810 row (823); no other row touched.

## Commands I ran (worktree, one process each, `-p no:xdist`, no extra -q)

- `tests/test_failure_bundle_wiring.py` -> 16 passed
- `tests/test_failure_bundle.py` -> 12 passed
- `uv run ruff check src tests scripts` -> All checks passed
- Falsification copy: `tests/test_failure_bundle_wiring.py` -> 1 failed, 15 passed (the new test)

## Merge note

Do not push from here. The branch carries the T-177 commits; the unit merges after T-177.

Cycle checked: 1

Metrics: tier=S checker_runs=1 suite_runs=0 tests_run=28 mutations=1 (copy) probes=2 cycle=1 wall_min=~6 policy=proportional-verification/2026-10-07.7
