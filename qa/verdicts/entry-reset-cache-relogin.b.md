# Verdict B (adversarial) - entry-reset-cache-relogin

**Unit:** entry-reset-cache-relogin, branch `fix/entry-reset-cache-relogin`, head ea0e64d2 (manifest `qa/manifests/entry-reset-cache-relogin.md`, Fix cycle 1).
**Cycle checked:** 1
**Verdict: PASS** (no blocking findings; two non-blocking observations). Checker B, fresh context, combined seat. No src or tests edited; probes live in `.work/` (gitignored).

## Summary
The three cycle-0 findings are closed and each fix was falsified in memory (a test goes red when the fix is removed). The key risk, `reset_to_logged_out` now raising when the HTTP cache cannot be cleared, cannot become an infinite discard/relaunch loop and cannot make entry cases error: it degrades to the pre-D-115 behaviour (one fresh wiped launch for that case).

## Cycle-0 findings
1. **B-F1 (screenshot counter zeroed by the replay): CLOSED.** `EntryBrowserPool.relogin` saves `session.state.screenshots` before `_prime` and restores it with `evidence_prefix = ""` on every exit (`src/autotester/ui/entry_browser.py:137`, `:146-149`). Re-ran the cycle-0 probe on real headless Chromium (`uv run --directory <wt> python .work/chk_b_probe_live.py`): calls show the counter continuing (`plain-4` starts at 7, `plain-5` at 9, was 2 and 4); evidence is 9 distinct ordinary PNGs `03..11-step*.png` plus `login-relogin/` and `login/`; cycle 0 had 5 PNGs for 9 shots. One saved result per ordinary case, 0 for `login`, 10 of 10 `/priv` hits carried the cookie, `lend now: True`. Falsified: `.work/falsify2_plugin.py` `FALSIFY=noshots` (relogin without the restore) -> `test_relogin_leaves_the_screenshot_counter_where_the_ordinary_cases_had_it`, `test_a_failed_replay_also_restores_the_screenshot_counter` and the real-Chromium `test_a_login_replay_after_a_relaunch_does_not_overwrite_earlier_cases_screenshots` all FAILED (3 failed, 10 passed).
2. **W1 (silent cache-clear failure): CLOSED.** `_clear_http_cache` is separate and unsuppressed (`src/autotester/browser/entry_reset.py:54-63`, called at `:80` after the best-effort per-origin clear `:78-79` and before the page's own clear `:81`); the module docstring now matches (`:7-11`). Falsified: `FALSIFY=swallowcache` (wrap it in `suppress`) -> `tests/test_entry_reset_cache_failure.py::test_a_failed_cache_clear_raises_after_the_origin_clears_so_the_pool_discards_it` and `tests/test_entry_browser_reuse_run.py::test_reset_fails_closed_when_devtools_is_unavailable_because_the_cache_cannot_be_cleared` FAILED (2 failed, 9 passed).
3. **W2 (cap per tier): CLOSED.** Manifest Known limits now say "3 per TIER"; matches `BrowserRecovery(session)` built per call at `src/autotester/ui/run_execution.py:180`.

## Key risk: reset now raises without a DevTools session
Facts: the browser is Chromium only (`src/autotester/browser/session.py:108`, `chromium.launch_persistent_context`), so "non-Chromium" cannot occur; the realistic cases are `new_cdp_session` or `Network.clearBrowserCache` failing.
- **Not an infinite loop.** `EntryBrowserPool.acquire` (`entry_browser.py:95-110`) calls `_reset` once on the live session; on exception it `_drop`s and calls `_open`; the fresh browser is never reset (reset is guarded by `self._session is not None`, evaluated before the open). One reset attempt per `acquire`, one launch per failure.
- **Not an all-cases error.** Real-Chromium probe `.work/chk_b_probe_cdp.py`, `MODE=cdp` (every `BrowserContext.new_cdp_session` raises) and `MODE=cache` (`_clear_http_cache` raises): 3 logged-out entry cases, then the login, then 4 ordinary cases lent from it. Output, both modes: all entry cases `completed`, `opens so far 1, 2, 3`, `resets {'n': 1, 'raised': 1}`, `{'n': 2, 'raised': 2}` (every reuse attempt raised, each answered by exactly one fresh launch, resets == opens - 1), login `completed` and `lent True` on its own fresh launch (4 opens in all), `plain-1..4` all `completed` with prefix `''`. So the cost is the pre-D-115 launch per entry case, with the failure visible only as extra launches.
- **Lent relogin path is also bounded, and fail-closed.** `MODE=relogin` (context closed inside `plain-2`, then the cache clear made to fail): `plain-2` errored (closed), `plain-3` and `plain-4` ERRORED with `browser relaunched and the login was lost: re-login (login) RuntimeError: cache clear boom; remaining cases not run`; opens 2 (one relaunch), 1 raised reset, no loop, never graded as logged in. See observation O1.

## Held (re-judged all criteria)
- Criteria 1, 7, 8, 9: above. Criterion 2-4 (relogin replays the remembered login, failure stops the tier with a named reason, one result per case): cycle-0 probe re-run above plus `tests/test_entry_browser_reuse_lent.py` (15 passed with `tests/test_entry_reset_cache_failure.py`).
- Criterion 5 (nothing else touched): `git diff c1cf25c4 ea0e64d2 -- src` touches only `browser/entry_reset.py` and `ui/entry_browser.py`; `reset_to_logged_out` has one caller (`run_execution.py:116`).
- Criterion 6: `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> `doctor: clean`; sizes `run_execution.py` 295, `entry_browser.py` 172, `entry_reset.py` 82; no function over 50 lines.
- Tests run by me, two files per call, one at a time (no full suite, low-memory host): lent + cache_failure 15 passed; reset_live + relogin_evidence_live (real Chromium) 4 passed; browser_reuse + browser_reuse_run 30 passed; parallel_crash_recovery + unauth_entry_case 13 passed.

## Observations (non-blocking)
**O1.** In `relogin`, a reset failure (cache clear) on the relaunched lent browser stops the tier instead of falling back to a fresh wiped launch the way `acquire` does (`entry_browser.py:139-144` vs `:99-106`). Fail-closed, named and bounded, and reachable only when `Network.clearBrowserCache` itself fails; accept as is. A later improvement could relaunch-and-retry once.
**O2.** `Network.clearBrowserCache` is browser-wide, not per origin, so it also empties the cache of anything else in the same Chromium; acceptable because the entry browser serves one project run.

## Close-out
PASS at Fix cycle 1. The maker may flip the manifest to `checked-PASS`.
