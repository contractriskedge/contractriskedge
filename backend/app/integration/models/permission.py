"""ConnectorPermission model — integration-level RBAC and governance."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PermissionAction(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SYNC = "sync"
    ADMIN = "admin"
    APPROVE = "approve"
    DISABLE = "disable"
    MANAGE_CREDENTIALS = "manage_credentials"
    VIEW_AUDIT = "view_audit"


class PermissionEffect(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"


class ConnectorPermission(Base):
    """Fine-grained permissions for connector access and operations."""

    __tablename__ = "connector_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    integration_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action: Mapped[PermissionAction] = mapped_column(
        Enum(
            PermissionAction,
            name="permission_action_enum",
            create_constraint=True,
        ),
        nullable=False,
    )
    effect: Mapped[PermissionEffect] = mapped_column(
        Enum(
            PermissionEffect,
            name="permission_effect_enum",
            create_constraint=True,
        ),
        default=PermissionEffect.ALLOW,
        nullable=False,
    )
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    conditions: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    granted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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

    __table_args__ = (
        Index("ix_connector_permissions_tenant_role", "tenant_id", "role_id"),
        Index("ix_connector_permissions_tenant_user", "tenant_id", "user_id"),
        Index(
            "ix_connector_permissions_integration_action",
            "integration_id",
            "action",
        ),
        UniqueConstraint(
            "tenant_id",
            "role_id",
            "user_id",
            "integration_id",
            "action",
            name="uq_connector_permission",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ConnectorPermission id={self.id} action={self.action} "
            f"effect={self.effect} role={self.role_id} user={self.user_id}>"
        )
