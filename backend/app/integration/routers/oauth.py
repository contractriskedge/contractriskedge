"""
OAuth2 authorization API router.

Endpoints for initiating OAuth flows, handling callbacks,
and managing token lifecycle.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration.routers.dependencies import (
    get_audit_service,
    get_db,
    get_oauth_service,
    get_tenant_id,
)
from app.integration.schemas.credential import (
    CredentialResponse,
    OAuthCallbackRequest,
    TokenRefreshRequest,
)
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.oauth_service import OAuthService

router = APIRouter(prefix="/oauth", tags=["OAuth2"])


@router.get(
    "/authorize/{integration_id}",
    summary="Generate OAuth2 authorization URL",
)
async def authorize(
    request: Request,
    integration_id: uuid.UUID,
    redirect_uri: str = Query(..., description="OAuth callback redirect URI"),
    oauth: OAuthService = Depends(get_oauth_service),
):
    """
    Generate an OAuth2 authorization URL for an integration.

    Returns the URL the user should be redirected to for authorization,
    along with the CSRF state token.
    """
    from app.integration.models.integration import Integration

    db = await anext(get_db())
    try:
        result = await db.execute(
            type(Integration).select().where(
                Integration.id == integration_id,
                Integration.tenant_id == request.state.tenant_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found",
            )

        auth_data = oauth.generate_authorization_url(
            provider=integration.provider.value,
            integration_id=integration_id,
            redirect_uri=redirect_uri,
        )

        return {
            "authorization_url": auth_data["authorization_url"],
            "state": auth_data["state"],
            "redirect_uri": auth_data["redirect_uri"],
            "scope": auth_data["scope"],
            "integration_id": str(integration_id),
        }
    finally:
        await db.close()


@router.get(
    "/callback",
    summary="Handle OAuth2 callback",
)
async def oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="CSRF state token"),
    integration_id: uuid.UUID = Query(..., description="Integration ID"),
    redirect_uri: Optional[str] = Query(None, description="Redirect URI used"),
    oauth: OAuthService = Depends(get_oauth_service),
):
    """
    Handle OAuth2 callback from external provider.

    Exchanges the authorization code for tokens and stores them securely.
    """
    try:
        expected_state = request.headers.get("X-OAuth-State", "")
        credential = await oauth.handle_callback(
            integration_id=integration_id,
            code=code,
            state=state,
            redirect_uri=redirect_uri or "",
            expected_state=expected_state,
        )

        return {
            "status": "success",
            "integration_id": str(integration_id),
            "credential_id": str(credential.id),
            "expires_at": credential.oauth_access_token_expires_at.isoformat()
            if credential.oauth_access_token_expires_at
            else None,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/refresh",
    summary="Refresh OAuth2 token",
)
async def refresh_token(
    request: Request,
    body: TokenRefreshRequest,
    oauth: OAuthService = Depends(get_oauth_service),
):
    """Manually trigger an OAuth2 token refresh."""
    try:
        credential = await oauth.refresh_token(
            integration_id=body.integration_id,
            force=body.force,
        )

        return {
            "status": "success",
            "integration_id": str(body.integration_id),
            "credential_id": str(credential.id),
            "expires_at": credential.oauth_access_token_expires_at.isoformat()
            if credential.oauth_access_token_expires_at
            else None,
            "rotation_count": credential.rotation_count,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/revoke/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke OAuth2 token",
)
async def revoke_token(
    request: Request,
    integration_id: uuid.UUID,
    oauth: OAuthService = Depends(get_oauth_service),
):
    """Revoke OAuth2 tokens and disable the integration."""
    try:
        await oauth.revoke_token(integration_id=integration_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
