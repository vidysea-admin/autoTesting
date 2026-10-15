# Manifest - xlsx-formula-guard

**Status:** ready-for-check
**Fix cycle:** 0
**Issues addressed:** AT-925, AT-582

## What changed
- `core/excel.py`: `clean_cell` prefixes `'` on strings starting with = + - @ tab CR (numbers untouched); new `append_row` helper cleans every cell.
- `stages/report_export.py`: run Excel rows go through `append_row` (net 0 lines, stays at 300).
- AT-582: the run export already carried criterion, reason and fix_hint (Failures column) plus repro steps for FAIL/INCONCLUSIVE; pinned by existing test_report_export_reason.py and the new test.
- `ux_advisory.add_ux_sheet` (out of scope) still uses raw append; ai_report and crawl_report already call clean_cell so are covered.
- Pre-existing env failures: 2 symlink tests in test_report_export.py (WinError 1314, no privilege).

## Tests
`tests/test_xlsx_formula_guard.py` (new).
