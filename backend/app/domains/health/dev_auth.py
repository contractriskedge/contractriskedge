"""Development auth token endpoint for the frontend API client."""

from __future__ import annotations

import base64
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.domains.audit.recorder import AuditRecorder
from app.kernel.dev_token import create_dev_access_token

router = APIRouter(tags=["Auth"])


def _read_jwt_claims(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        padded = payload + "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return {}


@router.post("/auth/token")
async def issue_dev_token(
    request: Request,
    role: Optional[str] = Query(None, description="Dev role: admin, reviewer, legal, viewer"),
):
    """Issue a short-lived dev JWT (development only).

    Supports role-based tokens for testing:
      POST /api/v1/auth/token          → admin (default)
      POST /api/v1/auth/token?role=reviewer → reviewer
      POST /api/v1/auth/token?role=legal    → legal ops
      POST /api/v1/auth/token?role=viewer   → read-only
    """
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not found")

    token = create_dev_access_token(role=role)
    claims = _read_jwt_claims(token)
    tenant_id = str(claims.get("tenant_id") or settings.dev_tenant_id)

    factory = getattr(request.app.state, "db_factory", None)
    if factory is not None:
        session = await factory.create_session(
            tenant_id=tenant_id,
            user_id=str(claims.get("sub", "unknown")),
            user_role=str(claims.get("role", role or "tenant_admin")),
        )
        try:
            recorder = AuditRecorder(session, tenant_id)
            await recorder.record(
                event_type="auth.login.success",
                actor_id=str(claims.get("sub", "unknown")),
                actor_role=str(claims.get("role", role or "tenant_admin")),
                description=f"Development login issued for role {role or 'admin'}",
                status="success",
                severity="info",
                source="dev_auth",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                after_state={"role": claims.get("role"), "email": claims.get("email")},
                metadata={"auth_provider": "dev_token", "requested_role": role},
            )
            await session.commit()
        except Exception:
            await session.rollback()
        finally:
            await session.close()

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }
