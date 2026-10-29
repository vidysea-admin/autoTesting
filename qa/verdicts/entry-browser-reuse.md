# Verdict - entry-browser-reuse (checker A, Mode A)

**Verdict:** PASS
**Cycle checked:** 2
**Unit:** entry-browser-reuse, branch `fix/entry-browser-reuse`, code head 33ebc6b8 (worktree `D:/autoTesting/.claude/worktrees/entry-browser-reuse`, clean tree at start)
**Authority:** D-115 item (1) as amended by D-116 (master a6e03fa4; Umesh 2026-10-29).
**Judged against:** `qa/manifests/entry-browser-reuse.md` criteria 1-10 (Fix cycle 2), `qa/contracts/ui-run.md` RU5, `core-invariants.md` C2/C12, `browser-and-secrets.md` B5-B9. Prior verdicts: this file at cycle 1 (A PASS, W1-W5) and `entry-browser-reuse.b.md` cycle 1 (B FAIL F1, W1-W4).

## Cycle-1 findings: closed, each falsified by me
Method: a throwaway script (`falsify.py`, scratchpad, in-memory monkeypatch of the shipped module, no repo file edited, `git status` clean afterwards) reintroduces the old behaviour and runs the named tests.

| Finding | Fix (file:line at 33ebc6b8) | Test | Falsification result |
|---|---|---|---|
| B F1: an ERRORED lent case closed the session the tier still used | `ui/entry_browser.py:123-128` `note_shared` only sets `_logged_in = False`, never closes; `ui/run_execution.py:196` unchanged; the closed-browser path relaunches via `BrowserRecovery` (`:186-188`) and `pool.close()` ends it once at run end | `tests/test_entry_browser_reuse_lent.py:88` (errored case, next cases still run), `:101` (closed-browser relaunch stays open), `:115` (pool never closes) | restoring `_drop()` in `note_shared`: red with `RuntimeError: session not started` (the original failure) |
| A/B W1: lend only the project login account | `entry_browser.py:55-56` `_is_project_login`, `:59-62` `order_entry_cases` puts the named login very last, `:115-117` `release` marks lent only for the named login (or, with no `login_case_id`, any passed happy login), `:119-121` `lend` | `test_entry_browser_reuse_lent.py:148`, `:162`, `:170` | patching `_is_project_login` to always true: red at `:155` (order `case-1` before `case-2`) and `:167`, `:175` (account B lent) |
| B W2: IndexedDB-only origin survived the reset | `browser/entry_reset.py:31` `storage_state(indexed_db=True)` feeds the per-origin `Storage.clearDataForOrigin` (`:39-48`) | `tests/test_entry_reset_live.py:88`, real headless Chromium, second origin with IndexedDB only | reverting to `storage_state()`: red, `assert ['auth'] == []` at `:107` |
| A W2 / B W3 (decision text lags) | D-116 now on master (a6e03fa4) amends D-115 item 1 | n/a | read: D-116 states the reset-per-logged-out-case, login-last, lend, own-launch-per-account, wipe-per-launch design that the code implements |
| A W3 (RU5 wording) | amended in this commit | n/a | see "Contract amendment" |

## Criteria
| # | Result | Evidence |
|---|---|---|
| 1 one pool per run | PASS | `stages/run_launcher.py:210-226` (create, pass to every serial tier, close in `finally`); `test_entry_browser_reuse_serial.py` passes |
| 2 order | PASS | `entry_browser.py:46-62`; applied at `run_execution.py` `_run_entry_cases` (`order_entry_cases`); ordering tests pass |
| 3 reset only when needed, fail closed | PASS | `entry_browser.py:90-105` `acquire` (reset only a used browser; reset raise -> `_drop` -> fresh wiped launch); `entry_reset.py:51-66`; real-Chromium test passes (both live tests ran, not skipped) |
| 4 login hand-off | PASS | `entry_browser.py:107-121`, `run_execution.py:149-196`; lent/serial tests pass |
| 5 different account own launch | PASS | `entry_browser.py:84-93` `_fits`; tests in `test_entry_browser_reuse.py` pass |
| 6 crash does not poison next | PASS | `entry_browser.py:111-114` discard on ERRORED entry case, latched `_restore_error`, no result, foreign session; lent case: stop lending, loop continues (F1 above) |
| 7 save before close, one bounded close | PASS | `_save_case` precedes `pool.release` (`run_execution.py:148-153`); only run-level close is `pool.close()`; `test_run_teardown_stall.py` passes |
| 8 secrets / allowed_domains / masking / video unchanged | PASS | reset navigates via `session.goto` (`entry_reset.py:61,66`); `_prime` `entry_browser.py:65-70`; no change to `browser/session.py`, `secrets.py`, video modules in this cycle (`git diff 4ead2e15..HEAD --stat` shows only the cycle-2 files) |
| 9 parallel path | PASS | `_run_entry_cases` without a pool owns and closes it (`run_execution.py` `_run_entry_cases`); `test_ui_runs_serial_entry_order.py`, `test_ui_runs_parallel_trace.py` pass |
| 10 design rules | PASS with two doc notes | `uv run ruff check src tests scripts`: All checks passed. Sizes: run_execution.py 293, run_launcher.py 288, entry_browser.py 139, entry_reset.py 66, new tests 292/175/230/144/108, all <= 300. See notes N1, N2 |

## Re-run evidence (this worktree, one pytest at a time, 2 files per call, `-o addopts=`)
```
test_entry_browser_reuse + _run                    30 passed
test_entry_browser_reuse_serial + _lent            11 passed
test_entry_reset_live + test_run_teardown_stall    20 passed
test_run_teardown_stall_wiring + ..._entry_order   29 passed
test_ui_runs_serial_resilience + ..._screenshot    9 passed
test_unauth_entry_case + ..._entry_mix_live        11 passed   (the live mix test ran; no skip)
test_ui_runs_parallel_trace                         8 passed
total 118 passed, 0 failed, 0 skipped
```
The full suite was not run (low-memory host, instructed).
`uv run autotester doctor`: exits 1 with 2 violations, both `decision-citation-dangling`: `qa/manifests/entry-browser-reuse.md:10` and `:65` cite D-116, which exists on master (a6e03fa4) but not on this branch (cut from 63445fbe; `git merge-base --is-ancestor a6e03fa4 HEAD` = 1). No other violation; the D-087 advisory lines are non-blocking. This clears when the branch is merged with, or rebased onto, master. It is not a code defect; the manifest's "doctor: clean" is true only after that.

## Contract amendment (RU5)
`qa/contracts/ui-run.md` RU5 amended in this commit to match D-116: the dedicated profile is wiped at each browser launch (not before every case); a run reuses one entry browser and resets it to logged out before each entry case that follows another; a different account gets its own launch; a passed login is lent unreset only to following logged-in cases; and the reset is itself a fail-closed measurement (a raise discards the browser and relaunches wiped). The existing wipe-failure requirement and its verification (ERRORED, never PASS, no session started) are unchanged and still pass (`test_unauth_entry_case.py`, `test_run_teardown_stall.py`). A dated amendment-log line was appended. The amendment adds a requirement and weakens none.

## Notes (non-blocking)
- N1. Manifest line citations drifted after cycle 2 (for example `entry_browser.py` is 139 lines, not 130; `entry_reset.py` 66, not 64; `reset_to_logged_out` is `:51-66`, not `:49-64`). Counts still satisfy the 300-line rule. Refresh at the next manifest touch.
- N2. Manifest says doctor clean; true only once D-116 is in the branch (above).
- N3. Known limits stand as the manifest states them: hand-off is proven by fakes plus the cycle-1 real-Chromium probe, not a headed Pathlynks run; CacheStorage-only third origins are unreachable; the lent session keeps the `{slug}-entry-test` profile.
- N4. I did not reproduce the maker's red-first runs; I reproduced the greens and falsified the three cycle-2 fixes.

## Not judged
The Mode B adversarial seat for cycle 2 (`entry-browser-reuse.b.md`) is separate; this verdict does not substitute for it. Merge and push are not done here (instructed).
