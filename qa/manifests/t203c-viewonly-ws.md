# Manifest - t203c-viewonly-ws (T-203 row HO12, server-side view vs control)

## Status: ready-for-check

**Contract:** qa/contracts/hosting.md HO12 (not edited)
**Goal task:** T-203
**Fix cycle:** 1
Branch: wave/t203c-viewonly-ws · Base: wave/t203b-hosting-gaps @ 69cdb452 (verdict: HO12 FAIL, view-only not server-side)
**Dual check:** yes recommended (permission path).

## What changed
- Two endpoints, decided by the server from the session principal, never by a client flag:
  `/novnc-view/*` -> `forward_auth /auth/check?need=view` -> websockify 6081 -> `x11vnc -viewonly` (rfb 5901; the VNC server drops input);
  `/novnc/*` -> `/auth/check?need=control` (live.control) -> websockify 6080 -> input-capable x11vnc (5900).
  Bare/look-alike VNC paths (`/novnc`, `/novnc-view`, `/websockify*`, `/vnc.html`) get 403 in Caddy.
- `docker/Caddyfile`, `docker/entrypoint.sh` (second x11vnc + websockify), `docker/compose.prod.yml` (expose 6081), `docker-compose.yml`, `Dockerfile` (EXPOSE), `docker/DEPLOY.md`.
- `ui/routes_auth.py`: `/auth/check` now fails closed (400) on any `need` other than view|control.
- `ui/routes_live.py`: `/live` sends users without live.control to the view-only endpoint (`view_only_url`), keeping `view_only=1` as a UI hint.
- Tests in `tests/test_hosting_gaps.py`: Caddyfile structure (distinct upstreams, need=view vs need=control, catch-all deny), entrypoint (-viewonly only on 5901), decision matrix (anon 401, no-live.view 403, viewer view 200 / control 403, controller both, unknown/mixed `need` fail closed), page endpoint selection.

## Pre-check (maker; not a verdict)
- pytest -p no:xdist tests/test_hosting_gaps.py tests/test_hosting_config.py tests/test_ui_auth_policy_table.py: 45 passed. ruff: clean except pre-existing E501 in tests/test_isolated_provider.py (not touched).

## Not done: Ubuntu/Docker only (BLOCKED-CAPABILITY here, no Docker/Caddy/VNC)
- Real websocket probes through Caddy per endpoint (viewer -> /novnc/ 403, /novnc-view/ ok, anon 401); path-traversal probes (`/novnc-view/../novnc/`) against Caddy's path normalisation; confirming typing in a view session changes nothing on the display; x11vnc -viewonly behaviour with two servers on :99.
