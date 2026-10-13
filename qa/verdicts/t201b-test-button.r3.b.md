# t201b-test-button r3.b (independent checker, fresh read of the contract): PASS

Cycle checked: 2
Scope: TT1-TT6 of `qa/contracts/team-test-button.md`, judged against code at head 34340027, not the maker's report. Scoped runs only (shared CPU); no browser, no full suite.

## Criteria
- TT1 PASS. `test_team_run_gate.py` and `test_ui_auth_escalation.py` (AU14 enumeration pins) pass. `_presser` (`ui/routes_team_run.py:39`) checks sign-in, project.view (404), project.run (403) before any work.
- TT2 PASS. `test_team_run_status.py` passes (303, status sequence, persistence).
- TT3 PASS. The id comes from `current_principal()` (session principal) via `who.user_id` / `who.email` at `routes_team_run.py:81-82`; `press_test(slug)` takes no body/query parameter, so nothing a user sends can set it. `QueueEntry.requested_by_id` (`schema/run_queue.py:40`) and `Run.requested_by_id` (`schema/run.py:90`) are `int | None` default None, `extra="forbid"` kept. `launch_run` passes it through (`stages/run_launcher.py:278`); `routes_runs.py:91` forwards it from the entry. Report header and status page render "(user #N)" (`ui/team_run_view.py:60,75`). `test_team_run_attribution.py`: two teammates give two different ids on entry and Run plus header text; forged query/body value is ignored; golden pre-change `run.json` loads with both fields None.
- TT4 PASS. `test_team_run_launcher.py`, `test_run_launcher.py`, `test_ui_runs_queue.py` pass; change to `launch_run` is additive keyword plumbing; `run_launcher.py` is exactly 300 lines (limit met), `launch_run` about 30 lines.
- TT5 PASS (queue seam). `test_team_run_queue_seam.py` passes.
- TT6 PASS. `test_team_run_approval.py` passes.

## Prior defects
- r1 AU14: fixed, the AU14 enumeration test passes.
- r2.a TT3 (email only): fixed as above.

## Gate (scoped)
- pytest: 70 passed (the nine files test_team_run_{attribution,gate,approval,launcher,queue_seam,status}, test_ui_auth_escalation, test_run_launcher, test_ui_runs_queue).
- ruff `src tests scripts`: all checks passed.
- doctor: 5 `decision-citation-dangling` hits. Three are the known t196 example citations; two are in `qa/verdicts/t201b-test-button.r3.a.md:21`, where r3.a quotes the same t196 example ids as prose. All are in verdict files, none in source. Non-blocking for this unit; the r3.a line should be reworded by the maker or the next close-out.
- Not run: full suite.

## Defects
None blocking.
