# Manifest — at929-proposal-scrub
**Contract:** qa/contracts/expand.md (criterion C1 = AT-929 expected text)
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** required
dual-trigger: security src/autotester/stages/expand.py:181
**Persona walk:** skip (no human screen changed; stage-layer store write)
**Issues addressed:** AT-929
**Executor:** claude-sonnet-subagent
**Executor rationale:** single-file S unit, file-disjoint from every other wave unit

## What changed
- src/autotester/stages/expand.py:162-177 — new `_scrub_proposals`: scrubs each staged proposal's title and rationale with the project redactor (id recomputed), refuses a `--by` or a flow id that matches a stored secret (neither can be masked: attribution and the FlowSpec link). No-op when no project/secrets exist.
- src/autotester/stages/expand.py:181 — `stage_and_review` stages the scrubbed rows (the scrub call).
- tests/test_expand_redaction.py:+57 — 4 AT-929 tests (name holding a secret, --by = secret, flow id = secret, ordinary reviewer unchanged).
- not touched: src/autotester/cli.py, src/autotester/store/project_store.py (both at the 300-line cap).

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: L (security: secret scrub on stored/model-bound proposals; dual check)
Base / checked state: base 69ebfae7, head b5d83803 (clean worktree)
Gate answers: none applicable (no new module; qa/gates/new-module-authorization.md not needed)
Affected tests / full-suite trigger: tests/test_expand_redaction.py, tests/test_expand.py, tests/test_expand_cli.py; no full-suite trigger.
Pre-check[C1]: b5d83803 uv run pytest tests/test_expand_redaction.py -> 27 passed t=33 blobs=tests/test_expand_redaction.py:c717628
Pre-check[C1]: b5d83803 uv run pytest tests/test_expand.py tests/test_expand_cli.py -> 25 passed t=24 blobs=tests/test_expand.py:3478be8,tests/test_expand_cli.py:202958c
Metrics: start=2026-10-17T12:30:00Z end=2026-10-17T12:50:00Z wall_min=20 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=0 mutants=1 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_expand_redaction.py` → expected: 27 passed
- `uv run pytest tests/test_expand.py tests/test_expand_cli.py` → expected: 25 passed
- `uv run ruff check src tests scripts` → expected: All checks passed!
- `uv run autotester doctor` → expected: doctor: clean

## Actual outputs (from maker's own run)
- redaction file: 27 passed in 32.68s; expand + expand_cli: 25 passed in 24.15s
- ruff: All checks passed!; doctor: clean; expand.py 254 lines (cap 300)

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | case_proposals.jsonl title/rationale are scrubbed; a secret in --by or flow id is refused unstored | tests/test_expand_redaction.py::test_a_flow_name_holding_a_secret_is_not_stored_in_case_proposals_jsonl, ::test_a_reviewer_name_that_is_a_declared_secret_is_refused_and_never_stored, ::test_a_flow_id_that_is_a_secret_is_refused_not_stored (expand.py:167-168) | in a throwaway copy outside the worktree, make `_scrub_proposals` return rows unchanged (delete the `if secrets is None: return rows` guard's body path so it always returns) | green before: 27 passed (full file). red after (same 3 nodes, assertion errors): "E assert ('Hunter2-Zebra-4411' not in '{\"schema_ve...proposed\"}\n' ... 'Hunter2-Zebra-4411' is contained here: ...Sign in Hunter2-Zebra-4411 Other-Projects-Key-9082"; "E Failed: DID NOT RAISE ValueError" x2; "3 failed, 1 passed, 23 deselected" (the ordinary-reviewer test stays green). Then restored: 27 passed. |

## Live browser evidence
Not UI-touching — no surface changed (changed paths: src/autotester/stages/expand.py, tests/test_expand_redaction.py)

## Status: ready-for-check
