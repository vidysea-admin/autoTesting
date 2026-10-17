# Verdict — chunk-aggregate-deadline

Date: 2026-10-17
Cycle checked: 0
Bound to: D:/autoTesting/.worktrees/chunk-aggregate-deadline (base 69ebfae7 = `git merge-base HEAD master`, head 827f464c, product head a171bf50)
Policy-Version: proportional-verification/2026-10-15.12

## Check plan
Single criterion C1 = ISS-at639-1 (aggregate ceiling over the `encode_chunks` loop). Logic changed in one media module, so: affected tests + falsification floor + step 4c diff read. Quick lane is off (`qa/adapter.json` has no `lane.enabled`), so this is a normal S check (`lane=normal`). No UI, security, auth, data-write or prompt trigger. Diff since base: `src/autotester/media/chunks.py`, `tests/test_media_shellout.py`, the manifest.

VERDICT: PASS
SCOREBOARD: 1/1 criteria met, core-invariants none-touched
TIER: S (one product file, one new constant and one guard in a for-loop, no L trigger; concurrency/timing keyword is a wall-clock deadline in a subprocess-timeout path, not shared state)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced
LIVE-BROWSER: not-applicable (src/autotester/media/chunks.py, tests/test_media_shellout.py)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence (all run by the checker in this check)
- C1 vs issue text: `chunks.py:35-43` adds `TOTAL_TIMEOUT_S = 1800.0`; `:127-133` takes `started = time.monotonic()`, raises `subprocess.TimeoutExpired` before a cut once `remaining <= 0`, and `:139` gives each cut `timeout=min(CHUNK_TIMEOUT_S, remaining)`. A 13-chunk plan at 900 s each (~3.25 h) is now capped at ~1800 s, the issue's own fix direction.
- `media_prep.prepare` degradation, read at `stages/media_prep.py:78-84`: `except Exception` around `encode_chunks` -> `raise UnreadableRecording(...)` before `store.save_media_prep`, so no media.json. `TimeoutExpired` is an `Exception`. Confirmed.
- Last-cut overshoot: its own `timeout=min(900, remaining)` raises `TimeoutExpired`, which the existing `except (OSError, SubprocessError)` at `chunks.py:141` catches (unlinks the half-written chunk, re-raises). The guard-raise path writes no chunk. Fine.
- `uv run pytest tests/test_media_shellout.py tests/test_media_prep.py` -> 20 passed (5.1 s, includes 1 DeprecationWarning from starlette, unrelated).
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean.
- FALSIFY (copy outside worktree, `git archive HEAD` in scratchpad `fals-cad`): `test_a_forty_minute_recording_whose_every_cut_is_slow_hits_a_total_deadline` green (1 passed); after deleting the `if remaining <= 0: raise` guard and reverting `timeout=min(...)` to `timeout=CHUNK_TIMEOUT_S` -> red `E Failed: DID NOT RAISE TimeoutExpired`, `1 failed`. Named assertion, not an import error.
- DIFF-SCOPE (4c): nothing removed other than the one replaced `timeout=` line; no file outside the manifest's declared two plus the manifest itself.

## Notes (non-blocking)
- Manifest Metrics carries placeholder start/end times (`00:00:00Z`); process note only, not filed.
- `TOTAL_TIMEOUT_S=1800` is a judgement, like the 900 s per-chunk bound; the docstring says so. A slow-but-working ffmpeg on a recording longer than ~60 min of 3-min chunks could now be cut short; the per-chunk docstring's "generous" reasoning is the mitigation. Question, not a finding.

EXPLANATION: The per-chunk bound is now wrapped by a monotonic whole-loop deadline and each cut is clamped to the time remaining. The new fake-clock test proves it and goes red when the fix is reverted. prepare already degrades any exception from encode_chunks to UnreadableRecording with no media.json.
Metrics: start=2026-10-17T00:00:00Z end=2026-10-17T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=300 mutants=0 defects_unit=0 defects_6c=0
