# Verdict B (adversarial) - entry-browser-reuse

Cycle checked: 0
Head reviewed: ba66be50
Verdict: PASS

Commands re-run by the checker (this worktree, one pytest at a time):
- `uv run pytest tests/test_run_teardown_stall.py tests/test_run_teardown_stall_wiring.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_resilience.py tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_unauth_entry_case.py tests/test_ui_runs_serial_entry_mix_live.py tests/test_ui_runs_parallel_trace.py tests/test_entry_browser_reuse.py tests/test_entry_browser_reuse_run.py -o addopts=` -> 96 passed, 1 skipped.
- `uv run ruff check src tests scripts` -> All checks passed.
- `uv run autotester doctor` -> "doctor: clean" (only D-087 advisory lines). Sizes: run_execution.py 264, entry_browser.py 103, entry_reset.py 52 lines.

Real Chromium (headless, loopback fixtures; throwaway `.work/ebr_probe.py`, `.work/ebr_probe2.py`, not committed). The maker ran nothing against a real browser; this closes that gap.
- `reset_to_logged_out` (browser/entry_reset.py:41-52) after a dirty case that had set an HttpOnly cookie, a JS cookie, localStorage, sessionStorage, IndexedDB, CacheStorage, typed into a password input and opened a second tab: pages 2 -> 1, cookies [sid, js] -> [], base-origin localStorage/sessionStorage/IndexedDB/CacheStorage all empty, password field empty.
- A page with a `beforeunload` handler and typed input did not block the reset (landed on base URL, 1 page).
- Real `EntryBrowserPool` + real `BrowserSession` (ui/entry_browser.py:60-98): same-identity case 2 reused case 1's session with no cookie and no localStorage; a different credential set got a new session and the old one was closed (`_context is None`); an adversarial-tier case got its own session and it was closed at release; an ERRORED case discarded its browser and the next case got a fresh one; a page closed under the pool made the reset raise and the next acquire launched fresh; after `pool.close()` every launched session had `_context is None` (6 launches, 0 left open).

Adversarial checks that held:
- Different credentials never reuse the live browser (`_fits`, entry_browser.py:67-68; a no-credential case fits any identity, a different set drops the browser first).
- Reset navigates only via `session.goto` (browser/session.py:178-183 -> `check_destination`); a base URL outside allowed_domains raises, the pool drops the browser and launches fresh (entry_browser.py:76-80). Secret substitution, `fill`, masking and `SecretStore` untouched (git diff of the unit touches none of them).
- Save before close: `_save_case` runs before `pool.release` in `_run_entry_case`'s finally (ui/run_execution.py:148-153); the single bounded close is `session.close()` -> `close_session` (`_drop`, entry_browser.py:96-103), and `pool.close()` in `_run_entry_cases`'s finally (run_execution.py:208-214) runs before the shared session or fan-out (AT-576 order kept).
- Per-case video: `begin_case_video`/`end_case_video` swap to a fresh page per case (browser/video.py:106-133, 204-221), so the reset's "keep" page is an idle blank page and per-case recordings are unaffected. `evidence_start` slicing (stages/execute.py:196-200) keeps one case's evidence out of the next; the reset's own evidence lands before it.
- RU5 fail-closed wipe remains on every fresh launch (`open_session`, run_execution.py:101-110).

Findings (non-blocking):
W1. Reset clears web storage only for the base origin and the origin the page lands on after `goto(base)` (entry_reset.py:30-36, 51-52). Storage on any OTHER origin a case visited survives the reset. Reproduced: a case that set localStorage on a second origin (port B) still read it after reset (probe key `B_ls_LEAK?` = "LSB"). Pathlynks is single-origin (projects/pathlynks/project.json: one allowed domain), so it is not exploitable there today, but a project whose login state lives in another allowed origin's localStorage/IndexedDB (SSO subdomain) would start a "logged-out" entry case logged in. Cheap fix: also clear every origin in `context.storage_state()["origins"]` (or all origins CDP reports) before returning. Cookies are cleared for all origins already.
W2. Residual the maker already named: on-disk profile (HTTP cache, history) is not re-wiped between pooled cases (manifest "Residual"). Not reproduced as a login leak.
W3. D-115 text says "one logged-in context ... reset page state"; the implementation resets to logged out (stricter, documented in the manifest and entry_browser.py docstring). Accepted as the safer reading; Umesh may confirm.
W4. Process: no separate red run was captured (manifest says so); the claimed 6 -> 4 launch count on the live case file was not re-derived by this check (fixture counts 6 -> 1 and 6 -> 5 are covered by tests that passed).

Probe files live in `.work/` (gitignored).
