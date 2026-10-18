# Checkpoint - at1305-capture-settle (cycle 0, checker)
- C1 tests/test_execute_capture_settle.py (7) @3f6efdfb/e9980de3: 7 passed; mutant `_capture_pending -> False` red x3 (2s case, never-settles case, budget case); mutant bound `bound_ms*100` red on test_page_that_never_settles... (sum(timeouts)==500+4000). Copies under .work/tmp/at1305-chk.
- C2 mutant fixed `wait_for_timeout(300)` before the loop -> red on settled-page test (events != [wait,mask,shot]).
- C3 mutant removing Session.screenshot's add_style_tag -> red on mask-order tests.
- Affected set (Pre-check[C3] list, 12 files): 162 passed. ruff clean. doctor: 4 violations, same as base, none in touched files.
- Detector in real Chromium (static HTML): heading Loading False; Logging in... True; unicode ellipsis True; hidden False; aria-busy True; plain False; static <a>Loading...</a> True (AT-1330).
