# Verdict — t183-export-reason

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent (Mode A + Mode D) + orchestrator capability re-run

```
VERDICT: PASS
SCOREBOARD: RE6 met in both exports (criterion, reason and fix_hint for every failure, plus the case's steps as repro, FAIL/INCONCLUSIVE only); RE1, RE2, RE3, RE4 and RE5 hold, with no regression
FAILURES: none
CAPABILITY-COVERAGE: 8/8 rows reproduced on the named tests. Subagent (copy c183-1): PASS-gets-no-detail, INCONCLUSIVE-repro, existing-columns. Orchestrator (copy c183-rows, baseline 7 passed): failures_text → shows_failure_reason_and_fix_hint_for_a_fail red; steps_text → that test plus shows_repro_steps_for_inconclusive red; html detail "" → both html shows_* red; drop steps_html → test_export_html_shows_repro_steps red only; detail always True → both PASS-blank tests red. Restored 7 passed, byte-identical.
LIVE-BROWSER: qa/evidence/browser-t183-export-reason-2026-09-26-checker (visible Chromium against the real uvicorn app, isolated AUTOTESTER_ROOT: the run page, then report.html and report.xlsx downloaded through the UI links; FAIL reason, fix_hint, both criterion ids and repro steps visible; 2 detail blocks (FAIL + INCONCLUSIVE), none for PASS; xlsx has the 2 new trailing columns; 0 console errors, 0 HTTP errors)
ISSUES-WRITTEN: AT-594 (low: no test pins that Case.steps values rendered as repro never carry a raw secret)
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: Every new field goes through html.escape; a <script> payload in a reason renders as text. The first 9 Excel columns are byte-identical to a pre-fix base export. A 2-failure verdict is complete and readable in both the newline-joined cell and the HTML list. The exports add no scrub; a base copy shows the existing Notes column already passes text verbatim, so this is inherited, not new. The must-fix/suggestion split is not required by RE6, so the rest of AT-582 stays open.
```

Evidence: targeted 5 files 40 passed · ruff clean · doctor clean · `git diff --stat 7913387..HEAD` = report_export.py (+65/-2, 244 lines, longest function 42), tests/test_report_export_reason.py (new), manifest · nothing deleted.
