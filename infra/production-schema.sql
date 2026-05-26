-- =============================================================================
-- ContractRiskEdge / ContractEdge V1 — Production PostgreSQL Schema
-- =============================================================================
-- Architecture: Modular Monolith, Multi-Tenant SaaS, AI-Native
-- Database: PostgreSQL 16 + pgvector 0.7+
-- Encoding: UTF-8
-- Target: Production Pilot Q3 2026
-- =============================================================================

-- ── Extensions ──────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- 1. TENANT + USER DOMAIN
-- =============================================================================

-- ── 1.1 tenants ─────────────────────────────────────────────────────────────
-- Purpose: Multi-tenant root. Every row in every tenant-scoped table references this.
-- Partitioning: None (small table, < 10k rows expected)
-- Retention: Permanent (tenants are never deleted, only deactivated)
-- Query patterns: Lookup by id, domain check on login, plan check on feature access

CREATE TABLE tenants (
    tenant_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                TEXT NOT NULL,
    slug                TEXT NOT NULL UNIQUE,       -- URL-friendly identifier
    domain              TEXT,                        -- Verified domain for SSO auto-provisioning
    plan                TEXT NOT NULL DEFAULT 'starter'
                        CHECK (plan IN ('starter', 'business', 'enterprise')),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    max_users           INTEGER NOT NULL DEFAULT 10,
    max_contracts       INTEGER NOT NULL DEFAULT 1000,
    features            TEXT[] NOT NULL DEFAULT '{}', -- Feature flag array
    settings            JSONB NOT NULL DEFAULT '{}',  -- Tenant-specific configuration
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_domain ON tenants(domain) WHERE domain IS NOT NULL;

-- ── 1.2 users ──────────────────────────────────────────────────────────────
-- Purpose: Platform users. Tied to Auth0 identity via user_id (Auth0 'sub' claim).
-- Partitioning: None (< 100k rows expected per instance)
-- Retention: Soft delete. Deactivated users retained for audit compliance.

CREATE TABLE users (
    user_id             TEXT PRIMARY KEY,            -- Auth0 'sub' claim
    email               TEXT NOT NULL,
    name                TEXT,
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    role                TEXT NOT NULL DEFAULT 'viewer'
                        CHECK (role IN ('admin', 'analyst', 'viewer', 'api')),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    permissions         TEXT[] NOT NULL DEFAULT '{}',  -- Additional granular permissions
    metadata            JSONB NOT NULL DEFAULT '{}',   -- User preferences, profile data
    last_login          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ                   -- Soft delete
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_users_tenant_email ON users(tenant_id, email);

-- ── 1.3 roles ──────────────────────────────────────────────────────────────
-- Purpose: Tenant-customizable roles. System roles are seeded, tenant roles are addable.
-- Retention: Permanent. Roles are never deleted, only deactivated.

CREATE TABLE roles (
    role_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name                TEXT NOT NULL,               -- 'Legal Reviewer', 'Procurement Manager'
    description         TEXT,
    is_system           BOOLEAN NOT NULL DEFAULT FALSE, -- System roles cannot be deleted
    permissions         TEXT[] NOT NULL DEFAULT '{}',   -- Permission codes
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_roles_tenant ON roles(tenant_id);

-- ── 1.4 permissions ────────────────────────────────────────────────────────
-- Purpose: System-wide permission registry. Immutable after creation.
-- Retention: Permanent.

CREATE TABLE permissions (
    permission_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code                TEXT NOT NULL UNIQUE,        -- 'contract:read', 'contract:write'
    label               TEXT NOT NULL,               -- 'Read Contracts'
    resource            TEXT NOT NULL,               -- 'contract', 'workflow', 'vendor'
    action              TEXT NOT NULL,               -- 'create', 'read', 'update', 'delete', 'approve'
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_permissions_code ON permissions(code);

-- ── 1.5 user_roles ─────────────────────────────────────────────────────────
-- Purpose: Many-to-many user-to-role assignment within a tenant.

CREATE TABLE user_roles (
    user_role_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id             TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id             UUID NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, user_id, role_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(tenant_id, user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);

-- ── Row-Level Security for Tenant Domain ────────────────────────────────────

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

CREATE POLICY tenant_isolation_roles ON roles
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

CREATE POLICY tenant_isolation_user_roles ON user_roles
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- =============================================================================
-- 2. CONTRACT DOMAIN
-- =============================================================================

-- ── 2.1 contracts ──────────────────────────────────────────────────────────
-- Purpose: Core entity. Represents an uploaded contract document.
-- Partitioning: HASH(tenant_id), 16 partitions
-- Retention: Soft delete. Archived after 7 years (or per tenant policy).
-- Query patterns:
--   - List by tenant (most recent first)
--   - Filter by status, type, date range
--   - Full-text search on filename
--   - Lookup by id for detail view

CREATE TABLE contracts (
    contract_id         UUID DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    user_id             TEXT NOT NULL,               -- Uploading user
    filename            TEXT NOT NULL,
    content_type        TEXT NOT NULL,               -- MIME type
    file_size           BIGINT NOT NULL DEFAULT 0,
    file_path           TEXT,                        -- S3 key
    checksum            TEXT,                        -- SHA-256 of original file

    -- Status lifecycle
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN (
                            'pending', 'processing', 'ready', 'error', 'archived'
                        )),
    contract_type       TEXT
                        CHECK (contract_type IS NULL OR contract_type IN (
                            'nda', 'service_agreement', 'license', 'msa', 'sow',
                            'dpa', 'amendment', 'other'
                        )),
    risk_score          REAL CHECK (risk_score >= 0 AND risk_score <= 1),

    -- Document metadata
    version             INTEGER NOT NULL DEFAULT 1,
    total_pages         INTEGER NOT NULL DEFAULT 0,
    total_chunks        INTEGER NOT NULL DEFAULT 0,
    tags                TEXT[] NOT NULL DEFAULT '{}',
    metadata            JSONB NOT NULL DEFAULT '{}',  -- Extensible metadata

    -- Review workflow
    review_status       TEXT NOT NULL DEFAULT 'pending_review'
                        CHECK (review_status IN (
                            'pending_review', 'in_review', 'approved', 'rejected'
                        )),
    assigned_reviewer   TEXT,                        -- user_id of reviewer
    sla_deadline        TIMESTAMPTZ,                 -- Review SLA

    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at         TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ,

    -- Partition key + PK
    PRIMARY KEY (tenant_id, contract_id)
) PARTITION BY HASH (tenant_id);

-- 16 initial partitions
CREATE TABLE contracts_p0 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE contracts_p1 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE contracts_p2 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE contracts_p3 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE contracts_p4 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE contracts_p5 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE contracts_p6 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE contracts_p7 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE contracts_p8 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE contracts_p9 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE contracts_p10 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE contracts_p11 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE contracts_p12 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE contracts_p13 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE contracts_p14 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE contracts_p15 PARTITION OF contracts FOR VALUES WITH (MODULUS 16, REMAINDER 15);

-- Contracts indexes (applied to parent, propagated to partitions)
CREATE INDEX idx_contracts_status ON contracts(tenant_id, status);
CREATE INDEX idx_contracts_type ON contracts(tenant_id, contract_type);
CREATE INDEX idx_contracts_created ON contracts(tenant_id, created_at DESC);
CREATE INDEX idx_contracts_reviewer ON contracts(tenant_id, assigned_reviewer)
    WHERE assigned_reviewer IS NOT NULL AND review_status = 'in_review';
CREATE INDEX idx_contracts_risk ON contracts(tenant_id, risk_score DESC)
    WHERE risk_score IS NOT NULL AND deleted_at IS NULL;

-- Full-text search on filename
ALTER TABLE contracts ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(filename, ''))) STORED;
CREATE INDEX idx_contracts_search ON contracts USING GIN(search_vector);

-- Tags GIN index
CREATE INDEX idx_contracts_tags ON contracts USING GIN(tags);

-- ── 2.2 contract_versions ──────────────────────────────────────────────────
-- Purpose: Version history for contracts. Each version is a full snapshot.
-- Partitioning: HASH(tenant_id), 16 partitions
-- Retention: Permanent (audit requirement)

CREATE TABLE contract_versions (
    version_id          UUID DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    version_number      INTEGER NOT NULL CHECK (version_number >= 1),
    filename            TEXT NOT NULL,
    file_size           BIGINT NOT NULL DEFAULT 0,
    file_path           TEXT,
    checksum            TEXT NOT NULL,
    change_notes        TEXT,
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, version_id),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
        ON DELETE CASCADE,
    UNIQUE(contract_id, version_number)
) PARTITION BY HASH (tenant_id);

-- 8 partitions (less data than contracts)
CREATE TABLE contract_versions_p0 PARTITION OF contract_versions FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_contract_versions_contract
    ON contract_versions(tenant_id, contract_id, version_number DESC);

-- ── 2.3 contract_files ────────────────────────────────────────────────────
-- Purpose: Tracks physical file storage locations and lifecycle.
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: Matches contract retention

CREATE TABLE contract_files (
    file_id             UUID DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    version_id          UUID,
    filename            TEXT NOT NULL,
    content_type        TEXT NOT NULL,
    file_size           BIGINT NOT NULL,
    storage_path        TEXT NOT NULL,               -- S3 key
    storage_bucket      TEXT NOT NULL,
    checksum_sha256     TEXT NOT NULL,
    scan_status         TEXT NOT NULL DEFAULT 'pending'
                        CHECK (scan_status IN ('pending', 'scanning', 'clean', 'quarantined')),
    is_original         BOOLEAN NOT NULL DEFAULT TRUE, -- TRUE = uploaded, FALSE = processed derivative
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,

    PRIMARY KEY (tenant_id, file_id),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE contract_files_p0 PARTITION OF contract_files FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_contract_files_contract
    ON contract_files(tenant_id, contract_id);

-- ── 2.4 document_pages ────────────────────────────────────────────────────
-- Purpose: Extracted text per page from OCR/digital extraction.
-- Partitioning: HASH(tenant_id), 16 partitions
-- Retention: Permanent (source of truth for chunk provenance)

CREATE TABLE document_pages (
    page_id             UUID DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    page_number         INTEGER NOT NULL CHECK (page_number >= 1),
    text                TEXT NOT NULL,
    method              TEXT NOT NULL
                        CHECK (method IN ('pymupdf', 'tesseract', 'ocrmypdf', 'cloud_ocr')),
    confidence          REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    metadata            JSONB NOT NULL DEFAULT '{}',  -- OCR metadata, detected tables, images
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, page_id),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
        ON DELETE CASCADE,
    UNIQUE(contract_id, page_number)
) PARTITION BY HASH (tenant_id);

CREATE TABLE document_pages_p0 PARTITION OF document_pages FOR VALUES WITH (MODULUS 16, REMAINDER 0);
-- ... p1 through p15

CREATE INDEX idx_document_pages_contract
    ON document_pages(tenant_id, contract_id, page_number);

-- Full-text search on page text
ALTER TABLE document_pages ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(text, ''))) STORED;
CREATE INDEX idx_document_pages_search ON document_pages USING GIN(search_vector);

-- ── Row-Level Security for Contract Domain ──────────────────────────────────

ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contract_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE contract_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_pages ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_contracts ON contracts
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_contract_versions ON contract_versions
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_contract_files ON contract_files
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_document_pages ON document_pages
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- =============================================================================
-- 3. INGESTION + CHUNKING + VECTOR DOMAIN
-- =============================================================================

-- ── 3.1 ingestion_jobs ─────────────────────────────────────────────────────
-- Purpose: Tracks document processing pipeline jobs (OCR → chunk → embed).
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: 90 days after completion (configurable)

CREATE TABLE ingestion_jobs (
    job_id              UUID DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    user_id             TEXT NOT NULL,
    filename            TEXT NOT NULL,
    content_type        TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    progress            REAL NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    error_message       TEXT,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    extraction_method   TEXT,
    total_chunks        INTEGER,
    processing_time_ms  INTEGER,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, job_id),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE ingestion_jobs_p0 PARTITION OF ingestion_jobs FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_ingestion_jobs_status ON ingestion_jobs(tenant_id, status);
CREATE INDEX idx_ingestion_jobs_contract ON ingestion_jobs(tenant_id, contract_id);

-- ── 3.2 chunks ────────────────────────────────────────────────────────────
-- Purpose: Semantic chunks of contract text with vector embeddings for search.
-- This is the HIGHEST VOLUME table. Expected: 100M+ rows at scale.
-- Partitioning: HASH(tenant_id), 16 partitions (minimum)
-- Retention: Permanent (tied to contract retention)
-- Query patterns:
--   - Vector similarity search (ANN via ivfflat)
--   - BM25 full-text search
--   - Lookup by contract_id for AI analysis
--   - Metadata filtering (page numbers, clause IDs)

CREATE TABLE chunks (
    chunk_id            UUID DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    chunk_index         INTEGER NOT NULL,            -- Order within contract
    text                TEXT NOT NULL,
    token_count         INTEGER NOT NULL CHECK (token_count >= 1),

    -- Embedding (pgvector)
    embedding           vector(1536),                -- text-embedding-3-large
    embedding_model     TEXT DEFAULT 'text-embedding-3-large',

    -- Provenance
    page_numbers        INTEGER[] NOT NULL DEFAULT '{}',
    clause_ids          UUID[] NOT NULL DEFAULT '{}',

    -- Lifecycle
    is_active           BOOLEAN NOT NULL DEFAULT TRUE, -- FALSE = re-indexed, not searchable
    checksum            TEXT,                          -- SHA-256 of text (for dedup)
    metadata            JSONB NOT NULL DEFAULT '{}',   -- Chunking metadata

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, chunk_id),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

-- 16 partitions
CREATE TABLE chunks_p0 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE chunks_p1 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 1);
CREATE TABLE chunks_p2 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 2);
CREATE TABLE chunks_p3 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 3);
CREATE TABLE chunks_p4 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 4);
CREATE TABLE chunks_p5 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 5);
CREATE TABLE chunks_p6 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 6);
CREATE TABLE chunks_p7 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 7);
CREATE TABLE chunks_p8 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 8);
CREATE TABLE chunks_p9 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 9);
CREATE TABLE chunks_p10 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 10);
CREATE TABLE chunks_p11 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 11);
CREATE TABLE chunks_p12 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 12);
CREATE TABLE chunks_p13 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 13);
CREATE TABLE chunks_p14 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 14);
CREATE TABLE chunks_p15 PARTITION OF chunks FOR VALUES WITH (MODULUS 16, REMAINDER 15);

-- Chunks indexes
CREATE INDEX idx_chunks_contract ON chunks(tenant_id, contract_id, chunk_index);
CREATE INDEX idx_chunks_active ON chunks(tenant_id, is_active)
    WHERE is_active = TRUE;
CREATE INDEX idx_chunks_checksum ON chunks(tenant_id, checksum)
    WHERE checksum IS NOT NULL AND is_active = TRUE;

-- Full-text search on chunk text
ALTER TABLE chunks ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(text, ''))) STORED;
CREATE INDEX idx_chunks_search ON chunks USING GIN(search_vector);

-- GIN index on page_numbers for array containment queries
CREATE INDEX idx_chunks_pages ON chunks USING GIN(page_numbers);

-- ── pgvector ivfflat Indexes ──────────────────────────────────────────────
-- Built AFTER data is loaded. Rebuilt when chunk volume doubles.
-- One index PER PARTITION for parallel maintenance.

-- Calculate lists: sqrt(n_rows) where n_rows is expected rows per partition
-- At 100M total rows / 16 partitions = 6.25M per partition
-- lists = sqrt(6.25M) ≈ 2500

-- These are created per-partition after initial data load:
-- CREATE INDEX idx_chunks_p0_embedding ON chunks_p0
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 2500);
-- ... repeat for p1 through p15

-- ── Row-Level Security for Ingestion Domain ─────────────────────────────────

ALTER TABLE ingestion_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_ingestion_jobs ON ingestion_jobs
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_chunks ON chunks
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- =============================================================================
-- 4. AI DOMAIN
-- =============================================================================

-- ── 4.1 ai_analyses ────────────────────────────────────────────────────────
-- Purpose: Records each AI analysis run against a contract.
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: Permanent (audit requirement for AI explainability)

CREATE TABLE ai_analyses (
    analysis_id         UUID DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    user_id             TEXT,                        -- Who requested (NULL = automated)

    -- Analysis metadata
    analysis_type       TEXT NOT NULL
                        CHECK (analysis_type IN (
                            'full', 'risk_only', 'classify_only', 'obligations_only'
                        )),
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    model_used          TEXT NOT NULL,               -- 'gpt-4o', 'gpt-4o-mini'
    provider            TEXT NOT NULL DEFAULT 'openai',

    -- Results
    risk_score          REAL CHECK (risk_score >= 0 AND risk_score <= 1),
    summary             TEXT,                        -- AI-generated executive summary
    findings_count      INTEGER NOT NULL DEFAULT 0,

    -- Performance
    prompt_tokens       INTEGER NOT NULL DEFAULT 0,
    completion_tokens   INTEGER NOT NULL DEFAULT 0,
    total_tokens        INTEGER NOT NULL DEFAULT 0,
    cost_usd            NUMERIC(12,8) NOT NULL DEFAULT 0,
    latency_ms          INTEGER NOT NULL DEFAULT 0,

    -- Timing
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, analysis_id),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE ai_analyses_p0 PARTITION OF ai_analyses FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_ai_analyses_contract ON ai_analyses(tenant_id, contract_id, created_at DESC);
CREATE INDEX idx_ai_analyses_status ON ai_analyses(tenant_id, status);

-- ── 4.2 ai_findings ────────────────────────────────────────────────────────
-- Purpose: Individual risk findings/clause classifications from AI analysis.
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: Permanent

CREATE TABLE ai_findings (
    finding_id          UUID DEFAULT uuid_generate_v4(),
    analysis_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    contract_id         UUID NOT NULL,

    -- Finding details
    finding_type        TEXT NOT NULL
                        CHECK (finding_type IN (
                            'risk', 'classification', 'obligation', 'redline'
                        )),
    clause_type         TEXT,                        -- 'indemnification', 'liability', etc.
    severity            TEXT NOT NULL
                        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    recommendation      TEXT,
    confidence          REAL CHECK (confidence >= 0 AND confidence <= 1),

    -- Source
    chunk_ids           UUID[] NOT NULL DEFAULT '{}', -- Source chunks
    clause_text         TEXT,                         -- Excerpt

    -- Lifecycle
    status              TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'acknowledged', 'resolved', 'dismissed')),
    resolved_by         TEXT,
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, finding_id),
    FOREIGN KEY (tenant_id, analysis_id) REFERENCES ai_analyses(tenant_id, analysis_id)
        ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE ai_findings_p0 PARTITION OF ai_findings FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_ai_findings_analysis ON ai_findings(tenant_id, analysis_id);
CREATE INDEX idx_ai_findings_contract ON ai_findings(tenant_id, contract_id);
CREATE INDEX idx_ai_findings_severity ON ai_findings(tenant_id, severity, status);

-- ── Row-Level Security for AI Domain ────────────────────────────────────────

ALTER TABLE ai_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_findings ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_ai_analyses ON ai_analyses
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_ai_findings ON ai_findings
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- =============================================================================
-- 5. WORKFLOW DOMAIN
-- =============================================================================

-- ── 5.1 workflows ──────────────────────────────────────────────────────────
-- Purpose: Tracks approval/review workflows for contracts.
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: 90 days after completion (configurable)

CREATE TABLE workflows (
    workflow_id         UUID DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    contract_id         UUID NOT NULL,

    workflow_type       TEXT NOT NULL
                        CHECK (workflow_type IN ('legal_review', 'approval', 'renewal')),
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN (
                            'pending', 'active', 'completed', 'cancelled', 'escalated'
                        )),
    priority            TEXT NOT NULL DEFAULT 'normal'
                        CHECK (priority IN ('urgent', 'high', 'normal', 'low')),

    assigned_to         TEXT,                        -- Current assignee
    sla_deadline        TIMESTAMPTZ,
    sla_breached        BOOLEAN NOT NULL DEFAULT FALSE,

    metadata            JSONB NOT NULL DEFAULT '{}',
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,

    PRIMARY KEY (tenant_id, workflow_id),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE workflows_p0 PARTITION OF workflows FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_workflows_contract ON workflows(tenant_id, contract_id);
CREATE INDEX idx_workflows_assignee ON workflows(tenant_id, assigned_to, status)
    WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_workflows_sla ON workflows(tenant_id, sla_deadline)
    WHERE status IN ('pending', 'active') AND sla_deadline IS NOT NULL;
CREATE INDEX idx_workflows_status ON workflows(tenant_id, status, created_at DESC);

-- ── 5.2 workflow_steps ─────────────────────────────────────────────────────
-- Purpose: Individual steps within a workflow (e.g., "Legal Review", "VP Approval").
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: 90 days after workflow completion

CREATE TABLE workflow_steps (
    step_id             UUID DEFAULT uuid_generate_v4(),
    workflow_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    step_order          INTEGER NOT NULL,
    step_type           TEXT NOT NULL
                        CHECK (step_type IN ('approval', 'review', 'notification', 'escalation')),
    name                TEXT NOT NULL,
    assigned_to         TEXT,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'active', 'approved', 'rejected', 'skipped')),
    sla_minutes         INTEGER,
    completed_at        TIMESTAMPTZ,
    completed_by        TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, step_id),
    FOREIGN KEY (tenant_id, workflow_id) REFERENCES workflows(tenant_id, workflow_id)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE workflow_steps_p0 PARTITION OF workflow_steps FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_workflow_steps_workflow ON workflow_steps(tenant_id, workflow_id, step_order);

-- ── 5.3 workflow_approvals ─────────────────────────────────────────────────
-- Purpose: Records approval decisions for workflow steps.
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: Permanent (audit requirement)

CREATE TABLE workflow_approvals (
    approval_id         UUID DEFAULT uuid_generate_v4(),
    step_id             UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    workflow_id         UUID NOT NULL,
    approver_id         TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected', 'conditionally_approved')),
    comments            TEXT,
    conditions          JSONB,                       -- Conditional approval terms
    decided_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, approval_id),
    FOREIGN KEY (tenant_id, step_id) REFERENCES workflow_steps(tenant_id, step_id)
        ON DELETE CASCADE,
    FOREIGN KEY (tenant_id, workflow_id) REFERENCES workflows(tenant_id, workflow_id)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE workflow_approvals_p0 PARTITION OF workflow_approvals FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_workflow_approvals_step ON workflow_approvals(tenant_id, step_id);
CREATE INDEX idx_workflow_approvals_approver ON workflow_approvals(tenant_id, approver_id, status);

-- ── Row-Level Security for Workflow Domain ──────────────────────────────────

ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_approvals ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_workflows ON workflows
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_workflow_steps ON workflow_steps
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_workflow_approvals ON workflow_approvals
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- =============================================================================
-- 6. NOTIFICATION + COMMENT DOMAIN
-- =============================================================================

-- ── 6.1 notifications ──────────────────────────────────────────────────────
-- Purpose: In-app notifications for users. Email notifications reference this.
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: 90 days (configurable)

CREATE TABLE notifications (
    notification_id     UUID DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    user_id             TEXT NOT NULL,               -- Recipient
    type                TEXT NOT NULL
                        CHECK (type IN (
                            'alert', 'task', 'escalation', 'ai_insight', 'workflow', 'approval'
                        )),
    title               TEXT NOT NULL,
    body                TEXT,
    severity            TEXT NOT NULL DEFAULT 'info'
                        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),

    -- Polymorphic entity reference
    entity_type         TEXT,                        -- 'contract', 'workflow', 'finding'
    entity_id           UUID,

    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    read_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, notification_id)
) PARTITION BY HASH (tenant_id);

CREATE TABLE notifications_p0 PARTITION OF notifications FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_notifications_user ON notifications(tenant_id, user_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_entity ON notifications(tenant_id, entity_type, entity_id);

-- ── 6.2 comments ──────────────────────────────────────────────────────────
-- Purpose: Threaded comments on contracts, clauses, workflows.
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: Permanent

CREATE TABLE comments (
    comment_id          UUID DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    entity_type         TEXT NOT NULL,               -- 'contract', 'clause', 'workflow', 'finding'
    entity_id           UUID NOT NULL,
    parent_comment_id   UUID,                        -- For threaded replies
    author_id           TEXT NOT NULL,
    body                TEXT NOT NULL,
    mentions            TEXT[] NOT NULL DEFAULT '{}', -- @mentioned user IDs
    is_resolved         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,

    PRIMARY KEY (tenant_id, comment_id)
) PARTITION BY HASH (tenant_id);

CREATE TABLE comments_p0 PARTITION OF comments FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_comments_entity ON comments(tenant_id, entity_type, entity_id, created_at DESC);
CREATE INDEX idx_comments_parent ON comments(parent_comment_id) WHERE parent_comment_id IS NOT NULL;

-- ── Row-Level Security ──────────────────────────────────────────────────────

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_notifications ON notifications
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_comments ON comments
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- =============================================================================
-- 7. AUDIT + SEARCH + COST DOMAIN
-- =============================================================================

-- ── 7.1 audit_logs ─────────────────────────────────────────────────────────
-- Purpose: Immutable audit trail for all compliance-relevant actions.
-- Partitioning: RANGE(created_at), monthly partitions
-- Retention: 7 years (regulatory requirement)
-- IMPORTANT: This is APPEND-ONLY. No UPDATE, no DELETE. Ever.

CREATE TABLE audit_logs (
    audit_id            UUID DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    user_id             TEXT NOT NULL,
    action              TEXT NOT NULL,               -- 'contract.uploaded', 'workflow.approved'
    resource_type       TEXT NOT NULL,               -- 'contract', 'workflow', 'finding'
    resource_id         TEXT NOT NULL,
    details             JSONB NOT NULL DEFAULT '{}',  -- Before/after snapshots, context
    ip_address          TEXT,
    user_agent          TEXT,
    correlation_id      TEXT,                        -- Distributed tracing ID
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Monthly partitions (create in advance, 3 months ahead)
CREATE TABLE audit_logs_2026_06 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE audit_logs_2026_07 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE audit_logs_2026_08 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE audit_logs_2026_09 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;

CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(tenant_id, action, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(tenant_id, resource_type, resource_id, created_at DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(tenant_id, user_id, created_at DESC);

-- ── 7.2 search_queries ─────────────────────────────────────────────────────
-- Purpose: Logs search queries for quality monitoring and future ranking training.
-- Partitioning: RANGE(created_at), monthly partitions
-- Retention: 90 days (aggregated data retained longer)

CREATE TABLE search_queries (
    query_id            UUID DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    user_id             TEXT,
    query_text          TEXT NOT NULL,
    result_count        INTEGER NOT NULL DEFAULT 0,
    latency_ms          INTEGER NOT NULL,
    filters             JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE search_queries_2026_06 PARTITION OF search_queries
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE search_queries_2026_07 PARTITION OF search_queries
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE search_queries_default PARTITION OF search_queries DEFAULT;

CREATE INDEX idx_search_queries_tenant ON search_queries(tenant_id, created_at DESC);
CREATE INDEX idx_search_queries_text ON search_queries USING GIN(to_tsvector('english', query_text));

-- ── 7.3 search_clicks ──────────────────────────────────────────────────────
-- Purpose: Tracks which search results users clicked (for ranking training).
-- Partitioning: RANGE(created_at), monthly partitions
-- Retention: 90 days

CREATE TABLE search_clicks (
    click_id            UUID DEFAULT uuid_generate_v4(),
    query_id            UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    user_id             TEXT,
    result_position     INTEGER NOT NULL,             -- 0-based position in results
    result_entity_type  TEXT NOT NULL,
    result_entity_id    UUID NOT NULL,
    dwell_time_ms       INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, click_id),
    FOREIGN KEY (tenant_id, query_id) REFERENCES search_queries(tenant_id, query_id)
        ON DELETE CASCADE
) PARTITION BY RANGE (created_at);

CREATE TABLE search_clicks_2026_06 PARTITION OF search_clicks
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
-- ... monthly partitions

CREATE INDEX idx_search_clicks_query ON search_clicks(tenant_id, query_id);

-- ── 7.4 ai_cost_ledger ─────────────────────────────────────────────────────
-- Purpose: Tracks every AI API call for cost attribution and optimization.
-- Partitioning: RANGE(created_at), monthly partitions
-- Retention: 12 months (aggregated data retained longer)

CREATE TABLE ai_cost_ledger (
    ledger_id           UUID DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    analysis_id         UUID,
    workflow_type       TEXT NOT NULL,
    provider            TEXT NOT NULL,               -- 'openai', 'anthropic'
    model               TEXT NOT NULL,               -- 'gpt-4o', 'claude-3-sonnet'
    prompt_tokens       INTEGER NOT NULL,
    completion_tokens   INTEGER NOT NULL,
    total_tokens        INTEGER NOT NULL,
    cost_usd            NUMERIC(12,8) NOT NULL,
    latency_ms          INTEGER NOT NULL,
    was_cached          BOOLEAN NOT NULL DEFAULT FALSE,
    had_retry           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE ai_cost_ledger_2026_06 PARTITION OF ai_cost_ledger
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
-- ... monthly partitions

CREATE INDEX idx_ai_cost_tenant ON ai_cost_ledger(tenant_id, created_at DESC);
CREATE INDEX idx_ai_cost_model ON ai_cost_ledger(model, created_at DESC);

-- ── 7.5 ocr_quality_metrics ────────────────────────────────────────────────
-- Purpose: Tracks OCR quality for monitoring and improvement.
-- Partitioning: HASH(tenant_id), 8 partitions
-- Retention: 90 days

CREATE TABLE ocr_quality_metrics (
    metric_id           UUID DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    extraction_method   TEXT NOT NULL,
    overall_score       REAL NOT NULL CHECK (overall_score >= 0 AND overall_score <= 1),
    text_confidence     REAL,
    blank_ratio         REAL,
    garbage_ratio       REAL,
    page_count          INTEGER NOT NULL,
    pages_below_threshold INTEGER NOT NULL DEFAULT 0,
    processing_time_ms  INTEGER NOT NULL,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    had_fallback        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, metric_id),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id)
        ON DELETE CASCADE
) PARTITION BY HASH (tenant_id);

CREATE TABLE ocr_quality_metrics_p0 PARTITION OF ocr_quality_metrics FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... p1 through p7

CREATE INDEX idx_ocr_quality_contract ON ocr_quality_metrics(tenant_id, contract_id);

-- ── Row-Level Security for Audit/Search/Cost Domain ─────────────────────────

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_clicks ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_cost_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_quality_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_search_queries ON search_queries
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_search_clicks ON search_clicks
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_ai_cost ON ai_cost_ledger
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
CREATE POLICY tenant_isolation_ocr_quality ON ocr_quality_metrics
    USING (tenant_id = current_setting('app.tenant_id')::UUID);

-- =============================================================================
-- 8. TRIGGERS + MAINTENANCE
-- =============================================================================

-- ── 8.1 Auto-update updated_at ─────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contracts_updated_at
    BEFORE UPDATE ON contracts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── 8.2 Audit Log Trigger (immutable append-only enforcement) ──────────────

CREATE OR REPLACE FUNCTION prevent_audit_log_mutations()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        RAISE EXCEPTION 'audit_logs is append-only. Mutations are forbidden.';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prevent_audit_log_updates
    BEFORE UPDATE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutations();

CREATE TRIGGER prevent_audit_log_deletes
    BEFORE DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutations();

-- =============================================================================
-- 9. MAINTENANCE JOBS (run via Celery Beat)
-- =============================================================================

-- ── 9.1 VACUUM ANALYZE ─────────────────────────────────────────────────────
-- Run daily during low-traffic period
-- VACUUM ANALYZE contracts;
-- VACUUM ANALYZE chunks;
-- VACUUM ANALYZE audit_logs;

-- ── 9.2 Partition Management ───────────────────────────────────────────────
-- Run monthly: Create next month's partitions
-- Run quarterly: Detach + archive old audit_log partitions (> 7 years)

-- ── 9.3 Reindexing ─────────────────────────────────────────────────────────
-- Run weekly: REINDEX all ivfflat indexes
-- Trigger: When chunk count doubles, rebuild with larger 'lists' parameter

-- ── 9.4 Archival ───────────────────────────────────────────────────────────
-- Run daily:
--   1. Soft-delete completed workflows > 90 days old
--   2. Soft-delete notifications > 90 days old
--   3. Detach audit_log partitions > 7 years old

-- =============================================================================
-- 10. JSONB GOVERNANCE RULES (documentation — not enforceable in SQL)
-- =============================================================================

-- ALLOWED:
--   contracts.metadata        — Extensible tenant-specific fields
--   tenants.settings          — Tenant configuration
--   audit_logs.details        — Variable audit context
--   workflows.metadata        — Workflow-specific configuration
--   document_pages.metadata   — OCR metadata (variable structure)

-- FORBIDDEN:
--   ❌ JSONB for queryable status fields → use TEXT column with CHECK
--   ❌ JSONB for sortable date fields   → use TIMESTAMPTZ column
--   ❌ JSONB for FK targets             → use UUID column with FK constraint
--   ❌ JSONB for frequently updated fields → use dedicated column
--   ❌ JSONB for JOIN conditions        → use dedicated column with index

-- =============================================================================
-- 11. QUERY PATTERNS (reference)
-- =============================================================================

-- ── Hot Query 1: List contracts for tenant (dashboard) ─────────────────────
-- SELECT contract_id, filename, status, contract_type, risk_score, created_at
-- FROM contracts
-- WHERE tenant_id = :tenant_id
--   AND deleted_at IS NULL
-- ORDER BY created_at DESC
-- LIMIT 20 OFFSET 0;
-- → Uses: idx_contracts_created (partial: WHERE deleted_at IS NULL)

-- ── Hot Query 2: Vector search chunks ──────────────────────────────────────
-- SELECT chunk_id, text, 1 - (embedding <=> :query_vector) AS similarity
-- FROM chunks
-- WHERE tenant_id = :tenant_id
--   AND embedding IS NOT NULL
--   AND is_active = TRUE
-- ORDER BY embedding <=> :query_vector
-- LIMIT 20;
-- → Uses: ivfflat index on embedding

-- ── Hot Query 3: BM25 search chunks ────────────────────────────────────────
-- SELECT chunk_id, text, ts_rank(search_vector, query) AS rank
-- FROM chunks
-- WHERE tenant_id = :tenant_id
--   AND search_vector @@ plainto_tsquery('english', :query)
--   AND is_active = TRUE
-- ORDER BY rank DESC
-- LIMIT 20;
-- → Uses: idx_chunks_search (GIN on search_vector)

-- ── Hot Query 4: Active workflows for user ─────────────────────────────────
-- SELECT w.* FROM workflows w
-- WHERE w.tenant_id = :tenant_id
--   AND w.assigned_to = :user_id
--   AND w.status IN ('pending', 'active')
-- ORDER BY w.sla_deadline ASC;
-- → Uses: idx_workflows_assignee (partial: WHERE assigned_to IS NOT NULL)

-- ── Hot Query 5: Audit log for resource ────────────────────────────────────
-- SELECT * FROM audit_logs
-- WHERE tenant_id = :tenant_id
--   AND resource_type = :resource_type
--   AND resource_id = :resource_id
-- ORDER BY created_at DESC
-- LIMIT 50;
-- → Uses: idx_audit_logs_resource

-- =============================================================================
-- 12. BACKUP + RECOVERY
-- =============================================================================

-- Continuous WAL archiving (postgresql.conf):
--   archive_mode = on
--   archive_command = 'aws s3 cp %p s3://contractrisk-backups/wal/%f'

-- Daily pg_dump (cron):
--   pg_dump -Fc -f /backups/contractrisk_$(date +%Y%m%d).dump contract_risk

-- Point-in-Time Recovery:
--   Restore base backup + replay WAL to target time
--   pg_ctl -D /data start
--   Recovery Target Time: '2026-06-15 14:30:00 UTC'

-- Retention:
--   Daily backups: 30 days
--   Weekly backups: 12 months
--   Monthly backups: 7 years
--   WAL files: Until next full backup completes
