# Verdict - crawl-live-hang (cycle 0)

Checked commit a5cdd4cb on wave/crawl-live-hang. Policy-Version: proportional-verification/2026-10-07.7. Tier L, single checker.
Issue-number note: the manifest's AT-787 collides with master's AT-787; the maker renumbers at close-out. Not judged here.

## Check plan

1. Each manifest criterion, evidenced from the diff and a re-run.
2. Watchdog safety in `tests/hard_timeout.py`: exactly which processes it kills; main-thread wake; timer cancellation; Windows behaviour.
3. Protected-test change: any assertion weakened, threshold lowered, skip/xfail added.
4. Run `tests/test_hard_timeout.py`; run the live file once at `AUTOTESTER_TIMING_SCALE=2` under `timeout 900` with `.work/suite.lock`.
5. Falsification in throwaway copies (scratchpad, never the worktree).
6. `ruff check src tests scripts` and `autotester doctor`.

## Verdict: FAIL

The unit meets its stated goal (the live file no longer hangs, no assertion is loosened). It fails on check 2: the watchdog kills every direct child of the pytest process, with no filter, and that set is not provably "the Playwright driver and Chromium this test started". Per the brief, a kill of a process the watchdog did not start is a FAIL (data-loss defect in changed code). The fix is small (see Required fixes).

## Evidence

### Findings that decide the verdict

F1 (FAIL) `tests/hard_timeout.py:98-99` (`_trip`: `for child in _child_pids(os.getpid()): _kill_tree(child)`), with `_kill_tree` at :73-77 using `taskkill /F /T` (whole subtree).
- The kill set is all direct children of the pytest PID at trip time. Nothing records which PIDs the test or Playwright started, and nothing checks image name or creation time.
- Demonstrated: in a throwaway probe, an unrelated `python -c "time.sleep"` child started BEFORE `hard_timeout` was armed was killed when the watchdog tripped (`P1 innocent alive after trip: False`). The unit's own `test_hard_timeout.py:35-44` relies on exactly this (it kills a child the watchdog never started).
- Measured on this host for the plain sequential case: during a live Playwright session the only direct child of the python process is one `node.exe` (the driver); Chromium is a grandchild reached through `/T`. So today, in a sequential pytest, the set is just the driver. That is true by observation of this host, not by construction. The kill can also reach: a subprocess leaked by an earlier test or fixture in the same run (several tests Popen, e.g. `tests/test_core.py:154`, `tests/test_mc_sessionstart_loop_status.py:239`); and, on Windows, a stale entry whose recorded parent PID equals the pytest PID after PID reuse (Windows never updates ParentProcessID; this host runs dozens of orphaned python/headless-shell processes), because the Toolhelp walk at :31-56 matches on `th32ParentProcessID` alone.
- `pytest-xdist` is not a dependency; under it each worker uses its own `os.getpid()`, so a worker would not kill the controller. Under `uv run`, `uv` is the parent of pytest, not a child, so it is not in the set. Neither is the problem; the unfiltered match is.

F2 (Warning, same file) `_trip` runs kill and wake in sequence with no try/finally (:95-101). If `_child_pids` or `_kill_tree` raises (e.g. a Toolhelp failure: `Process32FirstW`/`CloseHandle` have no `argtypes`, and an INVALID_HANDLE_VALUE snapshot makes ctypes raise), the exception ends the Timer thread and `_wake_main_thread()` is never reached. Demonstrated: with `_child_pids` patched to raise, a `time.sleep(40)` body under a 2 s bound ran the full 40.09 s (the watchdog did not free it). The goal "never hangs" is then lost for any body that depends on the wake.

F3 (Note) `_wake_main_thread` uses the private CPython symbol `ctypes.pythonapi._PyOS_SigintEvent` (:84-87). It works on the CPython 3.11 used here; an AttributeError on another version has the same effect as F2.

F4 (Note) A timer firing in the microsecond window after `state["done"]` is set but before `Timer.cancel()` can still kill children of a passing test. `Timer.run` checks `finished` before calling `_trip`, so the window is tiny.

### Items that pass

- Thread safety / cancel: 50 normal completions leave `threading.active_count()` unchanged (no leaked timer threads). The decorator form re-creates the generator context per call, so each call gets a fresh timer. `interrupt_main` plus the SIGINT event frees a sleeping body on Windows (test_hard_timeout sleeping case, and the 30 s copy below).
- No assertion changed: the diff of `tests/test_crawl_inventory_live.py` is imports, `FULL` moved above `WATCHDOG_S`, the preflight moved into `_require_chromium()` with a per-file cached verdict, and the decorator. `FULL` values are identical; no new skip/xfail. The preflight still skips with `chromium unavailable: <ExcName>` (same text); `importorskip` still runs per call.
- Design rules: `hard_timeout.py` 128 lines; functions under 50 lines; doctor clean.

### Commands run

- `uv run pytest tests/test_hard_timeout.py` (no `-q`): `4 passed in 5.13s`.
- `uv run ruff check src tests scripts`: `All checks passed!`. `uv run autotester doctor`: `doctor: clean`.
- Live file, `AUTOTESTER_TIMING_SCALE=2`, `timeout 900`, lock taken at 20:04:50 and released after: `2 passed in 335.95s (0:05:35)`, exit 0. It finished with a summary line.
- Falsification, live file copy with the decorator removed and `time.sleep(10**6)` injected after `session.start()`: ran until the outer `timeout 100` killed it (exit 124, 101 s). Hang reproduced.
- Falsification, same sleep with the decorator kept and `WATCHDOG_S = 30`: tripped, `WatchdogTripped: inventory crawl exceeded its 30s hard bound`, `1 failed ... in 32.57s`.
- Falsification of `test_hard_timeout.py` in copies: removing the kill step (`for child ... _kill_tree`) made the child-wait test hang past the outer `timeout 100` (exit 124; the faulthandler dump shows the main thread in `subprocess._wait`). Removing the wake step (`_wake_main_thread()` call) made the sleeping-body test hang past `timeout 150` (exit 124). Both are red. (One earlier run of the no-kill copy printed a `.` before also hitting the outer timeout at exit; the instrumented rerun hung inside the test. I treat the instrumented run as the evidence.)
- Probe (throwaway, `scratchpad/clh/probe/test_probe.py`): P1 FAILED (unrelated child killed), P2 passed (no thread leak), P3 FAILED (sleeping body not woken when child lookup raises).
- Children of a python process during a live Playwright session on this host: `['node.exe']` only (before: none; after close: none).

The full suite was not run (policy; the pre-push integration check runs it).

## Required fixes (cycle 1)

1. Kill only what this run provably started: snapshot the direct children when the timer is armed, or at `session.start()`, and in `_trip` kill only children that are new since then AND whose creation time is not earlier than the arm time (this also removes PID-reuse orphans). Alternatively filter by image name (`node.exe` / playwright driver) plus creation time. Keep the `test_hard_timeout.py` child case working by having it spawn its child inside the armed window, and add a case that an earlier unrelated child survives a trip.
2. Wrap the child lookup/kill in `try/finally` so `_wake_main_thread()` always runs; add a test with a lookup that raises and a sleeping body.
3. Optionally guard `_PyOS_SigintEvent` with `getattr` and fall back to `interrupt_main` alone.

Cycle checked: 0

Metrics: start=2026-10-07T14:05:00Z end=2026-10-07T15:15:00Z wall_min=70 agent_min=unavailable blocked_min=30 suite_runs=0 repeat_runs=1 mutations=4 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-07.7

PROPOSED-ISSUE: tests/hard_timeout.py `_trip` kills every direct child of the pytest process without filtering by PID set, image name or creation time (can kill a leaked/unrelated child or a PID-reuse orphan); snapshot-and-filter it. (severity: high, serves: suite safety)
PROPOSED-ISSUE: tests/hard_timeout.py `_trip` does not wake the main thread if the child lookup or kill raises; wrap in try/finally and test it. (severity: medium)
PROPOSED-ISSUE: Chromium `Browser.close()` takes 48-127 s per call on this host when it is busy (sibling sessions' browsers, CPU about 78%); a per-call cost that dominates every live-browser test. Diagnose (browser-process count, close vs kill fallback, a close timeout in `BrowserSession.close`). (severity: medium)
PROPOSED-ISSUE: Decision for Umesh, not an agent: raise the default crawl bound (`FULL.wall_clock_s = 240 * timing_scale()`) or default `AUTOTESTER_TIMING_SCALE` above 1 for live-browser files; at scale 1 on a saturated host the crawl test still ends `STOPPED_BOUND` (AT-757 flake) although it no longer hangs. (severity: low, owner: Umesh)
PROPOSED-ISSUE: Other live-browser test files have no watchdog; adopt `hard_timeout` there once the kill scope is fixed. (severity: low)
