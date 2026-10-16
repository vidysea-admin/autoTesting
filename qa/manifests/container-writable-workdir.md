# Manifest — container-writable-workdir

Status: ready-for-check
Fix cycle: 0
Unit: container-writable-workdir (PermissionError on /app/.work as uid 10001; Actions run 38908337519)
Base SHA: 3f081243
Branch: container-writable-workdir

## Changed paths
- src/autotester/core/paths.py: new `ENV_DATA_DIR` (AUTOTESTER_DATA_DIR), `data_root(root=None)`, `projects_root(root=None)`; the only place the var is read. Explicit root wins; unset = repo root (unchanged). ProjectPaths.dir/profile_dir, work_dir, team_path use it. `env_file` stays at the repo root.
- Rerouted hardcoded writers: ui/run_queue.py, auth/audit.py, auth/db.py (.auth default), stages/video_requests.py (outbox), store/server_settings.py, store/notification_prefs.py, providers/gemini.py (cwd-relative `.work/gemini_uploads.json` -> work_dir()).
- Project listing readers use projects_root(): ui/credential_guard.py, ui/helpers.py, stages/schedule_wiring.py, core/env.py (project_credentials).
- docker/entrypoint.sh: exports AUTOTESTER_DATA_DIR=${AUTOTESTER_DATA_DIR:-/data} (no Dockerfile edit, since the Docker team edits it), mkdirs, and seeds /app/projects into /data/projects with `cp -rn` (never overwrites).
- tests/test_data_dir.py (new).

## Notes
- Runs, evidence, bundles, video, crawl, sources are all ProjectPaths-derived, so they follow `projects/` to /data.
- /app stays root-owned; no chmod.
- Risk: /data is ephemeral on Cloud Run unless a volume is mounted; seeding copies the image's projects on each cold start.
- Not verifiable here (no docker): a real container start.
