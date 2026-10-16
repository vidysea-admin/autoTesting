#!/usr/bin/env bash
# Fail the whole stack when any service dies; Docker's restart policy restores it.
set -euo pipefail

# Same-user leftovers from a prior container start. Never change ownership as root here.
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99

PY=/opt/venv/bin/python
APP_PORT="${PORT:-8000}"

preflight_fail() {
  echo "PREFLIGHT FAIL: $1" >&2
  echo "  uid=$(id -u) gid=$(id -g) python=$PY" >&2
  echo "  readlink -f: $(readlink -f "$PY" 2>&1 || true)" >&2
  if command -v namei >/dev/null 2>&1; then namei -l "$PY" >&2 || true
  else ls -ld "$PY" "$(readlink -f "$PY" 2>/dev/null)" /opt/uv-python /opt/venv >&2 || true; fi
  echo "  /opt/uv-python perms: $(stat -c '%A %U:%G' /opt/uv-python 2>&1 || true)" >&2
  echo "  HINT: image built before f572a4b5 or wrong USER; rebuild from current master." >&2
  exit 126
}

[ -x "$PY" ] && [ -x "$(readlink -f "$PY" 2>/dev/null)" ] || preflight_fail "cannot exec $PY"
"$PY" -c "import sys" >/dev/null 2>&1 || preflight_fail "$PY fails to start"
echo "entrypoint: uid=$(id -u) python=$(readlink -f "$PY") app port=${APP_PORT} (PORT=${PORT:-unset})"

# /app is root-owned and read-only to uid 10001; /data is the one writable volume. All mutable state
# (projects/, profiles/, .work/, .auth/) goes there via core/paths.py. A caller's own value wins.
export AUTOTESTER_DATA_DIR="${AUTOTESTER_DATA_DIR:-/data}"
mkdir -p "$AUTOTESTER_DATA_DIR/projects" "$AUTOTESTER_DATA_DIR/.work" 2>/dev/null || true
# Seed the committed project definitions once; never overwrite what a run already changed.
cp -rn /app/projects/. "$AUTOTESTER_DATA_DIR/projects/" 2>/dev/null || true

# Readiness sockets gate startup; the supervisor monitors every service throughout.
# The app starts last on purpose: a resumed queued run launches headed Chromium at app startup and
# needs Xvfb on :99 first. The sidecars become ready in about a second; give the Cloud Run startup
# probe a generous timeout instead of racing the display.
# VNC stays loopback-only; the two web viewers retain separate proxy permissions.
exec /opt/venv/bin/python /app/docker/supervise.py \
  unix:/tmp/.X11-unix/X99 "Xvfb :99 -screen 0 ${AUTOTESTER_SCREEN:-1600x1000x24}" \
  tcp:5900 'x11vnc -display :99 -forever -shared -nopw -localhost -quiet -rfbport 5900' \
  tcp:5901 'x11vnc -display :99 -forever -shared -nopw -localhost -quiet -rfbport 5901 -viewonly' \
  tcp:6080 'websockify --web=/usr/share/novnc 6080 localhost:5900' \
  tcp:6081 'websockify --web=/usr/share/novnc 6081 localhost:5901' \
  "tcp:${APP_PORT}" "uv run uvicorn autotester.ui.app:app --host 0.0.0.0 --port ${APP_PORT} --no-access-log"
