#!/usr/bin/env bash
# One-file container diagnostics: writes container-debug-<timestamp>.log with every log needed to
# see why the AutoTester image fails (build, image config, permissions, run, logs, state), then a
# DIAGNOSIS section that names the likely cause and fix. Secrets are redacted in layers (see
# "redaction" below): real values first, then secret-looking names; if that is unavailable the log
# keeps only headers and signature lines. Still review the log before sharing it.
#
# Usage: scripts/container_diagnose.sh [--image TAG] [--no-build] [--timeout N] [--out DIR]
#                                      [--gcloud SERVICE --region REGION] [--secrets-file FILE]
#   --image TAG      diagnose an existing image; skips the build
#   --no-build       skip the build and use the existing local tag autotester-debug:local
#   --timeout N      seconds to wait for readiness (default 240)
#   --out DIR        directory for the log and summary.md (default .)
#   --gcloud/--region  append Cloud Run logs for the service (needs gcloud)
#   --secrets-file F extra secret values to mask everywhere: one per line, or KEY=VALUE lines
# Exit: 0 healthy; 1 a check failed (see DIAGNOSIS); 2 usage or no docker.
# redact and diagnose live in scripts/container_diagnose_lib.sh (sourced; tests use it without docker).

# shellcheck source=container_diagnose_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/container_diagnose_lib.sh"

_sec() { printf '\n===== SECTION %s =====\n' "$1" >>"$LOG"; echo "== $1" >&2; }
_run() { { echo "\$ $*"; "$@" 2>&1; echo "[exit=$?]"; } | redact >>"$LOG"; }

main() {
  set -u
  local image="" nobuild=0 timeout=240 out="." gsvc="" region="" ts root sfile="" vdir
  while [ $# -gt 0 ]; do
    case "$1" in
      --image) image="${2:?--image needs a tag}"; nobuild=1; shift 2 ;;
      --no-build) nobuild=1; shift ;;
      --timeout) timeout="${2:?--timeout needs seconds}"; shift 2 ;;
      --out) out="${2:?--out needs a directory}"; shift 2 ;;
      --gcloud) gsvc="${2:?--gcloud needs a service}"; shift 2 ;;
      --region) region="${2:?--region needs a region}"; shift 2 ;;
      --secrets-file) sfile="${2:?--secrets-file needs a file}"; shift 2 ;;
      -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}"; return 0 ;;
      *) echo "unknown argument: $1" >&2; return 2 ;;
    esac
  done
  command -v docker >/dev/null 2>&1 || { echo "docker not found on PATH" >&2; return 2; }
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  mkdir -p "$out"; out="$(cd "$out" && pwd)"
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  LOG="$out/container-debug-$ts.log"; : >"$LOG"
  local tag="${image:-autotester-debug:local}" cname="autotester-smoke-$$"
  local origins="${AUTOTESTER_ALLOWED_ORIGINS:-http://localhost:8000}" build_rc="skipped"
  umask 077  # every temp file below is 0600 (the values dir is 0700)
  vdir="$(mktemp -d)"; chmod 700 "$vdir"; _REDACT_VALUES="$vdir/values"; : >"$_REDACT_VALUES"
  # expand now: cname and vdir are local to main
  trap "docker rm -f '$cname' >/dev/null 2>&1; rm -rf '$vdir'" EXIT
  echo "container-debug log, UTC $ts, image tag $tag" >>"$LOG"
  [ -f "$root/.env" ] && _redact_env_load "$root/.env"
  [ -z "$sfile" ] || _redact_env_load "$sfile"
  docker image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$tag" 2>/dev/null | cut -d= -f2- | _redact_load
  if ! _redact_gnu_sed; then
    echo "NOTICE: full redaction unavailable (sed is not GNU): this log keeps only headers, signature lines and DIAGNOSIS." | tee -a "$LOG" >&2
  fi

  _sec "1 HOST AND DOCKER"
  _run uname -a; _run docker version; { docker info 2>&1 | head -40 | redact; } >>"$LOG"
  _sec "2 GIT REVISION"
  _run git -C "$root" rev-parse HEAD
  if [ "$nobuild" -eq 0 ]; then
    _sec "3 DOCKER BUILD (--no-cache --progress=plain)"
    ( cd "$root" && DOCKER_BUILDKIT=1 docker build --no-cache --progress=plain -t "$tag" . ) 2>&1 | redact >>"$LOG"
    build_rc="${PIPESTATUS[0]}"; echo "[build exit=$build_rc]" >>"$LOG"
  else
    _sec "3 DOCKER BUILD"; echo "skipped (--image or --no-build); using $tag" >>"$LOG"
  fi

  _sec "4 IMAGE INSPECT (env names only)"
  local img_user
  img_user="$(docker image inspect --format '{{.Config.User}}' "$tag" 2>/dev/null)"
  {
    echo "Id/digest: $(docker image inspect --format '{{.Id}} {{.RepoDigests}}' "$tag" 2>&1)"
    echo "User: ${img_user:-<empty: root>}"
    echo "Entrypoint: $(docker image inspect --format '{{json .Config.Entrypoint}}' "$tag" 2>&1)"
    echo "Cmd: $(docker image inspect --format '{{json .Config.Cmd}}' "$tag" 2>&1)"
    echo "Env names:"
    docker image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$tag" 2>&1 | cut -d= -f1 | sed 's/^/  /'
  } | redact >>"$LOG"

  _sec "5 PERMISSION CHECK"
  local chk who rc_import=0 pcheck
  chk='id; readlink -f /opt/venv/bin/python; namei -l /opt/venv/bin/python; ls -ld /opt/uv-python /opt/venv /data; /opt/venv/bin/python -c "import autotester; print(\"IMPORT_OK\")"; echo "[import rc=$?]"'
  for who in "image user" "--user 10001:10001"; do
    echo "--- as: $who" >>"$LOG"
    if [ "$who" = "image user" ]; then pcheck="$(docker run --rm --entrypoint sh "$tag" -c "$chk" 2>&1)"
    else pcheck="$(docker run --rm --user 10001:10001 --entrypoint sh "$tag" -c "$chk" 2>&1)"; fi
    printf '%s\n' "$pcheck" | redact >>"$LOG"
    printf '%s\n' "$pcheck" | grep -q 'IMPORT_OK' || rc_import=1
  done

  _sec "6 RUN WITH PORT=8000 (readiness wait up to ${timeout}s)"
  local ready="no" t0=$SECONDS elapsed=0 state
  docker run -d --name "$cname" -p 8000:8000 -e PORT=8000 -e "AUTOTESTER_ALLOWED_ORIGINS=$origins" "$tag" 2>&1 | redact >>"$LOG"
  while [ $((SECONDS - t0)) -lt "$timeout" ]; do
    if curl -fsS -o /dev/null -m 3 http://127.0.0.1:8000/healthz 2>/dev/null; then ready="yes"; break; fi
    state="$(docker inspect --format '{{.State.Running}}' "$cname" 2>/dev/null)"
    [ "$state" = "true" ] || break
    sleep 3
  done
  elapsed=$((SECONDS - t0))
  if [ "$ready" = "yes" ]; then echo "READINESS: READY after ${elapsed}s" >>"$LOG"
  else echo "READINESS: NOT READY after ${elapsed}s (limit ${timeout}s)" >>"$LOG"; fi

  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$cname" 2>/dev/null | cut -d= -f2- | _redact_load
  _sec "7 DOCKER LOGS"
  docker logs "$cname" 2>&1 | redact >>"$LOG"
  _sec "8 DOCKER PS AND STATE"
  _run docker ps -a
  docker inspect --format 'State: ExitCode={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}} Error={{.State.Error}} Status={{.State.Status}}' "$cname" 2>&1 | redact >>"$LOG"
  if [ -n "$gsvc" ]; then
    _sec "8a CLOUD RUN LOGS ($gsvc)"
    if command -v gcloud >/dev/null 2>&1; then
      local rev
      rev="$(gcloud run services describe "$gsvc" --region "${region:?--region is required with --gcloud}" --format='value(status.latestCreatedRevisionName)' 2>&1)"
      echo "revision: $rev" >>"$LOG"
      _run gcloud run services logs read "$gsvc" --region "$region" --limit 300
      _run gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$gsvc\" AND resource.labels.revision_name=\"$rev\"" --limit 300 --freshness 1d --format 'value(timestamp,severity,textPayload,protoPayload.status.message)'
    else echo "gcloud not found; skipped" >>"$LOG"; fi
  fi

  _sec "9 DIAGNOSIS"
  local dfile="$out/.diag-input.$$" dout="$out/.diag-out.$$" drc
  cat "$LOG" >"$dfile"
  if [ "$build_rc" != "skipped" ] && [ "$build_rc" != "0" ]; then echo "BUILD FAILED rc=$build_rc" >>"$dfile"; fi
  diagnose "$dfile" >"$dout"; drc=$?
  cat "$dout" >>"$LOG"
  rm -f "$dfile"
  local ok=1 reasons=""
  case "$img_user" in 10001|10001:*) ;; *) ok=0; reasons="$reasons image User is '${img_user:-root}', not 10001;" ;; esac
  [ "$rc_import" -eq 0 ] || { ok=0; reasons="$reasons import autotester failed in the permission check;"; }
  [ "$ready" = "yes" ] || { ok=0; reasons="$reasons port 8000 never became ready;"; }
  [ "$drc" -eq 0 ] || { ok=0; reasons="$reasons DIAGNOSIS reported $drc failure signature(s);"; }
  { [ "$build_rc" = "skipped" ] || [ "$build_rc" = "0" ]; } || { ok=0; reasons="$reasons docker build exit $build_rc;"; }
  {
    echo "# Container smoke summary"; echo
    echo "- image: \`$tag\`"; echo "- image User: \`${img_user:-root}\`"
    echo "- import autotester (both users): $([ "$rc_import" -eq 0 ] && echo ok || echo FAILED)"
    echo "- ready on 8000: $ready (waited ${elapsed}s)"; echo "- build exit: $build_rc"
    echo "- result: $([ "$ok" -eq 1 ] && echo PASS || echo "FAIL -$reasons")"
    echo; echo "## DIAGNOSIS"; echo '```'; cat "$dout"; echo '```'
    echo; echo "Full log: \`$(basename "$LOG")\`"
  } >"$out/summary.md"
  rm -f "$dout"
  echo "RESULT: $([ "$ok" -eq 1 ] && echo PASS || echo "FAIL -$reasons")" | tee -a "$LOG" >&2
  echo "log: $LOG" >&2
  [ "$ok" -eq 1 ]
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; exit $?; fi
