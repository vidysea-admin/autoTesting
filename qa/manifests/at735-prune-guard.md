# AT-735 prune_old_videos guard and ordering

Status: checked-PASS
Fix cycle: 0
Risk: low (post-save housekeeping ordering)
Base: 3f081243
Branch: at735-prune-guard

## Problem and fix

AT-735 / O5: the project-wide video prune ran before the "ask, don't guess" step and was
unguarded, so a prune error 500'd a saved run and could delete videos before the VideoRequests
were raised. Fix: `prune_old_videos_safely` (stages/video_retention.py) logs and skips on any
error; `run_follow_ups` (stages/run_launcher.py) runs advise, ask, then prune;
stages/orchestrate_downstream.py now asks first and uses the safe prune.

## Consumers

launch_run (UI and CLI via launcher), orchestrate_downstream run completion.

## Tests

tests/test_prune_guard.py (ordering, error-safe, follow-ups survive a raising prune);
existing tests/test_video_retention.py and tests/test_run_launcher.py.
