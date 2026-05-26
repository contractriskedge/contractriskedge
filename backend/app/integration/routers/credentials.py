"""
Credential management API router.

Endpoints for managing integration credentials (non-OAuth).
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.models.credential import (
    CredentialType,
    IntegrationCredential,
)
from app.integration.routers.dependencies import (
    get_audit_service,
    get_db,
    get_tenant_id,
)
from app.integration.schemas.credential import CredentialCreate, CredentialResponse
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.crypto import CredentialVault

router = APIRouter(prefix="/credentials", tags=["Credentials"])


@router.post(
    "/{integration_id}",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add credential to integration",
)
async def create_credential(
    integration_id: uuid.UUID,
    body: CredentialCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
):
    """Add a credential (API key, basic auth, etc.) to an integration."""
    vault = CredentialVault()

    encrypted_api_key = None
    if body.encrypted_api_key:
        encrypted_api_key = vault.store_token(
            str(tenant_id),
            str(integration_id),
            body.encrypted_api_key,
            token_type="api_key",
        )

    credential = IntegrationCredential(
        integration_id=integration_id,
        tenant_id=tenant_id,
        credential_type=CredentialType(body.credential_type),
        encrypted_api_key=encrypted_api_key,
        metadata_=body.metadata or {},
    )

    db.add(credential)
    await db.flush()
    await db.refresh(credential)

    await audit.log_credential_change(
        integration_id=integration_id,
        credential_id=credential.id,
        change_type="created",
    )

    return credential


@router.get(
    "/{integration_id}",
    response_model=list[CredentialResponse],
    summary="List credentials for integration",
)
async def list_credentials(
    integration_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """List all credentials for an integration."""
    result = await db.execute(
        select(IntegrationCredential).where(
            IntegrationCredential.integration_id == integration_id,
            IntegrationCredential.tenant_id == tenant_id,
            IntegrationCredential.is_revoked == False,
        ).order_by(IntegrationCredential.version.desc())
    )
    return list(result.scalars().all())


@router.delete(
    "/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke credential",
)
async def revoke_credential(
    credential_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    audit: IntegrationAuditService = Depends(get_audit_service),
):
    """Revoke a specific credential."""
    result = await db.execute(
        select(IntegrationCredential).where(
            IntegrationCredential.id == credential_id,
            IntegrationCredential.tenant_id == tenant_id,
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    credential.is_revoked = True
    credential.is_expired = True
    await db.flush()

    await audit.log_credential_change(
        integration_id=credential.integration_id,
        credential_id=credential.id,
        change_type="revoked",
    )
