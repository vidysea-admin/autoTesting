# Verdict - crawl-live-hang (cycle 1)

Cycle checked: 1
Checked commit deaf20d1 on wave/crawl-live-hang. Policy-Version: proportional-verification/2026-10-07.7. Tier S/M repair check, single checker. Cycle-0 verdict kept at qa/verdicts/crawl-live-hang.r0-1.md.

## Verdict: PASS

Both cycle-0 criteria are met. Only these two were re-checked, plus the AT-803 id consistency.

## Criterion 1 - the watchdog kills only children born after arming: PASS

- Read `git diff a5cdd4cb deaf20d1 -- tests/hard_timeout.py` and the final file myself. `hard_timeout()` snapshots `before = set(_children(os.getpid()))` at arm time (tests/hard_timeout.py:147-150); each child is `(pid, creation stamp)`: Toolhelp + `GetProcessTimes` on Windows (`_windows_created`), `pgrep` + `ps -o lstart=` on POSIX. `_trip` kills `[c for c in _children(os.getpid()) if c not in before]` (line ~133); the killed and spared PIDs are logged. The match is on the pair, so a reused PID with a new creation time is not spared.
- Falsification, throwaway copy in the scratchpad (m1, bound tree untouched): filter removed (`victims = [c for c in _children(os.getpid())]`). Result: `1 failed, 5 passed`; FAILED `test_a_child_started_before_arming_survives_the_trip`, stderr `WATCHDOG: killed pids [30488]; spared [30488]`. RED as required.

## Criterion 2 - the main-thread wake runs in a `finally`: PASS

- `_trip` (lines ~125-147): dump/kill in `try`, `except Exception` logs, `finally: if not state["done"]: _wake_main_thread()`. A raising lookup or kill cannot skip the wake.
- Falsification, throwaway copy (m2): `finally` and `except` removed so the wake sits after the kill step, with `test_the_main_thread_still_wakes_when_the_kill_step_raises` (kill monkeypatched to raise OSError). Result: pytest hung with no result line until my own `timeout 80` killed it (exit 124; the test's bound is 2 s + 120 s slack, the hang is the bound failure the real code prevents). RED as required. No stray sleeper processes left (checked by command line).

## Re-run in the bound tree

- `uv run pytest tests/test_hard_timeout.py -p no:xdist`: `6 passed in 9.49s`.
- `uv run ruff check src tests scripts`: All checks passed!
- `uv run autotester doctor`: 1 violation, `stale-generated: docs/SNAPSHOT.md` only, the known pre-existing item (not a FAIL).
- Live file and full suite not re-run (brief: two criteria only).

## Issue id consistency

AT-803 is the id in qa/issues.jsonl (feature crawl-live-hang, status open) and throughout the manifest's cycle-1 section; AT-787 remains only as T-178's own row on master and as the historical note in the manifest. The cycle-0 commit message still says AT-787 (disclosed by the maker, not rewritable). Close-out of the AT-803 row (status/verified_date) is the maker's/ledger step, not touched here.

Metrics: start=2026-10-07T15:20:00Z end=2026-10-07T15:30:00Z wall_min=10 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=2 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7

Issue id renumbered AT-803 → AT-809 (collision), 2026-10-07
