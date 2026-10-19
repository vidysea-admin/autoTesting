# Verdict - t136-negpath-assert (Mode A, single checker)
Date: 2026-10-19. Bound to D:/autoTesting/.worktrees/t136-negpath-assert. Cycle checked: 0. Policy-Version: proportional-verification/2026-10-19.16

## Check plan
Logic changed in the grader decision path plus 3 test-data rows: affected tests, falsification floor (1 per changed criterion C1, C2), diff-scope read (4c), behaviour probe of the guard, screenshot cross-check of the 3 asserted strings. No UI surface, no prompt text, no live run, no security/prod-write trigger.

VERDICT: PASS
SCOREBOARD: 3/3 criteria met (C1, C2, C12 as cited by the manifest; contract rows G3, G6, B11), 3/3 invariants hold (G6 unmet assertion still downgraded, B11 unbacked masked PASS still INCONCLUSIVE, C12 fail-closed)
TIER: M (grader decision path in grade.py:236-237,255-275 and rubric resolution run_case_pipeline.py:97-102; no security/auth/tenancy, no prod write; no raise)
FAILURES: none
CAPABILITY-COVERAGE: 3/3 floor rows reproduced (C1 two edits, C2 one) in copies, each green-before, red-after on the named test
LIVE-BROWSER: not-applicable (changed paths: src/autotester/stages/{grade,grade_images,run_case_pipeline}.py, projects/pathlynks/cases.jsonl, 2 test files; no UI surface)
ISSUES-WRITTEN: AT-1346 (low)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence
- Tests: `uv run pytest` on the 8 affected files (maker's C1/C12 set + C2 set) -> 264 passed. Maker pre-check counts (239 + 25) reproduced.
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> clean (file sizes grade.py 297, run_case_pipeline.py 298, within 300).
- Probe (real tree, 9 grade() calls, mock judge): INCONCLUSIVE for positive-path + met assertion + omitted defect_observed + expected-cue note; for negative-path with no met row; with an UNMET row; with a contrary marker ("but the page crashed"); with a generic error; with defect_observed=true; with a plain "invalid credentials error was shown" note. PASS only for negative-path + met assertion + omitted field + "correctly rejected as expected". The guard is unchanged for positive paths.
- rubric_for_case (run_case_pipeline.py:97-102, read here): raises expects_error to True in memory via model_copy only when the case expects an error; never persisted, never lowers (the else branch returns the stored rubric as is).
- grade_images rename: grep for `_met_assertions` in *.py finds no caller (only historical qa md text); grade.py:23 and grade_images.py:89 use `met_assertions`.
- Falsification in copies (scratchpad chk-t136-negpath/row1..row4, green-before 2/2, 2/2, 6/6, 2/2): row1 revert `return rubric` -> test_a_rubric_saved_before_expects_error_existed_still_gets_the_case_expectation red; row2 `expects_error and backed` -> `expects_error` -> test_without_a_met_assertion_the_missing_defect_field_still_holds_the_pass red; row3 cases.jsonl at 4ce91ea8 -> 3 of 6 in test_pathlynks_login_case_assertions red (empty visible_text); row4 `expects_error and backed` -> `backed` survives (see AT-1346).
- cases.jsonl: parsed against base, 7 rows, same id order; only step.expected of case_efaed2c0eb91 step 4, case_093f5070df79 step 4 and case_7a978722a38c step 2 changed; actions/targets/values byte-equal in value. Screenshots of run-01M58F744J7R3CB99CMH9S7FQ3 read directly: toast "Logged in successfully" (dashboard), toast and inline "Invalid credentials", inline "Email, mobile, or Student ID is required" and "Password is required". All three match.
- 4c diff scope: 7 files (3 src, cases.jsonl, 2 tests, manifest), all in What changed; nothing deleted or renamed except the intended `_met_assertions` -> `met_assertions`.

## Notes (not failures)
- AT-1346 (low, beyond the floor): the `expects_error` half of `expects_error and backed` is not pinned by a grade-level test; the code is correct.
- "Logged in successfully" is a toast that auto-dismisses; a slow capture could miss it (timing risk for case_efaed2c0eb91, not a criterion here).
- Review of manifest claim "positive-path ... keeps the guard exactly as before": true by probe; the named test of that claim passes with or without the expects_error condition.
slow: reading the 1,200-line checker protocol and the 4-copy falsification setup (conftest needs scripts/ on the path) about 4 min

Metrics: start=2026-10-19T09:54:59Z end=2026-10-19T10:08:00Z wall_min=13 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.16 check_s=780 mutants=1 defects_unit=0 defects_6c=0
