# Manifest - delivery-run-id-guard (test-only: AT-967)

Contract: qa/contracts/team-test-button.md (TT9: the run page shows one run's delivery attempts); issue AT-967 (feature t201a-delivery-core)
Issues addressed: AT-967 (one criterion: C1 = records_for_run returns only its own run for ids that differ where `.` would match)
Fix cycle: 0
Dual check: no - test-only; no product, security, auth or tenancy code edited
Executor: claude-sonnet-subagent (maker build subagent), 2026-10-17

## What changed
- tests/test_delivery_records_for_run.py:1-52 - new test file (test only): `run.1`/`run-1`, `run.`/`run-`, `run-1.`/`run-1-` each get records for two users; `records_for_run(id)` must return only that id's own records. Second test: an id with no records returns `[]` beside a dotted/dashed neighbour.
- falsified (unchanged): src/autotester/delivery/inbox.py - line 131 `re.escape(_encode_part(run_id))`; no product line changed.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: S (test only, no product file changed)
Base / checked state: base 69ebfae7; test commit ac849116 (tests/test_delivery_records_for_run.py blob 9fb97ff)
Gate answers: none; no new module (new test file only)
Affected tests / full-suite trigger: tests/test_delivery_records_for_run.py only; none
Pre-check[C1]: ac849116 uv run pytest tests/test_delivery_records_for_run.py -> 4 passed t=4 blobs=tests/test_delivery_records_for_run.py:9fb97ff
Metrics: start=2026-10-17T00:00:00Z end=2026-10-17T00:00:00Z wall_min=10 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal

## How to verify (commands + expected)
- `uv run pytest tests/test_delivery_records_for_run.py` -> expected: 4 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest: `4 passed, 1 warning` (the warning is a starlette/anyio DeprecationWarning, unrelated).
- ruff: `All checks passed!`
- doctor: `doctor: clean` (2 advisory decision-citation-known-disputed notes, non-blocking, D-087).

## Capability coverage (each new claim -> its isolating falsification)

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | `records_for_run` matches a run id exactly, so a dotted id never pulls in a dashed lookalike's records | tests/test_delivery_records_for_run.py::test_a_dotted_run_id_does_not_pull_in_the_records_of_its_dashed_lookalike[run.1-run-1], [run.-run-], [run-1.-run-1-] and ::test_a_run_id_with_no_records_returns_nothing_next_to_a_dotted_neighbour | in a throwaway copy OUTSIDE the worktree (scratchpad falsify-967, `PYTHONPATH` at the copy, `autotester.__file__` printed inside it), src/autotester/delivery/inbox.py:131 `re.escape(_encode_part(run_id))` -> `_encode_part(run_id)` | GREEN before (copy with re.escape): `4 passed, 1 warning`. RED after (re.escape dropped): `FAILED ...[run.1-run-1]`, `FAILED ...[run.-run-]`, `FAILED ...[run-1.-run-1-]`, `FAILED ...test_a_run_id_with_no_records_returns_nothing_next_to_a_dotted_neighbour`; `4 failed`; the assertion that fired: `AssertionError: assert ['alice', 'al... 'bob', 'bob'] == ['alice', 'bob']` (records_for_run('run.1') also returned run-1's rows), not an import error. Re-restored re.escape: 4 passed. |

## Live browser evidence
Not UI-touching - no surface changed. Changed path: tests/test_delivery_records_for_run.py (test only).

## Status: merged-no-check (test-lane)
