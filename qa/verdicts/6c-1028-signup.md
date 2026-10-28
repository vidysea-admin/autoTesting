# Verdict - 6c-1028-signup (maker step 6c pre-push, head bd56f8c5, Mode A, FULL sharded suite)
Verdict: PASS (6c GREEN, no new red)
Cycle checked: 0
Head tested: bd56f8c5 (branch fix/signup-requests, direct descendant of master 924d811a). Unit: signup-requests (dual A+B PASS cycle 0). Policy: proportional-verification/2026-10-19.17. Run on `git archive` copies of HEAD, so the owner's uncommitted D-110 files never entered it.

## Step 1 - full sharded suite
Command: `shard_suite.py --repo <worktree> --ref HEAD --shards 8 --budget-seconds 3300 -- -o addopts=` (exit 2: collect proof NOT ok, see below).
Collected 8965 (baseline 6c-1026-d109 was 8949; +16 = tests/test_ui_signup_requests.py). Log: .work/6c-1028-signup.run1.log.
Machine was loaded (cpu 76% at start); wall 47.1 min vs 15 min last time. Shards 2 and 4 ended rc=1 with no report (pytest process ended before its summary; cause not established, load suspected), so the tool's union was 6723 of 8965 and exit was 2.
Completion (no test skipped from the proof): the exact arg files of shards 2 and 4 were re-run in full (`pytest -v @args-N.txt`, two clean `git worktree` checkouts of bd56f8c5): shard 2 = 2 failed, 1117 passed, 2 skipped (1121); shard 4 = 1109 passed, 2 skipped, 10 errors (1121). Union now 6723 + 2242 = 8965 = baseline.
Totals: 8920 passed, 11 skipped, 11 failed, 23 error = 8965.

## Step 2 - every non-green, judged
Isolated re-run in the real worktree (`pytest -o addopts= tests/acceptance <the 11 failed ids>`): 74 passed, 5 failed.
| Test | Class | Evidence |
|---|---|---|
| tests/test_infra_trio.py::test_verify_gates_keeps_exit_code[0] and [3] | baseline (env, WSL bash) | baseline-reds.md; red alone on head AND on master 924d811a, same `execvpe(/bin/bash)` message |
| tests/test_role_port_mail.py::test_w2_a_mail_that_arrived_is_observed_through_the_read_only_reader | baseline | baseline-reds.md r8; red alone on master 924d811a (`'failed' == 'passed'`) |
| tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve | baseline | baseline-reds.md row; red alone on master 924d811a; diff touches no crawl-approval route |
| tests/test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus | timing flake, unrelated | wall-clock bound of 3 s on a 500 KB scan. Red in the sharded run, red in the mixed isolated run (5.82 s), and 1 of 5 times when its file was run alone on head (3.62 s); green in the other 4 head runs and 4 of 4 on master 924d811a (run times 3.5-4.5 s for the whole file, so the bound is near this machine's speed). Diff touches nothing under redact |
| tests/acceptance/* (23 errors: ta02, ta05, ta06, ta08, ta11, ta12, ta13) | shard-copy artifact (AT-1405, baseline-reds.md r10) | all of tests/acceptance green in the real worktree (inside the 74 passed) |
| tests/test_core.py::test_env_creation_is_coordinated_across_processes; test_video_parallel_sweep.py::...do_not_lose_each_others_video; test_browser_use_guard.py::test_af6_...; test_crawl_inventory_live.py::test_a_logged_in_crawl_...; test_hosting_config.py::test_healthz_source_root_...; test_mc_sessionstart_loop_status.py::test_hook_prints_the_report_... | load / shard-copy flake | each green alone on head (baseline-reds.md "load-dependent" and r10 notes name the last four) |
No red outside baseline-reds.md or a green-alone/timing flake. No test in tests/test_ui_signup_requests.py, test_ui_auth_*, test_ui_origin_guard, test_portal_* failed in any run (those 438 also passed in the maker's targeted run).

## Findings (non-blocking)
- process (medium): the sharded tool reported exit 2 because two shards' pytest processes ended without a report under load; recovery was to re-run exactly those shards' arg files. Worth a tool fix (retry a shard that has no report).
- tests/test_redact_wrap_perf.py has a fixed 3 s bound that this machine sits near under any load (candidate issue).

## Step 3 - push
See the coordinator report: ff-only merge of fix/signup-requests into master, then `git push origin master` (D-007).

Metrics: wall_min=47.1 (sharded) + 16 (shard 2/4 completion) suite_runs=1 repeat_runs=1 (shards 2,4) mutations=0 cycle=0 tests=8965 mode=full shards=8 prepush_wall_min=47.1 policy=proportional-verification/2026-10-19.17
