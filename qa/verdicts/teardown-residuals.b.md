# Verdict B - teardown-residuals (adversarial checker)

**Cycle checked:** 0
**Verdict:** PASS
**Branch / head checked:** `fix/teardown-residuals` @ `30235e16` (base a6e03fa4), worktree `D:/autoTesting/.claude/worktrees/teardown-r`
**Method:** read manifest + diff (`git diff a6e03fa4 HEAD`) + parent verdict `qa/verdicts/run-teardown-stall.b.md:35-36`; ran only targeted test files, one pytest at a time, worktree `src` via PYTHONPATH (`autotester.__file__` confirmed to resolve inside the worktree); reverted each fix in memory with a pytest plugin (`.work/revert_plugin.py`, `REVERT=<name>`, gitignored) and showed a test go red; probed real Playwright driver; no src/tests edited, no `.env` read.

## Re-run of the maker's evidence
| Command | Result |
|---|---|
| `tests/test_teardown_residuals.py tests/test_run_teardown_stall.py` | `26 passed` |
| `tests/test_run_budget_judge_time.py tests/test_parallel_run.py` | passed (neighbour of the `_consume` edit) |
| `tests/test_parallel_run_session_crash.py tests/test_browser_session_cdp.py` | `24 passed` (neighbours of session close) |
| `tests/test_run_teardown_stall_wiring.py` x3 (3 separate processes) | `8 passed` each |
| `ruff check src tests scripts` | `All checks passed!` |
| `autotester.exe doctor` | `2 violation(s)`, both `decision-citation-known-disputed` D-000/D-005 (`docs/DECISIONS.md:80,209`), non-blocking, in no touched file |
| line counts | `run_budget.py` 299, `teardown.py` 141, `test_teardown_residuals.py` 151 (all <= 300) |

## Falsification (each fix reverted in memory, a test goes red)
| # | Revert | Red test(s) |
|---|---|---|
| F-R1a | `excluded_report` forced `acted_during_exclusion=0.0` | `test_spends_made_while_a_scope_is_open_are_counted_once_each` (1 failed, 25 passed) |
| F-R1b | count every spend regardless of scope | `test_a_serial_run_records_no_spend_inside_an_excluded_scope` + `test_spends_made_while_a_scope_is_open_are_counted_once_each` (2 failed) |
| F-R2a | `detach` ignored (back to in-thread wait) | `test_a_step_the_cancel_cannot_reach_is_abandoned_not_waited_for` + `test_a_detached_step_does_not_hold_the_caller_past_the_timeout` (2 failed; the caller waits the full 20 s wedge) |
| F-R2b | one-shot `threading.Timer` instead of the re-sending `_watch` | `test_an_abort_that_did_not_take_is_re_sent_until_the_step_ends` red (also the two detach tests, expected, since this stub ignores `detach`) |
| F-W | `run_execution._housekeeping` replaced by `nullcontext` (the wipe no longer recorded as housekeeping) | `test_a_launched_run_records_phase_totals_and_unaccounted_seconds`: `assert saved.excluded_s["housekeeping"] == WIPE_S` -> `assert 0.0 == 45.0` (`tests/test_run_teardown_stall_wiring.py:93`) |

So F-W answers the specific ask: the hardened wiring test still fails when the wipe is not held off the clock as housekeeping, and its exact-equality assertions do not read real elapsed time (the only clock is the injected `run_budget.time` stub, `:73-76`).

## R2: can the daemon thread leak a browser or double-run a step?
- **Which owners detach.** `detach=_loop_of(owner) is None` (`teardown.py:118-119`). `_loop_of` is None only for an owner with no `_loop` or a closed loop. Real Playwright objects always carry `_loop` (`playwright/_impl/_sync_base.py:91`, `SyncBase.__init__`). Probe `.work/probe_real_driver.py` against a REAL `sync_playwright().start()` driver: `_loop_of(pw)` is live, `pw.stop` is callable, and `close_session(None, pw)` ran `stop` on the MAIN thread (`[True]`, 0.03 s), i.e. the thread-bound path is preserved. After stop `_loop_of(pw)` is None (loop closed).
- **No browser leak.** A real context/driver never detaches while its loop is alive. A closed loop means the node driver is already stopped, which ends Chromium; and on a closed loop `SyncBase._sync` raises `Error("Event loop is closed!")` before touching any greenlet (`_sync_base.py:102-104`), so running it on a daemon thread cannot hit the "Cannot switch to a different thread" failure and cannot hang. A simulated closed-loop owner returned in 0.02 s with the error recorded (ok=False), threads afterwards: MainThread only.
- **No double-run.** The step callable is invoked exactly once per `bounded_call` (`_run_detached` starts one worker; there is no retry). `BrowserSession.close` nulls `_context/_playwright` before calling `close_session` (`session.py:140-141`), so a second `close()` has nothing to close. An abandoned step's late exception/result is swallowed by design (docstring `:82`).
- Not run: a live Chromium probe (no browser launched; machine low on memory). The real-driver probe above covers the owner-classification boundary; the real BrowserContext path is unchanged code (in-thread + cancel) as in the parent unit's live probe.

## Findings (all non-blocking)
1. **F1 (note).** `acted_during_exclusion` is a COUNT stored in `Run.excluded_s`, a `dict[str, float]` documented as seconds (`schema/run.py:164-171`). The description states it, and grep shows no consumer that sums `excluded_s.values()` (only `run_launcher.py:229,265` and `parallel_run.py:62` pass it through). A future consumer summing the values would be wrong; a distinct field would have been cleaner but would cost a schema change. Accept.
2. **F2 (note).** `test_a_hung_context_close_is_abandoned_traced_and_teardown_continues` (`tests/test_run_teardown_stall.py:122`) monkeypatches `cancel_inflight`, but an owner with no `_loop` now takes the detach path, so that test no longer exercises the abort route. The abort + re-send route is still covered by `test_bounded_call_aborts_a_hung_step_and_reports_it` and the new `test_an_abort_that_did_not_take_is_re_sent_until_the_step_ends` (F-R2b red). No coverage hole.
3. **F3 (residual, pre-existing).** The cancel is queued on a loop shared by context and driver; a re-sent cancel fired exactly as a step ends could in theory hit its successor. The `done.is_set()` re-check (`teardown.py:93`) narrows it and the one-shot Timer had the same window; re-sending adds exposure only at the moment a step ends right at a resend boundary. Not demonstrated; not a regression.
4. **F4 (R1 scope).** The count measures spends, not leaked seconds (manifest says so). Serial claim verified from code: `check_start()` spends nothing (`run_budget.py:207-212`), and nothing in the teardown/session-start scopes calls `try_consume`/`check(actions|probes=)`; the case-start reservation (`parallel_run.py:160`) is outside any scope in a serial run. Semantics unchanged: test 3 shows a refused spend is not counted and the 99 s / 101 s clock rule is identical.

## Conclusion
R1 is observable without changing a rule; R2 abandons an unreachable step on time without touching the Playwright thread-bound path; the wiring test is deterministic and still red when the wipe is not recorded as housekeeping. Every claim above cites a command or file:line. PASS, cycle 0.
