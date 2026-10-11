# Verdict A - t178-failure-bundle-fb4-fb5 (coordinator A of a blind dual check)

Date: 2026-10-11. Bound to D:/autoTesting. Policy-Version: proportional-verification/2026-10-10.9. Commit checked: a7d3fa6c (tip of wave/t178-failure-bundle-fb4-fb5, re-checked unchanged). Cycle checked: 0. Resume: 1 of 2. Remaining (previous verdict, renamed qa/verdicts/t178-failure-bundle-fb4-fb5.a.r0-1.md): the one full suite.
Copy: `git archive` for every run; the bound worktree was never touched. I read no `.b.md`, `-b` directory or B checkpoint.

## Plan (step 0, resume)
Run only the one full suite (security-touching L unit), `shard_suite.py --repo D:/autoTesting --ref a7d3fa6c --shards 4 -- -o addopts=`; classify every red against the coordinator's list of reds already shown on master; show any other red on the merge base 3d8f7d5a. Everything else in the r0-1 verdict stands (nothing re-run; the code at a7d3fa6c is unchanged).

VERDICT: FAIL
SCOREBOARD: FB4 and FB5 met; containment met (r0-1 verdict). Full suite: 3066 passed, 7 failed, 19 skipped (3092 collected = union = baseline). 1 red is new and caused by this unit's diff.
TIER: L (security hunk `stages/failure_bundle.py:211-212`; full suite owed and now run)

## Full suite (own run, 4 shards, ref a7d3fa6c, started 06:02:48 after the lock freed, 3092 tests, collect proof ok)
Evidence: `qa/evidence/t178-failure-bundle-fb4-fb5-checker-a/suite-run-2.log`, `suite-summary.json`.
Reds (the harness re-ran each alone):
- tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed - FAILS ALONE. NEW, THIS UNIT'S. See FAILURES.
- tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads - failed alone; AT-920, already shown red on master (coordinator list).
- tests/test_hosting_config.py::test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere - failed alone; AT-921 (git-archive copies), on the coordinator's list.
- tests/test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen - failed alone; AT-792, on the list; the diff does not touch it.
- tests/test_crawl_inventory_live.py::test_a_logged_in_crawl_maps_every_route_and_names_the_one_it_refused - passed alone (load); AT-750, on the list.
- tests/test_mc_sessionstart_loop_status.py ::...healthy_log and ::...asleep_log... - both passed alone (load); AT-858 family, healthy-log on the list, the sibling asleep-log node is the same file and fixture and passed alone; the diff does not touch it.
AT-725 did not fire this run. No AT-924 red (the archive copy has no .git; the node is skipped/collected clean in this run).

## FAILURES
F1 (blocking, reproducible, caused by the diff): `tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed` is green on the merge base and red on a7d3fa6c.
- Command I ran: `PYTHONPATH=<git archive 3d8f7d5a>/src python -m pytest tests/test_cli_advice_resolves.py -o addopts= -p no:xdist` -> 28 passed on 3d8f7d5a; same command on a7d3fa6c -> `FAILED ... AssertionError: advice sites changed. gone: [] new: [('cli.py', 'expand'), ('ui/routes_learn.py', 'expand')]` (1 failed, 6 passed before -x stopped; the full file in the suite run: only this node red).
- Cause (I read the cited lines in this check): the diff adds two operator-advice sites that name `autotester expand <project> --proposals`: `src/autotester/cli.py` (`typer.secho(f"{exc}; review with \`autotester expand {project} --proposals\`"...)`) and `src/autotester/ui/routes_learn.py` (the refusal page `Review/prune with <code>autotester expand {slug} --proposals</code>`). The AT-210 guard pins the exact set of advice sites in `EXPECTED_SITES` and the diff did not update `tests/test_cli_advice_resolves.py` (diff stat for that file between 3d8f7d5a and a7d3fa6c: empty). The new advice commands themselves resolve (all other nodes of that file pass).
- Why it blocks: the builder's Pre-check covered 208 affected nodes and did not include this file, so a red the unit introduced reached the checker; the full suite is exactly the check meant to catch it. The fix is two entries in `EXPECTED_SITES` (a test-only, deliberate act per that test's own docstring), not a product change.
No other finding is blocking. FB4/FB5/containment verdicts, the secrets result, the browser result, the queue-field and security-class rulings and PROPOSED-ISSUE P1-P7 from the r0-1 verdict stand unchanged.

## PROPOSED-ISSUE (new, in addition to P1-P7 of the r0-1 verdict)
- P8 {"severity":"medium","feature":"failure-bundle","title":"T-178 added two `autotester expand --proposals` advice sites (cli.py, ui/routes_learn.py) without updating tests/test_cli_advice_resolves.py EXPECTED_SITES; the full suite goes red and the builder's Pre-check set omitted that file","evidence":"qa/evidence/t178-failure-bundle-fb4-fb5-checker-a/suite-run-2.log; 28 passed on 3d8f7d5a, 1 failed on a7d3fa6c"}

CAPABILITY-COVERAGE: 4/4 falsifications reproduced (FB4, FB5, CONTAIN, QUEUE); suite run once, 7 reds classified (5 on the master list, 1 sibling flake, 1 new)
ISSUES-WRITTEN: none (dual check: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: FB4 and FB5 are met and falsified, but the one full suite shows a deterministic red that this unit's diff introduced (two new advice sites vs the AT-210 pinned set). Evidence to block is met: a reproducible failing command I ran, green on the merge base. The maker adds the two EXPECTED_SITES entries (the fix is test-only) and re-dispatches; the cycle-1 check is repair-scoped. The owner round-cap waiver for the seven over-cap seams is still owed before merge.
Metrics: start=2026-10-10T20:48:08Z end=2026-10-11T00:58:00Z wall_min=50 agent_min=unavailable blocked_min=26 suite_runs=1 repeat_runs=0 mutations=4 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=3000 mutants=2 defects_unit=1 defects_6c=0
slow: suite lock wait 10 min + suite wall 20 min (blocked_min=26 incl. the earlier 15 min wait is cumulative per resume); session-limit gap excluded from wall_min
