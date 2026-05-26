"""Integration model — core entity for connector lifecycle management."""

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
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class IntegrationStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"
    ERROR = "error"
    PENDING_APPROVAL = "pending_approval"


class IntegrationType(str, enum.Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    BASIC_AUTH = "basic_auth"


class ConnectorProvider(str, enum.Enum):
    DOCUSIGN = "docusign"
    SHAREPOINT = "sharepoint"
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    SLACK = "slack"
    TEAMS = "teams"
    JIRA = "jira"
    SERVICENOW = "servicenow"
    SALESFORCE = "salesforce"
    SAP_ARiBA = "sap_ariba"


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[ConnectorProvider] = mapped_column(
        Enum(ConnectorProvider, name="connector_provider_enum", create_constraint=True),
        nullable=False,
    )
    integration_type: Mapped[IntegrationType] = mapped_column(
        Enum(IntegrationType, name="integration_type_enum", create_constraint=True),
        nullable=False,
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, name="integration_status_enum", create_constraint=True),
        default=IntegrationStatus.PENDING,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )
    scopes: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rate_limit_max: Mapped[Optional[int]] = mapped_column(nullable=True)
    rate_limit_window_seconds: Mapped[Optional[int]] = mapped_column(nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_sync_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    disabled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disabled_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
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

    # relationships
    credentials = relationship(
        "IntegrationCredential", back_populates="integration", lazy="selectin"
    )
    sync_jobs = relationship(
        "IntegrationSyncJob", back_populates="integration", lazy="selectin"
    )
    webhooks = relationship(
        "IntegrationWebhook", back_populates="integration", lazy="selectin"
    )
    audit_events = relationship(
        "IntegrationAuditEvent", back_populates="integration", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_integrations_tenant_provider", "tenant_id", "provider"),
        Index("ix_integrations_tenant_status", "tenant_id", "status"),
        Index("ix_integrations_tenant_active", "tenant_id", "is_deleted"),
    )

    def __repr__(self) -> str:
        return (
            f"<Integration id={self.id} tenant={self.tenant_id} "
            f"provider={self.provider} status={self.status}>"
        )
