# Manifest — crawl-approval-by-id
**Contract:** qa/contracts/consent.md (line 133, `check_crawl_approval.py` is T-145's `done_check`)
**Goal task:** T-145 (follow-up)
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Dual check:** no
**Persona walk:** skip (script and test only, no UI surface)
**Issues addressed:** AT-999
**Executor:** claude-sonnet-subagent
**Executor rationale:** S unit, two owned files, brief from the maker.

## What changed
- scripts/check_crawl_approval.py:45-69 — `_tracked_ids` (git ls-files, fail closed) and `_pick_summary` (optional crawl id, tracked + finished only); main :71-120 takes `<slug> [<crawl-id>]`; docstring updated.
- tests/test_check_crawl_approval.py — new, 4 tests building a throwaway git repo via AUTOTESTER_ROOT and running the real script.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: L (approval-gate script, security-adjacent; no prod-write or auth barrier touched, so no dual-trigger)
Base / checked state: base 69ebfae7, code commit b85086f4 (scripts/check_crawl_approval.py blob de5af1b)
Gate answers: none; no gate applies (no new src/ module).
Affected tests / full-suite trigger: tests/test_check_crawl_approval.py only; none. The builder runs no full suite.
Pre-check[C1]: b85086f4 uv run pytest tests/test_check_crawl_approval.py -> 4 passed t=143 blobs=tests/test_check_crawl_approval.py:89418b5
Metrics: start=2026-10-17 end=2026-10-17 wall_min=45 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=143 mutants=2 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_check_crawl_approval.py` -> expected: 4 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest: `4 passed, 1 warning in 143.29s`; ruff: `All checks passed!`; doctor: `doctor: clean`.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 | the script takes an optional crawl id and judges only git-tracked summaries (an untracked newer leftover is never judged) | tests/test_check_crawl_approval.py (4 nodes) | (a) revert the whole fix hunk to HEAD~ script, copy outside the worktree; (b) replace `tracked = _tracked_ids(store)` with all on-disk ids | green@b85086f4: `4 passed`. (a) red: `4 failed` on `assert (1 == 0)`, `assert (2 == 0)` (usage exit), `assert (2 == 1)`, `assert (0 == 1)` for test_untracked_newer_leftover_summary_is_not_judged_instead_of_the_reviewed_crawl, test_a_crawl_id_argument_judges_that_committed_summary_not_the_newest, test_a_crawl_id_naming_an_untracked_summary_is_refused_not_judged, test_only_untracked_summaries_fail_closed. (b) red: `3 failed, 1 passed`: test_untracked_newer_leftover_summary_is_not_judged_instead_of_the_reviewed_crawl `assert (1 == 0)`; test_a_crawl_id_naming_an_untracked_summary_is_refused_not_judged `assert (0 == 1)`; test_only_untracked_summaries_fail_closed `assert (0 == 1)`. Restored copy green again (4 passed). |

## Live browser evidence
Not UI-touching — no surface changed (changed paths: scripts/check_crawl_approval.py, tests/test_check_crawl_approval.py).

## Status: checked-PASS (qa/verdicts/crawl-approval-by-id.md, cycle 0)
