# Manifest — deeplink-unauth-session

**Unit:** Logged-out-precondition cases run in a fresh isolated profile; click actuator survives collapsed submenus.
**Contract:** `qa/contracts/core-invariants.md` C1, C2, C7 · `qa/contracts/ui-run.md` RU-entry rules (unchanged)
**Goal task:** none (defects from the real PathLynks run, `qa/evidence/t169-real/inconclusive-analysis.md`)
**Date:** 2026-10-13
**Fix cycle:** 2
**Status:** ready-for-check
**Dual check:** no

## Changes
1. `stages/entry_precondition.py` (new) `requires_unauthenticated(case)`: `CaseClass.DEEPLINK_UNAUTH`, or a
   precondition saying logged-out / unauthenticated / no session. `stages/run_launcher.py::is_entry_case`
   now ORs it in, so these cases take the existing `_run_entry_case` path: a wiped `<slug>-entry-test` profile
   (no cookies/storage, never the signed-in profile), same BrowserSession so secret masking, redaction and
   video recording are unchanged. Fixes the false FAIL of case_aafae754b289.
2. `browser/click_recovery.py` (new) + `BrowserSession.click`: trial-click probe (2.5 s) first; if blocked,
   scroll into view, then expand the parent menu once (aria-expanded=false toggle, else the element covering
   the target, else the nearest preceding button), re-probe. Never force-clicks; each recovery step is recorded
   as DOM evidence; a still-blocked target fails with Playwright's own error.

## Root cause (submenu)
Crawl-derived steps click a link inside a collapsed `menu-dropdown`; the parent `<button class="menu-item">`
intercepted pointer events for the whole 30 s default timeout (4 cases, 122 s of the 600 s budget). Nothing
expanded the parent first.

## Evidence
`tests/test_unauth_entry_case.py`, `tests/test_click_recovery.py` (fakes), `tests/test_unauth_menu_live.py`
(local fixture `tests/fixtures/guard_menu_site`, run once headed: unauth deeplink lands on login after a
signed-in session existed; collapsed and covered menus expand and click).
