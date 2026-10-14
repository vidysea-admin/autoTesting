# Manifest - grader-expected-error

**Unit:** expected-error exemption for the note guard (negative cases held INCONCLUSIVE since judge-defect-field cycle 3)
**Branch:** wave/grader-expected-error (from 138dbc2a; grader-lexicon now on master 93d6eb1a)
**Status:** ready-for-check
**Fix cycle:** 1

## Built
- `schema/verdict.py`: `Rubric.expects_error: bool = False` (no Case field existed that grade can see; grade only gets the Rubric).
- `stages/case_expectation.py` (new): `expects_error(case)` = kind worst/edge and rationale/title/step visible_text mention error/invalid/reject/validation/denied/refus/warning. `default_rubric` stamps it.
- `grade_note_guard.py`: with `expects_error`, only error/invalid/incorrect/wrong/denied/reject* are dropped, only in a clause saying expected/as intended/correctly/properly and not containing "unexpected". crash, 500, froze, timeouts etc. always hold. Lexicon adds nothing works, stops responding, won't load, nothing happened (not "... to ..."), did nothing, spinner never stops.
- `grade.py`: passes `rubric.expects_error` to the guard.
- Limit: persisted hand-written/older rubrics lack the flag (default false = old conservative behaviour).

## Tests
`tests/test_grade_defect_field.py`: expected-error negative passes (and is held when flag false); crash/500/froze/"unexpected error"/bare "Error message shown" held; best-case "error message shown" held; 6 new phrases hold; "Nothing happened to the saved data" stays clean; 7 real fixture notes unchanged. Grade/schema/golden/pipeline/doctor tests 273 passed, ruff clean, doctor 0 violations (docs/MAP.md regenerated).
