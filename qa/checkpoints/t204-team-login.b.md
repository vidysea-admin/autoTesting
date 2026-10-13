# Checkpoint t204-team-login (seat B) - cycle 0, resume 1 of 2
head=aa6fec2e product=5e0c4b0b base=9c9a91f3 policy=proportional-verification/2026-10-10.9
Verdict: FAIL (qa/verdicts/t204-team-login.b.md). Blocking: F1 credential_guard slug-prefix (own/repro.py), F2 AU27 refused-attempt audit (own/repro_audit.py).

Evidence identities (all on aa6fec2e, Windows, worktree venv):
- 10 auth test files + tests/test_ui_origin_guard.py, per-criterion -k sets, one process: 249 passed (verify sub-checker, evidence verify/results.jsonl)
- tests/test_permission_coverage.py test_credential_run_approval.py test_env_loading.py: 46 passed
- AU25 five UI files: 55 passed, 1 skipped
- falsification: 38 mutant rows in copies, 34 killed, 4 survived beyond the floor (AU3 lifetime, AU5 limit literal, AU11 grant table, AU18 repeated-Origin in the host file)
- attack scripts + raw json: qa/evidence/t204-team-login-B/{unauth,session,verify,diff,own}/
- ruff clean, doctor clean, uv lock --check Resolved 89 packages
Not run by seat B: full suite, browser (seat A), AU24, AU26.

# Cycle 3, merge-reconcile 1 (mr1), seat B - BLOCKED-PROCESS (suite lock held by pid 2844)
head=17c1422d code=997c842b base=2344c045 repair-base=37a1d211 policy=proportional-verification/2026-10-10.9
Evidence identities (git archive of 997c842b, Windows, fresh uv sync --frozen venv, -p no:xdist -o addopts=):
- route walk qa/evidence/t204-team-login-r3-mr1-b/route_walk.py -> 74 pairs, 0 unrouted, 0 anon-open, 0 zero-access-open
- 14 auth+policy_merge+routers_list files 131 passed; 13 auth/UI/CLI/hosting files 260 passed; 16 master-side files 425 passed; 21 files 888 passed + 9 failed (archive has no .git; 69 passed after git init)
- falsification AU14 AU16 AU18 AU25 red on named assertions (qa/evidence/t204-team-login-r3-mr1-b/falsify-f*.red.txt); ruff, doctor, uv lock --check clean
Remaining: ONE full suite on 997c842b via shard_suite (lock). Nothing else owed.

# Cycle 3 mr1 seat B - retry 1: CONTINUE-NEEDED (suite incomplete)
code=997c842b base=2344c045 policy=proportional-verification/2026-10-10.9
Done since BLOCKED-PROCESS: shard_suite 4 shards on 997c842b (lock free 13:52, host CPU 100%). Shards 0/1/3: 4213 passed, 9 failed, 21 skipped. Shard 2 killed at 3600 s (1169 tests, no result), collect proof ok=False. Files: qa/evidence/t204-team-login-r3-mr1-b/suite-run3.log, suite-summary.json, shard2/.
Known reds seen: mutation_check_judgement hung-baseline (AT-858), redact perf x2 (AT-921), mc_sessionstart x3, test_core env creation (AT-968), hosting_config healthz (runner artifact). Unproven on baseline: test_crawl_inventory_live logged-in crawl (wall_clock_s STOPPED_BOUND), test_mutation_check_judgement mutation-hang test.
Per-file rerun of shard 2: 12 files green (238 passed); 3 timing reds (video_parallel_sweep, flake_probe_real_process, hosting_config healthz); 4 files hit my 480 s cap (video_masking_live, mutation_check, explore_completeness, video_review_cleanup); rest not run (68 files in shard2/remaining-files.txt).
Remaining: the 68 files on a quiet host (1-2 workers); the 4 unproven reds alone on 997c842b and 2344c045.
