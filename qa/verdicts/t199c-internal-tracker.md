# Verdict - t199c-internal-tracker

Cycle checked: 1
Contract re-read: qa/contracts/team-bug-loop.md (TB7, TB15, HG-TB1 note, EXPORT-TIME markers on TB8/TB9/TB13).
Evidence: `uv run pytest tests/test_tracker_page.py tests/test_routers_list.py tests/test_sheet_plan.py tests/test_bug_store.py` 67 passed; `ruff check src tests scripts` clean.

| Criterion | Result | Basis |
|---|---|---|
| TB15 CSV + xlsx in Tracker layout, reusing sheet_plan mapping | PASS | header order and cells compared in csv/xlsx tests; mapping imports `bug_values`/`safe_cell` from `stages/sheet_plan.py` |
| TB15 every value scrubbed | PASS | planted secret absent from page, CSV and xlsx; formula title prefixed with apostrophe |
| TB15 no SheetClient/network; LiveWriteRefused unchanged | PASS | source scan test; `sheet_write.py` untouched |
| TB15 identical bytes on re-export | PASS | csv and xlsx (fixed zip times and doc properties) |
| TB15 requires report.view; no-scope user gets not-found | FAIL (blocked) | no session/permission layer in tree; only unknown-project 404 and `ROUTE_POLICY` declaration |
| TB15 screenshot links are authenticated product URLs | PASS (limited) | Evidence column is a relative `/projects/<slug>/runs/<run>` URL; enforcement is T-204's |
| TB7 list with status, severity, screen, assignee, first/last seen, count, evidence link; filters | PASS | page tests |
| TB7 report.view scoping, report.view@shared, not-found | FAIL (blocked on T-204) | not implemented |
| TB7 assignee edit gated on project.edit, 403 | FAIL (blocked on T-204) | no edit route exists |
| TB7 route-enumeration lists routes as guarded | PARTIAL | `ROUTE_POLICY` declared and tested against the router; no central gate in this tree |
| TB8, TB9, TB13, HG-TB1 | N/A | EXPORT-TIME / deferred (D-090) |

**Overall: FAIL for TB7 only** (the permission-bound parts need T-204 session and user model). TB15 file export passes on all criteria that can be tested without a session. Manifest stays at ready-for-check; not flipped to checked-PASS.

Pre-existing doctor violations, not from this unit: stale SNAPSHOT.md, D-9999/D-999 citations in t196 verdicts.
