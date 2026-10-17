# Manifest — at335-tolerance-scope
**Contract:** qa/contracts/explore.md X3, X4 (replay chain and its tolerance stay bounded)
**Goal task:** none (issue-driven)
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Dual check:** no
**Persona walk:** skip (api-only: no human screen; crawl-internal latency change)
**Issues addressed:** ISS-at335-followup-tolerance-scope
**Executor:** claude-sonnet-subagent
**Executor rationale:** Tier S single-function edit in one owned file; no external executor worthy.

## What changed
- src/autotester/stages/explore_return.py:65-90 (`return_to`) — computes `window_ms = 0 if depth >= MAX_REPLAY_DEPTH else RETURN_SETTLE_TOLERANCE_MS` and passes it to the two back/goto `_matches` calls, so the terminal-depth call (whose replay rung bails immediately, no click, no recursion) checks the fingerprint once instead of polling 1500ms after each rung. Rungs below the terminal depth, and the replay-arrival poll in `_replay_discovery`, keep the full bounded window.
- tests/test_explore_return_determinism.py:200-259 — two new tests with a fake clock (terminal depth does not poll; depth 0 still polls both recoverable rungs).

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: S (single function in one file, no tier trigger; X4 bound is unchanged, only shortened)
Base / checked state: base 69ebfae7, head e865e298 (clean tree for the owned paths)
Gate answers: none; qa/gates/new-module-authorization.md not engaged (no new src module)
Affected tests / full-suite trigger: tests/test_explore_return_determinism.py, tests/test_explore_error_causes.py; none (builder runs no full suite)
Pre-check[C1]: e865e298 uv run pytest tests/test_explore_return_determinism.py tests/test_explore_error_causes.py -> 12 passed t=41 blobs=tests/test_explore_return_determinism.py:f2179fe
Metrics: start=2026-10-17T13:00:00Z end=2026-10-17T13:12:00Z wall_min=12 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12

## How to verify (commands + expected)
- `uv run pytest tests/test_explore_return_determinism.py tests/test_explore_error_causes.py` → expected: 12 passed
- `uv run ruff check src tests scripts` → expected: All checks passed!
- `uv run autotester doctor` → expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest (both files): `12 passed, 1 warning in 41.33s`; determinism file alone after the ruff import-sort fix: `4 passed, 1 warning in 16.72s`
- ruff: `All checks passed!`
- doctor: `doctor: clean` (explore_return.py is 170 lines; only advisory D-087 citation findings, non-blocking)

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 | `return_to` at depth == MAX_REPLAY_DEPTH no longer polls after back/goto; below it the poll is kept | tests/test_explore_return_determinism.py `test_return_at_the_terminal_replay_depth_does_not_poll_a_rung_that_cannot_recover` and `test_return_below_the_terminal_depth_still_polls_each_recoverable_rung` | revert explore_return.py to base (drop `window_ms`) in a throwaway copy outside the worktree (scratchpad falsify-at335) | before-fix tree (fix reverted): `E   AssertionError: polled 3.299999999999999s on a rung that cannot recover` / `FAILED ...::test_return_at_the_terminal_replay_depth_does_not_poll_a_rung_that_cannot_recover` / `1 failed, 1 passed`; with fix restored in the same copy: `2 passed, 2 deselected` (the depth-0 test passes in both, so the poll is kept where it can recover) |

Note for the checker: the terminal-depth call now loses the late-re-render tolerance on its own back/goto rungs (a single fingerprint check, as before AT-335). The issue text and fact pass (.work/facts-m2.md) prescribe exactly this (`timeout_ms=0` when `depth >= MAX_REPLAY_DEPTH`); worst-case per-action overshoot drops by 2 x 1500ms at the terminal call (the three recursing depths are unchanged).

## Live browser evidence
Not UI-touching — no surface changed (changed paths: src/autotester/stages/explore_return.py, tests/test_explore_return_determinism.py).

## Status: checked-PASS (qa/verdicts/at335-tolerance-scope.md, cycle 0)
