# Checkpoint - t197-video-pointers, repair check A (cycle 2)

Attribution: claude-sonnet-subagent, coordinator A; verdict qa/verdicts/t197-video-pointers.r2.a.md. Result of every row below: PASS unless noted.
Environment: Windows 11, Python via uv 0.11.27, copy of `git archive b59dda0d` on C: (tree f40abd7d4776ac92b6cc2d9e9c18363d7331f044), pyproject sha256 6bc8b9cad2e2c396, uv.lock sha256 d795000fb0e210f1, ffmpeg present (real-ffmpeg files ran, not skipped).
Code identity: head b59dda0d, product 28035c82, repair base 0dcbbfa5; touched src files cli_video_review.py, cli_video.py, stages/video_pointers.py.

| Check | Command / scope | Result |
|---|---|---|
| F1 lint | `uv run ruff check src tests scripts`; `uv run autotester doctor` | All checks passed; doctor clean |
| Affected tests | 18 files (manifest's three pre-check commands), `-p no:xdist -o addopts=` | 373 passed after `git init` in the archive copy (8 `check-ignore` tests need a .git) |
| F2 / F3 | tests/test_cli_video_review_exits.py, tests/test_video_pointers.py | pass |
| Probes | 22 CliRunner probes, qa/evidence/t197-video-pointers-r2-A/probe_r2a.py | 21 pass; 1 deliberate leak probe fails (P1 low) |
| Falsification | 6 rows, qa/evidence/t197-video-pointers-r2-A/falsification-and-probes.md | all green-before / red-after on the named assertion |
| Full suite | `shard_suite.py --repo D:/autoTesting --ref b59dda0d --shards 4 -- -o addopts=`, collect proof ok 3631 | 3605 passed, 19 skipped, 7 failed: AT-858 x2, AT-750, AT-725, AT-920, AT-921 known; test_reconcile_schema rc2 pre-existing at merge base 09828f2d (fails), passes on master ccf3683b |
| Diff scope | repair diff 0dcbbfa5..b59dda0d in full; whole-unit stat vs 09828f2d (30 files) | no removal, no unlisted file |
