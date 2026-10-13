# Verdict — proposal-review-ui

**Cycle checked:** 1
**Result:** PASS (supplies the GA5 UI route; T-169 GA5 closes once the harness drives this route instead of the `ModeSeams.review_proposals` seam)
**Checker:** independent subagent

## Re-run myself
- tests/test_proposal_review_ui.py, test_ui_auth_policy_table.py, test_routers_list.py: 13 passed.
- `ruff check src tests scripts`: clean. `autotester doctor` (re-run after the MAP regeneration): clean.

## Read against the criteria
- Stage and review both call `expand.stage_and_review` (the CLI's function); list reads `ProjectStore.list_case_proposals`, filtered to the current FlowSpec fingerprint.
- Policy: GET `/proposals` = project.view; POST `/proposals/stage` and `/review` = project.edit; rows added to `ROUTE_POLICY` and the policy-table test, no existing row changed.
- Bulk with any absent or stale id returns 404 before any write (all-or-nothing); test asserts nothing changed.
- Signed name required (empty refused 400), also passed through `_refuse_unsafe_submission`.
- Labels: row checkbox aria-label, label-for title, scoped headers, aria-label on row buttons; test passes.
- Escaping: title, rationale, flow name, screen, reviewer all via `html.escape`.
- HAPPY prune stays pending (schema rule), tested.

## Browser smoke (headed Chromium, throwaway root and admin account, removed afterwards)
Approved FlowSpec whose flow name held `<img src=x onerror=window.__xss=1>`. Opened /proposals, clicked "Propose cases for review" (10 rows), signed "Checker Q", approved row 1: it showed "APPROVED by Checker Q", other 9 PROPOSED. `window.__xss` stayed undefined.

## Non-blocking
No test uses a hostile title on this page; covered by code read and the smoke.
