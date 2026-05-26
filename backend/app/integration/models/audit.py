"""IntegrationAuditEvent model — full audit lineage for integration operations."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class IntegrationAuditEvent(Base):
    """Immutable audit trail for all integration lifecycle operations."""

    __tablename__ = "integration_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor_type: Mapped[str] = mapped_column(
        String(50), default="user", nullable=False
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Change details
    previous_state: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    new_state: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Context
    correlation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Outcome
    success: Mapped[Optional[bool]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    integration = relationship("Integration", back_populates="audit_events")

    __table_args__ = (
        Index("ix_audit_events_tenant_action", "tenant_id", "action"),
        Index("ix_audit_events_tenant_timestamp", "tenant_id", "occurred_at"),
        Index("ix_audit_events_integration", "integration_id"),
        Index("ix_audit_events_correlation", "correlation_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<IntegrationAuditEvent id={self.id} "
            f"action={self.action} resource={self.resource_type}>"
        )
