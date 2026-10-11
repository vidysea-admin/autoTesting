# Checkpoint: t197-video-pointers, cycle 1, coordinator B (complete, no resume owed)

Verdict: FAIL (qa/verdicts/t197-video-pointers.r1.b.md). Policy-Version: proportional-verification/2026-10-10.9.

Evidence identity
- Command and scope: real `autotester.cli.app` (`ingest review`) with wrapped mock provider `wm`, synthetic ffmpeg video, scratch data root, projects zzr1b and zzr1b2; run kinds 1-9, caps, JSON exits, pointer limits (tables in qa/evidence/t197-video-pointers-r1-B/).
- Affected pytest: 195 passed, from inside the worktree with its own `.venv`; ruff check src tests scripts: 1 error (tests/test_video_pointers.py:199 E501); autotester doctor clean.
- Code hash: branch wave/t197-video-pointers head 0dcbbfa58ac552f0d41918580b2cf90b743501a1, tree D:/autoTesting/.worktrees/check-t197-r1-b (detached, left in place).
- Environment: Windows 11, worktree `.venv`, `autotester.__file__` inside the tree; ffmpeg on PATH; synthetic AUTOTESTER_APPROVAL_KEY in a gitignored worktree `.env` (removed at the end).
- Result: TV10 storage, TV7.3, TV7.4 cap, TV1 limits, human status kept: reproduced met. JSON on every exit and ruff: not met.
- Attribution: coordinator B, claude-sonnet-subagent.

Reusable on a repair: the run-kinds, caps, pointer-limit and falsification tables stay valid while src/autotester/cli_video_review.py, media/redacted.py, stages/video_review.py, stages/video_pointers.py and .gitignore are unchanged except for the JSON/exit-code hunks named in the verdict.
