"""Workflow integration tests — end-to-end review lifecycle validation.

Tests:
  - Upload → Review creation flow
  - Review status transitions
  - Finding resolution
  - Redline approval
  - Re-analysis trigger
  - Soft delete
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ingestion.models import UploadSession, IngestionState
from app.domains.review.models import ContractReview, ReviewStatus, ReviewFinding, ReviewRedline, FindingResolution, RedlineStatus
from app.domains.review.repository import ReviewRepository
from app.domains.review.service import ReviewService
from app.domains.ai.repository import AIRepository
from app.kernel.events.bus import EventBus

from tests.conftest import TENANT_A_ID_STR, TENANT_B_ID_STR


async def _create_review_service(session: AsyncSession, user, tenant_id: str) -> ReviewService:
    return ReviewService(
        review_repo=ReviewRepository(session, tenant_id=tenant_id),
        ai_repo=AIRepository(session, tenant_id=tenant_id),
        event_bus=EventBus(),
        user=user,
        tenant_id=tenant_id,
    )


class TestReviewLifecycle:
    """End-to-end review lifecycle tests."""

    @pytest.mark.asyncio
    async def test_create_review_from_upload(self, tenant_a_session, completed_upload, tenant_admin_user):
        """Should create a review from a completed upload."""
        service = await _create_review_service(tenant_a_session, tenant_admin_user, TENANT_A_ID_STR)

        result = await service.get_or_create_review(str(completed_upload.upload_id))

        assert result is not None
        assert result["upload_id"] == str(completed_upload.upload_id)
        assert result["status"] in ("draft", "ai_analyzed")
        assert result["created_by"] == "auth0|test-admin"

    @pytest.mark.asyncio
    async def test_review_status_transitions(self, tenant_a_session, sample_review, tenant_admin_user):
        """Should validate review status transitions."""
        service = await _create_review_service(tenant_a_session, tenant_admin_user, TENANT_A_ID_STR)

        # Transition from ai_analyzed to in_review
        result = await service.update_status(str(sample_review.review_id), "in_review")
        assert result is not None
        assert result["status"] == "in_review"

        # Transition from in_review to legal_approval
        result = await service.update_status(str(sample_review.review_id), "legal_approval")
        assert result["status"] == "legal_approval"

        # Transition from legal_approval to approved
        result = await service.update_status(str(sample_review.review_id), "approved")
        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_invalid_status_transition_fails(self, tenant_a_session, sample_review, tenant_admin_user):
        """Should reject invalid status transitions."""
        service = await _create_review_service(tenant_a_session, tenant_admin_user, TENANT_A_ID_STR)

        # Cannot transition from ai_analyzed directly to approved
        from app.domains.review.models import ReviewStatus
        review = await service.review_repo.get_review(str(sample_review.review_id), TENANT_A_ID_STR)
        assert review is not None
        assert not ReviewStatus(review.status).can_transition_to(ReviewStatus.APPROVED)

    @pytest.mark.asyncio
    async def test_list_reviews_with_filter(self, tenant_a_session, sample_review, tenant_admin_user):
        """Should list reviews with status filtering."""
        from app.domains.review.schemas import ReviewFilterParams

        service = await _create_review_service(tenant_a_session, tenant_admin_user, TENANT_A_ID_STR)

        filters = ReviewFilterParams(status="ai_analyzed")
        items, total = await service.list_reviews(filters)
        assert total >= 1
        # Verify the sample review exists in the DB with the correct status
        from sqlalchemy import select
        from app.domains.review.models import ContractReview
        result = await tenant_a_session.execute(
            select(ContractReview).where(
                ContractReview.review_id == sample_review.review_id,
                ContractReview.tenant_id == TENANT_A_ID_STR,
            )
        )
        db_review = result.scalar_one_or_none()
        assert db_review is not None
        assert db_review.status == ReviewStatus.AI_ANALYZED

    @pytest.mark.asyncio
    async def test_soft_delete_review(self, tenant_a_session, sample_review, tenant_admin_user):
        """Should soft-delete a review."""
        service = await _create_review_service(tenant_a_session, tenant_admin_user, TENANT_A_ID_STR)

        result = await service.soft_delete(str(sample_review.review_id), "Test deletion")
        assert result is True

        # Verify it's marked as deleted
        from sqlalchemy import select, update
        stmt = select(ContractReview).where(
            ContractReview.review_id == str(sample_review.review_id),
            ContractReview.tenant_id == TENANT_A_ID_STR,
        )
        result = await tenant_a_session.execute(stmt)
        review = result.scalar_one_or_none()
        assert review is not None
        assert review.is_deleted is True
        assert review.deleted_at is not None


class TestFindingsAndRedlines:
    """Finding and redline resolution tests."""

    @pytest.mark.asyncio
    async def test_resolve_finding(self, tenant_a_session, sample_review, tenant_admin_user):
        """Should resolve a finding with acknowledgment."""
        # Create a finding
        import uuid
        finding = ReviewFinding(
            finding_id=uuid.uuid4(),
            review_id=sample_review.review_id,
            upload_id=sample_review.upload_id,
            tenant_id=TENANT_A_ID_STR,
            severity="high",
            title="Unlimited liability clause",
            description="The contract contains an unlimited liability clause.",
            recommendation="Cap liability at 12 months of fees.",
        )
        tenant_a_session.add(finding)
        await tenant_a_session.flush()

        service = await _create_review_service(tenant_a_session, tenant_admin_user, TENANT_A_ID_STR)

        result = await service.resolve_finding(str(finding.finding_id), "acknowledged", "Reviewed and noted")
        assert result is not None
        assert result["resolution"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_resolve_finding_dismiss(self, tenant_a_session, sample_review, tenant_admin_user):
        """Should dismiss a finding as false positive."""
        import uuid
        finding = ReviewFinding(
            finding_id=uuid.uuid4(),
            review_id=sample_review.review_id,
            upload_id=sample_review.upload_id,
            tenant_id=TENANT_A_ID_STR,
            severity="medium",
            title="Test finding",
            description="Test description",
        )
        tenant_a_session.add(finding)
        await tenant_a_session.flush()

        service = await _create_review_service(tenant_a_session, tenant_admin_user, TENANT_A_ID_STR)

        result = await service.resolve_finding(str(finding.finding_id), "false_positive", "Incorrect analysis")
        assert result is not None
        assert result["resolution"] == "false_positive"

    @pytest.mark.asyncio
    async def test_update_redline(self, tenant_a_session, sample_review, tenant_admin_user):
        """Should accept a redline suggestion."""
        import uuid
        redline = ReviewRedline(
            redline_id=uuid.uuid4(),
            review_id=sample_review.review_id,
            upload_id=sample_review.upload_id,
            tenant_id=TENANT_A_ID_STR,
            clause_type="liability",
            original_text="Party A shall be liable for all damages.",
            proposed_text="Party A's liability shall be capped at 12 months of fees.",
        )
        tenant_a_session.add(redline)
        await tenant_a_session.flush()

        service = await _create_review_service(tenant_a_session, tenant_admin_user, TENANT_A_ID_STR)

        result = await service.update_redline(str(redline.redline_id), "accepted")
        assert result is not None
        assert result["status"] == "accepted"


class TestTenantIsolation:
    """Tenant isolation validation tests."""

    @pytest.mark.asyncio
    async def test_cross_tenant_review_isolation(self, tenant_a_session, tenant_b_session, sample_review, tenant_admin_user):
        """Tenant B should not see Tenant A's reviews."""
        service_b = await _create_review_service(tenant_b_session, tenant_admin_user, TENANT_B_ID_STR)

        # Tenant B should not find Tenant A's review
        from app.domains.review.schemas import ReviewFilterParams
        filters = ReviewFilterParams()
        items, total = await service_b.list_reviews(filters)
        review_ids = [str(r.review_id) for r in items]
        assert str(sample_review.review_id) not in review_ids

    @pytest.mark.asyncio
    async def test_cross_tenant_upload_isolation(self, tenant_a_session, tenant_b_session, sample_upload):
        """Tenant B should not see Tenant A's uploads."""
        from app.domains.ingestion.repository import IngestionRepository

        repo_b = IngestionRepository(tenant_b_session, tenant_id=TENANT_B_ID_STR)
        upload = await repo_b.get_upload(str(sample_upload.upload_id), TENANT_B_ID_STR)
        assert upload is None
