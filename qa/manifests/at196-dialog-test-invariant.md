# Manifest - at196-dialog-test-invariant

**Contract:** qa/contracts/explore.md (X8) + qa/contracts/core-invariants.md
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** no
**Persona walk:** skip (test-only diff, no user-facing flow)
**Issues addressed:** AT-196
**Executor:** claude-sonnet-subagent
**Executor rationale:** S-tier test-only change in one file; nothing external was worthy.

## What changed
- tests/test_explore_live.py:139-176 - `test_the_dialog_page_does_not_trap_the_crawl` now delegates to new `_assert_crawl_not_trapped`, which asserts `crawl.finished_at is not None` and that the `/dialog.html` node left the frontier (`status is not NodeStatus.QUEUED`) instead of enumerating `('aborted_dialog','explored')`. A load-induced `aborted_error` no longer reds the suite; a crawl that hangs (unfinished, or node stuck QUEUED) still does.
- tests/test_explore_live.py: three browser-free tests pin the invariant: `test_a_load_induced_aborted_error_on_the_dialog_node_is_not_a_trapped_crawl` (the AT-196 scenario), `test_a_dialog_node_left_queued_is_a_trapped_crawl`, `test_a_crawl_that_never_finished_is_a_trapped_crawl`. Imports `NodeStatus`, `ScreenNode` added.
- No file under src/ changed. Note: NodeStatus has five values (queued, explored, aborted_dialog, aborted_error, skipped_unchanged), not three as the issue text says; "any status but QUEUED" is the terminal set.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: S (test-only: tests/test_explore_live.py; not conftest/fixtures; no security/auth/tenancy/prod-write trigger)
Base / checked state: 69ebfae7 + dirty diff, tests/test_explore_live.py blob 497238a
Gate answers: none (no gate touched)
Affected tests / full-suite trigger: tests/test_explore_live.py only; none. The builder runs no full suite.
Pre-check[C1]: 69ebfae7 uv run pytest tests/test_explore_live.py -> 11 passed t=120 blobs=tests/test_explore_live.py:497238a
Metrics: start=2026-10-17T17:35:00 end=2026-10-17T18:05:00 wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=0 mutants=1 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_explore_live.py` -> expected: 11 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest tests/test_explore_live.py: `11 passed, 1 warning in 120.61s (0:02:00)`
- ruff: `All checks passed!`
- doctor: `doctor: clean` (2 advisory known-disputed D-087 findings, non-blocking, pre-existing)

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | a finished crawl whose dialog node aborted with ABORTED_ERROR (load-induced timeout) satisfies X8; a hung crawl still fails it | tests/test_explore_live.py::test_a_load_induced_aborted_error_on_the_dialog_node_is_not_a_trapped_crawl (+ `..._left_queued_...`, `..._never_finished_...`) | revert the one assertion line in `_assert_crawl_not_trapped` to `assert dialog.status in ("aborted_dialog", "explored")` (throwaway copy at D:/autoTesting/.work/fals196, outside the worktree, since deleted) | before (fix): `3 passed, 8 deselected in 21.04s`; after (hunk reverted): `E   AssertionError: assert <NodeStatus.ABORTED_ERROR: 'aborted_error'> in ('aborted_dialog', 'explored')` / `FAILED ..\..\.work\fals196\test_fals.py::test_a_load_induced_aborted_error_on_the_dialog_node_is_not_a_trapped_crawl` / `1 failed, 2 passed, 8 deselected in 12.21s` (the two queued/unfinished tests stay green, so only the targeted node reddens, on its assertion, not an import error) |

## Live browser evidence
Not UI-touching - no surface changed (only tests/test_explore_live.py).

## Status: checked-PASS (qa/verdicts/at196-dialog-test-invariant.md, cycle 0)
