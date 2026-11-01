# Verdict - e2e-fixes-e4 (E4.1-E4.3; AT-1421, AT-1415), fix cycle 1

**Verdict: PASS** (3 non-blocking warnings, W1-W3 below)
**Cycle checked:** 1
**Checked:** `feat/e2e-e4` head `15cb5df9` (base `dccc65e9`; cycle-0 PASS `962bea0d` sits below it), worktree `D:/autoTesting/.claude/worktrees/e2e-e4`. Fresh context, read-only toward `src/` and `tests/` (mutants ran on the harness's private copy). Fakes and local 127.0.0.1 stubs only: no internet, no `.env` value read or printed. `autotester.__file__` resolved to the worktree `src`.
**Contract:** `qa/contracts/e2e-fixes.md` unit E4. **Manifest:** `qa/manifests/e2e-fixes-e4.md` (cycle 1). The cycle-0 findings W1-W3 and the senior review's two findings were taken as the issue list; every claim below was re-run.

## Commands re-run (2 files per call, `env -u ANTHROPIC_BASE_URL uv run pytest <files> -o addopts= -q`, `PYTHONPATH=<worktree>/src`)

| Files | Result |
|---|---|
| test_target_probe + test_run_unreachable_target | 37 passed |
| test_run_bounds_stop + test_video_fate | 20 passed |
| test_run_launcher + test_run_launcher_approval | 24 passed |
| test_reachability_warning + test_ui_runs | 15 passed |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor` (> `.work/doctor-chk-e4c1.txt`) | rc 0, `doctor: clean` |

Full suite not run (low-memory rule).

**Known failure, edge list checked.** `tests/test_schedule_tick.py::test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively` still fails (the cycle-0 checker proved it identical on bare master `dccc65e9`). I called `scheduler_side_violations()` directly: exactly `store.mongo_routes -> browser.profiles`, `auth.store -> auth.store_mongo`, `auth.store_mongo -> auth.store_mongo_tx`. No E4 module (`reachability`, `run_launcher`, `parallel_run`, ...) appears. Not a FAIL of this unit.

**Merge.** `git merge-tree --write-tree master 15cb5df9` (master `bc284510`) -> tree `29ed36a4a4f6153183518f89068f71d2269dabd6`, no conflict output. No merge or push done.

## Cycle-1 findings

1. **Senior review #1 (scope escape via a non-http redirect): FIXED, verified two ways.** `stages/reachability.py:105` refuses any redirect where `bad_scheme(newurl)` (the 3xx is then the answer); `_build_opener :148-158` builds an `OpenerDirector` with only proxy-off, HTTP, HTTPS, Unknown, DefaultError, `_InScopeRedirects` and ErrorProcessor handlers, so no FTP/file/data handler exists. My own script `.work/chk_e4c1_probe.py` (allowed_domains `127.0.0.1`, a 302 server whose `Location` points at a listener that records connects, `HTTP_PROXY`/`FTP_PROXY` set to a dead port to prove they are ignored):

```
ftp on allowed host    result=None connect_at_target_port=False reqs=['/']
FTP upper-case         result=None connect_at_target_port=False reqs=['/']
file:                  result=None connect_at_target_port=False reqs=['/']
file://allowed         result=None connect_at_target_port=False reqs=['/']
data:                  result=None connect_at_target_port=False reqs=['/']
gopher on allowed      result=None connect_at_target_port=False reqs=['/']
javascript:            result=None connect_at_target_port=False reqs=['/']
foreign host http      result=None connect_at_target_port=False reqs=['/']
foreign host ftp       result=None connect_at_target_port=False reqs=['/']
in-scope redirect followed: None ['/landed']
```

   Every non-http scheme and every foreign host: no connection, probe returns None (run proceeds), 0.3 s. The in-scope http redirect is still followed (positive control). Mutant c1 (scheme check removed) KILLED by the named `[ftp]` test.
2. **Senior review #2 (a probe bug skipped runs with a false cause): FIXED and does not weaken real detection.** `_attempt :124` catches `Exception`; `probe_target :181-185` fails open only when the failure is neither `_NO_ANSWER` nor an instance of `_NETWORK_ERRORS = (OSError, http.client.HTTPException)` (`:60`), appending ONE warning naming the class and host. My script, same run:

```
refused: target 127.0.0.1 refused the connection from this server []
dns: target nope.invalid could not be resolved (DNS) from this server []
bug (RuntimeError): None ['the reachability check of 127.0.0.1 could not run (RuntimeError); the run went ahead without it']
netfail(ConnectionResetError): target 127.0.0.1 closed the connection without an HTTP answer from this server []
netfail(HTTPException BadStatusLine): target 127.0.0.1 closed the connection without an HTTP answer from this server []
```

   Real network failures (refused, DNS, reset, malformed HTTP) still stop the run with the named message and no warning; only a non-network exception fails open. The launcher copies the note into `Run.preflight_warnings` (`run_launcher.py:213`, `:269`); `test_a_probe_bug_lets_the_run_proceed_and_says_why_on_the_run` runs 2 cases through the real launcher. Mutants c3, c4, c7, c9 KILLED (c7, "a network failure fails open too", kills 8 tests, so it is well pinned).
3. **Cycle-0 W1 (acting clock): FIXED for the unreachable run.** `skip_run` records `NO_CLOCK` (`reachability.py:55,211`, all zeros) and `RunBudget.for_cases` is now created after the probe (`run_launcher.py:214`). The test now asserts `excluded_s["acting"] == 0.0` and the rendered page text `acting 0.0s` (no `acting 1.`). See W1 below for what the budget move does and does not pin.
4. **Cycle-0 W2 (join fallback untested): FIXED.** Mutant c6 (`_NO_ANSWER` default flipped to `None`) KILLED by both named tests (`test_a_resolver_that_never_returns_is_unreachable_within_the_bound`, `test_attempt_reports_no_answer_when_the_worker_outlives_its_join`).
5. **Cycle-0 W3b (docstring): FIXED** (`reachability.py:13` now names `skip_run`). W3a (`orchestrate_downstream.py` unguarded) is recorded out of scope by the maker; I accept it as outside the contract's named files (the probe guards `launch_run`: button, schedule, queue); it remains an open follow-up, not a defect of E4.
6. **Interfaces consistent.** `target_probe`'s only definition/call sites are `run_launcher.py:54,92,211` and the default `check_target`; `skip_run` has one caller (`:212`); `tests/conftest.py` autouse stub accepts the new `notes` argument and cannot mask the real function (the default-seam test passes). `plan.warnings` is only ever populated by E4 code, so `skip_run` replacing it with `(message,)` loses nothing today.

## Mutation evidence (C7, run by me)

`scripts/mutation_check.py .work/chk-e4c1-mut.json` (private-copy harness, baseline green; output `.work/chk-e4c1-mut-out.txt`): **6/9 killed.** Maker cycle-1 mutants re-run: **c1, c3, c4, c6, c7, c9 all KILLED** (6 of 6). My own three SURVIVED:

- own-a: `ProxyHandler({})` -> `ProxyHandler()` (probe honours the environment proxy): SURVIVED.
- own-b: acting budget created before the probe: SURVIVED (equivalent for the unreachable path, see W1).
- own-c: redirect deadline check dropped from `_InScopeRedirects.redirect_request`: SURVIVED.

## Warnings (non-blocking; PASS stands)

- **W1. The "budget after probe" move is not pinned.** own-b survives because `skip_run` ignores the budget and writes `NO_CLOCK` regardless, so the unreachable-run assertion (`acting == 0.0`) holds either way. The real effect of `run_launcher.py:214` is on a slow-but-reachable probe (it no longer consumes `wall_clock_s`), and no test observes that. The unreachable-run claim itself is pinned (maker mutant c8, `NO_CLOCK` with `acting: 1.0`, is in the maker's cycle-1 spec; I did not re-run c8). Suggest a launcher test with a probe seam that advances the injected clock and a tiny `wall_clock_s`.
- **W2. "No proxy" is unpinned by any test.** own-a survives: nothing fails if the probe starts honouring `HTTP_PROXY`. Behaviourally correct today (my script ran with `HTTP_PROXY`/`FTP_PROXY` pointed at a dead port and every row still resolved correctly; handler list at `reachability.py:152`), and the manifest (judgement call 5) states the choice. A test setting `HTTP_PROXY` to a dead port with a working local target would pin it.
- **W3. The redirect deadline clause is unpinned.** own-c survives: `time.monotonic() >= self.deadline` at `reachability.py:106` has no test. Harmless (each attempt is separately bounded by its socket timeout and the join in `_attempt`), so the total bound still holds; the clause is belt-and-braces.

## Close-out

PASS at cycle 1. The maker may flip `qa/manifests/e2e-fixes-e4.md` to `checked-PASS`. Merge and push remain with the orchestrator (D-130 holds pushes to origin in any case). Still unproven, outside the contract's falsifiers: a fast-fail against a real public DNS/TLS failure, and the wall-time invariant as a number.
