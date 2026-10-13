# fix-baseline-failures r2.a: FAIL

Cycle checked: 1
Checker: A (blind), sha 3715c2167cbaa41bfb8d7de1f6d0c8c394eb5f2a (origin/wave/fix-baseline-failures)

## Defect (blocking)
`tests/test_browser_settle.py::test_browser_startup_checks_before_and_after_launch` now FAILS
deterministically (reproduced in isolation). The test fakes the Playwright driver as
`SimpleNamespace(start=...)` with no `stop`. The new `BrowserSession.start()` except-path calls
`self.close()`, which calls `self._playwright.stop()` -> `AttributeError: 'types.SimpleNamespace' object
has no attribute 'stop'`, masking the expected `RunBudgetExceeded`. Fix: give the fake driver a `stop`
(test-side) or make the cleanup tolerant. This test passed on master; it is a regression from cycle 1.
Note: also means a real stop() error during failure cleanup would mask the original error (close() does not
guard stop()); consider try/except around cleanup in start().

## r1 defects: gone
- Chromium ABSENT (PLAYWRIGHT_BROWSERS_PATH=empty dir): test_browser + ui_intake* + ui_origin_guard*: 138 passed, 1 skipped.
  test_browser + scroll_invariance: 14 passed, 51 skipped (no errors).
- Chromium present: 139 passed; 51 passed + 14 xfailed.

## session.py review
- start() failure -> close() -> re-raise original (bare `raise`): correct apart from the stop() masking above.
- close() idempotent (all fields nulled, guarded). OK.
- 3 trimmed lines: removed comment; removed an early pure `timeout = self._timeout()` (re-computed after
  budget check; no side effects); `if scratch.is_dir()` dropped (rmtree ignore_errors). No behaviour change.
- Other start() callers (run_execution x2, manual_login, video restart) do not rely on a half-started session.
- No assertion weakened in the diff (skips/link helpers only).

## Gate
`pytest -o addopts=` full, Chromium + ffmpeg present: 4 failed, 5537 passed, 8 skipped, 14 xfailed.
Failures: test_browser_settle startup_checks (REAL, above); test_core env_creation (known flake);
test_mc_sessionstart_loop_status (known flake); test_crawl_inventory_live logged_in_crawl (passed on
isolated rerun; load flake). Baseline failures otherwise gone; no video errors.
ruff (src tests scripts): clean. doctor: clean.
