# t201-live: real-queue integration of the Test button (TT1-TT6): PASS

Checked 2026-10-13 on branch `check/t201-live` (from master 53f069ed). Scope: the live half of TT5 that the r3 verdicts left to T-203, plus a live pass over TT1-TT4 and TT6. TT7-TT9 and email are out of scope (deferred to production).

## Setup (real app, no TestClient, no fakes)
- Server: `uv run uvicorn autotester.ui.app:app` on 127.0.0.1:59025 (the command `scripts/serve_windows.ps1 -DryRun` prints), data root `.work/t201-root` (a fresh `AUTOTESTER_ROOT`), login gate ON, real `RunQueue` file `.work/t201-root/.work/run_queue.json`. No Scheduled Task installed.
- Fixture product: `tests/fixtures/regression_site` served by `python -m http.server` on 127.0.0.1:59024. No external site.
- Accounts made only with `auth.accounts.signup`, `auth.groups`, `auth.access.set_owner`: `admin@live.test` (first account), `dev@live.test` (Developer group, owner of project `livefix`).
- Project `livefix`: 1 case (navigate to the fixture index page), `providers.judge = mock` (no model call possible), `headed = true`. A signed live_case approval for the fixture target was added with `RunApproval.sign` after the first press was refused.
- Driver: Playwright, headless UI session (the run's own browser was the one headed browser). Scripts in `evidence/t201-live/scripts/`.

## Steps
| Step | Result | Observed |
|---|---|---|
| TT1 anonymous POST | PASS | 302 to `/auth/login?next=/projects/livefix/test` |
| TT1 cross-origin POST with valid session | PASS | 403 (Origin guard) |
| TT6 press with no approval | PASS | 403 page: "no_secretref: this project declares no credential pair ... no approval exists ... Grant one with: ..." (`00-TT6-refused-no-approval.png`); queue file and `runs/` dir byte-identical before and after; no browser started |
| TT2 press returns at once | PASS | form click navigated to `/projects/livefix/test/run-01M4T4V2QN7VJVNRPSK7DNTGQX` in 0.36 s; page showed RUNNING |
| TT5 second press while active | PASS | 303 to the same run id; one entry only in the queue file |
| TT5 queue, not bypass | PASS | the entry sits in the real queue file with status `done`, `started_at` 6 ms after `enqueued_at`, `finished_at` 41 s later; the run executed in a real headed Chromium (webm recorded) |
| TT2 status sequence | PASS (partial) | observed `running` then `done`; `queued` with a position was NOT observed live because the slot was free (limit not contended); that state is covered by `test_team_run_status.py` only |
| TT3 attribution | PASS | queue entry: `requested_by=dev@live.test`, `requested_by_id=2`, `trigger=button`, `via=team_button`; `run.json`: same id and email, `trigger=manual`, `via=team_button`; status page "Requested by dev@live.test (user #2)"; report header "Started by dev@live.test (user #2) with the Test button" |
| TT4 one launcher | PASS (observed) | run record has a trace `execute done 40.58s` and a persisted case result; code-level AST check stays with the r3 verdicts |
| Report page | PASS | `/projects/livefix/runs/run-01M4T4V2QN7VJVNRPSK7DNTGQX` renders the case, evidence and video (`04-report.png`) |

## Notes and defects
- The case verdict is INCONCLUSIVE ("not judged: the grader failed after execution completed"), as expected with the mock judge and no queued response: the run executed (`completed`) but no real grading happened, because a model call was out of scope. This shows execution and attribution, not grading.
- Anonymous POST without `Accept: text/html` returns 401, with it 302; contract TT1 says 302, which holds for browsers. Not a defect.
- No credential values appear anywhere in the evidence; the only secret, `AUTOTESTER_APPROVAL_KEY`, lives in the throwaway data root `.env`, which is not copied.
- Servers on both ports stopped at the end; confirmed no listener.

## T-201 task-level gaps (non-deferred)
1. `.goal/goal.json` done_check needs `qa/verdicts/t-201-team-loop.md` (task-level verdict) which does not exist; T-200 and T-198 are still `pending`, and T-201 depends on T-200.
2. TT7: no `/inbox` ("My reports") route or page exists in `src/autotester/ui` (grep finds none); the delivery core exists only as a module and schema, so the website inbox is not reachable by a user.
3. TT2 `queued`-with-position was not seen on the live app (only under test fakes); a contended-slot live check (two projects, limit 1) would close it.
4. No grading in this run (mock judge); a real-judge run needs a model key and is out of this scope.
5. TT8 / TT9 (email) deferred by instruction.
