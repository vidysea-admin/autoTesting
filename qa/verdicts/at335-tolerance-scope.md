# Verdict - at335-tolerance-scope
Cycle checked: 0
Date: 2026-10-17 | Bound root: D:/autoTesting/.worktrees/at335-tolerance-scope | Base 69ebfae7 (git merge-base HEAD master) | Head checked e865e298 (+ manifest commit 59d06163)
Policy-Version: proportional-verification/2026-10-15.12 | Dual check: no

## Plan
Logic change in one function (explore_return.py `return_to`), api-only/crawl-internal: affected tests + the falsification floor (1 per criterion). No UI, data, prompt or security trigger. Quick lane: `tick.mjs --lane-check 69ebfae7` -> `lane-ineligible: lane-disabled`, so normal check, lane=normal.
Criterion C1 = ISS-at335-followup-tolerance-scope (AT-335 follow-up): skip the settle poll on the terminal depth == MAX_REPLAY_DEPTH rung, keep it on rungs that can recover.

VERDICT: PASS
SCOREBOARD: 1/1 criteria met, 2/2 invariants hold (X3 identity untouched; X4 bound only shortened: window 0 at depth>=3, 1500ms elsewhere, termination unchanged)
TIER: S (single function, one product file; no L trigger in the diff; external callers explore_node.py:259,291, explore_traversal.py:133, explore_typing.py:127 use depth=0 and are unchanged)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced
LIVE-BROWSER: not-applicable (src/autotester/stages/explore_return.py, tests/test_explore_return_determinism.py; no UI surface)
ISSUES-WRITTEN: ISS-at335-tolerance-scope-terminal-loses-tolerance (low); ISS-at335-followup-tolerance-scope open -> fixed
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The diff (read in full, step 4c: 7 src lines, 64 test lines, nothing removed except two call sites gaining a 3rd arg) computes `window_ms = 0 if depth >= MAX_REPLAY_DEPTH else RETURN_SETTLE_TOLERANCE_MS` (explore_return.py:82) and passes it to the back/goto `_matches` calls (:89,:93); `_replay_discovery`'s arrival poll (:141) keeps the full window. With window 0 `_matches` does exactly one fingerprint check (:57-61). Judged against the issue text, which prescribes `timeout_ms=0` at the terminal depth, this meets C1. Residual tradeoff (low row): the depth-3 back/goto rungs lose the late-render tolerance, as the manifest discloses.

## Evidence I produced
- `uv run pytest tests/test_explore_return_determinism.py tests/test_explore_error_causes.py` -> 12 passed (42.7 s)
- `uv run pytest tests/test_explore_modal.py tests/test_explore_replay.py tests/test_explore_node_recovery.py tests/test_explore_traversal.py` -> 28 passed (276 s), return_to callers beyond the manifest's set
- `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean (D-087 advisories only)
- `shard_suite.py --affected 69ebfae7..e865e298 --mode unit --list` -> exit 2 integration-required (dynamic globs across the repo), so the merged-head pre-push full suite (6c) still owns the rest; no full suite run here.
- FALSIFY (throwaway copy of `git archive e865e298` under the scratchpad, outside the worktree, PYTHONPATH pinned to the copy and confirmed by importing autotester from it): the 2 new tests green (`2 passed`); `git apply -R` of the src diff -> `AssertionError: polled 3.299999999999999s on a rung that cannot recover`, `FAILED ...::test_return_at_the_terminal_replay_depth_does_not_poll_a_rung_that_cannot_recover`, `1 failed, 1 passed` (depth-0 test passes in both, so the poll is kept where it recovers). Red is on the named assertion, not an import error.
- Pre-check line in manifest is present, sha e865e298 matches the checked code head.

Metrics: start=2026-10-17T13:20:00Z end=2026-10-17T13:42:00Z wall_min=22 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=1320 mutants=0 defects_unit=0 defects_6c=0
slow: affected-test runs (modal/replay/traversal group) 4.6 min
