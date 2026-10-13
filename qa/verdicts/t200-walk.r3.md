# T-200 persona walk, round 3 - tick run ended INCONCLUSIVE at process exit

**Defect (from r2):** a run started by `autotester schedule tick` ended INCONCLUSIVE with
"RuntimeError: cannot schedule new futures after interpreter shutdown".

**Root cause:** the contract (team-schedule.md TS6/TS7) has the tick enqueue and run in its own process, through an in-memory queue whose
workers are threads. The CLI returned right after `tick_all`; at interpreter exit Python shuts the `concurrent.futures` thread pools down
BEFORE it joins non-daemon threads, so the run's `ThreadPoolExecutor` (parallel case execution, browser-use backend) refused new work
mid-run. Making the threads non-daemon (the old design) was not enough. There is no server-side timer tick in this tree: the only
`tick_all` caller is the CLI, and the server's queue lives in a live interpreter, so it has no such exit.

**Fix:** `ui/routes_runs.py` tracks the tick queue's worker threads and exposes `wait_for_tick_runs()`; `cli_schedule.py` prints the report,
then waits for those runs before exiting (not on `--dry-run`, which opens no queue). Exit code is still the tick's, not the run's.

**S11 ruling:** the contract defines the requester as the schedule owner (team-schedule.md "Owner = the user who last saved the schedule
(`requested_by` of every run it enqueues)"); the word "scheduled" is the walk's label, not a contract field. Data is correct
(trigger "schedule", requested_by = owner); no change to data, display or contract.

## Re-check
- `tests/test_tick_waits_for_runs.py` runs a real child interpreter. Control (no wait): run hits "interpreter shutdown" (reproduces r2).
  With `wait_for_tick_runs()`: the run's thread-pool work succeeds and the run reaches its result ("ok"). Both pass.
- `tests/test_cli_schedule.py::test_a_real_tick_waits_for_the_runs_it_started`: a real tick drains, `--dry-run` does not.
- schedule tick / wiring / owner guard / cli_schedule, run_queue (+resilience, seam), ruff, doctor: green except 3 tests that fail
  identically on the unmodified head 27773f51 (owner-disabled refusal in two cli_schedule tests; a transitive-import test in
  test_schedule_tick). Not caused by this change; left for triage.
- No full browser walk re-run (CPU shared); the process-exit failure is covered by the child-interpreter test.

## Overall: PASS for the shutdown defect and the S11 ruling.

## Addendum: the three pre-existing failures (found, fixed)
Same three failures on current local master c377504e, so not caused by this branch. Cause: the HO24 owner guard
(`stages/schedule_owner.py`, t200c cycles 2-3) fails closed with auth ON.
- `test_cli_schedule.py` x2: the fixture project has no owner, so the tick recorded `refused` (owner_refused) instead of
  `blocked_no_credentials`. The `root` fixture now sets `AUTOTESTER_AUTH_DISABLED=1` (AU17 loopback single-user mode). Test setup only.
- `test_schedule_tick.py` TS6 closure: a real regression. `schedule_owner` -> `auth.config` -> (lazy) `ui.helpers` -> `browser.session`.
  Fix: `hosted`, `_option`, `bind_host`, `bind_port`, `auth_disabled` moved verbatim to the pure `auth/loopback.py`, re-exported
  from `auth.config`; `schedule_owner` imports from `loopback`. Behaviour identical (honoured only on loopback, never when hosted, AU17).
  `ALLOWED_OUTSIDE` extended by exactly the HO24 modules (stages.schedule_owner, auth, auth.access, auth.db, auth.defaults,
  auth.loopback); nothing browser-side. New `tests/test_auth_loopback.py` proves auth_disabled is ignored when hosted or off loopback.
- doctor: `docs/MAP.md` regenerated for the new module; ruff clean.
