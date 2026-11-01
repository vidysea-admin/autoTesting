# Verdict - e2e-fixes-e4 (E4.1-E4.3; AT-1421, AT-1415)

**Verdict: PASS** (3 non-blocking warnings, W1-W3 below)
**Cycle checked:** 0
**Checked:** `feat/e2e-e4` head `efad4496` (base `dccc65e9`), worktree `D:/autoTesting/.claude/worktrees/e2e-e4`. Fresh context; read-only toward `src/` and `tests/` (mutants ran on the harness's private copy). Fakes and local 127.0.0.1 stubs only: no internet, no `.env` value read or printed (the approval key used by my scratch scripts was a dummy env value).
**Contract:** `qa/contracts/e2e-fixes.md` unit E4. **Manifest:** `qa/manifests/e2e-fixes-e4.md`.

## Commands re-run by the checker (2 files per call, `env -u ANTHROPIC_BASE_URL uv run pytest <files> -o addopts= -q`, `PYTHONPATH=<worktree>/src`)

| Files | Result |
|---|---|
| test_target_probe + test_run_unreachable_target | 25 passed |
| test_run_bounds_stop + test_video_fate | 20 passed |
| test_run_teardown_stall + test_run_teardown_stall_wiring | 26 passed |
| test_teardown_residuals + test_run_launcher_approval | 26 passed |
| test_session_survives_failure + test_ui_runs | 26 passed |
| test_run_failure_artifacts + test_video_retention (V2/V6/V8) | 9 passed |
| test_video_pointers + test_run_launcher | 35 passed |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor` (to `.work/doctor-chk-e4.txt`) | rc 0, `doctor: clean` |

`autotester.__file__` resolved to the worktree `src` (checked). Full suite not run (machine low on memory, per the brief).

**Known failure, confirmed pre-existing.** `tests/test_schedule_tick.py::test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively` fails identically on bare master `dccc65e9` (temporary detached worktree `.work/chk-master-dccc`, same venv with `PYTHONPATH` at that tree, removed afterwards): `store.mongo_routes -> browser.profiles` plus the two `auth.store*` edges. The sorted failure text diffs IDENTICAL between master and the branch. Not caused by E4; not a FAIL.

**Merge against moved master.** `git merge-tree --write-tree 2ffa1e60 efad4496` -> rc 0, tree `8b1acbb9`, **no conflicts** (the expected `routes_report.py` and `docs/MAP.md` collisions did not occur; E1 and E4 touch different hunks). Merged `run_launcher.py` is 296 lines, `routes_report.py` 288 (both under the 300 cap). I built a throwaway merge commit in `.work/chk-merged-e4` and ran there: test_run_bounds_stop + test_video_fate 20 passed; test_run_unreachable_target + test_ui_runs 13 passed; E1's test_ui_report_corrupt_trace + test_run_launcher 12 passed; `autotester doctor` rc 0 `doctor: clean`. Worktree removed. No merge or push done.

## Per-criterion findings

1. **E4.1(a) PASS.** The bound is the existing mechanism (`stages/run_budget.py:187-189,221-225` unchanged). `test_run_bounds_stop.py:25` drives the real `RunBudget` with an injected clock (case 1 burns 200 s of a 170 s bound): exactly 1 case runs, 2 INCONCLUSIVE with `wall_clock_s` in the note, 0 FAIL, EXECUTE span `("failed", "run budget exhausted: wall_clock_s")`, and the new `Run.stop_reason == "wall_clock_s"` (`run_launcher.py:236-237,274`). Mutant m15 (bound not enforced) KILLED. The contract's wall-time invariant is not asserted as a number (it rests on the existing D-112 mechanism); acceptable, the contract says prove the behaviour, not rebuild it.
2. **E4.1(b) PASS.** `ui/preflight_view.py:39-60` renders acting seconds, judging and housekeeping held off the clock, the bounds line and the stop reason; `excluded_s=None` -> "clock accounting NOT RECORDED" (never zero); a D-112 run without `acting` -> "acting time NOT RECORDED". Rendered the real unreachable-run page through `TestClient`: "Preflight warnings (1) / The run did not start: no case was run. / target 127.0.0.1 did not answer within 1 s from this server / Run bounds / clock (only time acting on the target counts): acting 1.0s; held off it: judging 0.0s, housekeeping 0.0s / stopped early: the target did not answer, so no case was run (each recorded INCONCLUSIVE)". Maker mutants m25, m26, m27, m28 were killed in the maker's run; m28 re-run by me KILLED.
3. **E4.2 PASS.** Probe `stages/reachability.py:137-157`: one GET, `ProxyHandler({})`, no cookie processor, no body, scope test `:144` (`bad_scheme`, `host_of`, `allows_domain`), two attempts inside `PROBE_TOTAL_S = 10.0`, any `HTTPError` is an answer (`:110-112`). Launcher `run_launcher.py:211-212` calls it once, after `prepare_run` (so after every gate) and before `_entry_pool` (so before any `BrowserSession.start`). `skip_run` `:166-182` saves one ERRORED `RawResult` + INCONCLUSIVE verdict per case, fails the EXECUTE span, and returns the plan with `stop_reason="target_unreachable"` and the one message, which `launch_run` writes to `Run.preflight_warnings` and `Run.stop_reason`. Tests: blackhole with the REAL 10 s constant ends in <= 15 s with the exact message; launched run: 3 INCONCLUSIVE carrying the one cause, `BrowserSession.start` never called, no `.png`/`.webm` under the run dir; a 500 target runs the cases (5 status codes parametrised); out-of-scope host, no allowed domains, ftp/javascript/userinfo/bare-host URLs: no connection. Mutants m3 (host outside scope probed), m7 (cookies), m12 (probe skipped by launcher), m2 (redirects out of scope) KILLED by me; own3 (default seam never probes) and own4 (skipped cases carry no cause) KILLED.
4. **E4.3 PASS.** `browser/video.py:228,239,243` route all three silent-`None` paths through `_video_lost` (event label `video-lost`, reason string, scrubbed); recording-off stays silent (m20 test). `video_fate :257-272` yields the one sentence per fate; `ui/routes_video.py:81-93` shows it and keeps the V8 link for a kept video. `_finalize_video` (`stages/run_case_pipeline.py`) is not in the diff, so V2 is unchanged; V2/V6/V8 tests (test_video_retention, test_video_pointers) pass unmodified. Rendered the unreachable run page: each unrun case shows "no video: recording was off for this session, or the case never reached execution". Mutants m17, m21, m23 KILLED; own2 (every case treated as PASS in `video_section`) KILLED.

## Security probe (judgement call 5, ruled on with evidence)

Own script `.work/chk_e4_redirect_probe.py` (allowed_domains = `["127.0.0.1"]`, a 302 server, a second listener standing for the foreign host, `HTTP_PROXY=http://127.0.0.1:9` set in the environment):

```
absolute foreign host        result=None foreign_connect=False requests=['/']
protocol-relative foreign    result=None foreign_connect=False requests=['/']
userinfo trick               result=None foreign_connect=False requests=['/']
backslash trick              result=None foreign_connect=False requests=['/']
lookalike suffix             result=None foreign_connect=False requests=['/']
```

The redirect to a foreign host is never followed (the 3xx is itself the answer, so the run proceeds), no request reaches the foreign listener, and the environment proxy is ignored (a proxy at port 9 would have made every row fail). In-scope redirects are followed and carry no cookie, authorization or content-length (test at `test_target_probe.py:80`; mutant m7 kills it). A stuck resolver is bounded: with `urllib.request.OpenerDirector.open` patched to sleep 30 s and `PROBE_TOTAL_S=2`, the probe returned in 2.5 s with the "did not answer" message (`.work/chk_e4_hang.py`).

## Rulings on the maker's 12 judgement calls

1. **ERRORED raw outcome graded INCONCLUSIVE: ACCEPT.** The verdicts are INCONCLUSIVE with the one cause; no goto was attempted; same path as an exhausted budget (`grade_errored_result`). A new raw outcome would touch `schema/enums.py` and E2's verdict path, outside E4's files.
2. **Host outside `allowed_domains` not probed, run proceeds: ACCEPT.** The contract text is "skipped for `base_url` hosts outside the project's allowed domains (refuse, do not probe)" and the falsifier is "refused, no connection attempted (assert the socket saw no connect)". What is refused is the probe's connection. Failing the whole run for a project whose `base_url` is declared outside its own scope is a separate decision the contract does not make; the gate and the browser already refuse an out-of-scope navigation per case.
3. **`acting` inside `Run.excluded_s`: ACCEPT.** One source for the D-112 arithmetic; pre-D-112 runs are unambiguously NOT RECORDED. See W1 for a side effect.
4. **`PINNED_SEAMS` gains `target_probe`, consulted only after the gate: ACCEPT.** `launch_run` calls `prepare_run` (which runs `require_live_case_approval`) before `run_cases_traced`; the probe can only END a run, never widen one. `routes_runs.py:58` and the queue path (`_run_queued` -> `launch_run`) use the default seam, so button, schedule and queue are guarded. Own3 shows the pin does not hide a dead default.
5. **Probe resolves from the server, no proxy: ACCEPT** (verified above; the browser also verifies TLS by default and no `ignore_https_errors` exists in `src`, so a TLS failure is consistent between probe and browser).
6. **Exact-key pins extended with `"acting"`: ACCEPT.** Diff read: each set grew by one key, no assertion weakened.
7. **`test_session_survives_failure` filters `video-lost`: ACCEPT.** Its fake page has `video=None` with recording on, which is exactly the formerly silent path; the test's own subject (one `session-restart`) is unchanged and the new behaviour is pinned by `test_video_fate.py` (m17 KILLED).
8. **Two `run_cases_traced` stubs gain `stop_reason=None, warnings=()`: ACCEPT** (additive).
9. **HTML export unchanged: ACCEPT** (live page only; out of the contract's named files).
10. **`_video_section` moved to `routes_video.py`: ACCEPT.** The merge dry-run shows no conflict with E1.
11. **AT-1415 premise (PASS case, V2 prune by design): ACCEPT.** No V2 change; the page line and the loud paths are the deliverable.
12. **Not run / not done: ACKNOWLEDGED.** The lifecycle review is this checker pass; no separate `senior-software-engineer` dispatch was made, per the brief. A real DNS/TLS failure on a public name is not exercised by the maker or by me (no internet by design); the classes are covered with the local stub and the `.invalid` name.

**The autouse conftest fixture cannot mask a real failure: ACCEPT.** `tests/conftest.py:60-67` patches only the name `reachability.probe_target`. The probe tests import the real function by name at module import (before the fixture runs) and inject it through `RunSeams(target_probe=...)`; the launched tests pass against local stubs. The one thing the fixture could hide, the default seam being dead, is pinned by `test_the_default_seam_reaches_the_probe_by_late_binding`, and my own3 mutant (`check_target` returns None) is KILLED by it.

## Mutation evidence (C7, run by me)

`scripts/mutation_check.py .work/chk-e4-mut.json` (private-copy harness, baseline green): **12/13 killed.** Maker mutants KILLED: m2, m3, m7, m12, m15, m17, m21, m23, m28 (9 of 9, including the two the maker had to re-run, m17 and m23). My own: own2, own3, own4 KILLED; own1 SURVIVED (see W2). Output in `.work/chk-e4-mut-out.txt`.

## Warnings (non-blocking; PASS stands)

- **W1. "acting" on an unreachable run is the probe's duration, not zero.** The rendered page says `acting 1.0s` (would say about 10 s on a real blackhole) for a run in which no case acted, because `RunBudget`'s acting clock starts at budget creation, before the probe (`run_launcher.py:205,211`). Defensible (the probe is an action on the target, contract E4.2) but `test_the_stopped_run_records_zero_acting_time_not_a_missing_measurement` (`test_run_unreachable_target.py:61`) asserts only `excluded_s["total"] == 0.0`, the held-off union, not `acting`; its name overstates. The same early clock start means a slow-but-reachable probe consumes `wall_clock_s`. Suggest: rename the test, or a follow-up that stamps `acting` from case start.
- **W2. The stuck-resolver guard is untested.** own1 (`outcome` default changed from `TimeoutError` to `None`) survives because every test lets the socket timeout fire first. I exercised the guard by hand (above: 2.5 s for a 2 s bound), so it works, but no test pins it. Worst case the probe can exceed `PROBE_TOTAL_S` by about 0.5 s per attempt (about 10.5 s against 10 s); the contract falsifier allows <= 15 s, so this is within contract.
- **W3. Scope notes.** (a) The probe guards `launch_run` (button, schedule, queue); the staged pipeline in `stages/orchestrate_downstream.py` (`make_report_stage`, `save_tracked_run` at `:188`) builds its own `Run` and neither calls the probe nor carries `stop_reason`; contract E4 does not name that path, but a follow-up should decide whether it needs the same guard. (b) The `stages/reachability.py:13` docstring names `record_unreachable`, which does not exist (the function is `skip_run`). (c) After merge `docs/MAP.md` showed no conflict and `doctor` is clean on the merged tree, so no regeneration is owed.

## Close-out

PASS. The maker may flip `qa/manifests/e2e-fixes-e4.md` to `checked-PASS`. Merge and push remain with the orchestrator (not done here). Unproven corners, both outside the contract's falsifiers: a fast-fail against a real public DNS/TLS failure, and the E4.1 wall-time invariant as a number.
