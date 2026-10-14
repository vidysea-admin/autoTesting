# t200-advisories

Status: ready-for-check
Fix cycle: 1
Branch: wave/t200-advisories (rebased on a172f38a)

Closes the two cycle-2 advisories of t200-ts4-ts7.

1. Cross-process append safety: new `core/file_lock.py::file_lock` (msvcrt/flock, moved out of
   `ui/env_editor.py::_env_lock`, which now delegates). `schedule_store._append_line` holds it
   on a `.<name>.lock` sidecar. Test: two OS processes x 40 appends -> 80 intact lines.
2. Sweep bound: `schedule_sweep.stale_after_for` = max(3h, min(run.bounds.wall_clock_s + 30min,
   24h)); unknown bound keeps 3h. Tests in `tests/test_schedule_advisories.py`.

Verify: scoped schedule*, run_queue*, ui_env_editor, core tests (281 passed), ruff clean.
