# Verdict - grader-lexicon

Cycle checked: 1
Verdict: PASS
Head checked: 138dbc2a

## Passed
- All 11 hold and 2 keep-clean test cases pass; 7 real fixture notes stay not-held. "no error, crash or hang on submit" and "No error, rejection, wrong result, or missing element" both clean.
- 321 passed (grade, schema, golden); ruff clean; doctor clean (advisory only); git merge-tree vs master 502feb93 conflict-free.
- Cycle-3 advisory items (froze, no longer works, "a bug or two", "or the error banner") all closed.

## Adversarial notes (35 run; 20 hold-intended, 15 clean-intended)
Held correctly: "isn't working", "fails to load", "did not save", "button is not working", "it crashed", "no error or warning, but the page froze", "no crash, the app freezes", "app is not responding", and 6 more.
Clean correctly: "no error and no crash", "free of errors or crashes", "the app did not freeze", "nothing froze", "no issue or regression observed", and 6 more.

## Residual (non-blocking, advisory; lexicon gaps behind defect_observed)
False-PASS (not held): "nothing works", "the page stops responding", "the dashboard won't load", "nothing happened after click", "the submit did nothing", "no errors; the spinner never stops".
Over-hold (intentional, documented tradeoff, a false INCONCLUSIVE beats a false PASS): "the error message for invalid email appeared as expected", "expected validation error shown for empty password". grade.py has no expected-error exemption; negative cases rely on defect_observed=false, and note_guard still runs after it.
