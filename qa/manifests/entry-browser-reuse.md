# Manifest - entry-browser-reuse

**Status:** ready-for-check
**Fix cycle:** 0
**Authority:** D-115 item (1) (`docs/DECISIONS.md` 2850-2862); cause: `.work/pathlynks-explore/stall-diagnosis.md` section 6
**Branch:** `fix/entry-browser-reuse` (from master 63445fbe). Not merged, not pushed.

## Criteria
1. A run's entry cases share ONE browser launch (one wipe, one launch, one bounded close) while their identity fits. Pinned by `tests/test_entry_browser_reuse_run.py::test_six_entry_cases_of_one_identity_cost_one_launch_one_wipe_one_close` (1 launch, was 6).
2. Before every reuse the browser is reset to logged out, single tab, start URL: stray pages closed, cookies cleared, `session.goto(base_url)`, origin storage cleared (`src/autotester/browser/entry_reset.py:41-52`). A login case after a logged-in case therefore still logs in (`test_a_login_case_after_a_logged_in_case_is_reset_to_logged_out_first`). A failed reset discards the browser and launches a fresh wiped one (`ui/entry_browser.py:71-85`, `test_a_failed_reset_falls_back_to_a_fresh_launch_once`).
3. A case with a different credential set, a logged-out precondition (`requires_unauthenticated`), or an adversarial-tier class gets its own wiped launch, closed straight after it (`ui/entry_browser.py:40-47` `context_key`, `:87-95` `release`; `test_a_different_identity_gets_its_own_browser`, `test_adversarial_and_logged_out_cases_...`). Only one entry browser is ever live (shared `{slug}-entry-test` profile; AT-576).
4. A crash does not poison the next case: an ERRORED outcome, a latched `_restore_error`, or no result discards the browser (`ui/entry_browser.py:87-95`; `test_an_errored_case_discards_...`, `test_a_latched_restore_error_...`, `test_a_case_that_crashes_before_a_result_...`).
5. Save before close is kept: every case is saved (`run_execution.py:148` `_save_case`) before `pool.release`/`pool.close`; the one close at the end of the leg is `session.close()` -> `browser/teardown.py::close_session` (bounded, traced), `run_execution.py:211-215`. Pinned by the six-case test (all 6 saves precede the single close) and the unchanged `test_run_teardown_stall.py::test_an_entry_case_is_saved_before_a_slow_close_...`.
6. Secrets and masking unchanged: no change to `BrowserSession.fill`/`goto`/`screenshot`, `SecretStore`, `allowed_domains`. The reset navigates only through `session.goto` (runs `check_destination`, B6; `test_reset_goes_through_the_session_so_allowed_domains_scoping_applies`).
7. Per-case video/trace/evidence stay per case: `evidence_prefix = case.id` and `screenshots = 0` are set per acquire (`ui/entry_browser.py:50-56`, so files still nest under `run_dir/<case.id>/` numbered from 01), `secret_locators`/`hitl` cleared; `begin_case_video`/`end_case_video` untouched; reset is traced as phase `entry_reset` and counted as housekeeping (`run_execution.py:116-118`).
8. Both run shapes use the pool: `_run_cases_serially` (`:165`) and `_run_cases_in_parallel` (`:232`) both go through `_run_entry_cases` (`:199-215`), which closes the pool before the shared session or fan-out starts (AT-576 order). `_run_entry_case` keeps its signature (new optional `pool=`); with no pool it is launch-run-save-close as before.
9. Design rules: `uv run ruff check src tests scripts` clean; every new/changed file <= 300 lines (run_execution.py 264, entry_browser.py 103, entry_reset.py 52, tests 214 and 198); no function > 50 lines; `autotester doctor` has no violation attributable to this unit (docs/MAP.md and docs/SNAPSHOT.md regenerated with `autotester map` / `autotester snapshot`; the "stale-committed" pair clears on commit; the decision-citation lines are advisory, D-087).

## Files changed
- NEW `src/autotester/ui/entry_browser.py` - `EntryBrowserPool`, `context_key`. A new module because `run_execution.py` (237 lines) had no headroom for it under the 300-line cap; the pool does not launch anything itself (open/reset are injected by `run_execution.py:97-120`, so the existing monkeypatch seams `BrowserSession`, `_wipe_entry_profile` keep working).
- NEW `src/autotester/browser/entry_reset.py` - `reset_to_logged_out`. New for the same reason (`session.py` is at 298 lines, `video.py` 263).
- EDIT `src/autotester/ui/run_execution.py` - `_entry_pool` (new, :97), `_run_entry_case` (:123, optional `pool`), `_run_cases_serially` (:165), `_run_entry_cases` (:199). `_run_cases_in_parallel` unchanged.
- EDIT `tests/test_run_teardown_stall.py:244-255` - the fake case is now a real `Case` (`_case(1)`) because the pool reads `case_class` and step text; assertions unchanged.
- NEW `tests/test_entry_browser_reuse.py`, `tests/test_entry_browser_reuse_run.py`.
- REGEN `docs/MAP.md`, `docs/SNAPSHOT.md`.

## Design choice (reset vs keep the login) - say-why
Pooled cases are reset to logged out, not kept logged in. Entry cases are by definition the ones that start logged out (`stages/run_gates.py::is_entry_case`), so a kept login would let case N's login hide case N+1's sign-in, and a "different context in the same browser" is not possible here (`launch_persistent_context` = one context per browser launch). A reset keeps the pre-D-115 AT-733/RU5 guarantee and still removes what stalled the runs (a launch plus a Chromium teardown per case). The accepted D-115 risk (state left by one case) is bounded by the reset, by discard-after-ERRORED, and by isolation. Residual: the on-disk profile (cache, history) is not re-wiped between pooled cases, only at each launch.

## Launch count, 6-case run
Real planned cases of `projects/pathlynks/cases.jsonl` at this commit (6 non-retired, all entry cases; computed by running `EntryBrowserPool` over them, `/tmp/count.py` style, output below):
```
c0961a auth_wrong_creds None          <- own launch
9ebb56 input_empty ''  | 6b95c2 happy 'PATHLYNKS_USER_EMAIL,PATHLYNKS_USER_PASSWORD' | c0eb91 happy (same) <- one shared launch
70df79 auth_wrong_creds None          <- own launch
22a38c input_empty ''                 <- one shared launch
before launches: 6   after: 4
```
Fixture run in the tests: 6 same-identity entry cases 6 -> 1 (1 wipe, 1 close); a mixed 6 with two wrong-creds cases 6 -> 5. Not done (would cut further, changes entry order): grouping the isolated cases together.

## Targeted test output
```
uv run pytest tests/test_run_teardown_stall.py tests/test_run_teardown_stall_wiring.py tests/test_ui_runs_serial_entry_order.py tests/test_ui_runs_serial_resilience.py tests/test_ui_runs_serial_entry_screenshot_namespace.py tests/test_unauth_entry_case.py tests/test_ui_runs_serial_entry_mix_live.py tests/test_ui_runs_parallel_trace.py tests/test_entry_browser_reuse.py tests/test_entry_browser_reuse_run.py -o addopts=
96 passed, 1 skipped, 1 warning in 22.89s
uv run ruff check src tests scripts   -> All checks passed!
```
The full suite was NOT run (low-memory host, instructed). Not exercised: a live Chromium/real Pathlynks run (the CDP `Storage.clearDataForOrigin` path and the real `context.pages` are covered by fakes only); the checker should run one headed reset against a scratch profile if it wants that proven.
Process note: the tests and code were written in one pass; the red run (before the code existed) was not captured separately.
