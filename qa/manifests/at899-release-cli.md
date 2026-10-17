# Manifest - at899-release-cli
**Contract:** qa/contracts/release-regression.md
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Dual check:** no
**Persona walk:** skip (CLI message and exit path only; persona-walk-release-manager steps 2,4,5 are the source of the issue and are covered by the four CliRunner tests)
**Issues addressed:** AT-899
**Executor:** claude-sonnet-subagent
**Executor rationale:** bounded CLI edit in two owned files; no external executor was worthy.

## What changed
- src/autotester/cli_release.py:26-72 - `_echo_scope` prints flows with case counts, case total, action budget, build and unplanned flows at the pause; `_echo_closing` gives approve ("approved by X: stopped at execute", `next:` release-log) and decline ("declined by X: nothing was run and no release record exists", `next:` new release) their own closing lines; "finished" now prints only when nothing is pending and the run was not declined.
- src/autotester/cli_release.py:release_cmd - catches the `ValueError` raised by `run_or_resume` for an answer on a release that is not paused and prints a one-line refusal (exit 1); a ValueError with no decision is re-raised unchanged.
- tests/test_cli_release.py:63-111 - four new scenario tests, one per criterion.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: M (CLI public surface; approval-flow adjacent, message/exit-path only - RunApproval and ReleaseDecision logic untouched)
Base / checked state: 69ebfae7 / f7605b35 (clean)
Gate answers: none; no new module (all code in the two owned existing files, cli_release.py now 143 lines)
Affected tests / full-suite trigger: tests/test_cli_release.py only; none. The builder runs no full suite.
Pre-check[C1]: f7605b35 uv run pytest tests/test_cli_release.py -> 8 passed t=4 blobs=tests/test_cli_release.py:9a0a54ad
Pre-check[C2]: f7605b35 uv run pytest tests/test_cli_release.py -> 8 passed t=4 blobs=tests/test_cli_release.py:9a0a54ad
Pre-check[C3]: f7605b35 uv run pytest tests/test_cli_release.py -> 8 passed t=4 blobs=tests/test_cli_release.py:9a0a54ad
Pre-check[C4]: f7605b35 uv run pytest tests/test_cli_release.py -> 8 passed t=4 blobs=tests/test_cli_release.py:9a0a54ad
Metrics: start=2026-10-17T00:00:00Z end=2026-10-17T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12

Criteria (AT-899 is one issue; its expected text is split into C1-C4):
- C1 the pause shows what is being approved (flows, case and action counts, build, unplanned flows)
- C2 approve says what happened and what to run next
- C3 decline says what happened, what to run next, and does not print "finished - see release-log"
- C4 a repeated answer is a clean one-line refusal, not a raw ValueError traceback

## How to verify (commands + expected)
- `uv run pytest tests/test_cli_release.py` -> expected: 8 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest tests/test_cli_release.py: `8 passed, 1 warning`
- ruff: `All checks passed!`
- doctor: `doctor: clean`

## Capability coverage (each new claim -> its isolating falsification)
Falsifying edit for every row: `git show 69ebfae7:src/autotester/cli_release.py` over the fix, run in a throwaway copy outside the worktree (scratchpad `fal/`), then the fix restored. Before the edit the whole file was `8 passed`; after it `4 failed, 4 passed`.

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | pause lists flows, case/action counts, build, unplanned flows | tests/test_cli_release.py::test_pause_shows_the_release_manager_what_he_is_approving | revert cli_release.py to base | green: `8 passed`; red: `AssertionError: assert 'flow f1 - 2 case(s)' in 'demo: release rel1\n  confirm  awaiting_human ...paused for your decision...'` |
| C2 | approve prints what happened and `next:` | tests/test_cli_release.py::test_approve_says_what_happened_and_what_to_run_next | revert cli_release.py to base | green: `8 passed`; red: `AssertionError: assert 'approved by rm' in 'demo: release rel1\n  confirm  done ... stopped at execute: no executor is wired...'` |
| C3 | decline says declined/nothing run/next, no "finished" | tests/test_cli_release.py::test_decline_does_not_claim_a_release_record_exists | revert cli_release.py to base | green: `8 passed`; red: `AssertionError: assert 'finished' not in 'demo: relea...' ... finished - see 'autotester release-log demo rel1'` |
| C4 | repeated answer is a one-line refusal, exit 1 | tests/test_cli_release.py::test_answering_an_already_answered_release_is_a_one_line_refusal | revert cli_release.py to base | green: `8 passed`; red: `AssertionError: assert (not True) where True = isinstance(ValueError('a human reply needs an existing paused release'), ValueError)` |

## Live browser evidence
Not UI-touching - no surface changed. Changed paths: src/autotester/cli_release.py, tests/test_cli_release.py (terminal CLI output only).

## Status: ready-for-check
