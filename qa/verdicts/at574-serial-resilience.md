# Verdict — at574-serial-resilience

**Date:** 2026-09-25 · **Head checked:** e4611c7 (fix c0a11b4, base master 5444604) · **Cycle checked: 1** (manifest Fix cycle: 1 of 3) · **Issues addressed (claimed):** AT-574

```
VERDICT: PASS
SCOREBOARD: AT-574 expected clause met (a grader or run_case crash on one serial case: every case + the Run saved, no 500); ui-run RU1-RU4 hold; core invariants hold
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (A, B), each in its own throwaway copy; green before, red on exactly the named tests after
LIVE-BROWSER: qa/evidence/browser-at574-serial-resilience-2026-09-25-checker/report.json
ISSUES-WRITTEN: AT-576, AT-577 (both pre-existing on master, not charged to this unit)
EXECUTOR: claude-sonnet-subagent (checker: claude-opus-session, checker seat)
EXPLANATION: Live, on the serial path the planner chose by itself (n=1, budget), a judge outage on one case now yields that case completed + INCONCLUSIVE "grader failed" while the rest PASS and the run redirects (303); the tests prove the run_case-crash and entry-case shapes. Mode D also exposed two older, serious defects in the default serial path that no unit test can see because they fake BrowserSession: any run mixing an entry case with ordinary cases 500s (AT-576, reproduced identically on master), and every serial case inherits earlier cases' evidence, so judges grade on other cases' screenshots (AT-577). Neither is this unit's code; both should be the next units.
```

## Maker's question: the test retargeting

Sound. In `test_ui_runs.py`, `test_ui_runs_parallel_trace.py` and the `test_coverage_wiring.py` helper, each fake is renamed and re-patched from `run_and_grade_case` to `run_and_grade_case_resilient`. Fixtures, fake bodies and every assertion are unchanged. The patch point moved one level down, so the new `_run_and_grade_resilient` wrapper runs for real around the fake. No test was deleted.

## What I re-ran

- Targeted (copy): `23 passed` · `ruff` clean · `doctor` clean.
- **Every non-browser test file** (copy): `2 failed, 1558 passed, 5 skipped`. Both failures are environmental and pass in the worktree (`3 passed`):
  - `test_uploaded_recordings_are_gitignored` needs `.git`, which copies lack.
  - `test_flake_probe_real_process::…kills_a_real_hung_process…` is a real-process timing test that ran under ~0.6 GB free RAM (suite 7 min vs ~4). The unit doesn't touch flake_probe.
- Row A (serial non-entry branch back to the bare `run_and_grade_case`): `3 passed` -> fails `test_a_grader_crash_…` (`RuntimeError: boom grading`) and `test_a_run_case_crash_…` (`boom running the case`); the entry test survives, as claimed.
- Row B (outer `try/except` removed): `3 passed` -> fails `test_a_run_case_crash_…` and `test_an_entry_case_crash_…` (`boom entering`); the grader test survives, as claimed.
- Diff scope 5444604..e4611c7: 6 files, all listed; removed lines are only the retargeted fakes, the now-unused `run_and_grade_case` import, and docstring rewording in `_run_cases_serially`/`trigger_run`. `run_and_grade_case` stays in `stages/run_case_pipeline.py` for CLI callers.
- **Mode D**, two live runs (details in report.json):
  1. With an entry case: 500 from `BrowserSession.start` in `_run_entry_case` (nested sync Playwright). **Identical on master with no outage** -> AT-576, pre-existing.
  2. All non-entry, outage on one case: 303, 3 results + 3 verdicts, outage case `completed` + INCONCLUSIVE naming the grader failure, 30/30 images render, no secret in the run dir or DOM -> this unit's claim holds live. Evidence accumulation across serial cases -> AT-577, pre-existing.

## Debt noted (not blocking)

`_run_entry_case` and the shared serial session call `session.start()` outside the new guard, so a browser-launch failure still 500s. Guarding it would only hide AT-576; the real fix is AT-576's.

## Status: PASS
