"""Development-only HS256 JWT helper (matches JWTValidator._try_dev_token)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64encode

from app.config import settings


def create_dev_access_token(*, expires_in: int = 3600) -> str:
    """Build a signed dev JWT for local frontend/API testing."""
    header = urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload_data = {
        "sub": settings.dev_user_id,
        "email": "dev@localhost",
        "tenant_id": settings.dev_tenant_id,
        "role": "tenant_admin",
        "permissions": ["*"],
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
