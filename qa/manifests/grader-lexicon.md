# Manifest - grader-lexicon

**Unit:** grader hardening follow-up to judge-defect-field (cycle 3 checker advisory)
**Branch:** wave/grader-lexicon (from 033931a5)
**Status:** checked-PASS
**Fix cycle:** 1

## Built
`src/autotester/stages/grade_note_guard.py`: "or" + determiner/new subject ends a negation scope;
an "or" list item must be a defect word ("a bug or two", "broken or not" now held); lexicon adds
froze/frozen, "no longer works", "stopped working", "doesn't/does not work".

## Tests
`tests/test_grade_note_guard.py`: all 11 hold cases and 2 keep-clean cases added to the
parametrized lists; the 7 real clean fixture notes still pass (test_grade_defect_field.py).
Grade/schema/golden tests 321 passed, ruff clean.
