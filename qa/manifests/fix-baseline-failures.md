# Manifest — fix-baseline-failures

Status: superseded
Superseded-by: qa/verdicts/fix-baseline-failures.r3.a.md (branch merged to master)
Fix cycle: 2

**Goal task:** none (test-isolation fixes; no product code changed)

## Root causes and fixes
- **Symlink (5, WinError 1314):** Windows symlink creation needs a privilege. New `tests/symlink_support.py`:
  `link_dir` tries a symlink then falls back to an NTFS junction (same escape the code must refuse);
  `link_file` skips with the reason (no junction equivalent for files). Used in test_discover,
  test_report_export (2), test_ui_crawls, test_ui_video_route_traversal. Assertions unchanged.
- **Asyncio pollution (16, test_ui_intake*/test_ui_origin_guard*):** `tests/conftest.py::page_factory` and
  `test_browser_scroll_invariance.py::shape_page` called `sync_playwright().start()` inside the same `try` as
  `chromium.launch`; with Chromium missing, launch raised, the test skipped, and the started driver (which keeps
  an asyncio loop running on the thread) was never stopped. Fix: `runner.stop()` before skip. Repro: with the
  fix reverted, `test_browser_visual_order.py` + intake/origin files = 16 failed; with it = 0.
- **serial_entry_mix_live:** needs real Chromium (not installed here: "Executable doesn't exist"); it
  had no browser probe. Added the same launch probe other `*_live` files use, skipping when unavailable.
- **Flake (env_creation_is_coordinated_across_processes):** not touched; cause not clear/small.

## Evidence
- Before (12 relevant files): 6 failed, 329 passed; polluter+intake/origin: 16 failed.
- After (11 files incl. polluters): 246 passed, 84 skipped, 0 failed.
- `uv run ruff check src tests scripts`: all checks passed. `uv run autotester doctor`: clean
  (test_discover.py kept at 300 lines).
- No product bug found; no secrets involved.

## Fix note (cycle 1, answers r1.a FAIL)
- Product fix: `BrowserSession.start()` (src/autotester/browser/session.py) now wraps everything after
  `sync_playwright().start()` in try/except BaseException -> `self.close()`; raise, so a failed launch
  stops the driver. Minimal; t177 (wave/t177-slice0-browser-seam) also edits session.py: expect a
  small merge conflict in `start()` (also trimmed 3 lines to stay at the 300-line cap).
- Fixtures `shape_page` and `conftest.page_factory`: start() back inside the try (runner=None first),
  stop runner if started, then skip. Missing Chromium is a skip again, not an error.
- Audit of tests/: other `sync_playwright()` uses are `with` blocks (safe); `BrowserSession.start()`
  callers are covered by the product fix. No other leaks.
- Chromium absent (empty PLAYWRIGHT_BROWSERS_PATH): test_browser+ui_intake*+ui_origin_guard* 138 passed,
  1 skipped, 0 failed; test_browser+scroll_invariance 14 passed, 51 skipped, 0 errors.
- Chromium present: (a) 139 passed; (b) all passed. ruff clean, doctor clean.

## Fix note (cycle 2, answers r2.a FAIL)
- Product fix (browser/session.py, 300 lines): start() except path suppresses any cleanup error then bare `raise`
  of the original; close() runs context.close and driver.stop each guarded (tolerates a driver without stop),
  nulls fields first, idempotent. Test fake unchanged.
- New tests/test_browser_close_tolerant.py: cleanup failure keeps original error; stop() raising tolerated;
  close() idempotent.
- test_browser_settle 10 passed. Repro (a) 139 passed / absent 138 passed 1 skipped; (b) 51 passed 14 xfailed /
  absent 14 passed 51 skipped. ruff and doctor clean.
