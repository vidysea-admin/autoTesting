# Manifest — at656-status-by-id
**Contract:** qa/contracts/living-ledger.md (L8 bullet 3)
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** no
**Persona walk:** skip (backend-only: one ledger reader, no screen)
**Issues addressed:** AT-656 (high, open -> fixed)
**Executor:** claude-sonnet-subagent
**Executor rationale:** Tier S, one function plus its tests; nothing external was worthy.

## What changed
- src/autotester/ledger/checks.py:141-162 — `_status_by_id` collects every status per id; a repeated id reads as `conflict:<sorted distinct statuses>`, never one row's status. New `_is_open` (:158) treats `open` or a conflict containing `open` as open; `check_qa_issue_rows` :198 uses it, so a PASSed unit's claimed fix is flagged `ledger-row-stale` while any twin row is still `open`. File stays 298/300 lines.
- tests/test_ledger_checks.py:272-299 — four-case stale parametrization (open/verified, verified/open, open/fixed -> stale; fixed/verified -> clean) and a reader test (repeated id never reads as a plain status; unique id still plain). File 299/300 lines.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: S (one function, <=12 net lines because ledger/checks.py was 288/300)
Base / checked state: fcedc9f4 / bdfd4c5f642dd1bd260640f1921995f9dcc6f461 (clean tree)
Gate answers: none (no security/auth/tenancy/prod-write trigger; single checker)
Affected tests / full-suite trigger: tests/test_ledger_checks.py, tests/test_issue_ids.py (the other reader of the same ledger); no full-suite trigger; builder ran no full suite.
Pre-check[C1]: bdfd4c5f uv run pytest tests/test_ledger_checks.py tests/test_issue_ids.py -> 41 passed t=11 blobs=tests/test_ledger_checks.py:b314c9a,tests/test_issue_ids.py:c892ab8
Metrics: start=2026-10-17T09:30:00Z end=2026-10-17T09:50:00Z wall_min=20 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=11 mutants=1 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_ledger_checks.py tests/test_issue_ids.py` → expected: 41 passed
- `uv run ruff check src tests scripts` → expected: All checks passed!
- `uv run autotester doctor` → expected: `doctor: clean` (in this worktree)

## Actual outputs (from maker's own run)
- pytest: `41 passed, 1 warning in 1.77s`
- ruff: `All checks passed!`
- doctor: `doctor: clean`

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | a repeated id never reads as one clean status; an open twin keeps a PASSed unit stale | tests/test_ledger_checks.py::test_a_repeated_id_with_an_open_twin_still_makes_a_passed_unit_stale, ::test_the_reader_never_reports_one_clean_status_for_a_repeated_id | throwaway copy outside the worktree with checks.py restored to base fcedc9f4 (last-wins `out[id] = status`) | green@bdfd4c5f: `41 passed`; red on base: `AssertionError: assert ('ledger-row-stale' in []) is True` (statuses0, statuses2) and `assert 'verified' not in {'fixed', 'open', 'verified'}` (reader, both cases); `4 failed, 31 passed` |

## Live browser evidence
Not UI-touching — no surface changed (src/autotester/ledger/checks.py and tests/test_ledger_checks.py only).

## Status: ready-for-check
