"""Test configuration and shared fixtures for the API test suite.

Provides pytest fixtures for test database setup, test client,
authentication mocks, and common test data factories.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Generator

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

# ── Test Configuration ──────────────────────────────────────────────────

TEST_TENANT_ID = "test-tenant-001"
TEST_USER_ID = "auth0|test-user-123"
TEST_USER_EMAIL = "test@example.com"

# Patch auth middleware and dependencies BEFORE any app imports
os.environ["ENVIRONMENT"] = "test"
os.environ["AUTH0_DOMAIN"] = "test.auth0.com"
os.environ["AUTH0_CLIENT_ID"] = "test-client-id"
os.environ["AUTH0_CLIENT_SECRET"] = "test-client-secret"
os.environ["AUTH0_AUDIENCE"] = "https://api.contractriskedge.com"
os.environ["REDIS_URL"] = ""
os.environ["DATABASE_URL"] = ""

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock the auth middleware module BEFORE it's imported by main.py
from unittest.mock import MagicMock, AsyncMock
import middleware.auth as auth_module
import middleware.rate_limit as rate_limit_module


class MockTokenPayload:
    """Mock token payload for testing."""
    def __init__(self, **kwargs):
        self.sub = kwargs.get("sub", TEST_USER_ID)
        self.tenant_id = kwargs.get("tenant_id", TEST_TENANT_ID)
        self.email = kwargs.get("email", TEST_USER_EMAIL)
        self.role = kwargs.get("role", "admin")
        self.permissions = kwargs.get("permissions", [
            "read:contracts", "write:contracts", "delete:contracts",
            "read:redlines", "write:redlines",
            "read:benchmarks",
            "write:playbooks",
            "read:audit", "export:audit",
            "export:data",
            "manage:users", "admin:tenant",
        ])
        self.iss = "https://test.auth0.com/"
        self.aud = "https://api.contractriskedge.com"


async def mock_get_current_user(request: Request = None):
    """Mock get_current_user dependency."""
    return MockTokenPayload()


def mock_require_permission(*args, **kwargs):
    """Mock require_permission dependency."""
    async def dependency():
        return None
    return dependency


# Apply patches
auth_module.get_current_user = mock_get_current_user
auth_module.require_permission = mock_require_permission


class MockAuthMiddleware:
    """Mock auth middleware that always passes."""
    def __init__(self, app, exclude_paths=None):
        self.app = app
        self.exclude_paths = exclude_paths or set()

    async def __call__(self, scope, receive, send):
        """Pass through without auth validation."""
        await self.app(scope, receive, send)


auth_module.AuthMiddleware = MockAuthMiddleware


class MockRateLimitMiddleware:
    """Mock rate limit middleware that always passes."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)


rate_limit_module.RateLimitMiddleware = MockRateLimitMiddleware


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create the FastAPI application for testing with mocked auth.

    Returns:
        The FastAPI app instance with mocked authentication.
    """
    from main import app as _app
    return _app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with mock authentication.

    Args:
        app: The FastAPI application.

    Yields:
        An async HTTP client.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def sample_clause_text() -> str:
    """Provide a sample contract clause for testing.

    Returns:
        A realistic indemnification clause text.
    """
    return (
        "The Supplier shall indemnify, defend, and hold harmless the Customer "
        "from and against any and all claims, damages, losses, liabilities, "
        "and expenses arising out of or related to any breach of this Agreement "
        "by the Supplier, its employees, agents, or subcontractors. "
        "The Customer shall promptly notify the Supplier of any claim, "
        "reasonably cooperate in the defense, and permit the Supplier to "
        "control the defense and settlement of any claim."
    )


@pytest.fixture
def sample_playbook_rule_data() -> Dict[str, Any]:
    """Provide sample playbook rule creation data.

    Returns:
        Dict with rule creation fields.
    """
    return {
        "clause_type": "indemnification",
        "condition": "contains",
        "value": "indemnify",
        "action": "set_severity",
        "action_value": "high",
        "priority": 10,
    }


@pytest.fixture
def sample_playbook_data() -> Dict[str, Any]:
    """Provide sample playbook creation data.

    Returns:
        Dict with playbook creation fields.
    """
    return {
        "name": "Test Playbook",
        "description": "A test playbook for unit tests",
        "contract_types": ["nda", "service_agreement"],
    }
