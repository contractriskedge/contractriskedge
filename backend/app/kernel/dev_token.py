"""Development-only HS256 JWT helper (matches JWTValidator._try_dev_token)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64encode
from typing import Optional

from app.config import settings


# Role configurations for dev token generation
DEV_ROLE_CONFIGS = {
    "admin": {
        "sub": "test-admin-1",
        "email": "admin@test.cre",
        "role": "tenant_admin",
        "permissions": ["*"],
    },
    "reviewer": {
        "sub": "test-reviewer-1",
        "email": "reviewer@test.cre",
        "role": "reviewer",
        "permissions": [
            "contracts:read", "contracts:write",
            "ai:view",
            "workflows:read", "workflows:write",
            "reviews:export", "benchmarks:read",
        ],
    },
    "legal": {
        "sub": "test-legal-1",
        "email": "legal@test.cre",
        "role": "legal_reviewer",
        "permissions": [
            "contracts:read", "contracts:approve", "ai:view",
            "workflows:read", "workflows:write", "workflows:approve",
            "workflows:escalate", "audit:read", "reviews:export",
            "benchmarks:read",
        ],
    },
    "viewer": {
        "sub": "test-viewer-1",
        "email": "viewer@test.cre",
        "role": "viewer",
        "permissions": [
            "contracts:read", "ai:view",
            "workflows:read", "audit:read",
        ],
    },
}


def create_dev_access_token(*, expires_in: int = 3600,
                            role: Optional[str] = None) -> str:
    """Build a signed dev JWT for local frontend/API testing.

    Args:
        expires_in: Token lifetime in seconds (default 3600).
        role: Optional role key from DEV_ROLE_CONFIGS. If None or unknown,
              defaults to tenant_admin (full access).
    """
    cfg = DEV_ROLE_CONFIGS.get(role, {
        "sub": settings.dev_user_id,
        "email": "dev@localhost",
        "role": "tenant_admin",
        "permissions": ["*"],
    })

    header = urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload_data = {
        "sub": cfg["sub"],
        "email": cfg["email"],
        "tenant_id": settings.dev_tenant_id,
        "role": cfg["role"],
        "permissions": cfg["permissions"],
        "exp": int(time.time()) + expires_in,
        "iat": int(time.time()),
    }
    payload = urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
    signature = urlsafe_b64encode(
        hmac.new(
            settings.dev_jwt_secret.encode(),
            f"{header}.{payload}".encode(),
            hashlib.sha256,
        ).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.{signature}"
