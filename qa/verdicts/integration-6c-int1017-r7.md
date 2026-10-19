# 6c integration check r7 - int/1017 @ 5223173b

Verdict: PASS
Cycle checked: 0
Head tested: 5223173b8b0c219bdc9d387c58c8ff315f7ea481 (int/1017 head at start and end of the run). Base: d25227c3 (= origin/master, ancestor of head, 12 commits behind: g11-oracle-wiring merge).
Policy: proportional-verification/2026-10-18.15; full sharded suite already run (summary.json below), triage only here.

## Commands run (real clean detached worktrees, TMP/TEMP=D:/autoTesting/.work/tmp)
- Reused full sharded run: .work/tmp/aios-shards/int-6c-5223173b-20261019-103754/summary.json - passed=8748 failed=24 error=19 skipped=11;
  collect_proof ok (8802 collected = 8802 ran, no duplicates or missing). 43 nodes in failed_still_failing_alone.
- Re-ran all 43 nodes in .worktrees/int-6c-5223173b (git status clean, HEAD 5223173b): `uv run pytest <26 non-mutation nodes>` = 4 failed, 22 passed;
  `uv run pytest <17 mutation nodes>` = 10 failed, 7 passed. Logs: .work/6c-r7/other.log, mut.log.
- Re-ran the 14 still-red nodes' files on base d25227c3 (.worktrees/int-6c-base-d25227c3, detached): 14 failed, 69 passed - the same 14. Log: .work/6c-r7/base.log.
- `uv run ruff check src tests scripts` (head): All checks passed. `uv run autotester doctor` (head): clean (advisory D-087 findings only).

## Red classification (43 reds in the shard run)
| Class | Count | Nodes | Disposition |
|---|---|---|---|
| git-archive artifact, green in a real worktree | 29 | tests/acceptance test_ta01 (2), ta08 (6), ta09 (3), ta10 (2), ta12 (3), ta13 (3); test_core env_creation; test_mc_sessionstart_loop_status; test_hosting_config healthz; test_mutation_check_judgement x3 (escape-by-climbing, absolute path, hang timeout); test_mutation_check x4 (nodes that pass alone, load-sensitive) | passed on head in a real worktree; not defects |
| Baseline, red on base d25227c3 and head (TMP inside repo) | 10 | test_mutation_check x9, test_mutation_check_judgement::test_an_interrupted_run_with_real_failures_is_not_a_kill | already in baseline-reds.md |
| Baseline, red on base d25227c3 and head (WSL has no /bin/bash) | 2 | test_infra_trio verify_gates_keeps_exit_code[0], [3] | already in baseline-reds.md |
| Baseline, red on base d25227c3 and head | 1 | test_cli_advice_resolves::test_the_collector_reports_what_it_could_not_resolve (routes_crawl_approval.py:184, AT-1024) | already in baseline-reds.md |
| Baseline, red on base d25227c3 and head | 1 | test_goal_contract_registration::test_revised_goal_contract_is_registered (AT-743) | in baseline-reds.md; failing line is now `assert all(value in dashboard ...)` on both base and head (was `92 == 106` at fcedc9f4: the message drifts with goal.json) |
| New on head only | 0 | none | - |

Count check: 29 + 14 = 43 (29 pass = 22 non-mutation + 7 mutation nodes; 14 red = 4 non-mutation + 10 mutation).
New reds: 0. Load flakes: none claimed (every red reproduced alone).

Metrics: start=2026-10-19T12:45 end=2026-10-19T13:05 wall_min=20 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=0 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 check_s=1200 mutants=0 defects_unit=0 defects_6c=0
