# Manifest - crawl-live-hang (AT-803 tests/test_crawl_inventory_live.py never finishes under load)

Contract: qa/contracts/core-invariants.md (no assertion removed; C2 file/function caps); suite-health unit raised by the coordinator 2026-10-07; issue AT-803 (qa/issues.jsonl).
Goal task: none (suite health, blocks other units' checkers)
Policy-Version: proportional-verification/2026-10-07.7
Fix cycle: 1
Status: checked-PASS
Tier: L - protected test change (a skip precondition is now cached once per file; a watchdog wraps the crawl).
Base: a77ed746b37b31d6777f9e56f362474acfcd5c83 (origin/master), branch wave/crawl-live-hang
Source: see `git log wave/crawl-live-hang -1` (the commit that adds this manifest)

## Root cause

No code deadlock. The file is unbounded and the host makes every step slow:

- `tests/test_crawl_inventory_live.py:55-60` (base) ran a full `sync_playwright()` launch+close preflight in EVERY test, then `BrowserSession.start()/close()` (`src/autotester/browser/session.py:88-117`). On a busy host (CPU ~78%, 18 headless-shell processes from sibling sessions) `Browser.close()` measured 48 s, 56 s, 67 s, 123 s, 127 s per call (probe3/probe4) and 0.6 s on a quiet moment. One test therefore paid 1-3 minutes of pure close time before and after the crawl.
- The crawl's own bound `FULL.wall_clock_s = 240 * timing_scale()` (`tests/test_crawl_inventory_live.py:53`) is hit at scale 1 (settle waits at `src/autotester/browser/session.py:223-237`, `explore_*`), so test one fails with `STOPPED_BOUND` / `wall_clock_s` after 240 s and the file takes 285-600 s. Test one measured 349 s (pass), 285 s, 502 s, 599 s (fail). `timeout 600` in a full-suite run kills it (exit 124, as at base af8f3218).
- Nothing bounded the body: a Playwright call blocked on a dead driver, or any `join()`, held the suite until the outer kill. pytest-timeout is not a dependency.

faulthandler at 150 s showed the main thread inside the Playwright greenlet's asyncio `_poll` (`playwright/sync_api/_context_manager.py:56`), waiting on the browser.

## What was built

- `tests/hard_timeout.py` (new, test-only, one job; precedent `tests/timing_scale.py`): `hard_timeout(seconds, label)`, usable as a context manager or decorator. On expiry: dumps all thread tracebacks to stderr, kills the pytest process's direct children (Playwright driver and Chromium under it; Toolhelp snapshot via ctypes on Windows, `pgrep -P` elsewhere), and wakes the main thread (`interrupt_main` plus the interpreter's SIGINT event, because on Windows `interrupt_main` alone does not wake a waiting `time.sleep`). The body then raises `WatchdogTripped` (an AssertionError). Normal bodies pay one cancelled timer.
- `tests/test_hard_timeout.py` (new, 4 cases): quick body untouched, an error inside the bound propagates unchanged, a sleeping body trips, a body blocked on a child process is freed by killing the child.
- `tests/test_crawl_inventory_live.py` (edited in place): imports `hard_timeout`; `_crawl_inventory` is decorated `@hard_timeout(WATCHDOG_S, "inventory crawl")` with `WATCHDOG_S = 600 * timing_scale()` (line 57, 76); the launch+close preflight moved into `_require_chromium()` (line 61) and runs once per file (cached verdict) instead of once per test; `FULL` moved above it (same value, unchanged).
- Protected-change justification: no assertion removed or loosened; `FULL` bounds identical; the skip is the same skip (`chromium unavailable`, now raised from a cached verdict), it just no longer pays a second launch+close in the second test. A launch failure still skips with the precondition named.
- Product code untouched; none of the owned-by-others files touched.
- `qa/issues.jsonl`: row AT-803 appended (open).

## Fix cycle 1 (checker FAIL at cycle 0, qa/verdicts/crawl-live-hang.md)

- Issue id renamed AT-787 -> AT-803 (AT-787 is T-178's row on master); row, manifest and this commit use AT-803. The cycle-0 commit message still says AT-787.
- tests/hard_timeout.py: `hard_timeout` snapshots the direct children (PID plus creation time: Toolhelp + GetProcessTimes on Windows, `pgrep` + `ps -o lstart=` elsewhere) when armed; `_trip` kills only children not in that snapshot and logs killed and spared PIDs to stderr.
- `_trip`: dump/kill steps run in `try/except Exception` (logged), and `_wake_main_thread()` is in `finally`, so a failing lookup or kill still wakes the main thread.
- tests/test_hard_timeout.py: child-wait test now starts its child inside the watchdog; new `test_a_child_started_before_arming_survives_the_trip` and `test_the_main_thread_still_wakes_when_the_kill_step_raises` (6 cases total).
- Falsified in throwaway copies: dropping the `not in before` filter -> bystander test FAILED (1 failed, 5 passed); `_trip` without try/finally and a raising kill -> the file hung until the outer `timeout 600` killed it (no summary line); restored -> 6 passed in 9.5 s. The live file was not re-run (checker ran it at scale 2).
- ruff: All checks passed! doctor: 1 violation, `stale-generated: docs/SNAPSHOT.md` (decision list D-070/071 vs D-075/076), present on origin/master independent of this unit; not regenerated here.

## How to verify

```
uv run pytest tests/test_hard_timeout.py                         # 4 passed in ~5 s
timeout 900 uv run pytest tests/test_crawl_inventory_live.py     # finishes with a summary line; at scale 1 on a busy host test one may still fail STOPPED_BOUND (AT-757)
AUTOTESTER_TIMING_SCALE=2 timeout 900 uv run pytest tests/test_crawl_inventory_live.py   # 2 passed
uv run ruff check src tests scripts
uv run autotester doctor
```

## Falsification rows

| claim | check | falsifier / result |
|---|---|---|
| a blocked live crawl fails fast | throwaway copy of the test (`WATCHDOG_S = 30`) with `time.sleep(10**6)` injected after `session.start()` | tripped at 30 s: `WatchdogTripped: inventory crawl exceeded its 30 s hard bound`, 37 s total |
| a crawl blocked inside Playwright fails fast | same copy with `session.page.wait_for_timeout(10**9)` | tripped, 37 s total |
| the watchdog is what does it | same sleep copy with the decorator removed | hung until the outer `timeout 90` killed it (exit 124, 91 s) |
| helper behaviour | tests/test_hard_timeout.py | 4 passed; earlier draft using a PowerShell child lookup hung 600 s in the sleeping-body case and a plain `interrupt_main` did not wake `time.sleep` on Windows (both fixed, see helper docstring) |
| the file always finishes | 3 runs alone, `timeout 900` | see Evidence |
| no assertion loosened | `git diff` of tests/test_crawl_inventory_live.py | only imports, `FULL` moved, preflight cached, decorator |

## Evidence

- Three runs of the file alone at default scale, each under `timeout 900`, on a host at ~78% CPU: run1 exit 1, `1 failed, 1 passed in 285.90s`; run2 exit 1, `1 failed, 1 passed in 502.82s`; run3 exit 1, `1 failed, 1 passed in 598.81s`. All three finished with a summary line (no hang, no exit 124). The failure in each is `test_a_logged_in_crawl_maps_every_route...`: `AssertionError: wall_clock_s`, `STOPPED_BOUND` instead of `COMPLETED`, the AT-757 load flake (the crawl needs more than 240 s of wall clock when Chromium is this slow), not a hang.
- One run at `AUTOTESTER_TIMING_SCALE=2`: `2 passed in 393.84s`.
- Forced hangs: rows above.
- `uv run ruff check src tests scripts`: All checks passed! `uv run autotester doctor`: doctor: clean.
- Full suite not run (brief; the suite lock was not needed).

## Open items

- At scale 1 on a saturated host the 240 s crawl bound still produces `STOPPED_BOUND` (AT-757's design: sweeps run with `AUTOTESTER_TIMING_SCALE=2`). This unit makes the failure bounded and fast to report, it does not make a slow crawl faster. A checker may judge whether a higher default is warranted; it is Umesh's call, not made here.
- Other live-browser test files have no watchdog; `tests/hard_timeout.py` is ready for them to adopt.
- Chromium close taking 1-2 minutes on this host is an environment problem (sibling sessions' browsers, CPU load), not diagnosed further.

Metrics: start=2026-10-07T13:00:00Z end=2026-10-07T14:25:00Z wall_min=85 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=5 mutations=3 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-07.7

Issue id renumbered AT-803 → AT-809 (collision), 2026-10-07
