# Task-level verdict - T-204 team login (independent close-out check, 2026-10-13)

Checked on master after merge e35731ad (code 37a1d211 + master reconcile). Contract `qa/contracts/auth.md` AU1-AU27. Single checker, read fresh; unit-level dual PASS r3 A+B (37a1d211) and merge-reconcile A PASS relied on for rows whose inputs did not change; I re-ran the 13 auth test files, test_cli_subapp_hook, test_cli_advice_resolves, test_hosting_deploy, test_ui_origin_guard on the merged tree: 407 passed after repairing one environment-dependent test (test_au21_a_slug_that_swallows_a_variable depended on an ambient NODE_OPTIONS; it now sets it). ruff clean; doctor clean.

VERDICT: FAIL (task not closed; the file at the done_check path is deliberately not written)

Gaps:
1. AU24 not met: the contract requires the auth tests to pass inside the Docker image on Linux, recorded as `qa/evidence/t204-linux-run.md`. That file does not exist; the manifest itself says HELD/PARTIAL; this host has no docker.
2. AU26 Mode D walk: evidence is from cycle 1 (`qa/evidence/browser-t204-team-login-r1-A/`); no browser walk was run on the merged tree (CPU policy). Treat as carried, not re-proved.

Acceptance in the goal note (unauthenticated refused, signed-in gets through, no credentials in logs): met per r3 evidence and the re-run tests.
Not a T-204 gap: the intake gate seam (set_gate) is T-198's (see T-198 task check).
