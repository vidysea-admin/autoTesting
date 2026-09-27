# Manifest — at571-ledger-json-parse
**Contract:** qa/contracts/core-invariants.md (C10 — the ledger never silently loses what the handshake recorded)
**Goal task:** none
**Date:** 2026-09-25
**Fix cycle:** 1 of max 3
**Dual check:** no
**Issues addressed:** AT-571 (medium, open -> fixed)
**Executor:** claude-opus-5-5 (maker orchestrator, inline — a 15-line single-function fix)
**Executor rationale:** tiny contained change found while reconciling the at562-564 doctor output; no subagent needed

## What changed
- src/autotester/ledger/checks.py — new `_status_by_id(text)` (JSON per line, skips non-object/unparseable lines, keeps only ids matching ISSUE_ID, last row wins) replaces the order-dependent regex `"id":\s*"(…)".*?"status":\s*"(\w+)"` in `check_qa_issue_rows`. Nothing else changed.
- tests/test_ledger_checks.py — `test_a_row_is_found_whatever_order_its_keys_are_in`: a status-first row named by a manifest must not be reported lost.

## How to verify (commands + expected)
- `uv run pytest tests/test_ledger_checks.py tests/test_doctor.py` → all pass
- `uv run ruff check src tests scripts` → clean
- `uv run autotester doctor` → clean

## Actual outputs (from maker's own run, commit 997d341)
- new test BEFORE the fix: `FAILED tests/test_ledger_checks.py::test_a_row_is_found_whatever_order_its_keys_are_in` / `1 failed, 28 passed in 1.47s`
- after: `41 passed in 0.49s` (test_ledger_checks + test_doctor)
- `All checks passed!` · `doctor: clean`
- Full suite: NOT RUN — RAM ~2.5 GB free (below the 3.5 GB floor). The change is confined to one doctor rule; declared as a gap.

## Capability coverage
| capability | check | falsifying edit | observed |
|---|---|---|---|
| a ledger row is found regardless of JSON key order | tests/test_ledger_checks.py::test_a_row_is_found_whatever_order_its_keys_are_in | in checks.py, put back `status_of = dict(re.findall(rf'"id":\s*"({ISSUE_ID})".*?"status":\s*"(\w+)"', text))` in place of `_status_by_id(...)` | before the fix (that exact code): `FAILED …::test_a_row_is_found_whatever_order_its_keys_are_in`, `1 failed, 28 passed`; with the fix: `41 passed`. The pre-fix run IS the falsification (same file, the one hunk). |
| id-first rows and all existing C10 behaviour unchanged | the 28 pre-existing tests in test_ledger_checks.py | — | `28 passed` before and within `41 passed` after |

## Live browser evidence
Not UI-touching — changed paths are src/autotester/ledger/checks.py and tests/test_ledger_checks.py only.

## Status: checked-PASS (qa/verdicts/at571-ledger-json-parse.md, Cycle checked: 1, 37f9956)
