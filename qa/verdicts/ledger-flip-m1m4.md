# Verdict — ledger-flip-m1m4 (Mode A, bookkeeping only)

**Cycle checked: 0**
**Bound to:** D:/autoTesting/.worktrees/int-1017 (branch int/1017). Inputs: .work/facts-m1..m4.md.
VERDICT: PASS (ledger close-out only; no product claim)

Method: opened every cited file:line at this HEAD; ran the cited test files in one `uv run pytest` of 20 named files (342 collected: 341 passed, 1 failed); edited each confirmed row IN PLACE in qa/issues.jsonl (no appended rows, ids unique, CRLF kept). `uv run autotester doctor` -> clean (no issue-id-duplicate).

Flipped to `fixed` (22): AT-655, ISS-t179b-hg1-1, ISS-t179b-hg1-2, AT-892, AT-588, ISS-t164-1, ISS-t168-damage-control-report-2, AT-787, AT-399, AT-407, AT-549, AT-544, AT-548, AT-708, AT-673, AT-648, AT-728, AT-582, AT-792, AT-794, AT-379, AT-735.
Flipped to `dismissed` (4, obsolete; the ledger has no `obsolete` status): AT-745, AT-318, AT-488, AT-460.

Refused (2):
- AT-743: `tests/test_goal_contract_registration.py::test_revised_goal_contract_is_registered` FAILS at this HEAD (`assert progress["total"] == len(data["tasks"])`, 92 == 106; .goal/goal.json progress is stale). The T-167 deps pin the row named is fixed, but the cited test is red, so the fact pass's "passes" is not reproduced. Stays open.
- AT-558: the cited evidence "worktree no longer exists" is wrong on disk: `.worktrees/t170-network-assertions/` still exists (unregistered, has `.venv`). The fix is process text only (qa/loop.md preflight) with no test; not confirmable as obsolete. Stays open.

Not in scope (GATE per the fact passes, untouched): AT-666, AT-327, AT-710, AT-718, AT-669.

Metrics: start=2026-10-17T00:00:00Z end=2026-10-17T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=0 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=unavailable mutants=0 defects_unit=1 defects_6c=0
