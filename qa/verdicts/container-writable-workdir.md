# Verdict - container-writable-workdir

**Verdict:** FAIL
**Status:** FAIL
**Cycle checked:** 0
**Reviewed SHA:** 64cc8cc8957d398eb04877420af87d264f150c31
**Base:** 3f081243030be35f856a57286ffa0efc5602d6d7 (one commit, 15 files; worktree clean before review)

## Blocking findings (proven)

1. **HO9 drift test fails (hosting.md HO9).** `tests/test_hosting_deploy.py::test_env_example_documents_every_key_the_code_reads`
   fails with `undocumented env keys: ['AUTOTESTER_DATA_DIR']`. The new var is not in `.env.example`. Reproduced twice
   (`pytest.out`, `pytest-rerun.out`). The base has no such key, so the candidate introduced this failure.
2. **Dev compose loses state on recreate (docker.md D6).** `docker-compose.yml` bind-mounts `.:/app` and sets neither
   `AUTOTESTER_ROOT` nor `AUTOTESTER_DATA_DIR`. `/startup-diagnostics.sh` runs `exec /entrypoint.sh`, which now always exports
   `AUTOTESTER_DATA_DIR=/data`. `/data` is container-local there, with no volume. Runs, evidence, profiles (browser login state),
   `.work/` (queue, settings, audit) and the auth store (`/data/.auth`) are therefore written inside the container and lost on
   `docker compose down && up`. The host's existing `./.auth` and `./profiles` are ignored. D6 requires that recreating the
   container "retains prior project data and browser login state". There is a security side effect too: every recreate starts
   with an empty auth store, which puts first-account seeding back into play. Fix direction (maker's choice): only default the
   var when `/app` is not writable, or set it explicitly in the Dockerfile/CI and leave compose on `/app`.

## Non-blocking findings

- **Seeding is a no-op in the built image.** `.dockerignore` excludes `**/projects/`, so `/app/projects` does not exist and
  `cp -rn` fails silently (`2>/dev/null || true`). The manifest's claim that it "seeds the committed project definitions" is
  false. The seeding has no security impact: it copies no secret, and `-n` never overwrites existing files.
- **Residual writers on /app.** `ui/routes_credentials.py:171,235` and `ui/routes_settings.py:98` write `repo_root()/.env`.
  This is by design (`.env` is config), but a container without `AUTOTESTER_ROOT` gets a PermissionError when it saves a
  credential. HO3 already defines `AUTOTESTER_ROOT=/data` as the container's data root, and `docker/compose.prod.yml` sets it.
  `AUTOTESTER_DATA_DIR` is a second variable for an overlapping concept, so record the reason in the manifest or a decision.
  Other matches are a dev-only writer that is unaffected (`cli_loop.py` writing `qa/.last-tick`) and a script that takes an
  explicit root (`providers/config_migration.py`).
- **mkdir failure is non-fatal and not announced.** The first write then raises PermissionError (loud, not silent loss), but
  the entrypoint prints no diagnostic. Advisory: echo a warning when `$AUTOTESTER_DATA_DIR` is not writable.

## Checks that held

- **Unset behaviour is unchanged** (`probe_unset.py`, exit 0). `ProjectPaths.dir`, `profile_dir`, `_queue_file`, `auth_db_path`
  and `team_path` equal the base locations under the repo root. When the var is set, paths move to it. `env_file` stays at the
  repo root, and an explicit root still wins.
- **Security.**
  - The auth db keeps `chmod 0700` on its directory and `0600` on the file (`auth/db.py:117-118`) wherever it is placed.
  - `.env` is still read only from `repo_root()` (`core/env.py:100`).
  - `project_credentials` and credential_guard keep key namespacing. Only the operator sets the var, which is the same trust
    level as `AUTOTESTER_ROOT`.
  - The auth/envkeys/hardening/refusal-audit tests pass.
- **Entrypoint ordering.** The preflight still runs first and still exits 126. `bash -n` exit 0.
- **Commands** (repo `.venv` Python 3.11.16, PYTHONPATH=worktree/src, preflight PREFLIGHT_OK):
  - pytest on test_data_dir, test_container_{ci_workflow,entrypoint_behaviour,supervision}, test_run_queue,
    test_run_queue_resilience, test_team_run_queue_seam, test_ui_auth_{envkeys,hardening,refusal_audit}, test_env_loading and
    test_hosting_deploy: 3 failed, 128 passed, 1 skipped.
  - Two of those failures (`test_au21_*[anthropic-ANTHROPIC_BASE_URL]`) come from this host: the checker's shell sets
    `ANTHROPIC_BASE_URL`. With that variable unset the rerun passes them, and only the HO9 test still fails (1 failed, 11 passed).
  - ruff on the changed paths: exit 0.
  - doctor: clean (advisory warnings only).
- All evidence is under `qa/verdicts/container-writable-workdir/` and was produced independently. No maker evidence was reused.

## Limits

- No docker on this host, so a real container start is not exercised.
- **Budget.** BOOTSTRAP_REVIEW (180 s / 6,000 allocated tokens) plus the standing escalation (+300 s), giving a cap of 480 s.
  Active time was about 1,690 s, mostly CPU-bound pytest wall time on a saturated machine. The final assess returns
  NEEDS_EXTRA_REVIEW with active_s and tokens exceeded. This breach is recorded, not waived.
- Actual checker tokens are unknown (null), and so is maker usage, so the ratios are unverified.
