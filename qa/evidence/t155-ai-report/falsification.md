# t155-ai-report falsification (checker, 2026-10-11, sha a4308b35)

Each row: copy of src/tests/scripts/pyproject under the scratchpad (outside the worktree), PYTHONPATH at the copy, green first, then one edit to `stages/ai_report.py`, then red. One pytest process at a time.

| Criterion | Edit | Test node | Before | After (assertion) |
|---|---|---|---|---|
| AI9 | skip tiers with no entries | test_ai9_empty_tier_is_present_and_says_zero | 1 passed | failed: `'behavioural' in ['Summary','static']` |
| AI10 | blocked status BLOCKED -> PASS | test_ai10_blocked_row_for_every_reason | 6 passed | 6 failed: `'PASS' == 'BLOCKED'` |
| AI11 | failure.reason[:5] | test_ai11_every_failure_string_verbatim | 1 passed | failed: reason cut to 'missi' |
| AI12 | write a second file beside the workbook | test_ai12_read_only_deterministic_and_no_model_or_network | 1 passed | failed: file list gained `out/ai.log` |
| AI13 | refusal reason cell emptied | test_ai13_two_refusals_two_rows_no_probe_text | 1 passed | failed: reason `''` |
| AI14 | `clean_cell(redactor.scrub(c))` -> `clean_cell(c)` | test_ai14_planted_secret_never_reaches_a_cell | 1 passed | failed: `CaptureWithheld` (the `assert_clean` gate catches it, so the secret is withheld, not leaked) |
| AI14 | `autosize_columns(ws)` -> `pass` | test_ai14_autosize_columns_is_the_shared_helper | 1 passed | failed: `call_count 0 == 4` |

Probe script and 24-build secret/formula matrix: scratchpad `t155chk/probe.py` (not committed). Key outputs: secret in file = False in every plain, newline/unicode and long case; control-split secret -> report withheld; `=cmd|' /C calc'!A0` -> formula cells in `static` H3/I3/J3/K3 (verdict criterion_id, reason, fix_hint, note) and `adversarial` B6/E6 (refusal target, reason), C3 (run endpoint); refusals.jsonl with invalid UTF-8 -> `UnicodeDecodeError` out of `export_ai_report`.
