#!/usr/bin/env bash
# Sourced library of scripts/container_diagnose.sh: the layered `redact` filter (stdin -> stdout) and
# `diagnose LOGFILE` (the DIAGNOSIS signatures). No side effects when sourced; tests source it directly.

# ---- redaction -------------------------------------------------------------------------------
# redact: stdin -> stdout, layered, strongest first. The log is shared outside the team, so it fails
# safe: when unsure, mask. The KEY NAME is kept; only the value goes.
#  1 value layer: _REDACT_VALUES names a 0600 file of real secret values (repo-root .env and
#    --secrets-file via _redact_env_load, image and container Env). Every exact occurrence is
#    masked, any key name. A .env is read by the repo's own parser (python-dotenv, through
#    core.redact_cli --values-from-env) when python imports; the dotenv-compatible awk reader
#    (_redact_assignments) always runs too, and is the only reader without python.
#  2 name layer (GNU sed): value after a secret-looking name (PW|PASS|PASSWORD|SECRET|TOKEN|KEY|
#    APIKEY|AUTH|CREDENTIAL|COOKIE|SESSION|PRIVATE as a segment or suffix) for = : => whitespace,
#    XML tags, URL-encoded %3D, JSON (escaped quotes too), --password x, -p x; URL user:pass@,
#    Authorization/Cookie headers, ?code=, PEM blocks, token shapes (AKIA ghp_ JWT AIza xox sk-).
#  3 python layer: when python and the repo src import, the values go through core.redact.Redactor
#    (exact value plus its encodings) before the sed layers. One concept, one place. If it fails,
#    a NOTICE is printed and that block takes the fail-safe path: never raw text, never nothing.
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
_redact_cli() { PYTHONPATH="$(_redact_home)/src" "$_REDACT_PY" -m autotester.core.redact_cli "$@"; }

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

# _redact_assignments: stdin .env / secrets-file lines -> candidate values, read the way
# python-dotenv reads them (optional export, spaces around =, ' and " quotes, multiline quoted
# values, an unquoted value ends at " #"). It over-emits on purpose: each value goes out raw AND
# trimmed, comment-stripped, unquoted and unescaped. A bare line is a value itself; a short "value"
# such as base64 padding keeps the whole line. Without python this is the only .env reader.
_redact_assignments() {
  awk '
    function emit(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); if (s != "") print s }
    function unesc(s) { gsub(/\\\\/, "\001", s); gsub(/\\"/, "\"", s); gsub(/\\\047/, "\047", s); gsub(/\001/, "\\", s); return s }
    function closeq(s, q,   i, ch) { for (i = 1; i <= length(s); i++) { ch = substr(s, i, 1); if (ch == "\\") { i++; continue } if (ch == q) return i } return 0 }
    function inner(s,   n, i, parts) { emit(s); emit(unesc(s)); n = split(s, parts, /\\n/); if (n > 1) for (i = 1; i <= n; i++) emit(parts[i]) }
    { line = $0; sub(/\r$/, "", line) }
    inq != "" { p = closeq(line, inq); if (p == 0) { inner(line); next } inner(substr(line, 1, p - 1)); emit(line); inq = ""; next }
    line ~ /^[[:space:]]*(#|$)/ { next }
    { l = line; sub(/^[[:space:]]*export[[:space:]]+/, "", l)
      if (!match(l, /^[[:space:]]*[A-Za-z_][A-Za-z0-9_.-]*[[:space:]]*=/)) { print line; next }
      raw = substr(l, RLENGTH + 1); emit(raw); old = raw; gsub(/^["\047]|["\047]$/, "", old); emit(old)
      v = raw; sub(/^[ \t]+/, "", v); q = substr(v, 1, 1)
      if (q == "\"" || q == "\047") {
        rest = substr(v, 2); p = closeq(rest, q)
        if (p == 0) { inner(rest); inq = q } else inner(substr(rest, 1, p - 1))
      } else { sub(/[ \t]+#.*$/, "", v); emit(v) }
      if (length(old) < 6 && !(old == "" && l ~ /^[[:space:]]*[A-Z_][A-Z0-9_]*[[:space:]]*=$/)) print line }
  '
}

# _redact_load: add the candidate values on stdin to the value file (0600) and rebuild its sed script.
_redact_load() {
  local vf="$_REDACT_VALUES"
  [ -n "$vf" ] || { cat >/dev/null; return 0; }
  ( umask 077
    { [ -f "$vf" ] && cat "$vf"; cat; } | _redact_filter_values >"$vf.new" && mv "$vf.new" "$vf"
    sed -e 's#[][\\/.*^$|+?(){}~]#\\&#g' -e 's#^#s~#' -e 's#$#~<redacted>~g#' "$vf" >"$vf.sed" 2>/dev/null || : >"$vf.sed" )
}

# _redact_env_load FILE: load a .env / secrets file's values. Both readers run and their union is
# masked: python-dotenv (the parser core.env uses) when python imports, plus the awk reader.
# Values travel only through pipes and the 0600 value file, never argv.
_redact_env_load() {
  local f="$1"
  { _redact_assignments <"$f"
    if _redact_python && ! _redact_cli --values-from-env "$f"; then
      echo "NOTICE: dotenv value reader failed for $(basename "$f"); only the awk reader's values are used." >&2
    fi
  } | _redact_load
}

# _redact_failsafe [REASON]: the sed or python layers are unavailable, so keep only what DIAGNOSIS
# needs. A kept line that mentions a secret-like word is withheld too. One summary line says how
# many were withheld and why.
_redact_failsafe() {
  awk -v why="${1:-sed is not GNU}" '
    BEGIN {
      keep = "^(=====|== |\\$ |\\[(FAIL|INFO|OK|NOTICE|exit=|build exit)|RESULT:|READINESS:|State:|[0-9]+ failure signature|Id/digest:|User:|Entrypoint:)|PREFLIGHT FAIL|Permission denied|PermissionError|Errno 13|OOMKilled|exceeded.*memory limit|already in use|already allocated|exec format error|bad interpreter|\\.env is absent|IMPORT_OK|probe failed|uid=|readlink|Cannot open display|container service|Xvfb|x11vnc|websockify"
      secret = "key|token|secret|pass|pwd|pw=|auth|cred|cookie|session|private|://[^ ]*@|[?&]code="
    }
    { l = tolower($0) }
    $0 ~ keep && l !~ secret { print; next }
    { held++ }
    END { if (held) print "[" held " line(s) withheld: full redaction unavailable (" why ")]" }
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

# _redact_sed: the value and name sed layers (GNU sed), else the fail-safe with REASON.
_redact_sed() {
  local vf="$_REDACT_VALUES"
  if ! _redact_gnu_sed; then _redact_failsafe "${1:-sed is not GNU}"
  elif [ -n "$vf" ] && [ -s "$vf.sed" ]; then sed -E -f "$vf.sed" -e "$_REDACT_SED"
  else sed -E -e "$_REDACT_SED"; fi
}

redact() {
  local vf="$_REDACT_VALUES"
  if [ -z "$vf" ] || [ ! -s "$vf" ] || ! _redact_python; then _redact_sed; return; fi
  # python layer: buffer the block in the 0700 values dir (0600 files) so a failure is detectable.
  ( umask 077
    cat >"$vf.in"
    if _redact_cli "$vf" <"$vf.in" >"$vf.out"; then
      _redact_sed <"$vf.out"
    else
      echo "NOTICE: python redaction (redact_cli) failed: this block keeps only headers and signature lines." >&2
      echo "[NOTICE: python redaction failed; fail-safe output follows]"
      if _redact_gnu_sed; then _redact_sed <"$vf.in" | _redact_failsafe "python redaction failed"
      else _redact_failsafe "python redaction failed" <"$vf.in"; fi
    fi
    rm -f "$vf.in" "$vf.out" )
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
