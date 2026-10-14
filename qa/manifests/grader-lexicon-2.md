# grader-lexicon-2

Status: checked-PASS
Fix cycle: 1
Branch: wave/grader-lexicon-2 (from d33033c2)

Unit: src/autotester/stages/grade_note_guard.py defect lexicon adds expos(ed|es|ing), duplicat*, lost, data loss / loss of data, blank page|screen, went blank, another|other user's, someone else's. Held with field absent and with expects_error=True. "not saved" already held by the negated-success rule. leak* already present.
Left out on purpose: "logged in" - it is success wording in best cases ("user logged in and dashboard shown"); a bare phrase would false-hold them.
Tests: tests/test_grade_note_guard.py (+ lexicon_2 cases), test_grade_defect_field.py, test_grade.py: 191 passed. ruff clean, doctor clean.
