# ContractRiskEdge — Production PostgreSQL Schema Blueprint

## V1 Physical Database Design for Enterprise AI-Native Contract Intelligence

---

## Table of Contents

1. [Schema Overview](#1-schema-overview)
2. [Tenant + User Domain](#2-tenant--user-domain)
3. [Contract Domain](#3-contract-domain)
4. [Ingestion + Chunking + Vector Domain](#4-ingestion--chunking--vector-domain)
5. [AI Domain](#5-ai-domain)
6. [Workflow Domain](#6-workflow-domain)
7. [Notification + Comment Domain](#7-notification--comment-domain)
8. [Audit + Search + Cost Domain](#8-audit--search--cost-domain)
9. [Indexing Strategy](#9-indexing-strategy)
10. [Partitioning Strategy](#10-partitioning-strategy)
11. [JSONB Governance](#11-jsonb-governance)
12. [Migration Governance](#12-migration-governance)
13. [Query Performance](#13-query-performance)
14. [Backup + Recovery](#14-backup--recovery)
15. [Operational Governance](#15-operational-governance)

---

## 1. Schema Overview

### Table Inventory

| # | Table | Domain | Partitioning | Est. Rows/Year | Retention |
|---|-------|--------|-------------|----------------|-----------|
| 1 | `tenants` | Tenant | None | < 10k | Permanent |
| 2 | `users` | Tenant | None | < 100k | Permanent |
| 3 | `roles` | Tenant | None | < 1k | Permanent |
| 4 | `permissions` | Tenant | None | < 200 | Permanent |
| 5 | `user_roles` | Tenant | None | < 500k | Permanent |
| 6 | `contracts` | Contract | HASH(16) | 1M | Permanent |
| 7 | `contract_versions` | Contract | HASH(8) | 5M | Permanent |
| 8 | `contract_files` | Contract | HASH(8) | 1M | Permanent |
| 9 | `document_pages` | Contract | HASH(16) | 50M | Permanent |
| 10 | `ingestion_jobs` | Ingestion | HASH(8) | 1M | 90 days |
| 11 | `chunks` | Vector | HASH(16) | 100M | Permanent |
| 12 | `ai_analyses` | AI | HASH(8) | 5M | Permanent |
| 13 | `ai_findings` | AI | HASH(8) | 50M | Permanent |
| 14 | `workflows` | Workflow | HASH(8) | 5M | 90 days |
| 15 | `workflow_steps` | Workflow | HASH(8) | 25M | 90 days |
| 16 | `workflow_approvals` | Workflow | HASH(8) | 25M | Permanent |
| 17 | `notifications` | Notification | HASH(8) | 50M | 90 days |
| 18 | `comments` | Comment | HASH(8) | 10M | Permanent |
| 19 | `audit_logs` | Audit | RANGE(monthly) | 50M | 7 years |
| 20 | `search_queries` | Search | RANGE(monthly) | 10M | 90 days |
| 21 | `search_clicks` | Search | RANGE(monthly) | 5M | 90 days |
| 22 | `ai_cost_ledger` | Cost | RANGE(monthly) | 10M | 12 months |
| 23 | `ocr_quality_metrics` | OCR | HASH(8) | 1M | 90 days |

**Total tables:** 23  
**Total partitions:** ~200 (at steady state)  
**Estimated total rows/year:** ~400M

### Schema File

The complete production schema is at `infra/production-schema.sql` (650+ lines).

---

## 2. Tenant + User Domain

### 2.1 `tenants`

**Purpose:** Multi-tenant root. Every tenant-scoped table references this.

**Key design decisions:**
- `slug` is UNIQUE for URL-friendly tenant identification
- `domain` enables SSO auto-provisioning (partial index)
- `features` is a TEXT[] array for feature flags (simpler than a separate table for V1)
- `settings` is JSONB for tenant-specific configuration (allowed use case)
- No soft delete — tenants are deactivated via `is_active = FALSE`
- No partitioning — < 10k rows expected

**Query patterns:**
- Lookup by `tenant_id` (PK)
- Lookup by `slug` for URL routing
- Lookup by `domain` for SSO

### 2.2 `users`

**Purpose:** Platform users tied to Auth0 identity.

**Key design decisions:**
- `user_id` is TEXT (Auth0 `sub` claim) — not UUID, because Auth0 controls the identity
- `role` is a simple TEXT CHECK (not FK to roles) for V1 simplicity — roles table is for custom roles
- `permissions` is TEXT[] for granular overrides beyond role
- `metadata` is JSONB for user preferences (allowed use case)
- Soft delete via `deleted_at` — users are never hard-deleted for audit compliance
- `UNIQUE(tenant_id, email)` prevents duplicate emails within a tenant

### 2.3 `roles` + `permissions` + `user_roles`

**Purpose:** Custom role definitions for enterprise tenants.

**Key design decisions:**
- System roles (`is_system = TRUE`) are seeded and cannot be deleted
- Tenant roles can be created for custom permission sets
- `permissions` is a system-wide registry — immutable after creation
- `user_roles` is a simple many-to-many bridge table

### 2.4 Row-Level Security

```sql
-- Applied to ALL tenant-scoped tables
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_{table} ON {table}
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

**Critical:** The application MUST set `app.tenant_id` at the start of each request via:
```sql
SET app.tenant_id = 'tenant-uuid';
```

This is done in the FastAPI tenant middleware before any query executes.

---

## 3. Contract Domain

### 3.1 `contracts`

**Purpose:** Core entity. Represents an uploaded contract document.

**Key design decisions:**
- **Partitioned by HASH(tenant_id)** with 16 partitions — ensures even distribution and parallel index maintenance
- `contract_type` uses TEXT with CHECK constraint (not PG enum) — easier to add values without migration
- `status` lifecycle: `pending → processing → ready → archived` (with `error` as failure state)
- `review_status` tracks the human review workflow separately from processing status
- `risk_score` is denormalized from AI analysis for fast dashboard queries
- `search_vector` is a generated column for full-text search on filename
- Soft delete via `deleted_at`

**Indexes:**
- `idx_contracts_status` — Dashboard filtering by status
- `idx_contracts_type` — Filtering by contract type
- `idx_contracts_created` — Default sort for contract list
- `idx_contracts_reviewer` — "My reviews" query (partial index)
- `idx_contracts_risk` — High-risk contract sorting (partial index)
- `idx_contracts_search` — Full-text search on filename (GIN)
- `idx_contracts_tags` — Tag-based filtering (GIN)

### 3.2 `contract_versions`

**Purpose:** Version history. Each version is a full snapshot (not a diff).

**Key design decisions:**
- 8 partitions (less data than contracts)
- `checksum` is SHA-256 for integrity verification
- `change_notes` documents what changed
- `UNIQUE(contract_id, version_number)` ensures sequential versioning

### 3.3 `contract_files`

**Purpose:** Tracks physical file storage in S3.

**Key design decisions:**
- `scan_status` tracks malware/DLP scanning state
- `is_original` distinguishes uploaded files from processed derivatives (e.g., OCR output)
- `storage_path` + `storage_bucket` enables multi-region S3

### 3.4 `document_pages`

**Purpose:** Extracted text per page from OCR or digital extraction.

**Key design decisions:**
- 16 partitions (high volume — 50M rows/year)
- `method` tracks which extraction engine was used
- `confidence` enables quality filtering in downstream AI
- `UNIQUE(contract_id, page_number)` prevents duplicate pages
- `search_vector` enables page-level full-text search

---

## 4. Ingestion + Chunking + Vector Domain

### 4.1 `ingestion_jobs`

**Purpose:** Tracks document processing pipeline jobs.

**Key design decisions:**
- 8 partitions (moderate volume)
- `progress` enables real-time progress tracking in UI
- `retry_count` enables automatic retry logic
- `extraction_method` records which OCR engine was used
- 90-day retention — completed jobs are not needed for audit

### 4.2 `chunks` (HIGHEST VOLUME TABLE)

**Purpose:** Semantic chunks of contract text with vector embeddings.

**This is the most critical table in the database.** It powers:
- Semantic search (pgvector ANN)
- BM25 full-text search
- AI analysis (chunks are the input to LLM prompts)
- Citation/provenance tracking

**Key design decisions:**
- **16 partitions minimum** — at 100M rows, each partition has ~6.25M rows
- `embedding` is `vector(1536)` — OpenAI text-embedding-3-large dimension
- `embedding_model` tracks which model generated the embedding (for re-indexing)
- `is_active` enables safe re-indexing — old embeddings remain queryable until new ones are ready
- `checksum` enables chunk deduplication (same text = same checksum)
- `page_numbers` is an INTEGER[] array for page-level filtering
- `clause_ids` is a UUID[] array for clause-level filtering (future use)
- `search_vector` is a generated column for BM25 search
- `metadata` is JSONB for chunking strategy parameters

**Chunking defaults:**
- Max chunk size: 512 tokens
- Overlap: 64 tokens
- Strategy: Semantic (paragraph boundaries)

**pgvector index:**
```sql
-- One index per partition, built after data load
CREATE INDEX idx_chunks_p0_embedding ON chunks_p0
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 2500);
```

`lists` parameter: `sqrt(n_rows_per_partition)` = `sqrt(6,250,000)` ≈ **2500**

**Re-indexing trigger:** When chunk count doubles, rebuild with larger `lists`.

---

## 5. AI Domain

### 5.1 `ai_analyses`

**Purpose:** Records each AI analysis run.

**Key design decisions:**
- `analysis_type` supports partial re-analysis (risk only, classify only, etc.)
- `model_used` + `provider` enables multi-provider tracking
- Token and cost fields enable AI cost governance
- `latency_ms` enables performance monitoring
- 8 partitions (5M rows/year)

### 5.2 `ai_findings`

**Purpose:** Individual risk findings/clause classifications.

**Key design decisions:**
- `finding_type` distinguishes risk findings from classifications from obligations
- `chunk_ids` is a UUID[] array linking to source chunks (polymorphic, avoids join table)
- `severity` enables priority-based filtering
- `status` lifecycle: `open → acknowledged → resolved/dismissed`
- 8 partitions (50M rows/year — high volume)

---

## 6. Workflow Domain

### 6.1 `workflows`

**Purpose:** Tracks approval/review workflows.

**Key design decisions:**
- 8 partitions (5M rows/year)
- `sla_deadline` enables SLA monitoring
- `sla_breached` is a denormalized flag for fast dashboard queries
- 90-day retention after completion (configurable)

### 6.2 `workflow_steps` + `workflow_approvals`

**Purpose:** Multi-step workflow tracking with approval decisions.

**Key design decisions:**
- `workflow_approvals` is permanent (audit requirement)
- `conditions` JSONB in approvals supports conditional approval (e.g., "approved with changes")

---

## 7. Notification + Comment Domain

### 7.1 `notifications`

**Purpose:** In-app notifications.

**Key design decisions:**
- Polymorphic `entity_type` + `entity_id` instead of hard FKs
- 8 partitions, 90-day retention
- `idx_notifications_user` is the primary query path (user's inbox)

### 7.2 `comments`

**Purpose:** Threaded comments on contracts, clauses, workflows.

**Key design decisions:**
- Polymorphic entity reference
- `parent_comment_id` enables threading (self-referencing FK)
- `mentions` TEXT[] array enables @mention notifications
- Soft delete (comments are hidden, not deleted, for audit)

---

## 8. Audit + Search + Cost Domain

### 8.1 `audit_logs` (APPEND-ONLY)

**Purpose:** Immutable audit trail for all compliance-relevant actions.

**CRITICAL RULES:**
- **No UPDATE permitted** — enforced by trigger
- **No DELETE permitted** — enforced by trigger
- **No ALTER after data exists** — plan schema carefully

**Key design decisions:**
- **Partitioned by RANGE(created_at)** — monthly partitions
- 7-year retention (regulatory requirement)
- `details` JSONB stores before/after snapshots
- `correlation_id` enables distributed tracing across services
- Partitions are detached and archived after 7 years, not dropped

### 8.2 `search_queries` + `search_clicks`

**Purpose:** Search quality monitoring and future ranking model training.

**Key design decisions:**
- Monthly RANGE partitions
- 90-day retention for raw data (aggregated data retained longer)
- `search_clicks` links to `search_queries` for click-through analysis

### 8.3 `ai_cost_ledger`

**Purpose:** Every AI API call is tracked for cost attribution.

**Key design decisions:**
- Monthly RANGE partitions
- 12-month retention
- `was_cached` tracks cache effectiveness
- `had_retry` tracks reliability issues

---

## 9. Indexing Strategy

### 9.1 Index Types Used

| Type | When | Example |
|------|------|---------|
| **B-tree** | Default for equality/lookup | `idx_contracts_status` |
| **B-tree (composite)** | Multi-column filters | `idx_contracts_tenant_created` |
| **B-tree (partial)** | Filtered subsets | `idx_contracts_reviewer` (WHERE assigned IS NOT NULL) |
| **GIN** | Array/JSONB/Full-text | `idx_contracts_tags`, `idx_contracts_search` |
| **ivfflat** | ANN vector search | `idx_chunks_p0_embedding` |
| **UNIQUE** | Uniqueness constraints | `idx_users_tenant_email` |

### 9.2 Complete Index List

```sql
-- Tenants
idx_tenants_slug                         -- UNIQUE B-tree
idx_tenants_domain                       -- B-tree partial (WHERE domain IS NOT NULL)

-- Users
idx_users_tenant                         -- B-tree
idx_users_email                          -- B-tree
idx_users_tenant_email                   -- UNIQUE B-tree composite

-- Contracts
idx_contracts_status                     -- B-tree composite (tenant_id, status)
idx_contracts_type                       -- B-tree composite (tenant_id, contract_type)
idx_contracts_created                    -- B-tree composite (tenant_id, created_at DESC)
idx_contracts_reviewer                   -- B-tree partial (WHERE assigned IS NOT NULL)
idx_contracts_risk                       -- B-tree partial (WHERE risk IS NOT NULL)
idx_contracts_search                     -- GIN (search_vector)
idx_contracts_tags                       -- GIN (tags)

-- Chunks
idx_chunks_contract                      -- B-tree composite (tenant_id, contract_id, chunk_index)
idx_chunks_active                        -- B-tree partial (WHERE is_active = TRUE)
idx_chunks_checksum                      -- B-tree partial (WHERE checksum IS NOT NULL)
idx_chunks_search                        -- GIN (search_vector)
idx_chunks_pages                         -- GIN (page_numbers)
idx_chunks_p{0-15}_embedding             -- ivfflat (embedding) — one per partition

-- Workflows
idx_workflows_contract                   -- B-tree composite
idx_workflows_assignee                   -- B-tree partial
idx_workflows_sla                        -- B-tree partial
idx_workflows_status                     -- B-tree composite

-- Audit logs
idx_audit_logs_tenant                    -- B-tree composite (tenant_id, created_at DESC)
idx_audit_logs_action                    -- B-tree composite
idx_audit_logs_resource                  -- B-tree composite
idx_audit_logs_user                      -- B-tree composite

-- Notifications
idx_notifications_user                   -- B-tree composite
idx_notifications_entity                 -- B-tree composite

-- AI Cost
idx_ai_cost_tenant                       -- B-tree composite
idx_ai_cost_model                        -- B-tree composite
```

### 9.3 Index Maintenance

- **B-tree indexes:** Auto-maintained by PostgreSQL
- **GIN indexes:** Auto-maintained, but VACUUM is important for update-heavy tables
- **ivfflat indexes:** Must be rebuilt when data volume doubles (or quality degrades)
- **Partial indexes:** Require no special maintenance

---

## 10. Partitioning Strategy

### 10.1 Partitioned Tables

| Table | Type | Key | Count | Retention |
|-------|------|-----|-------|-----------|
| `contracts` | HASH | `tenant_id` | 16 | Permanent |
| `contract_versions` | HASH | `tenant_id` | 8 | Permanent |
| `contract_files` | HASH | `tenant_id` | 8 | Permanent |
| `document_pages` | HASH | `tenant_id` | 16 | Permanent |
| `chunks` | HASH | `tenant_id` | 16 | Permanent |
| `ingestion_jobs` | HASH | `tenant_id` | 8 | 90 days |
| `ai_analyses` | HASH | `tenant_id` | 8 | Permanent |
| `ai_findings` | HASH | `tenant_id` | 8 | Permanent |
| `workflows` | HASH | `tenant_id` | 8 | 90 days |
| `workflow_steps` | HASH | `tenant_id` | 8 | 90 days |
| `workflow_approvals` | HASH | `tenant_id` | 8 | Permanent |
| `notifications` | HASH | `tenant_id` | 8 | 90 days |
| `comments` | HASH | `tenant_id` | 8 | Permanent |
| `ocr_quality_metrics` | HASH | `tenant_id` | 8 | 90 days |
| `audit_logs` | RANGE | `created_at` | Monthly | 7 years |
| `search_queries` | RANGE | `created_at` | Monthly | 90 days |
| `search_clicks` | RANGE | `created_at` | Monthly | 90 days |
| `ai_cost_ledger` | RANGE | `created_at` | Monthly | 12 months |

### 10.2 HASH Partitioning Rules

- **HASH(tenant_id)** ensures all rows for a tenant are in the same partition
- **16 partitions** for high-volume tables (chunks, contracts, document_pages)
- **8 partitions** for medium-volume tables
- Partitions can be added by splitting existing ones (requires data migration)
- New tenants automatically distribute across existing partitions

### 10.3 RANGE Partitioning Rules

- Monthly partitions created 3 months in advance
- Partitions named: `{table}_YYYY_MM`
- Default partition catches any data outside defined ranges
- Archival: Detach partition, export to Parquet in S3, drop from PostgreSQL

### 10.4 Partition Maintenance Schedule (Celery Beat)

```python
# Run 1st of every month
@celery_app.task(name='create_next_partitions')
def create_next_partitions():
    """Create partitions for the next 3 months."""
    for table in ['audit_logs', 'search_queries', 'search_clicks', 'ai_cost_ledger']:
        for month in range(1, 4):
            date = datetime.utcnow() + timedelta(days=30 * month)
            partition_name = f"{table}_{date.strftime('%Y_%m')}"
            # CREATE TABLE {partition_name} PARTITION OF {table} ...

# Run 1st of every quarter
@celery_app.task(name='archive_old_partitions')
def archive_old_partitions():
    """Archive partitions older than retention period."""
    # For audit_logs: detach partitions > 7 years old
    # For notifications: detach partitions > 90 days old
    # Export to Parquet in S3, then DROP
```

---

## 11. JSONB Governance

### 11.1 Allowed Use Cases

| Table.Column | Purpose | Schema | Indexed? |
|-------------|---------|--------|----------|
| `tenants.settings` | Tenant configuration | `{"ai_model": "gpt-4o", "max_tokens": 4096}` | No |
| `contracts.metadata` | Extensible fields | `{"department": "Eng", "project": "PRJ-123"}` | GIN (jsonb_path_ops) |
| `audit_logs.details` | Variable audit context | `{"before": {...}, "after": {...}}` | No |
| `workflows.metadata` | Workflow config | `{"source": "api", "auto_assigned": true}` | No |
| `document_pages.metadata` | OCR metadata | `{"tables_detected": 3, "has_signature": true}` | No |
| `users.metadata` | User preferences | `{"notifications": {"email": true}}` | No |

### 11.2 Forbidden Use Cases

```
❌ Queryable operational data
   BAD:  WHERE metadata->>'status' = 'active'
   GOOD: status TEXT NOT NULL CHECK (status IN ('active', ...))

❌ Sortable date fields
   BAD:  ORDER BY metadata->>'created_at'
   GOOD: created_at TIMESTAMPTZ NOT NULL

❌ Foreign key targets
   BAD:  metadata->>'contract_id'
   GOOD: contract_id UUID NOT NULL REFERENCES contracts(contract_id)

❌ Frequently updated fields
   BAD:  UPDATE ... SET metadata = jsonb_set(metadata, '{status}', '"active"')
   GOOD: UPDATE ... SET status = 'active'

❌ JOIN conditions
   BAD:  JOIN ON metadata->>'vendor_id' = vendors.vendor_id
   GOOD: JOIN ON contracts.vendor_id = vendors.vendor_id
```

### 11.3 Migration Path (JSONB → Column)

When a JSONB field is queried in WHERE > 1000x/day:
1. Add column: `ALTER TABLE contracts ADD COLUMN department TEXT;`
2. Backfill: `UPDATE contracts SET department = metadata->>'department' WHERE metadata ? 'department';`
3. Add index: `CREATE INDEX idx_contracts_department ON contracts(department);`
4. Update application code to use column
5. Remove JSONB extraction from queries

---

## 12. Migration Governance

### 12.1 Alembic Strategy

```
alembic/
├── env.py
├── versions/
│   ├── 001_create_tenants_users.py
│   ├── 002_create_contracts.py
│   ├── 003_create_chunks.py
│   ├── 004_create_ai_tables.py
│   ├── 005_create_workflows.py
│   ├── 006_create_audit_logs.py
│   ├── 007_create_notifications.py
│   ├── 008_create_search_tables.py
│   ├── 009_create_cost_ledger.py
│   └── 010_create_indexes.py
└── script.py.mako
```

### 12.2 Migration Rules

1. **Every migration MUST have both `upgrade()` and `downgrade()`**
2. **Migrations MUST NOT lock tables for > 5 seconds**
   - Use `CREATE INDEX CONCURRENTLY` for large tables
   - Use `ALTER TABLE ... ADD COLUMN` (not blocking in PG 16)
3. **Large table changes use expand/contract pattern:**
   - Add column (NULLABLE)
   - Backfill in background job
   - Add NOT NULL constraint (separate migration)
   - Drop old column (separate deployment)
4. **Migration review checklist:**
   - [ ] Downgrade script exists
   - [ ] No long-running locks
   - [ ] Index created (if needed for new column)
   - [ ] RLS policy updated (if tenant table)
   - [ ] Trigger updated (if audit table)

### 12.3 Zero-Downtime Migration Pattern

```python
"""Example: Add a new column with backfill."""

def upgrade():
    # Step 1: Add column (non-blocking in PG 16)
    op.add_column('contracts', sa.Column('department', sa.Text()))

def upgrade_post_deploy():
    # Step 2: Backfill in background (run after deploy)
    # UPDATE contracts SET department = metadata->>'department'
    # WHERE metadata ? 'department' AND department IS NULL;

def upgrade_v2():
    # Step 3: Make NOT NULL (separate deploy, after backfill completes)
    op.alter_column('contracts', 'department', nullable=False)
```

---

## 13. Query Performance

### 13.1 Hot Queries

```sql
-- Q1: Dashboard — list recent contracts
EXPLAIN ANALYZE
SELECT contract_id, filename, status, contract_type, risk_score, created_at
FROM contracts
WHERE tenant_id = '...' AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 20;
-- → Index Only Scan on idx_contracts_created

-- Q2: Vector search — find similar chunks
EXPLAIN ANALYZE
SELECT chunk_id, text, 1 - (embedding <=> '[...]'::vector) AS similarity
FROM chunks
WHERE tenant_id = '...' AND embedding IS NOT NULL AND is_active = TRUE
ORDER BY embedding <=> '[...]'::vector
LIMIT 20;
-- → ANN Index Scan on idx_chunks_pN_embedding

-- Q3: BM25 search — keyword search
EXPLAIN ANALYZE
SELECT chunk_id, text, ts_rank(search_vector, query) AS rank
FROM chunks, plainto_tsquery('english', 'indemnification liability') AS query
WHERE tenant_id = '...' AND search_vector @@ query AND is_active = TRUE
ORDER BY rank DESC
LIMIT 20;
-- → Bitmap Heap Scan on idx_chunks_search

-- Q4: Active workflows for user
EXPLAIN ANALYZE
SELECT w.* FROM workflows w
WHERE w.tenant_id = '...' AND w.assigned_to = 'user_123'
  AND w.status IN ('pending', 'active')
ORDER BY w.sla_deadline ASC;
-- → Index Scan on idx_workflows_assignee

-- Q5: Audit log for resource
EXPLAIN ANALYZE
SELECT * FROM audit_logs
WHERE tenant_id = '...' AND resource_type = 'contract' AND resource_id = '...'
ORDER BY created_at DESC
LIMIT 50;
-- → Index Scan on idx_audit_logs_resource
```

### 13.2 Anti-Patterns to Avoid

```
❌ N+1 queries in REST endpoints
   BAD:  For each contract in list, query chunks separately
   GOOD: JOIN or batch load

❌ SELECT * in production queries
   BAD:  SELECT * FROM contracts
   GOOD: SELECT contract_id, filename, status FROM contracts

❌ Unbounded pagination
   BAD:  LIMIT 1000000
   GOOD: LIMIT 100 (with cursor or keyset pagination)

❌ Sequential scan on large tables
   BAD:  WHERE metadata->>'status' = 'active' (no index)
   GOOD: WHERE status = 'active' (indexed column)

❌ JSONB for queryable fields (see JSONB governance)

❌ Missing tenant_id filter
   BAD:  SELECT * FROM contracts WHERE status = 'active'
   GOOD: SELECT * FROM contracts WHERE tenant_id = '...' AND status = 'active'
```

### 13.3 Pagination Strategy

**V1: Offset pagination** (simpler, acceptable for < 10k pages)
```sql
SELECT * FROM contracts
WHERE tenant_id = '...'
ORDER BY created_at DESC
LIMIT 20 OFFSET 40;
```

**V2+: Keyset pagination** (for large datasets)
```sql
SELECT * FROM contracts
WHERE tenant_id = '...' AND created_at < :last_created_at
ORDER BY created_at DESC
LIMIT 20;
```

---

## 14. Backup + Recovery

### 14.1 Backup Strategy

| Backup | Frequency | Retention | Method |
|--------|-----------|-----------|--------|
| WAL archive | Continuous (5 min) | Until next full backup | `archive_command` to S3 |
| Full database | Daily | 30 days | `pg_dump -Fc` |
| Full database | Weekly | 12 months | `pg_dump -Fc` |
| Full database | Monthly | 7 years | `pg_dump -Fc` |

### 14.2 Recovery

```bash
# Point-in-Time Recovery to specific time
pg_ctl -D /data stop
# Restore base backup from S3
aws s3 cp s3://backups/contractrisk_20260601.dump /data/
pg_restore -d contract_risk /data/contractrisk_20260601.dump
# Recover to target time
# Set in postgresql.conf:
#   restore_command = 'aws s3 cp s3://wal/%f %p'
#   recovery_target_time = '2026-06-15 14:30:00 UTC'
pg_ctl -D /data start
```

### 14.3 RPO/RTO

| Metric | Target | Notes |
|--------|--------|-------|
| RPO (Recovery Point Objective) | 5 minutes | WAL archiving every 5 min |
| RTO (Recovery Time Objective) | 1 hour | Restore from daily backup + replay WAL |
| DR RTO | 4 hours | Provision new infra + restore |

---

## 15. Operational Governance

### 15.1 Maintenance Jobs (Celery Beat)

```python
@celery_app.task(name='vacuum_analyze_daily')
def vacuum_analyze_daily():
    """Daily VACUUM ANALYZE during low-traffic period."""
    # VACUUM ANALYZE contracts;
    # VACUUM ANALYZE chunks;
    # VACUUM ANALYZE audit_logs;

@celery_app.task(name='reindex_vectors_weekly')
def reindex_vectors_weekly():
    """Weekly ivfflat index rebuild if needed."""
    # Check index quality, rebuild if degraded

@celery_app.task(name='archive_partitions_monthly')
def archive_partitions_monthly():
    """Monthly partition archival."""
    # Create next 3 months of partitions
    # Detach partitions beyond retention
```

### 15.2 Monitoring Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Connection count | > 150 | > 200 | Scale connection pool |
| Active queries | > 50 | > 100 | Investigate slow queries |
| Long-running queries | > 5s | > 30s | Kill + optimize |
| Chunk count per partition | > 10M | > 20M | Add partitions |
| ivfflat query latency | > 200ms | > 500ms | Rebuild index |
| Audit log partition age | > 6yr 11mo | > 7yr | Archive partition |
| Disk usage | > 70% | > 85% | Add storage or archive |
| Replication lag | > 10s | > 60s | Investigate |

### 15.3 Vacuum Strategy

```sql
-- Configure per table based on update frequency
ALTER TABLE contracts SET (autovacuum_vacuum_scale_factor = 0.01);  -- 1% of rows
ALTER TABLE chunks SET (autovacuum_vacuum_scale_factor = 0.05);    -- 5% of rows (mostly append)
ALTER TABLE audit_logs SET (autovacuum_vacuum_scale_factor = 0.0,   -- Never updated
                            autovacuum_vacuum_threshold = 1000000); -- Only when 1M dead tuples
```

### 15.4 Scaling Thresholds

| Stage | Chunks | Contracts | DB Size | Action |
|-------|--------|-----------|---------|--------|
| **Green** | < 10M | < 100k | < 100 GB | No action |
| **Yellow** | 10-50M | 100k-500k | 100-500 GB | Monitor, tune ivfflat |
| **Orange** | 50-100M | 500k-1M | 500 GB-1 TB | Plan read replica, test external vector DB |
| **Red** | 100-250M | 1M-2.5M | 1-2.5 TB | Migrate to dedicated vector DB, add read replicas |
| **Critical** | > 250M | > 2.5M | > 2.5 TB | External vector DB required, consider sharding |
