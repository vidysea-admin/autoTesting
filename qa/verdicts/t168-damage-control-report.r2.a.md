# Verdict - t168-damage-control-report, seat A (blind dual check), 2026-10-11

Cycle checked: 2
Sha checked: 4b93d952 (product 6ef7f14b, repair base fb47735c ancestor-verified, master 476666d6 merged at ccc86dd0)
Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting. Verdict path: qa/verdicts/t168-damage-control-report.r2.a.md. Checkpoint: qa/checkpoints/t168-damage-control-report.r2.a.md. Evidence: qa/evidence/t168-damage-control-report-r2-A/

## Plan
Repair check, tier L (dual-trigger security, stages/unified_report.py:265 present). Re-judge DC4; DC1-DC3 inputs (stages/unified_report.py, unified_report_render, schema) are untouched by the repair except the error path in `stages/unified_report.py`, `cli_release.py`, `routes_unified_report.py`, so DC1-DC3 keep their recorded result and were re-run only inside the 19 unified tests. Reads: repair diff fb47735c..72a7ecae in full, whole-unit diff 476666d6..4b93d952 (scope scan). Fan-out: one read-only sub-checker for the three rulings; the full suite and the DC4 counterexample sweep ran by this coordinator.

VERDICT: PASS
SCOREBOARD: 4/4 criteria met (DC4 re-judged; DC1-DC3 unchanged inputs, pass in the 19-test run), invariants: none touched
TIER: L (security class: redaction of report output; dual-trigger stages/unified_report.py:265)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 repaired-criterion falsification reproduced
LIVE-BROWSER: not-applicable (repair changed no rendered markup; the new 500 page is covered by TestClient in test_dc4_route_error_path_is_an_error_status_without_the_stored_secret)
ISSUES-WRITTEN: none (dual coordinator)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## DC4 - met
- Repair read in full (stages/unified_report.py:52-97, 243-281; cli_release.py:106-111; routes_unified_report.py:27-35, all read in this check). Every non-`ReportUnavailable` exception in `build_report` becomes `ReportUnreadable`, whose text is fixed wording plus the stored file's last two path parts and field names that match an identifier regex, passed through the project `Redactor`, raised `from None`. `filestore.read_json` wraps pydantic text as `<path>: ...`; `_where` takes only the path for `ValueError`, so pydantic's `input_value` never enters the message.
- Acceptance: `pytest tests/test_unified_report.py tests/test_unified_report_secrets.py -k dc4` in a copy of 4b93d952 -> 8 passed; whole two files -> 19 passed.
- Falsification (one hunk, copy): `raise ReportUnreadable(str(exc))` instead of `_unreadable(store, exc)`; green before (3 passed), red after on `input_value="p&ss<w>o'rdQ9"` in the CLI output, the message, and the route body.
- My own counterexamples (`fuzz.py`): 362 single-field mutations over all 11 stored files of a seeded project (field := secret, extra key := secret, extra key := undeclared token-shaped name). 0 leaks of raw, HTML-escaped or URL-encoded forms in CLI/build/export output or the written artifact; 0 untyped exceptions; cause chain suppressed. A corrupt project.json gives route 500 "Internal Server Error" and a fixed CLI line.
- Success path unchanged since cycle 1 (object scrub then render); scanner subprocess assertion passes.

## Rulings requested
1. Advice-site registration: CORRECT and NOT a protected test change. The advice string is stages/unified_report.py:125 ("a release is started with `autotester release`"); `release` is registered at cli.py:294; the test passes (31 passed). The diff is two added lines (one frozen site, count 21 -> 22): no assertion deleted or weakened, no threshold lowered, no skip. Adding a site is the registry's documented procedure.
2. routes_report.py merge: nothing from master dropped. Master 299 lines, result 297. Differences from master are only the collapsed `ui.helpers` import tuple (same three names) plus this unit's `routes_unified_report` import and `include_router`; master's `run_queue_view` import and queue-panel lines are identical in the result.
3. cli.py at exactly 300 lines: passes. doctor.py:20 `MAX_FILE_LINES = 300`, :80 `lines > MAX_FILE_LINES`; `uv`-less doctor run on a clean copy printed `doctor: clean`.

## Diff scope (4c)
Repair diff: only cli_release.py, stages/unified_report.py, routes_unified_report.py, the new secrets tests; nothing removed. Whole unit vs master: 14 files, all in the manifest's What changed, plus `qa/manifests/t167-release-regression.md` (a one-line status flip to checked-PASS arriving with the master close-out, maker bookkeeping, not product code). No removed def/class/route/test.

## Full suite (seat A's one run, sharded, 4 shards, collect proof ok 3397)
3374 passed, 4 failed, 19 skipped. Known: AT-792 test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen (red alone), AT-858 test_hook_prints_the_report_and_exits_zero_on_a_healthy_log (passed alone: load), test_env_example_documents_every_key_the_code_reads. Not on the maker's list: tests/test_hosting_config.py::test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere. I ran it alone on a `git archive` of master 476666d6: it fails identically (expects D:/autoTesting/src/autotester, gets the archive path, an archive-copy artefact of the editable install), so it is not this unit's.
PROPOSED-ISSUE: {"severity":"low","feature":"hosting","title":"test_healthz_source_root_is_the_package fails on any git-archive copy of master 476666d6 (editable install resolves to D:/autoTesting)","evidence":"pytest of the node on archive of 476666d6: AssertionError D:/autoTesting/src/autotester != <archive>/src/autotester","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"damage-control-report","title":"routes_unified_report.py calls shared _load_project_or_404 outside the typed handler; a corrupt project.json is an untyped 500 whose server-side traceback carries pydantic text (response body is clean)","evidence":"ui/helpers.py:165-171 and routes_unified_report.py:24 read in this check; probe: route 500 'Internal Server Error', CLI fixed text","found_by":"checker-unit"}

EXPLANATION: The repair closes the DC4 error path: stored-data exception text no longer reaches CLI, route or build_report output, and 362 single-field corruptions found no leak. The merge, the advice-site registration and the 300-line cli.py are sound. One red outside the maker's list reproduces identically on master and is not this unit's.
Metrics: start=2026-10-11T00:09:13Z end=2026-10-11T00:25:00Z wall_min=16 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=0 mutations=1 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=950 mutants=0 defects_unit=0 defects_6c=0
