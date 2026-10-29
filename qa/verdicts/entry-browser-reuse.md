# Verdict - entry-browser-reuse (checker A, Mode A)

**Verdict:** FAIL
**Cycle checked:** 0
**Unit:** entry-browser-reuse, branch `fix/entry-browser-reuse`, code head ba66be50 (worktree `D:/autoTesting/.claude/worktrees/entry-browser-reuse`)
**Authority:** D-115 item (1) (`docs/DECISIONS.md`, D-115 `Changes-authorized`: `ui/run_execution.py`, `browser/*`, their tests; no enforcement path touched).
**Judged against:** `qa/manifests/entry-browser-reuse.md` criteria 1-9, `qa/contracts/ui-run.md` RU5 (an entry case starts from a genuinely logged-out state), `core-invariants.md` C2/C12, `browser-and-secrets.md` B5-B9. No contract names this unit; the manifest and D-115 are the source.

## Blocking finding

**F1 (criterion 2 fails on the real browser): `reset_to_logged_out` does not clear `sessionStorage`.**
`src/autotester/browser/entry_reset.py:33` clears origin storage with CDP `Storage.clearDataForOrigin {storageTypes: "all"}`. That CDP call has no session-storage type, so it leaves `sessionStorage` untouched. The only code that clears `sessionStorage` is the JS fallback (`entry_reset.py:18,38`), and the fallback runs only when the CDP session raises (`entry_reset.py:37`). On a normal Chromium the CDP path succeeds, so `sessionStorage` survives into the next entry case.

Proof against real headless Chromium, loopback fixture server (script `reset_proof.py` in the checker scratchpad, run through `BrowserSession(...).start()` and the shipped `reset_to_logged_out`). The start page (`/`) sets nothing, so the surviving value cannot have been re-set by the reload:
```
BEFORE {'cookies': ['sid','vis'], 'ls': 'L', 'ss': 'S', 'pages': 2, 'url': '.../other/page'}
AFTER  {'cookies': [],            'ls': None, 'ss': 'S', 'pages': 1, 'url': '.../'}
```
Cookies (including HttpOnly), localStorage, the extra tab and the URL reset correctly. `sessionStorage` still holds `S`.

Why it matters: sessionStorage is a common place for SPA auth tokens. An entry login case that follows a logged-in case would then start with the token present, which is exactly the hidden-login failure the manifest's design choice ("Pooled cases are reset to logged out") exists to prevent, and it weakens RU5 / AT-733 (start state genuinely logged out). The unit tests cannot see it: `tests/test_entry_browser_reuse_run.py:65-75` drive fakes only, and the CDP-succeeds fake asserts only that the CDP command was sent (`:69`). The manifest itself flags that real Chromium was never exercised.

Smallest fix (edit in place, `entry_reset.py::_clear_origin_storage`): run the page's own `localStorage.clear(); sessionStorage.clear()` after the CDP clear as well, not only in the fallback (and clear sessionStorage for the final page origin if it differs from base). Add one real-Chromium test over the `serve_dir` fixture (tests/conftest.py:136) that sets all three kinds of state, resets, and asserts empty. Re-submit at Fix cycle 1.

## Criteria

| # | Result | Evidence |
|---|---|---|
| 1 one launch, one wipe, one close | PASS | `tests/test_entry_browser_reuse_run.py::test_six_entry_cases_of_one_identity_cost_one_launch_one_wipe_one_close` passes; pool logic `src/autotester/ui/entry_browser.py:68-85` (`_fits`, `acquire`); wipe lives only in `open_session` (`ui/run_execution.py:97-117`). |
| 2 reset to logged out before each reuse | FAIL | See F1. Cookies, extra tabs, URL, localStorage verified on real Chromium; sessionStorage not cleared. Fail-closed on reset error is correct: `entry_browser.py:75-79` drops and relaunches wiped. |
| 3 own launch for different identity / logged-out / adversarial | PASS | `entry_browser.py:40-47` `context_key` (None for `requires_unauthenticated` or adversarial tier), `:68-74` drops on mismatch, `:91` closes after an isolated case. Tests pass. One live browser at a time holds: `_drop` precedes `_open` (`:73-81`). |
| 4 crash does not poison next case | PASS | `entry_browser.py:89-92` discards on ERRORED, latched `_restore_error`, or no result; `run_execution.py:151-154` passes `outcome[0]`. An `acquire` that raises leaves `_session` None so nothing stale is reused. |
| 5 save before close, one bounded close | PASS | `_save_case` at `run_execution.py:148` precedes `pool.release` (`:152`); the end-of-leg close is `pool.close()` in `finally` (`:213-215`) -> `BrowserSession.close` -> `browser/teardown.py::close_session` (`session.py:` close). `test_run_teardown_stall.py::test_an_entry_case_is_saved_before_a_slow_close...` passes. |
| 6 secrets and allowed_domains unchanged | PASS | `git diff master...HEAD` touches no `browser/session.py`, `secrets.py`, `evidence.py`. Reset navigates via `session.goto` (`entry_reset.py:50`), which runs `check_destination`. Credential identity read via `placeholder_keys` over step target/value (`entry_browser.py:45-46`). |
| 7 per-case evidence/video | PASS | `entry_browser.py:50-56` `_prime` sets `evidence_prefix`, `screenshots=0`, clears `secret_locators` and `hitl` per acquire; masking code untouched; reset traced as `entry_reset` and counted housekeeping (`run_execution.py:116-118`). |
| 8 both run shapes use the pool | PASS | `_run_cases_serially` (`:164-166`) and the parallel path both go through `_run_entry_cases` (`:199-215`); pool closed before the shared session / fan-out. `_run_entry_case` keeps its signature plus optional `pool=`; the no-pool path owns and closes a private pool (`:136,152-155`). |
| 9 design rules | PASS | `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: clean (advisory D-087 citation lines only). `run_execution.py` 264, `entry_browser.py` 103, `entry_reset.py` 52 lines; no function over 50. |

## Re-run evidence
- Targeted pytest (manifest list, `-o addopts=`, one at a time): run 1 `1 failed, 95 passed, 1 skipped` (failure: `tests/test_run_teardown_stall_wiring.py::test_a_launched_run_records_phase_totals_and_unaccounted_seconds`); the same 10 files re-run: `96 passed, 1 skipped`; that wiring file alone 4 more times: `8 passed` each. Treated as a timing flake, not blamed on this unit: the test asserts `excluded_s["housekeeping"] >= 0.05` against a `time.sleep(0.06)` wipe (`tests/test_run_teardown_stall_wiring.py:71,86`), and the first run overlapped a `uv` env sync. Not reproduced in 5 further runs; mentioned so the maker is not surprised if it recurs.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: `doctor: clean`.
- Real Chromium reset proof: output above.

## Not judged / residual (not blocking)
- Only origins of base URL and the post-`goto` page URL get storage cleared (`entry_reset.py:51`); a login that lives on another origin keeps that origin's storage across a reuse. Cookies are context-wide so are covered. Worth a line in the fix or the manifest.
- Maker reported no separate red run; process note only.
