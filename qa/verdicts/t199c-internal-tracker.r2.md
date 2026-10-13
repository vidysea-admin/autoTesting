# Verdict - t199c-internal-tracker (cycle 2)

Cycle checked: 2
Contract re-read: qa/contracts/team-bug-loop.md (TB7, TB15, HG-TB1 note).
Evidence: pytest on test_tracker_auth, test_tracker_page, test_routers_list, test_sheet_plan, test_bug_store, test_ui_auth_surface: 109 passed. `ruff check src tests scripts` clean. `autotester doctor`: clean (advisory decision-citation warnings only, non-blocking).

| Criterion | Result | Basis |
|---|---|---|
| TB7 list: status, severity, screen, assignee, first/last seen, count, evidence link, filters | PASS | test_tracker_page |
| TB7 report.view scoping, not-found without scope (AU13) | PASS | `auth/policy.py` ROUTE_POLICY rows for list/csv/xlsx/detail = report.view over project; 16-case table (4 groups x own/assigned/shared/none) gives 404 on list, export and detail when out of scope |
| TB7 report.view@shared | PASS (limited) | only project-level sharing exists in the tree; "shared" relation grants view (table rows dev/tester). Per-run sharing has no model anywhere, so it cannot be tested; the contract's "latest evidence run shared" refinement is residual, not a defect of this unit |
| TB7 assignee edit needs project.edit; 403 and value unchanged | PASS | POST `/projects/{slug}/tracker/{bug_key}/assignee` = project.edit in the central policy; handler re-checks `authorize`; tester row gets 403 (viewable) or 404, store unchanged; sabotage-relevant: tester row asserts unchanged value |
| TB7 assignee free text or member; blank clears; actor recorded; over-length 400 | PASS | test_assignee_edit_accepts_free_text_clears_and_records_the_actor |
| TB7 evidence link refused without session | PASS | anon gets 401 JSON / 302 HTML on list, detail, export and `/runs/run1` |
| TB7 route-enumeration lists routes as guarded | PASS | every served tracker (method, path) is in `policy.ROUTE_POLICY`, kind project, correct key |
| TB7 no parallel auth logic | PASS | routes use `auth.access.authorize/resource_for` and the middleware gate; the module `ROUTE_POLICY` is a declaration mirrored in the central table |
| TB15 CSV + xlsx in Tracker layout, reusing sheet_plan mapping | PASS | unchanged since cycle 1 |
| TB15 every value scrubbed | PASS | planted secret absent from page, CSV and xlsx |
| TB15 no SheetClient/network; LiveWriteRefused intact | PASS | source scan test; test_sheet_plan asserts LiveWriteRefused; sheet_write.py untouched |
| TB15 identical bytes on re-export | PASS | csv and xlsx tests |
| TB15 report.view required, no-scope gets not-found | PASS | export routes in the table: 404 out of scope |
| Design rules | PASS | routes_tracker.py 196, tracker_export.py 90, policy.py 161, tests 119 lines; functions short; doctor clean |
| TB8, TB9, TB13, HG-TB1 | N/A | export-time / deferred |

**Overall: PASS.** Manifest flipped to checked-PASS. Residual note: per-run sharing is not modelled in the tree; revisit if a per-run share is ever added.
