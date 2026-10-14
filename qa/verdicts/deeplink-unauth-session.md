# Verdict - deeplink-unauth-session

**Cycle checked:** 1
**Verdict:** FAIL (one mechanical defect; the behaviour is sound)
**Head checked:** 72457705

## Scope: the branch fixes BOTH
- Unauth session: `stages/entry_precondition.py::requires_unauthenticated` is OR-ed into `run_launcher.py::is_entry_case` (~108-114). Such cases take the existing `_run_entry_case` path (`ui/run_execution.py:77`), which wipes `<slug>-entry-test` fail-closed (RU5) and uses the same BrowserSession. No cookies from the signed-in profile.
- Sidebar expand: `browser/click_recovery.py::ready_to_click`, called from `BrowserSession.click` (`session.py:~202`). It trial-click probes, scrolls, expands the parent once (aria-expanded=false, else the covering element, else the preceding button), then re-probes. It never force-clicks and has no retry loop. Each step is recorded as DOM evidence.

## Checks
- Secrets/redaction: unchanged. Same BrowserSession, same SecretStore, same Redactor.scrub on the error path.
- Tests: 13 passed (`test_click_recovery`, `test_unauth_entry_case`). The live-browser test `test_unauth_menu_live` was not run (no-browser rule), so it is unverified by this check.
- ruff: clean.
- `git merge-tree HEAD master`: clean, no conflicts.
- File sizes: `run_launcher.py` is exactly 300 lines (at the limit).

## Defects
1. BLOCKING: `autotester doctor` reports 1 violation, `stale-generated: docs/MAP.md`. The new modules `browser/click_recovery.py` and `stages/entry_precondition.py` need `autotester map` run and docs/MAP.md committed.
2. Minor, non-blocking: recovery probes are 2.5 s each (`click_recovery.py:~PROBE_MS`, up to about 5 of them, roughly 12 s). They are not deducted from `BrowserSession._timeout()` (`session.py:171`), so the worst case is that overhead plus the step's own timeout. Bounded, but not strictly "bounded by the step timeout".
3. Minor: the `requires_unauthenticated` regex is heuristic. A precondition such as "no session" matches, so a false positive only costs a slower isolated run.

## Handback
Maker: run `autotester map`, commit docs/MAP.md, set `Fix cycle: 2`, status ready-for-check. Optionally tie the probe time to the budget.
