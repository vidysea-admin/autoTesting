# Verdict - 6c-1028-batch (integration 6c, branch integrate/1028, head 806a87bc, FULL sharded suite)
Verdict: RED (6c RED: two regressions from feat/d111-standing-approval; every other red is baseline, master-red or flake)
Head tested: 806a87bc (15 commits over master e74664f8; merges feat/d111-standing-approval, fix/ephemeral-storage-warning, run-summary-inconclusive). Tree clean except untracked qa/.paused.

## Step 1 - lint and doctor
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 2 violations, both on docs/SNAPSHOT.md (`stale-generated`, `stale-committed`: differs from regeneration; run `autotester snapshot`). Generated file, not regenerated here; the rest is advisory D-087 output. Not compared against master.

## Step 2 - full sharded suite
Command: `python D:/ai_os/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting/.claude/worktrees/integrate-1028 --ref HEAD --shards 4 --budget-seconds 3300 -- -o addopts=` (exit 1, collect proof ok=True). Collected 9054 = union 9054 = ran 9054. Totals: 8999 passed, 11 skipped, 16 failed, 28 error. Wall 23.9 min. Log: .work/6c-1028-batch.run1.log.

## Step 3 - every non-green, judged
Isolated rule: regression only if red alone on the batch AND green alone on master e74664f8 (detached worktree). Batch isolated run of the 12 file-groups: 12 failed. Master isolated run of the same files: 10 failed.

| Test | Class | Evidence |
|---|---|---|
| tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed | REGRESSION | red alone on batch, green on master. `new: [('cli_crawl.py', 'revoke')]`: cli_crawl.py:239 help text "(autotester revoke)" is picked up as an advice site; EXPECTED_SITES (test_cli_advice_resolves.py) and EXPECTED_SITE_COUNT=31 do not list it. Fix: reword the help or register the site (decision for the maker). |
| tests/test_crawl_real_cli.py::test_the_refusals_command_grants_the_run_once_a_human_fills_it_in | REGRESSION | red alone on batch, green on master. `core/consent.py:156-157` (`_grant_command`, commit e35066ad) appends ` (or --standing, until revoked)` to the printed grant command; the test shlex-splits the whole line, so `--standing,` becomes a token: "No such option: --standing, (Possible options: --standing)", exit 2. Fix: put the standing hint outside the pasteable line. |
| tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve | baseline (AT-1024) | baseline-reds.md row; red alone on master too |
| tests/test_role_port_mail.py::test_w2_a_mail_that_arrived_... | baseline (r8 note) | red alone on master too |
| tests/test_infra_trio.py::test_verify_gates_keeps_exit_code[0],[3] | baseline (env, WSL bash) | baseline-reds.md rows |
| tests/test_role_port_escalation.py::test_w4_below_allow_writes_... | pre-existing master red (not in baseline-reds.md) | red alone on master e74664f8 and on batch, same failure (`assertions[0].verdict` failed) |
| tests/test_role_port_authz.py::test_w3_* (5 tests) | pre-existing master red (not in baseline-reds.md) | red alone on master and batch |
| tests/test_platform_links.py::test_mp12_* (2 tests) | pre-existing master red (not in baseline-reds.md) | red alone on master and batch: `net::ERR_FAILED` on goto (browser/environment) |
| tests/acceptance/* (28 errors: ta04, ta05, ta06, ta09, ta10, ta11, ta12, ta13) | shard-copy artifact (AT-1405) | `pytest tests/acceptance` in the real worktree: 66 passed |
| tests/test_hosting_config.py::test_healthz_source_root_...; tests/test_mc_sessionstart_loop_status.py::test_hook_prints_the_report_... | load flake | both green alone on the batch (baseline-reds.md r10 note) |
Not seen: test_redact_wrap_perf, test_env_creation_is_coordinated_across_processes, test_crawl_inventory_live.

## Findings
- blocker: the two regressions above, both in the D-111 unit (feat/d111-standing-approval, e35066ad); its manifest/verdict passed without running these two tests. Return to the maker; re-run 6c after the fix.
- master-red candidates for baseline-reds.md: test_role_port_escalation w4, test_role_port_authz w3 x5, test_platform_links mp12 x2 (red on e74664f8 as well).
- docs/SNAPSHOT.md needs `autotester snapshot` + commit.
