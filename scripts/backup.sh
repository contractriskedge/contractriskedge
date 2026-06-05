#!/bin/bash
# =============================================================================
# ContractEdge Automated Backup Script — Enhanced v2.0
# =============================================================================
# Features:
#   - PostgreSQL full backup (custom format, compressed)
#   - PostgreSQL schema-only backup
#   - MinIO/S3 object storage backup (mc mirror + boto3 fallback)
#   - Retention: 7 daily + 4 weekly backups
#   - Structured JSON logging
#   - Failure alerting (log-based, non-zero exit)
#   - Backup integrity verification
#   - Dry-run and validate-only modes
#
# Usage:
#   ./scripts/backup.sh                    # Run once (manual or cron)
#   ./scripts/backup.sh --dry-run          # Preview without executing
#   ./scripts/backup.sh --validate-only    # Check retention + integrity only
#
# Cron (install via: crontab scripts/crontab):
#   0 2 * * * /Volumes/ContractEdge/ContractRiskEdge/scripts/backup.sh
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PG_DUMP="/opt/homebrew/opt/postgresql@16/bin/pg_dump"
PG_RESTORE="/opt/homebrew/opt/postgresql@16/bin/pg_restore"
PSQL="/opt/homebrew/opt/postgresql@16/bin/psql"

BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_STAMP=$(date +%Y%m%d)
WEEK_NUM=$(date +%V)

DB_URL="postgresql://dev_user:dev_password@localhost:5432/contract_risk_dev"
DB_NAME="contract_risk_dev"

S3_ENDPOINT="http://127.0.0.1:9000"
S3_ACCESS_KEY="pgskannan"
S3_SECRET_KEY="Welcome2ibm$"
S3_BUCKET="contractrisk-documents"

# Retention: keep 7 daily + 4 weekly
DAILY_RETENTION=7
WEEKLY_RETENTION=4

LOG_DIR="${BACKUP_DIR}/logs"
LOG_FILE="${LOG_DIR}/backup_${TIMESTAMP}.log"
JSON_LOG="${LOG_DIR}/backup_${TIMESTAMP}.json"

# ── Helpers ──────────────────────────────────────────────────────────────────

mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly" "$BACKUP_DIR/logs" "$BACKUP_DIR/minio"

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

json_log() {
    local status="$1"
    local details="$2"
    cat > "$JSON_LOG" <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "script": "backup.sh",
  "version": "2.0",
  "status": "${status}",
  "database": "${DB_NAME}",
  "backup_file": "${backup_file:-null}",
  "backup_size_bytes": ${backup_size:-0},
  "schema_file": "${schema_file:-null}",
  "minio_objects": ${minio_count:-0},
  "minio_bytes": ${minio_bytes:-0},
  "duration_seconds": ${duration:-0},
  "daily_retention": ${DAILY_RETENTION},
  "weekly_retention": ${WEEKLY_RETENTION},
  "details": ${details}
}
EOF
}

cleanup_old_backups() {
    local dir="$1"
    local pattern="$2"
    local keep="$3"
    local label="$4"

    local count=0
    count=$(find "$dir" -name "$pattern" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -gt "$keep" ]; then
        local to_delete=$((count - keep))
        log "INFO" "Retention [${label}]: ${count} backups found, removing ${to_delete} oldest (keeping ${keep})"
        find "$dir" -name "$pattern" -type f -print0 2>/dev/null | sort -z | head -z -"$to_delete" | while IFS= read -r -d '' f; do
            rm -f "$f"
            log "INFO" "  Removed old backup: $(basename "$f")"
        done
    else
        log "INFO" "Retention [${label}]: ${count} backups (within limit of ${keep})"
    fi
}

# ── Parse Arguments ──────────────────────────────────────────────────────────

DRY_RUN=false
VALIDATE_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --validate-only) VALIDATE_ONLY=true ;;
    esac
done

# ── Validate Only Mode ───────────────────────────────────────────────────────

if [ "$VALIDATE_ONLY" = true ]; then
    echo "=== ContractEdge Backup Validation Report ==="
    echo "Timestamp: $(date -u)"
    echo ""

    echo "--- Backup Directory ---"
    ls -lh "$BACKUP_DIR/daily/" 2>/dev/null | head -20
    echo ""

    echo "--- Retention Check ---"
    daily_count=$(find "$BACKUP_DIR/daily" -name "contractedge_*.dump" -type f 2>/dev/null | wc -l | tr -d ' ')
    weekly_count=$(find "$BACKUP_DIR/weekly" -name "contractedge_*.dump" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "  Daily backups:  ${daily_count} (limit: ${DAILY_RETENTION})"
    echo "  Weekly backups: ${weekly_count} (limit: ${WEEKLY_RETENTION})"
    echo ""

    echo "--- Integrity Check ---"
    found_any=false
    for f in "$BACKUP_DIR/daily/"contractedge_*.dump "$BACKUP_DIR/weekly/"contractedge_*.dump; do
        if [ -f "$f" ]; then
            found_any=true
            size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)
            echo "  $(basename "$f"): ${size} bytes"
            if [ "$size" -eq 0 ]; then
                echo "    WARNING: Empty backup file!"
            fi
        fi
    done
    if [ "$found_any" = false ]; then
        echo "  No backup files found."
    fi
    echo ""

    echo "--- MinIO Backups ---"
    minio_count=$(find "$BACKUP_DIR/minio" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
    echo "  MinIO backups: ${minio_count}"
    echo ""

    echo "--- Logs ---"
    log_count=$(find "$LOG_DIR" -name "backup_*.log" -type f 2>/dev/null | wc -l | tr -d ' ')
    echo "  Log files: ${log_count}"
    echo ""

    # Check latest backup freshness
    latest=$(find "$BACKUP_DIR/daily" -name "contractedge_*.dump" -type f -print 2>/dev/null | sort -r | head -1)
    if [ -n "$latest" ]; then
        file_time=$(stat -f%m "$latest" 2>/dev/null || stat -c%Y "$latest" 2>/dev/null || echo 0)
        now=$(date +%s)
        age=$(( (now - file_time) / 3600 ))
        echo "--- Freshness ---"
        echo "  Latest backup: $(basename "$latest")"
        echo "  Age: ${age} hours"
        if [ "$age" -gt 30 ]; then
            echo "  WARNING: Backup is over 30 hours old!"
        else
            echo "  Status: OK"
        fi
    fi

    exit 0
fi

# ── Dry Run Mode ─────────────────────────────────────────────────────────────

if [ "$DRY_RUN" = true ]; then
    echo "=== DRY RUN ==="
    echo "Would execute:"
    echo "  1. pg_dump --format=custom --compress=9"
    echo "     → ${BACKUP_DIR}/daily/contractedge_${TIMESTAMP}.dump"
    echo "  2. pg_dump --schema-only"
    echo "     → ${BACKUP_DIR}/daily/contractedge_schema_${TIMESTAMP}.sql"
    echo "  3. Weekly copy (if Friday)"
    echo "     → ${BACKUP_DIR}/weekly/contractedge_week${WEEK_NUM}_${DATE_STAMP}.dump"
    echo "  4. MinIO backup"
    echo "     → ${BACKUP_DIR}/minio/minio_${TIMESTAMP}/"
    echo "  5. Retention cleanup: keep ${DAILY_RETENTION} daily, ${WEEKLY_RETENTION} weekly"
    echo "  6. Log → ${LOG_FILE}"
    exit 0
fi

# ── Main Backup Routine ──────────────────────────────────────────────────────

OVERALL_START=$(date +%s)

log "INFO" "=== ContractEdge Backup v2.0 ==="
log "INFO" "Backup directory: ${BACKUP_DIR}"
log "INFO" "Database: ${DB_NAME}"

# ── 1. PostgreSQL Full Backup ────────────────────────────────────────────────

log "INFO" "Step 1/5: PostgreSQL full backup (custom format, compressed)..."
backup_file="${BACKUP_DIR}/daily/contractedge_${TIMESTAMP}.dump"
schema_file="${BACKUP_DIR}/daily/contractedge_schema_${TIMESTAMP}.sql"

if ! $PG_DUMP \
    --dbname="$DB_URL" \
    --format=custom \
    --compress=9 \
    --file="$backup_file" \
    --verbose 2>> "$LOG_FILE"; then
    log "ERROR" "PostgreSQL full backup FAILED"
    json_log "failed" "\"pg_dump full backup failed\""
    exit 1
fi

backup_size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo 0)
log "INFO" "  Backup file: $(basename "$backup_file") (${backup_size} bytes)"

# Verify backup is non-empty
if [ ! -s "$backup_file" ]; then
    log "ERROR" "Backup file is empty (0 bytes)"
    json_log "failed" "\"Backup file is empty\""
    exit 1
fi

# ── 2. Schema-Only Backup ────────────────────────────────────────────────────

log "INFO" "Step 2/5: Schema-only backup..."
if ! $PG_DUMP \
    --dbname="$DB_URL" \
    --schema-only \
    --file="$schema_file" 2>> "$LOG_FILE"; then
    log "WARNING" "Schema-only backup had issues (non-fatal)"
fi
log "INFO" "  Schema file: $(basename "$schema_file")"

# ── 3. Weekly Promotion (Fridays) ────────────────────────────────────────────

DOW=$(date +%u)  # 1=Mon, 5=Fri, 7=Sun
if [ "$DOW" -eq 5 ]; then
    log "INFO" "Step 3/5: Promoting to weekly backup (Friday)..."
    weekly_file="${BACKUP_DIR}/weekly/contractedge_week${WEEK_NUM}_${DATE_STAMP}.dump"
    cp "$backup_file" "$weekly_file"
    log "INFO" "  Weekly backup: $(basename "$weekly_file")"
else
    log "INFO" "Step 3/5: Skipped (not Friday — daily backup only)"
fi

# ── 4. MinIO Object Storage Backup ───────────────────────────────────────────

log "INFO" "Step 4/5: MinIO object storage backup..."
minio_backup_dir="${BACKUP_DIR}/minio/minio_${TIMESTAMP}"
mkdir -p "$minio_backup_dir"

minio_count=0
minio_bytes=0

if command -v mc &>/dev/null; then
    log "INFO" "  Using mc mirror for MinIO backup..."
    mc alias set contractedge-minio "$S3_ENDPOINT" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" 2>/dev/null
    if mc mirror contractedge-minio/"$S3_BUCKET" "$minio_backup_dir" >> "$LOG_FILE" 2>&1; then
        minio_count=$(find "$minio_backup_dir" -type f 2>/dev/null | wc -l | tr -d ' ')
        minio_bytes=$(find "$minio_backup_dir" -type f -exec stat -f%z {} + 2>/dev/null | awk '{s+=$1} END {print s}' || echo 0)
        log "INFO" "  MinIO backup via mc: ${minio_count} objects, ${minio_bytes} bytes"
    else
        log "WARNING" "  mc mirror failed, falling back to boto3..."
    fi
fi

if [ "$minio_count" -eq 0 ]; then
    log "INFO" "  Using boto3 fallback for MinIO backup..."
    # Use python to download all objects
    cd "$PROJECT_DIR/backend"
    boto3_output=$(.venv/bin/python -c "
import boto3, os
from botocore.config import Config

c = boto3.client('s3',
    endpoint_url='${S3_ENDPOINT}',
    aws_access_key_id='${S3_ACCESS_KEY}',
    aws_secret_access_key='${S3_SECRET_KEY}',
    config=Config(connect_timeout=5, read_timeout=10))

objs = c.list_objects_v2(Bucket='${S3_BUCKET}')
contents = objs.get('Contents', [])
count = 0
total = 0
for o in contents:
    key = o['Key']
    local = os.path.join('${minio_backup_dir}', key.replace('/', '_'))
    c.download_file(Bucket='${S3_BUCKET}', Key=key, Filename=local)
    count += 1
    total += o['Size']

print(f'{count}|{total}')
" 2>> "$LOG_FILE")
    minio_count=$(echo "$boto3_output" | cut -d'|' -f1)
    minio_bytes=$(echo "$boto3_output" | cut -d'|' -f2)
    log "INFO" "  MinIO backup via boto3: ${minio_count} objects, ${minio_bytes} bytes"
fi

# ── 5. Retention Cleanup ─────────────────────────────────────────────────────

log "INFO" "Step 5/5: Retention cleanup..."
cleanup_old_backups "$BACKUP_DIR/daily"  "contractedge_*.dump"       ${DAILY_RETENTION}  "daily"
cleanup_old_backups "$BACKUP_DIR/daily"  "contractedge_schema_*.sql" ${DAILY_RETENTION}  "daily_schema"
cleanup_old_backups "$BACKUP_DIR/weekly" "contractedge_*.dump"       ${WEEKLY_RETENTION} "weekly"

# Clean up old MinIO backups (keep same as daily)
minio_count_all=$(find "$BACKUP_DIR/minio" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
if [ "$minio_count_all" -gt "$DAILY_RETENTION" ]; then
    to_delete=$((minio_count_all - DAILY_RETENTION))
    log "INFO" "Retention [minio]: ${minio_count_all} backups, removing ${to_delete} oldest"
    find "$BACKUP_DIR/minio" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null | sort -z | head -z -"$to_delete" | while IFS= read -r -d '' d; do
        rm -rf "$d"
    done
fi

# Clean up old logs (keep 30 days)
find "$LOG_DIR" -name "backup_*.log" -type f -mtime +30 -delete 2>/dev/null
find "$LOG_DIR" -name "backup_*.json" -type f -mtime +30 -delete 2>/dev/null

# ── Summary ───────────────────────────────────────────────────────────────────

OVERALL_END=$(date +%s)
duration=$((OVERALL_END - OVERALL_START))

log "INFO" "=== Backup Complete ==="
log "INFO" "  Duration: ${duration}s"
log "INFO" "  DB backup: $(basename "$backup_file") (${backup_size} bytes)"
log "INFO" "  Schema:    $(basename "$schema_file")"
log "INFO" "  MinIO:     ${minio_count} objects (${minio_bytes} bytes)"
log "INFO" "  Log:       $(basename "$LOG_FILE")"

# Write JSON log
cat > "$JSON_LOG" <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "script": "backup.sh",
  "version": "2.0",
  "status": "success",
  "database": "${DB_NAME}",
  "backup_file": "$(basename "$backup_file")",
  "backup_size_bytes": ${backup_size},
  "schema_file": "$(basename "$schema_file")",
  "minio_objects": ${minio_count},
  "minio_bytes": ${minio_bytes},
  "duration_seconds": ${duration},
  "daily_retention": ${DAILY_RETENTION},
  "weekly_retention": ${WEEKLY_RETENTION},
  "details": "Backup completed successfully"
}
EOF

log "INFO" "JSON log: $(basename "$JSON_LOG")"

# Success exit
exit 0
