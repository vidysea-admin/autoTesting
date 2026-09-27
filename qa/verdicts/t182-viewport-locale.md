# Verdict — t182-viewport-locale

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent (Mode A + real Chromium) + orchestrator capability re-run

```
VERDICT: PASS
SCOREBOARD: E6 met: a VIEWPORT_MOBILE case runs at 390x844 and is reset to 1366x850 afterwards; a LOCALE_I18N case is recorded as NOT_RUN with a reason, runs no step, and grades INCONCLUSIVE without reaching the judge; every executor path (serial, parallel, agent_loop, explore) goes through run_case's single enact/reset seam
FAILURES: none
CAPABILITY-COVERAGE: 4/4 rows reproduced on the named tests. Subagent (copy c182-1): A (enact → None) and C (grade NOT_RUN branch removed → judge reached). Orchestrator (copy c182-rows, baseline 8 passed): B (LOCALE branch returns None → the 3 locale tests red); D (finally reset → pass → test_viewport_resets_to_default_after_the_case_for_a_reused_session red only). Restored 8 passed, byte-identical.
LIVE-BROWSER: qa/evidence/browser-t182-viewport-locale-2026-09-26-checker (the project's real launch path, visible Chromium, localhost fixture, one session: mobile navigate and click screenshots 390x844, and the page itself reported innerWidth "390x844" during the steps (assert visible_text met); the following HAPPY case 1366x850; LOCALE_I18N NOT_RUN → INCONCLUSIVE with judge prompts = 0)
ISSUES-WRITTEN: AT-600 (low: enums.py docstring edit dropped two clauses, not a pure reflow), AT-601 (low: no isMobile/touch/DPR emulation)
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: Flag 2 ruling: E6 says "a mobile-sized viewport" and names size only, so set_viewport_size enacts it; true device emulation needs a new context per case and is filed as AT-601. On the parallel route, every case gets its own default-sized session and run_case resizes it (fake-page proof: mobile page [390x844, 1366x850], happy page untouched). NOT_RUN folds into the unchanged Result.INCONCLUSIVE, no Outcome-keyed exhaustive map exists, and old RawResult JSON loads. 4c: of the 3 reflowed enums.py docstrings, OVERLAY is a pure reflow, but ASSERTION_FAILED lost "the grader still owns the verdict" and EVIDENCE lost "for third-party noise". The meaning is essentially kept ("never a grade"), so this is filed low, to be restored when enums.py (at the 300-line cap) is split.
```

Evidence: test_viewport_locale_enact.py 8 passed; 8 execute/grade/parallel files 50 passed · ruff clean · doctor clean · `git diff 7913387..b7506f0 --stat` = the 8 manifest files (+325/-31) · run_case 37, _run_steps 35 lines.
