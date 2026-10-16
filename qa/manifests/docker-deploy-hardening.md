# Manifest - docker-deploy-hardening

**Status:** ready-for-check
**Fix cycle:** 0
**Unit:** make the Cloud Run deploy self-diagnosing (exit 126 `/opt/venv/bin/python: Permission denied`)
**Base SHA:** c4d48ad109f1ef77f73ee9172866cc5feeca7063
**Candidate SHA:** the commit that adds this file (see `git log -1`)
**Contract:** qa/contracts/hosting.md HO11; qa/contracts/core-invariants.md (file/function limits, LF for *.sh)

## Changes
- Dockerfile: `UV_PYTHON_PREFERENCE=only-managed`, `UV_PYTHON_DOWNLOADS=manual`; after `USER 10001:10001` a smoke RUN imports autotester and tests the resolved python is executable.
- docker/entrypoint.sh: preflight (PREFLIGHT FAIL with uid, readlink -f, namei/ls, /opt/uv-python perms, hint; exit 126); app port from `${PORT:-8000}`, logged; supervisor readiness uses the same port.
- Ordering unchanged: app starts last, because a resumed queued run launches headed Chromium at app startup and needs Xvfb. Startup probe timeout is raised in docs instead.
- docker/DEPLOY.md: Cloud Run flags and exit-126 triage.
- tests/test_container_supervision.py: one static test.

## Required checks
uv run pytest tests/test_container_supervision.py tests/test_hosting_deploy.py tests/test_auth_deploy_files.py (29 passed); uv run ruff check on the test file (clean); uv run autotester doctor (clean).

## Honest limits
No docker build and no container run happened on this machine. The smoke RUN and preflight are verified by `bash -n` and static tests only. Compose healthcheck still probes 8000 (unchanged; compose does not set PORT).
