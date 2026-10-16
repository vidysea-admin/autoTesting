#!/usr/bin/env bash
# One job: archive the AutoTester writable state root into a timestamped tar.gz plus a sha256 manifest.
# Usage: backup.sh [--root DIR] [--out DIR] [--gcs gs://bucket/prefix] [--include-secrets]
set -euo pipefail

ROOT="${AUTOTESTER_DATA_DIR:-/data}"
OUT="./backups"
GCS=""
SECRETS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --gcs) GCS="$2"; shift 2 ;;
    --include-secrets) SECRETS=1; shift ;;
    -h|--help) sed -n 2,3p "$0"; exit 0 ;;
    *) echo "backup: unknown argument $1" >&2; exit 2 ;;
  esac
done

[ -d "$ROOT" ] || { echo "backup: state root not found: $ROOT" >&2; exit 1; }
mkdir -p "$OUT"
ROOT="$(cd "$ROOT" && pwd)"
OUT="$(cd "$OUT" && pwd)"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="$OUT/autotester-backup-$TS.tar.gz"
MANIFEST="$ARCHIVE.manifest"

# Caches are always excluded. Secrets (.env, auth db, logged-in browser profiles) only on request.
EXCLUDES=(-name __pycache__ -o -name .cache -o -name Cache -o -name "Code Cache" -o -name GPUCache -o -name "*.tmp")
SECRET_PATHS=(./.env ./.auth ./profiles)
if [ "$SECRETS" -eq 1 ]; then
  echo "WARNING: --include-secrets set: the archive holds credentials, auth db and browser sessions. Store it encrypted and private." >&2
fi

LIST="$(mktemp)"; trap 'rm -f "$LIST"' EXIT
(
  cd "$ROOT"
  find . \( "${EXCLUDES[@]}" \) -prune -o -type f -print0 | sort -z | while IFS= read -r -d '' f; do
    skip=0
    if [ "$SECRETS" -eq 0 ]; then
      for s in "${SECRET_PATHS[@]}"; do
        case "$f" in "$s"|"$s"/*) skip=1 ;; esac
      done
    fi
    [ "$skip" -eq 1 ] || printf '%s\0' "${f#./}"
  done
) > "$LIST"

tar -C "$ROOT" --null -T "$LIST" -czf "$ARCHIVE"

{
  echo "# autotester backup manifest"
  echo "created_utc $TS"
  echo "secrets_included $SECRETS"
  echo "files $(tr -cd '\0' < "$LIST" | wc -c | tr -d ' ')"
  echo "archive_sha256 $(sha256sum < "$ARCHIVE" | cut -d' ' -f1)"
  echo "# sha256 path (sha256sum format)"
  (cd "$ROOT" && xargs -0 -r sha256sum < "$LIST")
} > "$MANIFEST"

echo "backup: $ARCHIVE"
echo "manifest: $MANIFEST"

if [ -n "$GCS" ]; then
  if command -v gsutil >/dev/null 2>&1; then
    gsutil cp "$ARCHIVE" "$MANIFEST" "${GCS%/}/"
  elif command -v gcloud >/dev/null 2>&1; then
    gcloud storage cp "$ARCHIVE" "$MANIFEST" "${GCS%/}/"
  else
    echo "backup: --gcs given but neither gsutil nor gcloud is installed; archive kept locally" >&2
    exit 3
  fi
fi
