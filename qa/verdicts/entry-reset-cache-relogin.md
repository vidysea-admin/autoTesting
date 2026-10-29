# Verdict A (contract) - entry-reset-cache-relogin

Cycle checked: 0
Code head reviewed: c1cf25c4 (branch `fix/entry-reset-cache-relogin`, worktree `.claude/worktrees/ebr-followup`)
Verdict: PASS (2 warnings, none blocking)

Judged against: `qa/manifests/entry-reset-cache-relogin.md` (Fix cycle 0), warnings W1 and W3 of `qa/verdicts/entry-browser-reuse.b.md`, D-115 item 1, D-116.

## Commands re-run by the checker (`-o addopts=`, 2 files per call, one at a time)
| Command | Result |
|---|---|
| `pytest tests/test_entry_browser_reuse_lent.py tests/test_entry_reset_live.py` | 13 passed (live Chromium test ran, not skipped) |
| `pytest tests/test_entry_browser_reuse.py tests/test_entry_browser_reuse_run.py` | 30 passed |
| `pytest tests/test_entry_browser_reuse_serial.py tests/test_run_teardown_stall.py` | 23 passed |
| `pytest tests/test_run_teardown_stall_wiring.py tests/test_ui_runs_serial_entry_order.py` | 29 passed |
| `pytest tests/test_ui_runs_serial_resilience.py tests/test_ui_runs_serial_entry_screenshot_namespace.py` | 9 passed |
| `pytest tests/test_unauth_entry_case.py tests/test_ui_runs_serial_entry_mix_live.py` | 10 passed, 1 skipped (the live mix test's own environment skip) |
| `pytest tests/test_ui_runs_parallel_trace.py tests/test_ui_runs_parallel_crash_recovery.py` | 11 passed |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor` | `doctor: clean` (advisory decision-citation warnings only) |
| `wc -l` | `ui/run_execution.py` 295, `ui/entry_browser.py` 169, `browser/entry_reset.py` 70 (manifest says 66; all under 300) |

## Criteria
1. PASS (W1). `entry_reset.py:_clear_devtools_storage` sends `Network.clearBrowserCache` after the per-origin `Storage.clearDataForOrigin` loop, with the comment "last: a failure here loses no origin"; module and function docstrings updated. Live test `test_reset_drops_the_http_cache_so_a_logged_out_case_never_sees_a_cached_login` passed on real Chromium. Independent probe `.work/erc_probe_a.py` (real Chromium, loopback, `Cache-Control: private, max-age=600`): with the fix `cached_after=PLEASE-LOGIN`; with the cache call made to raise, `cached_after=LOGGED-IN-ONLY` (so the test does discriminate the one-line fix) while `ls_after=None` and `cookies=[]` (the origin clears were not skipped by the cache failure).
2. PASS (W3). `EntryBrowserPool.relogin` (`ui/entry_browser.py`), `_login` set in `release` only when `_logged_in` and cleared in `_drop`; wiring in `run_execution.py:_run_normal_cases` (`relaunched = recovery.recover()`, then `pool.relogin(...)` after `note_shared`, for a lent session only). Tests pass.
3. PASS (W3). A non-PASS, raising or un-resettable replay returns the named reason; `startup_error` carries it so remaining cases are saved ERRORED/INCONCLUSIVE and never run; `_logged_in=False` is set before the replay and set True only after a PASS, so `lend()` is None afterwards. The replay verdict is not saved (`_save_case` is not called for it; probe below shows no `case-1` row in saved results).
4. PASS. The four named tests exist and pass; the one changed expectation (`ran` now includes `case-1`) is the intended behaviour change; the non-closed-error test is unchanged and passes.
5. PASS. `git diff d141715d c1cf25c4 --stat` touches only `entry_reset.py`, `entry_browser.py`, `run_execution.py` (plus tests, manifest, SNAPSHOT); no change to `BrowserSession`, `SecretStore`, `BrowserRecovery` or allowed-domains.
6. PASS. ruff and doctor as above.

## Adversarial focus items
- Different account: PASS. `_login` is exactly the case that made the lent login (`release`, which already requires the named project login via `_is_project_login`, W1 of the parent unit), so the replay reuses that account's `{{SECRET:KEY}}` set and `_prime(session, login)` re-primes with it. A non-login or other-account case can never become `_login` (set to None when `_logged_in` is False; cleared on `_drop`).
- Second saved login result: PASS. `.work/erc_probe_b.py` (6 ordinary cases that all close the browser): saved results and verdicts contain only plain-1..plain-6, no `case-1`. Replay evidence nests under `case-1-relogin/` and the replay video is `<prefix>/<case_id>.webm`, so it cannot overwrite the original.
- Loop beyond the 3-relaunch cap: PASS. Same probe: `ran = plain-1, case-1, plain-2, case-1, plain-3, case-1, plain-4`, `relaunches 3`; plain-4 closing hit `BrowserRecovery.recover()` -> False (`stop_reason`), no relogin, plain-5 and plain-6 saved with "browser closed: relaunch limit reached (3 per run); remaining cases not run". At most 3 replays per run; the replay itself never calls `recover()`, and `BrowserSession._restart_session` has its own cap.
- Remaining cases after a failed replay never graded as logged in: PASS (criterion 3; test `..._not_a_logged_out_pass`). A grader failure on the replay also yields a non-PASS verdict, so the tier stops (conservative).
- Network.clearBrowserCache failure cannot skip other clears: PASS for clears (probe above).

## Warnings (not blocking)
- Cache-call failure is silent. `reset_to_logged_out` wraps `_clear_devtools_storage` in `contextlib.suppress(Exception)` (`entry_reset.py`, pre-existing), so a failed `Network.clearBrowserCache` leaves the reset reporting success while the HTTP cache still serves the logged-in document (probe: `raised=False`, `cached_after=LOGGED-IN-ONLY`). The module docstring still says "Any failure raises". The criterion only requires that no origin clear is lost, which holds; consider letting the cache call raise (fail closed, the pool then relaunches a wiped browser) as a follow-up.
- The relogin replay was proven with fakes at pool/tier level only; no real-Chromium end-to-end of "crash, relaunch, reset, replay login". The reset itself and a real relaunch are each covered live elsewhere, and the replay reuses both. Also a failed replay's video (kept for non-PASS) is attached to a result that is never saved, so it is an orphan file under `<run>/case-1-relogin/`; harmless.

## Close-out
PASS for c1cf25c4. No blocking findings.
