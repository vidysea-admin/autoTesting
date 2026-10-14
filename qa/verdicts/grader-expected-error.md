# Verdict - grader-expected-error

**Cycle checked:** 1
**Head checked:** f5723188
**Verdict:** FAIL

## Mechanical (all green, rerun after rebase)
pytest -k "grade or schema or golden or pipeline": 427 passed. ruff clean. doctor clean. merge-tree vs 951cbd75: no conflicts. No file over 300 lines (run_case_pipeline.py 299). Schema: `expects_error` defaults False, extra=forbid untouched, old artifacts load.

## Findings (false-PASS)
1. (a) HELD: best case (expects_error False): "login failed with invalid password error as expected" -> failed, invalid, error. Good.
2. (c) FAIL: with expects_error=True, `failure_terms` returns [] for "invalid total shown correctly formatted", "wrong amount charged correctly", "denied access properly but data leaked". The cues `correctly`/`properly` are generic adverbs, not statements that the error was the expected outcome, so any clause with "wrong/invalid/incorrect" plus "correctly" is exempted.
3. (b) FAIL (by inspection of `_ERROR_EXPECTED`): bare keyword regex over title/rationale/step text; a worst case titled "user should not see an error when ..." sets expects_error=True, and then "error shown as expected" passes. No negation handling.
4. Exemption scope is clause-wide, not adjacent to the term: "error ... as expected" is exempt even when a different defect claim shares the clause (non-lexicon words like "leaked").

## Required fix
Drop `correctly`/`properly` from the cue (keep expected / as intended / as designed), or require the cue within a few tokens of the term. Add negation handling ("not/no/without ... error") in `case_expectation`. Add tests for the cases in 2 and 3.

---

# Cycle 2

**Cycle checked:** 2
**Head checked:** 4903ba07
**Verdict:** FAIL (narrow)

## Mechanical (green)
pytest -k "grade or schema or golden or pipeline": 440 passed. ruff clean. doctor clean. merge-tree vs 951cbd75: clean. No file over 300 lines (run_case_pipeline.py 299).

## Cycle 1 findings
(a) held; (c) fixed ("invalid total shown correctly formatted" -> invalid; "wrong amount charged correctly" -> wrong); "denied access properly but data leaked" -> denied, leaked; "error 500 returned, expected a success page" -> 500; canonical "error message for invalid email appeared as expected" passes. (b) negation now handled in expects_error.

## New false PASS (expects_error=True, note returns no terms)
1. "expected error not shown, a generic error appeared" - the cue "expected" precedes a negated expectation; the error the case wanted did not appear. Same for "Error was not displayed, expected". These are the classic way a negative case FAILS, so they must hold.
2. "access denied to admin page, expected for a guest but also denied to the owner" - cue in the clause covers a second, unexpected denial.
3. "error appeared as expected, form was submitted anyway" and "denied as expected but the record was deleted" - the clause continues with a contrary outcome after "but/anyway" (delete not in lexicon).
4. "rejected the valid card as expected" is exempt (semantically a defect on a valid input); lower severity.

## Required fix
Do not apply the cue when the term or cue is negated or followed by not shown/displayed/absent/missing within the clause; split clauses at "but", "also", "however", "anyway" so a cue only covers its own sub-clause. Add tests for 1-3.

---

# Cycle 3

**Cycle checked:** 3
**Head checked:** d33033c2
**Verdict:** PASS (with residual risk recorded)

## Mechanical (green)
Based on 951cbd75. pytest -k "grade or schema or golden or pipeline": 450 passed. ruff clean. doctor clean. merge-tree vs 951cbd75: clean. No file over 300 lines (run_case_pipeline.py 299).

## Re-run of cycle 1 and 2 phrases (expects_error=True)
All now held: invalid total / wrong amount / denied...leaked / error 500 / "expected error not shown, a generic error appeared" / "Error was not displayed, expected" / double denied / "submitted anyway" / "denied ... but ... deleted" / "rejected the valid card". The canonical "error message for invalid email appeared as expected" still passes. Best case (flag false) still held.

## New probes that still pass (expects_error=True, no marker, no main-lexicon word)
"error shown as expected and page went blank"; "...then redirected to another user's profile"; "rejected as expected; duplicate entry created"; "...and the form data was lost"; "...and the admin panel opened"; "...and the session was exposed"; "...and user logged in"; "rejected as expected and the order was placed".

## Reasoning
Each passes only because the defect is stated in words the main lexicon does not hold either (blank, lost, exposed, duplicate, opened, logged in, placed). The exemption removes only error/denied/reject*/input-invalid, requires expects_error AND defect_observed=false AND "as expected/intended/designed" AND no contrary marker. The residual is the pre-existing open-ended lexicon limit, not a new hole in the exemption. Accepted; recommend a later lexicon pass adding blank/lost/exposed/duplicate/redirected-to-another.
