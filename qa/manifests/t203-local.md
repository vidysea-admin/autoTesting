# Manifest — t203-local

**Unit:** T-203 local Windows host (D-090). **Contract:** `qa/contracts/hosting.md` HO39-HO46.
**Status:** ready-for-check
**Fix cycle:** 1
**Files:** scripts/serve_windows.ps1, scripts/install_windows_task.ps1, tests/test_windows_host.py, docker/DEPLOY.md (Part B.1 appended; Part A untouched).
**Reused:** `/healthz` in ui/routes_live.py (no new endpoint).
**Not done / blocked:** T-204 login middleware does not exist yet (only auth/policy.py), so HO41's 401/302 check cannot run.
**Not done by design:** the Scheduled Task is NOT registered on this machine (needs Umesh).
