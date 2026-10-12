# Verdict - fix-baseline-failures, checker A (blind)

Cycle checked: 0
Bound to: worktree .worktrees/chk-baseline-A, detached at origin/wave/fix-baseline-failures = 5c64431ad415955abd027bf59be113820a6ad2ae (merge-base 441224ed). Date 2026-10-12.

VERDICT: FAIL

## What holds
- Diff is tests only (9 files, qa manifest + tests/); no src or other product file changed.
- No assertion weakened. Each changed test differs only in how the link is made (link_dir/link_file) or in the browser probe.
- Junction stand-in valid: a junction is readable through the link (content read back), is not a symlink, and the code under test still refuses it. test_discover already had a junction=True case with the same assertion.
- Symlink 5: 4 pass via junction, 1 (file symlink, test_png_embedding_refuses_a_file_symlink) skips (WinError 1314).
- serial_entry_mix_live skips cleanly (chromium unavailable: TargetClosedError).
- `ruff check src tests scripts`: clean. `autotester doctor`: clean.

## Defect: the asyncio pollution is NOT gone when Chromium is missing
Second leak not fixed: tests/test_browser.py::test_real_headless_launch_navigates_a_data_url calls BrowserSession.start(), which starts the Playwright driver, then skips on launch failure without stopping it. The running asyncio loop then breaks later tests.
- Full suite on the branch (Chromium absent at start): 17 failed, 5291 passed, 113 skipped, 14 xfailed, 128 errors (29:23). Failed: 15 test_ui_intake + 1 test_ui_origin_guard (asyncio.run() cannot be called from a running event loop), 1 test_core env_creation (flake). Errors: 86 playwright "Sync API inside the asyncio loop" (test_browser_scroll_invariance 36, test_browser_visual_order 32, test_browser_unreadable 16, test_browser_scroll_reach 2) plus 42 test_cli_video_review_exits (ffmpeg, known).
- Controlled repro with PLAYWRIGHT_BROWSERS_PATH pointing at an empty dir (Chromium absent):
  - `pytest tests/test_browser.py tests/test_ui_intake.py tests/test_ui_origin_guard.py`: branch 16 failed; base 16 failed (not fixed).
  - `pytest tests/test_browser.py tests/test_browser_scroll_invariance.py`: base 14 passed, 51 skipped; branch 14 passed, 1 skipped, 36 errors. REGRESSION: moving start() outside the try in shape_page (and page_factory) turns a skip into an ERROR whenever a prior leak exists.
- The manifest repro only used test_browser_visual_order.py as polluter (16 -> 0), which is real but not the only polluter.
- With Chromium installed (checked after install): tests/test_[a-b]*.py 1043 passed; test_ui_* clean, so the failures are Chromium-absent only.

## Fix needed
Stop the driver in BrowserSession.start() on launch failure (or in that test's skip path, `s.close()`/`s._playwright.stop()`), so no test leaves a driver running. Consider keeping start() inside a guarded block in the fixtures so a polluted loop skips rather than errors. Re-run the repro with Chromium absent.

## Skips
Chromium-missing skips (test_browser_visual_order and others), file symlink skip (WinError 1314), serial_entry_mix_live (chromium unavailable).
