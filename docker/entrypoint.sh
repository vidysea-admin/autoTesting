#!/usr/bin/env bash
# Fail the whole stack when any service dies; Docker's restart policy restores it.
set -euo pipefail

# Same-user leftovers from a prior container start. Never change ownership as root here.
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

# Readiness sockets gate startup; the supervisor monitors every service throughout.
# VNC stays loopback-only; the two web viewers retain separate proxy permissions.
exec /opt/venv/bin/python /app/docker/supervise.py \
  unix:/tmp/.X11-unix/X99 "Xvfb :99 -screen 0 ${AUTOTESTER_SCREEN:-1600x1000x24}" \
  tcp:5900 'x11vnc -display :99 -forever -shared -nopw -localhost -quiet -rfbport 5900' \
  tcp:5901 'x11vnc -display :99 -forever -shared -nopw -localhost -quiet -rfbport 5901 -viewonly' \
  tcp:6080 'websockify --web=/usr/share/novnc 6080 localhost:5900' \
  tcp:6081 'websockify --web=/usr/share/novnc 6081 localhost:5901' \
  tcp:8000 'uv run uvicorn autotester.ui.app:app --host 0.0.0.0 --port 8000 --no-access-log'
