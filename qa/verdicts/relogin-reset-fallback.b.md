# Verdict B (adversarial, combined A+B seat) - relogin-reset-fallback

**Unit:** relogin-reset-fallback, branch `fix/relogin-reset-fallback`, head 28ddccbb (manifest `qa/manifests/relogin-reset-fallback.md`, Fix cycle 0).
**Cycle checked:** 0
**Verdict: PASS** (no blocking findings; two non-blocking observations). Fresh context. No src or tests edited; probes live in `.work/` (gitignored). Authority: observation O1 of `qa/verdicts/entry-reset-cache-relogin.b.md`.

## Summary
When the logged-out reset raises inside `EntryBrowserPool.relogin`, the pool now discards the browser, opens one fresh wiped one and replays the login once there (`src/autotester/ui/entry_browser.py:164-178`, `_reset_or_replace`). The launch is charged to the tier's relaunch cap (`src/autotester/stages/browser_recovery.py:44` `spend`, passed at `src/autotester/ui/run_execution.py:199`), and the tier loop rebinds to the replacement (`run_execution.py:200`). Every criterion held, five of six fixes were falsified in memory (a test goes red), and a real-Chromium probe confirmed cap, single fallback, no discarded browser reuse, no leak and monotonic evidence.

## Criteria
1. **Fallback launch and replay: HELD.** Code `entry_browser.py:164-178`: reset raising -> `may_relaunch()` -> `_drop(session)` (closes the old one BEFORE `_open`, so the shared `{slug}-entry-test` profile is free for the wipe) -> `_open(login)`; the fresh browser is not reset again; `_session/_key/_login` point at it. Test `test_a_failed_reset_falls_back_...` passes.
2. **Bounded, one per relogin: HELD.** `_reset_or_replace` runs once per `relogin`; the replay is a single `grade` call; a failed replay or a failed launch is named (`relogin` `except Exception` at `:152-153`, failure string `:159`). Real Chromium, replay forced to fail (`.work/chk_b_fb_live.py::test_replay_fails`): 2 distinct sessions, login ran on sessions [0, 1], `p3..p5` never ran, saved INCONCLUSIVE, 0 browsers open after `pool.close()`.
3. **Inside the per-tier cap: HELD.** Real Chromium, `max_relaunches=1` (`test_cap1`): the closed case spent the only relaunch, reset failed, no fallback launch (1 distinct session), `p3..p5` not run, INCONCLUSIVE, 0 open at the end. Cap 3 (`test_fallback`): 2 distinct sessions (one fallback launch), 1 live at end of tier, 0 after close. `recover()` behaviour unchanged (`browser_recovery.py:53`).
4. **Tier loop follows the replacement: HELD.** Same probe: `login` ran on [0, 1], `p3, p4, p5` all on session 1 (the fresh one), none on the discarded session 0; saved PASS for p3/p4/p5. If `_open` itself fails, `pool.live()` is None and `or session` keeps the old variable, but `startup_error` is then set so no further case runs on it (`run_execution.py:184`).
5. **Unchanged paths: HELD.** Reset that succeeds takes the old path (covered by the unchanged neighbours: 30 passed in `test_entry_browser_reuse.py` + `test_entry_browser_reuse_run.py`; the live probe's reset-OK baseline was not run); `acquire` untouched (`git diff e4cb7db2 HEAD -- src` touches only `entry_browser.py`, `browser_recovery.py`, `run_execution.py`).
6. **Design rules: HELD.** `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> `doctor: clean`; sizes `run_execution.py` 297, `entry_browser.py` 196, `browser_recovery.py` 65, new test 142.

## Key-risk probes
- **No account swap:** `_reset_or_replace` replays only `self._login` (set by `release` for the named project login, `entry_browser.py:105-116`) and sets `_key = context_key(login)`; no other case's credentials reach the fresh browser.
- **Screenshot counter monotonic, no overwritten evidence:** real Chromium, reset failing, browser killed inside `p2`: 9 ordinary PNGs `03..11-step*.png`, all distinct and present on disk (`test_fallback`: "evidence distinct+exist: True"); the fresh session's counter is restored to the ordinary cases' running count at `entry_browser.py:145`, `:157`.
- **No browser left open:** `left_open_after_pool.close=0` in all three probe runs.
- **Neighbour regressions:** none; `test_entry_browser_reuse.py` + `test_entry_browser_reuse_run.py` 30 passed, `test_ui_runs_parallel_crash_recovery.py` + `test_entry_browser_reuse_serial.py` 8 passed, and the unit's own fallback + lent tests 18 passed (two files per call, one pytest at a time, no full suite).

## Falsification (in-memory exec of a mutated source into the live module, `.work/chk_b_falsify_plugin.py`; run on `tests/test_entry_relogin_reset_fallback.py` + `tests/test_entry_browser_reuse_lent.py`, baseline 18 passed)
| Mutation | Result |
|---|---|
| remove the `may_relaunch()` gate | `test_a_relaunch_the_tier_may_not_spend_keeps_the_existing_stop_without_a_launch` FAILED |
| drop the loop rebind (`run_execution.py:200`) | `test_the_tier_loop_switches_to_the_fresh_browser_after_the_fallback` FAILED ("session not started") |
| `spend()` stops charging | `test_the_fallback_launch_counts_against_the_tiers_relaunch_cap` FAILED |
| `relogin` stops passing `may_relaunch=recovery.spend` | same cap test FAILED |
| counter not restored | 3 FAILED (fallback test `0 == 6`, `test_relogin_leaves_the_screenshot_counter_...`, `test_a_failed_replay_also_restores_...`) |
| old browser not dropped before the fresh launch | 2 FAILED (`..._falls_back_to_one_fresh_launch...`, `..._does_not_loop`) |
| drop `self._key, self._login = ...` after the fallback | **survives (18 passed)**, see O1 |

## Observations (non-blocking)
**O1. The "a later relogin replays again" claim is untested.** The line `self._key, self._login = context_key(login), login` (`entry_browser.py:177`) can be deleted and all 18 tests stay green. Probe `.work/chk_b_second.py` (fake pool, two relogins in a row, reset failing both times): current code -> second relogin `None`, 3 launches, first fresh browser closed; with the line removed -> `browser relaunched and the login was lost: no login case to replay`, 2 launches. So the code is right; only the test is missing. Fail-safe either way (named stop, never graded as logged in). Suggest adding that two-relogin test.
**O2. Cap-denied reason text.** As the manifest already notes, when the cap denies the fallback the reported reason may become "relaunch limit reached" rather than the reset error; both stop the tier and are named. Accept.

## Close-out
PASS at Fix cycle 0. The maker may flip the manifest to `checked-PASS`. Not merged, not pushed.
