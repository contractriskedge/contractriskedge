"""Excluded paths that bypass auth and tenant middleware.

These paths are publicly accessible without authentication.
In production, only health/readiness endpoints and API docs should be excluded.
"""

from __future__ import annotations


def canonical_request_path(path: str) -> str:
    """Normalize URL path for exclusion checks (handles trailing slashes)."""
    stripped = path.rstrip("/")
    return stripped if stripped else "/"


# Canonical paths that bypass auth and tenant middleware (no trailing slash)
EXCLUDED_PATHS: frozenset[str] = frozenset(
    {
        canonical_request_path(p)
        for p in (
            "/api/v1/health",
            "/api/v1/ready",
            "/health",
            "/ready",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/token",
        )
    }
)


def is_path_excluded(path: str) -> bool:
    """Return True if this request path should skip JWT auth and tenant checks."""
    return canonical_request_path(path) in EXCLUDED_PATHS
