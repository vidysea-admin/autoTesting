# Verdict - t168-damage-control-report, merge reconcile 1, seat B
Cycle checked: merge-reconcile 1
Head: 2425506a (verified with git; worktree clean). Repair base: 4b93d952 (ancestor). Policy-Version: proportional-verification/2026-10-10.9. Date 2026-10-11.

## Plan
Repair-scope check of a master merge (no feature change intended). Emphasis: behavioural collisions from t178, at733, t155, at792. Steps: re-run DC1-DC4 verify commands; read the master-side diff for anything the report reads or renders; route/CLI registration; ruff + doctor; one falsification of secret redaction in a copy. No browser (no UI diff vs the unit's own change).

VERDICT: PASS
SCOREBOARD: 4/4 criteria met, 0 invariants touched
TIER: M (merge reconcile of a multi-file unit; dual-trigger line cites src/autotester/stages/unified_report.py:265, redaction)
FAILURES: none
CRITERIA (own re-run on 2425506a, `uv run --project <worktree> pytest -p no:xdist -o addopts=`):
- [DC1] met: `tests/test_unified_report.py -k dc1` 1 passed (c1.txt)
- [DC2] met: `-k dc2` 1 passed (c2.txt)
- [DC3] met: `-k "one_invocation or regression_reads or no_baseline"` 3 passed (c3.txt)
- [DC4] met: `tests/test_unified_report.py tests/test_unified_report_secrets.py -k dc4` 8 passed (c4.txt)
- Whole unit files plus cli_surface, cli_release, ui_report, cli_advice_resolves: 118 passed (files.txt). ruff: All checks passed. autotester doctor: clean.

SEMANTIC COLLISION READ (master-side src diff 97465d5d^1..HEAD, read in full for the touched owners): none found.
- The report reads release records, results, verdicts, runs, cases, persona, crawl and crawl network via ProjectStore, plus crawl_summary. It never reads failure bundles, so t178's schema/failure_bundle.py and stages/failure_bundle.py containment changes do not reach it.
- store.list_cases(): t178 added an optional `priorities` arg, default None returns the same rows; the report's call (unified_report.py:179) is unchanged in behaviour. Case gained `priority` (default p2); the report schema does not carry it.
- crawl_report.py: `_clean` moved to core.excel (same function, aliased); the unified report does not use it, the xlsx path is untouched by this unit.
- Redaction: `scrub_obj(report.model_dump(mode="json"))` at unified_report.py:265 scrubs the whole dumped object, so any field t178/t155 might add to what the report embeds is covered by construction; the report schema is its own and gained nothing from master.
- ui/helpers.py: master's new Host allow-list (AT-758) applies to every route; damage-report route answers 404 "no project" on a loopback Host and 403 on a foreign Host (routes.txt), consistent with every other route.
- Registration: damage-report is mounted as a sub-router of routes_report (routes_report.py:29), unique path in app.openapi(), no shadowing; `autotester --help` lists release-report and `release-report --help` resolves. test_cli_advice_resolves (both advice sites, count 24) passed.

FALSIFICATION (DC4, copy outside the worktree, import path printed in falsify-import.txt, copy deleted afterwards): in the copy `tests/test_unified_report_secrets.py -k dc4` was 7 passed (green); after replacing `_load_redactor(store).scrub_obj(report.model_dump(mode="json"))` with the unscrubbed dump at stages/unified_report.py:265 it went 2 failed, 5 passed: test_dc4_report_object_is_clean_before_it_is_rendered (assertion `form not in dumped`, secrets test line 116) and test_dc4_special_character_secret_is_absent_raw_and_escaped_in_html_and_cli. Red on the secret assertion, not an import error. Worktree status stayed clean.
CAPABILITY-COVERAGE: 1/1 row reproduced (DC4 redaction); DC1-DC3 keep their recorded falsifications (their input files are unchanged by the merge)
LIVE-BROWSER: not-applicable (no UI file changed by this reconcile; route resolved by request)
ISSUES-WRITTEN: none (PASS, no PROPOSED-ISSUE)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The merge changed nothing the unified report reads or renders; its behaviour on 2425506a matches the passing criteria, redaction still scrubs the whole object and is falsifiable. Wall time passed 5 min because test runs (118-test file set 87 s, dc4 25 s) were sequenced with my reading of the master diff.
Metrics: start=2026-10-11T04:03:51Z end=2026-10-11T04:21:00Z wall_min=17 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1030 mutants=0 defects_unit=0 defects_6c=0 slow: test runs and master-diff read 17 min
