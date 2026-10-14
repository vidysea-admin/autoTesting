# Manifest — budget-judge-time

**Contract:** qa/contracts/parallel-run.md PR7; qa/contracts/consent.md CN10 (bounds mean one thing; C12 fail closed)
**Goal task:** none (defect from the T-169 real PathLynks run; analysis: `check/t169-real:qa/evidence/t169-real/inconclusive-analysis.md`)
**Status:** checked-PASS
**Fix cycle:** 0
**Date:** 2026-10-13

## Defect
13 of 30 cases never launched (INCONCLUSIVE, 0.0 s, "run budget exhausted: wall_clock_s"): the 600 s clock counted serial judge latency; 17 executed cases used ~195 s of browser time.

## Contract reading
`RunApproval.wall_clock_s` is documented as "how many seconds this run may take in total" (`schema/approval.py`), and PR7/CN10 bound the AGGREGATE. So its semantics were NOT changed. Judge time is accounted in a separate, bounded allowance instead; the conflict is filed in `qa/feedback-inbox.md`.

## Change
- `stages/run_budget.py`: `RunBudget(approval, judge_allowance_s=0.0)`; `judging()` context manager excludes grading time (union of overlapping workers) from the approval clock, up to the allowance; grading beyond it is charged to the clock, so total time <= `wall_clock_s + allowance`. `judge_allowance_s(cases)` = 45 s per case; `wall_clock_request_s` adds it so the consent request covers the whole run. Default allowance 0 keeps the old behaviour.
- `stages/run_case_pipeline.py`: both `grade()` calls in `run_and_grade_case` / `_resilient` run inside `_judging(session)` (no-op without a budget).
- `stages/run_launcher.py`: `RunBudget(approval, judge_allowance_s=judge_allowance_s(cases))`.
- Unrun cases still stop with `wall_clock_s` -> INCONCLUSIVE (fail closed), unchanged.

## Tests
`tests/test_run_budget_judge_time.py` (new): judge latency does not starve later cases; browser time still capped; over-allowance judge time charged; overlap counted once; no allowance = old semantics; request includes allowance; pipeline scope. Also run: parallel_run_approval, run_case_pipeline(+resilient), run_launcher(+approval), team_run_launcher, ui_runs_live_case_approval, ruff, doctor.

## Not done
Cause 2 (grade_note_guard false holds) and the "not run: budget" run-summary surfacing are out of scope.

## Verify
`uv run pytest` (named files above), `uv run ruff check src tests scripts`, `uv run autotester doctor`
