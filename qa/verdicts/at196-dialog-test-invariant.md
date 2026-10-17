# Verdict - at196-dialog-test-invariant

Cycle checked: 0
Date: 2026-10-17
Bound to: D:/autoTesting/.worktrees/at196-dialog-test-invariant (base 69ebfae7 via git merge-base HEAD master; head 0e2dd45d)
Policy-Version: proportional-verification/2026-10-15.12

## Check plan
Diff is one file, tests/test_explore_live.py (+ helper `_assert_crawl_not_trapped`, 3 browser-free tests, 2 imports). Logic changed: a test assertion. Tier L (protected test change: an assertion was weakened from a 2-value set to "not QUEUED"), judged against AT-196's own fix direction. Signals: affected tests (the file), lint, doctor, one falsification (C1). No UI, no security, no data. Lane: quick lane not used (protected test change; lane=normal).

## Evidence (all run by the checker)
- `uv run pytest tests/test_explore_live.py` -> `11 passed, 1 warning in 124.73s`.
- `uv run ruff check src tests scripts` -> `All checks passed!`; `uv run autotester doctor` -> `doctor: clean` (2 known-disputed D-087 advisories only).
- Falsification C1, throwaway copy outside the worktree (scratchpad/fals196/test_fals.py): green before `3 passed, 8 deselected in 16.89s`; after replacing the one assertion line with `assert dialog.status.value in ("aborted_dialog", "explored")`: `E AssertionError: assert 'aborted_error' in ('aborted_dialog', 'explored')`, `1 failed, 2 passed` (only test_a_load_induced_aborted_error_on_the_dialog_node_is_not_a_trapped_crawl reddens; the queued/unfinished tests stay green); restored copy -> `3 passed`. Worktree `git status --short` empty afterwards.
- Diff-scope (4c): `git diff 69ebfae7 -- tests/test_explore_live.py` read in full. Removed lines: the `nodes = {...}` dict line inline and the `assert dialog_node.status.value in (...)` line. Nothing else removed; no skip/xfail; no src/ file touched; no conftest/fixture change.

## Weakening judgement (protected test change)
AT-196 text (qa/issues.jsonl): assert the node "reached SOME terminal status (not left pending/queued) plus finished_at, so the test fails when the crawl hangs ... and not when a busy host times a navigation out". The new assertion is exactly that: `crawl.finished_at is not None` kept, and `dialog.status is not NodeStatus.QUEUED`. The old set never asserted `aborted_dialog` specifically (it also accepted `explored`), so no X8 behaviour assertion was lost; the circuit-breaker contract X8 (qa/contracts/explore.md:99-103) is "abort that node and let the crawl continue rather than hang", which is what finished_at + left-the-frontier carries. Beyond the old set the new one also admits `aborted_error` (the AT-196 case) and `skipped_unchanged` (cannot occur on a persona-free crawl). The issue's "exactly three terminal values" is inaccurate (NodeStatus has five, src/autotester/schema/enums.py:263-272); the maker's "anything but QUEUED" is the correct terminal set. Not a weakening beyond what AT-196 asks. The two negative tests (`..._left_queued_...`, `..._never_finished_...`) pin that a hung crawl still fails.

Non-blocking note (not filed, pre-existing, unchanged): `if dialog is not None` lets the invariant pass vacuously if /dialog.html was never discovered.

```
VERDICT: PASS
SCOREBOARD: 1/1 criteria met, core-invariants none-touched (no src/ change)
TIER: L (protected test change: assertion widened from {aborted_dialog, explored} to not-QUEUED; justified by AT-196 text; test-only, one checker)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced
LIVE-BROWSER: not-applicable (tests/test_explore_live.py only)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The test now asserts the invariant it is named for (crawl finished, dialog node left the frontier), a load-induced aborted_error no longer reds it, and a queued node or unfinished crawl still does; reproduced green-before/red-after on the named assertion. Weakening is exactly what AT-196 asks and no more.
Metrics: start=2026-10-17T18:10:00 end=2026-10-17T18:30:00 wall_min=20 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
```
