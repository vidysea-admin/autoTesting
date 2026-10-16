# Verdict - xlsx-formula-guard

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** c513b3638a679ae5b406f793a85bc9b88ec69379 (base b26712caab75995f2cd4040d4f39f4e1fd0db37f; checked on HEAD 880cc70663524376fee6033511859c1893163253, ancestor)

## Scope
AT-925 (formula-leading cells neutralised) and AT-582 (run export carries criterion, reason, fix_hint, repro). Changed: core/excel.py (clean_cell prefix `'` on = + - @ TAB CR, numbers untouched; append_row), stages/report_export.py (run rows via append_row), tests/test_xlsx_formula_guard.py.

## Independent checks (exit codes in .work/xfg/*.rc)
- pytest tests/test_xlsx_formula_guard.py test_report_export_reason.py test_report_export.py test_crawl_report.py test_ai_report.py: 55 passed, 1 skipped, rc 0 (the 2 symlink env failures the maker cited did not occur here).
- ruff check on changed paths: clean, rc 0.
- uv run autotester doctor: clean, rc 0. report_export.py 298 lines, excel.py 46 (<=300).

## Review
- Diff read; clean_cell strips control chars first, then tests the lead, so a control-char-prefixed formula is also caught. Non-strings unchanged (numbers keep type n, asserted).
- Consumers: crawl_report, issues, ux_advisory, ai_report all use clean_cell/append_row; none depend on the raw lead char. Header row and the bundle-note cell (col 12, added by a later commit) are system text, not tested-app text; noted, not a violation.
- Test asserts no cell data_type "f" in the exported run sheet and that reason/fix text survives (AT-582).

## Limits
No sabotage mutation run (shared CPU); the data_type != "f" assertion is directly sensitive to reverting append_row. Full suite not run (post-merge gate). Maker usage not supplied: BOOTSTRAP_REVIEW, ratio unverified; checker tokens not exposed by host (null).
