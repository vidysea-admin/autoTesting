# Checkpoint — t167-release-regression, repair coordinator A (cycle 1)

Policy-Version: proportional-verification/2026-10-10.9 · Tier L · Resume: 0 of 2 · Retry: 0
Checked sha: 102a4b91 (repair range 667a0c64..102a4b91; product commit 00f25489)
Environment: win32, Python 3.11.15 (worktree .venv), pytest 9.1.1, langgraph 1.2.14 from uv.lock
Code hashes (blob, 102a4b91): orchestrate_gate.py 1021b5d9748e · release.py 932dcb614e4e · tests/test_release_gate.py 82d90ac15a68
Dependency hashes: uv.lock 4882ef560a75 · pyproject.toml 72a83bd9e4af (both untouched by the repair)
Tree: 6200d9a3fef1. No browser/live/data checks (CLI only, fixture-only): no deploy id, no data snapshot.
Attribution: coordinator A, claude-sonnet-subagent, this file.

## Completed checks (all in a git-archive copy of 102a4b91, never the bound tree)
| Check | Command / scope | Result |
|---|---|---|
| RR2 own reproduction | `repro_rr2.py` (own script, 9 scenarios S1-S9, real multi-step Cases, signed approval) | S1 forged scope (declared 3, true cost 15, approval 3) REFUSED, also with human yes, 0 execute calls, run dir holds only the forged scope.json; S2 honest scope pauses then completes; S3 approval one short refused; S4 declared 1e9 refused; S5 cases grown after freeze refused (fail closed); S6 plans naming absent cases cost 1 each, refused; S7 empty plans accepted, executes zero cases; S8 wall-clock under-declared refused; S9 on-disk bool/str refused, negative/zero/float rejected by schema (ValueError) before the gate, nothing ran |
| RR1..RR6 affected | 11 test files of the manifest pre-check (release_gate, regression_trigger, cli_release, orchestrate, orchestrate_runners, cli_orchestrate, cli_orchestrate_resume, consent, parallel_run_approval, schema, store), `-p no:xdist -o addopts=` | 137 passed |
| RR5 | `grep -n langgraph pyproject.toml` -> line 17 `langgraph==1.2.14`; autotester doctor -> clean; ruff -> All checks passed | met |
| Falsification RR2 (mine) | copy fals1: `actions = scope.max_actions` (re-cost removed) | my script S1 asserts (RR2 NOT FIXED); repo `tests/test_release_gate.py`: 1 failed (under_declared...), 2 passed |
| Extra mutant | copy fals2: `wall_clock_s=scope.wall_clock_s` (max removed) | my S8 accepts the forged wall-clock scope (red); the repo tests: 25 passed (survives) -> PROPOSED-ISSUE P1 |
| Step 4c | repair diff 667a0c64..102a4b91 read in full; whole-unit diff master...branch (19 files) | nothing pre-existing removed (only `_plan_cost`, a function created in this unit, moved to `plans_cost`); every file is in the manifest's What changed |

## Full suite (done)
`shard_suite.py --repo ...t167-release-regression --ref 102a4b91 --shards 1 -- -o addopts=`: collected 2889, 2865 passed, 19 skipped, 5 failed (alone: advice-resolves failed; rc2 failed (AT-792); redact perf, sessionstart healthy-log, explore_modal passed alone). Unit-owned red: test_cli_advice_resolves (new cli_release.py advice sites). Verdict FAIL, qa/verdicts/t167-release-regression.r1.a.md.

## Remaining
none
