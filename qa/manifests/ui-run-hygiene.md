# ui-run-hygiene

Status: ready-for-check
Fix cycle: 0
Issues: AT-733, AT-734, AT-735

- AT-733: `_wipe_entry_profile` (already fail-closed on master) now clears read-only bits and retries 3x before failing.
- AT-735: prune moved to `stages/run_launcher.py` on master; now `prune_old_videos_safely` (logged, never raises), run after the O5 ask step. Touched video_retention.py and run_launcher.py (outside the listed files; unavoidable).
- AT-734: `end_case_video` narrow excepts + logging; move guarded (RawResult survives); `video_lost` marker; `_ignore_close_errors` only swallows `Exception`.
- Tests: tests/test_ui_run_hygiene.py (9); the five named files pass (live-browser ones skipped).
