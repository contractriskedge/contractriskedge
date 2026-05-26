"""Initial schema: tenants, users, contracts, ingestion, clauses, chunks, risk, audit.

Revision ID: 001
Revises:
Create Date: 2026-05-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply the initial schema migration.

    Creates all core tables, enums, indexes, and RLS policies.
    """
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"vector\"")

    # Create enum types
    op.execute("CREATE TYPE job_status AS ENUM ('PENDING', 'PROCESSING', 'DONE', 'FAILED')")
    op.execute("CREATE TYPE contract_status AS ENUM ('pending', 'processing', 'ready', 'error', 'archived')")
    op.execute("CREATE TYPE contract_type AS ENUM ('nda', 'service_agreement', 'license', 'employment', 'lease', 'statement_of_work', 'master_service_agreement', 'other')")
    op.execute("CREATE TYPE risk_severity AS ENUM ('critical', 'high', 'medium', 'low', 'info')")
    op.execute("CREATE TYPE extraction_method AS ENUM ('pymupdf', 'tika', 'docx', 'ocr_textract', 'ocr_fallback')")
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'analyst', 'viewer', 'api')")

    # Tenants
    op.create_table(
        "tenants",
        sa.Column("tenant_id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), server_default="starter", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("max_users", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("max_documents", sa.Integer(), server_default=sa.text("1000"), nullable=False),
        sa.Column("features", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id"),
    )
    op.create_index("idx_tenants_domain", "tenants", ["domain"], postgresql_where=sa.text("domain IS NOT NULL"))

    # Users
    op.create_table(
        "users",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text(), server_default="viewer", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("permissions", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("idx_users_tenant", "users", ["tenant_id"])
    op.create_index("idx_users_email", "users", ["email"])
    op.create_unique_constraint("idx_users_tenant_email", "users", ["tenant_id", "email"])
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")

    # Contracts (partitioned)
    op.execute("""
        CREATE TABLE contracts (
            contract_id UUID DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            content_type TEXT NOT NULL,
            file_size BIGINT NOT NULL DEFAULT 0,
            file_path TEXT,
            checksum TEXT,
            status contract_status NOT NULL DEFAULT 'pending',
            contract_type contract_type,
            version INTEGER NOT NULL DEFAULT 1,
            total_pages INTEGER NOT NULL DEFAULT 0,
            total_clauses INTEGER NOT NULL DEFAULT 0,
            total_chunks INTEGER NOT NULL DEFAULT 0,
            tags TEXT[] NOT NULL DEFAULT '{}',
            metadata JSONB NOT NULL DEFAULT '{}',
            search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(filename, ''))) STORED,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            archived_at TIMESTAMPTZ,
            PRIMARY KEY (contract_id, tenant_id)
        ) PARTITION BY HASH (tenant_id)
    """)
    for i in range(4):
        op.execute(f"CREATE TABLE contracts_p{i} PARTITION OF contracts FOR VALUES WITH (MODULUS 4, REMAINDER {i})")
    op.create_index("idx_contracts_tenant", "contracts", ["tenant_id"])
    op.create_index("idx_contracts_status", "contracts", ["status"])
    op.create_index("idx_contracts_user", "contracts", ["user_id"])
    op.create_index("idx_contracts_type", "contracts", ["contract_type"])
    op.create_index("idx_contracts_created", "contracts", [sa.text("created_at DESC")])
    op.create_index("idx_contracts_tags", "contracts", ["tags"], postgresql_using="gin")
    op.create_index("idx_contracts_search", "contracts", ["search_vector"], postgresql_using="gin")
    op.execute("ALTER TABLE contracts ENABLE ROW LEVEL SECURITY")

    # Ingestion Jobs
    op.create_table(
        "ingestion_jobs",
        sa.Column("job_id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="PENDING", nullable=False),
        sa.Column("progress", sa.REAL(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("extraction_results", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["contracts.contract_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("idx_ingestion_jobs_tenant", "ingestion_jobs", ["tenant_id"])
    op.create_index("idx_ingestion_jobs_status", "ingestion_jobs", ["status"])
    op.create_index("idx_ingestion_jobs_document", "ingestion_jobs", ["document_id"])
    op.execute("ALTER TABLE ingestion_jobs ENABLE ROW LEVEL SECURITY")

    # Extracted Pages
    op.create_table(
        "extracted_pages",
        sa.Column("page_id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("contract_id", sa.UUID(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("confidence", sa.REAL(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(),
                  sa.Computed("to_tsvector('english', coalesce(text, ''))", persisted=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.contract_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("page_id"),
        sa.UniqueConstraint("contract_id", "page_number"),
    )
    op.create_index("idx_extracted_pages_contract", "extracted_pages", ["contract_id"])
    op.create_index("idx_extracted_pages_search", "extracted_pages", ["search_vector"], postgresql_using="gin")
    op.execute("ALTER TABLE extracted_pages ENABLE ROW LEVEL SECURITY")

    # Clauses
    op.create_table(
        "clauses",
        sa.Column("clause_id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("contract_id", sa.UUID(), nullable=False),
        sa.Column("page_id", sa.UUID(), nullable=True),
        sa.Column("clause_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("section_number", sa.Text(), nullable=True),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("clause_type", sa.Text(), nullable=True),
        sa.Column("level", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("parent_clause_id", sa.UUID(), nullable=True),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.REAL(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.contract_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["extracted_pages.page_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_clause_id"], ["clauses.clause_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("clause_id"),
    )
    op.create_index("idx_clauses_contract", "clauses", ["contract_id"])
    op.create_index("idx_clauses_type", "clauses", ["clause_type"])
    op.create_index("idx_clauses_parent", "clauses", ["parent_clause_id"])
    op.execute("ALTER TABLE clauses ENABLE ROW LEVEL SECURITY")

    # Chunks with pgvector
    op.execute("""
        CREATE TABLE chunks (
            chunk_id UUID DEFAULT uuid_generate_v4(),
            contract_id UUID NOT NULL REFERENCES contracts(contract_id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            token_count INTEGER NOT NULL CHECK (token_count >= 1),
            embedding vector(1536),
            clause_ids UUID[] NOT NULL DEFAULT '{}',
            page_numbers INTEGER[] NOT NULL DEFAULT '{}',
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (chunk_id)
        )
    """)
    op.create_index("idx_chunks_contract", "chunks", ["contract_id"])
    op.execute("CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    op.execute("ALTER TABLE chunks ENABLE ROW LEVEL SECURITY")

    # Risk Reports
    op.create_table(
        "risk_reports",
        sa.Column("report_id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("contract_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("overall_score", sa.REAL(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("categories_analyzed", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.contract_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("report_id"),
    )
    op.create_index("idx_risk_reports_contract", "risk_reports", ["contract_id"])
    op.create_index("idx_risk_reports_tenant", "risk_reports", ["tenant_id"])
    op.execute("ALTER TABLE risk_reports ENABLE ROW LEVEL SECURITY")

    # Risk Findings
    op.create_table(
        "risk_findings",
        sa.Column("finding_id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("clause_reference", sa.Text(), nullable=True),
        sa.Column("clause_text", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("score", sa.REAL(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["risk_reports.report_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("finding_id"),
    )
    op.create_index("idx_risk_findings_report", "risk_findings", ["report_id"])
    op.create_index("idx_risk_findings_severity", "risk_findings", ["severity"])
    op.execute("ALTER TABLE risk_findings ENABLE ROW LEVEL SECURITY")

    # Redline Comparisons
    op.create_table(
        "redline_comparisons",
        sa.Column("comparison_id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("source_contract_id", sa.UUID(), nullable=False),
        sa.Column("target_contract_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("diff_text", sa.Text(), nullable=True),
        sa.Column("summary", postgresql.JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("changes", postgresql.JSONB(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["source_contract_id"], ["contracts.contract_id"]),
        sa.ForeignKeyConstraint(["target_contract_id"], ["contracts.contract_id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("comparison_id"),
    )
    op.create_index("idx_redline_source", "redline_comparisons", ["source_contract_id"])
    op.create_index("idx_redline_target", "redline_comparisons", ["target_contract_id"])
    op.create_index("idx_redline_tenant", "redline_comparisons", ["tenant_id"])
    op.execute("ALTER TABLE redline_comparisons ENABLE ROW LEVEL SECURITY")

    # Webhook Registrations
    op.create_table(
        "webhook_registrations",
        sa.Column("webhook_id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("events", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{ingestion.completed,ingestion.failed}'"), nullable=False),
        sa.Column("secret_hash", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("webhook_id"),
    )
    op.create_index("idx_webhooks_tenant", "webhook_registrations", ["tenant_id"])
    op.execute("ALTER TABLE webhook_registrations ENABLE ROW LEVEL SECURITY")

    # Audit Logs (partitioned by month)
    op.execute("""
        CREATE TABLE audit_logs (
            audit_id UUID DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            ip_address TEXT,
            details JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (audit_id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)
    for month in range(1, 7):
        month_str = f"2026-{month:02d}"
        next_month = f"2026-{month + 1:02d}" if month < 12 else "2027-01"
        op.execute(
            f"CREATE TABLE audit_logs_{month_str.replace('-', '_')} PARTITION OF audit_logs "
            f"FOR VALUES FROM ('{month_str}-01') TO ('{next_month}-01')"
        )
    op.execute("CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT")
    op.create_index("idx_audit_logs_tenant", "audit_logs", ["tenant_id"])
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])
    op.create_index("idx_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("idx_audit_logs_user", "audit_logs", ["user_id"])
    op.create_index("idx_audit_logs_created", "audit_logs", [sa.text("created_at DESC")])
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")

    # RLS helper function and policies
    op.execute("""
        CREATE OR REPLACE FUNCTION get_current_tenant_id()
        RETURNS UUID LANGUAGE plpgsql STABLE AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.tenant_id', TRUE), '')::UUID;
        END;
        $$
    """)

    # Apply RLS policies
    for table in ["users", "contracts", "ingestion_jobs", "extracted_pages",
                   "clauses", "chunks", "risk_reports", "risk_findings",
                   "redline_comparisons", "webhook_registrations", "audit_logs"]:
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING (tenant_id = get_current_tenant_id())")

    # Updated_at triggers
    for table in ["tenants", "users", "contracts", "webhook_registrations"]:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """)


def downgrade() -> None:
    """Revert the initial schema migration."""
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS webhook_registrations CASCADE")
    op.execute("DROP TABLE IF EXISTS redline_comparisons CASCADE")
    op.execute("DROP TABLE IF EXISTS risk_findings CASCADE")
    op.execute("DROP TABLE IF EXISTS risk_reports CASCADE")
    op.execute("DROP TABLE IF EXISTS chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS clauses CASCADE")
    op.execute("DROP TABLE IF EXISTS extracted_pages CASCADE")
    op.execute("DROP TABLE IF EXISTS ingestion_jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS contracts CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
    op.execute("DROP TABLE IF EXISTS tenants CASCADE")

    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS extraction_method")
    op.execute("DROP TYPE IF EXISTS risk_severity")
    op.execute("DROP TYPE IF EXISTS contract_type")
    op.execute("DROP TYPE IF EXISTS contract_status")
    op.execute("DROP TYPE IF EXISTS job_status")

    op.execute("DROP FUNCTION IF EXISTS get_current_tenant_id()")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
