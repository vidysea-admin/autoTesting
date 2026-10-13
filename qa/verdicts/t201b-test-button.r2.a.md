# t201b-test-button r2 (checker A): FAIL

Cycle checked: 1
Sha: 7cc532d95f03a364de3c1bb37266ade961f09e38 (origin/wave/t201b-test-button)

## Verdict: FAIL on TT3 (the one remaining defect). Everything else passes.

### TT3 ruling: FAIL
Contract TT3 says the `RunRequest` and the `Run` record `requested_by` as "user id and email taken from the session", and the Vocabulary
section repeats "the signed-in user's id and email". The route stores `requested_by=who.email` only (`ui/routes_team_run.py`
`queue.submit(... requested_by=who.email ...)`); no user id is stored on the queue entry, the `Run` or the report header. The manifest
admits this ("TT3 not done, deliberate"). The contract requires the id, so email-only does not meet it. Fix: add a user-id field to
`QueueEntry` and `Run` (optional, so an old `run.json` still loads), fill it from the session, show it with the email, and have
`test_team_run_attribution.py` assert two different ids. The existing assertions on email stay.

### r1 defect: fixed
`tests/test_ui_auth_escalation.py` now pins `POST /projects/{slug}/test` as `project.run` and `GET /projects/{slug}/test/{run_id}` as
`report.view`. These match the contract and the route's own checks. 22 passed, including
`test_au14_every_policy_row_requires_exactly_its_pinned_key`.

### Merge resolutions (b9239a06, parents eea525fc and 99960519): nothing lost
Diffed the merge against both parents for cli_subapps.py, routes_runs.py, run_queue.py, tests/golden/cli_commands.json and
tests/test_cli_subapp_hook.py. Against master, the only changed lines are the branch's `via` plumbing and the `auth` golden/hook
entries. Every line the branch added over the merge base is present, except two that were deliberately rewritten (`via=via` on the
`submit` call; the hook assertion widened to `{"ingest","issues","auth","schedule"}`).

### Mutations (run on a scratch merge, then reverted)
- TT1, drop the `project.run` check: gate test fails (1 failed).
- TT3, read `requested_by` from the request: attribution test fails (1 failed).
- TT5, always enqueue a second entry: queue seam test fails (1 failed).
- TT6, skip the approval check (`prepare_run`): approval tests fail (4 failed).

### Temp-merge onto current origin/master (04e461f9)
Merge was clean with no conflicts. The six `test_team_run_*` files, `test_ui_auth_escalation.py` and `test_cli_subapp_hook.py`
all passed: 58 passed.

### Headed browser persona walk (local app, gate on, fake runner; browser closed, server stopped)
- Developer who owns the project: the Test button was visible. Pressing it ended on the project report with a new run; a second press
  after reload made another run.
- Tester with no relation to the project: 404 on the project page, no button.
- Anonymous: GET of the status route redirected to `/auth/login?next=...`.

### Gate
- Full suite `uv run pytest -o addopts=`: 6 failed, 5842 passed, 7 skipped, 14 xfailed. The failures are the 5 known symlink tests
  (test_discover, 2 in test_report_export, test_ui_crawls, test_ui_video_route_traversal) and the au21 flake
  (`test_au21_a_slug_that_swallows_a_variable_the_server_has_is_refused`). No new failures.
- ruff on `src` and `tests`: all checks passed.
- doctor: clean.
