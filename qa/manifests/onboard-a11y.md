# Manifest — onboard-a11y

**Contract:** qa/contracts/auth.md (AU26 labelled controls; AU16 closed public set)
**Goal task:** none (T-204 / T-198 walk findings)
**Date:** 2026-10-13
**Status:** ready-for-check
**Fix cycle:** 1
**Issues addressed:** AT-994 (/onboard unlabelled controls), AT-995 (/favicon.ico 401 on sign-in pages)

## What changed
- `src/autotester/ui/project_view.py`: every /onboard input/select/textarea has `<label for>` (fixed fields) or `aria-label` (cloned repeater rows).
- `src/autotester/ui/auth_view.py`: auth pages carry `<link rel='icon' href='data:,'>`, so no `/favicon.ico` request. AU16 lists no favicon, so the public set is NOT widened.
- `tests/test_ui_onboard_a11y.py`: no unlabelled controls on /onboard; auth pages have the inline icon and anonymous /favicon.ico stays 401.
- `qa/feedback-inbox.md`: AU16 favicon question for the checker.

## Verify
pytest tests/test_ui_onboard_a11y.py tests/test_ui_auth_escalation.py tests/test_ui_auth_policy_table.py tests/test_ui.py (37 passed before a line-wrap-only edit); ruff clean; doctor clean.
