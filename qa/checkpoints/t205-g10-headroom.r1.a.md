# Checkpoint - t205-g10-headroom r1 A (head fb93776b, repair base 0b8325b6)

Evidence identity (all run by coordinator A in D:/autoTesting/.worktrees/t205-g10-headroom, autotester.__file__ inside the tree, `uv --directory <tree> run`):
- pytest -p no:xdist -o addopts= -v on 10 files (test_run_launcher, test_run_launcher_approval, test_project_schema_team, test_safe_names_windows, test_team_store, test_team_enums_home, test_policy_merge, test_routers_list, test_cli_subapp_hook, test_schedule_model) -> 665 passed. Output: qa/evidence/t205-g10-headroom-r1-A/affected-tests.txt
- ruff check src tests scripts -> All checks passed; autotester doctor -> clean.
- code hashes: head fb93776bbf21; product 57cec910; uv.lock unchanged by the repair.
- falsifications TF1 TF2 TF6 TF7 done (qa/evidence/t205-g10-headroom-r1-A/falsifications-and-attacks.md).

Remaining (suite-only retry): one full suite at fb93776b via shard_suite (4 shards, -o addopts=). Blocked 15 min by the suite.lock holder pid 13816 (D:\hei-sweep), not ours; not killed.
