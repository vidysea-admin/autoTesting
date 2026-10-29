# Verdict B (adversarial) - entry-browser-reuse

Cycle checked: 2
Code head reviewed: 33ebc6b8 (HEAD ea99579f adds only `qa/contracts/ui-run.md` and `qa/verdicts/entry-browser-reuse.md`; `git diff 33ebc6b8 ea99579f --stat` shows no `src/` or `tests/` change)
Verdict: PASS (3 warnings, none blocking)

(The cycle 1 B verdict, FAIL at ff3cb1f6, is in git history; this file replaces it.)

Judged against: `qa/manifests/entry-browser-reuse.md` (Fix cycle 2), D-115 item 1, D-116 (master `a6e03fa4`), `qa/contracts/ui-run.md` RU5, `core-invariants.md` C12.

## Commands re-run by the checker (this worktree, `-o addopts=`, 2 files per pytest call, one at a time)
| Files | Result |
|---|---|
| `test_entry_browser_reuse_lent.py`, `test_entry_reset_live.py` | 8 passed |
| `test_entry_browser_reuse.py`, `test_entry_browser_reuse_run.py` | 30 passed |
| `test_entry_browser_reuse_serial.py`, `test_run_teardown_stall.py` | 23 passed |
| `test_run_teardown_stall_wiring.py`, `test_ui_runs_serial_entry_order.py` | 29 passed |
| `test_ui_runs_serial_resilience.py`, `test_ui_runs_serial_entry_screenshot_namespace.py` | 9 passed |
| `test_unauth_entry_case.py`, `test_ui_runs_serial_entry_mix_live.py` | 11 passed (the live mix test ran this time) |
| `test_ui_runs_parallel_trace.py` | 8 passed |
Total 118 passed, 0 failed, 0 skipped (matches the manifest's 118). `uv run ruff check src tests scripts` -> All checks passed. Full suite not run (low-memory host, instructed).
`uv run autotester doctor` -> exit 1, see W2 (a dangling D-116 citation, not a code or design-rule finding). File sizes: run_execution.py 293, run_launcher.py 288, entry_browser.py 139, entry_reset.py 66.

## Cycle 1 findings re-verified on real headless Chromium (loopback server, real `EntryBrowserPool`, real `_run_entry_case` / `_run_normal_cases`, `run_case` real, grader stubbed; probes `.work/ebr_probe_c1_a.py`, `_b`, `_c`, re-run unchanged)
- F1 CLOSED. Probe a, a lent session with `p1` ERRORED (`NavigationRefused`): `p2 completed`, `p3 completed` (was "session not started"). `note_shared` now only sets `_logged_in = False` (`ui/entry_browser.py:123-128`); the loop owns the session and `pool.close()` closes it once.
- W1 CLOSED. Probe c, `login_case_id = c1` (account A), cases c1 (A), c2 (B), c3 (wrong password A): order `c3, c2, c1` (`order_entry_cases` `entry_browser.py:59-62`), live cookie after the entry leg `sessA`, `lend()` returns the session, the ordinary case ran as A.
- W2 CLOSED. Probe b, an origin holding only IndexedDB and CacheStorage: IndexedDB record gone (`db-absent(created-empty)`), cache entry gone, base-origin cookies and storage gone (`_known_origins` uses `storage_state(indexed_db=True)`, `entry_reset.py:31`).

## New adversarial probes (cycle 2), all real Chromium (probes `.work/ebr_probe_c2_a.py` .. `_e.py`, share `.work/ebr_probe_c2_base.py`)
Held:
1. Browser crash mid lent tier (`_a`: `p1` closes the context itself). `p1 errored (TargetClosedError)`, `recovery.recover()` relaunched in place, `p2 completed`, `p3 completed`; the pool still owns the same session object (`pool._session is sess` True); after `pool.close()` `_context` and `_playwright` are None. No second driver (AT-576).
2. Browser crash mid entry case (`_e`: `c1` closes the context). `c1 errored`, `release` discarded it (`release` `entry_browser.py:107-114`), the next entry case got a fresh wiped browser (`cookies of live: []`), `c2 completed`.
3. Multi-tier driver hygiene (`_c`, start/close events logged from `BrowserSession.start/close`): tier 1 login + ordinary case ran in the lent entry-test session (no relaunch, evidence at the run root `01-step01-navigate.png`); tier 2 wrong-password entry case reset in place, then its ordinary case closed the pool's browser BEFORE the shared-profile browser started (`close ebr-entry-test` precedes `start ebr`); tier 3 ordinary-only started and closed its own. Never two live drivers.
4. `login_case_id` absent from the run (`_d`, `login_case_id = "not-here"`, passed happy login): nothing lent, `pool._session` None afterwards, the ordinary case ran in the shared-profile session.
5. Browsers left open: after probes a-e, 0 processes whose command line carries the probe profile directories (`Get-CimInstance Win32_Process`, `ebrc1_`).
6. Accounts and secrets: a credential set that is neither within nor around the live browser's drops it and launches a fresh wiped one (`_fits`, `entry_browser.py:84-88`; unit tests `test_a_different_identity_gets_its_own_browser` in the 30-pass file); only the named project login is lent (probe c, tests `test_another_accounts_passed_login_is_not_lent_when_the_project_names_its_login`, `test_a_run_without_the_project_login_case_lends_nothing`). `browser/session.py`, `browser/secrets.py` untouched by the unit; `_prime` (`entry_browser.py:65-70`) clears `secret_locators` and `hitl` per entry acquire.

## Warnings (non-blocking)

**W1. The HTTP cache survives the reset, so a logged-out entry case can be served an authenticated document.**
Repro: `uv run python .work/ebr_probe_c2_b.py` (real Chromium). A page that returns `LOGGED-IN-ONLY` with `Cache-Control: private, max-age=600` when the cookie is present and `PLEASE-LOGIN` otherwise. After a passed login case the logged-in session fetches it; then `pool.acquire` of the next (wrong-password) entry case reuses the SAME browser and runs `reset_to_logged_out`. Output:
```
logged-in sees: LOGGED-IN-ONLY
same browser: True
after reset sees: LOGGED-IN-ONLY | cookies: []
```
Cookies are empty and the reset passed, yet the case navigates to a page and gets the authenticated body from cache without a request. The wiped-profile launch this unit replaces removed the cache with the directory (RU5/C12 start state); `_clear_devtools_storage` (`entry_reset.py:39-48`) uses `Storage.clearDataForOrigin` "all", which does not include the HTTP cache. Realistic only when an authenticated document is served with freshness headers (an `unauthenticated access to a protected route` case would then see content it should not); Pathlynks responses were not measured. Cheap fix in place: in the same CDP session send `Network.clearBrowserCache` (and `Network.clearBrowserCookies` as belt and braces) in `_clear_devtools_storage`, with a live test beside `test_entry_reset_live.py`; or at minimum add "HTTP cache is not cleared" to the manifest Known limits. Recommend doing it before the first headed Pathlynks run.

**W2. `autotester doctor` is not clean on this branch: dangling D-116 citations.**
`git show 33ebc6b8:docs/DECISIONS.md | grep -c "^## D-116"` -> 0 (D-116 is on master `a6e03fa4`, committed after this branch point `63445fbe`). At 33ebc6b8 the manifest cites D-116 at `qa/manifests/entry-browser-reuse.md:10` and `:65` -> 2 `decision-citation-dangling` violations (the first doctor run of this check: `2 violation(s)`); at HEAD ea99579f `qa/contracts/ui-run.md:35,118,120,125,126` and the verdict files add 10 more -> `12 violation(s)`, exit 1. The manifest line 71 claim "`autotester doctor`: clean" and criterion 10 are therefore not true on the branch as it stands. This is a branch-ordering defect, not a code defect: a merge with master carries D-116 and removes all of them. Condition for merge: merge master into the branch (or merge into master) and re-run `uv run autotester doctor` -> must print `doctor: clean`.

**W3. After a relaunch of the lent session the remaining ordinary cases run logged out, silently.**
Repro: `uv run python .work/ebr_probe_c2_a.py` -> `cookies after relaunch: []` (the probe's login cookie is a session cookie; the persistent profile does not restore it) and `lend: False`; `p2`, `p3` ran in the relaunched browser with no login and are judged as ordinary cases. `BrowserRecovery` has always had this property for session-cookie logins on the shared profile ("login continues from saved cookies", `stages/browser_recovery.py` docstring), so this is not a regression, but the lent session now has no saved-profile login to fall back on (known limit, manifest), so it applies to every relaunch in a lent tier. Suggested follow-up (not for this unit): after `recovery.recover()` on a lent session, stop the tier with the named reason or re-run the login, rather than grade logged-out cases as logged-in ones.

## Accepted, documented (manifest Known limits), unchanged from cycle 1
Only the real-Chromium reset is proven live; the lent session keeps the `{slug}-entry-test` profile (tier 2 and later ordinary cases after a wrong-password reset use the shared-profile session, probe `_c`); CacheStorage on an origin with no localStorage or IndexedDB cannot be listed.

## Close-out
PASS for the code at 33ebc6b8. The merge condition is W2 (doctor clean after master is merged). W1 should be fixed or added to Known limits before a real Pathlynks run; W3 is a follow-up note. No finding blocks.
