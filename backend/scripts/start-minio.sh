#!/usr/bin/env bash
# MinIO on Mac — document data stored on Synology NAS mount.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
NAS_DATA_DIR="/Volumes/home/contractriskstorage/minio-data"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

export MINIO_ROOT_USER="${S3_ACCESS_KEY:?Set S3_ACCESS_KEY in backend/.env}"
export MINIO_ROOT_PASSWORD="${S3_SECRET_KEY:?Set S3_SECRET_KEY in backend/.env}"

mkdir -p "$NAS_DATA_DIR"

if ! command -v minio >/dev/null 2>&1; then
  echo "Install MinIO: brew install minio/stable/minio"
  exit 1
fi

echo "Starting MinIO (API http://127.0.0.1:9000, console http://127.0.0.1:9001)"
echo "Data directory: $NAS_DATA_DIR"
exec minio server "$NAS_DATA_DIR" --console-address ":9001"
