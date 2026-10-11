# Verdict - t177-slice0-browser-seam - coordinator B - repair check, fix cycle 1

Bound to D:/autoTesting. Checked head 0a4859a1 (code f8fdbd33), Repair base 3495ee61 (ancestor of head, verified with git). Cycle checked: 1
Policy-Version: proportional-verification/2026-10-10.9. Blind dual check: I read no earlier verdict, checkpoint or evidence of this unit and nothing from coordinator A.
Work copies: `git archive` of 0a4859a1 and 3495ee61 on C: (session scratchpad, `r1b-head`, `r1b-base`) with a venv there; `autotester.__file__` confirmed inside the copy. Nothing created on D: except this verdict, the checkpoint and `qa/evidence/t177-slice0-browser-seam-r1-B/` (88 KB).

## Check plan
Failed list F1a, F1b, F2 -> real headless Chromium through `BrowserSession(expose_cdp=True)` with a hostile loopback listener and a forced failure between launch and publish, differential against the repair base; happy path off/on; `_reaches_past_loopback` measured; one headed attempt; repair diff read in full (4 files); whole-unit diff scan; ruff, doctor, affected tests (no full suite, no suite lock); one falsification per repaired item in copies.

## Result
VERDICT: PASS
SCOREBOARD: F1a, F1b, F2 repaired and evidenced; B5/B6/B9/AF3 as the manifest cites them: met (118 affected tests green)
TIER: L (security: loopback DevTools endpoint on a credentialed browser, `launch.py:142`); dual-trigger as in the manifest
FAILURES: none
CAPABILITY-COVERAGE: 4/4 falsifications reproduced (table below)
LIVE-BROWSER: qa/evidence/t177-slice0-browser-seam-r1-B/ (real headless Chromium 151 and one headed run, local 127.0.0.1 pages only; no browser MCP used)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines below)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## 1. F1 forced for real (`h1.py`, `out-head-item1.jsonl`, `out-base-item1b.jsonl`)
Method: real Chromium launched by `start()` with expose on; `launch._published` patched to return the REAL path but a hostile listener's port, so the identity probe talks to my listener while the real browser runs. A positive control counts the browser pids with the profile dir in their command line while it is alive (1 each time). After each: pids by profile dir, real DevTools port, port file, `cdp_url`, then a second `start()` on a fresh session with the same profile dir.

| Case | head 0a4859a1: start() raised | procs alive after | real port accepts | port file | cdp_url | 2nd start |
|---|---|---|---|---|---|---|
| non-HTTP bytes | CdpEndpointError "not this browser" | 0 | no | gone | None | ok |
| `[]` | CdpEndpointError | 0 | no | gone | None | ok |
| `"x"` | CdpEndpointError | 0 | no | gone | None | ok |
| `null` | CdpEndpointError | 0 | no | gone | None | ok |
| JSON of a different browser (other guid) | CdpEndpointError | 0 | no | gone | None | ok |
| 302 redirect / truncated body | CdpEndpointError | 0 | no | gone | None | ok |
| `RunBudgetExceeded` between launch and publish | RunBudgetExceeded (original error not masked) | 0 | n/a | gone | None | ok |
| `KeyboardInterrupt` between launch and publish | KeyboardInterrupt | 0 | n/a | gone | None | ok |
| 200000 x `[` (deep nesting) | **RecursionError** (not CdpEndpointError) | 0 | no | gone | None | ok |

Same cases on the repair base 3495ee61 (each in its own process): non-HTTP -> BadStatusLine, `[]`/`"x"`/`null` -> AttributeError, RunBudgetExceeded, KeyboardInterrupt: in all six the chrome-headless-shell stayed alive, the real port still accepted and the port file remained (I killed those pids myself, by pid, afterwards). So F1a and F1b are real on the base and gone at head. (`out-base-item1.jsonl` is a first base run whose later cases were confounded by the leaked in-process driver; `out-base-item1b.jsonl` is the clean one.)
Drip case (`h1b.py`): a loopback listener that sends headers then one byte per second keeps `start()` inside the probe for as long as it drips (26.9 s here, bounded only by my 25 s script); the exposed browser and port are open meanwhile; after it stops: CdpEndpointError, 0 procs, file gone. See P2.

## 2. Happy path, head vs base (`h2.py`, `out-item2.jsonl`)
Identical at head and base. Expose off: 1 browser pid, no listening socket in its tree, no port file, `cdp_url` None. Expose on: one listening socket, `127.0.0.1:<port>` only; connect 127.0.0.1 yes, 127.0.0.2 no, LAN 192.168.1.4 no, ::1 no; `/json/version` websocket path equals line 2 of the port file; the DevTools page list shows the local page served on 127.0.0.1; after `close()`: port refuses, file removed, 0 procs, `cdp_url` None.

## 3. `_reaches_past_loopback` measured (`h3.py`, `h3b.py`, `out-item3a.json`, `out-item3b.json`)
Windows 11, this host. Closed port: connect to 127.0.0.1, 127.0.0.2 and the LAN address each gives `TimeoutError` at 1.0 s; with a 6 s timeout each gives `ConnectionRefusedError` (10061) at 2.0-2.06 s. A loopback-only listener probed from 127.0.0.2 and from the LAN address: `TimeoutError` at 1.0 s (so every legitimate start pays 1 s and the function returns False, as the builder said). Wildcard `0.0.0.0` listener, idle: connects to 127.0.0.2 in 0.0 s, function True. Wildcard listener under load: 100 calls idle and 100 calls with 60 CPU burners on 20 cores: 0 False, max 0.53 s. Wildcard listener with a FULL accept queue (backlog 1, one parked client): connects to 127.0.0.1 and to 127.0.0.2 both time out at 1.0 s and the function returns **False**, i.e. a wildcard bind does pass that layer on a timeout.
Judgement: the builder's choice is forced at a 1 s timeout (refusal and silence are indistinguishable below 2 s on Windows), and the pass-on-timeout case needs a wildcard listener whose accept queue is full at that instant, while the identity probe through 127.0.0.1 (layer one, same listener, run first with its own 2 s timeout) must have answered correctly just before; a wildcard-bound endpoint was not produced by Chromium here (headless and headed both bound loopback only, item 4). Not a criterion breach as written; recorded as P3 with a measured fix (timeout above 2.1 s makes TimeoutError a real doubt).

## 4. Headed (`h4.py`, `out-item4.txt`), one attempt
Headed session, expose on: started in 8.3 s, 7 chrome processes, `cdp_url` on 127.0.0.1; 127.0.0.2 and LAN refuse (headed honours loopback as well). `close()` returned after 13.1 s (120 s watchdog never needed): 0 procs, port file gone, port refused. The earlier "headed close never returns" was NOT reproduced; headed refuse paths were not exercised (one attempt only).

## Repair diff and scope
Repair diff 3495ee61..0a4859a1 read in full: launch.py (+`errno`, `http.client`; `_answers_as` dict guard; `_reaches_past_loopback` fail-closed except), session.py (`try/except BaseException` -> `_close_quietly`, `contextlib`), the test file (+3 tests), manifest. Whole-unit diff 808cdf7f..0a4859a1: 10 files, all listed in the manifest's What changed; removed defs are only the three moved ones (`settle` body, `_poll_for_expected`, `_sweep_orphan_videos`), which now exist in assertions.py/video.py. `docs/MAP.md` is listed as regenerated but is not in the diff (wording, low). Lines: session.py 281, test_browser_session_cdp.py 299, launch.py 159.
Checks: `ruff check src tests scripts` all passed; `autotester doctor` clean; `pytest` test_browser_session_cdp, _cdp_live, _settle, test_browser, test_browser_navigation_secrets (copy, `-p no:xdist -o addopts=`): 118 passed in 60 s (same count as the builder's batch).

## Falsification (copies of src/tests/scripts on C:, green in pristine copy, red after edit; `fal/`)
| Item | Edit in the copy | Green (pristine) | Red node and assertion |
|---|---|---|---|
| F1a bytes | drop `http.client.HTTPException` from the except | 4 passed | `..._tears_down[garbage, not http]` raises BadStatusLine |
| F1a shape | drop `isinstance(body, dict)` guard | 4 passed | 3 red: `[]`, `"x"`, `null` (AttributeError) |
| F1b | `except BaseException` -> `except ZeroDivisionError` | 1 passed | `test_a_failure_after_launch_closes_the_exposed_browser` asserts the port closed: `refuses_connections(...)` False |
| F2 | fail-closed branch -> `return False` | 5 passed | `test_reaching_past_loopback_fails_closed...[ENETUNREACH]`, `[PermissionError]` red |

## Known, not repaired: ruling on each (none blocks; the contract names no DevTools endpoint, B5/B6/B9/AF3 hold as written)
a. Same-user process that rewrites the port file and serves a matching `/json/version` is adopted: PROPOSED-ISSUE P4 (low). Such a process can already read the real port file and drive the browser; adoption only adds a man-in-the-middle for the later attach. Owner confirm at merge covers the posture.
b. Headed `close()` hang: not reproduced (13 s). PROPOSED-ISSUE P5 (low): `close()` has no bounded wait; slow on headed.
c. Second-tab mask gap: pre-existing on master, recorded by a passing test, no caller sets expose yet: PROPOSED-ISSUE P6 (tracked, owed by next slice).
d. P2 residual: see item 3: PROPOSED-ISSUE P3.

PROPOSED-ISSUE: {"severity":"medium","feature":"t177-slice0-browser-seam","title":"P1 verified_cdp_url: a hostile loopback reply that is valid-looking JSON nested ~200000 deep raises RecursionError, not CdpEndpointError","evidence":"qa/evidence/t177-slice0-browser-seam-r1-B/h1.py case deep_nest: start() raised RecursionError; browser closed, port refused, file gone (the outer BaseException net holds). launch.py:72-75 catches (OSError, ValueError, HTTPException) only. The manifest sentence 'any endpoint doubt ... raises CdpEndpointError' is over-quantified (wording, not a FAIL)","fix":"catch RecursionError (or Exception) in _answers_as and cap the body read"}
PROPOSED-ISSUE: {"severity":"medium","feature":"t177-slice0-browser-seam","title":"P2 identity probe has no total deadline: a trickling listener holds start() with the exposed browser open","evidence":"h1b.py: 1 byte/s listener kept start() inside _answers_as for 26.9 s (2 s is per read); real port open and browser alive meanwhile; cleanup correct afterwards. launch.py:71 opener.open(timeout=2) + json.load","fix":"read at most N bytes under one monotonic deadline"}
PROPOSED-ISSUE: {"severity":"low","feature":"t177-slice0-browser-seam","title":"P3 _reaches_past_loopback passes a wildcard bind when its probe times out (full accept queue)","evidence":"h3.py: wildcard listener with backlog full -> function returns False; closed ports refuse at 2.0-2.06 s on this host so a timeout above ~2.1 s would separate silence from refusal (cost 1 s more per start). launch.py:88-93","fix":"timeout 3 s and treat TimeoutError as doubt, or read the listening address from the OS table"}
PROPOSED-ISSUE: {"severity":"low","feature":"t177-slice0-browser-seam","title":"P4 a same-user listener matching the port file is adopted as the browser's endpoint","evidence":"manifest Known a; not exercised; no pid-in-process-tree check in launch.py","fix":"verify the listener pid is in the launched browser's process tree"}
PROPOSED-ISSUE: {"severity":"low","feature":"t177-slice0-browser-seam","title":"P5 BrowserSession.close() has no bounded wait; headed close took 13 s","evidence":"h4.py out-item4.txt close_begin 15.4 -> close_returned 28.5; session.py:132-142","fix":"bounded close with a pid-scoped fallback"}
PROPOSED-ISSUE: {"severity":"low","feature":"t177-slice0-browser-seam","title":"P6 second tab opened during a recorded case is recorded without the secret mask","evidence":"test_owed_gap_a_second_tab_opened_during_a_recorded_case_has_no_mask passes today; also on master","fix":"mask at context level in the slice that wires expose_cdp"}

## Explanation
Both F1 paths and the F2 fail-open on unexpected errors are repaired and reproduced as fixed on real Chromium: every hostile reply and both forced failures end with the exception raised, no browser process, a closed port, no port file and a working second start; the repair base shows the leak for the same inputs. Happy path is unchanged against the base and loopback-only on 127.0.0.2, LAN and ::1. Two residuals worth fixing next (P1 error type, P2 unbounded probe time) leave nothing running after `start()` returns or raises, so they do not breach the cycle-0 failure.
Metrics: start=2026-10-11T18:43:36Z end=2026-10-11T19:40:00Z wall_min=56 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=100 mutations=4 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=3384 mutants=0 defects_unit=0 defects_6c=0
slow: real-browser matrix and the interrupted session 56 min (L budget 45 min wall includes a session interruption and resume; the 2 x 100 calls of the measured function were a load probe the brief asked for, not a flaky claim)
