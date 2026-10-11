# Checkpoint - t200b-scheduled-test, cycle 1, coordinator A

Identity: code sha 6d6bc318 (head 371eb7f6, manifest only), repair base 0d9a3b56, policy proportional-verification/2026-10-10.9, env = worktree .venv (uv.lock unchanged), attribution = checker coordinator seat A, verdict `qa/verdicts/t200b-scheduled-test.r1.a.md`. Dataset/build id: n/a.

| Check | Command and scope | Code hashes | Result |
|---|---|---|---|
| Affected set | pytest -p no:xdist -o addopts= schedule x8, explore_consent, credential_run_approval, consent, approval_signing, env_loading (236 collected) | schedule_store.py, schedule_gate.py, scheduler.py, explore_consent.py, schedule_fakes.py, tests at 6d6bc318 | 236 passed; ruff, doctor clean |
| TS6 (F1) | about 60 import shapes x 5 modules + 3 real-tree falsifications (sub-checker) | test_schedule_tick.py at 6d6bc318 | all accidental shapes detected; falsifications red then green |
| TS1 purge (F2) | spawn concurrency x3 layouts, crash points x12, Windows handles, 2 falsifications (sub-checker) | schedule_store.py at 6d6bc318 | no loss; half-purge on hard crash only, re-run converges |
| TS5 / P5 | key-mint probe in temp root; falsification signing_key_available -> True | explore_consent.py, schedule_gate.py | manifest claims confirmed; red then green |
| TS7 / P3 | falsification TickDeps.scrub default | scheduler.py | red then green |

Not run: checker full suite (BLOCKED-PROCESS; suite.lock held by foreign PID 25796). Owed command: `python ~/.claude/skills/checker/tools/shard_suite.py --repo D:/autoTesting/.worktrees/t200b-scheduled-test --ref 371eb7f6 --shards 8`. Browser: not applicable.

## Retry 1 (suite only), 2026-10-11

| Check | Command and scope | Code hashes | Result |
|---|---|---|---|
| Full suite | `shard_suite.py --repo D:/autoTesting --ref 371eb7f6 --shards 4 -- -o addopts=` ; 3484 collected, 252 files, collect proof ok | tree 371eb7f6 (code sha 6d6bc318), uv.lock unchanged | 3458 passed, 20 skipped, 6 failed; 3 still red alone (AT-792, AT-921, healthy_log hook timeout, all red on master archive 0ffee6ed or fixed there), 3 passed alone (AT-725, AT-750 b and d, load flakes) |
| Master comparison | single nodes on `git archive master` (0ffee6ed) | n/a | rc2 passes (AT-792 fixed there); healthz fails (AT-921); healthy_log fails alone (60 s timeout) |

Owed checker full suite is now done (suite_runs=1). Previous attempt 1 of this retry: lock held by foreign PID 32092 (D:/hei-sweep), 901 s wait, exit 3. Evidence: qa/evidence/t200b-scheduled-test-r1-A/suite-r1-1-*.
