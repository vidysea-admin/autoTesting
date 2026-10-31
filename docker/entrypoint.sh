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

# The data root is AUTOTESTER_ROOT (hosting.md HO3; core/paths.py::repo_root is its only reader). An
# operator or compose value always wins. Unset and /app not writable (the image runs as uid 10001
# with a root-owned /app) -> /data, the one writable volume. A writable /app (the dev compose bind
# mount) keeps the repo-root behaviour so state survives recreate (docker.md D6).
if [ -z "${AUTOTESTER_ROOT:-}" ] && [ ! -w /app ]; then
  export AUTOTESTER_ROOT=/data
fi
if [ -n "${AUTOTESTER_ROOT:-}" ]; then
  mkdir -p "$AUTOTESTER_ROOT/projects" "$AUTOTESTER_ROOT/.work" 2>/dev/null || true
  [ -w "$AUTOTESTER_ROOT" ] || echo "WARNING: AUTOTESTER_ROOT=$AUTOTESTER_ROOT is not writable by uid $(id -u); runs and queue state will fail" >&2
fi

# True only when EVERY state area is on Mongo, so no state needs the /data volume (mongo-store M28):
# the global AUTOTESTER_STORE=mongo, no AUTOTESTER_STORE_AREAS entry sending an area back to file,
# and auth flipped by its OWN entry (auth/store.py::_auth_on_mongo ignores the global value).
# Conservative on purpose: anything it cannot read as "all mongo" is "not all", which keeps the warning.
all_state_on_mongo() {
  [ "${AUTOTESTER_STORE:-}" = "mongo" ] || return 1
  local items=() item area backend auth=""
  IFS=, read -ra items <<< "${AUTOTESTER_STORE_AREAS:-}" || true
  for item in "${items[@]}"; do
    item="${item// /}"
    [ -n "$item" ] || continue
    area="${item%%=*}"
    backend="${item#*=}"
    [ "$backend" = "mongo" ] || return 1
    [ "$area" = "auth" ] && auth=1
  done
  [ -n "$auth" ]
}

# One loud line when the data root is not a persistent volume: every deploy would then wipe the
# accounts and projects (docker/DEPLOY.md, "Persistent storage"). Informational ONLY: it never
# exits or fails, because DevOps may not have mounted the volume yet and a refused start would
# take the live site down. Ephemeral = the root shares a device with / or has no /proc/mounts line
# (a volume mounted at an ancestor counts). AUTOTESTER_EPHEMERAL_OK=1 silences it (local docker).
# With every area on Mongo the data root holds only scratch, so it is silent (all_state_on_mongo).
warn_if_ephemeral() {
  [ "${AUTOTESTER_EPHEMERAL_OK:-}" = "1" ] && return 0
  if all_state_on_mongo; then
    echo "entrypoint: every state area is on Mongo; the data root holds scratch only (docker/DEPLOY.md, State store on MongoDB)"
    return 0
  fi
  local root="${AUTOTESTER_ROOT:-/app}" mounts="${AUTOTESTER_MOUNTS_FILE:-/proc/mounts}"
  local root_dev slash_dev mp="$root" listed=""
  root_dev=$(stat -c %d "$root" 2>/dev/null) || return 0
  slash_dev=$(stat -c %d / 2>/dev/null) || return 0
  [ -r "$mounts" ] || return 0
  while [ -n "$mp" ]; do
    if [ "$mp" != "/" ] && [ "$(awk -v m="$mp" '$2 == m && $3 != "tmpfs" && $3 != "ramfs" { f = 1 } END { print f + 0 }' "$mounts")" = 1 ]; then
      listed=1
      break
    fi
    [ "${mp%/*}" = "$mp" ] && break
    mp="${mp%/*}"
  done
  if [ "$root_dev" = "$slash_dev" ] || [ -z "$listed" ]; then
    echo "WARNING: storage is not persistent: AUTOTESTER_ROOT=$root is on the container's own filesystem; accounts and projects are LOST on every deploy. Mount a volume at $root (docker/DEPLOY.md, Persistent storage)." >&2
  fi
  return 0
}
warn_if_ephemeral || true

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
  "tcp:${APP_PORT}" "uv run uvicorn autotester.ui.app:app --host 0.0.0.0 --port ${APP_PORT} "
