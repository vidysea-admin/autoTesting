# Verdict - teardown-residuals (checker A: contract)

**Cycle checked:** 0
**Verdict:** PASS (no blocking finding; three non-blocking observations O1-O3)
**Checked:** branch fix/teardown-residuals @ 30235e16 (base a6e03fa4), worktree only. Sources: manifest `qa/manifests/teardown-residuals.md`, parent verdict `qa/verdicts/run-teardown-stall.b.md:35-36` (R1, R2) and `:30` (P9). Probes (gitignored): `.work/mut/`, `.work/base/`. No browser, no .env read (a dummy `AUTOTESTER_APPROVAL_KEY` literal was used only for probes run outside `tests/conftest.py`).

## Commands run (main venv, `PYTHONPATH=<worktree>/src`, one pytest at a time, `-o addopts=`)
- `pytest tests/test_run_teardown_stall.py tests/test_run_teardown_stall_wiring.py` -> `26 passed, 1 warning in 26.86s`
- `pytest tests/test_run_budget_judge_time.py tests/test_teardown_residuals.py` -> `16 passed, 1 warning in 1.36s` (matches the manifest)
- `python -m ruff check src tests scripts` -> `All checks passed!`
- `wc -l`: `run_budget.py` 299, `teardown.py` 141, `test_teardown_residuals.py` 151 (cap 300).
- `autotester doctor` -> `2 violation(s)`: only the two `decision-citation-known-disputed` rows (`docs/DECISIONS.md:80,209`); no design-rule line. (Dangling citations to decisions newer than the base are not defects per brief.)
- Wiring test, 3 extra consecutive runs: `1 passed` x3 (1.23 s, 1.26 s, 0.92 s).

## Criteria
1. PASS. R1 serial = 0: `test_a_serial_run_records_no_spend_inside_an_excluded_scope` passes; source `run_budget.py:198-200` increments `_overlapped` only when `(actions or probes) and self._excluded.active`.
2. PASS. Counted once per non-zero successful spend, bare `check()` and out-of-scope spend not counted (`test_spends_made_while_a_scope_is_open_are_counted_once_each`, expects 2.0). The increment sits after both refusal returns (`:195-197`).
3. PASS. Refused spend not counted; clock rule unchanged: 99 s acting + 20 s housekeeping allowed, 101 s refused (`test_a_refused_spend_is_not_counted_and_the_clock_rule_is_unchanged`). The diff to `run_budget.py` adds only `_overlapped`, the report key and the `:198-200` count; no clock arithmetic touched.
4. PASS. `Run.excluded_s` carries the key (`schema/run.py` description only, no new field); wiring test asserts the 4-key set; `test_excluded_seconds_report_each_kind_and_the_union` expected dict gained the key (the only edit in that file, `git diff`).
5. PASS. A loop-less step is abandoned on time, driver and sweep still run, phase row ok=False "abandoned" (`test_a_step_the_cancel_cannot_reach_is_abandoned_not_waited_for`, asserts `returned == []` so the wedge was still running when `close_session` returned); `teardown.py:56-74,118-120`. Contrast P9 of the parent verdict (3.0 s for a 1 s timeout).
6. PASS. Detached success returns True; an exception inside the window is re-raised in the caller (`teardown.py:72-73`; test passes).
7. PASS. Cancel re-sent every `timeout_s` until the step ends (`_watch` loop `:91-97`; test observes 3 sends and `finished is False`). The `done.is_set()` re-check at `:93` prevents cancelling a finished step.
8. PASS. Owners with a live loop keep the in-thread step + cancel (`_teardown_step` passes `detach=_loop_of(owner) is None`, `:118-119`; `test_a_playwright_owner_still_runs_in_the_calling_thread` asserts the step ran on the calling thread). The parent unit's bounded-teardown tests pass unchanged (26 passed above).
9. PASS. No assertion in the wiring test depends on elapsed wall time: `run_budget.time` is a stub and the wipe is a jump of that clock; exact equalities (`housekeeping == 45.0`, `total == 45.0`, `judging == 0.0`, `acted_during_exclusion == 0.0`). 3 further consecutive passes (the manifest's 5 were not repeated).
10. PASS. Ruff clean, sizes above, `_teardown_step` / `bounded_call` / `_run_detached` all under 50 lines, edited in place, no `*_v2`.

## Extra checks requested
- **Tests-first / tests discriminate.** Ran `tests/test_teardown_residuals.py` against base `a6e03fa4` src (`git archive` into `.work/base`): `7 failed, 1 passed`; the one pass is `test_a_playwright_owner_still_runs_in_the_calling_thread`, which is a preservation test and correctly green on both.
- **Hardened wiring test still fails if the wipe is not recorded as housekeeping.** Mutant copy of `src/` with `ui/run_execution.py:112` changed from `with wipe, _housekeeping(budget):` to `with wipe:`; probe copy of the test printed `{'judging': 0.0, 'housekeeping': 0.0, 'total': 0.0, ...}` and failed `assert 0.0 == 45.0`; unmutated src printed `housekeeping 45.0`, passed. (Gotcha for anyone repeating this: under `tests/`, pytest's own path setup wins over `PYTHONPATH`, so a mutant run in-place wrongly passes; the probe must live outside `tests/`.)
- **R2 cannot leak a live browser.** Detach happens only when `_loop_of(owner)` is None (`teardown.py:33-38`: no `_loop` attribute, not an event loop, or a closed loop). Real Playwright `BrowserContext` and `Playwright` are `SyncBase` subclasses (verified: `issubclass(...) -> True, True`; `_sync_base.py:91` sets `self._loop`), so the real path (`session.py:102,108` `sync_playwright().start()`, `launch_persistent_context`) has a loop and stays in-thread. The only real object that goes detached is one whose loop is already closed; its call raises "Event loop is closed" immediately (`_sync_base.py:102-104`), same as before, and no browser is reachable through it.
- **R2 cannot double-run a step.** `_run_detached` starts one worker per call, `_teardown_step` calls `bounded_call` once, there is no retry; after abandonment only the sweep and driver step run, which are distinct steps. The abandoned worker's later outcome is held in a local list and never re-raised.

## Observations (non-blocking)
- **O1.** `acted_during_exclusion` counts spends, not seconds, and the case-start reservation counts once (manifest says so); the key lives in a `dict[str, float]` named `excluded_s`, so a reader could misread 2.0 as seconds. The `Run.excluded_s` description (`schema/run.py`) and `excluded_report` docstring both say it is a count; acceptable.
- **O2.** The re-send watcher has a theoretical window between the `done.is_set()` check and `abort()` in which the step could finish; at a `timeout_s` of 20 s the next step starting inside that window is negligible and the cancel is a client-side one. Not a regression of the old one-shot timer.
- **O3.** An abandoned detached thread keeps running until its step returns (no kill, B9), as the manifest discloses. No live Chromium probe was run by the maker or by this check.

## Integration
Merge-safe on its own: no `docs/DECISIONS.md`, `qa/contracts`, or enforcement path touched. Not pushed, not merged (per brief).
