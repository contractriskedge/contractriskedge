"""Development auth token endpoint for the frontend API client."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.kernel.dev_token import create_dev_access_token

router = APIRouter(tags=["Auth"])


@router.post("/auth/token")
async def issue_dev_token():
    """Issue a short-lived dev JWT (development only)."""
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not found")

    token = create_dev_access_token()
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
    }
