#!/usr/bin/env bash
# One job: verify a backup.sh archive against its sha256 manifest, then restore it into a state root.
# Usage: restore.sh ARCHIVE.tar.gz [--root DIR] [--force]   (needs ARCHIVE.tar.gz.manifest beside it)
set -euo pipefail

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
[ -n "$ARCHIVE" ] && [ -f "$ARCHIVE" ] || { echo "restore: archive required and must exist" >&2; exit 2; }
MANIFEST="$ARCHIVE.manifest"
[ -f "$MANIFEST" ] || { echo "restore: manifest missing: $MANIFEST" >&2; exit 1; }

want="$(awk '$1=="archive_sha256"{print $2}' "$MANIFEST")"
have="$(sha256sum < "$ARCHIVE" | cut -d' ' -f1)"
if [ -z "$want" ] || [ "$want" != "$have" ]; then
  echo "restore: REFUSED, archive sha256 does not match the manifest (tampered or corrupt)" >&2
  exit 1
fi

if [ -d "$ROOT" ] && [ -n "$(ls -A "$ROOT" 2>/dev/null)" ] && [ "$FORCE" -ne 1 ]; then
  echo "restore: REFUSED, target $ROOT is not empty (use --force to overwrite)" >&2
  exit 1
fi

mkdir -p "$ROOT"; ROOT="$(cd "$ROOT" && pwd)"
STAGE="$(mktemp -d "$ROOT/.restore-stage.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
tar -C "$STAGE" -xzf - < "$ARCHIVE"

# Verify every file against the manifest before anything touches the live tree.
(cd "$STAGE" && grep -E '^[0-9a-f]{64} [ *]' "$MANIFEST" | sha256sum -c --quiet -) \
  || { echo "restore: REFUSED, per-file sha256 check failed" >&2; exit 1; }
n="$(grep -cE '^[0-9a-f]{64} [ *]' "$MANIFEST" || true)"

# Move into place (cp -a keeps modes; the stage dir is excluded since it sits under ROOT).
(cd "$STAGE" && tar -cf - .) | tar -C "$ROOT" -xf -
echo "restore: $n files restored into $ROOT"
