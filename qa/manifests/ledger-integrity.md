# ledger-integrity

Status: ready-for-check
Fix cycle: 0

**Issues addressed:** AT-676 (high, open -> fixed), AT-645 (high, open -> fixed; code half, data migration run by maker)

## Built
- `src/autotester/ledger/issue_ids.py`: `append_issue` refuses a duplicate id, `next_issue_id`, doctor rule `issue-id-duplicate` (`check_issue_id_unique`), wired in `doctor.run`.
- `qa/issues-dupes-grandfathered.json`: 24 {id,title} entries (12 ids x 2 rows); a repeat is tolerated only while every row is listed; list only shrinks.
- `scripts/renumber_duplicate_issue_ids.py` (`--dry-run`, `--path`, `--grandfather`); NOT run for real.
- `tests/test_issue_ids.py` (6 tests); `docs/MAP.md` regenerated.

## Dry-run plan (old -> new, later row only)
AT-288->AT-994, AT-289->AT-995, AT-290->AT-996, AT-291->AT-997, AT-547->AT-998, AT-548->AT-999, AT-549->AT-1000, AT-550->AT-1001, AT-551->AT-1002, AT-552->AT-1003, AT-710->AT-1004, AT-745->AT-1005 (12 rows)

After the real run, empty `qa/issues-dupes-grandfathered.json` (use `--grandfather`). Prose references to those ids in manifests stay ambiguous.

## Verify
per-file pytest (issue_ids, ledger, ledger_checks, doctor) 99 passed; ruff clean; `autotester doctor` clean.
