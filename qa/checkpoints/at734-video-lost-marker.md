# Checkpoint - at734-video-lost-marker (checker, cycle 0)
Code hash: src/autotester/browser/video.py + stages/run_case_pipeline.py + tests/test_video_lost_artifact.py at 895e5138; uv.lock unchanged vs base; env: Windows, worktree .venv.
- pytest tests/test_video_lost_artifact.py (6 collected) -> 6 passed
- pytest 10 manifest files (93 collected) -> 93 passed
- ruff check src tests scripts -> pass; autotester doctor -> clean
- falsify C1/C2/C3 in copies of git archive HEAD -> red on named tests; control green
Result: PASS, cycle 0, checker claude-sonnet-subagent.
