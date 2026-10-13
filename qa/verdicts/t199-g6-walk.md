# T-199 G6 developer live-browser walk (Mode D) - team-bug-loop.md "Persona walks" G6 (dev), TB2, TB6, TB7, TB15

Cycle checked: 0 (branch check/t199-g6 from wave/t199d-bug-wiring cb4ad0e4). Method: local uvicorn on 127.0.0.1 (random port), scratch data root,
login gate ON, seeded accounts (admin, dev = owner of `demo`, tester = SHARED on `demo`), one headed Chromium (Playwright), local fixture project
`demo` with three cases (S1 Checkout, S3 Profile photo upload, S2 Login). Runs are real: the UI "Run tests" button -> queue -> `launch_run` ->
`record_run_bugs`. LIMIT: the browser session and the case grader are stubbed (as in tests/test_bug_wiring.py), the verdict per case is set from a
file, so no product page was driven and no model was called. Evidence: qa/evidence/browser-t199-g6/ (PNG per step, results.json, export.csv,
export.xlsx; password inputs masked). Server stopped, browser closed.

| Step | Result |
|---|---|
| W1 Dev signs in, opens project `demo`, finds the tracker from the project page | FAIL (D1): no link to /tracker anywhere on the project page or nav; reached by typing the URL |
| W2 Tracker before any run | PASS: "0 of 0 bug(s)", "No bugs match" (02) |
| W3 Run tests (2 cases fail, 1 passes) creates tracked bugs via launch_run | PASS: exactly 2 OPEN bugs, S1 and S3, passing case absent, count 1, first/last seen, evidence = run id link (03) |
| W4 Filters status/severity | PASS: status=open 2 rows; +severity S1 1 row; status=fixed none; severity S3 1 row (04); controls unlabelled, see D2 |
| W5 Bug detail: history, evidence link | PASS: status, severity, seen count, evidence link to /projects/demo/runs/<id> (200 for dev), history table fail/system:bug-loop (05) |
| W6 Assignee edit by dev (project.edit) | PASS: "priya" saved, shown in list and detail, history row `assign user:dev@team.test` (06) |
| W7 Tester (report.view, no project.edit) | PASS: list+detail visible (200), no assignee form, direct POST 403, value unchanged (07, 08) |
| W8 CSV and xlsx downloads, TB15 columns | PASS: demo-tracker.csv / .xlsx; header Bug ID, Title, Severity, Screen, Status, Assigned To, First Seen, Last Seen, Count, Evidence; values match page; xlsx identical cells; tester 200, anonymous 401 for export and evidence link |
| W9 Re-run, case A passes once, B still fails | PASS: still 2 bugs; A open (k<2); B count 2, no duplicate (09) |
| W10 Third run, A passes again | PASS: A FIXED, 2 bugs total, B count 3; detail lists both closing pass events with run ids (10, 11); 3 runs exist |
| W11 Labels | FAIL (D2): the Status and Severity selects have no label association; assignee input is labelled |
| W12 Console errors | PASS: 0 errors or warnings on all pages walked |

Not walked: reopened/stale transitions, scrub of a planted secret, non-member 404 (all covered by tests/test_tracker_auth.py and test_bug_wiring.py), real browser execution of cases.

## Defects
- D1 (medium, usability): the project page has no entry to the tracker (src/autotester/ui/project_view.py:96 lists Issues, Cases, Report etc. but no Tracker link); the contract's persona step "open the project, open the tracker" has no click path.
- D2 (low, AU26 labelled controls): src/autotester/ui/routes_tracker.py:95-96 renders "Status <select>" and "Severity <select>" as bare text, not `<label for>`.

## Overall: FAIL on W1 (D1) and W11 (D2) as a persona walk; all functional steps (wiring, filters, history, assignee gate, exports, fixed-without-duplicate) PASS.
