# Manifest — container-ci-smoke

Status: ready-for-check
Fix cycle: 0
Unit: container-ci-smoke (CI container smoke + one-file diagnostics for the Cloud Run exit 126 failure)
Base SHA: 7a9c5365
Branch: ci-container-smoke

## Changed paths
- scripts/container_diagnose.sh (new): writes container-debug-<ts>.log (sections 1-9, 8a with --gcloud) and summary.md; sourceable `diagnose` and `redact`.
- .github/workflows/container-smoke.yml (new): push master / PR on image paths / workflow_dispatch; contents: read; 40 min; always() summary + artifact `container-smoke-evidence` (14 days).
- docker/DEPLOY.md: "Debugging a failing container" section.
- tests/test_container_ci_workflow.py (new).

## Findings
- Missing /app/.env: `core/env.py::load_repo_env` returns [] when absent; the startup script prints "/app/.env is absent". Not an error.
- No in-app GCS download exists; Cloud Storage is a Cloud Run volume mount only. The smoke needs no secrets.
- Not hosted (no AUTOTESTER_HOSTED=1), so AUTOTESTER_PUBLIC_ORIGIN is not required; a missing first-admin email only warns. Env used: PORT=8000, AUTOTESTER_ALLOWED_ORIGINS=http://localhost:8000.

## Not verifiable here (no docker)
First real Actions run: build time, whether /healthz answers within 240 s, and whether any DIAGNOSIS regex false-positives on real build or app output.
