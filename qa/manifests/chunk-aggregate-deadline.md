# Manifest — chunk-aggregate-deadline

**Contract:** qa/contracts/video-learning.md (VL1 shell-out boundary)
**Goal task:** none (ledger-driven unit)
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Dual check:** no
**Persona walk:** skip (backend-only: ffmpeg shell-out in the INGEST stage, no screen or flow changes)
**Issues addressed:** ISS-at639-1
**Executor:** claude-sonnet-subagent
**Executor rationale:** two-file S unit localised to file:line by the m4 fact pass.

## What changed
- `src/autotester/media/chunks.py`:35-43 — new `TOTAL_TIMEOUT_S = 1800.0` (whole-loop wall-clock ceiling) with its reasoning docstring.
- `src/autotester/media/chunks.py`:127-139 — `encode_chunks` takes `started = time.monotonic()`, raises `subprocess.TimeoutExpired` before a cut when the budget is spent, and gives each cut `timeout=min(CHUNK_TIMEOUT_S, remaining)`. `media_prep.prepare` already turns that into UnreadableRecording (no media.json). `import time` added at :16.
- `tests/test_media_shellout.py`:191-223 — `test_a_forty_minute_recording_whose_every_cut_is_slow_hits_a_total_deadline`.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: S (single criterion, two files, no security/UI trigger)
Base / checked state: base 69ebfae7, head a171bf50, worktree clean after commit
Gate answers: none (no new module; qa/gates/new-module-authorization.md not needed, no new src file)
Affected tests / full-suite trigger: tests/test_media_shellout.py, tests/test_media_prep.py; no full-suite trigger. Builder ran no full suite.
Pre-check[C1]: a171bf50 uv run pytest tests/test_media_shellout.py tests/test_media_prep.py -> 20 passed (also ruff check src tests scripts: All checks passed; autotester doctor: clean) t=3 blobs=tests/test_media_shellout.py:7a366d9,tests/test_media_prep.py:56939a3
Metrics: start=2026-10-17T00:00:00Z end=2026-10-17T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=3 mutants=1 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_media_shellout.py tests/test_media_prep.py` → expected: 20 passed
- `uv run ruff check src tests scripts` → expected: All checks passed
- `uv run autotester doctor` → expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest: `20 passed, 1 warning in 2.73s`
- ruff: `All checks passed!`
- doctor: `doctor: clean`

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 | a 13-chunk plan whose every cut succeeds after 800 fake seconds raises TimeoutExpired once the 1800s total is spent, and each cut's timeout never exceeds CHUNK_TIMEOUT_S | tests/test_media_shellout.py::test_a_forty_minute_recording_whose_every_cut_is_slow_hits_a_total_deadline | in a throwaway copy outside the worktree (scratchpad/fals), delete the `if remaining <= 0: raise ...` guard and revert `timeout=min(CHUNK_TIMEOUT_S, remaining)` to `timeout=CHUNK_TIMEOUT_S` | green@a171bf50: `20 passed` (shellout+prep). red with fix reverted: `E       Failed: DID NOT RAISE TimeoutExpired` / `FAILED tests/test_media_shellout.py::test_a_forty_minute_recording_whose_every_cut_is_slow_hits_a_total_deadline` / `1 failed, 9 passed`. Before the fix existed the test also failed (AttributeError on the missing `chunks_mod.time`, TDD red). |

## Live browser evidence
Not UI-touching — no surface changed (changed paths: src/autotester/media/chunks.py, tests/test_media_shellout.py).

## Status: ready-for-check
