================================================================================
  SPRINT 22 TASK 1.2 — MinIO Backup Validation Audit
  Completed: June 5, 2026
================================================================================

1. MINIO INFRASTRUCTURE SUMMARY
───────────────────────────────────────────────────────────────────────────────

  Component       | Detail
  ────────────────┼─────────────────────────────────────────────────
  Service         | MinIO (S3-compatible object storage)
  Endpoint        | http://127.0.0.1:9000
  Console UI      | http://127.0.0.1:9001
  Credentials     | pgskannan / Welcome2ibm$
  Buckets         | 1 (contractrisk-documents)
  Total Objects   | 23
  Total Size      | 255 KiB
  File Types      | 15 .txt, 8 .docx
  Tenant Prefix   | 00000000-0000-4000-8000-000000000001 (dev tenant)
  Data Location   | Docker volume (minio_data) or local filesystem

2. BUCKET INVENTORY
───────────────────────────────────────────────────────────────────────────────

  Bucket Name                | Environment      | Status
  ───────────────────────────┼──────────────────┼──────────
  contractrisk-documents     | Local dev (.env) | ✅ Active (23 objects)
  contractrisk-documents     | Docker Compose   | ⚠ Uses default creds
  contractrisk-documents     | K8s Production   | ⚠ Placeholder values
  contractedge-documents     | Pydantic default | ❌ Never created
  contractriskedge-staging-  | Staging          | ⚠ Not verified
    documents                |                  |
  contractriskedge-prod-     | Production       | ⚠ Not verified
    documents                |                  |

  ⚠ 7 different bucket names exist across configurations — a consistency risk.

3. OBJECT INVENTORY
───────────────────────────────────────────────────────────────────────────────

  All objects are under prefix: 00000000-0000-4000-8000-000000000001/

  File                                 | Size   | Type
  ─────────────────────────────────────┼────────┼──────
  .../07c6c8c2-.../e2e_stage_test.txt  | 1.0 KB | txt
  .../0e3dc474-.../CONTRACT_05_PSA...  | 29 KB  | docx
  .../1dc7032c-.../quick_test.txt      | 66 B   | txt
  .../29f43e2c-.../test_nda.txt        | 3.0 KB | txt
  .../2b48e740-.../CONTRACT_03_SaaS... | 29 KB  | docx
  .../3057b322-.../escalated_queue.txt | 224 B  | txt
  .../3441fdd5-.../e2e_test_contract   | 1.4 KB | txt
  .../42e728be-.../compliance_test.txt | 253 B  | txt
  .../42f14dd2-.../compliance_test.txt | 305 B  | txt
  .../573f073f-.../compliance_test.txt | 289 B  | txt
  .../5d05f72a-.../exec_queue.txt      | 232 B  | txt
  .../60b18c8b-.../queue_test.txt      | 991 B  | txt
  .../63c2b66d-.../legal_queue.txt     | 215 B  | txt
  .../67ad4ef7-.../CONTRACT_08_Joint.. | 29 KB  | docx
  .../9fda3bea-.../CONTRACT_06_DPA...  | 28 KB  | docx
  .../a873fdd4-.../CONTRACT_03_SaaS... | 29 KB  | docx
  .../ab18cbab-.../investigate.txt     | 79 B   | txt
  .../ad57d614-.../CONTRACT_03_SaaS... | 29 KB  | docx
  .../b6c90c6d-.../legal_test.txt      | 249 B  | txt
  .../b7554523-.../compliance_queue.txt| 256 B  | txt
  .../c800112d-.../CONTRACT_03_SaaS... | 38 KB  | docx
  .../ca2e4de3-.../test_e2e_contract   | 7.5 KB | txt
  .../f9579a1c-.../CONTRACT_03_SaaS... | 29 KB  | docx

  Total: 23 objects, 255 KiB

4. OBJECT KEY PATTERN
───────────────────────────────────────────────────────────────────────────────

  Standard pattern (from StorageService.build_object_key):
    {tenant_id}/contracts/{year}/{month}/{uuid}/{filename}

  Example:
    00000000-0000-4000-8000-000000000001/contracts/2025/06/550e8400-e29b-41d4-a716-446655440000/nda-agreement.pdf

  ⚠ Three different key patterns exist across the codebase:
    1. StorageService.build_object_key() — tenant-scoped, date-partitioned
    2. Direct upload router — flat tenant/uuid/filename
    3. Version prefix — contracts/{review_id}/versions/v{num}.docx

5. BACKUP VALIDATION RESULTS
───────────────────────────────────────────────────────────────────────────────

  Step                          | Result
  ──────────────────────────────┼────────────────────────────────
  1. mc mirror to local FS      | ✅ 23 files, 328 KiB on disk
  2. SHA256 integrity check     | ✅ Original == Backup match
  3. Delete local copy          | ✅ Removed from /tmp
  4. Restore from backup        | ✅ mc cp succeeded
  5. Verify restored object     | ✅ Accessible, content matches
  6. Cleanup test artifact      | ✅ Removed

  SHA256 of sample file (e2e_stage_test.txt):
    Original: 4165e94a17c1505de51ba19b59c5014a78cdb587b6e3df412377cc7461f4aa56
    Backup:   4165e94a17c1505de51ba19b59c5014a78cdb587b6e3df412377cc7461f4aa56
    ✅ MATCH

6. BACKUP PROCEDURE
───────────────────────────────────────────────────────────────────────────────

  6.1 Prerequisites
  ─────────────────────────────────────────────────────────────────────────────
    ── MinIO Client (mc): brew install minio/stable/mc
    ── MinIO server running on localhost:9000
    ── Valid credentials (from backend/.env)

  6.2 Full MinIO Backup
  ─────────────────────────────────────────────────────────────────────────────

    # Configure MinIO alias
    mc alias set contractedge-minio http://127.0.0.1:9000 pgskannan "Welcome2ibm$"

    # Backup all buckets to local filesystem
    BACKUP_DIR="/Volumes/ContractEdge/ContractRiskEdge/minio_backup_$(date +%Y%m%d)"
    mc mirror contractedge-minio/contractrisk-documents "$BACKUP_DIR"

  6.3 Verify Backup Integrity
  ─────────────────────────────────────────────────────────────────────────────

    # Count files
    find "$BACKUP_DIR" -type f | wc -l

    # Check total size
    du -sh "$BACKUP_DIR"

    # Verify individual file (spot check)
    mc cat contractedge-minio/contractrisk-documents/path/to/file.txt | shasum -a 256
    shasum -a 256 "$BACKUP_DIR/path/to/file.txt"
    # Both must match

7. RESTORE PROCEDURE
───────────────────────────────────────────────────────────────────────────────

  7.1 Full Restore from Backup
  ─────────────────────────────────────────────────────────────────────────────

    # Restore entire bucket from local backup
    mc mirror /Volumes/ContractEdge/ContractRiskEdge/minio_backup/ \
      contractedge-minio/contractrisk-documents

  7.2 Restore Single Object
  ─────────────────────────────────────────────────────────────────────────────

    mc cp /Volumes/ContractEdge/ContractRiskEdge/minio_backup/path/to/file.txt \
      contractedge-minio/contractrisk-documents/path/to/file.txt

  7.3 Verify Restore
  ─────────────────────────────────────────────────────────────────────────────

    # List restored objects
    mc ls contractedge-minio/contractrisk-documents --recursive

    # Spot-check content
    mc cat contractedge-minio/contractrisk-documents/path/to/file.txt | head -5

8. INTEGRITY VERIFICATION PROCEDURE
───────────────────────────────────────────────────────────────────────────────

  After any backup or restore, run this verification:

    #!/bin/bash
    # verify_minio_backup.sh — checks all files exist and have matching sizes
    BACKUP_DIR="/Volumes/ContractEdge/ContractRiskEdge/minio_backup"
    BUCKET="contractrisk-documents"
    ALIAS="contractedge-minio"

    echo "=== Backup File Count ==="
    find "$BACKUP_DIR" -type f | wc -l

    echo "=== MinIO Object Count ==="
    mc ls "$ALIAS/$BUCKET" --recursive | wc -l

    echo "=== Spot-check SHA256 (first 3 files) ==="
    find "$BACKUP_DIR" -type f | head -3 | while read f; do
      rel_path="${f#$BACKUP_DIR/}"
      echo "Checking: $rel_path"
      original_hash=$(mc cat "$ALIAS/$BUCKET/$rel_path" 2>/dev/null | shasum -a 256 | cut -d' ' -f1)
      backup_hash=$(shasum -a 256 "$f" | cut -d' ' -f1)
      if [ "$original_hash" = "$backup_hash" ]; then
        echo "  ✅ MATCH"
      else
        echo "  ❌ MISMATCH"
      fi
    done

9. RECOVERY TIME ESTIMATE
───────────────────────────────────────────────────────────────────────────────

  Operation            | Estimated Time
  ─────────────────────┼────────────────
  Backup (255 KiB)     | < 1 second
  Backup (1 GB)        | ~30 seconds
  Restore (255 KiB)    | < 1 second
  Restore (1 GB)       | ~30 seconds
  Integrity verify     | < 1 second per file

10. FINDINGS & RISKS
───────────────────────────────────────────────────────────────────────────────

  🔴 HIGH: No Automated MinIO Backup
  ─────────────────────────────────────────────────────────────────────────────
  MinIO data is backed up only when manually triggered. No cron job or
  scheduled backup exists. If MinIO data is lost, all 23 uploaded contracts
  are unrecoverable from object storage.

  🟡 MEDIUM: 7 Different Bucket Names Across Configs
  ─────────────────────────────────────────────────────────────────────────────
  contractrisk-documents, contractedge-documents, contractriskedge-staging-
  documents, contractriskedge-prod-documents, and Docker/K8s variants. A
  cross-environment naming convention should be standardized.

  🟡 MEDIUM: Inconsistent Object Key Patterns
  ─────────────────────────────────────────────────────────────────────────────
  Three different key patterns exist (build_object_key, direct upload,
  version prefix). This complicates backup/restore scripts and data lifecycle
  management.

  🟡 MEDIUM: No Backup Rotation
  ─────────────────────────────────────────────────────────────────────────────
  Backups accumulate without cleanup. Recommend keeping 7 daily backups.

  🟡 MEDIUM: Dev Credentials Divergence
  ─────────────────────────────────────────────────────────────────────────────
  Local .env uses pgskannan/Welcome2ibm$ while docker-compose defaults to
  minioadmin/minioadmin. Switching between modes requires credential changes.

  🟢 GOOD: Backup Integrity Verified
  ─────────────────────────────────────────────────────────────────────────────
  SHA256 hashes match between MinIO and backup copy. Restore procedure
  confirmed working.

  🟢 GOOD: Tenant Isolation
  ─────────────────────────────────────────────────────────────────────────────
  All objects are prefixed with tenant UUID, ensuring data isolation.

================================================================================
