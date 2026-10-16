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
# The functions below are sourceable (redact, diagnose) so tests run without docker.

# ---- redaction -------------------------------------------------------------------------------
# redact: stdin -> stdout, layered, strongest first. The log is shared outside the team, so it fails
# safe: when unsure, mask. The KEY NAME is kept; only the value goes.
#  1 value layer: _REDACT_VALUES names a file of real secret values (repo-root .env, image and
#    container Env, --secrets-file; see _redact_load). Every exact occurrence is masked, any key name.
#  2 name layer (GNU sed): value after a secret-looking name (PW|PASS|PASSWORD|SECRET|TOKEN|KEY|
#    APIKEY|AUTH|CREDENTIAL|COOKIE|SESSION|PRIVATE as a segment or suffix) for = : => whitespace,
#    XML tags, URL-encoded %3D, JSON (escaped quotes too), --password x, -p x; URL user:pass@,
#    Authorization/Cookie headers, ?code=, PEM blocks, token shapes (AKIA ghp_ JWT AIza xox sk-).
#  3 python layer: when python and the repo src import, the values go through core.redact.Redactor
#    (exact value plus its encodings) before the sed layers. One concept, one place.
#  4 fail safe: sed that is not GNU cannot run layer 2 reliably, so only headers, signature lines
#    and the DIAGNOSIS block are kept (see _redact_failsafe), with a loud notice.
_REDACT_VALUES="${_REDACT_VALUES:-}"
_REDACT_PY=""
_redact_home() { (cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); }
_redact_gnu_sed() { sed --version 2>/dev/null | head -n 1 | grep -q 'GNU sed'; }
_redact_python() {
  [ -z "${REDACT_NO_PYTHON:-}" ] || return 1
  local c home
  if [ -z "$_REDACT_PY" ]; then
    _REDACT_PY=none; home="$(_redact_home)"
    for c in "${AUTOTESTER_PYTHON:-python3}" python3 python; do
      if command -v "$c" >/dev/null 2>&1 &&
         PYTHONPATH="$home/src" "$c" -c 'import autotester.core.redact_cli' >/dev/null 2>&1; then
        _REDACT_PY="$c"; break
      fi
    done
  fi
  [ "$_REDACT_PY" != none ]
}

# _redact_filter_values: stdin candidate values -> stdout the ones worth masking, longest first.
# Skips values shorter than 6, common words, paths, plain numbers/versions and localhost URLs.
_redact_filter_values() {
  awk '
    BEGIN { n = split("true false null none yes no on off localhost root admin", c, " "); for (i = 1; i <= n; i++) common[c[i]] = 1 }
    { v = $0; sub(/\r$/, "", v) }
    length(v) < 6 { next }
    tolower(v) in common { next }
    v ~ /^\/[A-Za-z0-9_.\/:-]*$/ { next }
    v ~ /^[0-9.:-]+$/ { next }
    v ~ /localhost|127\.0\.0\.1/ { next }
    { print length(v) "\t" v }
  ' | sort -t "$(printf '\t')" -k1,1nr | cut -f2- | awk '!seen[$0]++'
}

# _redact_assignments: stdin .env / secrets-file lines -> candidate values (the value of KEY=VALUE,
# quotes stripped; a bare line is a value itself; a short "value" such as base64 padding keeps the line).
_redact_assignments() {
  awk '
    /^[[:space:]]*#/ { next }
    { line = $0; sub(/\r$/, "", line); sub(/^[[:space:]]*export[[:space:]]+/, "", line)
      if (match(line, /^[A-Za-z_][A-Za-z0-9_]*=/)) {
        v = substr(line, RLENGTH + 1); gsub(/^["\047]|["\047]$/, "", v); print v
        if (length(v) < 6) print line
      } else print line }
  '
}

# _redact_load: add the candidate values on stdin to the value file and rebuild its sed script.
_redact_load() {
  local vf="$_REDACT_VALUES"
  [ -n "$vf" ] || { cat >/dev/null; return 0; }
  { [ -f "$vf" ] && cat "$vf"; cat; } | _redact_filter_values >"$vf.new" && mv "$vf.new" "$vf"
  sed -e 's#[][\\/.*^$|+?(){}~]#\\&#g' -e 's#^#s~#' -e 's#$#~<redacted>~g#' "$vf" >"$vf.sed" 2>/dev/null || : >"$vf.sed"
}

# _redact_failsafe: the sed layers are unavailable, so keep only what DIAGNOSIS needs. A kept line
# that mentions a secret-like word is withheld too. One summary line says how many were withheld.
_redact_failsafe() {
  awk '
    BEGIN {
      keep = "^(=====|== |\\$ |\\[(FAIL|INFO|OK|exit=|build exit)|RESULT:|READINESS:|State:|[0-9]+ failure signature|Id/digest:|User:|Entrypoint:)|PREFLIGHT FAIL|Permission denied|PermissionError|Errno 13|OOMKilled|exceeded.*memory limit|already in use|already allocated|exec format error|bad interpreter|\\.env is absent|IMPORT_OK|probe failed|uid=|readlink|Cannot open display|container service|Xvfb|x11vnc|websockify"
      secret = "key|token|secret|pass|pwd|pw=|auth|cred|cookie|session|private|://[^ ]*@|[?&]code="
    }
    { l = tolower($0) }
    $0 ~ keep && l !~ secret { print; next }
    { held++ }
    END { if (held) print "[" held " line(s) withheld: full redaction unavailable (sed is not GNU)]" }
  '
}

# Name layer rule pieces. _RN is the key name (a segment or suffix of the name), _RT its optional
# tail (_FILE, -id, id), _RS the separator (= : => whitespace-colon, JSON quote, %3D, %22%3A%22).
_RT='([_.-][A-Za-z0-9_.-]*|id)?'
_RS='(\\?["'"'"']?[[:space:]]*(=>|[=:])[[:space:]]*|%22%3[Aa]%22|%3[Dd])'
_RN_I="(((password|passwd|secret|token|credentials?|cookie|api[_-]?key|private|session)|(^|[^A-Za-z])(pass|pwd|pw|key|auth))${_RT}${_RS})"
_RN_C="([a-z](Key|Pass|Pwd|Pw|Auth)${_RT}${_RS})"
# _redact_valrules PREFIX FLAGS: escaped-JSON, double-quoted, single-quoted, then unquoted values.
_redact_valrules() {
  printf '%s\n' \
    "s/($1)\\\\\"([^\\\\\"]|\\\\[^\"])*\\\\\"/\\1\\\\\"<redacted>\\\\\"/$2" \
    "s/($1)\"(\\\\.|[^\"\\\\])*\"/\\1\"<redacted>\"/$2" \
    "s/($1)'[^']*'/\\1'<redacted>'/$2" \
    "s/($1)[^[:space:]\"'&<>\\][^[:space:]\"'&]*/\\1<redacted>/$2"
}
_redact_script() {
  cat <<'EOF'
s/-----BEGIN [A-Z ]*-----.*-----END [A-Z ]*-----/<redacted-pem>/g
/-----BEGIN [A-Z ]*-----/{
s/-----BEGIN [A-Z ]*-----.*/<redacted-pem>/
x
s/.*/PEM/
x
b pemend
}
x
/^PEM$/{
x
/^[A-Za-z0-9+\/=]{32,}[[:space:]]*$/{
s/.*/<redacted-pem-body>/
b pemend
}
x
s/.*//
x
b pemend
}
x
:pemend
s/((proxy-)?authorization\\?["']?[[:space:]]*[=:][[:space:]]*).*/\1<redacted>/I
s/((set-)?cookie[[:space:]]*:[[:space:]]*).*/\1<redacted>/I
s/(bearer[[:space:]]+)[A-Za-z0-9._~+\/=-]+/\1<redacted>/Ig
s#(//)[^/@[:space:]"']+@#\1<redacted>@#g
s/(<[A-Za-z0-9_.:-]*(password|passwd|secret|token|credentials?|api[_-]?key|pass|pw|key)[A-Za-z0-9_.:-]*>)[^<]+/\1<redacted>/Ig
s/(--?[A-Za-z0-9_-]*(password|passwd|pwd|pass|pw|token|secret|key|auth|credentials?|session|cookie)[A-Za-z0-9_-]*[[:space:]]+)[^-[:space:]][^[:space:]]*/\1<redacted>/Ig
s/((^|[[:space:]])-p[[:space:]]+)[^-\/.0-9[:space:]][^[:space:]]*/\1<redacted>/g
s/((^|[[:space:]])-p[[:space:]]+)[0-9][0-9:]*[^0-9:[:space:]][^[:space:]]*/\1<redacted>/g
s/([?&]code=)[^&[:space:]"']+/\1<redacted>/Ig
s/("code"[[:space:]]*:[[:space:]]*)"[^"]*"/\1"<redacted>"/Ig
EOF
  _redact_valrules "$_RN_I" Ig
  _redact_valrules "$_RN_C" g
  cat <<'EOF'
s/((^|[^A-Za-z0-9])(password|passwd|secret|token|api[_-]?key)([_.-][A-Za-z0-9_.-]*)?[[:space:]]+((is|was)[[:space:]]+)?)[^[:space:]=:<][^[:space:]]*/\1<redacted>/Ig
s/\b(AKIA|ASIA)[A-Z0-9]{16}/\1<redacted>/g
s/(gh[pousr]_)[A-Za-z0-9]{20,}/\1<redacted>/g
s/(github_pat_)[A-Za-z0-9_]{20,}/\1<redacted>/g
s/eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]*)?/eyJ<redacted>/g
s/(xox[baprs]-)[A-Za-z0-9-]{8,}/\1<redacted>/g
s/(AIza)[A-Za-z0-9_-]{20,}/\1<redacted>/g
s/(sk-)[A-Za-z0-9_-]{16,}/\1<redacted>/g
EOF
}
_REDACT_SED="$(_redact_script)"

redact() {
  local vf="$_REDACT_VALUES" py=0 home
  if [ -n "$vf" ] && [ -s "$vf" ] && _redact_python; then py=1; home="$(_redact_home)"; fi
  if ! _redact_gnu_sed; then
    if [ "$py" -eq 1 ]; then PYTHONPATH="$home/src" "$_REDACT_PY" -m autotester.core.redact_cli "$vf" | _redact_failsafe
    else _redact_failsafe; fi
    return
  fi
  if [ "$py" -eq 1 ]; then
    PYTHONPATH="$home/src" "$_REDACT_PY" -m autotester.core.redact_cli "$vf" | sed -E -f "$vf.sed" -e "$_REDACT_SED"
  elif [ -n "$vf" ] && [ -s "$vf.sed" ]; then sed -E -f "$vf.sed" -e "$_REDACT_SED"
  else sed -E -e "$_REDACT_SED"; fi
}

# diagnose LOGFILE: print one [FAIL]/[INFO] line (cause + fix) per known signature found in LOGFILE.
# Return status = number of FAIL signatures (max 100); 0 means none.
diagnose() {
  local f="$1" fails=0 cr
  cr="$(printf '\r')"
  _hit() { grep -Eq -- "$1" "$f"; }
  _fail() { echo "[FAIL] $1: $2 Fix: $3"; fails=$((fails + 1)); }
  if _hit '(/opt/venv/bin/python.*Permission denied|Permission denied.*/opt/venv/bin/python|ExitCode=126|exit code:? 126|exited with (status|code) 126|exit\(126\))'; then
    _fail perm-denied "python cannot be executed (Permission denied / exit 126): the image is stale (built before f572a4b5, python under /root) or the wrong USER runs it." "rebuild with 'docker build --no-cache' from current master, redeploy by digest, and confirm the image User is 10001."
  fi
  if _hit '(PermissionError: \[Errno 13\]|Errno 13\] Permission denied|(cannot (create|open|write)|mkdir|touch)[^[:cntrl:]]*Permission denied)'; then
    _fail app-perm "the app writes under a path uid 10001 cannot write (PermissionError)." "make the directory writable by uid 10001 in the image, or point it at /data (the writable volume)."
  fi
  if _hit 'PREFLIGHT FAIL'; then
    _fail preflight "the entrypoint preflight refused to start; its uid and path lines follow." "rebuild from master (see perm-denied) and compare the uid and permissions below."
    grep -E -A8 'PREFLIGHT FAIL' "$f" | grep -E 'PREFLIGHT FAIL|uid=|readlink|perms|HINT|^ *[fd]:|^[-dl][-rwxs]{9}' | sed 's/^/        /'
  fi
  if _hit '(OOMKilled=true|"OOMKilled": *true|exceeded.*memory limit|Memory limit .*exceeded)'; then
    _fail oom "the container was killed for running out of memory." "give it at least 4 GiB (Cloud Run: --memory 4Gi; compose: AUTOTESTER_MEM_LIMIT=6g)."
  fi
  if _hit '(READINESS: NOT READY|STARTUP TCP probe failed|startup probe failed)'; then
    _fail not-ready "port 8000 never accepted connections within the wait." "raise the startup-probe timeout (failureThreshold x periodSeconds >= 180 s), check PORT and that the container port is 8000, and read the container logs section for the first error."
  fi
  if _hit 'Address already in use|address already in use|port is already allocated'; then
    _fail port-in-use "the port is already bound by another process or container." "stop the other listener (docker ps -a; ss -ltnp) or map a different host port."
  fi
  if _hit '(GCS|gcsfuse|Cloud Storage|gs://)[^[:cntrl:]]*([Ee]rror|[Ff]ailed|denied|not found|403|404)|FileNotFoundError[^[:cntrl:]]*\.env'; then
    _fail gcs-or-env "a Cloud Storage download/mount or a required .env file failed." "check the bucket name and that the service account has storage.objects access; the app starts without /app/.env but provider keys are then missing."
  fi
  if _hit '(Xvfb|x11vnc|websockify)[^[:cntrl:]]*([Ff]ailed|[Cc]annot|[Ee]rror|not found|died)|Cannot open display|Fatal server error|container service (exited|startup timed out|could not start)'; then
    _fail display "Xvfb, x11vnc or websockify failed, so the supervisor stopped the stack." "read the lines before 'container service' in the container logs; make sure /tmp is writable and shm is not tiny."
  fi
  if _hit '[Ee]xec format error'; then
    _fail exec-format "the image architecture does not match this host (exec format error)." "build for linux/amd64: docker build --platform linux/amd64 ."
  fi
  if _hit "bad interpreter|\^M|/bin/(ba)?sh${cr}"; then
    _fail crlf "a shell script has Windows (CRLF) line endings (bad interpreter)." "check out with LF endings (.gitattributes sets *.sh eol=lf), run 'git add --renormalize .' and rebuild."
  fi
  if _hit '/app/\.env is absent'; then
    echo "[INFO] env-absent: /app/.env is not in the image. Expected; the app starts without it (provider keys and logins are then unset)."
  fi
  if [ "$fails" -eq 0 ]; then echo "[OK] no known failure signature found"; else echo "$fails failure signature(s) found"; fi
  [ "$fails" -gt 100 ] && fails=100
  return "$fails"
}

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
      -h|--help) sed -n '2,19p' "${BASH_SOURCE[0]}"; return 0 ;;
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
  vdir="$(mktemp -d)"; chmod 700 "$vdir"; _REDACT_VALUES="$vdir/values"; : >"$_REDACT_VALUES"
  # expand now: cname and vdir are local to main
  trap "docker rm -f '$cname' >/dev/null 2>&1; rm -rf '$vdir'" EXIT
  echo "container-debug log, UTC $ts, image tag $tag" >>"$LOG"
  [ -f "$root/.env" ] && _redact_assignments <"$root/.env" | _redact_load
  [ -z "$sfile" ] || _redact_assignments <"$sfile" | _redact_load
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
