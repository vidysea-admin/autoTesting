# t201b-test-button r3 (checker, fresh read of the contract): PASS

Cycle checked: 2
Scope: TT1-TT6 of `qa/contracts/team-test-button.md`, re-read before checking. Scoped runs only (shared CPU); no browser, no full suite.

## Criteria
- TT1 PASS. `test_team_run_gate.py` and `test_ui_auth_escalation.py` (AU14 pins for both routes) pass; no change to the gate in this cycle.
- TT2 PASS. `test_team_run_status.py` passes (303, status sequence, persistence).
- TT3 PASS. Contract: "user id and email taken from the session". Code: `routes_team_run.press_test` passes `requested_by=who.email, requested_by_id=who.user_id`; `QueueEntry.requested_by_id` and `Run.requested_by_id` exist, optional; `launch_run` stores it; the report header and status page show "(user #N)". Test `test_two_teammates_...` asserts two different ids (dev vs admin) on queue entry and `Run`, plus the header text; the forged-body test asserts the id is the session's; the golden pre-change `run.json` loads with both fields `None`. Mutation (route passes `requested_by_id=None`): 2 failed, 2 passed; reverted.
- TT4 PASS. `test_team_run_launcher.py` passes; `test_run_launcher.py` and `test_ui_runs_queue.py` pass unedited; only additive keyword plumbing in `launch_run`; `run_launcher.py` stays at 300 lines.
- TT5 PASS (fake-queue/RunQueue seam; real-queue integration stays T-203's). `test_team_run_queue_seam.py` passes after the FakeQueue gained the new optional field.
- TT6 PASS. `test_team_run_approval.py` passes.

## r1 and r2 defects
- r1 AU14 pin: still fixed (`test_au14_every_policy_row_requires_exactly_its_pinned_key` passes).
- r2 TT3 id: fixed as above.

## Gate (scoped)
- pytest: 94 passed across test_team_run_{attribution,gate,approval,launcher,queue_seam,status}, test_ui_auth_escalation, test_cli_subapp_hook, test_run_queue, test_run_launcher, test_ui_runs_queue.
- ruff `src tests scripts`: all checks passed.
- doctor: 3 `decision-citation-dangling` hits, all in `qa/verdicts/t196-citation.r1.{a,b}.md` (two non-existent example decision ids quoted as illustrations); files not touched by this unit.
- Not run here: full suite (shared machine); the r2 full-suite result (only known failures) predates a purely additive change.
