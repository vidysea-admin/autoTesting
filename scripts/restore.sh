#!/usr/bin/env bash
# One job: verify a backup.sh archive against its sha256 manifest, then restore it into a state root.
# Usage: restore.sh ARCHIVE.tar.gz [--root DIR] [--force]   (needs ARCHIVE.manifest and .manifest.sha256 beside it)
set -euo pipefail
export LC_ALL=C

ROOT="${AUTOTESTER_DATA_DIR:-/data}"
FORCE=0
ARCHIVE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) sed -n 2,3p "$0"; exit 0 ;;
    -*) echo "restore: unknown argument $1" >&2; exit 2 ;;
    *) ARCHIVE="$1"; shift ;;
  esac
done
refuse() { echo "restore: REFUSED, $1" >&2; exit 1; }
[ -n "$ARCHIVE" ] && [ -f "$ARCHIVE" ] || { echo "restore: archive required and must exist" >&2; exit 2; }
ARCHIVE="$(cd "$(dirname "$ARCHIVE")" && pwd)/$(basename "$ARCHIVE")"
MANIFEST="$ARCHIVE.manifest"
[ -f "$MANIFEST" ] && [ -f "$MANIFEST.sha256" ] || refuse "manifest or manifest.sha256 missing beside the archive"

[ "$(sha256sum < "$MANIFEST" | cut -d' ' -f1)" = "$(tr -d ' \r\n' < "$MANIFEST.sha256")" ] \
  || refuse "manifest sha256 mismatch (tampered or corrupt)"
want="$(awk '$1=="archive_sha256"{print $2}' "$MANIFEST")"
[ -n "$want" ] && [ "$want" = "$(sha256sum < "$ARCHIVE" | cut -d' ' -f1)" ] \
  || refuse "archive sha256 does not match the manifest (tampered or corrupt)"

# Member names and types are checked from the listing before anything is extracted.
TYPES="$(tar -tzvf - < "$ARCHIVE" | cut -c1)"
if printf '%s\n' "$TYPES" | grep -qvE '^[-d]$'; then refuse "archive holds a non-regular member (link or device)"; fi
NAMES="$(tar -tzf - < "$ARCHIVE")"
if printf '%s\n' "$NAMES" | grep -qE '^/|(^|/)\.\.(/|$)'; then refuse "archive holds an absolute or parent-relative path"; fi

if [ -d "$ROOT" ] && [ -n "$(ls -A "$ROOT" 2>/dev/null)" ] && [ "$FORCE" -ne 1 ]; then
  refuse "target $ROOT is not empty (use --force to overwrite)"
fi

CREATED=0; [ -d "$ROOT" ] || { mkdir -p "$ROOT"; CREATED=1; }
ROOT="$(cd "$ROOT" && pwd)"
STAGE="$(mktemp -d "$ROOT/.restore-stage.XXXXXX")"
cleanup() { rm -rf "$STAGE"; [ "$CREATED" -eq 1 ] && [ "$OK" -ne 1 ] && rmdir "$ROOT" 2>/dev/null || true; }
OK=0; trap cleanup EXIT
tar -C "$STAGE" -xzf - < "$ARCHIVE"

[ -z "$(find "$STAGE" ! -type f ! -type d -print -quit)" ] || refuse "extracted tree holds a non-regular entry"
# Allowlist and integrity in one: the staged tree must hash to exactly the manifest entries.
EXPECT="$(sed -n '/^# entries/,$p' "$MANIFEST" | tail -n +2)"
ACTUAL="$(cd "$STAGE" && find . -type f -print0 | sed -z 's|^\./||' | sort -z | xargs -0 -r sha256sum)"
[ "$EXPECT" = "$ACTUAL" ] || refuse "staged files differ from the manifest (extra, missing or modified file)"

# Rename each top-level entry into place (same filesystem as the stage).
shopt -s nullglob dotglob
for e in "$STAGE"/*; do
  name="$(basename "$e")"
  rm -rf "${ROOT:?}/$name"
  mv "$e" "$ROOT/$name"
done
OK=1
echo "restore: $(printf '%s' "$EXPECT" | grep -c . || true) files restored into $ROOT"
