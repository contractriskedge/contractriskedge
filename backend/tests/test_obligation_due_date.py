"""Unit tests for obligation due date validation.

Tests cover:
- future date (pass)
- today (pass)
- past date (fail)
- admin override (pass)
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.obligations.schemas import ObligationCreate, ObligationUpdate
from app.domains.obligations.service import ObligationService

VALID_TENANT = "00000000-0000-4000-8000-000000000001"

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def service(mock_session):
    return ObligationService(mock_session, tenant_id=VALID_TENANT)


def _future_date(days=30):
    return datetime.now(timezone.utc) + timedelta(days=days)


def _past_date(days=1):
    return datetime.now(timezone.utc) - timedelta(days=days)


def _today():
    return datetime.now(timezone.utc)


# ── Schema-level tests (Pydantic validators) ────────────────────────


class TestObligationCreateSchemaValidation:

    def test_future_date_passes(self):
        """Creating an obligation with a future due_date should pass."""
        data = ObligationCreate(
            name="Test",
            obligation_type="payment",
            contract_uuid_id="00000000-0000-4000-8000-000000000001",
            due_date=_future_date(),
        )
        assert data.due_date is not None

    def test_today_passes(self):
        """Creating an obligation with due_date = today should pass."""
        data = ObligationCreate(
            name="Test",
            obligation_type="payment",
            contract_uuid_id="00000000-0000-4000-8000-000000000001",
            due_date=_today(),
        )
        assert data.due_date is not None

    def test_past_date_fails(self):
        """Creating an obligation with a past due_date should raise ValueError."""
        with pytest.raises(ValueError, match="Due date cannot be in the past"):
            ObligationCreate(
                name="Test",
                obligation_type="payment",
                contract_uuid_id="00000000-0000-4000-8000-000000000001",
                due_date=_past_date(),
            )

    def test_none_due_date_passes(self):
        """Creating an obligation without a due_date should pass."""
        data = ObligationCreate(
            name="Test",
            obligation_type="payment",
            contract_uuid_id="00000000-0000-4000-8000-000000000001",
        )
        assert data.due_date is None


class TestObligationUpdateSchemaValidation:

    def test_future_date_passes(self):
        """Updating with a future due_date should pass."""
        data = ObligationUpdate(
            due_date=_future_date(),
        )
        assert data.due_date is not None

    def test_today_passes(self):
        """Updating with due_date = today should pass."""
        data = ObligationUpdate(
            due_date=_today(),
        )
        assert data.due_date is not None

    def test_past_date_fails(self):
        """Updating with a past due_date should raise ValueError."""
        with pytest.raises(ValueError, match="Due date cannot be in the past"):
            ObligationUpdate(
                due_date=_past_date(),
            )

    def test_admin_override_passes(self):
        """Admin override flag should bypass past date validation."""
        data = ObligationUpdate(
            due_date=_past_date(),
            _admin_override_due_date=True,
        )
        assert data.due_date is not None
        assert data.admin_override_due_date is True

    def test_none_due_date_passes(self):
        """Updating without a due_date should pass."""
        data = ObligationUpdate(
            name="New name",
        )
        assert data.due_date is None


# ── Service-level tests ─────────────────────────────────────────────


VALID_UUID = "00000000-0000-4000-8000-000000000001"
VALID_OID = "00000000-0000-4000-8000-000000000002"


class TestObligationServiceCreateValidation:

    @patch("app.domains.obligations.service.uuid.uuid4")
    @patch("app.domains.obligations.service.select")
    async def test_create_future_date_passes(self, mock_select, mock_uuid4, service, mock_session):
        """Service should accept future due_date."""
        mock_uuid4.return_value = VALID_UUID
        mock_select.return_value.where.return_value = mock_select.return_value
        mock_execute = AsyncMock()
        mock_scalar = mock_execute.scalar_one_or_none
        mock_scalar.return_value = MagicMock(review_id="test")
        mock_session.execute = AsyncMock(return_value=mock_execute)

        data = ObligationCreate(
            name="Test",
            obligation_type="payment",
            contract_uuid_id=VALID_UUID,
            due_date=_future_date(),
        )
        # Should not raise
        await service.create_obligation(data)

    @patch("app.domains.obligations.service.uuid.uuid4")
    @patch("app.domains.obligations.service.select")
    async def test_create_past_date_fails(self, mock_select, mock_uuid4, service, mock_session):
        """Service should reject past due_date with HTTP 422."""
        data = ObligationCreate(
            name="Test",
            obligation_type="payment",
            contract_uuid_id=VALID_UUID,
            due_date=_past_date(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await service.create_obligation(data)
        assert exc_info.value.status_code == 422
        assert "Due date cannot be in the past" in exc_info.value.detail


class TestObligationServiceUpdateValidation:

    async def _setup_existing_obligation(self, service, mock_session):
        """Helper to mock an existing obligation in the database."""
        mock_ob = MagicMock()
        mock_ob.id = VALID_OID
        mock_ob.status = "open"
        mock_ob.assignee = None
        mock_ob.updated_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_ob
        mock_session.execute.return_value = mock_result
        return mock_ob

    async def test_update_future_date_passes(self, service, mock_session):
        """Standard user can update to a future due_date."""
        await self._setup_existing_obligation(service, mock_session)
        data = ObligationUpdate(due_date=_future_date())
        result = await service.update_obligation(VALID_OID, data)
        assert result is not None

    async def test_update_today_passes(self, service, mock_session):
        """Standard user can update to today's date."""
        await self._setup_existing_obligation(service, mock_session)
        data = ObligationUpdate(due_date=_today())
        result = await service.update_obligation(VALID_OID, data)
        assert result is not None

    async def test_standard_user_past_date_fails(self, service, mock_session):
        """Standard user cannot update to a past due_date."""
        await self._setup_existing_obligation(service, mock_session)
        data = ObligationUpdate(due_date=_past_date())
        with pytest.raises(HTTPException) as exc_info:
            await service.update_obligation(VALID_OID, data)
        assert exc_info.value.status_code == 422
        assert "Due date cannot be in the past" in exc_info.value.detail

    async def test_admin_override_past_date_passes(self, mock_session):
        """Admin user can override and set a past due_date."""
        admin_service = ObligationService(
            mock_session, tenant_id=VALID_TENANT, user_role="admin"
        )
        await self._setup_existing_obligation(admin_service, mock_session)
        data = ObligationUpdate(due_date=_past_date(), _admin_override_due_date=True)
        result = await admin_service.update_obligation(VALID_OID, data)
        assert result is not None

    async def test_superadmin_override_past_date_passes(self, mock_session):
        """Superadmin user can override and set a past due_date."""
        admin_service = ObligationService(
            mock_session, tenant_id=VALID_TENANT, user_role="superadmin"
        )
        await self._setup_existing_obligation(admin_service, mock_session)
        data = ObligationUpdate(due_date=_past_date(), _admin_override_due_date=True)
        result = await admin_service.update_obligation(VALID_OID, data)
        assert result is not None

    async def test_system_override_past_date_passes(self, mock_session):
        """System user can override and set a past due_date."""
        admin_service = ObligationService(
            mock_session, tenant_id=VALID_TENANT, user_role="system"
        )
        await self._setup_existing_obligation(admin_service, mock_session)
        data = ObligationUpdate(due_date=_past_date(), _admin_override_due_date=True)
        result = await admin_service.update_obligation(VALID_OID, data)
        assert result is not None
