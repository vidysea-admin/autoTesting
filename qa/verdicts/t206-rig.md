# Verdict - t206-rig
Cycle checked: 1
Verdict: FAIL
Head checked: 3ee8202b (ea25d946 + master merge; only qa/feedback-inbox.md conflicted, both sides kept)

## Rulings
1. D-074 text is items (a)-(e) and says nothing of "evidence only"; the rule is the contract header and TAI1, which allow `tests/acceptance/**`. A test rig is allowed. `git diff --stat 22eac602..HEAD -- src/` is empty.
2. TAI2 amended (contract folded): strict xfail only while the named task id is still pending (or a D-number defers the row); no xfail may remain at T-206 PASS.
3. Credentials page: `routes_credentials.py` renders stored values only when `show_values` (credentials.view, AU21/D-034, admin by default); everyone else sees set/not set. That is the approved design, not a defect, and the CLAUDE.md boundary (no value in prompt/log/screenshot) is not breached by the page. TA12 amended: admin credentials pages exempt from the page-body canary scan, never screenshotted or copied into evidence. No issue logged.

## Findings
- F1 (blocking): master now has `ui/routes_tracker.py` (T-199 TB7). Run on the merged tree: `test_ta07 ...::test_tb7_dev_subadmin_admin_see_the_tracker_tester_only_shared_other_nothing` and `test_ta09 ...::test_tb7_subadmin_opens_the_tracker_page_and_sees_status_severity_screen` XPASS(strict) = FAILED. Remove the marker and make them pass; re-check TB15 export too.
- F2 (blocking): xfail reasons on TA3 (`run=False`), TA4 and TA5 name no pending task. Name one (or a D-number) or turn the row into a DEFERRED/live-walk note (TA3 is really a live-walk item). TA6/TA8/TA14 reasons cite T-200/T-201 mostly; TA6 email rows are deferred by D-092/D-093, so cite those, not "blocked".
- F3 (TAI3): `test_ta03_real_server.py::test_a_foreign_host_and_a_foreign_origin_post_are_refused` ERRORED (server fixture 60 s /healthz deadline) under CPU load from the live Chrome worker; widen to 180 s.
- OK: reuses auth_harness/team_run_fakes/delivery_fakes/drive_fakes/video_review_fakes; roles created via accounts/set_relation; sockets loopback (127.0.0.1); sleeps bounded; no file over 300 lines.

## Ran
`uv run pytest tests/acceptance` on merged tree: 54 passed, 11 xfailed, 2 failed (F1), 1 error (F3), 328 s. Reverse-order, ruff and doctor runs were still queued behind the loaded CPU and are not counted.
