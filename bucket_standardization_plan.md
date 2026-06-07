================================================================================
  SPRINT 22 TASK 1.2A — MinIO Bucket Standardization Plan
  Completed: June 5, 2026
================================================================================

EXECUTIVE SUMMARY
───────────────────────────────────────────────────────────────────────────────

  7 distinct bucket names exist across the codebase.
  1 bucket actually exists in MinIO.
  1 Pydantic default would silently fail if env var is unset.
  5 are unused legacy/documentation names.

  Recommendation: Standardize to a SINGLE canonical bucket name:
    contractrisk-documents

  This is the name that already exists in MinIO, is used by local .env,
  K8s ConfigMap, 15+ hardcoded fallbacks, and all backup scripts.

================================================================================
BUCKET NAME INVENTORY
================================================================================

  1. contractrisk-documents        ✅ ACTIVE    — 35+ references
  2. contractedge-documents        ❌ BROKEN    — Pydantic default (never created)
  3. contractrisk-documents-dev    ⚠ LEGACY    — Docker Compose (dev)
  4. contractrisk-documents-staging ⚠ LEGACY   — Docker Compose (staging)
  5. contractrisk-documents-prod   📝 DOC ONLY  — enterprise-architecture doc
  6. contractriskedge-staging-     📝 DOC ONLY  — audit finding
     documents
  7. contractriskedge-prod-        📝 DOC ONLY  — audit finding
     documents

================================================================================
DETAILED FINDINGS
================================================================================

FINDING 1: Pydantic Default Mismatch (CRITICAL)
───────────────────────────────────────────────────────────────────────────────

  File: backend/app/config.py, line 210
  Current: s3_bucket: str = "contractedge-documents"

  Impact: If the S3_BUCKET env var is not set, the application falls through
  to a bucket name that DOES NOT EXIST. Every file upload will fail with
  "NoSuchBucket" error.

  All .env files, K8s ConfigMaps, and hardcoded fallbacks use
  "contractrisk-documents" — the Pydantic default is the ONLY place that
  uses "contractedge-documents".

  Fix: Change to s3_bucket: str = "contractrisk-documents"

FINDING 2: Docker Compose Env Var Name Mismatch (HIGH)
───────────────────────────────────────────────────────────────────────────────

  File: docker-compose.yml, lines 73, 112
  Current: S3_BUCKET_NAME=contractrisk-documents-dev

  Problem: Pydantic settings maps S3_BUCKET (not S3_BUCKET_NAME) to
  s3_bucket. The env var S3_BUCKET_NAME is silently ignored.

  Impact: Docker Compose deployments use the Pydantic default
  "contractedge-documents" instead of the intended value.

  Fix: Change S3_BUCKET_NAME to S3_BUCKET in docker-compose.yml

FINDING 3: Staging Docker Compose Env Var Name Mismatch (HIGH)
───────────────────────────────────────────────────────────────────────────────

  File: deploy/staging/docker-compose.yml, lines 219, 279, 339, 396, 438, 480, 522
  Current: S3_BUCKET_NAME=contractrisk-documents-staging

  Problem: Same as Finding 2 — S3_BUCKET_NAME is silently ignored.
  7 separate service definitions all have this mismatch.

  Impact: Staging deployments use the wrong bucket name.

  Fix: Change S3_BUCKET_NAME to S3_BUCKET in deploy/staging/docker-compose.yml

FINDING 4: K8s ConfigMap Env Var Name Mismatch (HIGH)
───────────────────────────────────────────────────────────────────────────────

  Files: deploy/k8s/configmap.yaml (line 66), api-deployment.yaml (line 108),
         worker-deployment.yaml (line 93)
  Current: S3_BUCKET_NAME: "contractrisk-documents"
           valueFrom: secretKeyRef: s3_bucket_name

  Problem: Same as Finding 2 — S3_BUCKET_NAME is silently ignored.

  Impact: Production K8s deployments use the Pydantic default
  "contractedge-documents" instead of "contractrisk-documents".

  Fix: Change S3_BUCKET_NAME to S3_BUCKET in all K8s configs.

FINDING 5: Hardcoded Fallbacks (MEDIUM)
───────────────────────────────────────────────────────────────────────────────

  15+ files have hardcoded "contractrisk-documents" as a fallback when
  settings.s3_bucket is used. These are correct but fragile — if the
  canonical bucket name ever changes, all of these must be updated.

  Affected files include:
    backend/app/domains/ingestion/service.py
    backend/app/domains/ingestion/orchestrator.py
    backend/app/domains/review/service.py
    backend/app/domains/review/router.py
    backend/app/domains/review/document_generation.py
    backend/app/domains/ingestion/extraction/service.py
    backend/app/domains/ingestion/extraction/worker.py
    backend/tests/conftest.py
    backend/seed_data.py
    start_api.sh

  Fix: Remove all hardcoded fallbacks. Use settings.s3_bucket exclusively.
  (Requires Finding 1 to be fixed first so the default is correct.)

================================================================================
STANDARDIZATION PLAN
================================================================================

  Phase 1: Fix the Pydantic Default (5 minutes, 1 file)
  ──────────────────────────────────────────────────────────────────────────────
  File: backend/app/config.py, line 210
  Change: s3_bucket: str = "contractedge-documents"
  To:     s3_bucket: str = "contractrisk-documents"

  This ensures that if S3_BUCKET env var is unset, the application uses
  the correct bucket name that actually exists.

  Phase 2: Fix Docker Compose Env Var Names (5 minutes, 2 files)
  ──────────────────────────────────────────────────────────────────────────────
  File: docker-compose.yml
  Change: S3_BUCKET_NAME=contractrisk-documents-dev
  To:     S3_BUCKET=contractrisk-documents-dev

  File: deploy/staging/docker-compose.yml (7 occurrences)
  Change: S3_BUCKET_NAME=contractrisk-documents-staging
  To:     S3_BUCKET=contractrisk-documents-staging

  Phase 3: Fix K8s ConfigMap Env Var Names (5 minutes, 3 files)
  ──────────────────────────────────────────────────────────────────────────────
  File: deploy/k8s/configmap.yaml
  Change: S3_BUCKET_NAME: "contractrisk-documents"
  To:     S3_BUCKET: "contractrisk-documents"

  File: deploy/k8s/api-deployment.yaml
  File: deploy/k8s/worker-deployment.yaml
  Change: name: S3_BUCKET_NAME
  To:     name: S3_BUCKET
  And:    key: s3_bucket_name → key: s3_bucket

  Phase 4: Remove Hardcoded Fallbacks (15 minutes, ~15 files)
  ──────────────────────────────────────────────────────────────────────────────
  In all files where bucket_name is hardcoded as a fallback:
    bucket_name = settings.s3_bucket or "contractrisk-documents"
  Change to:
    bucket_name = settings.s3_bucket

  This is safe once Phase 1 ensures the default is correct.

================================================================================
CANONICAL BUCKET NAME RECOMMENDATION
================================================================================

  Canonical name: contractrisk-documents

  Rationale:
    ✅ Already exists in MinIO (23 objects, actively used)
    ✅ Used by local .env, K8s ConfigMap, and all hardcoded fallbacks
    ✅ Used by all backup scripts and DR runbooks
    ✅ Simple, consistent pattern: {project}-documents

  Environment-specific suffixes should be handled via separate buckets
  (contractrisk-documents-dev, contractrisk-documents-staging) rather
  than changing the base name.

  The Pydantic default MUST match this canonical name to prevent silent
  failures when env vars are unset.

================================================================================
IMPLEMENTATION ORDER
================================================================================

  Priority | Phase | Change                        | Risk  | Effort
  ─────────┼───────┼───────────────────────────────┼───────┼───────
  P1       | 1     | Fix Pydantic default          | Low   | 1 file, 1 line
  P2       | 2     | Fix Docker Compose env vars   | Low   | 2 files, 8 lines
  P2       | 3     | Fix K8s env vars              | Low   | 3 files, 3 lines
  P3       | 4     | Remove hardcoded fallbacks    | Medium | ~15 files

================================================================================
