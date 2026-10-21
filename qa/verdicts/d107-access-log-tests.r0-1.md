# Verdict - d107-access-log-tests (Tier L, protected test change, single checker, cycle 0)
Verdict: PASS
Cycle checked: 0
Policy: proportional-verification/2026-10-19.17. Bound to D:/autoTesting/.worktrees/int-1019. Unit diff: commit 07c05e7c (base b752af42..HEAD for the unit; product line docker/entrypoint.sh came from master 5976c832, accepted by D-107).
Tier L only because an assertion was removed (protected test change); no product-code change in this unit, so one checker (no security behaviour change made here).

## Judgement (read the diff in full)
- tests/test_auth_deploy_files.py: exactly one assertion removed (`assert "--no-access-log" in commands[0]`). Kept: single logical launch line found, `len(commands) == 1`, `commands[0][:4] == ["uv","run","uvicorn","autotester.ui.app:app"]`. Test renamed `..._without_an_access_log` -> `..._once_under_the_supervisor` (no other file references the old name outside old evidence); module docstring and a D-107/AT-1390 comment updated.
- tests/test_container_supervision.py: one line changed, `"--no-access-log" in entrypoint and "chown" not in entrypoint` -> `"chown" not in entrypoint`. The supervisor-exec assertion above it and the chown assertion are kept.
- No threshold lowered, no skip/xfail, no conftest/fixture touched. Change matches D-107 (access log kept per master 5976c832; the two named tests updated; AU22 audit rules unchanged; residual AT-1390 open).

## Falsification floor (copy, never the bound tree): .work/tmp/fals-d107 (git archive of HEAD)
- Current tests on current entrypoint: 2 passed.
- Old flag-requiring assertions put back (copy only): 2 failed (`assert '--no-access-log' in ...`), both against the HEAD entrypoint which has no flag.
- Old assertions removed again (= HEAD tests): 2 passed (identical to the first run).

## Fold
Step 1 contract fold committed first: 6e4ebaa5 (qa/contracts/auth.md AU22 sentence + amendment-log line; Re-derive line unchanged because it does not mention the access log flag).

PROPOSED-ISSUE: none new (AT-1390 already open, medium security).

Metrics: start=2026-10-21T18:14 end=2026-10-21T18:22 wall_min=8 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
