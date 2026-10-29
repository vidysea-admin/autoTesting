# Verdict B (adversarial) - entry-reset-cache-relogin

**Unit:** entry-reset-cache-relogin, branch `fix/entry-reset-cache-relogin`, head c1cf25c4 (manifest `qa/manifests/entry-reset-cache-relogin.md`).
**Cycle checked:** 0
**Verdict: FAIL** (one blocking finding, F1; two warnings). Checker B, fresh context. No src or tests edited; probes live in `.work/` (gitignored).

## Summary
W1 (HTTP cache) is fixed and falsified. W3 (relogin) does what it says on account, result count, failure stop and loop bound, but the replay zeroes the lent session's screenshot counter, so after a relaunch the next ordinary cases overwrite the screenshots of the earlier ordinary cases in the run root (F1, reproduced on real Chromium). That is silent evidence loss on exactly the scenario this unit adds.

## Blocking
**F1. The login replay resets `state.screenshots`, so later ordinary cases overwrite earlier cases' evidence.**
Cause: `relogin` calls `_prime(session, login)` (`src/autotester/ui/entry_browser.py:139`), and `_prime` sets `state.evidence_prefix, state.screenshots = case.id, 0` (`entry_browser.py:73`). `relogin` restores `evidence_prefix = ""` afterwards but not the counter. Ordinary cases in a lent session share the run root with the prefix `""` and a counter that only goes up across cases (`browser/evidence.py:144-146`: `name = f"{screenshots:02d}-{label}.png"`). After the replay the counter restarts from the replay's own shot count, so the next ordinary case writes `NN-stepXX-navigate.png` at indexes earlier cases already used.

Repro (real headless Chromium, loopback server, real `BrowserSession`, real `EntryBrowserPool`, real `_run_normal_cases`, real `run_case`; only grading stubbed): `uv run --directory D:/autoTesting/.claude/worktrees/ebr-followup python .work/chk_b_probe_live.py`. Login (2 steps) then plain-1..plain-5, 2 navigate steps each; the browser context is closed inside plain-3's second screenshot. Output:
```
calls (case, prefix, screenshots-before):
   ('plain-1', '', 2) ('plain-2', '', 4) ('plain-3', '', 6)
   ('login', 'login-relogin', 0)          <- the replay, counter zeroed
   ('plain-4', '', 2) ('plain-5', '', 4)
plain-1 evidence: ['03-step01-navigate.png', '04-step02-navigate.png']
plain-2 evidence: ['05-step01-navigate.png', '06-step02-navigate.png']
plain-3 evidence: ['07-step01-navigate.png']
plain-4 evidence: ['03-step01-navigate.png', '04-step02-navigate.png']   <- same paths as plain-1
plain-5 evidence: ['05-step01-navigate.png', '06-step02-navigate.png']   <- same paths as plain-2
files in run root: 03,04,05,06,07 (5 PNGs for 9 recorded screenshots)
```
So plain-1 and plain-2 now point at plain-4's and plain-5's pictures. Second scenario (`FAIL_AT=plain-1`): plain-2 starts at `03-step01-navigate.png`, overwriting the errored plain-1's only screenshot. The same invariant is asserted by `tests/test_ui_runs_serial_entry_mix_live.py` ("one screenshot per step, none overwritten", AT-577 cycle 2). Before this unit a relaunch never touched the counter (`BrowserSession.relaunch` -> `_restart_session`, `browser/video.py:196-200`), so this is a regression introduced by the replay. The fake-based tests cannot see it: `FakeSession.state.screenshots` is never read.

Required fix (in place): in `EntryBrowserPool.relogin`, save `session.state.screenshots` before `_prime` and restore it next to the `evidence_prefix = ""` reset (the replay's files are already under `<id>-relogin/`, so no collision there). Add a test that fails first: a lent session with a counter above 0, a replay that bumps it, and the counter equal to its pre-replay value after `relogin`; ideally also a real-Chromium file-count assertion like the probe's.

## Held (each claim with evidence)
1. **W1 fixed and falsified.** `Network.clearBrowserCache` follows the per-origin clear loop (`src/autotester/browser/entry_reset.py:46-49`). In-memory revert of `_clear_devtools_storage` to the old body (`.work/falsify_plugin.py`, `FALSIFY=nocache`): `tests/test_entry_reset_live.py::test_reset_drops_the_http_cache_...` FAILED (1 failed, 2 passed). Unmodified: 13 passed across `test_entry_browser_reuse_lent.py` + `test_entry_reset_live.py`.
2. **A cache-call failure cannot skip other clears.** Order is origins first, cache last inside one `try/finally` (`entry_reset.py:46-52`); cookies clear before it (`context.clear_cookies()`), and the page's own storage clear runs after the suppressed block (`entry_reset.py:68`). Held, but see W1 below for what a failure still costs.
3. **Relogin never runs another account's credentials.** `_login` is the exact case `release` saw pass, set only when `named and logs_in` (`entry_browser.py:121-123`), cleared by `_drop` (`entry_browser.py:166`). With `login_case_id` set only that case is lent. The live probe replays `login` (`USER`) and every `/priv` hit after it carried the cookie (10 of 10 hits).
4. **No second saved login result.** Live probe: `login results saved in tier: 0`; each plain case has exactly one saved result. The replay's grade result is dropped (`run_execution.py:196-197`, the lambda returns the verdict only).
5. **Remaining cases after a failed replay are never graded as logged in.** Live probe with the replay forced to ERRORED (`LOGIN_FAILS=1`): plain-4 and plain-5 saved ERRORED/INCONCLUSIVE with `browser relaunched and the login was lost: re-login (login) did not pass; remaining cases not run`, no `/priv` hit after plain-3 (hits stop at `?3b`), `lend now: False`. Exceptions in reset/prime/grade are caught into the same reason (`entry_browser.py:141-143`).
6. **Loop bound.** The replay calls `grade` only (never `recovery.recover()`), so it cannot trigger another relaunch; a browser that dies during the replay fails the grade and stops the tier. Relaunches stay capped by `BrowserRecovery` (`stages/browser_recovery.py:51-61`, 3). Note: that cap is per `_run_normal_cases` call (`BrowserRecovery(session)` is built at `run_execution.py:180`), i.e. per tier, not "per run" as the manifest Known limits say. Pre-existing; documentation inaccuracy only.
7. **Falsification of the replay (in-memory, `.work/falsify_plugin.py`).** `noreplay` (relogin does nothing): 5 failed (the 4 new tests plus the updated one). `ignorefail` (replay result ignored, marked logged in): the failing-replay test and the no-login-case test failed. A relogin that always returns a reason: 5 failed. The new tests are discriminating for the replay itself; none of them covers the counter (F1).
8. **Neighbours.** Non-closed ERRORED ordinary case: no replay, session stays (`relaunched` is False; unchanged test passes). Shared-profile session: `lent is None`, relogin not called. `uv run ruff check src tests scripts`: All checks passed. File sizes 295 / 169 / 66 as claimed.

## Warnings (non-blocking)
**W1. A failed `Network.clearBrowserCache` is swallowed, so a stale cached login can survive a "successful" reset.** `reset_to_logged_out` wraps the whole devtools clear in `contextlib.suppress(Exception)` (`entry_reset.py:67`); the module docstring still says "Any failure raises" (`entry_reset.py:7-9`). Before this unit that was harmless for the origins (the page's own clear ran after); now the cache call, which is the only thing standing between a `max-age` authenticated document and a logged-out case, is also silent on failure. No test makes the cache call fail. Suggest: let a failure of `Network.clearBrowserCache` raise (the pool then discards the browser and launches a wiped profile, which is the fail-closed path it already has), or at least record it as a session event.
**W2. Manifest Known limits say the relaunch cap is "3 per run"**; it is 3 per tier (item 6 above). Correct the sentence.

## Close-out
FAIL at cycle 0 on F1 only. Everything else the unit claims held under adversarial probing. Fix cycle 1 needs: the counter save/restore in `relogin`, a failing-first test for it, then re-run the two lent/live test files and `.work/chk_b_probe_live.py` (expect 9 distinct PNGs in the run root, plain-4 and plain-5 on new indexes).
