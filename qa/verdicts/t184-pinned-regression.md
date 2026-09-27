# Verdict — t184-pinned-regression

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent (Mode A + Mode D)

```
VERDICT: PASS
SCOREBOARD: AT-585 core met: pin_issue_as_case builds a REGRESSION_ANCHOR case tied to its issue; the schema validator holds; pinned cases cannot be deleted (store raises PinnedCaseError, UI route answers 409); pinned cases ride every regression run (ui/routes_runs.py::trigger_run runs store.list_cases() unfiltered); T-184 done_check passes
FAILURES: none
CAPABILITY-COVERAGE: 6/6 rows reproduced (copy c184-1, own venv, baseline 20/20): pinned→False, case_class→HAPPY, validator disarmed, store guard disarmed (both store and UI 409 tests red), guard over-fire (unpinned delete test red), each red on its named test; restored green
LIVE-BROWSER: qa/evidence/browser-t184-pinned-regression-2026-09-26-checker (visible Chromium against the real uvicorn app, isolated AUTOTESTER_ROOT: deleting the pinned case gives 409 and the case survives; deleting the unpinned case gives 303 and the case is gone; 1 console line = the browser's own 409 resource log, no JS error)
ISSUES-WRITTEN: AT-596 (medium: every UI 4xx renders as raw JSON, app-wide), AT-597 (medium: pin_issue_as_case has no UI or CLI caller)
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: 4c: the only pre-existing line removed is the delete_case docstring. It was condensed, not deleted: "Past runs/verdicts stay" keeps the guarantee, and a live probe deleted an unpinned case that had a run, result and verdict on disk and confirmed all three survive. routes_cases.py still states it in full. Caller: T-184 ("Known bug -> pinned p0 regression Case that runs in every regression run") and AT-585 ("issue -> pinned Case (priority p0) that is part of every regression run") are met at the mechanism level, and run-inclusion is real. But no human can pin a bug yet (the only caller is the test), so the entry point is filed as AT-597 for the next unit, disclosed in the manifest's Known limits. The pinned 409 renders as Chrome's raw JSON viewer. That is the app-wide pattern (no exception_handler anywhere in ui/), so it is filed as AT-596, not charged here. Validator probes: an issue id without pinned is rejected; old-shape case JSON without the new keys loads (pinned False); extra="forbid" still fires.
```

Evidence: targeted 9 files 107 passed, 1 skipped · ruff clean · doctor clean · case.py 128, issues.py 218, project_store.py 300, routes_cases.py 296 lines · no renames.
