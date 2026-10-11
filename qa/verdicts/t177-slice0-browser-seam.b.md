# Verdict - t177-slice0-browser-seam, seat B (blind dual check)
Cycle checked: 0
Head: 3495ee61fa5604beebc01e4354ec8f3e3d935425 (code d2d463a9), base master 808cdf7f. Policy-Version: proportional-verification/2026-10-10.9. Date 2026-10-11.
Trees: `D:/autoTesting/.worktrees/check-t177s0-b` (head, detached, left in place) and `D:/autoTesting/.worktrees/check-t177s0-b-master` (808cdf7f, differential only, left in place). `autotester.__file__` proven in-tree for every run; pytest/ruff/doctor via `uv --directory <tree> run` (evidence: unit-and-live-tests.txt). Blind to seat A. No `.env` value read.

VERDICT: CONTINUE-NEEDED
SCOREBOARD: B5, B6, B9, AF3 met on everything that could be run; 3 mandatory checks not completed (listed below)
TIER: L (dual-trigger: security src/autotester/browser/launch.py:142); coordinator B
FAILURES: none found

## Criteria (own runs, real browsers, headless AND headed, local pages only)
- B5 (default session opens no DevTools): met. Headless and headed, expose off: no listener, no `DevToolsActivePort`, `cdp_url` None, no remote-debugging flag on the browser root process. Falsified (below).
- B6 (hostile URL schemes through the real `goto`): met. 19 hostile URLs (leading space/C0/nbsp, tab/newline inside the scheme, mixed case, `javascript:`, `data:`, `file:`, `view-source:`, `ftp`, `ws`, `blob`, `about`, `chrome:`) are refused before any navigation (server_hits+0, page unchanged, `__pwned` unset); 4 legitimate http(s) URLs still navigate. On master 808cdf7f the same `javascript://allowed-host/%0a...` forms EXECUTE in the page (pwned=1) and `data://allowed-host` navigates, so the change closes a real hole. Falsified.
- B9 (opt-in endpoint is loopback-only, belongs to this browser, closes at teardown): met for headless and headed bind (table in SUMMARY.txt: only 127.0.0.1 accepts; 127.0.0.2, LAN 192.168.1.4 and ::1 refused; ws path matches the port file; listener owner in the browser's own process tree), stale file not adopted (headless and headed), two concurrent sessions each get their own endpoint (headless in-process; headless and headed as separate simultaneous processes), forced wrong-identity and forced past-loopback refusals tear down cleanly (headless: `CdpEndpointError`, `cdp_url` None, port closed, file gone, no process left), normal teardown closes the port and removes the file (headless, headed). Falsified.
- AF3 (destination check refuses a non-http(s) scheme): met by the same B6 matrix (the refusal is the `bad_scheme` branch of `check_destination`). Falsified.
- Refactor regression vs master (settle, recorded case, video, first-tab mask): headless head and master identical (late text found, video finalised and frame-extractable, no secret in video bytes, tab1 mask on). The second-tab mask gap (tab2 list-style `none`) is present on BOTH, i.e. not introduced here. Headed regression NOT completed (see below).
- Own gates: 83 passed (test_browser_session_cdp.py, test_browser_session_cdp_live.py, test_browser_navigation_secrets.py, in-tree), `ruff check src tests scripts` clean, `autotester doctor` clean. No full suite run.

## Falsifications (floor: 1 per changed criterion; each in a copy on C:, green before / red after / restored, copy deleted)
- B5: `if expose_cdp:` -> `if True:` at launch.py:141: 2 passed -> 2 failed -> 2 passed.
- B6: `bad_scheme` body -> `return None`: 15 passed -> 9 failed -> 15 passed.
- AF3: drop `bad or` in `check_destination`: 9 passed -> 9 failed -> 9 passed.
- B9: `close()` stops clearing `_cdp_url` and the port file: 1 passed -> 1 failed -> 1 passed.
The copy's `src` was diffed identical to the head `src` after restore. Output: falsifications.txt.

## CONTINUE-NEEDED: mandatory checks not completed
1. Killed-browser teardown (kill the browser process, then `close()`): not verifiable on this machine. `Stop-Process` on the browser's own PIDs leaves the root process listed and the listener open, and `session.close()` then blocks past 110 s inside Playwright (kill-scenario-headless.txt). Whether the head leaves the port closed, `cdp_url` None and the port file gone after a real kill is therefore UNVERIFIED here.
2. Headed refuse / forced-wildcard / start-raises-midway teardown scenarios: not run. Headed `close()` hangs in this environment, so each scenario stalls at teardown. The same hang reproduces on master 808cdf7f with expose off and no video (headed-close-hang-probe.txt: head off/off, head off/video, head expose, master off/off all hit the 70 s timeout), so it is not attributable to this change. The headless equivalents passed.
3. Headed regression (late-text settle, recorded case, video, first-tab mask, second-tab gap on both): not run; it ends at the same headed `close()` hang.
Estimate to finish: about 15 min on a machine whose headed close returns and where a killed browser process actually dies. Alternative for the maker: accept 1-3 as environment-blocked under a HUMAN_GATE.

## Notes
- N1 (headed close hang): `BrowserSession.close()` with a HEADED Chromium 151 did not return on this Windows box for head AND master, with or without video or expose. Environmental and pre-existing.
- N2 (wildcard bind): rewriting the launch arg to `--remote-debugging-address=0.0.0.0` did not widen the bind on this Chromium 151 build (still 127.0.0.1 only; 127.0.0.2 and LAN refused), so the `_reaches_past_loopback` guard was exercised by forcing it true, not by a real wildcard listener.
- N3 (same-user race): a hostile local process that rewrites `DevToolsActivePort` continuously during start AND serves a matching `/json/version` on loopback was adopted (`adopted_fake: True`, fake_hits 1, headless and headed). The stale-file case (file planted before start) is correctly refused. The identity check proves that something on loopback answers as the file says, not that it is our child. It needs same-user write access to the profile directory, which already grants control of the browser, so it is low.

PROPOSED-ISSUE: {"severity":"low","feature":"browser-cdp","title":"cdp identity check can be satisfied by a same-user process that keeps rewriting DevToolsActivePort","evidence":"qa/evidence/t177-slice0-browser-seam-B/scenarios-headless.txt and scenarios-headed.txt REPLANT line: adopted_fake True, fake_hits 1. Consider also requiring the listener owner PID to be in the launched browser process tree","criterion":"B9"}
PROPOSED-ISSUE: {"severity":"low","feature":"browser-session","title":"BrowserSession.close() does not return for a headed Chromium on this machine, on master too","evidence":"qa/evidence/t177-slice0-browser-seam-B/headed-close-hang-probe.txt; blocks any headed regression run; consider a bounded close with a process-tree kill fallback","criterion":"process"}
PROPOSED-ISSUE: {"severity":"low","feature":"browser-session","title":"owed gap still open: a second tab opened during a recorded case has no secret mask","evidence":"tab2 list-style none on head and master (regression-head-vs-master.txt); test_owed_gap_a_second_tab_opened_during_a_recorded_case_has_no_mask records it","criterion":"secret masking"}
PROPOSED-ISSUE: {"severity":"low","feature":"process","title":"environment limits: D: at 100% (457 MB free) and a zombie browser process after Stop-Process","evidence":"check wall time far over the L deadline; chrome-headless-shell PID 46248 stays listed after Stop-Process twice","criterion":"process"}

CAPABILITY-COVERAGE: B5, B6, AF3, B9 reproduced with real browsers headless and headed (bind, stale, concurrency) plus the hostile-URL matrix and master differential; killed-browser and headed refuse/regression not covered
LIVE-BROWSER: headless and headed Chromium 151 on local pages, bind table and scenarios done; headed close hangs (note N1)
ISSUES-WRITTEN: none (dual-check coordinator; PROPOSED-ISSUE lines only). No merge, no push, no manifest flip.
Metrics: start=2026-10-11T08:20Z end=2026-10-11T14:05Z wall_min=345 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=20700 mutants=0 defects_unit=0 defects_6c=0 slow: headed browser scenarios and close hangs ~150 min, in-tree pytest 4.3 min, rate-limit pause
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Everything that can be run here passes with real browsers, and four named falsifications turn red when the code is broken. Three mandatory scenarios (a killed browser, headed refusal teardown and headed regression) could not finish because headed close and process kill do not behave on this machine, so the verdict is CONTINUE-NEEDED rather than PASS.
