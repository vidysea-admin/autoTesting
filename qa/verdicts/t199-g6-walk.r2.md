# T-199 G6 walk r2 - re-walk of the two failed steps (W1/D1, W11/D2)

Cycle checked: 1 (branch check/t199-g6). Method: local uvicorn on 127.0.0.1, scratch data root, login gate ON, one headed Chromium, dev account (owner of `demo`) with one seeded tracked bug. Evidence: qa/evidence/browser-t199-g6/r2-01-project-page-tracker-link.png, r2-02-tracker-labelled-filters.png, r2-results.json.

| Step | Result |
|---|---|
| W1 (D1) Open project page, click "Bug tracker" | PASS: link visible on /projects/demo; click lands on /projects/demo/tracker ("Bug tracker" heading) |
| W11 (D2) Status and Severity filters | PASS: `get_by_label("Status")` and `get_by_label("Severity")` each resolve to a SELECT; filter applied by label; 0 console errors |

Tests: test_tracker_auth, test_tracker_page, test_ui_onboard_a11y 39 passed (link present for report.view holders, absent for a user with no grant; selects have no unlabelled controls); ruff clean; doctor clean.

## Overall: PASS
