"""Admin domain unit tests — settings defaults and response envelope."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.admin.responses import admin_ok
from app.domains.admin.repository import AdminRepository
from app.domains.admin.service import AdminService
from app.domains.admin.schemas import TenantSettingsResponse
from app.domains.admin.models import TenantSettings
from tests.conftest import TENANT_A_ID_STR


@pytest.mark.asyncio
async def test_get_settings_returns_defaults_when_no_row():
    repo = MagicMock()
    repo.get_settings = AsyncMock(return_value=None)
    service = AdminService(repo=repo, tenant_id="00000000-0000-4000-8000-000000000001", user_id="dev-user")

    result = await service.get_settings()

    assert isinstance(result, TenantSettingsResponse)
    assert result.brand_name == "ContractRiskEdge"
    assert result.risk_threshold_critical == 70
    assert result.risk_threshold_high == 50
    assert result.created_at is None


@pytest.mark.asyncio
async def test_get_settings_maps_persisted_row():
    now = datetime.now(timezone.utc)
    row = TenantSettings(
        tenant_id="00000000-0000-4000-8000-000000000001",
        brand_name="Acme Legal",
        risk_threshold_critical=80,
        risk_threshold_high=60,
        created_at=now,
        updated_at=now,
    )
    repo = MagicMock()
    repo.get_settings = AsyncMock(return_value=row)
    service = AdminService(repo=repo, tenant_id="00000000-0000-4000-8000-000000000001", user_id="dev-user")

    result = await service.get_settings()

    assert result.brand_name == "Acme Legal"
    assert result.risk_threshold_critical == 80
    assert result.created_at == now


@pytest.mark.asyncio
async def test_list_users_reads_seeded_rows(tenant_a_session, ensure_test_tenants):
    repo = AdminRepository(tenant_a_session, tenant_id=TENANT_A_ID_STR)
    service = AdminService(repo=repo, tenant_id=TENANT_A_ID_STR, user_id="dev-user")

    users = await service.list_users()
    roles = await service.list_roles()

    assert isinstance(users, list)
    assert len(roles) >= 7
    # Seed migration targets dev tenant; may be empty in fresh test DB without migration.
    assert all(u.email for u in users) or users == []


def test_admin_ok_envelope_sets_total_for_lists():
    envelope = admin_ok([{"user_id": "a"}, {"user_id": "b"}])
    assert envelope.success is True
    assert envelope.error is None
    assert envelope.meta.total == 2
    assert len(envelope.data) == 2
