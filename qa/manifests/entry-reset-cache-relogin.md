# Manifest - entry-reset-cache-relogin

**Status:** ready-for-check
**Fix cycle:** 1
**Cycle 1:** fixes checker B cycle-0 F1 (blocking), W1 (both checkers) and W2 (`qa/verdicts/entry-reset-cache-relogin.b.md`, `.md`); criteria 7-9 below. Criterion 1's "a failure of the cache call loses no origin" is superseded by criterion 8.
**Authority:** checker-B cycle-2 verdict of `entry-browser-reuse` (`qa/verdicts/entry-browser-reuse.b.md`, warnings W1 and W3), D-115 item 1, D-116.
**Branch:** `fix/entry-reset-cache-relogin` from `fix/entry-browser-reuse` (d141715d). Not merged, not pushed.

## Criteria
1. (W1) `reset_to_logged_out` also empties the browser's HTTP cache: `src/autotester/browser/entry_reset.py` `_clear_devtools_storage` sends `Network.clearBrowserCache` after the per-origin `Storage.clearDataForOrigin` loop (so a failure of the cache call loses no origin clear); module and function docstrings say so. Pinned on a real headless Chromium, loopback only, by `tests/test_entry_reset_live.py::test_reset_drops_the_http_cache_so_a_logged_out_case_never_sees_a_cached_login` (a `/cached` page, `Cache-Control: private, max-age=600`, `LOGGED-IN-ONLY` with the cookie and `PLEASE-LOGIN` without; after the reset the same URL returns `PLEASE-LOGIN`). Written first: it failed at its last assertion (`PLEASE-LOGIN` expected, `LOGGED-IN-ONLY` served from cache) before the one-line fix, and passes after.
2. (W3) After a closed-browser case in a LENT session is recovered (`BrowserRecovery.recover()` True), the project's login case is replayed before the next ordinary case: `src/autotester/ui/entry_browser.py` `EntryBrowserPool.relogin(grade)` resets the relaunched browser to logged out (the same injected `reset`), primes it, runs and grades the remembered login case with evidence under `<login id>-relogin/`, restores `evidence_prefix = ""`, and marks the session lendable again only when that replay PASSED. `_login` is remembered in `release` (the case that made the lent login) and forgotten in `_drop`. Wiring: `src/autotester/ui/run_execution.py` `_run_normal_cases` (`relaunched = recovery.recover()`, then after `note_shared`, `startup_error = pool.relogin(...)` for a lent session only). A shared-profile session is untouched (its login continues from the persistent profile, as before).
3. (W3) A replay that does not pass (or raises, or cannot reset) stops the tier with a named reason through the existing `startup_error` path, so the remaining ordinary cases are reported ERRORED/INCONCLUSIVE with `browser relaunched and the login was lost: re-login (<id>) ...; remaining cases not run` and are never run logged out and graded as logged in; `lend()` is then None for later tiers. The replay is not a second saved result for the login case (the run still has exactly one result per case id).
4. Tests (W3), written first (fakes, `tests/test_entry_browser_reuse_lent.py`): `test_a_relaunched_lent_session_replays_the_login_before_the_next_ordinary_case` (ran = plain-1, case-1, plain-2, plain-3; no `case-1` result saved; prefix restored; still lent); `test_a_login_replay_that_fails_stops_the_tier_with_a_named_reason_not_a_logged_out_pass` (plain-2 and plain-3 never ran, saved INCONCLUSIVE with the reason; not lent); `test_relogin_resets_the_relaunched_browser_first_and_marks_it_logged_in_again`; `test_relogin_with_no_remembered_login_case_names_the_reason`. One existing test, `test_a_closed_browser_case_is_relaunched_and_the_relaunched_session_stays_open`, now expects the login replay in `ran` (intended behaviour change); `test_an_errored_ordinary_case_does_not_close_the_session_...` (non-closed error: no replay) is unchanged and still passes.
5. No change to `BrowserSession`, `SecretStore`, `BrowserRecovery`, allowed-domains scoping, or the other criteria of the `entry-browser-reuse` manifest.
6. Design rules: `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> only advisory warnings and the SNAPSHOT staleness fixed by regenerating (see below); file sizes `ui/run_execution.py` 295, `ui/entry_browser.py` 172, `browser/entry_reset.py` 82; no function over 50 lines.

7. (F1) The login replay no longer restarts the lent session's screenshot counter: `EntryBrowserPool.relogin` (`src/autotester/ui/entry_browser.py`) saves `session.state.screenshots` before `_prime` zeroes it for the replay (whose files live under `<id>-relogin/`) and restores it together with `evidence_prefix = ""` on every exit (pass, fail, exception). Before, plain-4 and plain-5 wrote the same `03/04/05/06-step..png` paths as plain-1 and plain-2 and overwrote them. Tests, written first: real Chromium `tests/test_entry_relogin_evidence_live.py::test_a_login_replay_after_a_relaunch_does_not_overwrite_earlier_cases_screenshots` (real `BrowserSession`, `EntryBrowserPool`, `_run_normal_cases`, `run_case`; the context is closed inside p2; failed first with 4 distinct paths for 7 screenshots), and fakes `test_relogin_leaves_the_screenshot_counter_where_the_ordinary_cases_had_it`, `test_a_failed_replay_also_restores_the_screenshot_counter` (`tests/test_entry_browser_reuse_lent.py`).
8. (W1) A failed `Network.clearBrowserCache` now raises: the cache clear moved out of the suppressed `_clear_devtools_storage` into its own `_clear_http_cache` (`src/autotester/browser/entry_reset.py`), called after the best-effort per-origin clear and before the page's own storage clear, never suppressed. `reset_to_logged_out` raises, `EntryBrowserPool.acquire` discards the browser and launches a fresh wiped one (fail closed; `test_a_failed_reset_falls_back_to_a_fresh_launch_once`). The module docstring now says exactly which failures raise. Tests, written first, `tests/test_entry_reset_cache_failure.py` (fakes): cache failure raises after the origin clears; a failed origin clear stays best effort and the cache is still cleared; a clean reset runs all four clears. The real-Chromium cache test from cycle 0 still passes.
9. (W2) Known limits corrected: the relaunch cap is per tier.

Falsified: with the cycle-0 `entry_reset.py` and `entry_browser.py` restored in place, the 4 new fake tests fail (2 in `test_entry_reset_cache_failure.py`, 2 in `test_entry_browser_reuse_lent.py`); with them restored, they pass.

## Files changed
- EDIT `src/autotester/browser/entry_reset.py` - HTTP cache clear (W1); cycle 1: `_clear_http_cache`, raises (W1).
- EDIT `src/autotester/ui/entry_browser.py` - `_login`, `relogin`, docstring (W3); cycle 1: screenshot counter save/restore (F1).
- EDIT `src/autotester/ui/run_execution.py` - `_run_normal_cases` relaunch flag and replay (W3).
- TESTS `tests/test_entry_reset_live.py` (+1 real Chromium test), `tests/test_entry_browser_reuse_lent.py` (+4, 1 expectation updated; cycle 1 +2), NEW `tests/test_entry_relogin_evidence_live.py` (real Chromium), NEW `tests/test_entry_reset_cache_failure.py` (fakes).
- REGEN `docs/SNAPSHOT.md`.

## Tests run (cycle 1; each `uv run pytest <files> -o addopts=`, two files per call, one at a time)
| Files | Result |
|---|---|
| `test_entry_browser_reuse_lent.py`, `test_entry_reset_cache_failure.py` | 15 passed |
| `test_entry_reset_live.py`, `test_entry_relogin_evidence_live.py` (real Chromium) | 4 passed |
| `test_entry_browser_reuse.py`, `test_entry_browser_reuse_run.py` | 30 passed |
| `test_entry_browser_reuse_serial.py`, `test_run_teardown_stall.py` | 23 passed |
| `test_run_teardown_stall_wiring.py`, `test_ui_runs_serial_entry_order.py` | 29 passed |
| `test_ui_runs_serial_resilience.py`, `test_ui_runs_serial_entry_screenshot_namespace.py` | 9 passed |
| `test_unauth_entry_case.py`, `test_ui_runs_serial_entry_mix_live.py` | 10 passed, 1 skipped |
| `test_ui_runs_parallel_trace.py`, `test_ui_runs_parallel_crash_recovery.py` | 11 passed |
Full suite not run (low-memory host). Existing tests changed in cycle 1 (`tests/test_entry_browser_reuse_run.py`): the fake DevTools session accepts a parameterless `send` and the expected reset log now includes `cdp Network.clearBrowserCache`; `test_reset_still_clears_page_storage_when_the_devtools_clear_is_unavailable` became `test_reset_fails_closed_when_devtools_is_unavailable_because_the_cache_cannot_be_cleared` (the browser is Chromium only, `browser/session.py:108`, so no DevTools session means the cache cannot be emptied, and the reset raises so the pool relaunches wiped). `ruff check src tests scripts`: All checks passed.

## Known limits
- The replay uses the project's `login_case_id` case as remembered by the pool (the lent login); a run whose lent login was another passed happy login is not lent at all (W1 of the parent unit), so this never replays a different account.
- Only the lent session is replayed. A relaunch of the shared-profile session still relies on saved cookies (unchanged, `stages/browser_recovery.py`).
- The replay is graded like any case (one extra judge call for the login case's rubric); its result is not saved.
- The pool is not told the replay happened beyond `_logged_in`; a second closed-browser case replays again, bounded by `BrowserRecovery`'s relaunch cap, which is 3 per TIER (`BrowserRecovery(session)` is built per `_run_normal_cases` call, `run_execution.py:180`), not per run.
