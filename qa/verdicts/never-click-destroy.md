# Verdict - never-click-destroy

**Cycle checked:** 1
**Verdict:** PASS (with non-blocking residual gaps)
**Commit checked:** 9f942ed4

## Verified
- Scoped tests: 172 passed (never_click_destroy, explore_safety, explore_blocked, browser_use_guard, agent_tools). Ruff clean. Doctor clean. merge-tree vs master: clean (no conflicts).
- Fixtures (c): test_explore_safety flips only (ALLOW_WRITES, delete) to True; test_explore_blocked renames "Delete account" to "Delete invoice" so the depth-refusal test keeps its meaning. No other assertion weakened.
- D-098 (d): well formed, cites only D-053 and ISS-t179b-hg1-2; no fake ids.
- Paths: crawl/deny_reason, agents/guards, browser-use actuator (via deny_reason), crawl_coverage, BrowserSession.click and press_key(locator) all route through the one matcher.

## Matcher probes (blocked = True)
Blocked: Close My Account, DELETE ACCOUNT, Deactivate account/profile, Remove my profile permanently, Delete Account?, NBSP "Delete account", "delete-account", Yes delete my account, Delete my data, Erase all data, Close your account.
Allowed (correct): Delete draft, Remove item from cart, Close dialog, Cancel subscription renewal reminder, Close account settings, Delete profile photo.

## Residual bypasses (still click; non-blocking, recommend follow-up)
1. Bare "Deactivate", "Terminate", "Delete user" (no account noun).
2. CamelCase/joined "DeleteAccount" as visible text.
3. href-only: link `/account/delete` with a neutral label; the guard reads locator, text, aria-label, title, value, never href or page URL.
4. Context-free confirm: "Confirm" on a delete-account page and "Yes, delete" are not blocked; the guard has no memory of the preceding destroy request/URL.
5. Keyboard Enter via press_key with no locator (page-level) is not guarded; Enter on a locator is.
6. Cancel subscription / Cancel my membership: not blocked. Judged not account-destroying (billing, usually reversible; account survives), so correct under the stated scope; "cancel account" is blocked.
Also, `uv run` in the worktree builds a fresh venv and gave 12 spurious failures; use the main .venv.
