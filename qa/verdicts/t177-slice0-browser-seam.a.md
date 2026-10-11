# Verdict (coordinator A, blind dual check) - t177-slice0-browser-seam

Cycle checked: 0
Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting. Head checked: 3495ee61 (code d2d463a9), base master 808cdf7f (merge-base verified with git). Manifest lint: exit 0.
Angle: code-level security review of the whole diff (every hunk read). Blind: no t177 verdict, checkpoint or evidence file opened.
Dispatch note: the maker corrected the command rule mid-check (`uv run --project` from another directory collects master's tests). Redone with `uv --directory <worktree> run pytest`, recording `autotester.__file__` and `rootdir` inside the worktree: the head affected-test run (`qa/evidence/t177-slice0-browser-seam-A/affected-tests-rerun.txt`) and the video-sweep run. Sub-checker head runs made with `--project` (98, 57, 15, 16 passed) are discarded and superseded; their falsification runs were in copies with their own cwd and rootdir, and stand. Not re-run: `test_explore.py` (sub-checker 57-pass run, discarded).

## Check plan (first section)
Signals: security (DevTools port in `launch.py`), destination check (`secrets.py`/`session.py`), refactor moves, tests added. Routed: full-diff read; live probes in a scratch outside the tree; attack table on `bad_scheme`; refactor body diff; test diff; owed-gap on master; one falsification per criterion in copies; full suite only if every criterion met.

VERDICT: FAIL
SCOREBOARD: 4/4 cited criteria (B5, B6, B9, AF3) are evidenced as written in the contract; FAIL is on the reviewer-scope rule (security/correctness defect in changed code, plus a false manifest claim about behaviour)
TIER: L (security: `launch.py:142` `--remote-debugging-port=0` / `--remote-debugging-address`; destination check in `secrets.py:88`)
FAILURES:
- [security, B5/B9 teardown] sev: medium · P1 · the manifest claims "any endpoint doubt closes the context and raises `CdpEndpointError`" (session.py `_publish_cdp`, line 113-118 catches only `CdpEndpointError`). It is false:
  (a) `launch.py:71` `_answers_as` catches only `(OSError, ValueError)`. A listener that answers non-HTTP bytes raises `http.client.BadStatusLine`; one that answers JSON that is not an object (`[]`, `"x"`, `null`) raises `AttributeError` on `.get`. Both escape `start()` with the browser still running and the DevTools port still open (`cdp_url` stays None, so nothing marks it). Ran: `probe-answers-as-escape.py` -> "non-HTTP garbage ESCAPES BadStatusLine; json list/string/null ESCAPES AttributeError".
  (b) any exception in `start()` between launch and `_publish_cdp` (`session.py:105-106`: `pages`/`new_page()`/`_timeout()`, which raises `RunBudgetExceeded` on an exhausted budget) leaves the exposed browser running with its `DevToolsActivePort` file in place. Ran with a real headless Chromium: `probe-p2-start-leak.py` -> "after failed start: port file exists True, context still open True, leaked endpoint accepting on 127.0.0.1: True, json/list targets 1"; only a caller's explicit `close()` removed it. A `with BrowserSession(...)` block never calls `__exit__` when `__enter__` raises. The browser leak itself is pre-existing on master; the exposed DevTools port on it is new.
  Reachability today: nothing in `src/` passes `expose_cdp=True`, so zero live exposure now. It is a defect of the control this slice adds, and the slice's own text promises the opposite.
  Fix direction: in `start()` wrap everything after launch in `try/except BaseException: self.close(); raise` (when `expose_cdp`, or always); widen `_answers_as` to treat any non-dict JSON and any `http.client.HTTPException` as "not this browser"; add a test per path (garbage listener; exception after launch).

## Per-criterion (contract text read verbatim)
- B5 (headed default; persistent profile; this slice: opt-in arg only): MET. Default launch args carry no debug flag, 4 headed x video combinations never hold a non-loopback address, no caller sets `expose_cdp`, port is `0` so no pre-picked port, stale file is deleted at `session.py:101` before launch, identity check needs the browser GUID path from the same file. Falsified: `if expose_cdp:` -> `if True:` (copy) red on `test_launch_options_carry_no_debug_port_unless_asked`, `test_not_started_or_not_exposed...` and the live no-port test; green 2 before.
- B6 (named refusal outside allowed hosts): MET. Falsified: drop `bad or` in `check_destination` -> 9 new scheme tests red (`DID NOT RAISE NavigationRefused`).
- B9 (close only own context; no process-wide kill): MET. `close()` clears `_cdp_url` and removes the port file in `finally`. No `taskkill|pkill|killall|Stop-Process` in `src/`. Falsified: drop `forget_cdp_port` in `close()` -> teardown test and the live teardown test red; mutating `self._context.close()` -> `test_close_only_closes_own_context_and_is_idempotent` red `(0,1) != (1,1)`. Observation: the `_cdp_url = None` half of that hunk is not independently observable (the property already returns None when `_context` is None).
- AF3 (scheme half of the destination check): MET for what this slice carries. Falsified: `bad_scheme` -> `return None` (copy) -> same 9 tests red on `assert bad_scheme(url) is not None`.
Invariants: none touched beyond those above.

## Security findings (evidence in qa/evidence/t177-slice0-browser-seam-A/)
- Default off, no src caller, loopback-only args: confirmed by reading and by the arg tests; 3 extra mutants: `_reaches_past_loopback` `return False` caught, `_answers_as` -> `if False` caught, check-order swap equivalent (not caught, harmless).
- Live headless Chromium: port bound on 127.0.0.1 only (127.0.0.2 refused), port closed and file removed after teardown (`own-probe.txt`).
- Port file read only after a stale one is deleted: yes (`session.py:101`, test `test_a_stale_port_file_never_becomes_the_url`).
- Residual, owner decision, not a defect: `/json/list` answers without the GUID (`own-probe.txt`: "needs no secret: targets 1, ws page url present"). The GUID proves identity to US; it does not stop another local process from driving the page targets. The owner-confirm note should say exactly that.
- P2 medium (non-blocking): `launch.py:79` `_reaches_past_loopback` returns False on ANY `OSError`, so it fails open on a timeout or on a host with no 127.0.0.2 alias (macOS), where the wildcard check is vacuous (probe P3: both -> False). Distinguish `ConnectionRefusedError`; treat other errors as doubt. Layer two of two (Chromium's default loopback bind and the identity check through 127.0.0.1 come first); Windows is the project platform.
- `bad_scheme`: 120-URL attack table (sub-checker, in copy/head/master): never disagrees with `host_of` (same `urlparse` expression); no ACCEPT of an explicit non-http(s) scheme with `//` on an allowed host, incl. leading space/control chars, tab/newline inside the scheme, case; 17 URLs newly refused vs master, none newly accepted; `_host_matches`/`SecretStore.resolve` byte-unchanged (11 pure insertions in `secrets.py`). Pre-existing on master, unchanged: `app.pathlynks.test:8080/x` accepted (pinned by a new test, deliberate), `https://app.pathlynks.test:abc/x` accepted (browser rejects), fullwidth-dot host maps to same host. Caveat: control-char stripping depends on CPython 3.11.15 urllib (P5, low).
- Refactors: `_poll_for_expected` and `_sweep_orphan_videos` 0 diff lines after rename; `settle` differs by the one required `session` argument; every caller/patch still binds. Test diff: +357/-0, no existing test edited, no new skip/xfail (only `_skip_if_no_chromium` in the new live file).
- Owed gap (second tab unmasked): PRE-EXISTING on master (ported test passes on 808cdf7f; master `video.py:103` masks only the one page). No cited criterion is unmet because of it: B5/B6/B9 are about launch, destinations, teardown; AF3 is destination/guards. It is a latent run-video V3/V4 exposure that becomes reachable once the later slice lets an agent open tabs; the recorded test is honest and the owner list names the slice.

## New-module table (D-082 item 1)
| File | New under | Named by brief/contract | One job in docstring |
|---|---|---|---|
| (no new file under `src/`) | - | - | - |
| tests/test_browser_session_cdp.py | tests/ | brief line 121 (115 lines planned, 249 built) | yes: `cdp_url` is read-only, loopback-only, opt-in, proven THIS browser's |
| tests/test_browser_session_cdp_live.py | tests/ | manifest only; brief names no live file | yes: real browser serves DevTools on loopback only and closes at teardown |

## Tests and suite
Head affected run (`uv --directory`, rootdir in tree): 162 passed, 1 failed (`test_video_parallel_sweep.py::test_two_sessions_sharing_a_run_dir_do_not_lose_each_others_video`, "A never finished closing", a wait timeout under heavy machine load); the same test alone on the same head: 1 passed (396 s). `load-flake: tests/test_video_parallel_sweep.py::test_two_sessions_sharing_a_run_dir_do_not_lose_each_others_video` (P4, low). Full suite: NOT RUN (owed on the re-check) because a criterion-level security defect is open; no lock was taken or waited on. Merge is additionally held on the owner confirmation for the DevTools port (not mine to give; ARCHITECTURE security-model line also owed).

## PROPOSED-ISSUES (no ledger write)
P1 {"severity":"medium","type":"security","title":"CDP endpoint doubt does not always close the browser: _answers_as lets BadStatusLine/AttributeError escape; start() exception after launch leaves the exposed browser and port file","evidence":"launch.py:71; session.py:105-118; probe-answers-as-escape.py, probe-p2-start-leak.py"}
P2 {"severity":"medium","type":"security-hardening","title":"_reaches_past_loopback fails open on any OSError (timeout, no 127.0.0.2 alias)","evidence":"launch.py:79; probe P3"}
P3 {"severity":"low","type":"test-gap","title":"_cdp_url=None half of close() unobservable; no test pins failing both checks"}
P4 {"severity":"low","type":"load-flake","title":"test_two_sessions_sharing_a_run_dir... times out under load (passes alone)"}
P5 {"severity":"low","type":"pre-existing","title":"destination check accepts host:port/x schemeless form and depends on CPython urllib control-char stripping"}
P6 {"severity":"low","type":"process","title":"check wall 110 min vs L 45: sub-checker live-browser tests ran 4-7 min each under load (slow: live tests/falsification copies 60 min)"}

EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent; sub-checkers read-only)
EXPLANATION: The criteria's own text is met and every falsification went red on the named assertion, but the new control does not fail closed the way the manifest says: two reproducible paths leave an exposed DevTools browser running after `start()` raises. Both fixes are small and local to `launch.py` and `session.py`.
Metrics: start=2026-10-11T04:26:10Z end=2026-10-11T06:16:00Z wall_min=110 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=8 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=6590 mutants=3 defects_unit=1 defects_6c=0 slow: sub-checker live-browser runs and copies 60 min
