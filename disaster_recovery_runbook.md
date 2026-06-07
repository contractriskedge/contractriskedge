================================================================================
  CONTRACT RISK EDGE — DISASTER RECOVERY RUNBOOK
  Version: 1.0 — June 5, 2026
  Database: PostgreSQL 16.13 (Homebrew) — 26 MB
  Object Storage: MinIO — localhost:9000 — bucket: contractrisk-documents
================================================================================

TABLE OF CONTENTS
───────────────────────────────────────────────────────────────────────────────

  1.  Prerequisites
  2.  pg_dump Version Check
  3.  Full Database Backup
  4.  Schema-Only Backup
  5.  Roles/Users Backup
  6.  MinIO/S3 Backup
  7.  Full Database Restore
  8.  Restore Validation Procedure
  9.  Recovery Checklist
  10. Recovery Time Estimate
  11. Risks and Gaps

================================================================================
1. PREREQUISITES
================================================================================

  Required Tools:
    ── PostgreSQL 16 client tools (pg_dump, psql, pg_restore)
    ── AWS CLI v2 or MinIO Client (mc) for S3 backup
    ── Python 3.11+ with Alembic (for migration replay)
    ── 100 MB free disk space (current DB is 26 MB, allow 4x growth)

  Verify Tool Availability:
    /opt/homebrew/opt/postgresql@16/bin/pg_dump --version
    /opt/homebrew/opt/postgresql@16/bin/psql --version
    /opt/homebrew/opt/postgresql@16/bin/pg_restore --version
    aws --version || mc --version

  Connection Details (from backend/.env):
    DATABASE_URL=postgresql+psycopg2://dev_user:dev_password@localhost:5432/contract_risk_dev
    S3_ENDPOINT=http://127.0.0.1:9000
    S3_ACCESS_KEY=pgskannan
    S3_SECRET_KEY=Welcome2ibm$
    S3_BUCKET=contractrisk-documents

================================================================================
2. pg_dump VERSION CHECK (CRITICAL)
================================================================================

  ⚠ The default pg_dump on PATH is version 14.20.
  ⚠ The PostgreSQL server is version 16.13.
  ⚠ pg_dump 14 CANNOT dump from PG 16.

  ALWAYS use the full path to pg_dump 16:

    PG_DUMP="/opt/homebrew/opt/postgresql@16/bin/pg_dump"
    PSQL="/opt/homebrew/opt/postgresql@16/bin/psql"

  Verify correct version before every backup:

    $PG_DUMP --version
    # Must print: pg_dump (PostgreSQL) 16.13

================================================================================
3. FULL DATABASE BACKUP
================================================================================

  Command:

    PG_DUMP="/opt/homebrew/opt/postgresql@16/bin/pg_dump"
    BACKUP_DIR="/Volumes/ContractEdge/ContractRiskEdge"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    DB_URL="postgresql://dev_user:dev_password@localhost:5432/contract_risk_dev"

    $PG_DUMP \\
      --dbname="$DB_URL" \\
      --format=custom \\
      --compress=9 \\
      --file="$BACKUP_DIR/contractedge_full_$TIMESTAMP.dump" \\
      --verbose

    echo "Backup created: $BACKUP_DIR/contractedge_full_$TIMESTAMP.dump"

  Explanation:
    --format=custom   : Creates a compressed, parallel-restore-capable dump
    --compress=9      : Maximum gzip compression (smallest file)
    --file            : Output file path
    --verbose         : Prints progress (remove for cron)

  Expected Output:
    File size: ~50-100 KB (current DB is 26 MB uncompressed)
    Duration: < 5 seconds

  Alternative (SQL format, human-readable):

    $PG_DUMP \\
      --dbname="$DB_URL" \\
      --format=plain \\
      --file="$BACKUP_DIR/contractedge_full_$TIMESTAMP.sql" \\
      --verbose

  SQL format is larger but can be inspected with a text editor.

================================================================================
4. SCHEMA-ONLY BACKUP
================================================================================

  Use this for version control, schema diffs, and migration validation.

  Command:

    PG_DUMP="/opt/homebrew/opt/postgresql@16/bin/pg_dump"
    DB_URL="postgresql://dev_user:dev_password@localhost:5432/contract_risk_dev"

    $PG_DUMP \\
      --dbname="$DB_URL" \\
      --schema-only \\
      --file="contractedge_schema_$(date +%Y%m%d).sql"

  This produces a clean SQL file with all CREATE TABLE, CREATE INDEX,
  CREATE TYPE, and ALTER TABLE statements — no data rows.

================================================================================
5. ROLES/USERS BACKUP
================================================================================

  Command:

    PG_DUMP="/opt/homebrew/opt/postgresql@16/bin/pg_dump"
    DB_URL="postgresql://dev_user:dev_password@localhost:5432/contract_risk_dev"

    $PG_DUMP \\
      --dbname="$DB_URL" \\
      --globals-only \\
      --file="contractedge_globals_$(date +%Y%m%d).sql"

  This captures:
    ── Roles and users
    ── Permissions and grants
    ── Tablespace assignments

================================================================================
6. MinIO/S3 BACKUP
================================================================================

  6.1 Using AWS CLI v2
  ─────────────────────────────────────────────────────────────────────────────

    export AWS_ACCESS_KEY_ID="pgskannan"
    export AWS_SECRET_ACCESS_KEY="Welcome2ibm$"
    export AWS_ENDPOINT_URL="http://127.0.0.1:9000"
    export AWS_DEFAULT_REGION="us-east-1"

    # Sync all objects to local backup directory
    aws s3 sync s3://contractrisk-documents \\
      /Volumes/ContractEdge/ContractRiskEdge/minio_backup/ \\
      --endpoint-url http://127.0.0.1:9000

    # Verify
    echo "MinIO backup size:"
    du -sh /Volumes/ContractEdge/ContractRiskEdge/minio_backup/

  6.2 Using MinIO Client (mc)
  ─────────────────────────────────────────────────────────────────────────────

    # Install: brew install minio/stable/mc
    mc alias set localminio http://127.0.0.1:9000 pgskannan "Welcome2ibm$"
    mc mirror localminio/contractrisk-documents \\
      /Volumes/ContractEdge/ContractRiskEdge/minio_backup/

================================================================================
7. FULL DATABASE RESTORE
================================================================================

  7.1 Prerequisites
  ─────────────────────────────────────────────────────────────────────────────

    ── Target PostgreSQL 16 server running
    ── Empty target database (created below)
    ── pg_dump 16 tools available
    ── Alembic migrations available at backend/alembic/

  7.2 Create Clean Database
  ─────────────────────────────────────────────────────────────────────────────

    PSQL="/opt/homebrew/opt/postgresql@16/bin/psql"
    DB_URL="postgresql://dev_user:dev_password@localhost:5432"

    # Drop if exists (⚠ IRREVERSIBLE)
    $PSQL "$DB_URL/postgres" -c "DROP DATABASE IF EXISTS contract_risk_dev_restore;"

    # Create clean database
    $PSQL "$DB_URL/postgres" -c "CREATE DATABASE contract_risk_dev_restore;"

  7.3 Restore from Custom Format Dump
  ─────────────────────────────────────────────────────────────────────────────

    PG_RESTORE="/opt/homebrew/opt/postgresql@16/bin/pg_restore"
    RESTORE_DB_URL="postgresql://dev_user:dev_password@localhost:5432/contract_risk_dev_restore"

    $PG_RESTORE \\
      --dbname="$RESTORE_DB_URL" \\
      --format=custom \\
      --verbose \\
      --exit-on-error \\
      "contractedge_full_20260605.dump"

  7.4 Restore from SQL Format Dump
  ─────────────────────────────────────────────────────────────────────────────

    $PSQL "$RESTORE_DB_URL" -f "contractedge_full_20260605.sql"

  7.5 Run Alembic Migrations
  ─────────────────────────────────────────────────────────────────────────────

    cd /Volumes/ContractEdge/ContractRiskEdge/backend
    source .venv/bin/activate

    # Point to the restored database
    export DATABASE_URL="postgresql+psycopg2://dev_user:dev_password@localhost:5432/contract_risk_dev_restore"

    # Run all pending migrations
    alembic upgrade head

    # Verify migration state
    alembic current
    # Must print: l0m1n2o3p4q5 (head)

  7.6 Verify Alembic Version
  ─────────────────────────────────────────────────────────────────────────────

    $PSQL "$RESTORE_DB_URL" -c "SELECT version_num FROM alembic_version;"
    # Must match: l0m1n2o3p4q5

================================================================================
8. RESTORE VALIDATION PROCEDURE
================================================================================

  After restoring, run these checks to confirm data integrity:

  8.1 Table Count Verification
  ─────────────────────────────────────────────────────────────────────────────

    $PSQL "$RESTORE_DB_URL" -c "
      SELECT schemaname, tablename, tableowner
      FROM pg_tables
      WHERE schemaname = 'public'
      ORDER BY tablename;
    "
    # Expected: ~40+ tables matching production schema

  8.2 Row Count Verification
  ─────────────────────────────────────────────────────────────────────────────

    $PSQL "$RESTORE_DB_URL" -c "
      SELECT
        (SELECT COUNT(*) FROM contract_reviews) as reviews,
        (SELECT COUNT(*) FROM upload_sessions) as uploads,
        (SELECT COUNT(*) FROM review_findings) as findings,
        (SELECT COUNT(*) FROM ai_execution_runs) as ai_runs,
        (SELECT COUNT(*) FROM review_assignments) as assignments,
        (SELECT COUNT(*) FROM review_approvals) as approvals,
        (SELECT COUNT(*) FROM review_escalations) as escalations,
        (SELECT COUNT(*) FROM notifications) as notifications,
        (SELECT COUNT(*) FROM governance_audit_events) as audit_events;
    "

  8.3 Enum Values Verification
  ─────────────────────────────────────────────────────────────────────────────

    $PSQL "$RESTORE_DB_URL" -c "SELECT enum_range(NULL::review_status);"
    # Must include: analyzing, legal_review, procurement_review, security_review

  8.4 Alembic Version Verification
  ─────────────────────────────────────────────────────────────────────────────

    $PSQL "$RESTORE_DB_URL" -c "SELECT version_num FROM alembic_version;"
    # Must match: l0m1n2o3p4q5

  8.5 Unique Constraint Verification
  ─────────────────────────────────────────────────────────────────────────────

    $PSQL "$RESTORE_DB_URL" -c "
      SELECT conname FROM pg_constraint
      WHERE conname = 'uq_review_assignee';
    "
    # Must return 1 row

  8.6 Application Smoke Test
  ─────────────────────────────────────────────────────────────────────────────

    cd /Volumes/ContractEdge/ContractRiskEdge/backend
    source .venv/bin/activate
    export DATABASE_URL="postgresql+psycopg2://dev_user:dev_password@localhost:5432/contract_risk_dev_restore"

    # Run the state transition tests
    python -m pytest tests/test_state_transitions.py -q --no-header

    # Run the persistence validation tests
    python -m pytest tests/test_persistence_validation.py -q --no-header

================================================================================
9. RECOVERY CHECKLIST
================================================================================

  Use this checklist during any restore operation.

  [ ] 1. Verify pg_dump version (must be 16.x)
  [ ] 2. Verify backup file exists and is non-empty
  [ ] 3. Verify backup file checksum (if available)
  [ ] 4. Confirm target database name (don't overwrite production)
  [ ] 5. Create clean target database
  [ ] 6. Run pg_restore / psql restore
  [ ] 7. Verify no errors in restore output
  [ ] 8. Run Alembic migrations (alembic upgrade head)
  [ ] 9. Verify alembic_version matches expected head
  [ ] 10. Verify enum values (review_status must have 20 values)
  [ ] 11. Verify unique constraints (uq_review_assignee)
  [ ] 12. Verify row counts match pre-backup snapshot
  [ ] 13. Run application smoke tests
  [ ] 14. Restore MinIO/S3 data (if applicable)
  [ ] 15. Update DATABASE_URL in .env to point to restored database
  [ ] 16. Restart backend server
  [ ] 17. Verify API responds (curl /api/v1/reviews?page_size=1)
  [ ] 18. Verify executive dashboard loads (GET /api/v1/analytics/executive/dashboard)

================================================================================
10. RECOVERY TIME ESTIMATE
================================================================================

  Step                                    | Estimated Time
  ────────────────────────────────────────┼────────────────
  Create clean database                   | < 1 second
  Restore from custom-format dump         | < 5 seconds
  Run Alembic migrations                  | < 30 seconds
  Verify data integrity                   | < 10 seconds
  Run smoke tests                         | < 30 seconds
  Restore MinIO data                      | < 60 seconds (per GB)
  Update config and restart server        | < 30 seconds
  ────────────────────────────────────────┼────────────────
  TOTAL (database only)                   | < 2 minutes
  TOTAL (full including MinIO)            | < 5 minutes

  RTO Target: 15 minutes
  Current estimated RTO: < 5 minutes ✅

================================================================================
11. RISKS AND GAPS
================================================================================

  🔴 HIGH: No Automated Backups
  ─────────────────────────────────────────────────────────────────────────────
  All backups are manual. If the developer forgets to run pg_dump before a
  destructive operation, data loss is possible.

  Recommendation: Add a cron job:
    0 2 * * * /Volumes/ContractEdge/ContractRiskEdge/scripts/backup.sh

  🟡 MEDIUM: MinIO Backup Not Automated
  ─────────────────────────────────────────────────────────────────────────────
  Uploaded contract documents in MinIO are not included in the backup script.
  The aws s3 sync or mc mirror command must be run separately.

  Recommendation: Add MinIO backup to the backup script.

  🟡 MEDIUM: No Backup Rotation
  ─────────────────────────────────────────────────────────────────────────────
  Backups accumulate without cleanup. Disk could fill over time.

  Recommendation: Keep 7 daily backups, 4 weekly, 12 monthly.

  🟡 MEDIUM: No Off-Site Storage
  ─────────────────────────────────────────────────────────────────────────────
  Backups exist only on the local NVMe drive. A drive failure destroys
  both the database and all backups.

  Recommendation: Sync backups to a separate volume or cloud storage.

  🟢 LOW: No Backup Encryption
  ─────────────────────────────────────────────────────────────────────────────
  Backups contain sensitive contract data in plaintext. For production,
  use pg_dump's --encrypt option or pipe through gpg.

================================================================================
APPENDIX A: AUTOMATED BACKUP SCRIPT
================================================================================

  Save as: /Volumes/ContractEdge/ContractRiskEdge/scripts/backup.sh

  ```bash
  #!/bin/bash
  # ContractEdge Automated Backup Script
  # Run daily via cron: 0 2 * * * /path/to/scripts/backup.sh

  set -euo pipefail

  PG_DUMP="/opt/homebrew/opt/postgresql@16/bin/pg_dump"
  PSQL="/opt/homebrew/opt/postgresql@16/bin/psql"
  BACKUP_DIR="/Volumes/ContractEdge/ContractRiskEdge"
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  DB_URL="postgresql://dev_user:dev_password@localhost:5432/contract_risk_dev"
  RETENTION_DAYS=7

  echo "[$(date)] Starting backup..."

  # 1. Full backup (custom format)
  $PG_DUMP \
    --dbname="$DB_URL" \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_DIR/contractedge_${TIMESTAMP}.dump" \
    --verbose

  # 2. Schema-only backup (for git)
  $PG_DUMP \
    --dbname="$DB_URL" \
    --schema-only \
    --file="$BACKUP_DIR/contractedge_schema_${TIMESTAMP}.sql"

  # 3. Verify backup is non-empty
  if [ ! -s "$BACKUP_DIR/contractedge_${TIMESTAMP}.dump" ]; then
    echo "ERROR: Backup file is empty!"
    exit 1
  fi

  # 4. Remove backups older than RETENTION_DAYS
  find "$BACKUP_DIR" -name "contractedge_*.dump" -mtime +$RETENTION_DAYS -delete
  find "$BACKUP_DIR" -name "contractedge_schema_*.sql" -mtime +$RETENTION_DAYS -delete

  # 5. Log backup info
  echo "[$(date)] Backup complete: contractedge_${TIMESTAMP}.dump"
  ls -lh "$BACKUP_DIR/contractedge_${TIMESTAMP}.dump"

  # 6. MinIO backup (optional, uncomment if mc is configured)
  # mc mirror localminio/contractrisk-documents "$BACKUP_DIR/minio_${TIMESTAMP}/"
  ```

================================================================================
APPENDIX B: ONE-LINER BACKUP
================================================================================

  Quick full backup (copy-paste):

    /opt/homebrew/opt/postgresql@16/bin/pg_dump \
      --dbname="postgresql://dev_user:dev_password@localhost:5432/contract_risk_dev" \
      --format=custom --compress=9 \
      --file="/Volumes/ContractEdge/ContractRiskEdge/contractedge_$(date +%Y%m%d).dump"

================================================================================
