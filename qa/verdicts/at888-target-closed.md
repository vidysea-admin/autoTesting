# Verdict: at888-target-closed
Cycle checked: 1
Result: FAIL (test gap only; code looks right)

Wired: yes. run_execution._run_cases_serially builds BrowserRecovery(session), and after _run_and_grade_resilient replaces the verdict with closed_verdict (INCONCLUSIVE, "browser closed") and calls recover(). Verdict is never FAIL/PASS. Cap 3 in recovery and again in VideoMixin._restart_session. session.budget is kept on the same session object, so budget still applies after relaunch.

Blocking: tests/test_ui_runs_target_closed.py re-implements the loop in a local _loop() helper. Nothing drives the real _run_cases_serially, so removing the wiring would not fail any test. Required: a test through _run_cases_serially (monkeypatch BrowserSession and _run_and_grade_resilient with fakes) covering: closed case saved INCONCLUSIVE, later cases run, relaunch cap, and budget exhausted after a relaunch.

Minor: the closed case's RawResult is still saved as ERRORED, and the judge still ran on it before being overwritten.

Checks: 4 scoped tests pass; ruff clean; doctor clean; merge-tree with master clean.

## Cycle 2
Cycle checked: 2
Result: PASS (head ed3ca854, checked detached)

Tests now call the real rx._run_cases_serially, monkeypatching only BrowserSession, run_and_grade_case_resilient and grade_errored_result. The real _run_and_grade_resilient wrapper converts the raised TargetClosedError. Assertions hold: case 2 INCONCLUSIVE "browser closed", c3/c4 COMPLETED, relaunch 1; cap gives exactly 3 relaunches then c5/c6 carry "relaunch limit". 4 tests pass, ruff clean, doctor clean, merge-tree clean vs master.
Residual: budget-after-relaunch is not asserted in a test (budget stays on the same session object by code reading).
