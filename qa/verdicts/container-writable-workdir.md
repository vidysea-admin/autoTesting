# Verdict - container-writable-workdir

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 1
**Reviewed SHA:** 2ec00db18eb79c4aae9eea16c0098d96ef117d1d
**Base:** 3f081243030be35f856a57286ffa0efc5602d6d7 (worktree clean at review; net src diff vs base = `providers/gemini.py` only)
**Prior:** cycle 0 FAIL, persisted at 8bdbd0e3 (evidence kept unchanged in `qa/verdicts/container-writable-workdir/*.out`)

## Prior blockers - resolved

1. **HO9.** `AUTOTESTER_DATA_DIR` is gone from src, tests, docker and `.env.example` (grep is clean outside qa/). There is no new key, and `AUTOTESTER_ROOT=` is already at `.env.example:82`. `test_hosting_deploy` passes.
2. **D6.** `docker-compose.yml` now sets `AUTOTESTER_ROOT=/app` on the `.:/app` bind mount. On its own, the entrypoint also leaves the root unset when `/app` is writable. So `.auth/`, `profiles/`, `projects/`, `.work/` and `.env` stay on the host mount and survive a recreate. The auth store is never empty on a recreate, so the first-admin seeding is not reopened.
3. **Duplicate concept.** `AUTOTESTER_ROOT` (HO3) is now the only root, and `core/paths.py::repo_root` is its only reader.
4. **Residual .env writers.** `routes_credentials`/`routes_settings` write `repo_root()/.env`, which is the same resolver that `core/env.py:100` reads. When the root is `/data` both sides use `/data/.env`. There is one loader and no split-brain.

## Code-asset vs writable-state classification (critical check 1)

I grepped every `repo_root()` consumer in src.
- **Code assets resolve package-relative, not data-root-relative:**
  - `RepoDocs.prompts_dir` and `skills_dir` (AT-132) and `providers/base.load_skill_prompt`.
  - The `browser/observe.py` JS, via `__file__`.
  - `ui/routes_live.package_root`.
  - Probe (`cycle1/probe_assets.py/.out`) with `AUTOTESTER_ROOT=<empty tmp>`: the prompts and skills dirs exist and are not under the root, the grade skill loads, and the observe JS imports.
- **Repo-root but dev-only, with no ui/stages importer:** `RepoDocs` docs/.goal/CLAUDE.md, `doctor`, `ledger/*` (qa/), `loop_status`, and `cli_loop`'s `qa/.last-tick`.
- **Writable state:** projects/, profiles/, `.work/` (audit, queue, settings, outbox, notification_prefs, team), `.auth/`, `.env`, and the gemini upload cache, which is now `work_dir()`.
- **Result:** no code asset resolves under `/data`. This matches the existing `compose.prod.yml` (`AUTOTESTER_ROOT: /data`, a standalone file).

## Entrypoint (critical check 2)

- `bash -n` exits 0.
- The preflight is still first and still exits 126.
- The condition is `[ -z "${AUTOTESTER_ROOT:-}" ] && [ ! -w /app ]`.
- Mutation probe (`cycle1/entrypoint_mutation.out`): the original gives a writable app an empty root and an unwritable app `/data`. Dropping the `-w` guard changes the writable case to `/data`, and `test_writable_app_mount_keeps_repo_root_behaviour` asserts against exactly that.
- An operator value is never overridden (test).
- The non-writable warning goes to stderr.
- `/data` is created and chowned to 10001 in the Dockerfile.

## Security (critical check 4)

- `auth/db.py:117-118` sets 0700 on the directory and 0600 on the file.
- `env_editor.set_env_values` writes 0600 atomically under a lock.
- `.dockerignore` excludes `**/.env`, so the image bakes no `.env`.

## Non-blocking findings

- With a plain `docker run` that leaves the root unset and bind-mounts a host file at `/app/.env`, the root falls to `/data` and `/app/.env` is ignored with no warning. None of the documented paths do this: dev compose pins `/app`, and prod uses `/data` plus `env_file`. Advisory: warn when `/app/.env` exists and the root is not `/app`.
- The `gemini.py` `work_dir()` call creates `.work/` as a side effect. That is harmless.

## Commands (independent; no maker evidence reused). Evidence: `qa/verdicts/container-writable-workdir/cycle1/`

Environment: repo `.venv` Python 3.11.16, `PYTHONPATH=<worktree>/src`, preflight PREFLIGHT_OK.

| Check | Command | Result |
|---|---|---|
| pytest | `env -u ANTHROPIC_BASE_URL ... -m pytest` on `test_container_{ci_workflow,entrypoint_behaviour,supervision,writable_root}`, `test_hosting_deploy`, `test_ui_auth_envkeys`, `test_env_loading`, `test_run_queue`, `test_prompt_skills` and `test_gemini_media_guard` | 136 passed, 1 skipped, exit 0 (`pytest.out`) |
| ruff | `ruff check src tests scripts` | exit 0 |
| doctor | doctor | `doctor: clean`, exit 0 |
| bash | `bash -n docker/entrypoint.sh` | exit 0 |

## Limits / remaining gates

- There is no docker on this host, so a real container start was not exercised. The CI container job is the remaining gate.
- The full suite runs post-merge.
- **Budget.**
  - Maker: 3,100 s / 214k tokens (reported).
  - Checker cycle 1: 426 s active (within the 500 s aim). Cumulative with cycle 0: 2,116 s, an active ratio of 0.68.
  - The 10% target is MISSED and recorded, not waived.
  - Checker tokens are unknown (null, debit 80k), so the token ratio is unverified.
  - Assess (`cycle1/assess-final.out`): status BOOTSTRAP_REVIEW, within the escalation limits (2,300 s / 214k). Earlier attempts are kept as `*-attempt*.out`.
