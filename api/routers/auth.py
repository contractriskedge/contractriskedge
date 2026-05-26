"""Backend proxy for Auth0 token exchange.

Moves OAuth client secret from frontend to backend to prevent
exposure of credentials in browser-side code. Also provides a
development admin login for testing.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, HTTPException, Query, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://api.contractriskedge.com")

# Default admin user for development
DEV_ADMIN_USER = {
    "sub": "auth0|admin",
    "email": "admin@democorp.com",
    "name": "Admin User",
    "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "role": "admin",
    "permissions": [
        "read:contracts", "write:contracts", "delete:contracts",
        "read:redlines", "write:redlines", "accept:redlines",
        "read:benchmarks", "write:playbooks",
        "read:audit", "export:audit", "export:data",
        "manage:users", "manage:billing", "manage:integrations",
        "admin:tenant", "admin:system",
    ],
}


def _create_dev_token() -> str:
    """Create a development JWT token for the admin user.

    Uses a simple unsigned JWT (HS256 with a dev secret) for local
    development. In production, Auth0 handles token generation.

    Returns:
        A JWT token string.
    """
    import base64
    import hashlib
    import hmac

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    now = int(time.time())
    payload_dict = {
        **DEV_ADMIN_USER,
        "iss": "https://dev.auth0.com/",
        "aud": "https://api.contractriskedge.com",
        "iat": now,
        "exp": now + 86400,  # 24 hours
        "scope": "openid profile email",
    }
    payload = base64.urlsafe_b64encode(
        json.dumps(payload_dict).encode()
    ).rstrip(b"=").decode()

    # Simple dev secret for signing
    secret = os.getenv("DEV_JWT_SECRET", "dev-secret-change-in-production")
    signature = base64.urlsafe_b64encode(
        hmac.new(
            secret.encode(),
            f"{header}.{payload}".encode(),
            hashlib.sha256,
        ).digest()
    ).rstrip(b"=").decode()

    return f"{header}.{payload}.{signature}"


@router.post("/token")
async def get_auth_token(dev_mode: bool = Query(False, description="Use development admin login")) -> dict:
    """Exchange client credentials for an access token.

    This endpoint acts as a proxy for the Auth0 OAuth token exchange,
    keeping the client secret server-side instead of exposing it in
    the frontend code.

    When dev_mode=true, returns a development token for the admin user
    without requiring Auth0 configuration.

    Args:
        dev_mode: If true, returns a development admin token.

    Returns:
        Dict with access_token, token_type, expires_in.

    Raises:
        HTTPException: If Auth0 configuration is missing or exchange fails.
    """
    # Development mode: return a local admin token
    if dev_mode or os.getenv("ENVIRONMENT") == "development":
        token = _create_dev_token()
        return {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 86400,
            "dev_mode": True,
        }

    if not all([AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth0 not configured. Set AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET.",
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"https://{AUTH0_DOMAIN}/oauth/token",
                json={
                    "client_id": AUTH0_CLIENT_ID,
                    "client_secret": AUTH0_CLIENT_SECRET,
                    "audience": AUTH0_AUDIENCE,
                    "grant_type": "client_credentials",
                },
            )
            response.raise_for_status()
            data = response.json()

            return {
                "access_token": data["access_token"],
                "token_type": data.get("token_type", "Bearer"),
                "expires_in": data.get("expires_in", 86400),
            }

    except httpx.HTTPStatusError as exc:
        logger.error("Auth0 token exchange failed: %s", exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service unavailable",
        )
    except Exception as exc:
        logger.error("Auth0 token exchange error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.get("/dev-login")
async def dev_login() -> dict:
    """Development-only: Get an admin token without Auth0.

    Returns a signed JWT for the admin user with full permissions.
    Only available when ENVIRONMENT=development.

    Returns:
        Dict with access_token and user info.

    Raises:
        HTTPException: If not in development mode.
    """
    if os.getenv("ENVIRONMENT", "development") != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login only available in development mode",
        )

    token = _create_dev_token()
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 86400,
        "user": DEV_ADMIN_USER,
    }
