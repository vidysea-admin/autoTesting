# Verdict - t200b-scheduled-test, repair check, seat A (dual check), suite retry

Cycle checked: 1
Head: 371eb7f6 (verified with `git rev-parse --short=8 wave/t200b-scheduled-test`; unchanged); product sha 6d6bc318; Repair base 0d9a3b56.
Policy-Version: proportional-verification/2026-10-10.9
Retry: 1
Earlier same-cycle verdict (BLOCKED-PROCESS, every criterion met, full suite owed): `qa/verdicts/t200b-scheduled-test.r1-1.a.md`. Its per-criterion evidence stands (nothing changed in the unit); this retry ran only the owed full suite.

## Plan
Tier L, dual (dual-trigger `schedule_gate.py:74`). Retry scope: the one owed check, the checker full suite on 371eb7f6, then judge each red. No other check re-run (evidence identity unchanged: code sha 6d6bc318, same tree, same lock file; see checkpoint).

VERDICT: PASS
SCOREBOARD: 4/4 criteria in scope met (TS1 purge clause, TS5, TS6 guard, TS7 tick side; evidence in r1-1.a.md), the rest of TS1-TS4 green in the full suite; 0 invariants breached.
TIER: L (security `src/autotester/stages/schedule_gate.py:74`, a gate that can mint a signed approval and write the key to the repo-root `.env`)

## Full suite (suite_runs=1)
Command: `python D:/ai_os/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting --ref 371eb7f6 --shards 4 -- -o addopts=` (no -x). Collect proof ok: 3484 collected = union = ran, 252 files. Counts: 3458 passed, 20 skipped, 6 failed. Wall 1037 s (run 904 s, collect 56 s, isolated re-run 72 s). Lock: attempt 1 waited 901 s and got exit 3 (holder PID 32092, D:/hei-sweep suite, not ours, not touched); attempt 2 took the lock at once (`blocked_s` 0.0) and ran. Evidence: qa/evidence/t200b-scheduled-test-r1-A/suite-r1-1-summary.json, suite-r1-1-run.log, suite-r1-1-lockwait-attempt1.log.

Every red, classified (this unit's diff since the merge-base 771e0255 touches none of the six test files nor the product code they run; `git diff --name-only 771e0255 wave/t200b-scheduled-test` has no reconcile, hosting, hooks, mc_, redact or video path):
- Still red alone, known on master:
  - `test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen` = AT-792. Same failure as the ledger row (`step.narration` None, expected 'type your email here', test line 125). The branch does not contain master commit 05eb07bf (`merge-base --is-ancestor` says no); I ran it on a master archive (0ffee6ed): passes. Predates this unit, fixed on master.
  - `test_hosting_config.py::test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere` = AT-921 (child process imports the editable install at D:/autoTesting/src, not the copy; assertion at test line 40). On the master archive 0ffee6ed it fails the same way.
  - `test_mc_sessionstart_loop_status.py::test_hook_prints_the_report_and_exits_zero_on_a_healthy_log` = AT-858 family (the powershell hook subprocess; sharded run shows `TypeError: argument of type 'NoneType'`, the AT-858 signature). It did not pass alone here: on the master archive 0ffee6ed it also fails alone (`TimeoutExpired` after 60 s on `qa/hooks/mc-sessionstart.ps1`). So it is red on master on this machine today, not caused by this unit; the hook file is untouched by the diff.
- Passed alone, load-induced (rule: absent from `failed_still_failing_alone`; the assertion is on elapsed time or a timeout; no unit file touches the test or what it times). Load flakes, low ledger row below, no HOLD:
  - `test_redact_wrap_perf.py::...500kb_corpus`: 10.54 s vs a 3.0 s bound, CPU 100% at suite start = AT-725 (already open).
  - `test_mc_sessionstart_loop_status.py::test_hook_prints_unhealthy_line_only...`: 60 s subprocess timeout = AT-750(b) / ISS-t151-target-discovery-6.
  - `test_video_parallel_sweep.py::test_two_sessions_sharing_a_run_dir...`: 'A never finished closing', thread timing = AT-750(d).
- AT-920 and AT-924 were not red in this copy (no action).
No red outside the known list; none is caused by this unit's files.

FAILURES: none
CAPABILITY-COVERAGE: 7/7 repair falsification rows reproduced by seat A (r1-1.a.md); unchanged, no re-run owed
LIVE-BROWSER: not-applicable (no UI surface changed)
ISSUES-WRITTEN: none (dual coordinator; PASS has no side effects)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

PROPOSED-ISSUE: the four low rows P1-P4 in `qa/verdicts/t200b-scheduled-test.r1-1.a.md` stand unchanged (import-guard obfuscated dynamic imports; purge on a torn foreign row; purge crash hygiene; reader racing a purge).
PROPOSED-ISSUE: {"severity":"low","feature":"suite-health","title":"test_mc_sessionstart_loop_status healthy_log fails alone on a master archive (0ffee6ed) today with a 60 s powershell hook timeout, so AT-858 'passes alone' did not hold on this machine under load; record the node's baseline red","evidence":"qa/evidence/t200b-scheduled-test-r1-A/suite-r1-1-summary.json; master-archive single-node run 2026-10-11 (1 failed in 82.99s, TimeoutExpired mc-sessionstart.ps1)","status":"open"}

EXPLANATION: The owed full suite is green apart from six reds, all shown as pre-existing on master or as load flakes of timing tests, none touching this unit; combined with the r1-1 per-criterion evidence every criterion is met. One thing differs from the dispatch's expectation: the AT-858 healthy_log node did not pass alone; it timed out on a master archive as well, so it is not this unit's. Blocked time was waiting on D:/hei-sweep's suite; I did not touch its lock.
slow: suite lock wait 15 min (blocked, excluded from wall_min); suite run 17 min
Metrics: start=2026-10-11T03:59:49Z end=2026-10-11T04:50:00Z wall_min=35 agent_min=unavailable blocked_min=15 suite_runs=1 repeat_runs=0 mutations=0 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=2100 mutants=0 defects_unit=0 defects_6c=0
