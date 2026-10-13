# Verdict - t181-oracle-fix (re-check, AT-998 only)

**Manifest:** qa/manifests/t181-oracle-fix.md
**Contract:** core-invariants C12; grade.md
**Cycle checked:** 2
**Verdict: PASS** (AT-998 only; fresh re-check, other cycle-1 findings unchanged)

## Findings
- Coverage: tests/test_grade_note_guard.py parametrizes 26 defect phrases (did not succeed, unsuccessful, blocked, timed out, not working as expected, did not load, could not, cannot, never appeared, stuck, hangs, denied, incorrect, wrong, missing, broken, crash, exception, 500, 404, failed to, unable to) and 12 negations (no error, without errors, did not fail, nothing blocked, no timeouts, not broken, never crashed, 500ms, $500, ...). All pass.
- Design: defect lexicon plus negated-success pattern, shared negator lookback (3 words). Module 72 lines, functions under 50.
- False-INCONCLUSIVE scan (tests/**/*.json + qa/evidence/**/*.json, nested PASS rows with notes): 78 PASS rows, 11 with notes, 5 held. All 5 are the recorded T-181 bug-note rows (fixture and run_meta, 2 each = 4, true positives) plus one hand-written checker report note (qa/evidence/browser-t204-auth-.../report.json, mentions a 404 finding); that is not a grader output and never passes through grade(). Legitimate graded PASS flipped: 0.
- Known cost unchanged: a correct PASS note mentioning an expected error is held (accepted, fail closed).
- Tests: test_grade_note_guard + test_grade* 104 passed; ruff clean; doctor see commit report.
