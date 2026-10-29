# Manifest - entry-browser-reuse

**Status:** ready-for-check
**Fix cycle:** 2
**Authority:** D-115 item (1) (`docs/DECISIONS.md` 2850-2862, "one logged-in context"); cause: `.work/pathlynks-explore/stall-diagnosis.md` section 6. Direction change inside cycle 1, from Umesh 2026-10-29 ("login huaa use kro, baar baar logout kyu hi krna, fast kro kaam"): reuse the login, do not log out between cases.
**Branch:** `fix/entry-browser-reuse` (from master 63445fbe). Not merged, not pushed.

Cycle 0 (verdicts A FAIL F1, B W1) is superseded in two places: criterion 2 (the reset is now fixed AND only used when a case needs a logged-out page) and criterion 3 (no isolation of logged-out / adversarial cases any more; they share the browser after a reset).

Cycle 1 (verdict B FAIL F1, W1-W4; A PASS with warnings) is fixed in cycle 2 below. D-116 (2026-10-29, amends D-115: keep the login across entry cases) is the authority for the login hand-off and the login-last order of cycles 1-2 (checker B W3).

## Criteria
1. One entry browser per RUN, not per case or per tier: `run_cases_traced` creates one `EntryBrowserPool` and passes it to every serial tier, closing it once when the run ends (`src/autotester/stages/run_launcher.py:210-226`). Pinned by `tests/test_entry_browser_reuse_serial.py::test_a_launched_run_shares_one_entry_browser_across_its_tiers` (through `launch_run`: static + adversarial entry cases, 1 start, 1 close).
2. Order: cases that need a logged-out page (wrong password, empty submit, any "logged out" precondition) run first, login cases last (`ui/entry_browser.py:46-57` `logs_in`, `order_entry_cases`; used at `ui/run_execution.py:239`). `logs_in` = the project's `login_case_id`, or a HAPPY-class case that uses credentials and is not a logged-out check. Tests: `test_order_entry_cases_puts_login_last_and_keeps_every_other_order`, `test_logs_in_is_the_happy_path_credentialed_case`, `test_wrong_credentials_and_empty_submit_share_the_browser_and_login_runs_last`. Tier order (static, behavioural, adversarial, D-039) is untouched, so the order is applied within a tier; a wrong-password case in the adversarial tier therefore runs after the static tier's login (see Launch and login count).
3. A session is reset to logged out only before an entry case that runs on a browser that already ran something (`ui/entry_browser.py:85-100` `acquire`); a session being lent is never reset, so a logged-in case does not log in again. Reset = `src/autotester/browser/entry_reset.py:49-64`: stray tabs closed, cookies cleared, `session.goto(base_url)` (allowed-domains scoping, B6), DevTools `Storage.clearDataForOrigin` for base, landing origin and every origin in `context.storage_state()['origins']` (checker B W1; `:26-34`), then ALWAYS the page's own `localStorage.clear(); sessionStorage.clear()` (checker A F1; `:63`; CDP has no sessionStorage type), then `session.goto(base_url)` again. A reset failure raises; the pool discards the browser and launches a fresh wiped one (`test_a_failed_reset_falls_back_to_a_fresh_launch_once`). Real headless Chromium, loopback only: `tests/test_entry_reset_live.py` (HttpOnly cookie, localStorage and sessionStorage in one tab, localStorage on a second origin: all gone).
4. Login hand-off. After a PASSED login case the pool's session is lent to the ordinary (logged-in) cases of that tier (`ui/entry_browser.py:102-119` `release(..., passed=)`, `lend`, `note_shared`; `ui/run_execution.py:158-200` `_run_normal_cases`): same browser, no reset, no re-login, `evidence_prefix` set to "" so ordinary cases keep the shared-run layout. Tests: `test_logged_in_cases_run_in_the_login_session_without_a_reset_or_a_second_launch` (1 launch, was 2), `test_a_passed_login_case_leaves_its_session_to_lend_without_a_reset`, `test_lend_is_none_unless_the_last_case_was_a_passed_login_on_a_healthy_browser`. If the login did not pass, the old shared-profile session is used and the pool's browser is closed first (one live driver at a time, AT-576): `test_a_login_that_did_not_pass_falls_back_to_the_shared_profile_session`.
5. A different account gets its own launch: credential sets that are neither within nor around the browser's (`ui/entry_browser.py:79-83` `_fits`); a wrong-password case (email secret only) and the happy login (email and password) are the same account (`test_a_case_using_some_of_the_same_credentials_is_the_same_identity`, `test_a_different_identity_gets_its_own_browser`).
6. A crash does not poison the next case: an ERRORED case (entry or lent), a latched `_restore_error`, or no result discards the browser (`ui/entry_browser.py:102-119`; `test_an_errored_case_discards_...`, `test_a_latched_restore_error_...`, `test_an_errored_shared_case_discards_the_lent_session`, `test_a_case_that_crashes_before_a_result_is_errored_and_the_next_case_still_runs`).
7. Save before close and one bounded close: each case is saved (`ui/run_execution.py:148`) before `pool.release`, and the only close of the run's browser is `pool.close()` at run end -> `BrowserSession.close` -> `browser/teardown.py::close_session`. `test_run_teardown_stall.py::test_an_entry_case_is_saved_before_a_slow_close_...` unchanged in its assertions.
8. Secrets, `allowed_domains`, screenshot masking, per-case video: no change to `BrowserSession.fill/goto/screenshot`, `SecretStore`, `begin/end_case_video`. Per-case state is primed on each entry acquire (`evidence_prefix = case.id`, `screenshots = 0`, `secret_locators`, `hitl`; `ui/entry_browser.py:60-66`); the reset is traced as phase `entry_reset` and counted as housekeeping (`ui/run_execution.py:116-118`).
9. Parallel path (`plan.n > 1`): unchanged behaviour shape. Each tier's entry leg uses its own pool, ordered the same way, closed before the fan-out starts (siblings need their own profiles, so no hand-off there): `_run_entry_cases` without a `pool` creates and closes one (`ui/run_execution.py:226-244`; `tests/test_ui_runs_serial_entry_order.py` passes).
10. Design rules: `uv run ruff check src tests scripts` clean; `autotester doctor` has no violation except `stale-committed docs/MAP.md`, which clears on this commit (MAP and SNAPSHOT regenerated); all files <= 300 lines (run_execution.py 293, run_launcher.py 288, entry_browser.py 130, entry_reset.py 64; tests 299, 230, 144, 72); no function over 50 lines.

## Files changed (cycle 1 on top of cycle 0)
- EDIT `src/autotester/ui/entry_browser.py` - isolation removed; `logs_in`, `order_entry_cases`, `lend`, `note_shared`, `release(passed=)`, subset-based identity.
- EDIT `src/autotester/ui/run_execution.py` - new `_run_normal_cases` (logged-in cases of a serial tier, lent or shared-profile session), `_run_cases_serially(..., pool=)`, `_run_entry_cases(..., pool=)` orders and optionally owns the pool; `_run_entry_case` passes `passed=`. The shared-session loop moved from `_run_cases_serially` into `_run_normal_cases` unchanged apart from the lent-session branches.
- EDIT `src/autotester/stages/run_launcher.py` (D-115 authorizes "the run launcher") - one pool per run across tiers.
- EDIT `src/autotester/browser/entry_reset.py` - checker A F1 / B W1 (see criterion 3).
- EDIT `tests/test_run_teardown_stall.py` - the entry test's project is a real `Project` (the pool reads `login_case_id`); assertions unchanged.
- TESTS `tests/test_entry_browser_reuse.py`, `tests/test_entry_browser_reuse_run.py`, `tests/test_entry_browser_reuse_serial.py` (new), `tests/test_entry_reset_live.py` (new, real Chromium).
- REGEN `docs/MAP.md`, `docs/SNAPSHOT.md`.

## Launch and login count (Pathlynks)
Real cases of `projects/pathlynks/cases.jsonl` at this commit, through `EntryBrowserPool` + `order_entry_cases` + the tier order (static, behavioural, adversarial), counting launches, resets and `logs_in` cases:
```
3-case (wrong password, empty submit, happy login):
  old launches 3   new launches 1   resets 2   real logins 1
  order run: input_empty, happy*LOGIN, auth_wrong_creds
all 6 planned cases in this repo (2 each of the three; D-115 item 2 retires the duplicates):
  old launches 6   new launches 1   resets 5   real logins 2
```
Why the wrong-password case is not first: it is in the adversarial tier and tier order is a separate decision (D-039). So the run is: empty submit, login (browser now logged in; any logged-in cases of that tier run in it, no re-login), then in the adversarial tier one reset logs out for the wrong-password case. The 1 real login is the happy case; the wrong-password attempt is a deliberate failed login. With logged-in ordinary cases in the same tier as the login, the lent session serves them with no relaunch (`test_logged_in_cases_run_in_the_login_session_without_a_reset_or_a_second_launch`). Logged-in cases in a LATER tier than a reset-to-logged-out run in the shared-profile session instead (the pool's browser is closed first), which costs one launch and no new login attempt on the target by this code.

## Fix cycle 1 evidence
Red first, reset on real Chromium (`tests/test_entry_reset_live.py` before the fix):
```
>       assert page.evaluate(_STORED) == [None, None]  # localStorage AND sessionStorage, same tab
E       AssertionError: assert [None, '1'] == [None, None]
1 failed
```
Green after the fix: `1 passed`. Mutation: with `_known_origins` reduced to base + landing origin the same test fails with `['sso-token', None] != [None, None]` (the second-origin assertion is load-bearing; reverted).
Red first, ordering / hand-off / identity: `tests/test_entry_browser_reuse*.py` failed at import (`cannot import name 'logs_in' from 'autotester.ui.entry_browser'`) before the code, and `test_a_case_using_some_of_the_same_credentials_is_the_same_identity` failed (`1 failed, 22 passed`) before the subset-identity fix (a first version compared credential sets for equality and gave the Pathlynks set 2 launches instead of 1).
Green, one pytest invocation, `-o addopts=`:
```
tests/test_entry_browser_reuse.py tests/test_entry_browser_reuse_run.py tests/test_entry_browser_reuse_serial.py
tests/test_entry_reset_live.py tests/test_run_teardown_stall.py tests/test_run_teardown_stall_wiring.py
tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_resilience.py
tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_unauth_entry_case.py
tests/test_ui_runs_serial_entry_mix_live.py tests/test_ui_runs_parallel_trace.py
-> 111 passed, 1 skipped, 1 warning
uv run ruff check src tests scripts -> All checks passed!
```
The full suite was NOT run (low-memory host, instructed).

## Fix cycle 2 (checker B F1, W1, W2; D-116 cited for W3)
- F1 (blocking). `EntryBrowserPool.note_shared` (`ui/entry_browser.py`) no longer closes the lent session: an ERRORED ordinary case only stops the lending (`_logged_in = False`); the tier loop (`run_execution.py::_run_normal_cases`) keeps running on the live session, relaunches it in place via `BrowserRecovery` on a closed browser, and `pool.close()` still closes it exactly once at run end. Probe `.work/ebr_probe_c1_a.py` on real Chromium: before, `p2`/`p3` errored "session not started"; after, `p1 errored (NavigationRefused)`, `p2 completed`, `p3 completed`. The superseded pool-level test `test_an_errored_shared_case_discards_the_lent_session` is removed (its premise was the bug).
- W1. A project that names `login_case_id` lends only that case's session (`release`), and `order_entry_cases` puts it very last among login cases; if the named case is not in the run nothing is lent (identity cannot be confirmed; ordinary cases fall back to the shared profile). With no `login_case_id` the HAPPY+credentials heuristic stands.
- W2. `reset_to_logged_out` reads `storage_state(indexed_db=True)`, so an origin holding only IndexedDB (no localStorage) is listed and cleared by the per-origin DevTools `clearDataForOrigin`.
- Tests: new `tests/test_entry_browser_reuse_lent.py` (6) drives `_run_normal_cases` with a session that raises after `close()` (errored case then passing cases; closed-browser relaunch path stays open; pool-level; accounts A, B, wrong-password A); `tests/test_entry_reset_live.py` gains an IndexedDB-only second-origin test on real Chromium.
- Red first: loop tests failed with `RuntimeError: session not started` and `assert (not True)` (session closed); W1 tests `lend() is None` failed; live W2: `assert ['auth'] == []`. Green: all pass; combined run of 13 files -> 118 passed (one earlier combined run had `test_run_teardown_stall_wiring.py::test_a_launched_run_records_phase_totals_and_unaccounted_seconds` fail under load; it passes alone and in the repeat, a timing-sensitive test, not touched by this unit).
- ruff clean; `autotester doctor`: clean. Full suite NOT run (low-memory host).

## Known limits
- CacheStorage on an origin that holds neither localStorage nor IndexedDB cannot be reached: neither Playwright nor DevTools can list such origins (`CacheStorage.requestCacheNames` needs a known origin). CacheStorage on the base, landing and any stored origin IS cleared (`clearDataForOrigin` "all"). A login kept only in CacheStorage on a third origin is improbable and is not claimed.
- Only the real-Chromium reset is proven live. The hand-off (lend a logged-in `BrowserSession` to ordinary cases, `evidence_prefix = ""`, `BrowserRecovery` on the entry-test profile) is covered by fakes; a real headed run against Pathlynks was not made. The lent session keeps the `{slug}-entry-test` profile, not the project's shared profile, so ordinary cases that follow a passed login run on a profile logged in by THIS run (the shared profile's saved login is not used in that case).
- `reset_to_logged_out` guarantees the landing origin's sessionStorage and every stored origin's localStorage/IndexedDB; sessionStorage of other origins held by the same tab is not cleared by it (the real run path opens a fresh tab per case via `begin_case_video`, so it is moot there).
- `logs_in` is a heuristic (project `login_case_id`, or HAPPY + credentials); a login case classed otherwise runs in order but is not lent. The cost is a fallback to the shared-profile session, not a wrong result.
- The pool is per run for serial tiers only; the parallel path keeps one pool per tier (criterion 9).
