# Verdict - t203b-hosting-gaps (independent checker, security focus)

Cycle checked: 1 · checked code: wave/t203b-hosting-gaps 441899e9 · contract hosting.md HO4/HO12/HO15/HO19/HO21, auth.md AU14/AU16/AU17

| Row | Verdict | Evidence |
|---|---|---|
| HO12 (CRITICAL) | FAIL | `/auth/check` is right: 401 without a session, 403 without live.view (policy row `live.view`, so it is in AU14 and not in AU16's public set), identity only for the caller. But the contract says "sending input needs live.control (a view-only instance for the rest)". Input is gated only by the page iframe's client-side `view_only=1` (routes_live.py viewer_url). `docker/Caddyfile` `/novnc/*` calls `/auth/check` with no `need=control`, and proxies to the one input-capable websockify (`docker/entrypoint.sh:23`, x11vnc has no view-only twin). A live.view holder who opens the websocket directly can send keys and clicks. Query `view_only=1` is client-controlled and cannot be the enforcement. Fix is config, not app code: a second view-only VNC/websockify port behind `forward_auth ... /auth/check` for live.view, and the input-capable port behind `/auth/check?need=control` (live.control). Proof of it is SERVER-GATED; the missing design is not. |
| HO4 | PASS (local half) | `scripts/hosting_state_listing.py` + restart test pass. Container restart/recreate half: BLOCKED-CAPABILITY, container rows are Ubuntu/Docker (D-090), contract marks it BUILD-HOST. Not a deferral by text; it is unjudgeable here. |
| HO15 | PASS | `/settings/server` gated by settings.manage; bad input 400 without echo, nothing stored; audit line holds values only; `RunQueue.nudge()` applies a raised cap without restart. No nav link: contract does not require one. |
| HO19 | PASS | `_recheck_run_right` in `_run_queued` before `launch_run`; revoked, disabled, deleted requester gives `refused` with reason, nothing launched; reuses `principal_for_email`/`authorize`. |
| HO21 | PASS | requester and trigger recorded on Run button, shown in queue panel; per-project scoping unchanged. |

Deferral ruling: no text in D-090 or D-093 defers HO12's input enforcement or HO4/HO12 as rows; D-090 defers HO10/11/13/34-36 and D-093 HO39/40, HO26-29. Container probes are SERVER-GATED by the row's own words, but the missing view/control split is a design defect.
Tests: test_hosting_gaps, policy_table, auth_escalation, schedule_wiring: 64 passed; run-queue tests (4 files): 37 passed. doctor clean. ruff: 1 E501 at tests/test_isolated_provider.py:59, from master (73880ccf), not this branch.
