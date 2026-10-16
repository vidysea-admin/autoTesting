#!/usr/bin/env bash
# One job: archive the AutoTester writable state root into a timestamped tar.gz plus a sha256 manifest.
# Usage: backup.sh [--root DIR] [--out DIR] [--gcs gs://bucket/prefix] [--include-secrets]
set -euo pipefail
export LC_ALL=C

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

# Caches and restore staging are always skipped, at any depth.
PRUNE=(-name __pycache__ -o -name .cache -o -name Cache -o -name "Code Cache" -o -name GPUCache
       -o -name "*.tmp" -o -name ".restore-stage.*")
# Secrets (credentials, auth db, logged-in browser stores) are skipped at any depth unless requested.
SECRET_PRUNE=(-name ".env*" -o -name .auth -o -name profiles -o -name "*.pem" -o -name "*.key"
       -o -name "id_rsa*" -o -name "credentials*.json" -o -name "token*.json"
       -o -name "*service-account*.json" -o -name "Cookies*" -o -name "Login Data*"
       -o -name "Web Data" -o -name "Local Storage" -o -name "Session Storage" -o -name IndexedDB)
if [ "$SECRETS" -eq 1 ]; then
  echo "WARNING: --include-secrets set: the archive holds credentials, auth db and browser sessions. Store it encrypted and private." >&2
  EXPR=("${PRUNE[@]}")
else
  EXPR=("${PRUNE[@]}" -o "${SECRET_PRUNE[@]}")
fi

LIST="$(mktemp)"; ENTRIES="$(mktemp)"; trap 'rm -f "$LIST" "$ENTRIES"' EXIT
(cd "$ROOT" && find . \( "${EXPR[@]}" \) -prune -o -type f -print0 | sed -z 's|^\./||' | sort -z) > "$LIST"
(cd "$ROOT" && xargs -0 -r sha256sum < "$LIST") > "$ENTRIES"

tar -C "$ROOT" --null -T "$LIST" -czf "$ARCHIVE"

{
  echo "# autotester backup manifest"
  echo "created_utc $TS"
  echo "secrets_included $SECRETS"
  echo "files $(wc -l < "$ENTRIES" | tr -d ' ')"
  echo "archive_sha256 $(sha256sum < "$ARCHIVE" | cut -d' ' -f1)"
  echo "# entries (sha256sum format, names escaped by sha256sum)"
  cat "$ENTRIES"
} > "$MANIFEST"
sha256sum < "$MANIFEST" | cut -d' ' -f1 > "$MANIFEST.sha256"

echo "backup: $ARCHIVE"
echo "manifest: $MANIFEST"

if [ -n "$GCS" ]; then
  if command -v gsutil >/dev/null 2>&1; then
    gsutil cp "$ARCHIVE" "$MANIFEST" "$MANIFEST.sha256" "${GCS%/}/"
  elif command -v gcloud >/dev/null 2>&1; then
    gcloud storage cp "$ARCHIVE" "$MANIFEST" "$MANIFEST.sha256" "${GCS%/}/"
  else
    echo "backup: --gcs given but neither gsutil nor gcloud is installed; archive kept locally" >&2
    exit 3
  fi
fi
