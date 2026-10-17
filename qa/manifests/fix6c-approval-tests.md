# Manifest — fix6c-approval-tests
**Contract:** qa/contracts/consent.md (line 133, `check_crawl_approval.py` is T-145's `done_check`); repair of integration-6c-int1017 FAIL (qa/verdicts/integration-6c-int1017.md)
**Goal task:** T-145 (follow-up)
**Date:** 2026-10-17
**Fix cycle:** 1 of max 2
**Repair base:** 7b16f66b
**Dual check:** no — test-fixture repair; the AT-999 product rule is unchanged
**Persona walk:** skip (test-only, no UI surface)
**Issues addressed:** AT-999 (fallout: 4 tests red on int/1017)
**Executor:** claude-sonnet-subagent
**Executor rationale:** S unit, two owned test files, brief from the maker.

## What changed
- tests/test_approval_prod_gate.py — new helper `_track_summaries(root)` (git init + add projects/ + commit in the tmp project, so the crawl summary is git-tracked as in a real checkout); called in 3 tests after the summary is in its final form (for the no-approval-id test, after the summary is edited).
- tests/test_approval_prod_gate_paths.py — imports the helper and calls it in `test_done_check_fails_closed_for_production_without_the_key`.
- No assertion changed or removed; scripts/check_crawl_approval.py untouched (tracked-only rule stays); no skip/xfail; no src/ change.

## Verification scope
Policy-Version: proportional-verification/2026-10-17.13
Tier: L (security test scope, protected-test rule; a repair checker judges it)
Base / checked state: Repair base 7b16f66b, fix commit e4c8e662 (tests/test_approval_prod_gate.py:9fb80d0, tests/test_approval_prod_gate_paths.py:59d7d83)
Gate answers: none; no gate applies (no new src/ module).
Tests[C1]: tests/test_approval_prod_gate.py (3 done_check tests + 9 others in file), tests/test_approval_prod_gate_paths.py::test_done_check_fails_closed_for_production_without_the_key, tests/test_check_crawl_approval.py (the AT-999 unit's own 4 tests), tests/test_goal_done_check_shapes.py — the four reds are the repaired tests; the rest of those files and the AT-999 unit's tests guard the unchanged script rule.
Pre-check[C1]: e4c8e662 uv run pytest tests/test_approval_prod_gate.py tests/test_approval_prod_gate_paths.py tests/test_check_crawl_approval.py tests/test_goal_done_check_shapes.py -> 63 passed t=60 blobs=tests/test_approval_prod_gate.py:9fb80d0,tests/test_approval_prod_gate_paths.py:59d7d83
Falsification[C1]: mutation in a copy outside the worktree (scratchpad/fals): script's production-approval gate (`if project.production or latest.project_production:` -> `if False:`) -> tests/test_approval_prod_gate.py::test_done_check_fails_when_a_production_project_was_gated_by_a_non_production_row went RED (1 failed, 2 passed in -k done_check); unmutated worktree: green. Base-state (no tracked commit) red is the integration verdict's 4 reds ("no tracked crawl summary for 'demo'").
Metrics: start=2026-10-17 end=2026-10-17 wall_min=15 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=60 mutants=1 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_approval_prod_gate.py tests/test_approval_prod_gate_paths.py tests/test_check_crawl_approval.py tests/test_goal_done_check_shapes.py` -> 63 passed
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> doctor: clean

## Actual outputs (from maker's own run)
- pytest: `63 passed, 2 warnings in 59.51s`; ruff: `All checks passed!`; doctor: `doctor: clean`.

## Capability coverage (each repaired claim -> its isolating falsification)
| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 | the 4 done_check tests exercise their named property again with a git-tracked summary | the 4 tests + 63-test set above | drop the production-approval gate in a copy of the script | red: test_done_check_fails_when_a_production_project_was_gated_by_a_non_production_row; green on the real script |

## Live browser evidence
Not UI-touching — changed paths: tests/test_approval_prod_gate.py, tests/test_approval_prod_gate_paths.py.

## Status: checked-PASS (qa/verdicts/fix6c-approval-tests.md, cycle 1)
