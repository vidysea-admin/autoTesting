# Manifest - t203b-hosting-gaps (T-203 rows HO4, HO12, HO15, HO19, HO21)

## Status: superseded
Superseded-by: commit 80c15ebb (merged via t203c); T-203 done, qa/verdicts/t203-task

**Contract:** qa/contracts/hosting.md HO4, HO12, HO15, HO19, HO21 (not edited)
**Goal task:** T-203
**Fix cycle:** 1
Branch: wave/t203b-hosting-gaps · Base: master b2d42c9b · Judgement that triggered this: qa/verdicts/t203b-gaps-check.md (5 FAIL on master)
**Dual check:** yes recommended (auth and permission paths: `/auth/check`, the start-time `project.run` recheck). An independent checker, not this maker, must judge these fixes.
Deferred, untouched: Ubuntu rows (D-090), HO39/HO40 and HO26-HO29 (D-093). No decision entry written, no contract or enforcement path edited (`docker/Caddyfile` and `docker/DEPLOY.md` are deploy files, not hooks).

## What changed (all through the one central policy table and `authorize`; no parallel permission code)
- HO12: `ui/routes_auth.py` gains `GET /auth/check?need=view|control` (policy row `live.view` in `auth/policy.py`; the login gate gives 401/302 without a session and 403 without `live.view`; `need=control` also wants `live.control`; 200 returns the identity). `ui/routes_live.py`: `/live` adds noVNC `view_only=1` to the iframe unless the viewer holds `live.control` (`authorize`), and says so. `docker/Caddyfile`: `/novnc/*` now `forward_auth`s to `autotester:8000/auth/check` and proxies to the noVNC port instead of the blanket 503. `docker/DEPLOY.md` section 7 updated.
- HO15: new `ui/routes_server_settings.py` (`GET/POST /settings/server`, policy rows `settings.manage`, registered in `ui/routers.py`). Digits-only input, validated by the existing strict `ServerSettings`; any bad field gives 400, a message that does not echo the input, and stores nothing; a save writes an audit action line (the request line is written by the gate) and calls the new `RunQueue.nudge()` so a raised cap starts a waiting run without another press (also closes land-t203-hosting P3). Corrupt file: the page shows the existing fallback sentence.
- HO19: reuses the existing `ui/intake_gate_auth.py::principal_for_email` (no new helper); `ui/routes_runs.py::_recheck_run_right` runs first in `_run_queued`: the entry's requester must still be an enabled account holding `project.run` on the project (`authorize` + `resource_for`), else `RunRefused` (entry ends `refused`, `launch_run` and so any browser never reached). Skipped only with login off (`auth_disabled`) or no recorded requester. Applies to schedule entries too (their `requested_by` is the schedule owner, HO24).
- HO21: `trigger_run` (the Run button) now records `requested_by` and `requested_by_id` from the session, so every entry names who asked; `ui/run_queue_view.py` shows "Requested by (trigger)" per row (closes P1).
- HO4 (local half): `scripts/hosting_state_listing.py <root>` prints projects, accounts, groups, settings and queue as JSON for a before/after diff; no secrets read.
- Tests: `tests/test_hosting_gaps.py` (new, 27 cases); `tests/test_ui_auth_policy_table.py` gained the three new policy rows (EXPECTED table extended, nothing loosened).

## Pre-check (maker; not a verdict)
- `uv run pytest -p no:xdist tests/test_hosting_gaps.py tests/test_ui_auth_policy_table.py`: 27 passed. Wider affected run: see the commit message / handback.
- `ruff check src tests scripts`: clean. `autotester doctor`: see handback.

## Not done, honestly
- The view-only flag is enforced by the viewer page (`view_only=1`), not at the websocket: a `live.view` holder who builds their own noVNC client can still send input through the proxy. Closing it needs a second proxy path (input-capable websocket behind `/auth/check?need=control`); that and every container half (restart/recreate, websocket 401 probe, recording, Xvfb-size run) are BLOCKED-CAPABILITY here (no Docker). Left for the server rehearsal.
- No live browser walk of the new settings page or `/live`; exercised through the real ASGI app with the gate ON.
- No nav link to `/settings/server` yet (reachable by URL and from its breadcrumb); the admin nav entry is a small follow-up.
- `qa/contracts/hosting.md` HO16 still says "run page" where code redirects to the report (land-t203-hosting P6); contract is not mine to edit.
