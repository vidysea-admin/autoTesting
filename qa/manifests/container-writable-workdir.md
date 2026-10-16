# Manifest — container-writable-workdir

Status: checked-PASS
Fix cycle: 1
Unit: container-writable-workdir (PermissionError on /app/.work as uid 10001; Actions run 38908337519)
Base SHA: 3f081243
Branch: container-writable-workdir

## Cycle 1 (answers verdict 8bdbd0e3)
- Dropped AUTOTESTER_DATA_DIR (it duplicated HO3). The one variable is AUTOTESTER_ROOT, read only by core/paths.py::repo_root. All `src/` is back at base except gemini.py. That means projects/, profiles/, .work/ (audit, queue, settings, outbox), .auth and .env already follow it.
- Root cause of the CI failure: the image sets no AUTOTESTER_ROOT (only compose.prod.yml does), so a plain `docker run` wrote to the root-owned /app.
- docker/entrypoint.sh: `AUTOTESTER_ROOT=/data` only when unset AND /app is not writable. An operator or compose value always wins. It creates projects/ and .work/, and prints a warning to stderr if the root is not writable. The seeding step is removed (.dockerignore excludes projects/, so it was a no-op).
- D6 dev compose: docker-compose.yml now sets `AUTOTESTER_ROOT=/app` explicitly (the bind-mounted repo is the data root). The entrypoint also leaves a writable /app alone, so both mechanisms keep repo-root behaviour across recreate. Auth store stays in the mounted ./.auth.
- HO9: no new key; AUTOTESTER_ROOT is already in .env.example.
- .env: with AUTOTESTER_ROOT=/data the UI credential/settings writers write `repo_root()/.env` = /data/.env, which is writable and is exactly the file core/env.py::load_repo_env reads (the same resolver). In the container with a read-only /app and no root, the entrypoint now sets /data, so there is no split-brain. Nothing was moved.
- providers/gemini.py: the cwd-relative `.work/gemini_uploads.json` now uses work_dir() (the only real hardcoded-path gap).

## Changed paths
docker/entrypoint.sh, docker-compose.yml, src/autotester/providers/gemini.py, tests/test_container_writable_root.py (new; replaces test_data_dir.py), this manifest.

## Checks
scoped pytest (env -u ANTHROPIC_BASE_URL): test_container_*, test_hosting_deploy, test_ui_auth_envkeys, test_env_loading, test_run_queue = 103 passed, 1 skipped (before a lint-only edit of the new test; it then re-ran 6 passed). bash -n, ruff and doctor are clean.

## Test environment
This host sets ANTHROPIC_BASE_URL, which breaks two test_au21 cases; tests were run with `env -u ANTHROPIC_BASE_URL`.
Not verifiable here (no docker): a real container start.
