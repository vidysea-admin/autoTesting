# Verdict B (adversarial) - entry-browser-reuse

Cycle checked: 1
Head reviewed: ff3cb1f6
Verdict: FAIL

(The cycle 0 B verdict, PASS at ba66be50, is in git history; this file replaces it.)

Judged against: `qa/manifests/entry-browser-reuse.md` (Fix cycle 1), D-115 item 1 (`docs/DECISIONS.md`, D-115), `qa/contracts/ui-run.md` RU5, `core-invariants.md` C12, `browser-and-secrets.md`.

## Commands re-run by the checker (this worktree, one pytest at a time, `-o addopts=`)
- Manifest list (12 files: test_entry_browser_reuse, _run, _serial, test_entry_reset_live, test_run_teardown_stall, _wiring, test_ui_runs_serial_entry_order, _resilience, _entry_screenshot_namespace, test_unauth_entry_case, test_ui_runs_serial_entry_mix_live, test_ui_runs_parallel_trace) -> `111 passed, 1 skipped`. The skip is `test_ui_runs_serial_entry_mix_live.py:64`, a RAM gate (2649 MB free < 3584 MB floor), so no repo test drives the real pool + real Chromium + run loop together; the probes below do.
- `tests/test_entry_reset_live.py` alone: `1 passed` (it ran; it was not the skipped one).
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> `doctor: clean`.

## Blocking finding

**F1. One ERRORED logged-in case closes the lent browser while the loop keeps using it; every remaining case in the tier then ERRORs with "session not started".**
- `ui/run_execution.py:196` calls `pool.note_shared(result)` after each ordinary case that ran in the lent session. `ui/entry_browser.py:116-119` `note_shared` calls `_drop()`, which calls `target.close()` (`:124-130`), for any `Outcome.ERRORED`. But `_run_normal_cases` (`run_execution.py:171-196`) keeps looping on the same `session` object (`:178`, `:189`), which `BrowserSession.close()` has just set to `_context = _page = None` (`browser/session.py:137-144`). The next case hits `session.page` and gets `RuntimeError("session not started")` (`browser/session.py:165-168`).
- `ERRORED` is any exception in a step (`stages/execute.py:164-167`: a locator timeout, a refused navigation, a budget stop), the commonest non-pass outcome in a real run. Before this unit the shared-profile session was not closed by an ERRORED case; the tier carried on, and AT-888 `BrowserRecovery` handled a genuinely closed browser. The recover path is worse: `run_execution.py:186-188` relaunches the session (`recovery.recover()`), then `:196` `note_shared(result)` still sees the original ERRORED result and closes the freshly relaunched browser.
- Reproduced on real headless Chromium with a loopback server, a real `EntryBrowserPool`, a real `_run_entry_case` (login case, PASS, session lent), then a real `_run_normal_cases` over three ordinary cases (probe `.work/ebr_probe_c1_a.py`, gitignored; `run_case` real, grader stubbed):
  ```
  login saved: [('c1', 'completed', '')]
  ordinary: ('p1', 'errored', "NavigationRefused: host 'evil.invalid' is outside allowed domains ['127.0.0.1']")
  ordinary: ('p2', 'errored', 'RuntimeError: session not started')
  ordinary: ('p3', 'errored', 'RuntimeError: session not started')
  ```
  p2 and p3 are healthy cases (`/state`, `/app` on the allowed host); they never ran.
- Why the unit's tests missed it: `tests/test_entry_browser_reuse.py:241-245` (`test_an_errored_shared_case_discards_the_lent_session`) asserts only the pool-level discard (`session.closed and pool.lend() is None`), never that the next ordinary case in the loop still runs; `tests/test_entry_browser_reuse_serial.py` runs only passing ordinary cases.
- Smallest fix, edit in place: an ordinary case's ERRORED outcome must not close a session the tier loop is still using. Either drop the `note_shared` close (let `BrowserRecovery` and the end-of-run `pool.close()` do their jobs, as the shared-profile loop always did), or make `note_shared` only detach the pool's reference (`_session = None`, no `close()`) and have `_run_normal_cases` own closing a detached session. Add regression tests through `_run_normal_cases`: first lent case ERRORED, second and third must still run; and the `is_browser_closed` -> `recover()` path (the relaunched session must stay open). Use a fake session that raises on use after `close()`.

## Warnings (non-blocking, fold in with the fix)

**W1. A lent session can belong to a different account than the project's login.** `lend()` (`entry_browser.py:112-114`) never consults `project.login_case_id`; `order_entry_cases` (`:55-57`) only sorts login cases last in their original order, so the LAST credentialed happy case wins. Reproduced (`.work/ebr_probe_c1_c.py`): project with `login_case_id = c1` (account A), cases c1 (A), c2 (B), c3 (wrong password for A). Run order c3, c1, c2; the live cookie after the entry leg is `sessB`; `lend()` returned the B session and the ordinary case ran as B. Pathlynks today has one credential pair (`PATHLYNKS_USER_EMAIL/PASSWORD`, `projects/pathlynks/project.json`), so it does not trigger there; a multi-role project (Group 11) would run its ordinary cases under whichever role logged in last, not the saved-login role they ran under before this unit. Cheap fix: lend only when the passed login case is `project.login_case_id` (or has the same `context_key`), else fall back to the shared-profile session; and order the `login_case_id` case last. Account separation itself held: a different credential set always dropped the live browser and launched a fresh one (`entry_browser.py:79-88`; in the probe the A session was closed before B opened).

**W2. Reset leaves IndexedDB and CacheStorage of an origin that holds no localStorage.** `entry_reset.py:26-34` finds extra origins from `context.storage_state()["origins"]`, which lists only origins with localStorage. Reproduced on the real pooled `BrowserSession` (`.work/ebr_probe_c1_b.py`): a second origin (other port, allowed host) holding only an IndexedDB record and a CacheStorage entry kept both after the reset (`origin3 idb: IDBTOKEN`, `origin3 cache: c`), while cookies, base-origin localStorage and sessionStorage, and the second origin's localStorage were gone. Exploitable only for a login that lives solely in IndexedDB on a non-base origin; Pathlynks is single-origin. A fix may use `storage_state(indexed_db=True)` where available, or the residual goes into the manifest Known limits.

**W3. Decision and contract text lag the direction change.** D-115 item 1 (`docs/DECISIONS.md`) still says a different role account, a logged-out case and an adversarial probe "still get their own context". Cycle 1 shares one browser with logged-out and adversarial-tier entry cases after a reset, on Umesh's chat line of 2026-10-29 about reusing the login, which does not speak to adversarial cases. The security argument holds (every such case starts after a reset, verified below), but it should be one `append_decision.ps1` entry (Approver Umesh) amending D-115 item 1, and RU5's "wiped before its run" for reused browsers; the checker will fold the RU5 amendment on PASS. Not a code finding.

**W4. Known limit confirmed, not new:** the lent session keeps the `{slug}-entry-test` profile, not the shared project profile (manifest Known limits). Accepted as documented.

## Adversarial checks that held (real headless Chromium, loopback, persistent context via `BrowserSession.start()`)
- Closure of checker A cycle-0 F1 (sessionStorage survives reset): `tests/test_entry_reset_live.py` passes on real Chromium (`entry_reset.py:63` page-level `localStorage.clear(); sessionStorage.clear()`). In the real pooled flow, a login case left an HttpOnly cookie, sessionStorage `tok` and localStorage `ls` on `/app`, plus a second origin's localStorage; the next `pool.acquire` of a logged-out case reused the same browser and read `app state [ss,ls,cookie]: [null,null,""]`, cookies `[]`, second-origin localStorage `None`, and the stray tabs were closed.
- Different accounts never share a live browser unless one credential set contains the other (`_fits`, `entry_browser.py:79-83`); one live driver at a time (AT-576) held.
- Browser left open: after `pool.close()` the session's `_context is None` in every probe; `stages/run_launcher.py:210-226` closes the run's pool in `finally`; the parallel path keeps a per-tier pool closed before fan-out (`run_execution.py:226-244`).
- allowed_domains: reset and every case navigation go through `session.goto` -> `check_destination` (`browser/session.py:178-183`); an off-domain target was refused (`NavigationRefused`) in the probe; `browser/session.py` and `browser/secrets.py` are untouched by the unit (`git diff master --stat`).
- Secrets: no change to `SecretStore.resolve` or masking; `_prime` (`entry_browser.py:60-66`) clears `secret_locators`, `hitl` and the screenshot counter on each entry acquire. The lent session keeps the login case's `secret_locators`, which only over-masks.
- Save before close: `_save_case` (`run_execution.py:148`) precedes `pool.release` (`:150-152`); the single bounded close is `BrowserSession.close` -> `browser/teardown.py::close_session`.
- Order: logged-out cases first, login last (`order_entry_cases`). On the real Pathlynks case file, 7 cases are entry cases and `logs_in` is true only for the 3 happy credentialed ones (one is retired); `auth_wrong_creds` and `input_empty` are false.

## What the maker must do for cycle 2
1. Fix F1 in place (`ui/entry_browser.py::note_shared` and/or `ui/run_execution.py::_run_normal_cases`), tests first, with the loop-level regression tests named above.
2. Fold W1 (lend only to the project's login account) or state in the manifest why not; fix W2 or add it to Known limits; request the D-115 amendment (W3).
3. Re-submit at Fix cycle 2. Probes are re-runnable from the worktree root: `uv run python .work/ebr_probe_c1_a.py` (also `_b`, `_c`; they share `.work/ebr_probe_c1.py`).
