# Manifest - sheet-sync-hardening

**Contract:** qa/contracts/team-bug-loop.md (TB9, TB10, TB11, TB13 in part); criteria are the issue texts AT-981..AT-984, one each (C1..C4)
**Goal task:** none
**Date:** 2026-10-17
**Status:** checked-PASS (qa/verdicts/sheet-sync-hardening.md + sheet-sync-hardening.b.md, cycle 0, dual)
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** required
dual-trigger: security src/autotester/stages/sheet_write.py:89 (the outward-facing write barrier `_assert_writable`, AT-983) and security src/autotester/stages/sheet_plan.py:108 (sheet text scrubbed before show/hash/store, AT-981)
**Persona walk:** skip (no user-facing surface; stage and schema code behind a fake client)
**Issues addressed:** AT-981, AT-982, AT-983, AT-984
**Executor:** claude-sonnet-subagent
**Executor rationale:** four small edits in three existing files plus one test file; no external executor worthy.

## What changed
- src/autotester/stages/sheet_plan.py:57-61 - new `unguard` (the text a person sees, the `safe_cell` apostrophe removed). :88-115 `_row_for` now returns `(PlanRow | None, adopts)`: cells compare guard-normalised (AT-984); `CellChange.before` and `CellConflict.sheet_has` take `scrub(have)` (AT-981); a cell that already holds our (non-empty) value while memory lacks it is planned as an adoption (AT-982). :124-138 `plan_sync` collects `adopts` into the plan; :148 `render_plan` states the adoption count.
- src/autotester/schema/sheet_plan.py:108-119 - `SheetPlan.adopts` (bug key -> column -> value; memory only, no write), included in the plan hash only when non-empty so existing plan hashes are unchanged.
- src/autotester/stages/sheet_write.py:51-58,70-72,89-97,105-118 - `register_writer` allow-list (empty in production; only the test fake registers), `UnregisteredClient`, `_assert_writable` (live flag, then registered-class `isinstance`), called before the read path, after `client.read` and before each write (AT-983); `write_confirmed_plan` applies `plan.adopts` to memory before writing rows (AT-982). Module docstring step 1 updated.
- tests/sheet_fake.py - `FakeSheet` registered as a writer; new `StripGuardSheet` (drops the guard apostrophe on read-back).
- tests/test_sheet_sync_hardening.py (new, 6 tests, one or more per criterion).
- No new src module (qa/gates/new-module-authorization.md respected). Live sheet write stays gated (qa/gates/t199-first-live-write.md): no live client was called or added; `_WRITERS` is empty in production, so every non-fake client is refused.
- Nothing existing deleted or renamed. Files: sheet_plan.py 160, sheet_write.py 123, schema/sheet_plan.py 161, sheet_fake.py 67 lines (cap 300).
- Order note (honest): the fix was written before the new tests; red-first was then proven by reverting each fix hunk in a throwaway copy (below), not by a failing test before the edit.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: L (prod-write barrier and secret redaction; security trigger), dual check required
Base / checked state: base 69ebfae7, code at b3844a0d, clean tree
Gate answers: qa/gates/t199-first-live-write.md stays OPEN: the unit adds no live client and makes the refusal stricter (unregistered clients refused too).
Affected tests / full-suite trigger: tests/test_sheet_sync_hardening.py, tests/test_sheet_plan.py, tests/test_sheet_sync_tb12_tb14.py. Other importers of sheet_write (tests/test_tracker_page.py imports only `LiveWriteRefused`, unchanged). The builder ran no full suite.
Pre-check[C1]: b3844a0d uv run pytest tests/test_sheet_sync_hardening.py -> 6 passed, 1 warning t=2 blobs=tests/test_sheet_sync_hardening.py:2944d60,tests/sheet_fake.py:2a834a7
Pre-check[C2]: b3844a0d uv run pytest tests/test_sheet_sync_hardening.py -> 6 passed, 1 warning t=2 blobs=tests/test_sheet_sync_hardening.py:2944d60,tests/sheet_fake.py:2a834a7
Pre-check[C3]: b3844a0d uv run pytest tests/test_sheet_sync_hardening.py -> 6 passed, 1 warning t=2 blobs=tests/test_sheet_sync_hardening.py:2944d60,tests/sheet_fake.py:2a834a7
Pre-check[C4]: b3844a0d uv run pytest tests/test_sheet_sync_hardening.py -> 6 passed, 1 warning t=2 blobs=tests/test_sheet_sync_hardening.py:2944d60,tests/sheet_fake.py:2a834a7
Metrics: start=2026-10-17T10:00:00Z end=2026-10-17T10:40:00Z wall_min=40 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=8 mutants=5 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_sheet_sync_hardening.py tests/test_sheet_plan.py tests/test_sheet_sync_tb12_tb14.py` -> expected: 37 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- the three sheet test files: `37 passed, 1 warning in 8.03s`
- ruff: `All checks passed!`; doctor: `doctor: clean`

## Capability coverage (each new claim -> its isolating falsification)
Falsification ran in a throwaway copy outside the worktree (`.../scratchpad/fals2`, PYTHONPATH pointed at the copy's src), each hunk reverted, the named node run, then restored and re-run.

| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 (AT-981) | sheet-side text is scrubbed before plan/render/hash | tests/test_sheet_sync_hardening.py::test_at981_a_secret_typed_into_a_sheet_cell_is_in_no_plan_text_or_hash_input | sheet_plan.py `before=scrub(have)` -> `before=have`, `sheet_has=scrub(have)` -> `sheet_has=have` | green: `1 passed, 1 warning in 1.28s`; red: `E assert not True` / `E + where True = any(<generator ...>)` / `1 failed` |
| C2 (AT-982) | a retry after a write that landed adopts the equal cell into memory | ...::test_at982_a_retry_after_a_write_that_landed_does_not_make_a_later_change_a_conflict | sheet_plan.py `if new and last != new:` -> `if False:` | green: `1 passed, 1 warning in 0.97s`; red: `AssertionError: assert ([] == [] ... Right contains 1 more item: {'bug_000000000001': {'Status': 'fixed'}}` |
| C3 (AT-983) a | a non-fake class claiming live=False is refused | ...::test_at983_a_client_that_only_claims_live_false_is_not_written_to | sheet_write.py `if not isinstance(client, tuple(_WRITERS)):` -> `if False:` | green: `1 passed, 1 warning in 1.80s`; red: `Failed: DID NOT RAISE WriteRefused` |
| C3 (AT-983) b | `live` is re-checked after the read (and before each write) | ...::test_at983_a_client_that_turns_live_during_the_read_is_not_written_to | sheet_write.py both post-read and per-row `_assert_writable(client)` calls removed | green: `1 passed, 1 warning in 1.70s`; red: `Failed: DID NOT RAISE LiveWriteRefused` |
| C4 (AT-984) | guarded value read back without the apostrophe is not a conflict | ...::test_at984_a_sheet_that_strips_the_formula_guard_reports_no_conflict_and_converges | sheet_plan.py `unguard(have) == unguard(new)` -> `have == new` and `unguard(have) == unguard(last)` -> `have == last` | green: `1 passed, 1 warning in 2.10s`; red: `Left contains one more item: PlanRow(action='conflict' ... CellConflict(column='Title', sheet_has='-5', we_last_wrote="'-5", ...)` |

## Live browser evidence
Not UI-touching - no surface changed. Changed paths: src/autotester/stages/sheet_plan.py, src/autotester/stages/sheet_write.py, src/autotester/schema/sheet_plan.py, tests/sheet_fake.py, tests/test_sheet_sync_hardening.py (no UI route or template).

## Status: checked-PASS (qa/verdicts/sheet-sync-hardening.md + sheet-sync-hardening.b.md, cycle 0, dual)
