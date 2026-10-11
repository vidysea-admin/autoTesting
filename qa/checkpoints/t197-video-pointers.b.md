# Checkpoint - t197-video-pointers, coordinator B, cycle 0

Head 3d0be650 (worktree .worktrees/t197-video-pointers, product 5032cfa1), base 09828f2d. Policy proportional-verification/2026-10-10.9. Tier L, dual.
Environment: Windows 11, python 3.11 (uv project of the worktree), ffmpeg on PATH, fake approval key, fake provider, no network.

| check | command / scope | code hashes | result |
|---|---|---|---|
| approval gate matrix + tamper + cache + dry-run | qa/evidence/t197-video-pointers-B/test_b_adv.py -k gate/tampered/cached/dry_run (25 tests) | worktree 3d0be650 | all passed |
| approval reuse | test_approval_not_consumed_by_use | 3d0be650 | 3 calls on a 1-action approval (observed) |
| cap values | test_cap_values (nan, inf, -1, 0, 1e-9, -0.0) | 3d0be650 | nan/inf uncapped (observed) |
| pointer inputs, oversized, slug traversal, exit 4 | test_pointer_inputs, test_oversized..., test_many..., test_slug..., test_audio_only... | 3d0be650 | exit codes as contract; no pre-call spend on errors |
| redaction + egress + leftovers | test_noop_blackout..., test_redacted_run..., test_redact_edge_windows, test_edge_windows_25fps | 3d0be650 | gate holds; leftover redacted.mp4; reviews/ not gitignored |
| secrets | test_canary (10), test_encoded_canary_refused (4), repr check | 3d0be650 | no leak |
| determinism | test_determinism_diff | 3d0be650 | id equal; created_at differs |
| falsification M1 (copy, deleted) | tests/test_cli_video_review.py::test_redaction_window_frames_never_reach_the_provider | copy of 3d0be650 | green 7 passed (with M2 node) -> red on frame-time assertion |
| falsification M2 (copy, deleted) | ...::test_an_approval_that_does_not_cover_this_review_does_not_count | copy of 3d0be650 | green -> red [over2] (CRAWL-kind row) only, 5 others passed |
Attribution: coordinator B (claude-sonnet-subagent). Full suite not run by B (seat A owns it).
