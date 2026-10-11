# Manifest - at888-session-survives-failure

**Unit:** AT-888: one finished or failed case must not take the shared browser session down for the rest of its batch. Owner approval to build: `docs/DECISIONS.md` D-084 item 1.
**Issue:** AT-888 (`qa/issues.jsonl`, high, cascade). The Pathlynks run of 2026-10-11 (41 cases) returned 34 INCONCLUSIVE with closed-browser errors (31 `TargetClosedError`, 3 "Failed to open a new tab") that tested nothing; no case on a shared session ever passed after the first.
**Branch / base:** `wave/at888-session-survives-failure` on master 3748cb83.
**Code commit (pre-check sha):** 9286a25d (HEAD; its parent 55816796 holds the source change, 9286a25d only adds a hard deadline and a cached Chromium probe to the live test file). The manifest commit after it adds only this file.
Contract: C1, C2, C3, C4, C5 (this unit's acceptance criteria, quoted below; they serve `qa/contracts/ui-run.md` RU3, `qa/contracts/run-video.md` V1 and V3, and the fail-closed rule of `qa/contracts/core-invariants.md`)
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (concurrency/timing touch: a browser process that exits when its last page closes, a restart of the shared session between two cases)
Dual check: no (no auth, tenancy or production-write code is added; the secret-mask line `page.add_init_script(_MASK_INIT_SCRIPT)` in `begin_case_video` is byte-for-byte unchanged and C5 pins it by test, so the diff does not change secret masking; if the checker reads moving the call site of `new_page` as touching masking, that is its call to make and I would not object)
Fix cycle: 0
Executor: claude-sonnet-subagent (maker build subagent)
Status: ready-for-check
Full-suite trigger: none. `browser/session.py` is NOT edited; the diff is `browser/video.py` and one helper pair in `stages/run_case_pipeline.py`.

## Criteria served (quoted)

- AT-888 `expected`: "N normal cases in one tier on one session all execute whatever an earlier case's outcome was; a dead session is restarted once and the case retried, and an infrastructure failure is reported as such, not as one INCONCLUSIVE per remaining case. A test with a fake or real context that closes when its last page closes pins it."
- `ui-run.md` RU3: "Every case in `store.list_cases()` gets a real result + verdict saved".
- `run-video.md` V1: "Every case run through `run_and_grade_case`/`run_and_grade_case_resilient` ... produces exactly one video file ... for that `case_id`".
- `run-video.md` V3: masking "active for every frame the video recorder captures ... from the moment that field exists on the page".
- `core-invariants.md` C12: "Every signal and every measurement this system reports must fail closed".

Unit-local ids used below:

- **C1** After ANY case outcome (pass, fail, error, timeout, a page the case closed itself, a crashed page, a popup closed, a browser that died) the next case starts on a live page.
- **C2** A session that is truly dead is restarted ONCE, visibly: a `session-restart` evidence item on the result of the case that hit it, not a silent retry; later cases do not restart again.
- **C3** A case that could not run because the session could not be restored ends ERRORED (the raised `SessionRestoreError` is caught by `_run_and_grade_resilient`, `ui/run_execution.py:53-57`) naming that cause; the restart is not re-attempted per case; never a false PASS.
- **C4** The case's video is still finalised and returned by `end_case_video` for every case, including after a restart.
- **C5** The secret-mask init script is on the page of every case, including the first page after a restart.

## Root cause (proven by reproduction, not by reading)

Reproduction script: `.work/repro_at888.py` (gitignored scratch, local HTTP server on 127.0.0.1, no product, no credentials).

| Mode | Result |
|---|---|
| headless, 3 cases, case 1 fails | all three cases ran; context holds 0 pages after each `end_case_video`; no error. Does NOT reproduce. |
| headless with `channel="chromium"` (new headless) | same, no error. Does NOT reproduce. |
| **headed** (the Pathlynks project has `"headed": true`), case 1 fails by a 500 ms click timeout | case 1 ok; **case 2: `BrowserContext.new_page: Protocol error (Target.createTarget): Failed to open a new tab`; case 3 the same; `close()` raises `TargetClosedError`** |
| **headed**, case 1 PASSES | identical: case 2 and 3 die the same way |

So: (1) the leading suspect is right. `end_case_video` closed the case's page, which was the context's last page; a headed persistent Chromium exits when its last window closes; nothing restarted it. (2) The first case's outcome is irrelevant: it fails after a PASS too, which is why "no shared-session case ever passed". (3) The 31 `TargetClosedError` are the later cases hitting the already-dead driver. (4) Headless survives, which is why every existing browser test was green. I ran the headed reproduction (a visible window for about 10 s, local page only) because headless could not reproduce; this is the one deviation from "headless" in the brief.

## What changed

Only these functions. **`src/autotester/browser/session.py`: not touched.**

`src/autotester/browser/video.py` (150 -> 224 lines):
- `VideoMixin.begin_case_video` (`video.py:99-124`): a latched `_restore_error` raises `SessionRestoreError` first; `self._context.new_page()` is replaced by `self._open_case_page()`. The `add_init_script(_MASK_INIT_SCRIPT)` line is unchanged.
- `VideoMixin.end_case_video` (`video.py:178-197` (spare page at line 193)): opens a spare page BEFORE closing the case page (the fix for the root cause); `_page` is the spare, never `None`, unless the browser is already dead.
- new `SessionRestoreError` (`RuntimeError`), `VideoMixin.take_session_events`, `VideoMixin._open_case_page`, `VideoMixin._restart_session`, `VideoMixin._scrubbed`, module `_one_line`.

`src/autotester/stages/run_case_pipeline.py` (229 -> 243 lines):
- `run_and_grade_case` and `run_and_grade_case_resilient`: take the session's restart events right after `begin_case_video` and attach them to the result (`run_case` slices evidence after `begin_case_video`, so it cannot see them). New helpers `_take_session_events`, `_with_events`.

Tests: `tests/test_session_survives_failure.py` (229 lines, fake context that behaves like headed Chromium: closing the last page kills it) and `tests/test_session_survives_failure_live.py` (114 lines, real Chromium, hard `faulthandler` deadline; the headed reproduction test runs only with `AUTOTESTER_HEADED_TESTS=1`).

## Merge note (T-177 slice 0, branch `wave/t177-slice0-browser-seam`)

- I did not touch `session.py`, `settle`, `_poll_for_expected` or `_sweep_orphan_videos`. My hunks in `video.py` are inside `begin_case_video`, `end_case_video`, the new methods after `begin_case_video`, the import block and the lines before `_ignore_close_errors`; T-177 adds `_sweep_orphan_videos` to `video.py`, so expect a textual neighbour, not an overlap.
- **After T-177 lands, a restart must also re-run the DevTools publish step** (the debugging port changes with the browser). The restart is one function, `VideoMixin._restart_session` (`video.py`), and it relaunches ONLY by calling `self.start()`. If T-177 puts `_publish_cdp` inside `start()`, nothing more is needed; if it puts it anywhere else, add that call in `_restart_session` right after `self.start()`. Its teardown also must delete the old port file (T-177 deletes it at close, but `_restart_session` does not call `close()`).

## Pre-check (final code commit 9286a25d; worktree clean; no full suite; every run as `uv --directory <worktree> run ...`)

Pre-check[C1]: 9286a25d uv --directory D:/autoTesting/.worktrees/at888-session-survives-failure run pytest tests/test_session_survives_failure.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py tests/test_ui_runs_serial_resilience.py -p no:xdist -o addopts= t=47s -> 39 passed
Pre-check[C1]: 9286a25d uv --directory D:/autoTesting/.worktrees/at888-session-survives-failure run pytest tests/test_session_survives_failure_live.py -k first-passes -p no:xdist -o addopts= t=103s -> 1 passed
Pre-check[C1]: 9286a25d uv --directory D:/autoTesting/.worktrees/at888-session-survives-failure run pytest tests/test_session_survives_failure_live.py -k first-fails -p no:xdist -o addopts= t=185s -> 1 passed
Pre-check[C1]: 9286a25d AUTOTESTER_HEADED_TESTS=1 uv --directory D:/autoTesting/.worktrees/at888-session-survives-failure run pytest tests/test_session_survives_failure_live.py -k headed -p no:xdist -o addopts= t=238s -> 1 passed
Pre-check[C2]: 9286a25d uv --directory D:/autoTesting/.worktrees/at888-session-survives-failure run pytest tests/test_session_survives_failure_live.py -k died -p no:xdist -o addopts= t=261s -> 1 passed
Pre-check[C2]: 9286a25d uv --directory D:/autoTesting/.worktrees/at888-session-survives-failure run pytest tests/test_session_survives_failure.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py tests/test_ui_runs_serial_resilience.py -p no:xdist -o addopts= t=47s -> 39 passed
Pre-check[C3]: 9286a25d uv --directory D:/autoTesting/.worktrees/at888-session-survives-failure run pytest tests/test_session_survives_failure.py tests/test_ui_runs_serial_resilience.py -p no:xdist -o addopts= t=24s -> 26 passed
Pre-check[C4]: 9286a25d uv --directory D:/autoTesting/.worktrees/at888-session-survives-failure run pytest tests/test_video_evidence.py -p no:xdist -o addopts= t=266s -> 2 passed
Pre-check[C5]: 9286a25d uv --directory D:/autoTesting/.worktrees/at888-session-survives-failure run pytest tests/test_video_masking_live.py -p no:xdist -o addopts= t=502s -> 3 passed

Also on 9286a25d: `uv --directory <worktree> run ruff check src tests scripts` -> All checks passed. `uv --directory <worktree> run autotester doctor` -> one violation, `stale-generated: docs/SNAPSHOT.md`, which is pre-existing (this unit does not touch `docs/SNAPSHOT.md`; the same violation is recorded on the t200a manifest); no violation names a file of this unit. File sizes: `video.py` 224, `run_case_pipeline.py` 243, both tests under 300; longest new function under 50 lines. Earlier affected-file run (before the last test-only commit, same source): `tests/test_session_survives_failure.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py tests/test_ui_runs_serial_resilience.py tests/test_video_parallel_sweep.py tests/test_browser.py` -> 55 passed, t=278s.

The machine was heavily loaded by other agents: real-browser tests spent 90-135 s in setup and up to 114 s in teardown on some runs (the same tests took 25-36 s on a quiet minute). That slowness is load, not the bug: a dead session fails at once ("Failed to open a new tab"), it never waits. The earlier stall was a background run of the three live tests whose output was buffered behind a pipe and that exceeded the tool's wait; no test hung. The live test file now carries a `faulthandler` hard deadline (280 s per test, dumps all stacks and exits) so a stuck browser fails instead of hanging.

## Falsifications (one per criterion; throwaway copy of src+tests outside the worktree, green before, red after, copy deleted)

Run with `PYTHONPATH=<copy>/src`, the worktree's Python, each anchor matching exactly once.

Falsification[C1]: removed the spare-page line in `end_case_video` (the original bug). Green 18 passed, t=17s. Red: `test_the_next_case_starts_on_a_live_page_after_any_outcome[_passes]` FAILED, t=106s. Live copy: `-k first-passes` FAILED on "a page outlives every case", t=133s.
Falsification[C2]: `_open_case_page` re-raises instead of restarting. Green 18 passed, t=58s. Red: `...after_any_outcome[_closes_own_page]` FAILED (1 failed, 2 passed), t=61s.
Falsification[C2b]: deleted the `events.append(...)` of the `session-restart` event. Green 18 passed, t=12s. Red: `test_a_restart_is_a_recorded_event_not_a_silent_retry` FAILED, t=45s.
Falsification[C2c]: `_with_events` returns the result without the events. Green 18 passed, t=3s. Red: `test_a_session_restart_travels_on_the_cases_result_through_both_pipeline_paths[run_and_grade_case]` FAILED, t=42s.
Falsification[C3]: deleted the latch check in `begin_case_video`. Green 18 passed, t=12s. Red: `test_an_unrestorable_session_raises_a_named_error_and_does_not_relaunch_per_case` FAILED, t=38s.
Falsification[C5]: deleted `self._page.add_init_script(_MASK_INIT_SCRIPT)`. Green 18 passed, t=48s. Red: `test_the_mask_init_script_is_on_the_page_of_every_case_including_after_a_restart` FAILED, t=37s.
Falsification[C4]: not separately mutated; the existing `test_video_evidence.py` and the live tests assert a non-empty `.webm` per case, and the C1 live falsification above fails them.

## Leftovers

- Mid-case browser death still ends THAT case ERRORED (it is the case's own failure; only the next case restarts). A case that closes its own last page in headed mode is that same path.
- The spare page records a blank video file per case in the scratch directory; swept at `close()`. A popup a case leaves open is not closed by `end_case_video` (unchanged behaviour).
- Session cookies (not persisted by the profile) are lost on a restart; login continuity after a restart comes from the saved profile only. The recorded event says so.
- `ui/routes_runs.py` and `stages/run_launcher.py` are untouched.
