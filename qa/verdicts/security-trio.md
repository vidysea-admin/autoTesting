# Verdict - security-trio

**Cycle checked:** 1
**Head checked:** 8c217edb (base b26712ca, 47 commits behind master; merge-tree vs master clean)
**Verdict:** PASS

## Evidence
- New tests (run id safety, xlsx guard, priorities approval): 29 passed. Ruff clean, doctor clean.
- Wide scoped set (123 test files touching run_dir/excel/export/launch/issues/tracker/release), run after the last edit: 1775 passed, 9 failed. All 9 are pre-existing, not caused by this branch: 6 fail identically at the merge-base (cli_subapp_hook, explore_replay x4, ui_runs_serial_entry_order), and these pass on current master (fixed since the stale base); cli_advice_resolves x2 and goal_contract_registration fail on master too.
- AT-900 probes via run_dir: REJECTED `..\x`, `C:\x`, `a/../../b`, `\server\share\x`, `..`, `...`, NUL byte, `con`, `NUL.txt`, `a:b`, `/abs`, RLO+`..`, `.<ZWSP>.`. ACCEPTED as a single literal segment (not traversal on NTFS/POSIX): fullwidth dots U+FF0E, two-dot-leader U+2025, `%2e%2e`, fullwidth slash U+FF0F, division slash U+2215. No escape found.
- AT-925 clean_cell: `= + - @ TAB CR` and the DDE payload `=cmd|' /C calc'!A0` are apostrophe-prefixed; numbers and None untouched; control-char-then-`=` is stripped then prefixed. Writers: crawl_report, issues, report_export, ux_advisory (rows), ai_report (clean_cell), tracker xlsx and CSV (safe_cell) all guarded; header rows are literals. No unguarded writer found. No double-prefix.
- AT-956: 11 tests pass; product code unchanged.

## Advisories (non-blocking)
- A leading space or newline before `=` is not neutralised (Excel does not evaluate these; OWASP only lists the six).
- The apostrophe is literal text in openpyxl output (visible), a known tradeoff.
- run_dir returns the unresolved path; symlinked runs/ children are not checked.
- Rebase onto master before merge to clear the stale-base test failures.
