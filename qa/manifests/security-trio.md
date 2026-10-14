# Manifest - security-trio

**Status:** ready-for-check
**Fix cycle:** 1
**Issues addressed:** AT-900, AT-925, AT-956

## What changed
- AT-900: `ProjectPaths.run_dir` (core/paths.py) validates the id with `safe_name` and asserts the resolved path stays under `runs_dir`; covers release, release-log and every run-path accessor. Test: tests/test_run_id_path_safety.py.
- AT-925: cherry-picked wave/xlsx-formula-guard (`clean_cell` apostrophe-prefixes = + - @ tab CR; `append_row`). Applied to crawl_report, issues export and ux_advisory sheets; ai_report and report_export already route through it; tracker_export already uses `safe_cell`. Test: tests/test_xlsx_formula_guard.py.
- AT-956: tests/test_run_launcher_priorities_approval.py (7 priorities rows via launch_run + 4 via queued re-check, all refuse with no approval, data root unchanged). No bypass found; product code unchanged.

## Verification
Scoped pytest 196 passed 1 skipped (launcher, release, reports, issues, ux); ruff clean; doctor clean.
