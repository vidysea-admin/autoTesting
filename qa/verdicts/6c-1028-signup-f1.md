# Verdict - 6c-1028-signup-f1 (maker step 6c pre-push, head e0914745, Mode A, FULL sharded suite)
Verdict: PASS (6c GREEN, no new red attributable to the diff)
Cycle checked: 0
Head tested: e0914745 (branch fix/signup-requests-f1, direct descendant of master 26b2ce58). Unit: signup-requests-f1 (dual A+B PASS cycle 0). Reference verdict: qa/verdicts/6c-1028-signup.md. Run on `git archive` copies of HEAD by the sharded tool (the main checkout's uncommitted files never entered it).

## Step 1 - full sharded suite
Command: `python D:/ai_os/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting/.claude/worktrees/signup-requests-f1 --ref HEAD --shards 8 --budget-seconds 3300 -- -o addopts=` (exit 1: reds only; collect proof ok=True).
Collected 8990 (reference run 8965; +25 = tests/test_ui_signup_requests_f1.py). Union of shards 8990 = collected 8990 = ran 8990; every shard reported (no shard died without a report, so no shard re-run was needed). Wall 32.8 min, cpu 24% at start.
Totals: 8954 passed, 11 skipped, 9 failed, 16 error = 8990. Log: .work/6c-1028-signup-f1.run1.log.

## Step 2 - every non-green, judged
Isolated re-run in the real worktree (`pytest -o addopts= -p no:cacheprovider tests/acceptance <6 failed ids> tests/test_ui_signup_requests.py tests/test_ui_signup_requests_f1.py`): 109 passed, 1 failed (test_citations, below).
| Test | Class | Evidence |
|---|---|---|
| tests/test_infra_trio.py::test_verify_gates_keeps_exit_code[0] and [3] | baseline (env, WSL bash) | qa/checkpoints/baseline-reds.md rows; red on master in the reference verdict |
| tests/test_role_port_mail.py::test_w2_a_mail_that_arrived_is_observed_through_the_read_only_reader | baseline | baseline-reds.md r8 note |
| tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve | baseline | baseline-reds.md row (AT-1024) |
| tests/test_citations.py::test_the_real_tree_has_no_dangling_citation | pre-existing on master, not caused by this diff | red on a clean `git archive` of master 26b2ce58 with the identical violation (`qa/verdicts/6c-1028-signup.md:4 cites an entry that has no `## D-nnn` heading in docs/DECISIONS.md`): the master verdict cites the decision entry that lives only in the owner's uncommitted docs/DECISIONS.md diff in the main checkout. The f1 diff touches neither that verdict nor DECISIONS.md. Clears when that entry is committed. Same cause gives the single `autotester doctor` violation below. |
| tests/acceptance/* (16 errors: ta04, ta10, ta11, ta12, ta13) | shard-copy artifact (AT-1405, baseline-reds.md r10) | all of tests/acceptance green in the real worktree (inside the 109 passed) |
| tests/test_hosting_config.py::test_healthz_source_root_...; test_mc_sessionstart_loop_status.py::test_hook_prints_the_report_...; test_hosting_deploy.py::test_no_secret_value_anywhere_...; test_crawl_inventory_live.py::test_a_logged_in_crawl_... | load / shard-copy / order flake | each green alone in the real worktree; all four named in baseline-reds.md or the reference verdict |
Not seen this run: tests/test_redact_wrap_perf.py timing flake (green). No red outside baseline-reds.md, the reference verdict's flake list, or the master-red above. No test in tests/test_ui_signup_requests.py or tests/test_ui_signup_requests_f1.py failed in the sharded run or the isolated run (14 + 25 = 39 passed alone).

## Step 3 - lint and doctor
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 1 violation(s) - decision-citation-dangling at qa/verdicts/6c-1028-signup.md:4 (same pre-existing master cause as the test_citations red; all other output is advisory D-087 warnings). Not attributable to the diff.

## Findings (non-blocking)
- process (medium): master 26b2ce58 carries a committed verdict citing a decision entry that is not yet committed, so test_citations and `autotester doctor` are red on master until that entry is committed (or the citation removed). Owner action.

## Step 4 - push
See the coordinator report: ff-only merge of fix/signup-requests-f1 into master, then `git push origin master` (D-007).

Metrics: wall_min=32.8 suite_runs=1 repeat_runs=0 mutations=0 cycle=0 tests=8990 mode=full shards=8 prepush_wall_min=32.8 policy=proportional-verification/2026-10-19.17
