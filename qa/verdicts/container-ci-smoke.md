# Verdict - container-ci-smoke

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** c51966a21c2fed8d24e9ca4dae9fbbbd166f4fb9
**Base:** 7a9c5365 (maker commit 73653750; master 453716b6 merged as c51966a2)

## Evidence (independently produced, worktree ci-container-smoke, repo .venv, PYTHONPATH=worktree src)
- Diff 453716b6...c51966a2: 5 files (workflow, scripts/container_diagnose.sh, docker/DEPLOY.md, test, manifest). No src/ or Dockerfile change.
- Workflow security: `permissions: contents: read`; no pull_request_target, no `secrets.`, no env dump; checkout@v4 and upload-artifact@v4 (major pins); summary and upload both `if: always()`; `timeout-minutes: 40`; pull_request only reads code and uses no secrets. YAML parses.
- Fail conditions: `main` has no `set -e`, but every condition is computed explicitly into `ok`: image User not 10001, import failure (either user), readiness never reached (loop also breaks if the container stops), DIAGNOSIS count > 0, build exit != 0 (read from `PIPESTATUS[0]`, no `|| true`). Final status is `[ "$ok" -eq 1 ]` and the script does `exit $?`. The tee only echoes the result line. The EXIT trap does not change the status. The workflow step runs under bash -e, so it fails the job, and the always() steps still run.
- Smoke env claims verified: `load_repo_env` returns [] when .env is absent (core/env.py); the Dockerfile wrapper prints "/app/.env is absent"; AUTOTESTER_PUBLIC_ORIGIN is required only inside `_check_hosted()` (hosted=1), and the first-admin check only warns (auth/config.py); no GCS client code under src. `/healthz` exists (ui/routes_live.py) and is a PUBLIC_RULE route returning {"ok": true}.
- DIAGNOSIS false positives: ran `diagnose` over the Dockerfile text: [OK]/INFO only. The GCS, Xvfb and perm patterns need the keyword and the failure word on one line; plain "denied" alone does not match. Each signature maps to the right cause and fix (checked in the test and the code).
- Commands: `bash -n` rc 0; YAML parse ok; pytest tests/test_container_ci_workflow.py tests/test_container_*.py rc 0, 33 passed, 1 skipped (the earlier supervision failure is gone); ruff check src tests scripts rc 0; doctor clean (advisory warnings only).

## Redaction probe (independent)
Masked: `api_key=`, `apikey:`, JSON `"api_key":"x"`, `*_API_KEY=`, `-e SECRET_X=`, `X-Api-Key:`, `private_key:`, `passwd=`, Bearer (any case), AIza and sk- keys. Env values are not written at all (inspect uses names only, via `cut -d=`).
NOT masked (advisory, outside the documented KEY/TOKEN/SECRET/PASSWORD/Bearer claim):
- URL credentials `user:pass@host`
- `Authorization: Basic ...`
- `pwd=`, `auth=`, `credential=`
- `--password x` (space separated)
- ghp_ tokens
- the remainder of a quoted value containing spaces (`token = "a b c"` -> `<redacted> b c`)
Risk is low in the secretless CI run, but the local `--gcloud` log could carry such values. Recommended follow-up (non-blocking): add URL userinfo and Basic patterns, and mask to the closing quote.

## Limits (only a real run can prove)
- Docker is not available here. The build, the image User check, the 240 s readiness on /healthz, and absence of DIAGNOSIS false positives on real build and app output are unexercised. The main() flow was never run; only `diagnose` and `redact` are tested.
- Checker tokens unknown (null); the active time target was not verified.
