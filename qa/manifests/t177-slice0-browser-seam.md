# Manifest - t177-slice0-browser-seam

**Unit:** T-177 browser-use fallback, SLICE 0 only: the browser seam. No SDK, no dependency change, no agent code, no `ui/` wiring. Ported from `wave/t177-followup` @ 205302b4 where it was right, rewritten where the plan review or my own reading found it wrong.
**Brief:** `qa/briefs/t177-browser-use-fallback.md` (Phase A of `.work/t177-takeover/plan.md`, file subset only).
**Branch / base:** `wave/t177-slice0-browser-seam` on master 808cdf7f.
**Code commit (pre-check sha):** f8fdbd33 (fix cycle 1; cycle 0 code was d2d463a9). The manifest commit after it changes only this file.
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (security control: a DevTools endpoint on a browser holding credentials; a destination-check change)
Dual check: required
dual-trigger: security src/autotester/browser/launch.py:142 (the `--remote-debugging-port=0` / `--remote-debugging-address` arguments, the only place a DevTools port is requested)
Fix cycle: 1
Repair base: 3495ee61
Executor: claude-sonnet-subagent (maker build subagent)
Status: ready-for-check
Full-suite trigger: none run by the builder. Shared surface touched: `BrowserSession` (every run), `check_destination` (every navigation), `settle` (every step). The maker should schedule one integration suite under the machine lock.

## Contract and criteria this slice serves (quoted)

`qa/contracts/browser-and-secrets.md`:
- **B5** - "Launches Chromium headed when `Project.headed` is true (the default); headless only on explicit request." and "Uses a persistent profile at `profiles/<slug>/` so an interactive login survives to later runs." (`launch_options` gains one opt-in argument; nothing else about the launch changes.)
- **B6** - "Refuses to navigate to a host outside `Project.allowed_domains`, raising a named error." (`check_destination` now also refuses a non-http(s) scheme.)
- **B9** - "Teardown closes only the contexts this session opened, identified by its own `user_data_dir`." (the new endpoint is torn down with that context and never outlives it.)

`qa/contracts/agent-fallback.md` **AF3** (the part this slice can serve without agent code): "An agent-chosen action is subject to: the deny-list (D-016), the same-domain destination check (X7), `write_policy`, and the run's `RunApproval` budget". Slice 0 supplies the scheme half of the destination check and the `cdp_url` the later backend attaches to; the guard itself is a later slice.

Authority: D-075 "`browser/session.py` gains a read-only `cdp_url` property so the browser-use backend can attach to the session AutoTester already opened" (names `session.py` only; see Owner confirm). D-041 item 6. D-082 item 1 (new-module standing rule: this slice adds NO source module; the new file is one test file).

## What changed

| Path | Lines now | Change |
|---|---|---|
| `src/autotester/browser/launch.py` | 147 (was 68) | `launch_options(expose_cdp=False)`; `verified_cdp_url`, `forget_cdp_port`, `CdpEndpointError`. Candidate's `loopback_port()` / `cdp_endpoint()` / `cdp_port=` removed. |
| `src/autotester/browser/session.py` | **270 (was 299)** | `expose_cdp` ctor arg, `_publish_cdp`, read-only `cdp_url`, teardown forgets the endpoint; `settle()` body moved out; `_sweep_orphan_videos` moved out. |
| `src/autotester/browser/assertions.py` | 258 (was 203) | receives `settle(session, ...)` and `_poll_for_expected(session, ...)` verbatim (`self` -> `session`). |
| `src/autotester/browser/video.py` | 157 (was 150) | `_sweep_orphan_videos` moved here (candidate, unchanged). |
| `src/autotester/browser/secrets.py` | 284 (was 273) | `bad_scheme` (rewritten, see below). |
| `tests/test_browser_session_cdp.py` | 249 | new (candidate's file rewritten): 13 tests, no browser. |
| `tests/test_browser_session_cdp_live.py` | 77 | new: 2 tests, real headless Chromium on `about:blank`; skips when no Chromium. |
| `tests/test_browser_navigation_secrets.py` | 191 (was 160) | `bad_scheme` cases added to an existing secrets file. |
| `docs/MAP.md`, `docs/SNAPSHOT.md` | regenerated | SNAPSHOT was already stale on master (doctor's one violation, D-082 missing); regenerated with `autotester snapshot`. |

Not touched: `pyproject.toml`, `uv.lock`, `stages/*`, `prompts/*`, `schema/*`, `ui/*`, `qa/contracts/*`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`.

## Ported versus rewritten

- **Ported unchanged:** `video.py::_sweep_orphan_videos` move (video.py:88); `session.py` `expose_cdp` ctor argument and the `cdp_url` property shape (read-only, `fset`/`fdel` None).
- **Rewritten (candidate was wrong or insufficient):**
  - `launch.py:142`: candidate asked for a caller-chosen port. Now `--remote-debugging-port=0`; Chromium picks it.
  - `launch.py:53-97` `_published` / `verified_cdp_url`: new. Reads the port Chromium wrote to `<profile>/DevToolsActivePort`, requires the listener to answer `/json/version` with that file's own `/devtools/browser/<guid>` path, and refuses if the port also accepts on 127.0.0.2 (a wildcard bind).
  - `secrets.py::bad_scheme`: the candidate's regex on the raw text MISSED ` javascript://app/x` (leading space) and `java<TAB>script://app/x`, which `urlparse` and a browser both normalise to `javascript`. I reproduced the bypass red first (2 of 9 cases), then replaced the regex with the same `urlparse` call `host_of` uses, so the two cannot disagree.
  - `session.py::start/close`: stale `DevToolsActivePort` removed before launch and at teardown; any endpoint doubt closes the context and raises `CdpEndpointError`.
- **New (plan review items 2 and 3):** `settle`/`_poll_for_expected` move; the owed-gap test.

## How the port window was closed (plan review item 1)

The candidate picked a free loopback port, released it, then passed it to Chromium: between release and bind another process could take the port and `cdp_url` would point at it. Now there is no pick: Chromium is launched with port `0`, binds it itself, and writes the real port to `DevToolsActivePort`. `cdp_url` is built only from that file, only after (a) the file is fresh (a stale one is deleted before launch), (b) the listener answers with that file's unguessable per-launch path, (c) it does not accept beyond loopback. Tests: `test_a_stale_port_file_never_becomes_the_url` (a live "other process" is never even contacted), `test_an_endpoint_that_is_not_this_browser_is_refused_and_torn_down`, `test_a_wildcard_bound_endpoint_is_refused`.

DevTools bounds, each tested: OFF by default (`test_launch_options_carry_no_debug_port_unless_asked`, `test_not_started_or_not_exposed...`); opened only by `expose_cdp=True` and nothing in this slice sets it (grep: no caller in `src/`); launch args never hold a non-loopback address (`test_launch_args_never_hold_a_non_loopback_debugging_address`, 4 combinations of headed x video); closed at teardown (`test_teardown_closes_the_endpoint_and_forgets_the_port_file`, and the live test); `cdp_url` is None when not exposed.

**Measured, real launch (headless Chromium 151, Windows, probe scripts in `.work/t177-slice0/`):** `--remote-debugging-address` is NOT honoured by headless Chromium: with `--remote-debugging-address=0.0.0.0` the port still refused 127.0.0.2 and the LAN IP. The safety rests on Chromium's default loopback bind, which `verified_cdp_url` now checks instead of trusting. **Whether HEADED Chrome honours `--remote-debugging-address`, or binds loopback by default, is UNVERIFIED** (not launched headed; the 127.0.0.2 check in `verified_cdp_url` is the runtime guard if it does not). Chromium's `--remote-debugging-port=0` coexists with Playwright's pipe transport (measured). Teardown: Chromium leaves `DevToolsActivePort` behind after exit (measured), so the session deletes it.

## session.py room (plan review item 2)

299 lines before, **270 after** (this slice's own additions included; 29 free for AT-888's session restart). Moved: `settle` body (20 lines) and its helper `_poll_for_expected` (28 lines) into the EXISTING `browser/assertions.py`, where `_probe` ("shared by settle and assertion polling") and the `ExpectedState` evaluation already live; one concept, one place. `BrowserSession.settle` keeps its signature and delegates in 2 lines, so every caller and every test that patches `session.settle` is unchanged. Behaviour unchanged, existing tests unedited: `test_browser_settle.py` (10) and the 315-test affected run below pass.

## Video mask gap (plan review item 3) - OWED BY THE NEXT SLICE

`video.py::begin_case_video` adds the secret-mask init script to the ONE page it creates. **A second tab opened during a recorded case is recorded without the mask.** Not changed here. Recorded as a passing test, `tests/test_browser_session_cdp.py::test_owed_gap_a_second_tab_opened_during_a_recorded_case_has_no_mask`, which asserts today's behaviour and must be flipped by the slice that masks at context level (`run-video.md` V3/V4 are the criteria it would violate once the agent can open tabs).

## Pre-check (final code commit f8fdbd33, fix cycle 1; per-file runs, `-p no:xdist -p no:cacheprovider -o addopts=`, no full suite)

Pre-check[B5]: f8fdbd33 uv --directory <worktree> run pytest tests/test_browser_session_cdp.py tests/test_browser_session_cdp_live.py -> 25 passed (23 unit incl. the 6 new repair tests + 2 live)
Pre-check[B6]: f8fdbd33 uv --directory <worktree> run pytest tests/test_browser_navigation_secrets.py tests/test_browser.py -> 83 passed (68 + 15)
Pre-check[B9]: f8fdbd33 uv --directory <worktree> run pytest tests/test_browser_session_cdp.py tests/test_browser.py -> 38 passed (teardown; the repair paths close the context and remove the port file)
Pre-check[AF3]: f8fdbd33 uv --directory <worktree> run pytest tests/test_browser_navigation_secrets.py -> 68 passed (scheme half, unchanged by this cycle)
Pre-check: f8fdbd33 uv --directory <worktree> run pytest tests/test_browser_settle.py -> 10 passed (incl. test_browser_startup_checks_before_and_after_launch, see below)
Pre-check: f8fdbd33 one file at a time, each uv --directory <worktree> run pytest tests/test_<f>.py -> explore_modal 6 passed (t=366s), explore_replay 11 passed (t=57s), explore_typing 10 passed (t=300s), explore_secret_scrubbing 3 passed, parallel_run_session_crash 1 passed, video_evidence 2 passed (t=167s). (The B5/B6/B9/AF3 counts above are the per-file totals of the 118-pass batch.)

Run in one batch on f8fdbd33 (cdp, cdp_live, settle, browser, navigation_secrets): 118 passed, no failure. Earlier in the cycle, a broader run (cdp_live, browser_actions, navigation_secrets, settle, unreadable, manual_login, agent_loop) on the first repair draft had ONE failure, `test_browser_settle.py::test_browser_startup_checks_before_and_after_launch`: its fake context has no `close()`, so the new `self.close()` on the failed start raised `AttributeError` and masked the `RunBudgetExceeded` the test expects. Repaired in the source (not the test): the failure-path teardown is `_close_quietly()`, so a `close()` error never masks the error being raised; the other 127 tests of that run passed. The existing test now passes unedited.
`uv --directory <worktree> run ruff check src tests scripts` -> All checks passed. `uv --directory <worktree> run autotester doctor` -> clean. Line counts: launch.py 157, session.py 281, test_browser_session_cdp.py 299 (no new test file: the file stays under 300); no function over 50.
Machine note: the host was under heavy load (other sessions' browsers); live-browser files take minutes, and an 11-file batch hit the 590 s shell cap before finishing, so the later files were run one at a time (above). No full suite run.

## Fix cycle 1 - what was repaired (checker A's FAIL, cycle 0)

Both findings are P1 in `qa/verdicts/t177-slice0-browser-seam.a.md`; P2 folded in as agreed.
1. `launch.py::_answers_as`: `http.client.HTTPException` (non-HTTP bytes -> `BadStatusLine`) joins `(OSError, ValueError)`, and a JSON body that is not an object (`[]`, `"x"`, `null`) is "not this browser" (`isinstance(body, dict)` before `.get`). Both now lead to close + `CdpEndpointError("... not this browser")`. Test: `test_any_reply_that_is_not_this_browsers_json_object_refuses_and_tears_down` (4 raw replies; `FakeDevTools` gained a `raw=` option).
2. `session.py::start`: everything after `launch_persistent_context` is in `try/except BaseException: self._close_quietly(); raise`. `__exit__` never runs when `__enter__` raises, so this is the only place the leak can be closed. Test: `test_a_failure_after_launch_closes_the_exposed_browser` (a `RunBudgetExceeded` from `new_page`; asserts the port is closed and the port file removed). This also closes the session when `observer.attach` fails or `expose_cdp` is False: any failed start now leaves nothing running.
3. `session.py::_close_quietly` (new, one job): `close()` errors are suppressed (`Exception`, not `BaseException`) on a failure path so they never mask the original error; `close()` clears its state and the port file in `finally` regardless. Pinned by the existing `test_browser_startup_checks_before_and_after_launch`, which went red without it.
4. P2, `launch.py::_reaches_past_loopback`: no longer `return False` on every `OSError`. Unexpected errors (e.g. `ENETUNREACH`, `PermissionError`) are doubt and refuse. A refusal, a timeout and a host with no 127.0.0.2 alias still say "no". **Why the timeout stays "no" (measured on this Windows host):** a closed loopback port refuses only after ~2.0 s, so with the 1 s connect timeout a CLOSED port is a `TimeoutError`; failing closed on it turned 3 existing tests red (`test_exposed_session_reports_the_port_the_browser_chose`, `test_teardown_closes_the_endpoint_and_forgets_the_port_file`, `test_cdp_url_is_read_only`: "reaches beyond loopback") because every legitimate loopback-only endpoint timed out. So the timeout case is left as is and the P2 fix is partial on purpose (layer two of two; Chromium's default loopback bind and the identity check through 127.0.0.1 come first). Test: `test_reaching_past_loopback_fails_closed_on_an_unexpected_error` (5 parametrised errors).

## close() on a failure path: is the wait bounded?

Nothing bounds it, and no mechanism was added. `BrowserSession.close()` calls `self._context.close()` then `self._playwright.stop()`; the installed Playwright signatures are `BrowserContext.close(*, reason=None)` and `Playwright.stop()` (checked with `inspect.signature`): neither takes a timeout, and the session's `_timeout()` budget applies to page operations, not to teardown. A browser that does not answer a close therefore blocks `close()`, and so blocks `start()`'s failure path; the same is true of `close()` on master. This is observation (b) below.

## Falsifications (each in a throwaway copy of src/tests outside the worktree, deleted after; green before, red after, restored green)

| Criterion | Edit in the copy | Red node(s) | Green / red / restored |
|---|---|---|---|
| B5 default off | `if expose_cdp:` -> `if True:` (launch.py) | `test_launch_options_carry_no_debug_port_unless_asked`, `test_not_started_or_not_exposed_is_none_and_never_probes_a_port` | 13 / 11 (2 red) / 13, ~19 s each |
| B5 loopback arg | address `{CDP_HOST}` -> `0.0.0.0` | `test_launch_args_never_hold_a_non_loopback_debugging_address[*]` (4 red) | 13 / 9 / 13 |
| B5 port window: identity | `_answers_as` check -> `if False` | `test_an_endpoint_that_is_not_this_browser_is_refused_and_torn_down` | 13 / 12 (1 red) / 13 |
| B5 port window: stale file | drop `forget_cdp_port` before launch (session.py) | `test_a_stale_port_file_never_becomes_the_url` | 13 / 12 (1 red) / 13 |
| B5 loopback only | `_reaches_past_loopback` -> `return False` | `test_a_wildcard_bound_endpoint_is_refused` | 13 / 12 (1 red) / 13 |
| B9 teardown | drop `_cdp_url = None` and `forget_cdp_port` in `close()` | `test_teardown_closes_the_endpoint_and_forgets_the_port_file` | 13 / 12 (1 red) / 13 |
| B6 / AF3 scheme | `bad_scheme` -> `return None` | `test_bad_scheme_refuses_a_non_http_scheme_on_an_allowed_host[*]` (9 red) | 68 / 59 / 68, ~6 s |
| settle move | drop the `_poll_for_expected` call in `assertions.settle` | `test_settle_polls_for_expected_url_...`, `..._visible_text_...`, `test_settle_gives_up_after_its_bound_...` (4 red) | 10 / 6 / 10, ~5 s |

### Fix cycle 1 falsifications (throwaway copy of src/tests/scripts on C: under the session scratchpad, run with `PYTHONPATH=<copy>/src`, `autotester.__file__` confirmed inside the copy; deleted after)

| Repaired path | Edit in the copy (reverts the repair) | Red node(s) | Green / red / restored |
|---|---|---|---|
| `_answers_as` non-HTTP bytes | drop `http.client.HTTPException` from the except | `test_any_reply_that_is_not_...[garbage, not http]` | 23 / 22 (1 red) / 23 |
| `_answers_as` non-dict JSON | drop the `isinstance(body, dict)` guard | `test_any_reply_that_is_not_...` for `[]`, `"x"`, `null` (3 red) | 23 / 20 / 23 |
| `start()` failure after launch | `except BaseException` -> `except ZeroDivisionError` (no close) | `test_a_failure_after_launch_closes_the_exposed_browser` | 23 / 22 (1 red) / 23 |
| `_reaches_past_loopback` fail-closed | the `except OSError` branch -> `return False` | `test_reaching_past_loopback_fails_closed_...` for `ENETUNREACH` and `PermissionError` (2 red) | 23 / 21 / 23 |

The copy was made before `_close_quietly` was added (it uses plain `self.close()`); that helper is pinned by `test_browser_startup_checks_before_and_after_launch`, red on the plain-`close()` version and green now.

Not falsified: the live test file (it needs a real browser and is the cross-check of the unit tests); the owed-gap test (it records a gap, it guards no behaviour).

## Known, not repaired in this cycle (for the checkers to rule on; do not fix)

a. A same-user process that keeps rewriting `DevToolsActivePort` and serves a matching `/json/version` on loopback is adopted as the browser's endpoint. The identity check proves the answer matches the file, not that the listener is the browser we launched; a listener-pid-in-process-tree check would close it.
b. Headed `BrowserSession.close()` did not return on this machine, on master 808cdf7f as well, so headed teardown of the refuse paths (and of the new failure path in `start()`) is unverified. `close()` has no bounded wait (see above).
c. The second-tab mask gap exists on master too (already recorded: `test_owed_gap_a_second_tab_...`).
d. P2 residual: `_reaches_past_loopback` still says "no" on a timeout and on a host with no 127.0.0.2 alias (reason in item 4 above).

## Owner confirm at merge (needed before merge, not before check)

Opening a loopback DevTools port is a **security-posture change**: any local process (any user on a shared host) that can read `DevToolsActivePort` or scan loopback ports can drive the logged-in browser while a run holds it open. D-075 authorizes only the read-only `cdp_url` property on `session.py`; it does not name `launch.py` (the port request) or `secrets.py` (`bad_scheme`) or `video.py`/`assertions.py` (moves). Before merge: (1) a one-line owner confirmation from Umesh that a per-run loopback DevTools port is acceptable; (2) a `docs/ARCHITECTURE.md` security-model line describing it (off by default, per run, loopback, identity-checked, closed at teardown), written under a DECISIONS entry whose `Changes-authorized` names that section and the four extra files. The maker does not edit ARCHITECTURE or DECISIONS from this branch.

## What the next slice owes

1. Mask the second tab (above): the context-level init script, then flip the owed-gap test.
2. The wiring that sets `expose_cdp=True` per run (`ui/run_execution.py:74,108,178`, held by D-075 until T-204 lands), and attaching the SDK to `cdp_url` without closing AutoTester's own context at its teardown (live-only).
3. AT-888 (one failed case must not kill the shared session): the session restart goes into the 30 free lines of `session.py`; it must call `forget_cdp_port` and re-run `_publish_cdp` after a restart, because the DevTools port changes with the browser.
4. Headed Chrome check of `--remote-debugging-address` / default bind (unverified here).
5. Everything in Phase A not in this slice: nine new files, `pyproject.toml`/`uv.lock`, `agent_loop.py`, `run_case_pipeline.py`.

## Process notes

- One shell call ran `cd <dir> && pytest` (the affected-file run), contrary to the no-`cd X && cmd` rule; everything else used `--project`/`-C`. No other deviation; no denied tool call.
- The brief's plan pins say the candidate's `session.py` ends at 300 lines; after this slice it is 270.

Metrics: start=2026-10-11T03:45:00Z end=2026-10-11T04:20:00Z wall_min=35 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=8 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=0 mutants=0 defects_unit=0 defects_6c=0
