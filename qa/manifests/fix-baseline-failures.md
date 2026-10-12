# Manifest — fix-baseline-failures

Status: ready-for-check
Fix cycle: 0

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
