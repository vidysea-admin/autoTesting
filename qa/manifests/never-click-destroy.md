# Manifest - never-click-destroy

**Status:** ready-for-check
**Fix cycle:** 1
**Unit:** Umesh 2026-10-15 "Block destroy buttons" (D-098; ISS-t179b-hg1-2)
**Branch:** wave/never-click-destroy
**Contract:** none edited; core invariant: write policy never narrows below account rights except named never-click controls.

## Changes
- schema/crawl.py: `ACCOUNT_DESTROY_PATTERNS`, the ONE list (next to the logout never-click list).
- stages/explore_safety.py: `destroys_account()` (the one matcher) and `ACCOUNT_DESTROY_REFUSED` = "not exercised: account-destroying (policy)"; `deny_reason` checks it first, at every policy. Covers crawl (explore_node), agents/guards (`_click_denied`, all policies, closes ISS-t179b-hg1-2) and the browser-use actuator (`ActionGuard.refusal`).
- browser/destroy_guard.py (new mixin) + session.py: `BrowserSession.click` and `press_key(locator)` refuse by locator, innerText, aria-label, title, value; raises `AccountDestroyRefused`.
- stages/crawl_coverage.py: unreached destroy controls are reported with the same reason.
- tests/test_never_click_destroy.py; tests/test_explore_safety.py and test_explore_blocked.py fixtures changed (Delete account now never-click).
- docs/DECISIONS.md D-098; MAP/SNAPSHOT regenerated.

## Verify
uv run pytest tests/test_never_click_destroy.py tests/test_explore_safety.py tests/test_explore_blocked.py tests/test_browser_use_guard.py tests/test_agent_tools.py ; uv run ruff check src tests scripts ; uv run autotester doctor

## Notes
Case-execution reporting: a guarded case is refused pre-run with the reason; the session backstop surfaces as ERRORED with the same text. Full suite not run.
