# Verdict — comment-refusal-ux

**Cycle checked:** 1
**Result:** PASS
**Checker:** independent subagent

## Re-run myself
- tests/test_portal_comments.py + test_ui_auth_policy_table.py: 36 passed; test_portal_access/persona/share/requests: 49 passed.
- `ruff check src tests scripts`: clean. `autotester doctor`: clean.

## Findings
- Refused browser (Accept text/html) comment: status 400, nothing stored, video page re-rendered, `<p class='error' role='alert'>` reason inline, typed time and text restored through `esc` (quote=True, safe in single-quoted attribute and textarea). Test uses a script/onerror payload.
- JSON/non-HTML clients, unknown video or no resource: unchanged `_refused` 400. T-198/TP2 comment tests pass.
- **Defect (fixed by checker):** the maker's issue row reused id AT-994, already taken on master by the /onboard labels issue (AT-995 too). Renumbered to AT-996 via `next_issue_id` against master's rows. Merge note: re-run `next_issue_id` if another branch claimed AT-996 first.
