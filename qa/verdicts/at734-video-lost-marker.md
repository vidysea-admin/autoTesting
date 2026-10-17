# Verdict - at734-video-lost-marker

Date: 2026-10-17 · Cycle checked: 0 · Bound to: D:/autoTesting/.worktrees/at734-video-lost-marker · Base 69ebfae7 (git merge-base HEAD master) · Head 5244f7a0 (code 895e5138)

## Check plan
Tier M (video.py + run_case_pipeline.py, no L trigger; lane not applicable, multi-file). Logic changed -> affected tests + the .8-4 floor (1 falsification per criterion, C1..C3, each in its own copy outside the worktree). No UI, no data, no prompt, no security trigger -> no browser/walk/audit. Single checker.

## Criteria (AT-734 `expected`, three clauses)
- C1 lost video is a typed marker the report can show: MET. video.py:226-228 `video.path()` failure -> `_video_lost()` (video.py:240-247) appends Evidence(label="video-lost", note names case + cause, scrubbed); observe_case (run_case_pipeline.py:188) drains it into `RawResult.evidence` for every verdict. Only caller of end_case_video is :187 (read).
- C2 guard the move, keep the real RawResult: MET. mkdir/replace guarded by `except OSError` (video.py:231-236); `test_the_real_rawresult_survives...` runs the issue's fixture (move raises PermissionError inside observe_case's finally): outcome/error of the real result survive, marker attached.
- C3 `__exit__` returns True only for Exception: MET (video.py:261-263); KeyboardInterrupt and SystemExit propagate.

## Evidence I produced
- `uv run pytest tests/test_video_lost_artifact.py` -> 6 passed. 10-file affected set (manifest list) -> 93 passed (79.7 s). `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> clean (2 pre-existing D-087 advisories).
- Falsification floor, each in its own copy of `git archive HEAD` (PYTHONPATH at the copy's src; unedited control copy green `6 passed` first):
  - C1 `return self._video_lost(...)` -> `return None`: red `assert [] == ['video-lost']` on test_a_video_path_that_cannot_be_read_is_marked_lost_not_video_off (1 failed, 5 passed).
  - C2 `except OSError` -> `except ZeroDivisionError`: red, PermissionError escapes end_case_video in both the move test and the RawResult-survives test.
  - C3 `return exc_type is None or issubclass(...)` -> `return True`: red `DID NOT RAISE KeyboardInterrupt` (1 failed, 5 passed).
- Step 4c diff read in full (video.py 29 lines, run_case_pipeline.py 1 line, new test file): nothing removed beyond the replaced lines, no file outside the manifest's list, no assert removed or weakened, no skip/xfail.

## Non-blocking findings (not criterion failures)
- PROPOSED low: an already-vanished temp file (`temp_path.exists()` false, video.py:233) and a post-move `final_path.exists()` false (video.py:238) still return None with no marker. The manifest declares this by design (sibling sweep case); AT-734 clause (1) names only the `video.path()` failure, so it is not judged here. Maker to file the ledger row (I wrote none: worktree ledger append risks an id collision with master).

FAILURES: none · defects_unit=0

Metrics: start=2026-10-17T19:30:00+05:30 end=2026-10-17T20:09:00+05:30 wall_min=39 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=2340 mutants=0 defects_unit=0 defects_6c=0
slow: copy of git archive tree (cp -r x3, large projects/ dir) 25 min
