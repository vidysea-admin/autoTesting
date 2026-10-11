# Checkpoint - t197-video-pointers - coordinator A - cycle 0
Head 3d0be650 · policy .9 · environment: Windows, worktree uv env, ffmpeg present, ruff and doctor run from the worktree.

| Check | Command / scope | Result |
|---|---|---|
| TV1 + CLI | pytest test_video_pointers.py test_cli_video_review.py | 47 passed, 0 skipped |
| TV2 / TV7 / TV10 | pytest test_video_review_gates.py test_video_review_guards.py | 28 passed |
| TV3-6, TV8 | pytest test_video_review.py | 28 passed |
| TV7.3 | pytest test_video_review_redaction.py | 9 passed |
| CLI surface | pytest test_cli_advice_resolves.py test_approve_cli.py test_cli_surface.py | 89 passed |
| lint | ruff check src tests scripts; autotester doctor | clean; clean |
| falsification | 21 rows in copies | qa/evidence/t197-video-pointers-a/falsification.md |
| full suite | NOT RUN (maker instruction), owed at the repair check | - |

Findings: P1 json refusal paths (cli_video_review.py:183), P2 reviews/ not gitignored.
Code identity: git tree of 3d0be650 (identical to 5032cfa1 except the manifest).
