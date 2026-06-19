"""SQLAlchemy Table definition for redline_templates.

Used instead of a full ORM model to avoid ``extend_existing`` conflicts
with the shared ``Base`` metadata. The table is created by Alembic
migration ``34fb461caf36_add_redline_templates_table.py``.
"""

from sqlalchemy import Table, Column, Text, Integer, Float, DateTime, ForeignKey, Index, MetaData
from sqlalchemy.dialects.postgresql import UUID, JSONB

metadata = MetaData()

redline_templates_table = Table(
    "redline_templates",
    metadata,
    Column("template_id", UUID(as_uuid=True), primary_key=True),
    Column("tenant_id", UUID(as_uuid=True), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False),
    Column("name", Text, nullable=False),
    Column("clause_type", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("jurisdiction", Text, nullable=True),
    Column("industry", Text, nullable=True),
    Column("language", Text, nullable=False),
    Column("risk_level", Text, nullable=True),
    Column("template_text", Text, nullable=False),
    Column("variables", JSONB, nullable=True),
    Column("version", Integer, nullable=False),
    Column("status", Text, nullable=False),
    Column("playbook_id", UUID(as_uuid=True), ForeignKey("clause_standards.clause_id", ondelete="SET NULL"), nullable=True),
    Column("usage_count", Integer, nullable=False),
    Column("accept_rate", Float, nullable=False),
    Column("created_by", Text, nullable=True),
    Column("approved_by", Text, nullable=True),
    Column("effective_date", DateTime(timezone=True), nullable=True),
    Column("retired_date", DateTime(timezone=True), nullable=True),
    Column("last_used", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    extend_existing=True,
)

Index("ix_redline_templates_tenant_id", redline_templates_table.c.tenant_id)
Index("ix_redline_templates_clause_type", redline_templates_table.c.clause_type)
Index("ix_redline_templates_playbook_id", redline_templates_table.c.playbook_id)
