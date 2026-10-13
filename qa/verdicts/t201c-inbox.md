# Verdict - t201c-inbox

**Cycle checked:** 1
**Verdict:** FAIL (one defect; everything else holds)
**Checked at:** branch wave/t201c-inbox with master merged (9b75a83f).

## Rulings
- (a) "One stored value" for the report label: ACCEPTED as computed on read. The contract's own test is "defined once, read by inbox, page and message" (grep test + mutation), and `report_label` is the single definition (tests/test_inbox_scope.py, label_defined_once). A stored copy would be a second source that can drift from the verdicts. Not a defect.
- (b) DeliveryRecord rows for the inbox channel: REQUIRED. Contract changelog 2026-10-13 (D-093 item 2, qa/contracts/team-test-button.md:202) says "A DeliveryRecord with channel `inbox` is still written; email/outbox records apply only once email is built." The branch writes none (src/autotester/stages/report_delivery.py, ui/routes_inbox.py; the manifest admits it). `DeliveryRecord`, `DeliveryChannel` and the write-once store (delivery/inbox.py) already exist, so nothing blocks it. DEFECT.

## Passed
- Scope: only `inbox_for` -> central `authorize(report.view, resource_for(project))` per project (report_delivery.py:60); no parallel logic. Route policy row `GET /inbox` = report.view, no new key.
- 4 users x 2 projects x {list, direct URL}, cross-user isolation, hidden vs missing identical 404, refused/interrupted/low-coverage/all-blocked labels, queued position with a real one-slot RunQueue.
- Labelled controls (th scope, table aria-label, per-link aria-label). Project, run id, requester and link are all html-escaped in inbox_view.py (no raw interpolation found).
- Run: test_inbox_scope + test_ui_auth_policy_table + test_routers_list + run_queue tests = 38 passed; ruff clean.

## Not done
- Headed-browser two-user smoke not run: the machine is saturated by the live sweep (the 38-test run took 7.5 min). Scope is covered by the TestClient table instead. Owed on re-check if wanted.
- No XSS-payload test exists; escaping verified by reading only. Recommend adding one with the DeliveryRecord fix.

## Fix required (cycle 2)
Write one `DeliveryRecord(channel=inbox, status=sent, recipient_user_id=requester or schedule owner)` per finished request via the existing write-once store, with a test (record exists for done/failed/refused; none for queued; no duplicate on re-read), without changing the derive-on-read list.
