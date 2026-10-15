# Manifest - never-click-destroy-2

**Status:** checked-PASS
**Fix cycle:** 1
**Unit:** follow-up to never-click-destroy (D-098): checker-found controls still clicked
**Branch:** wave/never-click-destroy-2

## Changes
- stages/account_destroy.py (new): the ONE list + matcher moved here from schema/crawl.py/explore_safety (names re-exported). Adds: (1) bare Deactivate/Terminate/Delete user/Delete profile blocked when page URL/heading is account/profile/settings; (2) camelCase split and joined forms (`DeleteAccount`, `closeaccount`); (3) href path rules (`/account/delete`, `/account/close`, `/profile/delete`, `/deactivate`); (4) `DestroyContext` (30 s TTL): after a destroy-like request, Confirm/Yes/Yes, delete/OK are refused.
- explore_safety.deny_reason gains `page=` and `destroy_ctx=`; crawl (explore_node), actuator (ActionGuard), case guard (_Walk ctx; NAVIGATE to a destroy href refused) and BrowserSession (href/heading/ctx via browser/destroy_guard.py) all pass them.
- (5) press_key with no locator and Enter/Space judges the focused element.
- Still allowed: Delete draft, Remove from cart, Close dialog, Cancel subscription.
- tests/test_never_click_destroy_2.py; tests/test_explore.py allow_writes test updated (Delete account no longer clicked).

## Verify
uv run pytest tests/test_never_click_destroy.py tests/test_never_click_destroy_2.py tests/test_explore.py tests/test_explore_safety.py tests/test_explore_blocked.py tests/test_browser_use_guard.py tests/test_agent_tools.py ; uv run ruff check src tests scripts ; uv run autotester doctor

## Notes
Actuator knows page only from action.url; bare verbs there need an account URL. Full suite not run.
