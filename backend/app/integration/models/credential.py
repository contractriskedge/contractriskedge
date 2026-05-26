"""IntegrationCredential model — encrypted credential storage with OAuth metadata."""

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


class CredentialType(str, enum.Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
    CUSTOM = "custom"


class IntegrationCredential(Base):
    __tablename__ = "integration_credentials"

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
    credential_type: Mapped[CredentialType] = mapped_column(
        Enum(CredentialType, name="credential_type_enum", create_constraint=True),
        nullable=False,
    )

    # Encrypted payload (AES-256-GCM encoded as base64)
    encrypted_access_token: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    encrypted_api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_client_secret: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    # OAuth2 specific metadata
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    oauth_client_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    oauth_scopes: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    oauth_state: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    oauth_access_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    oauth_refresh_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    oauth_id_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    oauth_token_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Credential lifecycle
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rotation_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_rotated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    integration = relationship("Integration", back_populates="credentials")

    __table_args__ = (
        Index(
            "ix_integration_credentials_integration_type",
            "integration_id",
            "credential_type",
        ),
        Index(
            "ix_integration_credentials_tenant",
            "tenant_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<IntegrationCredential id={self.id} "
            f"integration={self.integration_id} type={self.credential_type}>"
        )
