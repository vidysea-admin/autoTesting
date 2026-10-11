# Verdict - t177-slice0-browser-seam, repair checker A (fix cycle 1)

Cycle checked: 1
Policy-Version: proportional-verification/2026-10-10.9
Dual check: coordinator A (blind; only its own failed list and checkpoint read). Bound to D:/autoTesting.
Checked head 0a4859a1 (code f8fdbd33), Repair base 3495ee61 (verified an ancestor of HEAD), merge-base with master 808cdf7f. Copy: git archive on C:, venv on C:, autotester.__file__ and pytest rootdir inside the copy.

## Plan
Tier L (dual-trigger security, launch.py:142). Re-run F1 (a, b) and F2; B5 and B9 (launch.py and session.py are touched); affected tests; repair diff in full; whole-unit scope scan; one falsification per repaired item; hostile loopback listener probes; live headless Chromium probes. Full suite owed only if everything is met: NOT run (F1a not met). Evidence: qa/evidence/t177-slice0-browser-seam-r1-A/results.md and the probe scripts beside it.

VERDICT: FAIL
SCOREBOARD: F1b met, F2 met as a hardening (partial by design), F1a not met; B5 met, B9 met as written
TIER: L (security: optional loopback DevTools endpoint on a credential-holding browser, launch.py:142)
FAILURES:
- [F1a] sev: medium · the claim "any DevTools endpoint doubt closes the context and raises CdpEndpointError" is still false for a listener on the file's port that is not this browser. A never-ending body HANGS start(): `launch.py:71-72` `json.load(reply)` reads to EOF with no size or total-time bound (the 2 s timeout is per recv). Reproduced: `hostile2.py` drip (1 byte / 0.5 s) gives no exception after 20 s; `livedrip.py` with a real headless Chromium: after 10 s start() had not returned and the REAL browser was running with its DevTools port open (57991, accepting, 4 chromium processes) until the hostile listener closed. A deeply nested JSON body escapes as RecursionError, not CdpEndpointError (`launch.py:73` catches OSError, ValueError, HTTPException only); the browser is closed in that case by the new BaseException handler, so only the exception type is wrong. A 300 MB body is buffered whole (peak 604 MB) before refusal. · fix direction: bounded read (`reply.read(65536)` plus an overall deadline), catch RecursionError, an opener without redirect handling · issue: P1
CAPABILITY-COVERAGE: 5/5 repaired-item falsifications reproduced (copy green, red on the named test, restored green): F1a x2, F1b, _close_quietly, F2.
LIVE-BROWSER: qa/evidence/t177-slice0-browser-seam-r1-A/results.md (headless only, own scripts live.py and livedrip.py; no UI surface changed)
ISSUES-WRITTEN: none (dual coordinator)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Per-item results
- F1a: non-HTTP bytes (BadStatusLine), [] / "x" / null / 7, bad UTF-8, huge int, HTTP 500, reset, truncated, empty, accept-and-never-reply (2.0 s), redirect loop and redirect to file:// all give CdpEndpointError "not this browser". socket.timeout and UnicodeDecodeError and JSONDecodeError are subclasses of what is caught; ssl does not apply (http only). Not met: the RecursionError type, the drip hang, the unbounded body.
- F1b met. Real browser, failure after publish: RecursionError, KeyboardInterrupt and SystemExit(3) are each re-raised unchanged after cleanup; port closed, port file gone, cdp_url None, 0 chromium descendants. The same holds when `context.close()` itself raises: the original error is re-raised and `playwright.stop()` in close()'s finally still ends the browser. The object is safely re-closable (close() twice) and restartable (start() again works, then closes).
- F2 met as the builder wrote it (an unexpected OSError refuses; 2 falsification reds). It stays partial, see ruling 3.
- B5: a default session opens no DevTools (unit and live test: no port file, cdp_url None). Met. B9 as written in the contract ("closes only the contexts this session opened, own user_data_dir"): met; the contract text has no loopback clause.
- Affected tests: cdp_live + navigation_secrets + browser + settle + cdp = 118 passed in the clean copy. ruff clean, `autotester doctor` clean. session.py 281, test file 299, launch.py 159; no function over 50. No existing assertion weakened or deleted (0 removed test lines in the whole unit; the moved defs `settle`, `_poll_for_expected`, `_sweep_orphan_videos` live on in assertions.py and video.py with delegation).
- Diff scope: every whole-unit file is in "What changed" (docs/MAP.md is claimed regenerated but unchanged: wording only). Nothing removed that no criterion allows.
- Falsifications (copy, green / red / restored): drop HTTPException 23/1/23; drop isinstance 23/3/23; BaseException to ZeroDivisionError 23/1/23; plain close() 10/1/10; OSError branch to return False 23/2/23.

## Rulings asked for
1. Identity probe: not every exception class is treated as "not this browser". RecursionError escapes and a never-ending body hangs. Every other class you listed is.
2. `_close_quietly` cannot hide a failure that leaves the browser or port alive in anything I ran, including close() raising. Read only, not run: if `playwright.stop()` itself raised, close() would leave `_playwright` set and skip the video sweep (`session.py:139-143`), P3. After a failed start cdp_url is None, the port file is gone, and the object is re-closable and restartable. BaseException is re-raised after cleanup (KeyboardInterrupt and SystemExit shown live).
3. Timeout in `_reaches_past_loopback`: yes, a wildcard listener can hide behind a timeout. On this host a CLOSED port also times out (127.0.0.1 and 127.0.0.2), so a timeout is not a refusal; a 0.0.0.0 listener with a full backlog that never accepts gives reaches=False, and a real Chromium wildcard bind that is slow to accept under load could be missed the same way. B9 as written is still met (no loopback clause); loopback-only is this unit's own security claim and rests on Chromium's default bind (headed unverified) plus the identity check. Non-blocking: P2.
4. Known list: (a) PROPOSED-ISSUE (P5: the process already reads the same-user profile dir, passes identity, no criterion text). (b) PROPOSED-ISSUE (P6: also on master; B9 concerns which contexts are closed). (c) PROPOSED-ISSUE (P7: on master, the owed test records it). (d) PROPOSED-ISSUE (P2, ruling 3). None blocks. The F1a hang does block, because the claim is explicit ("any doubt") and it is the same input class as the original F1; a listener must be the one named in the port file, so reaching it needs the (a) precondition, and `expose_cdp` having no caller in src/ today is why I rate it medium. I judged the criterion text.

PROPOSED-ISSUE: {"id":"P1","severity":"medium","feature":"t177-slice0-browser-seam","title":"identity probe unbounded: never-ending body hangs start() with the browser open; RecursionError escapes","evidence":"launch.py:71-73; qa/evidence/t177-slice0-browser-seam-r1-A/hostile2.py and livedrip.py"}
PROPOSED-ISSUE: {"id":"P2","severity":"low","title":"_reaches_past_loopback: a timeout is not a refusal on Windows (a closed port times out); a full-backlog wildcard listener evades","evidence":"launch.py:88-93; loop.py"}
PROPOSED-ISSUE: {"id":"P3","severity":"low","title":"BrowserSession.close(): playwright.stop() raising leaves _playwright set and skips the video sweep (read only)","evidence":"session.py:139-143"}
PROPOSED-ISSUE: {"id":"P4","severity":"low","title":"identity probe follows redirects: any host is contacted and another loopback listener can satisfy identity","evidence":"hostile2.py redirect cases"}
PROPOSED-ISSUE: {"id":"P5","severity":"low","title":"known (a): a same-user process rewriting DevToolsActivePort with a consistent /json/version is adopted","evidence":"manifest known list"}
PROPOSED-ISSUE: {"id":"P6","severity":"low","title":"known (b): headed close() does not return on this machine (also master); the headed failure path is unverified","evidence":"manifest known list"}
PROPOSED-ISSUE: {"id":"P7","severity":"low","title":"known (c): the second-tab mask gap exists on master","evidence":"test_owed_gap_a_second_tab_opened_during_a_recorded_case_has_no_mask"}

No-progress note: the cycle-0 failure was an exception escaping with the browser running; this cycle's failure is a different input (a never-ending body) with a new evidenced reproduction, so it is progress, not a repeat.
Full suite: not run (the precondition "everything above met" fails); owed on the next PASS cycle; no lock was taken. Disk: D: 20 G free at the end.
Merge note (not mine to give): a merge additionally needs the owner's confirmation of the DevTools port and an ARCHITECTURE security line under a DECISIONS entry.

Metrics: start=2026-10-11T18:43:13Z end=2026-10-11T19:50:00Z wall_min=67 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=4000 mutants=0 defects_unit=1 defects_6c=0
slow: hostile and live probes plus the 5 falsification copies under host load, about 30 min
