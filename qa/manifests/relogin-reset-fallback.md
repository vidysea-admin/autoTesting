# Manifest - relogin-reset-fallback

**Status:** checked-PASS
**Fix cycle:** 0
**Authority:** checker-B verdict of `entry-reset-cache-relogin` (`qa/verdicts/entry-reset-cache-relogin.b.md`), non-blocking observation O1; D-115 item 1.
**Branch:** `fix/relogin-reset-fallback` from `fix/entry-reset-cache-relogin` (e4cb7db2). Not merged, not pushed.

## Criteria
1. If the logged-out reset raises inside `EntryBrowserPool.relogin`, the pool discards that browser and opens ONE fresh wiped one (the injected `open_session`, as `acquire` does), then replays the login case once in it: `src/autotester/ui/entry_browser.py` `_reset_or_replace` (called from `relogin`). The fresh browser is not reset again; the pool's `_session`, `_key` and `_login` point at it, so a later relogin replays again. Test: `tests/test_entry_relogin_reset_fallback.py::test_a_failed_reset_falls_back_to_one_fresh_launch_and_replays_the_login_there` (launches == 2, old closed, replay ran in the fresh session under `case-1-relogin`, lent again, prefix `""`, screenshot counter carried over at 6).
2. Bounded, one fallback per relogin: a fallback replay that does not pass returns the existing named reason (`browser relaunched and the login was lost: re-login (<id>) did not pass; remaining cases not run`), exactly one replay and two launches in all, `lend()` None. Test: `test_a_fallback_replay_that_does_not_pass_keeps_the_named_reason_and_does_not_loop`. A fallback launch that itself raises is named, not raised: `test_a_fallback_launch_that_itself_fails_is_named_not_raised`.
3. Inside the per-tier relaunch cap: `src/autotester/stages/browser_recovery.py` `BrowserRecovery.spend()` charges one relaunch (False once spent, nothing charged); `recover()` now uses it (same behaviour and `stop_reason`). `relogin(..., may_relaunch=...)` asks it before the fallback launch; `src/autotester/ui/run_execution.py` `_run_normal_cases` passes `recovery.spend`. When denied, no launch happens and the reset error is named in the existing stop (`RuntimeError: ...; remaining cases not run`). Tests: `test_a_relaunch_the_tier_may_not_spend_keeps_the_existing_stop_without_a_launch` (pool), `test_the_fallback_launch_counts_against_the_tiers_relaunch_cap` (run level, cap 1: plain-2/3 INCONCLUSIVE, 1 launch).
4. The tier loop follows the replacement: after `relogin`, `_run_normal_cases` rebinds `session` and `recovery.session` to `pool.live()` (new `EntryBrowserPool.live()`), so the next ordinary cases do not run on the discarded browser. Test: `test_the_tier_loop_switches_to_the_fresh_browser_after_the_fallback` (ran = plain-1, case-1, plain-2, plain-3; `_StrictSession` raises on a closed session; no `case-1` result saved; 2 launches in all).
5. Unchanged: a reset that succeeds takes the old path (no launch); a relogin with no remembered login still names its reason; the replay is not a saved result; `acquire` unchanged; `reset_to_logged_out`, `BrowserSession`, `SecretStore` untouched.
6. Design rules: `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> doctor: clean; sizes `run_execution.py` 297, `entry_browser.py` 196, `browser_recovery.py` 65; no function over 50 lines.

Written first: the 6 new tests were run before any src edit and all 6 failed (relogin returned the stop reason, `TypeError: relogin() got an unexpected keyword argument 'may_relaunch'`, no `live()`); after the edit they pass.

## Files changed
- EDIT `src/autotester/ui/entry_browser.py` - `live()`, `relogin(may_relaunch)`, `_reset_or_replace`, docstring.
- EDIT `src/autotester/stages/browser_recovery.py` - `spend()`, `recover()` uses it.
- EDIT `src/autotester/ui/run_execution.py` - `_run_normal_cases` passes `recovery.spend`, rebinds the session (+2 lines).
- TESTS NEW `tests/test_entry_relogin_reset_fallback.py` (6, fakes); EDIT `tests/test_entry_browser_reuse_lent.py` (`_login_then_ordinary` takes an optional `reset=`; default unchanged).

## Tests run (each `uv run pytest <files> -o addopts=`, two files per call, one at a time)
| Files | Result |
|---|---|
| `test_entry_relogin_reset_fallback.py`, `test_entry_browser_reuse_lent.py` | 18 passed |
| `test_entry_relogin_evidence_live.py` (real Chromium), `test_entry_reset_cache_failure.py` | 4 passed |
| `test_entry_browser_reuse.py`, `test_entry_browser_reuse_run.py` | 30 passed |
| `test_ui_runs_parallel_crash_recovery.py`, `test_entry_browser_reuse_serial.py` | 8 passed |
| `test_ui_runs_target_closed.py`, `test_entry_reset_live.py` (real Chromium) | 7 passed |
Full suite not run (low-memory host). `ruff check src tests scripts`: All checks passed. `autotester doctor`: clean.

## Known limits
- The fallback uses `open_session(login)`, which wipes the entry profile; the lent account's saved profile is gone by design, the replay re-creates the login.
- When the cap denies the fallback, the loop's next-iteration `recovery.stop_reason` ("relaunch limit reached") may replace the reset-failure text as the reported reason; both stop the tier.
