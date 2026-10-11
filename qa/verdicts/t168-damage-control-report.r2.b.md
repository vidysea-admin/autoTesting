# Verdict - t168-damage-control-report, cycle 2, coordinator B (blind dual check)

Cycle checked: 2
Checked sha: 4b93d952 (branch `wave/t168-damage-control-report`; product sha 6ef7f14b, `git diff 6ef7f14b 4b93d952 -- src tests` empty)
Repair base: fb47735c (verified an ancestor of 4b93d952). Integration base for scope: 537bd7f9 (`git merge-base master 6ef7f14b`).
Policy-Version: proportional-verification/2026-10-10.9
Date: 2026-10-11. Seat B; read no r2 A material.

## Plan
Repair check, tier M (declared; no tier change). Re-judge DC4. Re-run DC1-DC3 via `tests/test_unified_report.py` (the repair edits `stages/unified_report.py`, which holds every loader). Read the repair diff in full (72a7ecae..6ef7f14b on the unit files) and scan the whole-unit diff for out-of-scope files. One falsification for the repaired criterion. Own attack on DC4 on all three output paths (stage, UI route, CLI). Affected tests for (fix diff + merge-conflict files). Seat A owns the full suite; none run here.

## Block
VERDICT: PASS
SCOREBOARD: 4/4 criteria met (DC1-DC4), invariants: none touched beyond C5/RE5 (hold)
TIER: M (reading five evidence owners, new report modules, CLI and HTTP surface; dual-trigger line cited: stages/unified_report.py:265, redaction)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 repaired-criterion row reproduced (DC4), plus checker's own 2 mutants and the guard-entry falsification
LIVE-BROWSER: not-applicable (this repair changed no rendered markup; route covered by TestClient, status and body asserted in attacks)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines below only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent; manifest Executor is the maker build subagent, so self != executor)
EXPLANATION: DC4 holds on the success path and now on the error path. I attacked the stage, the route and the CLI with six secret shapes and 468 malformed stored-file variants and found no raw, escaped or `input_value` leak and no uncaught CLI exception. The repair diff is confined to the declared files, the one guard-test edit is additions-only and its falsification is red by assertion.

## What I re-ran (all my own commands, in a `git archive 6ef7f14b` copy under scratch, one pytest process at a time, `-p no:xdist`)
- DC1-DC3: `tests/test_unified_report.py` 12 passed.
- DC4: `tests/test_unified_report_secrets.py` 7 passed (green-before in the copy).
- Scoped regression: `test_cli_advice_resolves.py` 31, `test_cli_release.py` 4, `test_ui_report.py` 15, `test_ui_report_no_runs.py` 4, `test_goal_contract_registration.py` 1, `test_run_trace.py` 10, `test_ui_video_route.py` 6, `test_release_gate.py` 4: all passed (`-m "not harness"`). Output: `qa/evidence/t168-damage-control-report-r2-B/scoped-tests.txt`.
- Not run: the other files the master merge changed (about 190, seat A's full suite covers them); I ran only those importing `routes_report.py` (the one conflicted file) or `cli_release.py`.

## DC4 attacks (script: `qa/evidence/t168-damage-control-report-r2-B/test_attack_b.py`; logs `attack-success-path.log`, `attack-error-paths.log`)
1. Success path, 6 secret shapes (`a.b*c(d)[e]{f}$^|x\y`, `pässwörd✓€`, `x<b>&amp;"z`, identifier-shaped `Hunter2Pass`, `tok=abc/def+ghi==`, `p&ss<w>o'rdQ9`), the secret planted in every text field. CLI `release-report`, route `GET /projects/demo/damage-report` and `?run=rel1`, and `scripts/check_no_secrets.py` as a subprocess on the artifact. Result: all exit 0 / 200, scanner `0 leak(s)` for all six, no raw, HTML-escaped, percent-encoded or JSON-escaped form in the HTML, CLI output or route bodies. (First run flagged `Hunter2Pass` only because pytest's own tmp dir name contained it; rerun with a neutral dir was clean.)
2. Error path, malformed stored inputs. For each of the 11 stored json/jsonl files of a seeded project (project, cases, flow_plans, flowspec, portal_persona, crawl, crawl network, run result, verdict, release, scope) and 3 secrets: extra key named by the secret, every field set to the secret, one field at a time, nested key, truncated JSON ending in the secret, secret-only content, garbage line. 156 variants per secret, 468 total. Each run through the CLI, both route forms and `build_report`. Result: 0 leaks, 0 `input_value`, 0 uncaught CLI exceptions. Corrupt records give exit 1 / HTTP 500 with the fixed text naming at most the last two path parts; corrupt `project.json` gives `cause ValueError`; files the report never reads (`flow_plans`, `flowspec`, `scope`) still give a normal report.
3. Direct attack on `_where`/`_unreadable` (`direct_unit_attack.py`): a ValidationError whose location holds an identifier-shaped secret as a dict key is masked to `[REDACTED]:DEMO_PASSWORD`; with `_load_redactor` raising the message falls back to `cause ValidationError`; KeyError/RuntimeError/OSError/ValueError carrying the secret and a path segment equal to the secret all come out clean. `__context__` of the new error still holds the original exception but `__suppress_context__` is True (a standard traceback does not print it).

## Falsification (one per repaired criterion; green before in the copy, red after; copies discarded)
| Criterion | Edit in a copy | Before | After |
|---|---|---|---|
| DC4 | `_where` ValueError branch returns `str(exc)` | 7 passed | 3 failed: CLI, route and build_report error-path tests; assertion `'input_value' not in ...` fired |
| DC4 | `build_report` re-raises the raw exception instead of `_unreadable` | 7 passed | 2 failed: CLI and build_report error-path tests |
| guard | `("stages/unified_report.py", "release")` removed from `EXPECTED_SITES` | 31 passed | `test_no_advice_site_can_vanish_unnoticed` red by assertion, `new: [('stages/unified_report.py', 'release')]` |
Output: `falsification.txt`.

## Diff scope (4c)
Repair diff (72a7ecae, 6ef7f14b) read in full: `stages/unified_report.py`, `cli_release.py`, `ui/routes_unified_report.py`, `tests/test_unified_report_secrets.py`, `tests/test_cli_advice_resolves.py`, the `routes_report.py` merge resolution. Whole unit vs master merge-base 537bd7f9: 13 files, all declared (`docs/MAP.md`, new report modules, cli.py +1, cli_release.py +22, routes_report.py, project_view.py +1, the two test files, test_cli_advice_resolves.py, the manifest). Nothing deleted or renamed. The `test_cli_advice_resolves.py` change is one new tuple and 21 -> 22: additions only, the site is real (`stages/unified_report.py:125` names `autotester release`, a command the CLI resolves; the guard test passes). Ruling: accepted, not a loosening.

## PROPOSED-ISSUE (non-blocking, none block this PASS)
PROPOSED-ISSUE: {"severity":"low","feature":"damage-control-report","title":"Percent-encoded secret in a stored network URL survives into the unified report","evidence":"checker attack test_percent_encoded_url_in_stored_network: stored `GET https://demo.test/g?pw=<quote(secret)> -> 500` appears verbatim in the report object and HTML; Redactor.scrub matches exact bytes only. Raw and HTML-escaped forms are masked and the DC4 scanner is clean. The stored row comes from capture (T-170), so the fix belongs there, or in scrub, not in this unit.","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"damage-control-report","title":"Route for a project whose project.json is corrupt falls through to the server's generic 500 and its traceback log","evidence":"`ui/helpers.py:165-171` `_load_project_or_404` calls `load_project()` outside the report's try; the HTTP body is clean (attack: 468 variants), but an unhandled ValidationError text with input_value goes to the server log. Pre-existing helper shared by every project page.","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"damage-control-report","title":"Route error-path test asserts only status >= 400, so it does not pin the fixed message","evidence":"mutant that re-raises the raw exception leaves `test_dc4_route_error_path_is_an_error_status_without_the_stored_secret` green (generic 500 hides it); the CLI and build_report tests do catch that mutant.","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"damage-control-report","title":"report_export private helpers imported across modules","evidence":"manifest finding, `stages/unified_report.py:40-47` imports `_failure_rows`, `_load_redactor`, `_needs_developer_detail`, `_repro_steps`, `_run_sort_key`; AT-582 owns report_export.py. Unchanged by this cycle.","status":"open","found_by":"checker-unit"}

Open questions for the maker (not failures): the new modules still await the owner's confirmation before merge (manifest note, checker ruling 1 of cycle 0); no browser or persona walk was run by the builder and none is required by this repair.

Processes: none of mine left running.

Metrics: start=2026-10-11T00:02:00Z end=2026-10-11T00:21:00Z wall_min=19 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1140 mutants=2 defects_unit=0 defects_6c=0
