# Manifest - teardown-residuals

**Status:** ready-for-check
**Fix cycle:** 0
**Source:** `qa/verdicts/run-teardown-stall.b.md:35` (R1) and `:36` (R2), plus the load-flaky wiring test `tests/test_run_teardown_stall_wiring.py::test_a_launched_run_records_phase_totals_and_unaccounted_seconds`. Parent unit: run-teardown-stall (checked-PASS, D-112).
**Branch:** `fix/teardown-residuals` from master a6e03fa4 (worktree `D:/autoTesting/.claude/worktrees/teardown-r`).

## Decision per residual
- **R1 is bounded by design (D-112 item 1: one shared clock). Semantics NOT changed; it is made observable.** `RunBudget.excluded_report()` gains `acted_during_exclusion`, a COUNT of spends (actions / probes) made while an excluded scope was open, i.e. while the shared clock was paused for every worker. 0 in a serial run (the one thread inside a scope cannot act); > 0 shows a parallel run leaked target-acting time into the allowance. It lands in `Run.excluded_s` (no schema field added; the dict description says it is a count). The leak stays capped by the combined allowance (verdict P4).
- **R2 is fixed, in place, without touching Playwright's thread-bound path.** (a) A teardown step whose owner has no reachable Playwright loop (so `cancel_inflight` cannot interrupt it) now runs on a daemon thread and is abandoned at `TEARDOWN_TIMEOUT_S`, traced `session_close.*` ok=False "abandoned after Ns" (before: the caller waited for however long the step wished, verdict P9: 3.0 s for a 1 s timeout). (b) A cancel that did not take is re-sent every `timeout_s` until the step ends (before: sent once). Owners with a live loop (real Playwright sync objects) keep the in-thread step plus cancel exactly as measured live in the parent unit.

## What changed (file:function)
- `src/autotester/browser/teardown.py`: `_loop_of` (new helper, `:33`; `cancel_inflight` now uses it), `_run_detached` (`:56`), `bounded_call(..., detach=False)` (`:77`; the one-shot `threading.Timer` became the re-sending `_watch` loop, `:91`), `_teardown_step` passes `detach=_loop_of(owner) is None` (`:118-119`). 106 -> 141 lines.
- `src/autotester/stages/run_budget.py`: `RunBudget._overlapped` (`:102`), counted in `_consume` on a successful non-zero spend while `self._excluded.active` (`:199-200`), reported by `excluded_report` (`:151`). The `WALL_CLOCK_PER_ACTION_S` docstring was condensed (same facts) to keep the file at 299 lines (cap 300).
- `src/autotester/schema/run.py`: `Run.excluded_s` description only (documents the count key). No new field.
- `tests/test_teardown_residuals.py` (NEW, 151 lines; both existing stall test files are near the 300-line cap).
- `tests/test_run_teardown_stall.py`: `test_excluded_seconds_report_each_kind_and_the_union` expected dict gains the new key (the only edit).
- `tests/test_run_teardown_stall_wiring.py`: hardened test (below).

## Wiring test hardening (flake)
Cause: the test slept a real `time.sleep(0.06)` and asserted measured `housekeeping >= 0.05`; on Windows (coarse monotonic tick, early sleep returns, loaded host) a 60 ms sleep can measure under 50 ms. Fix: `run_budget.time` is replaced by an injected clock (module-local stub, nothing else sees it) and the fake wipe advances it by `WIPE_S = 45.0`; assertions are now exact equalities (`housekeeping == 45.0`, `total == 45.0` uncapped under the 60 s allowance, `judging == 0.0`, `acted_during_exclusion == 0.0`). Nothing is weakened: it still proves the wipe runs inside `housekeeping()`, is recorded in `run.json`, and is held off the approval clock; it additionally proves the exact amount and the serial R1 zero. The key-set assertion now includes `acted_during_exclusion`. (The flake cause is a diagnosis from the code and platform timer behaviour; it was not reproduced here.)

## Criteria (numbered; each cites its test)
1. R1: a serial run (spends only outside scopes) reports `acted_during_exclusion == 0.0`: `tests/test_teardown_residuals.py::test_a_serial_run_records_no_spend_inside_an_excluded_scope`.
2. R1: each non-zero spend made inside a scope is counted once; a bare `check()` and an out-of-scope spend are not: `::test_spends_made_while_a_scope_is_open_are_counted_once_each`.
3. R1: observability changes no rule. A refused spend is not counted; the 100 s clock still allows 99 s acting and refuses at 101 s; judging / housekeeping / total are unchanged: `::test_a_refused_spend_is_not_counted_and_the_clock_rule_is_unchanged`.
4. R1: the saved run carries the count (0 for the serial launched run) alongside the three existing keys: `tests/test_run_teardown_stall_wiring.py::test_a_launched_run_records_phase_totals_and_unaccounted_seconds`; the report shape: `tests/test_run_teardown_stall.py::test_excluded_seconds_report_each_kind_and_the_union`.
5. R2: a step with no reachable loop is abandoned on time, later steps (driver, sweep) still run, the phase row is ok=False "abandoned": `::test_a_step_the_cancel_cannot_reach_is_abandoned_not_waited_for`; and `bounded_call(detach=True)` does not hold the caller: `::test_a_detached_step_does_not_hold_the_caller_past_the_timeout`.
6. R2: a detached step that finishes in time returns True and an ordinary exception inside the window still propagates: `::test_a_detached_step_that_finishes_in_time_returns_true_and_raises_like_any_step`.
7. R2: an abort that did not take is re-sent until the step ends (3 sends observed): `::test_an_abort_that_did_not_take_is_re_sent_until_the_step_ends`.
8. R2: a Playwright-style owner (live loop) still runs its step in the calling thread (thread-bound API preserved): `::test_a_playwright_owner_still_runs_in_the_calling_thread`. The parent unit's bounded-teardown tests in `tests/test_run_teardown_stall.py` pass unchanged.
9. The wiring test is deterministic: 5 consecutive runs pass (below), and no assertion depends on real elapsed time.
10. Design rules hold: ruff clean; `run_budget.py` 299 lines, `teardown.py` 141, new test 151; no function over 50 lines; edited in place, no `*_v2`.

## Tests run (worktree src via PYTHONPATH, main venv, one pytest at a time, `-o addopts=`)
- `tests/test_run_teardown_stall.py tests/test_run_teardown_stall_wiring.py` -> `26 passed, 1 warning in 5.67s`
- `tests/test_run_budget_judge_time.py tests/test_teardown_residuals.py` -> `16 passed, 1 warning in 1.10s`
- `ruff check src tests scripts` -> `All checks passed!`
- Hardened test, 5 repeats (five separate pytest processes): `1 passed` in 0.48 s, 0.53 s, 0.59 s, 0.46 s, 0.48 s.
- Tests first: before the source change `tests/test_teardown_residuals.py` was red on the new behaviours (6 failed, 2 passed; one of the 2 passes was a draft of the abandonment test that could not fail, then fixed to assert `returned == []`).
- `autotester doctor` -> `2 violation(s)`, matching the two `decision-citation-known-disputed` rows for D-000 / D-005 at `docs/DECISIONS.md:80,209` (recorded, non-blocking, in no file touched here); no design-rule line shown. NOT run: the full suite (host low on memory).

## Residual / for the checker
- `acted_during_exclusion` counts spends, not seconds: bare `check()` consults spend nothing and the case-start reservation (`parallel_run.py:160`, one call for the whole case cost) counts once. It is an indicator that overlap happened, not a measure of the leaked seconds (still bounded by the allowance, parent verdict P4).
- A detached, abandoned step keeps running on its daemon thread until it returns; no process is killed (B9). It applies only where the owner has no Playwright loop, so a real Chromium path is unchanged.
- Not run: a live Chromium probe (no browser, no .env read).
