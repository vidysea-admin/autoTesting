# 6c integration check r5 - int/1017 @ 81e0728e

Verdict: PASS
Cycle checked: 0
Head tested: 81e0728e2f462a0c2b196f9e67cc1f8562abb4be (int/1017 head at start and end of the run). Base: fcedc9f4.
Policy: proportional-verification/2026-10-18.15; full suite (.13-2: tests/conftest.py edit; tier-L security units incl. fix6c-r4-routeword).

## Commands run (real detached worktree .worktrees/int-6c-81e0728e, TMP/TEMP=D:/autoTesting/.work/tmp)
- Fail-fast on the 42 r4 reds: test_oracle_state_after, test_state_probe_schema, test_oracle_answer_key, test_oracle_copy_lint,
  test_network_oracles, test_leak_evidence, test_oracle_responsive, test_network_assertions, test_actuator_chokepoint: 169 passed, 0 failed.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: clean (advisory D-087 findings only).
- Full suite, no -x/--maxfail, run as r4 did: 526 test files, 5 in parallel, `pytest-timeout --timeout=240`.
  First pass: passed=8694 failed=21 skipped=10 errors=0. The 6 red files were rerun serially (docker/__pycache__ cleared first):
  test_hosting_deploy green; 7 load-only mutation_check/judgement reds cleared. After rerun: passed=8701 failed=14 skipped=10 errors=0.
- `tick.mjs --push-gate` (run in int-1017 before the stamp): no green stamp (expected).

## Reds (14, all baseline, none new)
All 14 match qa/checkpoints/baseline-reds.md (red on fcedc9f4): test_cli_advice_resolves (AT-1024) x1, test_goal_contract_registration (92 != 106, AT-743) x1,
test_infra_trio x2 (WSL bash), test_mutation_check x9 and test_mutation_check_judgement x1 (TMP inside the repo).
The 9th test_mutation_check node (`..._parametrized_test_with_spaces_in_its_id`, hash 441725533781) was shown red on a real worktree of fcedc9f4 and is
now recorded in baseline-reds.md. The r4 reds are fixed: 0 new reds; test_hosting_deploy green; AT-1019 timing test did not flake.

Logs: .work/6c-r5/files/, .work/6c-r5/serial/.

Metrics: start=2026-10-19T03:05 end=2026-10-19T03:45 wall_min=40 agent_min=unavailable blocked_min=0 suite_runs=2 repeat_runs=1 mutations=0 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=2400 mutants=0 defects_unit=0 defects_6c=0
