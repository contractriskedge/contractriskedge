"""add_obligation_management_tables

Revision ID: d7e8f9a0b1c2
Revises: c1a2b3c4d5e6
Create Date: 2026-05-28 12:00:00.000000

Creates obligation management domain tables:
- obligations — Core obligation records with risk scoring, AI predictions, and metadata
- obligation_instances — Recurring or multi-instance obligation tracking
- obligation_reminders — Reminder scheduling per obligation
- obligation_escalations — Escalation tracking for overdue or at-risk obligations
- obligation_evidence — Supporting evidence files per obligation
- sla_metrics — SLA performance tracking per vendor/contract
- vendor_performance — Vendor performance scoring and risk assessment
- financial_exposure — Financial exposure aggregation by category
- obligation_audit_log — Audit trail for obligation lifecycle events
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "c1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Obligations ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS obligations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(tenant_id),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            obligation_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            contract_id VARCHAR(255),
            contract_name VARCHAR(255),
            vendor VARCHAR(255),
            owner VARCHAR(255),
            assignee VARCHAR(255),
            due_date TIMESTAMP WITH TIME ZONE,
            completed_date TIMESTAMP WITH TIME ZONE,
            risk_score DOUBLE PRECISION DEFAULT 0,
            risk_level VARCHAR(20) DEFAULT 'medium',
            sla_status VARCHAR(50) DEFAULT 'on_track',
            sla_remaining_hours DOUBLE PRECISION DEFAULT 0,
            financial_impact DOUBLE PRECISION DEFAULT 0,
            currency VARCHAR(10) DEFAULT 'USD',
            escalation_level INTEGER DEFAULT 0,
            ai_risk_prediction DOUBLE PRECISION DEFAULT 0,
            ai_confidence DOUBLE PRECISION DEFAULT 0,
            clause_reference VARCHAR(255),
            department VARCHAR(255),
            business_unit VARCHAR(255),
            geography VARCHAR(255),
            is_recurring BOOLEAN DEFAULT FALSE,
            recurrence_pattern VARCHAR(50),
            recurrence_next_date TIMESTAMP WITH TIME ZONE,
            attachments_count INTEGER DEFAULT 0,
            reminders_count INTEGER DEFAULT 0,
            notes TEXT,
            is_favorite BOOLEAN DEFAULT FALSE,
            tags TEXT[] DEFAULT '{}',
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligations_tenant_id ON obligations (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligations_status ON obligations (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligations_obligation_type ON obligations (obligation_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligations_vendor ON obligations (vendor);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligations_due_date ON obligations (due_date);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligations_risk_level ON obligations (risk_level);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligations_sla_status ON obligations (sla_status);")

    # ── Obligation Instances ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS obligation_instances (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(tenant_id),
            obligation_id UUID NOT NULL REFERENCES obligations(id) ON DELETE CASCADE,
            instance_date TIMESTAMP WITH TIME ZONE,
            due_date TIMESTAMP WITH TIME ZONE,
            completed_date TIMESTAMP WITH TIME ZONE,
            status VARCHAR(50),
            financial_impact DOUBLE PRECISION DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_instances_tenant_id ON obligation_instances (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_instances_obligation_id ON obligation_instances (obligation_id);")

    # ── Obligation Reminders ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS obligation_reminders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(tenant_id),
            obligation_id UUID NOT NULL REFERENCES obligations(id) ON DELETE CASCADE,
            reminder_type VARCHAR(50) NOT NULL,
            remind_at TIMESTAMP WITH TIME ZONE NOT NULL,
            sent_at TIMESTAMP WITH TIME ZONE,
            message TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_reminders_tenant_id ON obligation_reminders (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_reminders_obligation_id ON obligation_reminders (obligation_id);")

    # ── Obligation Escalations ───────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS obligation_escalations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(tenant_id),
            obligation_id UUID NOT NULL REFERENCES obligations(id) ON DELETE CASCADE,
            escalation_level INTEGER NOT NULL,
            escalated_to VARCHAR(255) NOT NULL,
            reason TEXT,
            status VARCHAR(20) DEFAULT 'active',
            resolved_at TIMESTAMP WITH TIME ZONE,
            resolution_notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_escalations_tenant_id ON obligation_escalations (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_escalations_obligation_id ON obligation_escalations (obligation_id);")

    # ── Obligation Evidence ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS obligation_evidence (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(tenant_id),
            obligation_id UUID NOT NULL REFERENCES obligations(id) ON DELETE CASCADE,
            instance_id UUID REFERENCES obligation_instances(id) ON DELETE CASCADE,
            file_name VARCHAR(255) NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            file_url TEXT,
            uploaded_by VARCHAR(255),
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_evidence_tenant_id ON obligation_evidence (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_evidence_obligation_id ON obligation_evidence (obligation_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_evidence_instance_id ON obligation_evidence (instance_id);")

    # ── SLA Metrics ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS sla_metrics (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(tenant_id),
            obligation_id UUID REFERENCES obligations(id) ON DELETE CASCADE,
            vendor VARCHAR(255) NOT NULL,
            contract_type VARCHAR(255),
            sla_target VARCHAR(50) NOT NULL,
            performance DOUBLE PRECISION NOT NULL,
            trend DOUBLE PRECISION DEFAULT 0,
            breach_count INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'on_track',
            measured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_sla_metrics_tenant_id ON sla_metrics (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sla_metrics_obligation_id ON sla_metrics (obligation_id);")

    # ── Vendor Performance ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS vendor_performance (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(tenant_id),
            vendor VARCHAR(255) NOT NULL,
            category VARCHAR(50) NOT NULL,
            score DOUBLE PRECISION NOT NULL,
            trend DOUBLE PRECISION DEFAULT 0,
            contract_count INTEGER DEFAULT 0,
            breach_count INTEGER DEFAULT 0,
            risk_level VARCHAR(20) NOT NULL,
            predicted_risk DOUBLE PRECISION DEFAULT 0,
            last_assessed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_vendor_performance_tenant_id ON vendor_performance (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vendor_performance_vendor ON vendor_performance (vendor);")

    # ── Financial Exposure ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS financial_exposure (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(tenant_id),
            category VARCHAR(50) NOT NULL,
            total_exposure DOUBLE PRECISION DEFAULT 0,
            overdue_amount DOUBLE PRECISION DEFAULT 0,
            at_risk_amount DOUBLE PRECISION DEFAULT 0,
            recovered_amount DOUBLE PRECISION DEFAULT 0,
            trend DOUBLE PRECISION DEFAULT 0,
            currency VARCHAR(10) DEFAULT 'USD',
            as_of_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_financial_exposure_tenant_id ON financial_exposure (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_financial_exposure_category ON financial_exposure (category);")

    # ── Obligation Audit Log ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS obligation_audit_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(tenant_id),
            obligation_id UUID NOT NULL REFERENCES obligations(id) ON DELETE CASCADE,
            action VARCHAR(100) NOT NULL,
            actor VARCHAR(255),
            changes JSONB,
            comment TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_audit_log_tenant_id ON obligation_audit_log (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_obligation_audit_log_obligation_id ON obligation_audit_log (obligation_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS obligation_audit_log CASCADE;")
    op.execute("DROP TABLE IF EXISTS financial_exposure CASCADE;")
    op.execute("DROP TABLE IF EXISTS vendor_performance CASCADE;")
    op.execute("DROP TABLE IF EXISTS sla_metrics CASCADE;")
    op.execute("DROP TABLE IF EXISTS obligation_evidence CASCADE;")
    op.execute("DROP TABLE IF EXISTS obligation_escalations CASCADE;")
    op.execute("DROP TABLE IF EXISTS obligation_reminders CASCADE;")
    op.execute("DROP TABLE IF EXISTS obligation_instances CASCADE;")
    op.execute("DROP TABLE IF EXISTS obligations CASCADE;")
