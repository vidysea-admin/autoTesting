# Verdict - t201b-test-button, checker A (blind, cycle 0)

Cycle checked: 0
Bound to: worktree .worktrees/chk-t201b-A, detached at origin/wave/t201b-test-button = eea525fc9af4e6dd2c15808f691b4886d9576914. Date 2026-10-12.

VERDICT: FAIL
Cause (one blocking defect): the unit adds two route-policy rows (`GET /projects/{slug}/test/{run_id}` as `report.view`, `POST /projects/{slug}/test` as `project.run`) but does not add them to the pinned `EXPECTED` table in `tests/test_ui_auth_escalation.py`, so `test_au14_every_policy_row_requires_exactly_its_pinned_key` is red. TT1 requires "the AU14 enumeration test passes with it present". The maker ran per-file tests only, so it did not see this. Not in the master baseline.
Repro: `uv run pytest -o addopts= tests/test_ui_auth_escalation.py::test_au14_every_policy_row_requires_exactly_its_pinned_key` -> left has 2 more items: `('GET','/projects/{slug}/test/{run_id}'): ('project','report.view')` and `('POST','/projects/{slug}/test'): ('project','project.run')`.
Fix: add `"/test/{run_id}"` to the GET `report.view` tuple and `"/test"` to the POST `project.run` tuple in `EXPECTED`. That file is exactly at the 300-line doctor limit (commit 5e0c4b0b), so keep it at 300 lines or less (reflow the tuples, do not add lines).

## Criteria
- TT1 NOT MET only through the AU14 pin above; behaviour is met. `test_team_run_gate.py` 11 passed: anonymous 302 to /auth/login, no project.run 403 naming `project.run`, hidden project same 404 as missing, cross-origin with a valid session 403, unknown slug 404 (also for admin), GET 405/302 and changes nothing; every case asserts a byte-identical data-root listing, an empty queue, and 0 browser/grader calls; the four groups x {own, assigned, shared, other} table is present. The handler also refuses on its own (direct call without the gate). Mutations below.
- TT2 met. A press returns 303 in 0.13 to 0.20 s in the real browser walk and the test asserts < 2 s; the status page follows queued (position) / running / done, and renders after the queue object is rebuilt (`make()` persistence test). The button is hidden from a viewer without `project.run` (tester: 0 forms) and the route enforces regardless.
- TT3 met, with one gap. `requested_by` comes from the session; a forged `requested_by/user/email/owner` in query and body is ignored; two sessions give two names on entry, `Run` and the report header ("Started by dev@team.test with the Test button at ... UTC"); a golden pre-change run.json loads. Gap, non-blocking: the contract says "user id and email"; only the email is stored (the existing field `requested_by` holds the email, as the schedule path does).
- TT4 met. The worker calls `launch_run` once with trigger MANUAL, requested_by and via TEAM_BUTTON (spy test); the AST test finds no Run construction, BrowserSession or pipeline use in `routes_team_run.py` / `team_run_view.py`; RU2 (no cases / no provider -> 400 before any browser) and RU3 hold on the button path. `autotester doctor`: clean on the branch.
- TT5 met on the fake-queue and RunQueue seam. A second press, from another user too, returns the existing request (same location, one entry) for queued and running; a new entry only after finish; 3 projects against a cap of 2 never exceed 2 running or 2 of one project; no `max_concurrent_runs` in the unit's files; the launcher is never called from the request thread. Real-queue integration on T-203: OWED (BLOCKED-CAPABILITY), not a fail.
- TT6 met. `test_team_run_approval.py`: no SecretRef -> 403 "no_secretref: ... no credential pair"; SecretRef without value -> 400 "NOVAL_USER has no value ... Credentials page"; provisioned -> 303 with an account-derived approval carrying its own bounds. Developer and Admin both tested; browser/grader counters 0, listing unchanged, no run dir, canary and provisioned values absent from the text, and `Redactor.scrub` leaves the text unchanged. Same refusal seen in the live walk.

## Mutations (second throwaway worktree at the same sha; all reverted, `git status` clean)
- TT1 A (enqueue before the permission check): `test_the_handler_checks_permission_before_anything_else_even_without_the_login_gate` red (1 failed, 10 passed). Only the direct-handler test catches it, because the login gate refuses first over HTTP; acceptable.
- TT1 B (Origin guard returns None): `test_a_cross_origin_post_with_a_valid_session_is_refused_by_the_origin_guard` red.
- TT3 (read `requested_by` from the request): `test_a_forged_requested_by_in_the_query_or_body_is_ignored` red.
- TT5 (ignore the active entry, always create): `test_a_second_press_returns_the_existing_request_not_a_second_entry` red.
- TT6 (skip the approval check for project.run@all, the admin path): both admin cases in `test_team_run_approval.py` red (2 failed, 2 passed).

## Persona walk (headed Chrome, Playwright; local app only, scratch data root, fake browser and judge from the unit's own test fakes, a throwaway signing key)
dev logs in -> project page shows one Test button -> press -> 303 to `/projects/alpha/test/run-...` in 0.13 s, status page "Requested by dev@team.test ... RUNNING, The run is in progress" -> a second press from the project page lands on the same URL (existing request) -> status becomes done with "Open the report" -> the report shows "Started by dev@team.test with the Test button at ..." (3 clicks from the project page to the report). Negative: press on an uncredentialed project shows 403 "no_secretref: this project declares no credential pair ... declare one on the project's Credentials page". tester: no Test button, and an unshared project is 404. Browser closed and server stopped (port 8765 free). Not walked: My reports and the profile page (G4, TT7-TT9, out of this unit).

## Gate
- Full suite `uv run pytest -o addopts=`: 24 failed, 5168 passed, 211 skipped, 42 errors (26:29).
  - Baseline 22 matched: 5 symlink (discover, 2 report_export, ui_crawls, ui_video_route_traversal), 15 test_ui_intake + 1 test_ui_origin_guard, 1 ui_runs_serial_entry_mix_live.
  - Extra 1: the AU14 pin above (this unit; blocking).
  - Extra 2: `test_ui_auth_envkeys::test_au21_a_slug_that_swallows_a_variable_the_server_has_is_refused`, environment-dependent: passes when a `NODE_*` process variable exists (re-run with NODE_ENV=x: passed). Untouched by this unit.
  - 42 errors, all `test_cli_video_review_exits.py`: `ffmpeg` is not on PATH in this shell (WinError 2 in the fixture); file untouched by the unit.
  - No dangling-D-086 citation and no env_creation flake appeared.
- `uv run ruff check src tests scripts`: clean.
- `uv run autotester doctor`: clean on the branch.
