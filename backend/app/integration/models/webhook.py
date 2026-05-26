"""Webhook and webhook event models — replay-safe, idempotent event ingestion."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WebhookStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    EXPIRED = "expired"


class WebhookEventStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"
    IGNORED = "ignored"


class IntegrationWebhook(Base):
    """Webhook subscription configuration for external providers."""

    __tablename__ = "integration_webhooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    webhook_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[WebhookStatus] = mapped_column(
        Enum(WebhookStatus, name="webhook_status_enum", create_constraint=True),
        default=WebhookStatus.ACTIVE,
        nullable=False,
    )

    # Verification
    secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature_header: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    verification_token: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )

    # Configuration
    events_subscribed: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    api_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Security
    allowed_ips: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    require_signature: Mapped[bool] = mapped_column(Boolean, default=True)
    require_https: Mapped[bool] = mapped_column(Boolean, default=True)

    # Lifecycle
    last_event_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    integration = relationship("Integration", back_populates="webhooks")
    events = relationship("WebhookEvent", back_populates="webhook", lazy="selectin")

    __table_args__ = (
        Index("ix_webhooks_tenant_provider", "tenant_id", "provider"),
        UniqueConstraint(
            "integration_id", "webhook_id", name="uq_webhook_integration_id"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<IntegrationWebhook id={self.id} integration={self.integration_id} "
            f"provider={self.provider} status={self.status}>"
        )


class WebhookEvent(Base):
    """Individual webhook event with idempotency and replay protection."""

    __tablename__ = "integration_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integration_webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Idempotency key (prevents duplicate processing)
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)

    # Payload
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    parsed_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    headers: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Processing
    status: Mapped[WebhookEventStatus] = mapped_column(
        Enum(
            WebhookEventStatus,
            name="webhook_event_status_enum",
            create_constraint=True,
        ),
        default=WebhookEventStatus.RECEIVED,
        nullable=False,
    )
    processing_attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Replay protection
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Trace
    correlation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    signature_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    webhook = relationship("IntegrationWebhook", back_populates="events")

    __table_args__ = (
        Index("ix_webhook_events_webhook_status", "webhook_id", "status"),
        Index("ix_webhook_events_tenant_event_type", "tenant_id", "event_type"),
        Index("ix_webhook_events_idempotency", "idempotency_key"),
    )

    def __repr__(self) -> str:
        return (
            f"<WebhookEvent id={self.id} event_type={self.event_type} "
            f"status={self.status} key={self.idempotency_key}>"
        )
