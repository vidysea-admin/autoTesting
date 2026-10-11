# Verdict - t198a-zip-drive-intake, seat A, repair check (fix cycle 2), Retry 1 after BLOCKED-PROCESS

Cycle checked: 2
Retry: 1
Bound to: D:/autoTesting. Branch wave/t198a-zip-drive-intake, head dba80100 (verified with `git rev-parse --short=8`, unchanged). Repair base 3918a8aa.
Policy-Version: proportional-verification/2026-10-10.9 (the manifest pin). Dual check, coordinator A, blind to B. Date 2026-10-11.
Nothing in the unit changed since the earlier attempt. That attempt's verdict is `qa/verdicts/t198a-zip-drive-intake.r2-1.a.md`; it found every criterion met and was BLOCKED-PROCESS only for the missing full suite.

## Plan (retry)
Only the owed full suite was missing. All other evidence (repaired criterion, class-closure fuzz, breadth tests, two falsifications, 4c scope scan, affected tests: 174 passed) is kept by evidence identity: same head, same src and tests, same lock. See `qa/checkpoints/t198a-zip-drive-intake.r2.a.md`. No UI file changed, so no browser walk.

VERDICT: PASS
SCOREBOARD: criteria 1/1 repaired criterion met, criteria untouched by the repair keep their recorded result; invariants hold (none touched by the repair beyond the above). Floor met (2 falsifications, green before and red after).
TIER: L (untrusted archive intake and a request-body path: src/autotester/sources/zip_intake.py:214 `expand_zip`; dual-trigger line present in the manifest)

## Full suite (the one owed run, sharded, `suite_runs=1`)
Command: `python D:/ai_os/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting --ref dba80100 --shards 4 -- -o addopts=`. Evidence: qa/evidence/t198a-zip-drive-intake-r2-A/ (suite-full.txt, suite-summary.json, suite-tail.txt).
- Counts: 3742 passed, 7 failed, 19 skipped; collect proof ok (3768 collected = 3768 run, no duplicates or missing).
- Runner fix held: the `git archive` extraction finished in 42.7 s (the earlier attempt hung 30 min at 2,623 files). Lock: waited 74.6 s, then the tool reclaimed the dead lock of the earlier attempt (its pid had been reused by an unrelated process that exited). Extract 42.7 s, collect 204 s, run 896 s, rerun 318 s, overall 1461.7 s.
- Reds, each classified (isolated re-run by the tool, then single-test runs of my own on a `git archive` of this head and of master b0385cd6):

| red | alone | classification |
|---|---|---|
| test_hosting_deploy::test_env_example_documents_every_key_the_code_reads | failed | AT-920. Same message on this head and on master: undocumented keys SCHEDULE_GRACE_MINUTES and TICK_INTERVAL_S. The unit's only `.env.example` change adds AUTOTESTER_GWS_BIN and removes nothing |
| test_reconcile_schema::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen | failed | AT-792. Master b0385cd6 passes it, because master carries test-lane fix 238a1b7c, which this branch predates. With master's version of that test file dropped into a copy of this head it passes (1 passed). The unit's only `ingest.py` change is the declared rename `_project_redactor` to `project_redactor` |
| test_mc_sessionstart_loop_status::test_hook_prints_the_report_and_exits_zero_on_a_healthy_log | failed | AT-858 (same assertion line 164 on this head and on master). It also failed alone here, so the "passes alone" note for AT-858 did not hold on this machine today; the test file and the hook are untouched by the unit |
| test_hosting_config::test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere | failed | AT-921. The child process sees D:/autoTesting/src, identical assertion on master |
| test_redact_wrap_perf::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus | failed | AT-725 (load bound; master measured 22.6 s against 3 s today). It passed in my single-test run on this head. Files untouched by the unit |
| test_crawl_inventory_live::test_a_logged_in_crawl_maps_every_route_and_names_the_one_it_refused | passed | AT-750(a), load-induced; passed in the tool's isolated re-run and in my single-test run on this head |
| test_mc_sessionstart_loop_status::test_hook_prints_unhealthy_line_only_on_an_asleep_log_and_still_exits_zero | passed | load-induced; same file as AT-858; passed in the tool's isolated re-run and in my single-test run on this head |

All 7 are on the known list or are load flakes that pass alone. None is outside the known list. None is caused by this unit's files: its 43 changed files touch none of these tests or the code they exercise, except the one `.env.example` addition and the declared rename above, and both were shown not to cause the reds.

## Results kept from the earlier attempt (same identity)
- Repaired criterion (UTF-8 flag plus invalid UTF-8 name): 3 passed in a copy; the same bytes through `expand_zip` give a `failed` report and through the upload route a 200 with that row, no source row, nothing staged. MET.
- Class closure: 62 hostile archives (`expand_zip` and the upload route), a 300-mutant fuzz of `expand_zip` and a 60-mutant fuzz through the route: 128 passed, 0 exceptions, 0 responses >= 500, 0 staged leftovers. Breadth of the broad catch: 10 tests passed (interrupts, MemoryError, our own bugs and `ensure_inside` still propagate).
- Falsification, in copies outside the bound tree: constructor catch `except Exception` to `except ZeroDivisionError`: 3 passed before, 2 failed after. `_guarded` the same edit: 4 passed before, 4 failed after. Mutants beyond the floor: 0.
- 4c: repair diff (src: `sources/zip_intake.py` only, +36/-1) read in full; whole-unit scan found every file in the declared scope, nothing deleted or renamed, no test removed.

FAILURES: none
CAPABILITY-COVERAGE: 2/2 repaired rows reproduced (green before, red after)
LIVE-BROWSER: not-applicable (no UI file changed in the repair diff)
ISSUES-WRITTEN: none (coordinator verdict in a dual check; no ledger rows, no manifest flip, no goal close)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: With the runner fixed, the owed full suite ran once and every red is a known one or a load flake that passes alone; none comes from this unit, and the one red that differs from master (AT-792) is fixed by a test-lane commit that master has and this branch does not. The cycle-2 fix closes the class on my own evidence. The maker closes the goal task and writes issue rows only after both coordinators PASS.

PROPOSED-ISSUE: {"severity":"medium","type":"process","title":"shard_suite.py kept the lock of a dead run and the lock file named a pid that the OS later reused for an unrelated process; the next run waited until that process exited","file":"D:/ai_os/.claude/skills/checker/tools/suite_lock.py","fix":"record the process creation time with the pid so a reused pid is recognised as stale"}
PROPOSED-ISSUE: {"severity":"low","type":"gap","title":"One archive entry whose name the stdlib cannot decode (UTF-8 flag + invalid UTF-8) fails the whole archive as 'not a readable zip archive', so benign sibling videos are not registered; safe and crash-free, but TI5 'others still register' is not delivered for it","file":"src/autotester/sources/zip_intake.py:270","fix":"only if the owner wants it: an own central-directory reader that marks the unreadable record failed and lists the rest"}
PROPOSED-ISSUE: {"severity":"low","type":"wording","title":"A corrupt bzip2 member is reported as 'could not be staged (the write failed)' (bz2 raises OSError, which the member handler words as a staging failure)","file":"src/autotester/sources/zip_intake.py:211","fix":"catch the decompressor OSError inside _inflate and give it the 'corrupt member' reason"}
PROPOSED-ISSUE: {"severity":"low","type":"wording","title":"The manifest Metrics line lacks the five .9 fields (lane, check_s, mutants, defects_unit, defects_6c) and gives start/end as dates only","file":"qa/manifests/t198a-zip-drive-intake.md:66","fix":"the maker writes the full .9 Metrics line at close-out"}

Metrics: start=2026-10-11T03:32:58Z end=2026-10-11T04:14:00Z wall_min=40 agent_min=unavailable blocked_min=1 suite_runs=1 repeat_runs=0 mutations=2 cycle=2 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=2460 mutants=0 defects_unit=0 defects_6c=0
(slow: full suite 24 min, of which 14.9 min is pytest on four shards on a machine loaded by other projects' suites. The earlier attempt's checks are reused by evidence identity, so this retry's own time is the suite plus red classification of about 10 min, including two 5.5 min single-test runs.)
