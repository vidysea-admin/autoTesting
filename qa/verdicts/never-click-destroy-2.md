# Verdict - never-click-destroy-2

**Cycle checked:** 1
**Verdict:** PASS
**Commit checked:** c858beb0

- 238 scoped tests pass (every file referencing deny_reason/destroy plus related guards); ruff clean; doctor clean; merge-tree vs master clean.
- One concept one place: ACCOUNT_DESTROY_PATTERNS now defined only in stages/account_destroy.py; removed from schema/crawl.py.
- test_explore.py: only the deliberate flip (button.del not clicked under ALLOW_WRITES).
- Round-1 bypasses now blocked: bare Deactivate/Terminate/Delete user (on account/profile/settings pages), DeleteAccount/deleteAccount, href routes (/account/delete, /delete-account, case and absolute URL), Confirm/Yes/Yes, delete after a destroy request (30s context), page-level Enter/Space via focused element.
- No over-blocking: Delete draft, Remove item from cart, Close dialog, Cancel subscription (+renewal reminder), Close account settings, Delete profile photo, Delete message, Terminate session all allowed.
- Advisory: bare "Deactivate" is blocked on any page whose URL/heading contains settings/preferences/privacy (e.g. notifications settings): mild over-block, accepted. Confirm context is time-based (30s), not page-scoped.
