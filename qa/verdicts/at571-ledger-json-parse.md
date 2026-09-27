# Verdict — at571-ledger-json-parse

**Date:** 2026-09-25 · **Head checked:** 58db050 (fix 997d341, base master 78c21f1) · **Cycle checked: 1** (manifest Fix cycle: 1 of max 3) · **Contract:** qa/contracts/core-invariants.md C10

```
VERDICT: PASS
SCOREBOARD: 1/1 criteria met (C10: the ledger never silently loses what the handshake recorded), 1/1 invariants hold
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced (throwaway copy; green before, red on the named test after)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/ledger/checks.py, tests/test_ledger_checks.py)
ISSUES-WRITTEN: none (AT-571 flips open->fixed when the merge lands on master)
EXECUTOR: maker orchestrator inline (checker: claude-opus-session, checker seat)
EXPLANATION: check_qa_issue_rows now reads each line with json.loads, so key order cannot hide a row. On the live ledger (564 ids) the old regex and the new parser give an identical id->status map, so no behaviour changes for existing rows; last-row-wins on the AT-553 duplicate ids is preserved. Non-blocking gap (maker's reviewer noted it too): no test asserts that a valid-JSON non-object line is skipped.
```

## What I re-ran

- `pytest tests/test_ledger_checks.py tests/test_doctor.py` (throwaway copy) -> `41 passed`.
- `ruff check src tests scripts` -> All checks passed · `autotester doctor` -> clean.
- Every non-browser test file (throwaway copy) -> `1 failed, 1545 passed, 5 skipped`; the one failure is `test_ui_sources.py::test_uploaded_recordings_are_gitignored`, which needs `.git` (absent from copies) and passes in a real checkout. Net: all green.
- Capability row: in a copy, restored the old line `status_of = dict(re.findall(... "id" ... "status" ...))` in place of `_status_by_id(...)` -> `1 failed, 28 passed`, `FAILED test_a_row_is_found_whatever_order_its_keys_are_in` with `ledger-row-lost … AT-900` (the named assertion).
- Old-vs-new parser map on the live `qa/issues.jsonl`: `564 564 diffs: {}`.
- Diff scope 78c21f1..58db050: 3 files (manifest, checks.py, test file), all listed; 2 lines removed, both the replaced regex call. Hunted for other key-order regexes over the ledger in src/ and scripts/: none.

## Status: PASS
