# Manifest — at734-video-lost-marker

**Unit:** AT-734, `browser/video.py` silent paths. One criterion per clause of the issue's `expected`: C1 lost video is a typed marker, C2 guarded move keeps the real RawResult, C3 `_ignore_close_errors.__exit__` swallows `Exception` only.
**Contract:** `qa/contracts/run-video.md` (T-191, AT-587)
**Goal task:** none
**Status:** checked-PASS (qa/verdicts/at734-video-lost-marker.md, cycle 0)
**Policy-Version:** proportional-verification/2026-10-15.12
**Tier:** M (multi-file behaviour: `browser/video.py` + `stages/run_case_pipeline.py`); single checker
**Dual check:** no
**Fix cycle:** 0
**Date:** 2026-10-17
**Issues addressed:** AT-734
**Executor:** claude-sonnet-subagent
**Executor rationale:** build unit sized for one context; no external executor worthy.

## What changed
- `src/autotester/browser/video.py:204-238` (`end_case_video`) -- `video.path()` failure and the mkdir/replace move are now caught (`Exception` / `OSError`) and call the new `_video_lost()`; neither raises out of the caller's `finally`.
- `src/autotester/browser/video.py:240-247` (`_video_lost`, new method on the existing mixin) -- appends `Evidence(kind=DOM, label="video-lost", path=<scrubbed note naming case + cause>)` to `_session_events`, the existing AT-888 recorded-event list.
- `src/autotester/browser/video.py:261-263` (`_ignore_close_errors.__exit__`) -- returns True only when `exc_type is None or issubclass(exc_type, Exception)`; `KeyboardInterrupt`/`SystemExit` propagate.
- `src/autotester/stages/run_case_pipeline.py:188` (`observe_case`, same line, still 296 lines) -- after the `finally`, drains `_take_session_events(session)` again so the marker lands in `RawResult.evidence` with the restart events.
- `tests/test_video_lost_artifact.py` (new, 137 lines) -- 6 tests, fake context/page/video, no browser.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: M, multi-file behaviour, no security/auth/tenancy/prod-write trigger
Base / checked state: base 69ebfae7, code at 895e5138 (clean tree before manifest)
Gate answers: none (no gate touched)
Affected tests / full-suite trigger: new `tests/test_video_lost_artifact.py` plus every existing file that imports `browser/video.py` or `run_case_pipeline.py`: `test_session_survives_failure.py`, `test_video_parallel_sweep.py`, `test_video_duration_cap.py`, `test_run_case_pipeline.py`, `test_run_case_pipeline_resilient.py`, `test_run_budget_judge_time.py`, `test_agent_fallback.py`, `test_ui_runs_serial_resilience.py`, `test_team_run_launcher.py` (10 files, 93 passed). No full suite (builder runs none). No safe-fallback or contract-line trigger.
Pre-check[C1]: 895e5138 uv run pytest tests/test_video_lost_artifact.py::test_a_video_path_that_cannot_be_read_is_marked_lost_not_video_off -> 1 passed t=16 blobs=tests/test_video_lost_artifact.py:65a7bcd
Pre-check[C2]: 895e5138 uv run pytest tests/test_video_lost_artifact.py::test_the_real_rawresult_survives_a_lost_video_and_carries_the_marker -> 1 passed t=12 blobs=tests/test_video_lost_artifact.py:65a7bcd
Pre-check[C3]: 895e5138 uv run pytest tests/test_video_lost_artifact.py::test_close_guard_swallows_exceptions_but_not_interrupts -> 1 passed t=15 blobs=tests/test_video_lost_artifact.py:65a7bcd
Metrics: start=2026-10-17T17:00:00+05:30 end=2026-10-17T17:30:00+05:30 wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12

## How to verify (commands + expected)
- `uv run pytest tests/test_video_lost_artifact.py` -> expected: 6 passed
- `uv run pytest tests/test_session_survives_failure.py tests/test_video_parallel_sweep.py tests/test_video_duration_cap.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py tests/test_run_budget_judge_time.py tests/test_agent_fallback.py tests/test_ui_runs_serial_resilience.py tests/test_team_run_launcher.py` -> expected: all pass (93 with the new file)
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- new file + 9 existing files: `93 passed, 1 warning in 44.66s`
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean` (2 advisory D-087 findings, non-blocking, pre-existing)

## Capability coverage (each new claim -> its isolating falsification)
Falsified in a throwaway copy outside the worktree (`PYTHONPATH` at the copy's `src`), one edit per criterion, then restored.

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | an unreadable `video.path()` records a `video-lost` event instead of the 'video off' `None` | `tests/test_video_lost_artifact.py::test_a_video_path_that_cannot_be_read_is_marked_lost_not_video_off` | `return self._video_lost(case_id, "recording path unreadable", exc)` -> `return None` | green: `6 passed`; after edit: `FAILED ...::test_a_video_path_that_cannot_be_read_is_marked_lost_not_video_off` -- `AssertionError: assert [] == ['video-lost']`; restored: `6 passed` |
| C2 | a move that raises (PermissionError) is guarded; the real `RawResult` survives and carries the marker | `...::test_a_move_that_raises_does_not_escape_end_case_video_and_marks_the_video_lost` and `...::test_the_real_rawresult_survives_a_lost_video_and_carries_the_marker` | `except OSError as exc:` -> `except ZeroDivisionError as exc:` (move unguarded) | green: `6 passed`; after edit: both FAILED with `PermissionError: [WinError 5] Access is denied` / `PermissionError: denied` escaping `end_case_video`, `2 failed, 4 passed`; restored: `6 passed` |
| C3 | `_ignore_close_errors` swallows `Exception` only | `...::test_close_guard_swallows_exceptions_but_not_interrupts` | `return exc_type is None or issubclass(exc_type, Exception)` -> `return True` | green: `6 passed`; after edit: `FAILED ...::test_close_guard_swallows_exceptions_but_not_interrupts` -- `Failed: DID NOT RAISE KeyboardInterrupt`, `1 failed, 5 passed`; restored: `6 passed` |

Red-first (TDD): before the fix the new file ran `4 failed, 2 passed` (the move test and pipeline test with `PermissionError`, the path test with `assert [] == ['video-lost']`, the guard test with `DID NOT RAISE KeyboardInterrupt`).

## Live browser
Not UI-touching (fake context/page, no browser; the headed real-browser coverage stays in the existing `*_live.py` tests, unchanged).

## Notes
- Design choice: the marker travels on the existing `_session_events` list (AT-888), label `video-lost`, so the pipeline needed a one-expression change and no schema or signature change. `end_case_video` still returns `str | None`; callers are unchanged.
- Unchanged by design: a temp file already gone (`temp_path.exists()` false) still returns `None` silently -- that is the sibling-sweep case `tests/test_video_parallel_sweep.py` documents; AT-734 does not name it.
- A lost-video marker is attached whatever the verdict; a PASS case's video would have been discarded anyway, so the marker there is a cheap note, not a failure.
