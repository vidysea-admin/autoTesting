# Verdict - t201c-inbox (re-check of the single cycle-1 defect)

**Cycle checked:** 2
**Verdict:** PASS
**Scope:** only the defect from qa/verdicts/t201c-inbox.md: DeliveryRecord rows with channel `inbox` (team-test-button.md changelog, D-093 item 2).

## Evidence
- Written at run completion, not on read: `ui/run_queue.py::RunQueue._finish` and `recover()` -> `_deliver` -> `stages/report_delivery.py::record_inbox_delivery`, using the existing `DeliveryRecord` schema and write-once `delivery/inbox.py` store. No new store, no new schema.
- Recipient is the presser's id, else the schedule owner found by email; nothing written while queued or running, or with no known recipient. Key is `delivery_key(run, inbox, user)`, so a second call is a no-op (`records_for_key`, plus `FileExistsError` guard).
- tests/test_inbox_delivery.py (7): done, failed and refused each give exactly one sent/inbox record for the right user; queued writes none; re-delivery and two restarts add nothing; reading /inbox three times adds nothing; a hostile requester name renders as escaped text on /inbox.
- tests/test_inbox_scope.py 9 passed (list derivation unchanged); delivery tests 63 passed; policy table and run_queue 21 passed; ruff clean; doctor clean.

## Limits
- Run ids and project slugs are validated, so XSS reachable through /inbox is via the requester field only; that is the case tested.
- Headed-browser smoke still not run (CPU shared).
