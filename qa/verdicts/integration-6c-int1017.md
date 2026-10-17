# 6c pre-push integration verdict: int/1017

Verdict: FAIL
Status: FAIL
Cycle checked: 0
Reviewed SHA: ecb85f7c0d0301cac41d0a274f9fe72948ad9db8
Base SHA: fcedc9f4 (= origin/master); 122 unpushed commits
Trigger: full suite (.13-2: tests/conftest.py edit at672; tier-L security units at929-proposal-scrub, crawl-approval-by-id)

## Results (clean detached worktree .worktrees/int-6c-ecb8 at ecb85f7c)
- Full sharded suite (shard_suite.py --mode integration, 8 shards, `-o addopts=`): passed=7900 failed=14 error=21 skipped=11 (35 reds).
  The default tool run needs `-o addopts=` because pyproject `addopts=-q` makes the collect step print file counts (AT-503 shape); first attempt "collect failed" was that, not a product defect.
- ruff check src tests scripts: All checks passed. autotester doctor: clean.
- qa/checkpoints/baseline-reds.md does not exist in the repo, so no red is "in the record". Every red was re-run by node id with `uv run pytest` in the real head worktree and in a second detached worktree at base fcedc9f4.
- 25 of 35 reds PASS in a real worktree (archive-copy artifacts: acceptance TA01/05/07/09/12/13, hosting_deploy, hosting_config, mc_sessionstart_loop_status). Not defects.
- Head: 10 failed / 25 passed. Base: 5 failed / 30 passed.

## Pre-existing (also red on base fcedc9f4)
- tests/test_infra_trio.py::test_verify_gates_keeps_exit_code[0] and [3] (WSL bash)
- tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve (ui/routes_crawl_approval.py:184)
- tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered (92 == 106)
- tests/test_cli_subapp_hook.py::test_help_lists_exactly_the_commands_it_listed_before (red on base too, but the head diff is wider: the expected command list also lacks `ledger-backref` and `schedule`; the base red masks it)

## NEW reds (green on base, red on head) = 5
1. tests/test_approval_prod_gate.py::test_done_check_passes_from_summary_alone_for_a_production_row
2. tests/test_approval_prod_gate.py::test_done_check_fails_when_a_production_project_was_gated_by_a_non_production_row
3. tests/test_approval_prod_gate.py::test_done_check_fails_without_a_recorded_approval_id
4. tests/test_approval_prod_gate_paths.py::test_done_check_fails_closed_for_production_without_the_key
   Cause: "FAIL no tracked crawl summary for 'demo'". Owner: crawl-approval-by-id, commit b85086f4 (AT-999: scripts/check_crawl_approval.py now judges only git-tracked summaries via `git ls-files`). The old tests build summaries under tmp_path (not a git repo) and were not updated.
5. tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed
   Cause: `assert len(advice()) == EXPECTED_SITE_COUNT` is 31 vs 28. Owner: at899-release-cli, commit f7605b35 (cli_release.py adds 3 advice sites: `release`, 2x `release-log`); EXPECTED_SITE_COUNT (tests/test_cli_advice_resolves.py:210) not bumped.

## push-gate
`tick.mjs --push-gate --root .worktrees/int-1017` -> `push-gate: no green stamp for 3550f7ac...`. No 6c-green stamp written (red).

Metrics: start=2026-10-17T22:20 end=2026-10-17T23:15 wall_min=55 agent_min=unavailable blocked_min=0 suite_runs=2 repeat_runs=1 mutations=0 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=3300 mutants=0 defects_unit=0 defects_6c=5
