# ContractRiskEdge — Enterprise Architecture Hardening & Scalability Evolution

## Fortune 500 AI-Native Contract Intelligence Operating System

---

## Table of Contents

1. [Entity Ownership Normalization](#1-entity-ownership-normalization)
2. [Vector Scaling & Embedding Lifecycle](#2-vector-scaling--embedding-lifecycle)
3. [JSONB Governance Strategy](#3-jsonb-governance-strategy)
4. [Workflow Template Versioning](#4-workflow-template-versioning)
5. [AI Prompt Governance Platform](#5-ai-prompt-governance-platform)
6. [Advanced Search Ranking Architecture](#6-advanced-search-ranking-architecture)
7. [Integration Runtime Domain](#7-integration-runtime-domain)
8. [Policy Engine Domain](#8-policy-engine-domain)
9. [Feature Flag & Configuration Platform](#9-feature-flag--configuration-platform)
10. [Analytics Evolution Strategy](#10-analytics-evolution-strategy)
11. [File Storage & Legal Governance](#11-file-storage--legal-governance)
12. [Cost Governance & AI Economics](#12-cost-governance--ai-economics)
13. [Enterprise Hardening Summary](#13-enterprise-hardening-summary)

---

## 1. Entity Ownership Normalization

### 1.1 Problem Statement

The current architecture has workflows, notifications, comments, AI analyses, findings, activity feeds, and obligations using hard foreign keys directly to `contracts`. This creates:

- **Giant joins** — 8+ table joins for simple entity queries
- **Tight coupling** — Cannot associate workflows with vendors, obligations with clauses, etc.
- **Migration pain** — Schema changes cascade across all dependent tables
- **Scalability bottleneck** — Single table (contracts) becomes a hot spot

### 1.2 Polymorphic Entity Reference Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ENTITY REFERENCE SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Two-tier approach:                                                     │
│                                                                         │
│  Tier 1: entity_ref (UUID, entity_type, entity_id, tenant_id)          │
│    └── Used by: notifications, comments, activity_feed, audit_logs     │
│                                                                         │
│  Tier 2: Hard FK (for transactional integrity)                          │
│    └── Used by: workflows, AI analyses, obligations                     │
│    └── BUT: Add entity_type discriminator for future flexibility        │
│                                                                         │
│  Decision Matrix:                                                       │
│                                                                         │
│  ┌─────────────────────┬─────────────────────┬──────────────────────┐   │
│  │ Use Case            │ Strategy            │ Rationale             │   │
│  ├─────────────────────┼─────────────────────┼──────────────────────┤   │
│  │ Notifications       │ entity_ref          │ Multiple entity types │   │
│  │ Comments            │ entity_ref          │ Contracts, clauses,   │   │
│  │ Activity Feed       │ entity_ref          │ vendors, workflows   │   │
│  │ Audit Logs          │ entity_ref          │ Every resource type   │   │
│  │ Attachments         │ entity_ref          │ Any entity can have   │   │
│  │                     │                     │ attachments           │   │
│  ├─────────────────────┼─────────────────────┼──────────────────────┤   │
│  │ Workflows           │ entity_ref +        │ Transactional, but    │   │
│  │                     │ entity_type enum    │ needs to support     │   │
│  │                     │                     │ vendors, obligations  │   │
│  │ AI Analyses         │ entity_ref +        │ Future: clause-level  │   │
│  │                     │ entity_type enum    │ AI analyses           │   │
│  │ Obligations         │ Hard FK (contract)  │ Domain constraint —   │   │
│  │                     │ + entity_ref        │ always on contract    │   │
│  │                     │ (for clause-level)  │ or clause             │   │
│  ├─────────────────────┼─────────────────────┼──────────────────────┤   │
│  │ Contract-Vendor     │ Hard FK             │ Transactional domain  │   │
│  │ Clause-Contract     │ Hard FK             │ integrity required    │   │
│  │ Workflow-Step       │ Hard FK             │                       │   │
│  │ Approval-Workflow   │ Hard FK             │                       │   │
│  └─────────────────────┴─────────────────────┴──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Entity Reference Implementation

```sql
-- ── Polymorphic Entity Reference Type ──────────────────────────────

CREATE TABLE entity_references (
    reference_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(tenant_id),
    entity_type     TEXT NOT NULL,  -- 'contract', 'vendor', 'clause', 'workflow', 'obligation', etc.
    entity_id       UUID NOT NULL,
    -- No FK constraint — polymorphic by design
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique per combination (prevents duplicates)
    UNIQUE (tenant_id, entity_type, entity_id)
);

CREATE INDEX idx_entity_refs_type ON entity_references(tenant_id, entity_type);
CREATE INDEX idx_entity_refs_id ON entity_references(tenant_id, entity_id);

-- ── Usage Pattern: Notifications ───────────────────────────────────

CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL,
    user_id         TEXT NOT NULL,
    type            TEXT NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT,
    severity        risk_severity NOT NULL DEFAULT 'info',

    -- Polymorphic reference (instead of contract_id FK)
    entity_type     TEXT NOT NULL,
    entity_id       UUID NOT NULL,

    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Index for efficient lookup
    FOREIGN KEY (tenant_id, entity_type, entity_id)
        REFERENCES entity_references(tenant_id, entity_type, entity_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_notifications_lookup
    ON notifications(tenant_id, user_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_entity
    ON notifications(tenant_id, entity_type, entity_id);

-- ── Usage Pattern: Workflows (Hybrid: FK + entity_ref) ────────────

CREATE TABLE workflows (
    workflow_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL,
    workflow_type   TEXT NOT NULL,

    -- Entity reference (supports contracts, vendors, obligations, etc.)
    entity_type     TEXT NOT NULL,
    entity_id       UUID NOT NULL,

    -- Optional: direct FK for transactional integrity when entity is a contract
    contract_id     UUID,  -- NULLABLE — only set when entity_type = 'contract'

    status          TEXT NOT NULL DEFAULT 'pending',
    assigned_to     TEXT,
    sla_deadline    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (tenant_id, entity_type, entity_id)
        REFERENCES entity_references(tenant_id, entity_type, entity_id),
    FOREIGN KEY (tenant_id, contract_id)
        REFERENCES contracts(tenant_id, contract_id)
        DEFERRABLE INITIALLY DEFERRED
);
```

### 1.4 Query Optimization Strategy

```sql
-- ── Strategy 1: Materialized Entity Type Registry ──────────────────

CREATE MATERIALIZED VIEW entity_type_summary AS
SELECT
    tenant_id,
    entity_type,
    COUNT(*) AS total_entities,
    MAX(created_at) AS last_created
FROM entity_references
GROUP BY tenant_id, entity_type;

REFRESH MATERIALIZED VIEW CONCURRENTLY entity_type_summary;

-- ── Strategy 2: Partial Indexes for Hot Entities ───────────────────

-- Contracts get their own partial index (most common)
CREATE INDEX idx_notifications_contract
    ON notifications(tenant_id, entity_id)
    WHERE entity_type = 'contract';

-- Vendors get their own partial index
CREATE INDEX idx_notifications_vendor
    ON notifications(tenant_id, entity_id)
    WHERE entity_type = 'vendor';

-- ── Strategy 3: CQRS for Read Models ───────────────────────────────

-- When querying notifications for a contract:
-- 1. Lookup entity_references to validate existence
-- 2. Query notifications with (tenant_id, entity_type, entity_id)
-- 3. Join only if additional entity data needed

EXPLAIN ANALYZE
SELECT n.*
FROM notifications n
WHERE n.tenant_id = :tenant_id
  AND n.entity_type = 'contract'
  AND n.entity_id = :contract_id
  AND n.is_read = FALSE
ORDER BY n.created_at DESC
LIMIT 20;
```

### 1.5 Migration Strategy

```sql
-- ── Phase 1: Create entity_references table ────────────────────────
-- Run immediately, no downtime

CREATE TABLE entity_references (...);

-- ── Phase 2: Backfill existing entities ────────────────────────────
-- Background job, runs per entity type

INSERT INTO entity_references (tenant_id, entity_type, entity_id)
SELECT DISTINCT tenant_id, 'contract', contract_id
FROM contracts
ON CONFLICT DO NOTHING;

INSERT INTO entity_references (tenant_id, entity_type, entity_id)
SELECT DISTINCT tenant_id, 'vendor', vendor_id
FROM vendors
ON CONFLICT DO NOTHING;

-- ── Phase 3: Add entity_type + entity_id columns to dependent tables ──
-- Add as NULLABLE, backfill, then make NOT NULL

ALTER TABLE notifications ADD COLUMN entity_type TEXT;
ALTER TABLE notifications ADD COLUMN entity_id UUID;

UPDATE notifications n
SET entity_type = 'contract', entity_id = n.contract_id
WHERE n.contract_id IS NOT NULL;

ALTER TABLE notifications ALTER COLUMN entity_type SET NOT NULL;
ALTER TABLE notifications ALTER COLUMN entity_id SET NOT NULL;

-- ── Phase 4: Drop old FK columns (optional, after migration verified) ──
-- ALTER TABLE notifications DROP COLUMN contract_id;
```

---

## 2. Vector Scaling & Embedding Lifecycle

### 2.1 Embedding Version Management

```sql
-- ── Embedding Model Registry ───────────────────────────────────────

CREATE TABLE embedding_models (
    model_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name          TEXT NOT NULL,           -- 'text-embedding-3-large'
    model_version       TEXT NOT NULL,           -- '1.0', '2.0'
    dimension           INTEGER NOT NULL,        -- 1536, 1024, 768
    provider            TEXT NOT NULL,           -- 'openai', 'anthropic', 'custom'
    cost_per_1k_tokens  NUMERIC(10,8) NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT FALSE,
    is_default          BOOLEAN NOT NULL DEFAULT FALSE,
    released_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deprecated_at       TIMESTAMPTZ,
    UNIQUE(model_name, model_version)
);

-- ── Chunk Table with Version-Aware Embeddings ──────────────────────

CREATE TABLE chunks (
    chunk_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    chunk_index         INTEGER NOT NULL,
    text                TEXT NOT NULL,
    token_count         INTEGER NOT NULL,

    -- Current active embedding
    embedding           vector(1536),
    embedding_model_id  UUID REFERENCES embedding_models(model_id),

    -- Historical embeddings (for version comparison)
    previous_embeddings JSONB NOT NULL DEFAULT '[]',
    -- [{"model_id": "...", "version": "1.0", "embedding": [...], "generated_at": "..."}]

    chunking_strategy   TEXT NOT NULL DEFAULT 'semantic',
    parent_chunk_id     UUID REFERENCES chunks(chunk_id),
    clause_ids          UUID[] NOT NULL DEFAULT '{}',
    page_numbers        INTEGER[] NOT NULL DEFAULT '{}',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    checksum            TEXT NOT NULL,           -- SHA-256 of text (for dedup)
    metadata            JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
);

-- Partition by tenant hash
CREATE TABLE chunks_p0 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 0);
-- ... 16 partitions total

-- Index on active embedding only
CREATE INDEX idx_chunks_active_embedding
    ON chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE is_active = TRUE AND embedding IS NOT NULL;

-- Index on checksum for dedup
CREATE INDEX idx_chunks_checksum ON chunks(tenant_id, checksum)
    WHERE is_active = TRUE;
```

### 2.2 Vector Lifecycle States

```
                    ┌──────────────┐
                    │   PENDING    │  ← Chunk created, no embedding yet
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
              ┌────>│  EMBEDDING   │  ← Embedding generation in progress
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │   ACTIVE     │  ← Current embedding, searchable
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │  STALE       │  ← Model upgraded, needs re-embed
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │  RE-INDEXING │  ← Re-embedding in progress
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │   ARCHIVED   │  ← Contract archived, chunk retained
              │     └──────────────┘    for audit but not searchable
              │
              └── (return to ACTIVE after re-index)
```

### 2.3 Hot/Warm/Cold Vector Storage

```
┌─────────────────────────────────────────────────────────────────────────┐
│  VECTOR STORAGE TIERS                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TIER 1: HOT (pgvector, primary)                                        │
│    └── Active contracts (last 12 months)                                │
│    └── Currently searchable                                              │
│    └── Full ANN index (ivfflat, lists=100)                              │
│    └── Retention: Until contract archived or model upgraded             │
│                                                                         │
│  TIER 2: WARM (pgvector, secondary partition)                           │
│    └── Archived contracts (12-36 months)                                │
│    └── Searchable but lower priority                                     │
│    └── Reduced ANN index (ivfflat, lists=50)                            │
│    └── Retention: Until archival policy triggers                        │
│                                                                         │
│  TIER 3: COLD (Parquet in S3)                                           │
│    └── Contracts > 36 months                                             │
│    └── Not directly searchable (restore on demand)                      │
│    └── Embeddings stored as float32 arrays in Parquet                   │
│    └── Metadata in PostgreSQL for discovery                             │
│                                                                         │
│  TIER 4: FUTURE (Milvus/Qdrant/Pinecone)                                │
│    └── When pgvector limits are reached (>100M vectors)                 │
│    └── Dual-write during migration                                      │
│    └── pgvector as fallback                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Re-Indexing Strategy

```python
# ── Re-indexing Workflow ────────────────────────────────────────────

class EmbeddingReindexJob:
    """Handle model upgrades and bulk re-embedding."""

    BATCH_SIZE = 100
    MAX_CONCURRENT = 4

    async def reindex_tenant(
        self, tenant_id: str, new_model_id: UUID
    ) -> ReindexReport:
        """Re-index all active chunks for a tenant with a new model."""
        model = await self.get_model(new_model_id)

        # 1. Mark all chunks as STALE
        await self.chunk_repo.mark_stale(tenant_id, new_model_id)

        # 2. Process in batches
        total = 0
        cursor = None
        while True:
            chunks, cursor = await self.chunk_repo.get_stale_batch(
                tenant_id, batch_size=self.BATCH_SIZE, cursor=cursor
            )
            if not chunks:
                break

            # 3. Generate embeddings in parallel
            texts = [c.text for c in chunks]
            embeddings = await self.embedder.embed_batch(
                texts, model=model.model_name
            )

            # 4. Store new embeddings (preserve old in previous_embeddings)
            await self.chunk_repo.update_embeddings(
                chunks, embeddings, new_model_id
            )

            total += len(chunks)
            await self._report_progress(tenant_id, total)

        # 5. Rebuild vector index
        await self._reindex_vector_index(tenant_id)

        return ReindexReport(
            tenant_id=tenant_id,
            model=model.model_name,
            chunks_processed=total,
            completed_at=datetime.utcnow(),
        )
```

### 2.5 Future Vector DB Migration Plan

```
┌─────────────────────────────────────────────────────────────────────────┐
│  VECTOR DB MIGRATION STRATEGY                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1 (Months 1-12): pgvector                                       │
│    └── Up to 50M vectors                                                │
│    └── ivfflat index (lists = sqrt(n))                                 │
│    └── Partitioned by tenant hash                                      │
│    └── Hot/warm separation via partitions                              │
│                                                                         │
│  Phase 2 (Months 12-24): pgvector + external index                     │
│    └── 50M-200M vectors                                                 │
│    └── pgvector for hot data                                            │
│    └── External ANN index (e.g., pgvectorscale)                        │
│    └── Streaming index rebuilds                                         │
│                                                                         │
│  Phase 3 (Months 24+): Dedicated vector DB                             │
│    └── >200M vectors                                                    │
│    └── Milvus / Qdrant / Pinecone                                      │
│    └── Dual-write during migration                                     │
│    └── pgvector as cold tier fallback                                  │
│                                                                         │
│  Migration Pattern:                                                     │
│    1. Enable dual-write (write to both pgvector and new DB)            │
│    2. Backfill historical data to new DB                               │
│    3. Verify query parity (p95 latency, recall@10)                     │
│    4. Switch reads to new DB                                           │
│    5. Disable pgvector writes                                           │
│    6. Decommission pgvector index                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.6 Semantic Cache Strategy

```sql
-- ── Embedding Cache (Redis) ────────────────────────────────────────

-- Cache key: embedding:{model_name}:{sha256(text)}
-- Value: float32[] embedding vector
-- TTL: 24 hours
-- Purpose: Avoid re-embedding identical text chunks

-- ── Query Result Cache (Redis) ─────────────────────────────────────

-- Cache key: search:{tenant_id}:{sha256(query)}:{top_k}:{filters_hash}
-- Value: JSON array of {chunk_id, score, text}
-- TTL: 5 minutes (short, for freshness)
-- Purpose: Avoid repeated identical searches

-- ── Cache Invalidation ─────────────────────────────────────────────

-- On contract update: Invalidate search cache for that contract
-- On model upgrade: Invalidate embedding cache
-- On tenant data change: Invalidate tenant search cache
```

---

## 3. JSONB Governance Strategy

### 3.1 When JSONB Is Allowed

```sql
-- ── ALLOWED Use Cases ──────────────────────────────────────────────

-- 1. Extensible metadata (tenant-specific fields)
ALTER TABLE contracts ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}';
-- Schema: {"department": "Engineering", "cost_center": "CC-123", "project_code": "PRJ-456"}

-- 2. Flexible configuration/settings
ALTER TABLE tenants ADD COLUMN settings JSONB NOT NULL DEFAULT '{}';
-- Schema: {"ai_model": "gpt-4o", "max_tokens": 4096, "features": {"advanced_search": true}}

-- 3. AI analysis outputs (variable structure)
ALTER TABLE ai_outputs ADD COLUMN content JSONB NOT NULL;
-- Schema: {"risk_score": 0.82, "findings": [...], "summary": "..."}

-- 4. Audit log details (variable structure)
ALTER TABLE audit_logs ADD COLUMN details JSONB NOT NULL DEFAULT '{}';
-- Schema: {"before": {...}, "after": {...}, "reason": "..."}

-- ── FORBIDDEN Use Cases ────────────────────────────────────────────

-- ❌ Queryable operational data
-- BAD:  WHERE metadata->>'status' = 'active'
-- GOOD: status TEXT NOT NULL

-- ❌ Filtered/sorted columns
-- BAD:  ORDER BY metadata->>'created_at'
-- GOOD: created_at TIMESTAMPTZ NOT NULL

-- ❌ Foreign key targets
-- BAD:  metadata->>'contract_id'
-- GOOD: contract_id UUID NOT NULL REFERENCES contracts(contract_id)

-- ❌ Frequently updated fields
-- BAD:  UPDATE contracts SET metadata = jsonb_set(metadata, '{status}', '"active"')
-- GOOD: UPDATE contracts SET status = 'active'

-- ❌ Fields used in JOIN conditions
-- BAD:  JOIN ON metadata->>'vendor_id' = vendors.vendor_id
-- GOOD: JOIN ON contracts.vendor_id = vendors.vendor_id
```

### 3.2 JSON Schema Governance

```python
# ── Pydantic-based JSON Schema Validation ──────────────────────────

from pydantic import BaseModel, Field, field_validator
from typing import Optional

class ContractMetadata(BaseModel):
    """Validated schema for contract metadata JSONB."""
    department: Optional[str] = Field(None, max_length=100)
    cost_center: Optional[str] = Field(None, pattern=r'^CC-\d{3,6}$')
    project_code: Optional[str] = Field(None, max_length=50)
    procurement_category: Optional[str] = None
    business_unit: Optional[str] = None

    @field_validator('department')
    @classmethod
    def validate_department(cls, v):
        allowed = ['Engineering', 'Finance', 'Legal', 'Marketing', 'Sales', 'Operations']
        if v and v not in allowed:
            raise ValueError(f'Department must be one of: {allowed}')
        return v

# ── Governance Enforcement ──────────────────────────────────────────

class JSONBGovernance:
    """Enforces JSONB schema compliance."""

    SCHEMAS = {
        'contracts.metadata': ContractMetadata,
        'tenants.settings': TenantSettings,
        'ai_outputs.content': AIOutputContent,
    }

    @classmethod
    def validate(cls, table: str, column: str, data: dict) -> dict:
        schema = cls.SCHEMAS.get(f'{table}.{column}')
        if schema:
            validated = schema(**data)
            return validated.model_dump(exclude_none=True)
        return data
```

### 3.3 JSONB Indexing Standards

```sql
-- ── GIN Indexes for JSONB ──────────────────────────────────────────

-- Use jsonb_path_ops for better performance on path queries
CREATE INDEX idx_contracts_metadata
    ON contracts USING GIN (metadata jsonb_path_ops);

-- Partial GIN index for sparse keys
CREATE INDEX idx_contracts_metadata_department
    ON contracts USING GIN ((metadata -> 'department'))
    WHERE metadata ? 'department';

-- Expression index for specific paths (when querying a single key often)
CREATE INDEX idx_contracts_metadata_cost_center
    ON contracts ((metadata ->> 'cost_center'))
    WHERE metadata ? 'cost_center';
```

### 3.4 Migration Strategy (JSONB to Columns)

```sql
-- ── When to Extract JSONB to Columns ───────────────────────────────

-- Trigger: When a JSONB field is:
-- 1. Queried in WHERE clauses > 1000 times/day
-- 2. Used in JOIN conditions
-- 3. Used in ORDER BY
-- 4. Indexed with expression index > 3 times

-- Migration Pattern:
-- 1. Add new column
ALTER TABLE contracts ADD COLUMN department TEXT;

-- 2. Backfill from JSONB
UPDATE contracts
SET department = metadata ->> 'department'
WHERE metadata ? 'department';

-- 3. Add index
CREATE INDEX idx_contracts_department ON contracts(department);

-- 4. Update application code to use column
-- 5. Remove JSONB extraction in queries
-- 6. (Optional) Remove key from JSONB after migration verified
```

---

## 4. Workflow Template Versioning

### 4.1 Workflow Template Architecture

```sql
-- ── Workflow Templates ─────────────────────────────────────────────

CREATE TABLE workflow_templates (
    template_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),
    name                TEXT NOT NULL,
    description         TEXT,
    workflow_type       TEXT NOT NULL,  -- 'legal_review', 'procurement_approval', etc.
    category            TEXT NOT NULL,  -- 'legal', 'procurement', 'compliance'
    is_system           BOOLEAN NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    current_version_id  UUID,  -- Points to active version
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

CREATE TABLE workflow_template_versions (
    version_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id         UUID NOT NULL REFERENCES workflow_templates(template_id),
    version_number      INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'draft',
    -- 'draft', 'active', 'deprecated', 'superseded'

    definition          JSONB NOT NULL,
    -- {
    --   "steps": [
    --     {"type": "approval", "name": "Legal Review", "assignee": "role:legal_reviewer", "sla_minutes": 480},
    --     {"type": "approval", "name": "VP Approval", "assignee": "role:vp_procurement", "sla_minutes": 240}
    --   ],
    --   "triggers": [{"event": "contract.uploaded", "condition": "contract.value > 100000"}],
    --   "escalation_policy": {"levels": 3, "interval_minutes": 60}
    -- }

    change_notes        TEXT,
    compatibility_hash  TEXT,  -- Hash of definition for detecting breaking changes
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(template_id, version_number)
);

-- ── Workflow Instances (runtime) ───────────────────────────────────

CREATE TABLE workflow_instances (
    workflow_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,

    -- Snapshot of the template at time of creation
    template_id         UUID REFERENCES workflow_templates(template_id),
    template_version_id UUID REFERENCES workflow_template_versions(version_id),
    template_snapshot   JSONB NOT NULL,  -- Frozen copy of definition

    entity_type         TEXT NOT NULL,
    entity_id           UUID NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',
    priority            TEXT NOT NULL DEFAULT 'medium',
    assigned_to         TEXT,
    sla_deadline        TIMESTAMPTZ,
    sla_breached        BOOLEAN NOT NULL DEFAULT FALSE,
    metadata            JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

-- ── Migration Tracking ─────────────────────────────────────────────

CREATE TABLE workflow_migrations (
    migration_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    template_id         UUID NOT NULL REFERENCES workflow_templates(template_id),
    from_version_id     UUID NOT NULL REFERENCES workflow_template_versions(version_id),
    to_version_id       UUID NOT NULL REFERENCES workflow_template_versions(version_id),
    migration_strategy  TEXT NOT NULL,
    -- 'immediate' — All new instances use new version
    -- 'drain'     — Existing instances finish on old version, new use new
    -- 'snapshot'  — Each instance uses the version it was created with

    affected_instances  INTEGER NOT NULL DEFAULT 0,
    completed_instances INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'pending',
    executed_by         TEXT NOT NULL,
    executed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);
```

### 4.2 Version Freeze Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WORKFLOW VERSION FREEZE STRATEGY                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Rule: Every workflow instance freezes its template definition at       │
│  creation time via template_snapshot.                                   │
│                                                                         │
│  Migration Strategies:                                                  │
│                                                                         │
│  immediate:                                                             │
│    └── All NEW instances use the new version                            │
│    └── IN-FLIGHT instances continue with their snapshot                 │
│    └── Use: Bug fixes, non-breaking changes                             │
│                                                                         │
│  drain:                                                                 │
│    └── All NEW instances use the new version                            │
│    └── IN-FLIGHT instances continue until completion                    │
│    └── No instances are migrated mid-flight                             │
│    └── Use: Breaking changes, step reordering                           │
│                                                                         │
│  snapshot:                                                              │
│    └── Each instance permanently uses the version it was created with   │
│    └── No migration occurs                                              │
│    └── Use: Compliance workflows (audit trail integrity)                │
│                                                                         │
│  Compatibility Checking:                                                │
│    └── compatibility_hash detects breaking changes                     │
│    └── Breaking changes: step removed, step type changed, required      │
│        field added                                                     │
│    └── Non-breaking: step label changed, SLA adjusted, optional field   │
│        added                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Workflow Diffing

```python
class WorkflowDiffer:
    """Diff two workflow template versions for audit and migration."""

    def diff(self, old: dict, new: dict) -> WorkflowDiff:
        return WorkflowDiff(
            added_steps=[s for s in new['steps'] if s not in old['steps']],
            removed_steps=[s for s in old['steps'] if s not in new['steps']],
            modified_steps=self._find_modified(old['steps'], new['steps']),
            sla_changes=self._find_sla_changes(old, new),
            trigger_changes=self._find_trigger_changes(old, new),
            is_breaking=self._is_breaking(old, new),
        )

    def _is_breaking(self, old: dict, new: dict) -> bool:
        """Detect breaking changes that require drain migration."""
        old_steps = {s['name']: s for s in old['steps']}
        new_steps = {s['name']: s for s in new['steps']}

        for name, step in old_steps.items():
            if name not in new_steps:
                return True  # Step removed
            if step['type'] != new_steps[name]['type']:
                return True  # Step type changed

        return False
```

---

## 5. AI Prompt Governance Platform

### 5.1 Prompt Lifecycle

```
                    ┌──────────────┐
                    │    DRAFT     │  ← Created by prompt engineer
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   REVIEW     │  ← Peer review + legal review
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  STAGING     │  ← A/B test against current production
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌─────▼────┐ ┌────▼─────┐
        │ PRODUCTION│ │ROLLED BACK│ │ DEPRECATED│
        └─────┬────┘ └──────────┘ └──────────┘
              │
        ┌─────▼────┐
        │ ARCHIVED │
        └──────────┘
```

### 5.2 Prompt Registry Implementation

```sql
-- ── Prompt Registry ────────────────────────────────────────────────

CREATE TABLE prompt_registry (
    prompt_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_key          TEXT NOT NULL,  -- 'risk_assessment', 'clause_classification'
    name                TEXT NOT NULL,
    description         TEXT,
    category            TEXT NOT NULL,  -- 'analysis', 'classification', 'generation', 'extraction'
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    current_version_id  UUID,
    owner               TEXT NOT NULL,  -- Team/person responsible
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(prompt_key)
);

CREATE TABLE prompt_versions (
    version_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id           UUID NOT NULL REFERENCES prompt_registry(prompt_id),
    version_number      INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'draft',
    -- 'draft', 'review', 'staging', 'production', 'rolled_back', 'deprecated', 'archived'

    template            TEXT NOT NULL,  -- Jinja2 template
    variables           JSONB NOT NULL DEFAULT '[]',
    -- [{"name": "contract_text", "type": "string", "required": true}]

    model_config        JSONB NOT NULL DEFAULT '{}',
    -- {"model": "gpt-4o", "temperature": 0.1, "max_tokens": 4096}

    system_prompt       TEXT,  -- System-level instructions

    tools               JSONB NOT NULL DEFAULT '[]',
    -- [{"name": "search_contracts", "enabled": true}]

    guardrails          JSONB NOT NULL DEFAULT '{}',
    -- {"pii_detection": true, "toxicity_check": true, "max_tokens_output": 2048}

    evaluation_results  JSONB NOT NULL DEFAULT '{}',
    -- {"accuracy": 0.92, "hallucination_rate": 0.03, "sample_size": 200}

    change_notes        TEXT,
    created_by          TEXT NOT NULL,
    approved_by         TEXT,
    approved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(prompt_id, version_number)
);

-- ── Tenant Prompt Overrides ────────────────────────────────────────

CREATE TABLE tenant_prompt_overrides (
    override_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),
    prompt_id           UUID NOT NULL REFERENCES prompt_registry(prompt_id),
    version_id          UUID NOT NULL REFERENCES prompt_versions(version_id),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    override_config     JSONB NOT NULL DEFAULT '{}',
    -- {"model": "claude-3-opus", "temperature": 0.05}

    reason              TEXT,
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, prompt_id)
);

-- ── Prompt A/B Test Experiments ────────────────────────────────────

CREATE TABLE prompt_experiments (
    experiment_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt_id           UUID NOT NULL REFERENCES prompt_registry(prompt_id),
    name                TEXT NOT NULL,
    description         TEXT,
    baseline_version_id UUID NOT NULL REFERENCES prompt_versions(version_id),
    variant_version_id  UUID NOT NULL REFERENCES prompt_versions(version_id),
    traffic_percent     INTEGER NOT NULL DEFAULT 50,  -- % to variant
    status              TEXT NOT NULL DEFAULT 'running',
    -- 'running', 'completed', 'cancelled'

    metrics             JSONB NOT NULL DEFAULT '{}',
    -- {"baseline": {"accuracy": 0.88, "latency_ms": 1200},
    --  "variant": {"accuracy": 0.92, "latency_ms": 1500}}

    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    winner_version_id   UUID REFERENCES prompt_versions(version_id),
    created_by          TEXT NOT NULL
);
```

### 5.3 Prompt Deployment Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PROMPT DEPLOYMENT PIPELINE                                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 1: Create/Edit Prompt (DRAFT)                                    │
│    └── Prompt engineer creates version in prompt_registry              │
│    └── Validates template syntax (Jinja2)                              │
│    └── Runs automated tests (variable substitution, token estimation)  │
│                                                                         │
│  Step 2: Submit for Review (REVIEW)                                    │
│    └── Peer review: prompt quality, bias checking                      │
│    └── Legal review: compliance, PII exposure                          │
│    └── Security review: prompt injection vectors                       │
│    └── All reviews must approve                                        │
│                                                                         │
│  Step 3: Deploy to Staging (STAGING)                                   │
│    └── Available in staging environment only                           │
│    └── Automated evaluation against test dataset                       │
│    └── Manual testing by prompt team                                   │
│    └── Performance benchmarking (latency, token usage)                 │
│                                                                         │
│  Step 4: A/B Test (STAGING -> PRODUCTION)                              │
│    └── Traffic split: 50% baseline, 50% variant                        │
│    └── Metrics: accuracy, hallucination rate, latency, cost            │
│    └── Duration: minimum 24 hours, minimum 1000 samples                │
│    └── Auto-promote if variant wins with statistical significance      │
│                                                                         │
│  Step 5: Promote to Production (PRODUCTION)                            │
│    └── All traffic uses new prompt version                             │
│    └── Old version marked as DEPRECATED                                │
│    └── Rollback available for 30 days                                  │
│                                                                         │
│  Step 6: Archive (ARCHIVED)                                            │
│    └── After 30 days without rollback                                  │
│    └── Retained for audit but not deployable                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Prompt Observability

```sql
-- ── Prompt Execution Log ───────────────────────────────────────────

CREATE TABLE prompt_executions (
    execution_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    prompt_id           UUID NOT NULL REFERENCES prompt_registry(prompt_id),
    version_id          UUID NOT NULL REFERENCES prompt_versions(version_id),
    correlation_id      TEXT NOT NULL,

    -- Input
    rendered_prompt     TEXT NOT NULL,  -- Full rendered prompt
    input_tokens        INTEGER NOT NULL,
    variables           JSONB NOT NULL DEFAULT '{}',

    -- Output
    output_text         TEXT,
    output_tokens       INTEGER,
    model_used          TEXT NOT NULL,
    latency_ms          INTEGER NOT NULL,
    cost_usd            NUMERIC(10,8) NOT NULL,

    -- Quality
    confidence          REAL,
    was_truncated       BOOLEAN NOT NULL DEFAULT FALSE,
    had_errors          BOOLEAN NOT NULL DEFAULT FALSE,
    error_message       TEXT,

    -- Safety
    pii_detected        BOOLEAN NOT NULL DEFAULT FALSE,
    guardrail_triggered BOOLEAN NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Partition by month
CREATE TABLE prompt_executions_2026_05 PARTITION OF prompt_executions
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
```

---

## 6. Advanced Search Ranking Architecture

### 6.1 Ranking Pipeline

```
                    ┌──────────────────────┐
                    │     User Query       │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Query Parsing      │
                    │  - Intent detection  │
                    │  - Entity extraction │
                    │  - Query expansion   │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────▼──────┐  ┌─────▼──────┐  ┌──────▼──────┐
       │  Vector     │  │  BM25      │  │  Filters    │
       │  Search     │  │  Full-Text │  │  (metadata) │
       │  (semantic) │  │  (keyword) │  │             │
       └──────┬──────┘  └─────┬──────┘  └──────┬──────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Fusion (RRF)       │
                    │   Top 100 results    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Re-ranking         │
                    │  - Cross-encoder     │
                    │  - Freshness boost   │
                    │  - Authority score   │
                    │  - Personalization   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Result Enrichment  │
                    │  - AI summaries      │
                    │  - Relationship ctx  │
                    │  - Highlighting      │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Final Ranking      │
                    │   Top 20 results     │
                    └──────────────────────┘
```

### 6.2 Ranking Formula

```python
class RankingEngine:
    """Enterprise hybrid ranking with multiple signal sources."""

    # Weights (configurable per tenant)
    WEIGHTS = {
        'vector_similarity': 0.35,
        'bm25_score': 0.20,
        'freshness': 0.10,
        'authority': 0.15,
        'personalization': 0.10,
        'relationship': 0.10,
    }

    async def rank(
        self,
        query: str,
        tenant_id: str,
        user_id: str,
        results: list[RawResult],
    ) -> list[RankedResult]:
        """Multi-signal ranking pipeline."""

        # 1. Score each result
        scored = []
        for result in results:
            score = (
                self.WEIGHTS['vector_similarity'] * result.vector_score +
                self.WEIGHTS['bm25_score'] * result.bm25_score +
                self.WEIGHTS['freshness'] * self._freshness_score(result) +
                self.WEIGHTS['authority'] * await self._authority_score(result) +
                self.WEIGHTS['personalization'] * await self._personalization_score(
                    result, user_id, tenant_id
                ) +
                self.WEIGHTS['relationship'] * await self._relationship_score(
                    result, tenant_id
                )
            )
            scored.append(RankedResult(result=result, score=score))

        # 2. Sort by score
        scored.sort(key=lambda x: x.score, reverse=True)

        return scored[:20]

    def _freshness_score(self, result: RawResult) -> float:
        """Boost recently created/updated documents."""
        days_old = (datetime.utcnow() - result.created_at).days
        if days_old < 7:
            return 1.0
        elif days_old < 30:
            return 0.8
        elif days_old < 90:
            return 0.5
        elif days_old < 365:
            return 0.2
        return 0.0

    async def _authority_score(self, result: RawResult) -> float:
        """Score based on entity authority signals."""
        score = 0.5  # Baseline
        if result.entity_type == 'contract':
            # Active contracts rank higher
            if result.status == 'active':
                score += 0.3
            # High-value contracts rank higher
            if result.contract_value and result.contract_value > 1_000_000:
                score += 0.2
        return min(score, 1.0)

    async def _personalization_score(
        self, result: RawResult, user_id: str, tenant_id: str
    ) -> float:
        """Boost results relevant to the user's role and history."""
        score = 0.0
        # User has interacted with this entity before
        if await self._has_user_interaction(user_id, result.entity_id):
            score += 0.3
        # Entity is in user's assigned workflow
        if await self._is_user_assigned(user_id, result.entity_id):
            score += 0.4
        return score

    async def _relationship_score(
        self, result: RawResult, tenant_id: str
    ) -> float:
        """Boost entities with strong relationship networks."""
        connections = await self._count_relationships(result.entity_id, tenant_id)
        if connections > 10:
            return 0.8
        elif connections > 5:
            return 0.5
        elif connections > 0:
            return 0.2
        return 0.0
```

### 6.3 Search Learning Signals

```sql
-- ── Search Interaction Tracking ────────────────────────────────────

CREATE TABLE search_interactions (
    interaction_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    user_id             TEXT NOT NULL,
    search_id           UUID NOT NULL,  -- Groups interactions from same search
    query               TEXT NOT NULL,
    result_entity_type  TEXT NOT NULL,
    result_entity_id    UUID NOT NULL,
    result_position     INTEGER NOT NULL,  -- 0-based position in results
    interaction_type    TEXT NOT NULL,
    -- 'impression', 'click', 'dwell', 'conversion', 'skip'

    dwell_seconds       INTEGER,  -- How long user viewed result
    is_conversion       BOOLEAN,  -- User took action on result
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- For training future ranking models
    FOREIGN KEY (tenant_id, result_entity_type, result_entity_id)
        REFERENCES entity_references(tenant_id, entity_type, entity_id)
);

CREATE INDEX idx_search_interactions_query
    ON search_interactions(tenant_id, query, interaction_type);
CREATE INDEX idx_search_interactions_user
    ON search_interactions(tenant_id, user_id, created_at DESC);
```

---

## 7. Integration Runtime Domain

### 7.1 Integration Entities

```sql
-- ── Integration Connections ────────────────────────────────────────

CREATE TABLE integration_connections (
    connection_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),
    provider            TEXT NOT NULL,
    -- 'salesforce', 'sap', 'workday', 'docusign', 'slack', 'teams'

    name                TEXT NOT NULL,
    provider_instance   TEXT,  -- e.g., 'mycompany.salesforce.com'
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,

    -- Connection details (encrypted at rest)
    config_encrypted    BYTEA,  -- Encrypted JSON with credentials
    config_kms_key_id   TEXT,   -- KMS key used for encryption

    -- OAuth tokens
    oauth_token_encrypted   BYTEA,
    oauth_refresh_token_encrypted BYTEA,
    oauth_expires_at        TIMESTAMPTZ,

    -- Rate limiting
    rate_limit_per_minute   INTEGER NOT NULL DEFAULT 60,
    rate_limit_per_hour     INTEGER NOT NULL DEFAULT 1000,

    metadata            JSONB NOT NULL DEFAULT '{}',
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

-- ── External Entity Mappings ───────────────────────────────────────

CREATE TABLE external_entity_mappings (
    mapping_id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    connection_id       UUID NOT NULL REFERENCES integration_connections(connection_id),

    -- Internal entity
    entity_type         TEXT NOT NULL,  -- 'contract', 'vendor', 'clause'
    entity_id           UUID NOT NULL,

    -- External entity
    external_system     TEXT NOT NULL,  -- 'salesforce', 'sap'
    external_id         TEXT NOT NULL,  -- ID in external system
    external_url        TEXT,           -- Deep link to external system
    external_data       JSONB,          -- Cached external metadata

    sync_status         TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'synced', 'failed', 'conflict'

    last_synced_at      TIMESTAMPTZ,
    last_error          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, connection_id, external_system, external_id),
    FOREIGN KEY (tenant_id, entity_type, entity_id)
        REFERENCES entity_references(tenant_id, entity_type, entity_id)
);

CREATE INDEX idx_ext_mappings_entity
    ON external_entity_mappings(tenant_id, entity_type, entity_id);
CREATE INDEX idx_ext_mappings_external
    ON external_entity_mappings(tenant_id, external_system, external_id);

-- ── Sync Jobs ──────────────────────────────────────────────────────

CREATE TABLE sync_jobs (
    sync_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    connection_id       UUID NOT NULL REFERENCES integration_connections(connection_id),
    sync_type           TEXT NOT NULL,
    -- 'full', 'incremental', 'backfill', 'one_time'

    direction           TEXT NOT NULL,  -- 'inbound', 'outbound', 'bidirectional'
    status              TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'running', 'completed', 'failed', 'cancelled'

    items_total         INTEGER NOT NULL DEFAULT 0,
    items_processed     INTEGER NOT NULL DEFAULT 0,
    items_failed        INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Webhook Deliveries ─────────────────────────────────────────────

CREATE TABLE webhook_deliveries (
    delivery_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    webhook_id          UUID NOT NULL REFERENCES webhook_registrations(webhook_id),
    event_type          TEXT NOT NULL,
    payload             JSONB NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'delivering', 'delivered', 'failed', 'dead_letter'

    attempt_count       INTEGER NOT NULL DEFAULT 0,
    last_http_status    INTEGER,
    last_error          TEXT,
    next_retry_at       TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_webhook_deliveries_status
    ON webhook_deliveries(tenant_id, status, next_retry_at)
    WHERE status IN ('pending', 'failed');
```

### 7.2 Integration Lifecycle

```
                    ┌──────────────┐
                    │  DISCOVERED  │  ← Integration detected but not configured
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ CONFIGURING  │  ← OAuth flow, credential validation
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
              ┌────>│   ACTIVE     │  ← Integration operational
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │   ERROR      │  ← Auth failure, rate limit, API error
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │  SUSPENDED   │  ← Manual suspension (e.g., quota exceeded)
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │ DISCONNECTED │  ← OAuth revoked, integration removed
              │     └──────────────┘
              │
              └── (return to ACTIVE after re-auth)
```

### 7.3 Retry & DLQ Strategy

```python
class WebhookDeliveryEngine:
    """Enterprise webhook delivery with retry and dead letter queue."""

    RETRY_SCHEDULE = [30, 60, 120, 300, 600]  # Seconds: 30s, 1m, 2m, 5m, 10m
    MAX_RETRIES = len(RETRY_SCHEDULE)

    async def deliver(self, delivery: WebhookDelivery):
        """Deliver webhook with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        delivery.url,
                        json=delivery.payload,
                        headers={
                            'Content-Type': 'application/json',
                            'X-Signature': self._sign_payload(delivery.payload),
                            'X-Delivery-ID': str(delivery.delivery_id),
                        },
                    )

                if response.status_code < 500:
                    # Success or client error (4xx) — don't retry 4xx
                    await self._mark_delivered(delivery, response.status_code)
                    return

            except Exception as exc:
                logger.warning(f"Webhook delivery failed (attempt {attempt + 1})",
                    delivery_id=delivery.delivery_id, error=str(exc))

            # Schedule retry
            if attempt < self.MAX_RETRIES - 1:
                retry_delay = self.RETRY_SCHEDULE[attempt]
                await self._schedule_retry(delivery, retry_delay)

        # All retries exhausted — send to dead letter queue
        await self._send_to_dlq(delivery)
```

---

## 8. Policy Engine Domain

### 8.1 Policy Engine Architecture

```sql
-- ── Policy Definitions ─────────────────────────────────────────────

CREATE TABLE policy_definitions (
    policy_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),
    name                TEXT NOT NULL,
    description         TEXT,
    policy_type         TEXT NOT NULL,
    -- 'approval', 'ai_governance', 'compliance', 'escalation', 'risk_threshold'

    policy_dsl          TEXT NOT NULL,
    -- Rego (OPA) or custom DSL:
    -- "allow { input.contract_value < 100000 }
    --  allow { input.risk_score < 7 }
    --  deny { input.contract_type == "msa" }"

    evaluation_strategy TEXT NOT NULL DEFAULT 'allow_deny',
    -- 'allow_deny', 'score_based', 'routing'

    priority            INTEGER NOT NULL DEFAULT 100,  -- Lower = evaluated first
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    version             INTEGER NOT NULL DEFAULT 1,
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

-- ── Policy Evaluations ─────────────────────────────────────────────

CREATE TABLE policy_evaluations (
    evaluation_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    policy_id           UUID NOT NULL REFERENCES policy_definitions(policy_id),
    policy_version      INTEGER NOT NULL,
    entity_type         TEXT NOT NULL,
    entity_id           UUID NOT NULL,
    input               JSONB NOT NULL,
    result              TEXT NOT NULL,  -- 'allow', 'deny', 'score:0.85'
    decision            TEXT NOT NULL,  -- 'approved', 'rejected', 'escalated'
    reason              TEXT,
    evaluation_time_ms  INTEGER NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_policy_evaluations
    ON policy_evaluations(tenant_id, policy_id, created_at DESC);

-- ── Policy Simulation Runs ─────────────────────────────────────────

CREATE TABLE policy_simulations (
    simulation_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    policy_id           UUID NOT NULL REFERENCES policy_definitions(policy_id),
    name                TEXT NOT NULL,
    test_cases          JSONB NOT NULL,
    -- [{"input": {...}, "expected": "allow"}, ...]

    results             JSONB NOT NULL DEFAULT '{}',
    -- {"pass_count": 45, "fail_count": 3, "failures": [...]}

    status              TEXT NOT NULL DEFAULT 'running',
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);
```

### 8.2 Policy Execution Runtime

```python
class PolicyEngine:
    """Enterprise policy evaluation runtime (OPA-compatible)."""

    def __init__(self):
        self._policies: dict[str, str] = {}  # policy_id -> rego_dsl

    async def evaluate(
        self, policy_id: str, input_data: dict
    ) -> PolicyResult:
        """Evaluate a single policy against input data."""
        dsl = self._policies[policy_id]
        result = await self._run_rego(dsl, input_data)

        await self._log_evaluation(
            policy_id=policy_id,
            input=input_data,
            result=result,
        )

        return result

    async def evaluate_all(
        self, policy_type: str, input_data: dict, tenant_id: str
    ) -> list[PolicyResult]:
        """Evaluate all active policies of a given type."""
        policies = await self._get_active_policies(policy_type, tenant_id)
        results = []
        for policy in sorted(policies, key=lambda p: p.priority):
            result = await self.evaluate(policy.id, input_data)
            results.append(result)
            if result.decision == 'rejected':
                break  # Short-circuit on deny
        return results

    async def _run_rego(self, dsl: str, input_data: dict) -> PolicyResult:
        """Execute Rego policy (OPA-compatible)."""
        # In production, this calls OPA REST API or embedded Rego engine
        # For now, we use a simple rule evaluator
        ...
```

### 8.3 Policy DSL Examples

```rego
# ── Approval Policy ────────────────────────────────────────────────
# File: policies/approval/contract_value.rego

package contractrisk.approval

default allow = false

# Contracts under $100K auto-approve
allow {
    input.contract_value < 100000
}

# Contracts $100K-$1M require procurement manager
allow {
    input.contract_value >= 100000
    input.contract_value < 1000000
    input.approver_role == "procurement_manager"
}

# Contracts over $1M require VP + Legal
allow {
    input.contract_value >= 1000000
    input.approver_role == "vp_procurement"
    input.secondary_approver_role == "legal_director"
}

# High-risk contracts always require legal
deny {
    input.risk_score >= 8
    input.approver_role != "legal_director"
}

# ── AI Governance Policy ───────────────────────────────────────────
# File: policies/ai_governance/model_selection.rego

package contractrisk.ai_governance

# Default: use balanced routing
default model_tier = "balanced"

# Critical analysis always uses best model
model_tier = "critical" {
    input.analysis_type == "legal_reasoning"
}

# High-value contracts use accurate model
model_tier = "accurate" {
    input.contract_value > 500000
}

# Tenant override
model_tier = input.tenant_override {
    input.tenant_override != ""
}
```

---

## 9. Feature Flag & Configuration Platform

### 9.1 Feature Flag Architecture

```sql
-- ── Feature Flags ─────────────────────────────────────────────────

CREATE TABLE feature_flags (
    flag_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key                 TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    description         TEXT,
    category            TEXT NOT NULL,
    -- 'ai', 'ui', 'integration', 'workflow', 'compliance'

    default_value       BOOLEAN NOT NULL DEFAULT FALSE,
    is_kill_switch      BOOLEAN NOT NULL DEFAULT FALSE,
    owner               TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Tenant Feature Overrides ──────────────────────────────────────

CREATE TABLE tenant_feature_overrides (
    override_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),
    flag_id             UUID NOT NULL REFERENCES feature_flags(flag_id),
    value               BOOLEAN NOT NULL,
    reason              TEXT,
    expires_at          TIMESTAMPTZ,  -- Temporary override expiration
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, flag_id)
);

-- ── Gradual Rollout Rules ─────────────────────────────────────────

CREATE TABLE rollout_rules (
    rule_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flag_id             UUID NOT NULL REFERENCES feature_flags(flag_id),
    rollout_percent     INTEGER NOT NULL CHECK (rollout_percent >= 0 AND rollout_percent <= 100),
    targeting_rules     JSONB NOT NULL DEFAULT '{}',
    -- {"tenant_ids": ["uuid1", "uuid2"], "plan_tiers": ["enterprise", "business"]}

    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    created_by          TEXT NOT NULL
);
```

### 9.2 Feature Evaluation Engine

```python
class FeatureFlagEngine:
    """Enterprise feature flag evaluation with targeting and gradual rollout."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self._cache_ttl = 30  # 30-second cache

    async def is_enabled(
        self, flag_key: str, tenant_id: str, user_id: str | None = None
    ) -> bool:
        """Evaluate if a feature is enabled for a given context."""
        # 1. Check kill switch (fast path)
        flag = await self._get_flag(flag_key)
        if flag.is_kill_switch:
            return flag.default_value

        # 2. Check tenant override
        tenant_override = await self._get_tenant_override(flag_key, tenant_id)
        if tenant_override is not None:
            return tenant_override

        # 3. Check gradual rollout
        rollout = await self._get_rollout(flag_key)
        if rollout:
            # Deterministic hash for consistent experience
            hash_key = f"{tenant_id}:{user_id or ''}"
            hash_value = int(hashlib.md5(hash_key.encode()).hexdigest(), 16) % 100
            return hash_value < rollout.rollout_percent

        # 4. Default
        return flag.default_value

    async def get_all_flags(
        self, tenant_id: str, user_id: str | None = None
    ) -> dict[str, bool]:
        """Get all feature flags for a tenant (for frontend initialization)."""
        flags = await self._get_all_flags()
        result = {}
        for flag in flags:
            result[flag.key] = await self.is_enabled(flag.key, tenant_id, user_id)
        return result
```

### 9.3 Runtime Configuration

```sql
-- ── Runtime Configuration ─────────────────────────────────────────

CREATE TABLE runtime_config (
    config_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID,  -- NULL = global default
    key                 TEXT NOT NULL,
    value               JSONB NOT NULL,
    value_type          TEXT NOT NULL,
    -- 'string', 'number', 'boolean', 'json', 'ai_model_config'

    description         TEXT,
    is_encrypted        BOOLEAN NOT NULL DEFAULT FALSE,
    environment         TEXT NOT NULL DEFAULT '*',
    -- '*', 'development', 'staging', 'production'

    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, key, environment)
);

-- ── AI Model Configuration Overrides ──────────────────────────────

-- Allows per-tenant AI model selection without code changes
INSERT INTO runtime_config (tenant_id, key, value, value_type, description)
VALUES (
    'enterprise-tenant-uuid',
    'ai.model_config',
    '{
        "risk_analysis": {"model": "claude-3-opus", "temperature": 0.05},
        "clause_classification": {"model": "gpt-4o-mini", "temperature": 0.1},
        "redline_generation": {"model": "gpt-4o", "temperature": 0.2},
        "rag_query": {"model": "gpt-4o-mini", "temperature": 0.0}
    }',
    'ai_model_config',
    'Per-model configuration overrides for AI analysis pipeline'
);
```

---

## 10. Analytics Evolution Strategy

### 10.1 OLTP vs OLAP Separation

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ANALYTICS EVOLUTION ROADMAP                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1 (Months 1-6): Direct OLTP Queries                             │
│    └── All analytics queries run against PostgreSQL                    │
│    └── Materialized views for common aggregations                      │
│    └── analytics_snapshots table for time-series KPIs                  │
│    └── Limitation: Complex queries affect transactional performance    │
│                                                                         │
│  Phase 2 (Months 6-12): Read Replicas + Dedicated Analytics Schema     │
│    └── Analytics queries redirected to read replicas                   │
│    └── analytics schema with denormalized tables                       │
│    └── Event-driven aggregation pipeline                               │
│    └── Limitation: Still limited by PostgreSQL columnar performance    │
│                                                                         │
│  Phase 3 (Months 12-24): Dedicated OLAP Warehouse                      │
│    └── ClickHouse / BigQuery / Redshift                                │
│    └── Streaming ingestion via Kafka/NSQ                               │
│    └── Denormalized fact + dimension tables                            │
│    └── Sub-second queries on billions of rows                          │
│                                                                         │
│  Phase 4 (Months 24+): Real-Time Analytics                             │
│    └── Real-time streaming (Flink/Kafka Streams)                       │
│    └── AI-powered anomaly detection                                    │
│    └── Predictive analytics on streaming data                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Analytics Ingestion Pipeline

```sql
-- ── Analytics Events (Denormalized, append-only) ──────────────────

CREATE TABLE analytics_events (
    event_id            UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    event_type          TEXT NOT NULL,
    -- 'contract_created', 'contract_analyzed', 'workflow_completed',
    -- 'finding_created', 'obligation_due', 'vendor_risk_updated'

    timestamp           TIMESTAMPTZ NOT NULL,
    dimensions          JSONB NOT NULL,
    -- {"contract_type": "msa", "vendor_category": "cloud", "department": "engineering"}

    metrics             JSONB NOT NULL,
    -- {"risk_score": 0.82, "contract_value": 500000, "analysis_latency_ms": 3200}

    correlation_id      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, event_id, timestamp)
) PARTITION BY RANGE (timestamp);

-- ── Materialized KPI Aggregates ───────────────────────────────────

CREATE MATERIALIZED VIEW kpi_daily AS
SELECT
    tenant_id,
    date_trunc('day', timestamp) AS day,
    event_type,
    dimensions,
    COUNT(*) AS event_count,
    AVG((metrics->>'risk_score')::float) AS avg_risk_score,
    SUM((metrics->>'contract_value')::numeric) AS total_contract_value,
    AVG((metrics->>'analysis_latency_ms')::int) AS avg_latency_ms
FROM analytics_events
GROUP BY tenant_id, date_trunc('day', timestamp), event_type, dimensions;

REFRESH MATERIALIZED VIEW CONCURRENTLY kpi_daily;
```

### 10.3 Warehouse Sync Strategy

```python
class WarehouseSyncJob:
    """Sync analytics data from PostgreSQL to OLAP warehouse."""

    BATCH_SIZE = 10000
    SYNC_INTERVAL = 300  # 5 minutes

    async def sync_to_warehouse(self, last_sync: datetime):
        """Incremental sync of analytics events to warehouse."""
        events = await self._get_new_events(last_sync, limit=self.BATCH_SIZE)

        if not events:
            return last_sync

        # Transform to warehouse schema
        rows = []
        for event in events:
            rows.append({
                'event_id': event.event_id,
                'tenant_id': event.tenant_id,
                'event_type': event.event_type,
                'timestamp': event.timestamp.isoformat(),
                'dimensions': json.dumps(event.dimensions),
                'metrics': json.dumps(event.metrics),
                'correlation_id': event.correlation_id,
            })

        # Batch insert to warehouse
        await self._warehouse.insert('analytics_events', rows)

        return events[-1].created_at

    async def full_refresh(self):
        """Full refresh of warehouse data (for schema changes)."""
        await self._warehouse.truncate('analytics_events')
        cursor = None
        while True:
            batch, cursor = await self._get_all_events_batch(
                batch_size=self.BATCH_SIZE, cursor=cursor
            )
            if not batch:
                break
            await self._warehouse.insert('analytics_events', batch)
```

---

## 11. File Storage & Legal Governance

### 11.1 Storage Lifecycle States

```
                    ┌──────────────┐
                    │   UPLOADED   │  ← File received, virus scan pending
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
              ┌────>│   SCANNING   │  ← Malware + DLP scan
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │   CLEAN      │  ← Passed all scans
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │   ACTIVE     │  ← Available for processing
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │  LEGAL_HOLD  │  ← Subject to litigation hold
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │  ARCHIVED    │  ← Retention period met, moved to cold
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │  DELETED     │  ← Retention + hold expired, destroyed
              │     └──────────────┘
              │
              ├── (QUARANTINED) ← Malware detected
              └── (REJECTED)    ← DLP policy violation
```

### 11.2 Storage Governance Tables

```sql
-- ── Document Storage Records ──────────────────────────────────────

CREATE TABLE document_storage (
    document_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),

    -- Entity association
    entity_type         TEXT NOT NULL,
    entity_id           UUID NOT NULL,

    -- File metadata
    filename            TEXT NOT NULL,
    content_type        TEXT NOT NULL,
    file_size           BIGINT NOT NULL,
    checksum_sha256     TEXT NOT NULL,
    checksum_sha512     TEXT,

    -- Storage location
    storage_tier        TEXT NOT NULL DEFAULT 'hot',
    -- 'hot', 'warm', 'cold', 'glacier'

    storage_path        TEXT NOT NULL,  -- S3 key
    storage_bucket      TEXT NOT NULL,  -- S3 bucket name
    encryption_key_id   TEXT,           -- KMS key for tenant encryption

    -- Security
    scan_status         TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'scanning', 'clean', 'quarantined', 'rejected'

    scan_results        JSONB,  -- Malware scan + DLP results
    dlp_classification  TEXT,   -- 'public', 'internal', 'confidential', 'restricted'

    -- Legal hold
    legal_hold          BOOLEAN NOT NULL DEFAULT FALSE,
    legal_hold_reason   TEXT,
    legal_hold_placed_by TEXT,
    legal_hold_placed_at TIMESTAMPTZ,

    -- Retention
    retention_days      INTEGER NOT NULL DEFAULT 2555,  -- 7 years default
    retention_expires_at TIMESTAMPTZ,
    archival_reason     TEXT,

    -- Lifecycle
    status              TEXT NOT NULL DEFAULT 'active',
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,

    FOREIGN KEY (tenant_id, entity_type, entity_id)
        REFERENCES entity_references(tenant_id, entity_type, entity_id)
);

CREATE INDEX idx_doc_storage_entity
    ON document_storage(tenant_id, entity_type, entity_id);
CREATE INDEX idx_doc_storage_scan
    ON document_storage(tenant_id, scan_status)
    WHERE scan_status IN ('pending', 'scanning');
CREATE INDEX idx_doc_storage_hold
    ON document_storage(tenant_id, legal_hold)
    WHERE legal_hold = TRUE;

-- ── Retention Policies ────────────────────────────────────────────

CREATE TABLE retention_policies (
    policy_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),
    name                TEXT NOT NULL,
    entity_type         TEXT NOT NULL,  -- 'contract', 'audit_log', 'report'
    retention_days      INTEGER NOT NULL,
    storage_tier_after  JSONB NOT NULL DEFAULT '[]',
    -- [{"days": 365, "tier": "warm"}, {"days": 1095, "tier": "cold"}]

    legal_hold_override BOOLEAN NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Legal Hold Records ────────────────────────────────────────────

CREATE TABLE legal_holds (
    hold_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    case_name           TEXT NOT NULL,
    case_reference      TEXT,
    hold_type           TEXT NOT NULL,
    -- 'litigation', 'audit', 'regulatory', 'investigation'

    entity_type         TEXT NOT NULL,
    entity_ids          UUID[] NOT NULL,  -- List of entities under hold
    reason              TEXT NOT NULL,
    placed_by           TEXT NOT NULL,
    placed_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    released_at         TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_legal_holds_active
    ON legal_holds(tenant_id, is_active)
    WHERE is_active = TRUE;
```

### 11.3 DLP Scanning Pipeline

```python
class DocumentScanningPipeline:
    """Enterprise document security scanning (malware + DLP)."""

    async def scan_document(self, document_id: UUID) -> ScanResult:
        """Run full security scan on a document."""
        # 1. Malware scan (ClamAV)
        malware_result = await self._malware_scan(document_id)
        if malware_result.infected:
            await self._quarantine_document(document_id, malware_result)
            return ScanResult(status='quarantined', threat='malware')

        # 2. DLP scan (regex patterns, ML classification)
        dlp_result = await self._dlp_scan(document_id)
        if dlp_result.violations:
            await self._reject_document(document_id, dlp_result)
            return ScanResult(status='rejected', threat='dlp_violation')

        # 3. Document classification
        classification = await self._classify_document(document_id)

        # 4. Mark as clean
        await self._mark_clean(document_id, classification)
        return ScanResult(status='clean', classification=classification)
```

---

## 12. Cost Governance & AI Economics

### 12.1 Cost Allocation Model

```sql
-- ── AI Cost Tracking ──────────────────────────────────────────────

CREATE TABLE ai_cost_entries (
    cost_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    analysis_id         UUID NOT NULL REFERENCES ai_analyses(analysis_id),
    model               TEXT NOT NULL,
    prompt_tokens       INTEGER NOT NULL,
    completion_tokens   INTEGER NOT NULL,
    total_tokens        INTEGER NOT NULL,
    cost_usd            NUMERIC(12,8) NOT NULL,
    analysis_type       TEXT NOT NULL,
    workflow_id         UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_ai_cost_tenant
    ON ai_cost_entries(tenant_id, created_at DESC);

-- ── Tenant AI Budgets ─────────────────────────────────────────────

CREATE TABLE tenant_ai_budgets (
    budget_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),
    budget_period       TEXT NOT NULL,  -- 'daily', 'weekly', 'monthly'
    budget_amount_usd   NUMERIC(12,2) NOT NULL,
    spent_usd           NUMERIC(12,2) NOT NULL DEFAULT 0,
    alert_threshold     REAL NOT NULL DEFAULT 0.8,  -- Alert at 80% consumption
    hard_cap            BOOLEAN NOT NULL DEFAULT FALSE,  -- Hard stop at budget
    current_period_start DATE NOT NULL,
    current_period_end   DATE NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, budget_period, current_period_start)
);

-- ── AI Quota Rules ────────────────────────────────────────────────

CREATE TABLE ai_quota_rules (
    rule_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),
    analysis_type       TEXT NOT NULL,  -- 'risk_analysis', 'clause_classification'
    max_per_day         INTEGER,
    max_per_hour        INTEGER,
    max_concurrent      INTEGER NOT NULL DEFAULT 5,
    priority            TEXT NOT NULL DEFAULT 'normal',
    -- 'low', 'normal', 'high', 'critical'

    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 12.2 Cost Governance Engine

```python
class AICostGovernance:
    """Enterprise AI cost governance with budgeting, quotas, and throttling."""

    async def check_cost_eligibility(
        self, tenant_id: str, analysis_type: str
    ) -> CostDecision:
        """Check if a tenant can run an AI analysis."""
        # 1. Check budget
        budget = await self._get_current_budget(tenant_id)
        if budget and budget.spent_usd >= budget.budget_amount_usd:
            if budget.hard_cap:
                return CostDecision(
                    allowed=False,
                    reason=f"Monthly budget exhausted (${budget.spent_usd}/${budget.budget_amount_usd})"
                )

        # 2. Check daily quota
        daily_count = await self._get_daily_count(tenant_id, analysis_type)
        quota = await self._get_quota(tenant_id, analysis_type)
        if quota and daily_count >= quota.max_per_day:
            return CostDecision(
                allowed=False,
                reason=f"Daily quota exhausted ({daily_count}/{quota.max_per_day})"
            )

        # 3. Check concurrent limit
        concurrent = await self._get_concurrent_count(tenant_id)
        if quota and concurrent >= quota.max_concurrent:
            return CostDecision(
                allowed=False,
                reason=f"Concurrent limit reached ({concurrent}/{quota.max_concurrent})"
            )

        return CostDecision(allowed=True)

    async def record_cost(
        self, tenant_id: str, analysis_id: str, cost: CostEntry
    ):
        """Record AI cost and update budget."""
        await self._insert_cost_entry(cost)
        await self._update_budget_spend(tenant_id, cost.cost_usd)
        await self._check_budget_alert(tenant_id)
```

### 12.3 AI Efficiency Metrics

```sql
-- ── Model Efficiency Scores ───────────────────────────────────────

CREATE MATERIALIZED VIEW model_efficiency_scores AS
SELECT
    model,
    COUNT(*) AS total_calls,
    AVG(latency_ms) AS avg_latency_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95_latency_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99_latency_ms,
    AVG(total_tokens) AS avg_tokens_per_call,
    SUM(cost_usd) AS total_cost,
    SUM(cost_usd) / COUNT(*) AS avg_cost_per_call,
    COUNT(*) / SUM(cost_usd) AS calls_per_dollar
FROM ai_cost_entries
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY model;
```

---

## 13. Enterprise Hardening Summary

### 13.1 Critical Improvements

| # | Improvement | Impact | Effort | Priority |
|---|-------------|--------|--------|----------|
| 1 | Polymorphic entity references | Eliminates coupling, enables cross-domain workflows | Medium | P0 |
| 2 | Embedding version management | Prevents silent model upgrade failures | Medium | P0 |
| 3 | JSONB governance standards | Prevents query performance degradation | Low | P0 |
| 4 | Workflow template versioning | Enables safe workflow evolution | High | P1 |
| 5 | AI prompt governance | Enterprise AI safety and compliance | High | P1 |
| 6 | Advanced search ranking | Improves search relevance at scale | Medium | P1 |
| 7 | Integration runtime | Required for enterprise deployment | High | P1 |
| 8 | Policy engine | Replaces hardcoded rules with configurable policies | High | P2 |
| 9 | Feature flag platform | Enables safe rollouts and kill switches | Medium | P2 |
| 10 | Analytics evolution | Prevents OLTP/OLAP coupling at scale | High | P2 |
| 11 | File governance | Legal compliance and data security | Medium | P2 |
| 12 | AI cost governance | Prevents runaway AI costs | Medium | P1 |

### 13.2 Technical Debt Prevention

```
1. Entity Reference Migration
   └── Every new entity uses entity_references from day one
   └── No new hard FKs to contracts/vendors for cross-cutting concerns

2. JSONB Review Gate
   └── Every new JSONB column requires architecture review
   └── JSONB schema must be defined in governance registry
   └── Fields queried in WHERE/ORDER BY must be extracted to columns

3. Workflow Template Requirement
   └── All new workflow types must define a template
   └── No hardcoded workflow logic in service layer
   └── Every workflow instance freezes its template snapshot

4. Prompt Registry Requirement
   └── All prompts must be registered in prompt_registry
   └── No hardcoded prompts in AI agents
   └── Every prompt change requires a new version

5. Feature Flag Requirement
   └── All new features must be behind a feature flag
   └── Kill switches for AI features
   └── Gradual rollout for UI changes

6. Cost Tracking Requirement
   └── Every AI call must be tracked in ai_cost_entries
   └── All tenants must have AI budgets configured
   └── Cost dashboards for operations team
```

### 13.3 Migration Roadmap

```
Phase 1 (Weeks 1-4): Foundation Hardening
  [ ] Implement entity_references table
  [ ] Backfill existing entities
  [ ] Migrate notifications to entity_ref pattern
  [ ] Implement JSONB governance standards
  [ ] Add JSONB validation to CI pipeline

Phase 2 (Weeks 5-10): AI & Workflow Governance
  [ ] Implement embedding model registry
  [ ] Add embedding version tracking to chunks
  [ ] Build workflow template system
  [ ] Migrate existing workflows to templates
  [ ] Implement prompt registry
  [ ] Build prompt deployment pipeline

Phase 3 (Weeks 11-16): Search & Integration
  [ ] Implement hybrid search ranking pipeline
  [ ] Add search interaction tracking
  [ ] Build integration connection management
  [ ] Implement webhook delivery engine
  [ ] Build external entity mapping system

Phase 4 (Weeks 17-22): Policy & Configuration
  [ ] Implement policy engine (OPA-compatible)
  [ ] Build policy simulation framework
  [ ] Implement feature flag platform
  [ ] Build runtime configuration system
  [ ] Add tenant AI model overrides

Phase 5 (Weeks 23-28): Analytics & Storage
  [ ] Implement analytics event pipeline
  [ ] Build warehouse sync infrastructure
  [ ] Implement document governance tables
  [ ] Build DLP scanning pipeline
  [ ] Implement AI cost tracking

Phase 6 (Weeks 29-32): Governance & Operations
  [ ] Build cost governance dashboards
  [ ] Implement AI quota enforcement
  [ ] Build tenant budget management UI
  [ ] Create operations runbooks
  [ ] Load test all hardened systems
```
