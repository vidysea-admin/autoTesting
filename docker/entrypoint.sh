#!/usr/bin/env bash
# Contract: qa/contracts/docker.md D2-D3. Starts a virtual display, shares it over VNC, exposes
# that VNC feed through noVNC's web client, then starts the app itself -- in that order, so the
# app never launches a browser before a display exists for it to render into.
set -euo pipefail

# Found running this for real: `docker compose restart` doesn't always let Xvfb clean up its
# own lock file, so the next Xvfb refuses to start ("Server is already active for display 99")
# -- silently, since it's backgrounded with `&`. This leaves x11vnc with no display to attach to
# and the live view shows "Failed to connect to server" with nothing actually wrong reported.
# Removing any stale lock/socket from a prior run makes every start (fresh or restart) idempotent.
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

# 1600x1000 > the 1366x850 browser viewport, so a watcher never sees a clipped window.
Xvfb :99 -screen 0 "${AUTOTESTER_SCREEN:-1600x1000x24}" &
sleep 1

# -localhost: the raw VNC port (5900) is reachable only from inside the container; the only
# way in is websockify below, which a reverse proxy can gate.
x11vnc -display :99 -forever -shared -nopw -localhost -quiet &
sleep 1

websockify --web=/usr/share/novnc 6080 localhost:5900 &

# --no-access-log: the access log would print the full request line for every request;
# the audit trail (auth/audit.py) is the record, and it never carries a query string (AU22).
exec uv run uvicorn autotester.ui.app:app --host 0.0.0.0 --port 8000 --no-access-log
