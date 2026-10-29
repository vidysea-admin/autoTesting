# Verdict - entry-browser-reuse (checker A, Mode A)

**Verdict:** PASS
**Cycle checked:** 1
**Unit:** entry-browser-reuse, branch `fix/entry-browser-reuse`, code head ff3cb1f6 (worktree `D:/autoTesting/.claude/worktrees/entry-browser-reuse`)
**Authority:** D-115 item (1) plus Umesh's 2026-10-29 chat direction quoted in the manifest ("login huaa use kro, baar baar logout kyu hi krna, fast kro kaam").
**Judged against:** `qa/manifests/entry-browser-reuse.md` criteria 1-10, `qa/contracts/ui-run.md` RU5, `core-invariants.md` C2/C12, `browser-and-secrets.md` B5-B9. No contract names this unit; manifest and D-115 are the source.

## Cycle-0 FAIL closed
F1 (sessionStorage survived the reset) is closed. `src/autotester/browser/entry_reset.py:63` now always runs the page's own `localStorage.clear(); sessionStorage.clear()` after the DevTools clear; `:26-34` also covers every origin in `context.storage_state()['origins']` (checker B W1). Proof on real headless Chromium: `tests/test_entry_reset_live.py` (HttpOnly cookie, localStorage and sessionStorage in one tab, localStorage on a second origin, extra tab) passes. Falsification by me, in memory only, no file edited: patching `entry_reset._CLEAR_STORAGE_JS` to `() => {}` and re-running that test gives `1 failed`, so line 63 is load-bearing.

## Criteria
| # | Result | Evidence |
|---|---|---|
| 1 one pool per run | PASS | `stages/run_launcher.py:210` creates the pool, `:223` passes `pool=pool` to every serial tier, `:225-226` closes once in `finally`. `tests/test_entry_browser_reuse_serial.py::test_a_launched_run_shares_one_entry_browser_across_its_tiers` passes. |
| 2 order | PASS | `ui/entry_browser.py:46-57` (`logs_in`, `order_entry_cases`; stable sort, so logged-out cases keep their order); applied at `ui/run_execution.py:239`. Ordering tests pass. |
| 3 reset only when needed, fail closed | PASS | `entry_browser.py:85-100` `acquire` resets only a browser that already ran something, and `_drop`s then relaunches wiped if the reset raises (`:92-93`). `lend` hands a session over with no reset (`:112-114`). Real-Chromium reset proof above. |
| 4 login hand-off | PASS, proved live | `entry_browser.py:102-119`, `run_execution.py:158-200`. Fake-based tests pass; I added a real-browser probe (below). |
| 5 different account gets own launch | PASS for entry cases | `entry_browser.py:79-83` `_fits` (subset either way; empty fits any), `:87-88` drops on mismatch. Probe: an ADMIN case after a USER login got a new launch and the old one was closed (`_context is None`). See W1 for the ordinary-case path. |
| 6 crash does not poison next | PASS | `entry_browser.py:106-109` discards on ERRORED, `_restore_error`, no result, or a foreign session; `:116-119` `note_shared` discards after an ERRORED lent case. Tests pass. |
| 7 save before close, one bounded close | PASS | `_save_case` `run_execution.py:148` precedes `pool.release` `:153`; the only run-level close is `pool.close()` `run_launcher.py:226` -> `_drop` -> `session.close()` -> `browser/teardown.py::close_session`. `test_run_teardown_stall.py` passes. |
| 8 secrets, allowed_domains, masking, video unchanged | PASS | `git diff 63445fbe..HEAD --stat` touches no `browser/session.py`, `secrets.py`, `evidence.py`, `video.py`. Reset navigates only via `session.goto` (`entry_reset.py:59,64` -> `check_destination`). `_prime` (`entry_browser.py:60-65`) clears `secret_locators`/`hitl`, zeroes `screenshots`, sets `evidence_prefix` per entry case. Per-case video swaps to a fresh page per case (`browser/video.py:106-133`) inside the same context, so cookies and storage survive the swap (probe). |
| 9 parallel path | PASS | `_run_cases_in_parallel` still calls `_run_entry_cases(...)` without a pool, which owns and closes its private pool before the fan-out (`run_execution.py:226-245`). `test_ui_runs_serial_entry_order.py`, `test_ui_runs_parallel_trace.py` pass. |
| 10 design rules | PASS | `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: `doctor: clean` (D-087 advisory lines only). Sizes: run_execution.py 293, run_launcher.py 288, entry_browser.py 130, entry_reset.py 64; no function over 50 (doctor). |

## Re-run evidence
- Manifest pytest list, one invocation, `-o addopts=`: `111 passed, 1 skipped, 1 warning in 38.64s`. `tests/test_entry_reset_live.py` run alone: `1 passed` (not the skip).
- Real-Chromium hand-off probe (scratchpad `ebr_c1_probe.py`: loopback server that sets an HttpOnly cookie on `/login`; real `BrowserSession(record_video=True)`, real `EntryBrowserPool`, shipped `reset_to_logged_out`):
  `{"login_before":"OUT","login_after":"IN","lent_same_object":true,"ordinary_in_lent":"IN","diff_account_new_launch":true,"old_closed":true,"diff_acct_state":"OUT","reuse_same":true,"after_reset":"OUT","launches":2,"all_closed":true}`
  Meaning: the login survives `end_case_video`/`begin_case_video` page swaps into the lent session (no re-login); a different credential set launches a new browser and closes the old; a reuse after reset is logged out; nothing is left open.

## The two questions asked
**Is sharing one browser with adversarial-tier and logged-out cases safe? Yes, within what the manifest claims.** An entry case on a reused browser always passes through `acquire` -> reset first (`entry_browser.py:89-93`); the first case on a browser launches wiped (RU5 wipe kept in `open_session`, `run_execution.py` `_entry_pool`). The reset clears cookies (incl. HttpOnly), local/session storage, IndexedDB/caches/service workers (`storageTypes: "all"`), stray tabs and the URL. Secrets: `SecretStore`/`Redactor` are per run and untouched; `secret_locators` is reset per entry case, and a stale locator can only over-mask. Adversarial-tier non-entry cases never share the pool browser: `lend()` is None after any reset (`_logged_in=False`, `entry_browser.py:98`), so `_run_normal_cases` closes the pool first and uses the shared-profile session (`run_execution.py:166-172`). allowed_domains: the reset and every navigation go through `session.goto`. Residual: the on-disk Chromium profile (HTTP cache, history) is not re-wiped between pooled cases; not a login carrier (checker B, cycle 0).

**Can a lent session reach a case of a different account? Structurally yes, harmless today.** See W1.

## Warnings (non-blocking)
**W1. `lend()` has no identity guard.** `entry_browser.py:112-114` takes no argument and `_run_normal_cases` (`run_execution.py:166,183`) runs every non-entry case of the tier in the lent session regardless of its `context_key`. A project with two credential sets whose ordinary cases use the second account would run them as the first (a possible false pass or masked permission bug). No test covers it. Not exploitable now: every project in `projects/*/cases.jsonl` uses one credential set (pathlynks: `PATHLYNKS_USER_EMAIL`/`_PASSWORD` only), and Group 11 multi-role runs use another path. Cheap fix before a multi-account project lands: `lend(cases)` returns None when any case's `context_key` is non-empty and not `_fits` the pool's key, plus one test.
**W2. D-115 text is now contradicted and no DECISIONS entry records the change.** D-115 item 1 says logged-out cases, adversarial probes and different roles "still get their own context"; cycle 1 shares one browser (after a reset) for logged-out and adversarial entry cases, on Umesh's later chat instruction quoted only in the manifest. Different roles still get their own launch. Owner action: append a D-entry via `scripts/append_decision.ps1` superseding that clause, citing Umesh 2026-10-29. Not a code defect.
**W3. `qa/contracts/ui-run.md` RU5 wording lags the design.** RU5 says the wipe is "the only thing that makes that start state true" and is required before an entry case. Under D-115 the wipe happens at launch only; later entry cases get the logged-out reset. The fail-closed intent holds (reset failure -> discard -> wiped relaunch, `entry_browser.py:92-93`, tested), but the contract text should be amended by the checker/Approver, not the maker. Raised so it is not lost.
**W4. Whole-run real-browser coverage is fakes plus probe.** `BrowserRecovery` on a lent session (`run_execution.py:183`): a restart of the entry-test profile loses session-only cookies, so later ordinary cases would run logged out and fail. Same exposure as the old shared profile, not new, not tested.
**W5. Process:** I did not reproduce the maker's red-first runs, only the green ones and the falsification above.

## Not judged
The Mode B adversarial sweep for cycle 1 is a separate seat.
