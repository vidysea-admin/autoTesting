# Verdict: grader-lexicon-2

Cycle checked: 1
Verdict: PASS
Commit checked: b0ceb0f3

Phrase probe (failure_terms, field absent):
- Clean (correct): "no duplicate entries found", "nothing was lost", "page not blank, dashboard loaded", "no data loss occurred", "dashboard loaded and user saw own data".
- Held, defects (correct): duplicate rows appeared, another user's data visible, went blank, exposed to someone else's.
- Held, conservative over-holds (acceptable): "lost focus on the field", "exposed the expected settings panel", "the other user's view was not affected" (negation not applied to other user's).
Fixture t169_real_judge_notes.json: 8 notes; 7 clean. case_7a978722a38c holds error/errors identically on base d33033c2 (pre-existing, not a regression).
Tests: test_grade_note_guard, test_grade_defect_field, test_grade: 191 passed. ruff clean. doctor clean. merge-tree vs 7f66e3b4 clean.
