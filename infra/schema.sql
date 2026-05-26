-- =============================================================================
-- AI Contract Risk Analyzer - PostgreSQL Schema
-- =============================================================================
-- This schema defines the complete database structure including:
--   - Multi-tenant data isolation via Row-Level Security (RLS)
--   - pgvector extension for embedding similarity search
--   - Table partitioning for audit logs
--   - Comprehensive indexing strategy
-- =============================================================================

-- ── Extensions ──────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ── ENUM Types ──────────────────────────────────────────────────────────────

CREATE TYPE job_status AS ENUM ('PENDING', 'PROCESSING', 'DONE', 'FAILED');
CREATE TYPE contract_status AS ENUM ('pending', 'processing', 'ready', 'error', 'archived');
CREATE TYPE contract_type AS ENUM ('nda', 'service_agreement', 'license', 'employment', 'lease', 'statement_of_work', 'master_service_agreement', 'other');
CREATE TYPE risk_severity AS ENUM ('critical', 'high', 'medium', 'low', 'info');
CREATE TYPE extraction_method AS ENUM ('pymupdf', 'tika', 'docx', 'ocr_textract', 'ocr_fallback');
CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'viewer', 'api');

-- ── Tenants (Multi-tenant root) ─────────────────────────────────────────────

CREATE TABLE tenants (
    tenant_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name           TEXT NOT NULL,
    domain         TEXT,
    plan           TEXT NOT NULL DEFAULT 'starter',
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    max_users      INTEGER NOT NULL DEFAULT 10,
    max_documents  INTEGER NOT NULL DEFAULT 1000,
    features       TEXT[] NOT NULL DEFAULT '{}',
    settings       JSONB NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_domain ON tenants(domain) WHERE domain IS NOT NULL;

-- ── Users ───────────────────────────────────────────────────────────────────

CREATE TABLE users (
    user_id        TEXT PRIMARY KEY,  -- Auth0 'sub' claim
    email          TEXT NOT NULL,
    name           TEXT,
    tenant_id      UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    role           user_role NOT NULL DEFAULT 'viewer',
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    permissions    TEXT[] NOT NULL DEFAULT '{}',
    metadata       JSONB NOT NULL DEFAULT '{}',
    last_login     TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_users_tenant_email ON users(tenant_id, email);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- ── Documents / Contracts ───────────────────────────────────────────────────

CREATE TABLE contracts (
    contract_id    UUID DEFAULT uuid_generate_v4(),
    tenant_id      UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id        TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    filename       TEXT NOT NULL,
    content_type   TEXT NOT NULL,
    file_size      BIGINT NOT NULL DEFAULT 0,
    file_path      TEXT,
    checksum       TEXT,
    status         contract_status NOT NULL DEFAULT 'pending',
    contract_type  contract_type,
    version        INTEGER NOT NULL DEFAULT 1,
    total_pages    INTEGER NOT NULL DEFAULT 0,
    total_clauses  INTEGER NOT NULL DEFAULT 0,
    total_chunks   INTEGER NOT NULL DEFAULT 0,
    tags           TEXT[] NOT NULL DEFAULT '{}',
    metadata       JSONB NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at    TIMESTAMPTZ,
    PRIMARY KEY (tenant_id, contract_id)
) PARTITION BY HASH (tenant_id);

-- Create initial partitions
CREATE TABLE contracts_p0 PARTITION OF contracts FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE contracts_p1 PARTITION OF contracts FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE contracts_p2 PARTITION OF contracts FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE contracts_p3 PARTITION OF contracts FOR VALUES WITH (MODULUS 4, REMAINDER 3);

CREATE INDEX idx_contracts_tenant ON contracts(tenant_id);
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_user ON contracts(user_id);
CREATE INDEX idx_contracts_type ON contracts(contract_type);
CREATE INDEX idx_contracts_created ON contracts(created_at DESC);
CREATE INDEX idx_contracts_tags ON contracts USING GIN(tags);

ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;

-- ── Ingestion Jobs ──────────────────────────────────────────────────────────

CREATE TABLE ingestion_jobs (
    job_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id      UUID NOT NULL,
    tenant_id        UUID NOT NULL REFERENCES tenants(tenant_id),
    user_id          TEXT NOT NULL REFERENCES users(user_id),
    filename         TEXT NOT NULL,
    content_type     TEXT NOT NULL,
    status           job_status NOT NULL DEFAULT 'PENDING',
    progress         REAL NOT NULL DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 100.0),
    error_message    TEXT,
    retry_count      INTEGER NOT NULL DEFAULT 0,
    extraction_results JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ,
    FOREIGN KEY (tenant_id, document_id) REFERENCES contracts(tenant_id, contract_id) ON DELETE CASCADE
);

CREATE INDEX idx_ingestion_jobs_tenant ON ingestion_jobs(tenant_id);
CREATE INDEX idx_ingestion_jobs_status ON ingestion_jobs(status);
CREATE INDEX idx_ingestion_jobs_document ON ingestion_jobs(document_id);

ALTER TABLE ingestion_jobs ENABLE ROW LEVEL SECURITY;

-- ── Extracted Pages ─────────────────────────────────────────────────────────

CREATE TABLE extracted_pages (
    page_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id    UUID NOT NULL,
    tenant_id      UUID NOT NULL,
    page_number    INTEGER NOT NULL CHECK (page_number >= 1),
    text           TEXT NOT NULL,
    method         extraction_method NOT NULL,
    confidence     REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    metadata       JSONB NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(contract_id, page_number),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id) ON DELETE CASCADE
);

CREATE INDEX idx_extracted_pages_contract ON extracted_pages(contract_id);
CREATE INDEX idx_extracted_pages_tenant ON extracted_pages(tenant_id);

ALTER TABLE extracted_pages ENABLE ROW LEVEL SECURITY;

-- ── Clause Segments ─────────────────────────────────────────────────────────

CREATE TABLE clauses (
    clause_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id      UUID NOT NULL,
    tenant_id        UUID NOT NULL,
    page_id          UUID REFERENCES extracted_pages(page_id),
    clause_index     INTEGER NOT NULL,
    text             TEXT NOT NULL,
    section_number   TEXT,
    heading          TEXT,
    clause_type      TEXT,
    level            INTEGER NOT NULL DEFAULT 1,
    parent_clause_id UUID REFERENCES clauses(clause_id),
    start_char       INTEGER NOT NULL CHECK (start_char >= 0),
    end_char         INTEGER NOT NULL CHECK (end_char > start_char),
    confidence       REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id) ON DELETE CASCADE
);

CREATE INDEX idx_clauses_contract ON clauses(contract_id);
CREATE INDEX idx_clauses_type ON clauses(clause_type);
CREATE INDEX idx_clauses_parent ON clauses(parent_clause_id);

ALTER TABLE clauses ENABLE ROW LEVEL SECURITY;

-- ── Semantic Chunks (with pgvector embeddings) ──────────────────────────────

CREATE TABLE chunks (
    chunk_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id    UUID NOT NULL,
    tenant_id      UUID NOT NULL,
    chunk_index    INTEGER NOT NULL,
    text           TEXT NOT NULL,
    token_count    INTEGER NOT NULL CHECK (token_count >= 1),
    embedding      vector(1536),  -- OpenAI ada-002 embedding dimension
    clause_ids     UUID[] NOT NULL DEFAULT '{}',
    page_numbers   INTEGER[] NOT NULL DEFAULT '{}',
    metadata       JSONB NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id) ON DELETE CASCADE
);

CREATE INDEX idx_chunks_contract ON chunks(contract_id);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

-- ── Risk Reports ────────────────────────────────────────────────────────────

CREATE TABLE risk_reports (
    report_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id      UUID NOT NULL,
    tenant_id        UUID NOT NULL REFERENCES tenants(tenant_id),
    user_id          TEXT NOT NULL REFERENCES users(user_id),
    status           TEXT NOT NULL DEFAULT 'pending',
    overall_score    REAL CHECK (overall_score >= 0.0 AND overall_score <= 1.0),
    summary          TEXT,
    categories_analyzed TEXT[] NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ,
    FOREIGN KEY (tenant_id, contract_id) REFERENCES contracts(tenant_id, contract_id) ON DELETE CASCADE
);

CREATE INDEX idx_risk_reports_contract ON risk_reports(contract_id);
CREATE INDEX idx_risk_reports_tenant ON risk_reports(tenant_id);

ALTER TABLE risk_reports ENABLE ROW LEVEL SECURITY;

-- ── Risk Findings ───────────────────────────────────────────────────────────

CREATE TABLE risk_findings (
    finding_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id        UUID NOT NULL REFERENCES risk_reports(report_id) ON DELETE CASCADE,
    category         TEXT NOT NULL,
    severity         risk_severity NOT NULL,
    title            TEXT NOT NULL,
    description      TEXT NOT NULL,
    clause_reference TEXT,
    clause_text      TEXT,
    recommendation   TEXT,
    score            REAL NOT NULL DEFAULT 0.0 CHECK (score >= 0.0 AND score <= 1.0),
    metadata         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_risk_findings_report ON risk_findings(report_id);
CREATE INDEX idx_risk_findings_severity ON risk_findings(severity);

ALTER TABLE risk_findings ENABLE ROW LEVEL SECURITY;

-- ── Redline Comparisons ─────────────────────────────────────────────────────

CREATE TABLE redline_comparisons (
    comparison_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_contract_id  UUID NOT NULL,
    target_contract_id  UUID NOT NULL,
    tenant_id           UUID NOT NULL REFERENCES tenants(tenant_id),
    user_id             TEXT NOT NULL REFERENCES users(user_id),
    diff_text           TEXT,
    summary             JSONB NOT NULL DEFAULT '{}',
    changes             JSONB NOT NULL DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (tenant_id, source_contract_id) REFERENCES contracts(tenant_id, contract_id),
    FOREIGN KEY (tenant_id, target_contract_id) REFERENCES contracts(tenant_id, contract_id)
);

CREATE INDEX idx_redline_source ON redline_comparisons(source_contract_id);
CREATE INDEX idx_redline_target ON redline_comparisons(target_contract_id);
CREATE INDEX idx_redline_tenant ON redline_comparisons(tenant_id);

ALTER TABLE redline_comparisons ENABLE ROW LEVEL SECURITY;

-- ── Webhook Registrations ───────────────────────────────────────────────────

CREATE TABLE webhook_registrations (
    webhook_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    user_id       TEXT NOT NULL REFERENCES users(user_id),
    url           TEXT NOT NULL,
    events        TEXT[] NOT NULL DEFAULT '{ingestion.completed,ingestion.failed}',
    secret_hash   TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    description   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_webhooks_tenant ON webhook_registrations(tenant_id);

ALTER TABLE webhook_registrations ENABLE ROW LEVEL SECURITY;

-- ── Audit Logs (time-partitioned) ───────────────────────────────────────────

CREATE TABLE audit_logs (
    audit_id      UUID NOT NULL DEFAULT uuid_generate_v4(),
    tenant_id     UUID NOT NULL REFERENCES tenants(tenant_id),
    user_id       TEXT NOT NULL,
    action        TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id   TEXT NOT NULL,
    ip_address    TEXT,
    details       JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create monthly partitions for audit logs
CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE audit_logs_2026_02 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE audit_logs_2026_03 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE audit_logs_2026_04 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE audit_logs_2026_06 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;

CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- ── Row-Level Security Policies ─────────────────────────────────────────────

-- Tenant isolation: users can only see their own tenant's data
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    -- In production, this reads from the session/request context
    -- set by the application middleware
    RETURN NULLIF(current_setting('app.tenant_id', TRUE), '')::UUID;
END;
$$;

-- Apply RLS policies for each table
CREATE POLICY tenant_isolation ON users
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation ON contracts
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation ON ingestion_jobs
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation ON extracted_pages
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation ON clauses
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation ON chunks
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation ON risk_reports
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation ON risk_findings
    USING (report_id IN (SELECT report_id FROM risk_reports WHERE tenant_id = get_current_tenant_id()));

CREATE POLICY tenant_isolation ON redline_comparisons
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation ON webhook_registrations
    USING (tenant_id = get_current_tenant_id());

CREATE POLICY tenant_isolation ON audit_logs
    USING (tenant_id = get_current_tenant_id());

-- ── Full-Text Search ────────────────────────────────────────────────────────

ALTER TABLE contracts ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(filename, ''))) STORED;

CREATE INDEX idx_contracts_search ON contracts USING GIN(search_vector);

ALTER TABLE extracted_pages ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(text, ''))) STORED;

CREATE INDEX idx_extracted_pages_search ON extracted_pages USING GIN(search_vector);
CREATE INDEX idx_extracted_pages_tenant_search ON extracted_pages(tenant_id);

-- ── Trigger Functions ───────────────────────────────────────────────────────

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

CREATE TRIGGER update_webhooks_updated_at
    BEFORE UPDATE ON webhook_registrations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── Contract Relationships (Sprint 10 - V2-009) ────────────────────────────

CREATE TYPE relationship_type AS ENUM ('parent', 'child', 'amendment', 'addendum', 'dpa');

CREATE TABLE contract_relationships (
    relationship_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_contract_id   UUID NOT NULL,
    child_contract_id    UUID NOT NULL,
    relationship_type    relationship_type NOT NULL,
    effective_date       DATE,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (parent_contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE,
    FOREIGN KEY (child_contract_id) REFERENCES contracts(contract_id) ON DELETE CASCADE
);

CREATE INDEX idx_contract_rel_parent ON contract_relationships(parent_contract_id);
CREATE INDEX idx_contract_rel_child ON contract_relationships(child_contract_id);
CREATE INDEX idx_contract_rel_type ON contract_relationships(relationship_type);

ALTER TABLE contract_relationships ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON contract_relationships
    USING (
        parent_contract_id IN (SELECT contract_id FROM contracts WHERE tenant_id = get_current_tenant_id())
        AND child_contract_id IN (SELECT contract_id FROM contracts WHERE tenant_id = get_current_tenant_id())
    );

-- Add risk_score column to contracts for exposure propagation
ALTER TABLE contracts ADD COLUMN IF NOT EXISTS risk_score REAL CHECK (risk_score >= 0.0 AND risk_score <= 1.0);
CREATE INDEX IF NOT EXISTS idx_contracts_risk_score ON contracts(risk_score);
