# Verdict: judge-defect-field

Cycle checked: 1
Verdict: FAIL
Head checked: d1970464

## Passed
- Merge with master conflict-free (git merge-tree clean); 2869fe32 is an ancestor of the branch.
- tests/test_grade*.py plus schema/golden tests: 267 passed. ruff clean. doctor clean (advisory only).
- Schema: defect_observed/defect_summary default None, Judgment keeps extra="forbid", old artifacts load. Prompt text lives in skills/grade/SKILL.md.
- The 8 real phrases grade PASS (they are reconstructed from the analysis excerpts, not full notes).

## Defects
1. FAIL, false-PASS regression: src/autotester/stages/grade_note_guard.py:74-88 (`_negated`, `_SCOPE_WORDS = 14`).
   A negator anywhere earlier in the same clause, up to 14 words back, suppresses a later defect word.
   Master's 3-word lookback caught these notes; the branch passes them (field absent):
   - "The login showed no spinner and an error message is shown" -> []
   - "No data was saved and the error banner is displayed" -> []
   - "There is no confirmation, error message shown" -> []
   - "No redirect happened and an error is shown" -> []
   Plain "error message shown" is still caught. Fix: stop the negator's scope at "and"/"," when a
   new subject begins, or shrink the scope. Add these as tests.
2. tests/test_grade_defect_field.py:28-35: MISFIRES are paraphrases, not verbatim real notes
   (the full notes are not in the analysis file). Add the real notes from runs/ if available.
3. defect_observed=false is trusted over the note by design, so a judge that says false with a
   defect-describing note is a PASS. Note this as an accepted risk.

---

# Cycle 2

Cycle checked: 2
Verdict: FAIL
Head checked: 93fad43f

## Passed
- The 4 cycle-1 phrases are now held. 25 of 29 of my own adversarial notes held (scratch: .work/adv.py, adv2.py in the checker worktree).
- Fixture tests/fixtures/t169_real_judge_notes.json: 8 notes verbatim against run-01M4TS6A79X14E32AQ3KA7HJ9T verdict.json files (7 byte-exact, 1 identical modulo console encoding of an em dash). No secrets or emails.
- 282 passed (grade, schema, golden, gemini schema tests); ruff clean; doctor clean; git merge-tree with master has no conflicts.

## Defects
1. FAIL, false-PASS: `_negated` lets "," bridge to any following defect word, so a negated defect followed by a comma and a NEW defect statement is treated as one negated list. These wrongly PASS (field absent):
   - "No crash, error shown"
   - "no error, broken layout" / "no errors, wrong value" / "no error, invalid total shown"
   - "no error, 500" / "no error, unexpected redirect"
   - "no issues, crash on submit" / "no problems, unable to submit"
   - "Not blocked, missing field"
   Same shape as the cycle-1 hole ("no confirmation, error message shown") but with a defect word as the first item.
   Narrowest fix: a comma bridges only when the list is closed by "or"/"and"-free coordination, i.e. require an "or" later in the same list ("no error, rejection, or missing element"); a bare "A, B" with no "or" after the comma does not extend scope. Add the above as tests, keep the verbatim "No error, rejection, wrong result, or missing element" PASS.
2. Accepted risk (defect_observed=false overrides a defect note): consistent with C12 as the structured field is the judge's explicit claim and the note guard is only a backstop when it is absent; but it is a real hole where the judge says false and the note says "error shown". Not failing on this alone; narrowest mitigation: when defect_observed=false and note_guard finds terms, hold INCONCLUSIVE (costs only false INCONCLUSIVEs, and the real-run notes under the fix above stay clean). Recommend adopting it with fix 1.
