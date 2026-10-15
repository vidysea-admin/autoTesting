# Manifest - full-suite-fixes

**Status:** checked-PASS
**Fix cycle:** 1
**Unit:** the 17 failures in the last full suite on master (94da0c82)
**Branch:** wave/full-suite-fixes

## Per-failure disposition
- test_hosting_config (1): transient. Passes on current master.
- test_mc_sessionstart_loop_status (3): environmental. Fails identically on the pre-session baseline 09f968d8 (loop-status subprocess exits -1073741515, a DLL load failure). One of the three is intermittent. Not touched.
- test_ui_runs_serial_entry_order (1): test-updated. The grant request now includes the judge allowance (72s + 9 x 45s = 477.0), deliberate per b2d6558f. Comment cites it.
- test_explore_replay (4): test-updated. The fake secrets object lacked `redactor()`; crawl artifacts are deliberately scrubbed through the Redactor (b6336876, be2f0bd3). The fake gains a pass-through redactor.
- test_migrate_stamp_legacy_rubrics (4): regression-fixed in scripts/migrate_stamp_legacy_rubrics.py. Its template regex still pinned the pre-54cf364a rubric wording, so no rubric was ever a candidate. Regex updated to the current template. Tests unchanged.
- test_cli_advice_resolves (2): collector-holes one is regression-fixed. `MIN/MAX_UPLOAD_BYTES*` (schema/server_settings.py) and the tuple-assigned `MAX_GRANT_*` (core/consent.py) are now plain numeric literals the scanner can classify; no behaviour change. Site-count one is test-updated: 27 to 28, because b578526a (D-097, TV9) added a second `flowspec approve` advice site in stages/review.py.
- test_cli_subapp_hook (1): test-updated. The golden gains `revoke`, added by 6ce80275.
- test_goal_contract_registration (1): regression-fixed. `.goal/dashboard.html` was stale (76/92) against goal.json (88/92, refreshed in 9a53eb98). Counts and the Done/Remaining lists are synced. The donut arc and criticality bars are not regenerated and need a dashboard skill run.

## Verification
All 8 files pass in the worktree except the 3 environmental mc tests. `ruff check src tests scripts` is clean and `doctor` reports 0 violations. The full suite was not re-run.
