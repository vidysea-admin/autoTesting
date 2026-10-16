# Verdict - docker-deploy-hardening

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** bd70be450241765efdc10c922ed7771dbd412a73 (base c4d48ad109f1ef77f73ee9172866cc5feeca7063)

## Scope and limits
Static review only. NO CONTAINER WAS BUILT OR RUN (no docker on this machine). The Dockerfile smoke RUN and the cloud-run flags are reviewed by reading, not executed. The real image build and a Cloud Run deploy remain a required BUILD-HOST gate (hosting.md HO11 is DEFERRED TO UBUNTU).
Changed: Dockerfile, docker/entrypoint.sh, docker/DEPLOY.md, tests/test_container_supervision.py (+ manifest).

## Independent checks
- pytest test_container_supervision, test_hosting_deploy, test_auth_deploy_files: 29 passed, rc 0.
- ruff check on the test file: clean, rc 0. `bash -n docker/entrypoint.sh`: rc 0.
- autotester doctor: "clean", rc 0 (only advisory decision-citation warnings in docs/qa, none in changed files; base run not repeated).
- `git ls-files --eol`: entrypoint.sh i/lf attr eol=lf; Dockerfile, DEPLOY.md, test all i/lf (w/crlf is working-tree autocrlf only).
- Behavioural probe (scratch copy of entrypoint with PY pointed at a non-executable file, namei absent in that shell): prints PREFLIGHT FAIL with uid, readlink, ls fallback, perms, hint; exit code 126 preserved.

## Probe findings
1. Smoke RUN follows `USER 10001:10001`, so it runs as uid 10001; python -c import plus `test -x $(readlink -f ...)` would fail the build on the old /root-symlink layout. OK.
2. UV_PYTHON_DOWNLOADS=manual is set before `uv python install 3.12` (explicit install still permitted) and before both `uv sync` runs, which find the managed 3.12 in UV_PYTHON_INSTALL_DIR. Order OK. Runtime `uv run` with UV_NO_SYNC=1 needs no download.
3. Entrypoint: preflight precedes the exec line; namei guarded by `command -v` with ls fallback; `||` lists are safe under set -euo pipefail; exit 126; APP_PORT used by uvicorn and the `tcp:` readiness entry; compose.prod healthcheck stays on 8000 (PORT unset, default 8000). OK.
4. DEPLOY.md gcloud flags (execution-environment gen2, no-cpu-throttling, port, add-volume/mount, startup-probe tcpSocket.port with delay/timeout/period/threshold) are syntactically plausible; not executed against gcloud. Advisory: a GCS FUSE volume at /data with SQLite/uid 10001 is untested.
5. ADVISORY (non-blocking): the new test is string-presence only. Mutation: deleting the two preflight call lines from the entrypoint still passes it (function definition keeps "PREFLIGHT FAIL"/"exit 126"), so it does not prove the preflight runs. Suggest a follow-up behavioural test that runs the script with a non-executable PY and asserts rc 126.

## Remaining gates
Docker build + `docker run --user 10001` smoke and Cloud Run deploy on a build host.
