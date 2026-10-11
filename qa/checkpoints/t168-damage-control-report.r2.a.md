# Checkpoint - t168-damage-control-report, seat A, cycle 2 (checked 4b93d952, product 6ef7f14b)

Policy-Version: proportional-verification/2026-10-10.9. Environment: Windows 11, python 3.11 (uv), pydantic 2.13.5, checker scratch copies from `git archive` (never the worktree).
Code hashes (blob, 4b93d952): stages/unified_report.py deca508e59 - cli_release.py 95d638c742 - ui/routes_unified_report.py 63953c64dd - tests/test_unified_report_secrets.py cda6a4482d - tests/test_cli_advice_resolves.py b8c3e9016e. Lock: uv.lock 4882ef560a. Attribution: checker seat A (claude-sonnet-subagent), verdict `qa/verdicts/t168-damage-control-report.r2.a.md`.

| Check | Command / scope | Result |
|---|---|---|
| DC4 acceptance | pytest tests/test_unified_report.py tests/test_unified_report_secrets.py -k dc4 (copy of 4b93d952, collected 19, selected 8) | 8 passed |
| Unified tests | same two files, whole | 19 passed |
| DC4 error-path falsification | copy; `build_report` raises `ReportUnreadable(str(exc))`; 3 named nodes | green before (3 passed), red after on the named `input_value` assertions |
| DC4 counterexample sweep | `qa/evidence/t168-damage-control-report-r2-A/fuzz.py`, 362 single-field mutations of all 11 stored files (value := secret, extra key := secret, extra key := undeclared token) | 215 unreadable, 147 built, 0 leaks (raw, html, url forms), 0 non-typed exceptions |
| project.json corrupt | in-process TestClient + CliRunner | route 500 "Internal Server Error", CLI fixed text; no secret |
| advice registry | tests/test_cli_advice_resolves.py (sub-checker) | 31 passed |
| Full suite | shard_suite.py --ref 4b93d952 --shards 4, collect proof ok 3397 | 3374 passed, 4 failed, 19 skipped (see verdict) |
