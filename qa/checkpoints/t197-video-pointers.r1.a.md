# Checkpoint — t197-video-pointers coordinator A, cycle 1 (repair)
Attribution: checker coordinator A, verdict qa/verdicts/t197-video-pointers.r1.a.md, evidence qa/evidence/t197-video-pointers-r1-A/
Code: tree D:/autoTesting/.worktrees/t197-video-pointers head 0dcbbfa5 (product c726cfda, tests 802c72c9); repair base 3d0be650; whole-unit base 09828f2d
Environment: Windows 11, Python 3.11.15 (uv), ffmpeg on PATH, autotester.__file__ inside the tree; pyproject/uv.lock of the tree; no .env value read; approval key in scripts was a throwaway string

| Check | Command / scope | Result |
|---|---|---|
| Affected set 1 | pytest tests/test_video_pointers.py test_video_review.py _gates _redaction _guards _cleanup (118 collected) | 118 passed 1021 s |
| Affected set 2 | pytest tests/test_cli_video_review.py _exits test_cli_advice_resolves test_approve_cli test_cli_surface (135) | 135 passed 253 s |
| Ruff | uv --directory <tree> run ruff check src tests scripts | FAIL rc=1 E501 tests/test_video_pointers.py:199 |
| Doctor | uv --directory <tree> run autotester doctor | clean |
| Cleanup attacks | scripts/cleanup_attack*.py (success, ProviderError, RuntimeError, KeyboardInterrupt, SystemExit, no windows, locked file, junction) | clean except locked/junction residuals (P4, P5) |
| JSON attacks | scripts/json_attack*.py | click parse errors and provider exceptions give no document (P2, P3) |
| Pointer limits | scripts/limits.py | boundaries as designed |
| Falsification | scripts/falsify.py, 11 rows | all red after; evidence/falsify-rows.txt |
| Full suite | not run (criterion red) | owed for the next check |
Reuse for a next repair: the TV7.3, TV7.4, TV10, J1 and P5 rows keep their results while their input files (media/redacted.py, stages/video_review.py, cli_video_review.py, stages/video_pointers.py, .gitignore) are unchanged; ruff, the suite and the two PROPOSED-ISSUE gaps need a fresh look.
