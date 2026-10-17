# Manifest — at711-evidence-specs
**Contract:** none yet (checker-owned; wording for AT-711 to be folded in by /checker via qa/feedback-inbox.md)
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Dual check:** no
**Persona walk:** skip (no user-facing surface)
**Issues addressed:** AT-711
**Executor:** claude-sonnet-subagent
**Executor rationale:** tier M single-file build unit from a maker brief

## What changed
- src/autotester/ledger/evidence_specs.py:25-31,157-243 — adds `record_tree`, `check_capability_row_tree`, `tree_disclosures` (+ private helpers): a capability row names `tree: head=<sha> porcelain=<clean|digest>`; the check COMPARES the recorded head with the submitted commit (equal, or only `qa/manifests/` paths between them); a row naming no tree is refused; a non-clean digest is disclosure only. Read-only git via argv list, no shell.
- tests/test_evidence_spec_tombstones.py:176-end — four real-git scenario tests (dirty tree at submitted HEAD; clean tree at wrong commit; row with no tree; manifest-only follow-up commit). Existing tests untouched.
- Not done (outside the owned files): wiring into `doctor.run` / the checker's step. The functions are the comparison; a caller passes the submitted commit.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: M (new rule on an existing module; no security/auth/tenancy/prod-write trigger)
Base / checked state: fcedc9f4 / code commit 6a0052cf, clean tree
Affected tests / full-suite trigger: tests/test_evidence_spec_tombstones.py only; none
Pre-check[C1]: 6a0052cfda02d4913f75bcaa33a37989cbbde15c uv run pytest tests/test_evidence_spec_tombstones.py -> 18 passed t=21 blobs=tests/test_evidence_spec_tombstones.py:0a8809c
Metrics: start=2026-10-17 end=2026-10-17 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal

## How to verify (commands + expected)
- `uv run pytest tests/test_evidence_spec_tombstones.py` -> expected: 18 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: `doctor: clean`

## Actual outputs (from maker's own run)
- pytest: `18 passed, 1 warning in 4.12s`; ruff: `All checks passed!`; doctor: `doctor: clean`.
- TDD red: before implementing, the new tests failed at collection (`ImportError` for `check_capability_row_tree`/`record_tree`/`tree_disclosures`).

## Capability coverage (each new claim -> its isolating falsification)
Throwaway copy of `src/autotester` + the test file under the session scratchpad (outside the repo), imported via PYTHONPATH (verified `autotester.__file__` points into the copy). Each named test was GREEN in the copy first.

| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 | a row run on a clean tree at the WRONG commit is refused (comparison, not recording) | `test_a_row_on_a_clean_tree_at_the_wrong_commit_is_refused` | `_head_covers`: drop the equality test, `return True` | PASS before: `1 passed in 6.19s`. FAIL after: `AssertionError: assert [] == ['capability-...ree-mismatch']` tree: head=6a0052cfda02d4913f75bcaa33a37989cbbde15c porcelain=clean |
| C1 | a row naming no tree is refused | `test_a_row_naming_no_tree_at_all_is_refused` | `check_capability_row_tree`: `if found is None: continue` | PASS before: `1 passed in 4.15s`. FAIL after: `AssertionError: assert [] == ['capability-...e-unrecorded']` tree: head=6a0052cfda02d4913f75bcaa33a37989cbbde15c porcelain=clean |
| C1 | a dirty digest is disclosure, not disqualification | `test_a_row_run_on_a_dirty_tree_at_the_submitted_head_passes_with_disclosure` | add `found.group(2) != 'clean' or` to the mismatch condition | PASS before: `1 passed in 4.27s`. FAIL after: `assert [Violation(ru...260e7f6a668')] == []` (a capability-row-tree-mismatch on same head) tree: head=6a0052cfda02d4913f75bcaa33a37989cbbde15c porcelain=clean |

(A fourth falsification, removing the manifest-only allowance in `_head_covers`, also reddened `test_a_row_recorded_at_the_code_commit_survives_a_manifest_only_follow_up`; omitted from the table for the tier-M mutant cap.)

## Live browser evidence
Not UI-touching — no surface changed (changed paths: src/autotester/ledger/evidence_specs.py, tests/test_evidence_spec_tombstones.py).

## Status: ready-for-check
