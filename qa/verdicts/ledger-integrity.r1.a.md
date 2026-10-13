# ledger-integrity r1 checker A

Verdict: PASS
Cycle checked: 0
Branch sha: fa63dfd506dcf3315cc2fbe88fde9c583758ca6f (origin/wave/ledger-integrity); master at check time 04e461f9

## Evidence
- Write guard: append_issue refuses AT-288 with a different title and with the same title (both ValueError naming a free id; next id AT-994).
- Doctor rule issue-id-duplicate: new duplicate red; grandfathered pairs on current master clean; third AT-288 row (same title or new title) red; grandfathered id with edited title red.
- Grandfather list vs current master issues.jsonl (1019 rows): 12 duplicated ids, 24 rows, all 24 id+title entries match exactly, none missing, none stale. ISS-t179b-hg1-* rows add no duplicates.
- Migration on a COPY of master issues.jsonl: dry-run twice byte-identical, file unchanged; plan renumbers 12 later rows only (AT-994..AT-1005); real run on copy: 1019 rows, ids unique, only the id field changed on exactly the 12 later rows; rule clean. Real file never touched.
- Note: after the copy run, --grandfather removes only the later-row entries; the 12 first-row entries remain (stale, harmless, rule still clean). Maker's "empty the list" must be done by hand.
- Union simulation: two branches append different rows with new id AT-994, git merge-file --union keeps both, rule goes red.
- Temp merge onto current origin/master: automatic, clean; doctor shows only the 3 pre-existing t196 decision-citation-dangling lines (unrelated).
- Mutation: disabling both checks fails 3 of 6 tests in tests/test_issue_ids.py; reverted.
- Branch doctor: clean. ruff: clean.
- Full pytest: 5 failed, 5543 passed, 7 skipped, 14 xfailed. The 5 failures are the known symlink tests.
