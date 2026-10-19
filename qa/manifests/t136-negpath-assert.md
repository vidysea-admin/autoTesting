# Manifest - t136-negpath-assert
**Contract:** qa/contracts/grade.md (G3, G6), qa/contracts/core-invariants.md C12, qa/contracts/browser-and-secrets.md B11
**Goal task:** T-136
**Date:** 2026-10-19
**Fix cycle:** 0 of max 2
**Dual check:** no (a grader-decision and test-data change; no security/auth/tenancy surface and no production write, so no dual-trigger applies)
**Issues addressed:** none
**Authority:** Umesh, chat 2026-10-19: "go with the best way possible and with your recommendtation" (answers qa/gates/t136-route-after-r4.md: negative-path PASS yes; add assertions yes)

## What changed
- src/autotester/stages/run_case_pipeline.py:117-119 (rubric_for_case) - ROOT CAUSE of the a5ea hold: the stored rubric rub_case_a5ea57c0961a.json was saved 2026-09-04, before `Rubric.expects_error` existed, so it loads False; `is_stale_default` treats it as hand-authored and never refreshes it, so the G3 expected-rejection exemption never reached a persisted rubric. The flag is a fact about the case (`case_expectation.expects_error`: worst/edge whose own outcome is a rejection), so rubric_for_case now raises it in memory (never persisted, never lowered).
- src/autotester/stages/grade.py:236-237, 255-275 (_defect_decision) - when the judge omits `defect_observed`, a negative-path case (`expects_error`) whose own deterministic assertion was met (`backed`, the DOM showed the expected rejection) may use the expected-error exemption; positive-path cases, a missing assertion, and any contrary marker keep the guard exactly as before.
- src/autotester/stages/grade_images.py:68 - `_met_assertions` made public as `met_assertions` (one concept, one place: the B11 count is reused, not re-implemented).
- projects/pathlynks/cases.jsonl (3 rows, other rows byte-identical) - real `expected.visible_text` added from the recorded run evidence (.work/t136-live-report-r4.md, run-01M58F744J7R3CB99CMH9S7FQ3 screenshots read directly): case_efaed2c0eb91 step 4 "Logged in successfully" (toast after a correct login); case_7a978722a38c step 2 "Email, mobile, or Student ID is required" and "Password is required" (both inline messages on the empty submit); case_093f5070df79 step 4 "Invalid credentials" (toast and inline text). Ids kept stable (runs, verdicts and bench cite them); like the four older rows their id no longer equals compute_id, which update-in-place already allows (project_store.update_case). Editing `expected` changes the script `steps_hash`, so the next run re-records the replay script (locators only); that is the existing stale-script path.
- tests/test_grade_negative_path.py (6 tests added), tests/test_pathlynks_login_case_assertions.py (new, 6 tests).

## Verification scope
Policy-Version: proportional-verification/2026-10-19.16
Tier: M - changes the grader's fail-closed decision path (C12) plus 3 test-data rows; no security/auth/tenancy, no prod write, no schema change
Round: 6 files, 2 criteria, est 25 min - one guard parameter, one rubric-resolution line, three data rows, two test files
Base / checked state: base 4ce91ea8; code commit 45a4b889; the manifest commit follows and touches only qa/manifests
Gate answers: qa/gates/t136-route-after-r4.md (answered by Umesh in chat 2026-10-19): "negative-path PASS yes; add assertions yes"
Affected tests / full-suite trigger: grade tests below plus tests/test_store.py (reads the cases file); no conftest, shared fixture, lockfile or runner-config change, so no full-suite trigger. The builder runs no full suite.
Tests[C1]: tests/test_grade_negative_path.py::test_a_rubric_saved_before_expects_error_existed_still_gets_the_case_expectation, ::test_wrong_password_rejected_with_met_assertion_passes_even_without_defect_field, ::test_a_positive_path_case_never_gains_expects_error, ::test_a_positive_path_login_whose_note_says_rejected_is_still_downgraded, ::test_without_a_met_assertion_the_missing_defect_field_still_holds_the_pass, ::test_negative_path_note_with_a_contrary_marker_is_still_held_despite_met_assertion, plus the existing G3 set in the same file and tests/test_grade_note_guard.py, tests/test_grade_defect_field.py, tests/test_grade_visual.py, tests/test_grade.py, tests/test_grade_assertion_rule.py - they cover every caller of the changed _defect_decision, met_assertions and rubric_for_case
Tests[C2]: tests/test_pathlynks_login_case_assertions.py (3 scenario tests naming the real student actions, 3 action-untouched checks) and tests/test_store.py - the cases file still loads through the schema
Tests[C12]: tests/test_grade_note_guard.py, tests/test_grade_defect_field.py, tests/test_grade_negative_path.py (G3 and the held-pass cases) - core-invariants C12 (fail closed) is the invariant the change must not weaken: every held-pass case in them must stay held
Pre-check[C1]: 45a4b889 uv run pytest tests/test_grade_negative_path.py tests/test_grade_note_guard.py tests/test_grade_defect_field.py tests/test_grade_visual.py tests/test_grade.py tests/test_grade_assertion_rule.py -> 239 passed t=19 blobs=tests/test_grade_negative_path.py:14478d2,tests/test_grade_note_guard.py:e924e12,tests/test_grade_defect_field.py:963d2ce,tests/test_grade_visual.py:f2a4d29,tests/test_grade.py:7bc75db,tests/test_grade_assertion_rule.py:0810af0
Pre-check[C12]: 45a4b889 uv run pytest tests/test_grade_negative_path.py tests/test_grade_note_guard.py tests/test_grade_defect_field.py tests/test_grade_visual.py tests/test_grade.py tests/test_grade_assertion_rule.py -> 239 passed t=19 blobs=tests/test_grade_negative_path.py:14478d2,tests/test_grade_note_guard.py:e924e12,tests/test_grade_defect_field.py:963d2ce,tests/test_grade_visual.py:f2a4d29,tests/test_grade.py:7bc75db,tests/test_grade_assertion_rule.py:0810af0
Pre-check[C2]: 45a4b889 uv run pytest tests/test_pathlynks_login_case_assertions.py tests/test_store.py -> 25 passed t=15 blobs=tests/test_pathlynks_login_case_assertions.py:170d242,tests/test_store.py:a356f07
Falsification[C1]: copy under C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/e46c0e51-15e9-4a31-a0b0-cf49de9d445f/scratchpad/t136-negpath-assert: revert BOTH src edits (`note_guard(final, note)` and `return rubric`) -> 2 failed (test_a_rubric_saved_before_expects_error_existed_still_gets_the_case_expectation: assert False is True; test_wrong_password_rejected_with_met_assertion_passes_even_without_defect_field: INCONCLUSIVE is not PASS), 27 passed. Second edit `note_guard(final, note, True)` (drop the backing requirement) -> 4 failed, incl. test_without_a_met_assertion_the_missing_defect_field_still_holds_the_pass and the three G3 test_g3_without_the_structured_field_nothing_is_exempt cases.
Falsification[C2]: same copy, cases.jsonl restored to base 4ce91ea8 -> 3 failed (test_a_student_logs_in..., test_a_student_submits_an_empty_form..., test_a_student_types_a_wrong_password...), 3 passed.
Metrics: start=2026-10-19T08:15:00Z end=2026-10-19T09:25:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.16 check_s=0 mutants=0 defects_unit=0 defects_6c=0 builder_min=unavailable

## How to verify (commands + expected)
- `uv run pytest tests/test_grade_negative_path.py tests/test_pathlynks_login_case_assertions.py` -> expected: all pass
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
```
pytest (C1 set, 6 files): 239 passed, 1 warning
pytest (C2 set): 25 passed, 1 warning
uv run ruff check src tests scripts: All checks passed!
uv run autotester doctor: doctor: clean   (exit 0; the decision-citation lines are pre-existing advisory output)
```
Open point for the checker: the live verdict does not record whether gemini set `defect_observed`, so the two causes are not separable from the stored verdict. Both are fixed (the stored rubric has no flag, which is a certain cause; and a backed exemption covers an absent field). No rubric file was edited. A live re-run of a5ea is not part of this unit.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | a negative-path case (rubric saved before expects_error existed, judge note "correctly rejected ... invalid credentials", assertion met) reaches PASS | tests/test_grade_negative_path.py::test_a_rubric_saved_before_expects_error_existed_still_gets_the_case_expectation and ::test_wrong_password_rejected_with_met_assertion_passes_even_without_defect_field | revert the two src edits in the scratchpad copy | green in the tree, then "2 failed, 27 passed" in the copy (assert False is True; INCONCLUSIVE is not PASS) |
| C1 | a positive-path case with failure words is still downgraded; an unbacked or contrary note stays held | ::test_a_positive_path_login_whose_note_says_rejected_is_still_downgraded, ::test_without_a_met_assertion_the_missing_defect_field_still_holds_the_pass, ::test_negative_path_note_with_a_contrary_marker_is_still_held_despite_met_assertion | pass `True` instead of `expects_error and backed` in _defect_decision | "4 failed, 25 passed" in the copy, incl. test_without_a_met_assertion_the_missing_defect_field_still_holds_the_pass |
| C2 | the three login cases declare a deterministic expected text, so B11 has an `assert ...: met` row to back a masked-screenshot PASS | tests/test_pathlynks_login_case_assertions.py (3 scenario tests) | restore cases.jsonl from base 4ce91ea8 in the copy | "3 failed, 3 passed" in the copy |

## Live browser evidence
Not UI-touching - no surface changed. Changed paths: src/autotester/stages/grade.py, src/autotester/stages/grade_images.py, src/autotester/stages/run_case_pipeline.py, projects/pathlynks/cases.jsonl, tests/test_grade_negative_path.py, tests/test_pathlynks_login_case_assertions.py. The strings asserted were read from the recorded screenshots of run-01M58F744J7R3CB99CMH9S7FQ3 (projects/pathlynks/runs/run-01M58F744J7R3CB99CMH9S7FQ3/case_efaed2c0eb91/04-step04-click.png, case_7a978722a38c/02-step02-click.png, case_093f5070df79/04-step04-click.png); no new live run was made.

## Status: ready-for-check
