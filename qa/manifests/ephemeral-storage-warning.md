# Manifest - ephemeral-storage-warning

**Status:** ready-for-check
**Fix cycle:** 1
**Issues addressed:** 2026-10-28 deploy silently wiped the admin account (Cloud Run /data not a mounted volume)

## Criteria (from the task brief; no qa/contract edited)
1. Same-device data root on a hosted server shows the admin banner "Storage is not persistent: accounts and projects are lost on every deploy. Mount a volume at <root>."
2. Mounted root (own mount line, not tmpfs/ramfs, device differs from /) shows no banner.
3. Non-hosted (local) server shows no banner.
4. `AUTOTESTER_EPHEMERAL_OK=1` shows no banner and no entrypoint warning.
5. The check never stops the service from starting: the Python check swallows every error (unknowable = no warning); the shell function never exits and is called as `warn_if_ephemeral || true`.
6. `docker/entrypoint.sh` logs one `WARNING: storage is not persistent` line when the root shares a device with / or is not under a non-tmpfs mount in /proc/mounts.
7. `docker/DEPLOY.md` has one paragraph pointing at the warning.

## What changed
- `src/autotester/core/env.py`: new `storage_warning(root, mounts_path)`, helpers `_device`, `_mount_entries`, `_holding_mount`, const `EPHEMERAL_OK_ENV`. Ephemeral = deepest mount holding the root is `/`, is tmpfs/ramfs, or shares `st_dev` with `/`. An ancestor volume counts. Missing/garbled /proc/mounts or any exception returns None. (Chosen over core/paths.py, which is at 299 lines.)
- `src/autotester/ui/admin_view.py`: `storage_banner()` (gated on `auth.loopback.hosted()`), rendered at the top of `users_body` and `groups_body` (`/admin/users`, `/admin/groups`). There is no bare `/admin` route; the banner is on both admin pages.
- `docker/entrypoint.sh`: `warn_if_ephemeral` (stderr line), runs after the AUTOTESTER_ROOT setup, before the supervisor exec. Test seam: `AUTOTESTER_MOUNTS_FILE`.
- `docker/DEPLOY.md`: "Persistent storage" paragraph in the Cloud Run section.
- Not touched: auth/config.py, ui/helpers.py, docs/DECISIONS.md, qa/contracts, qa/.paused.

## Fix cycle 1
- `.env.example`: added empty `AUTOTESTER_EPHEMERAL_OK=` with a one-line comment (test_env_example_documents_every_key_the_code_reads).
- Manifest no longer cites a decision id.
- Optional octal-decoding of mount points with spaces in the awk path: not done (a data root with a space is not a deploy shape here).

## Tests
`tests/test_storage_warning.py` (new, 18): detector (same device, mounted root, ancestor mount, not-in-mounts, tmpfs, opt-out, missing/garbled mounts, device error), banner (hosted+ephemeral, not hosted, persistent, opt-out end to end), entrypoint (bash -n, no `exit` in function, real function run under bash with fake stat/mounts: warns and returns 0, quiet when mounted, quiet on opt-out and on missing mounts file).

## Verification
- `uv run pytest tests/test_storage_warning.py tests/test_container_entrypoint_behaviour.py tests/test_env_loading.py`: 30 passed, 1 skipped.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 1 violation, pre-existing and unrelated (the dangling decision citation at `qa/verdicts/6c-1028-signup.md:4`, whose target entry exists only in the main checkout's uncommitted decisions file).
- shellcheck not installed; `bash -n docker/entrypoint.sh` passes.
- Not exercised: a real Cloud Run / Linux container (Windows host; /proc/mounts and `stat -c %d` are faked in tests).

## Residual risk
Cloud Run gen2 GCS-FUSE mounts appear in /proc/mounts with fstype `fuse`/`fuse.gcsfuse`, not tmpfs, so they count as persistent; confirm on first deploy.
