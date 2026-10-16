# dockerfile-merge-fix

Status: ready-for-check
Fix cycle: 0
Base: b6aa6cae0f3227a5767c1d264e9216e0b67aa064
Candidate: see `git log -1 -- qa/manifests/dockerfile-merge-fix.md` (the commit that adds this file)
Context: devops commit dd1c7789 "Update Dockerfile", merged into the hardened Dockerfile (docker-deploy-hardening, passed at 29f6609c).

## Changed paths
- Dockerfile
- tests/test_container_supervision.py
- qa/manifests/dockerfile-merge-fix.md

## Behaviour
1. Final `USER 10001:10001` after `chmod 755 /startup-diagnostics.sh` (script is root-owned 0755, so readable and executable by uid 10001; nothing after it needs root).
2. Heredoc `/startup-diagnostics.sh` ends with `exec "$@"`, so CMD `/entrypoint.sh` actually starts.
3. Smoke RUN is `import autotester, os, sys`, matching the existing static test (test not weakened).
4. Static test now also asserts final USER is non-root and a heredoc wrapper ends with `exec "$@"`.
Devops additions kept: util-linux/file, diagnostics, chown, runtime-user check.

## Required checks
- pytest tests/test_container_supervision.py tests/test_hosting_deploy.py tests/test_auth_deploy_files.py: 29 passed
- bash -n docker/entrypoint.sh: ok; bash -n of extracted heredoc (.work/startup-diagnostics.sh): ok
- ruff check on the test file: clean
- doctor: clean (2 advisory known-disputed warnings, non-blocking)

No container was built; runtime behaviour is unverified beyond static checks.
