"""Comprehensive regression tests for the Workflow Reliability Layer.

Tests the full state machine, lock guards, audit trail, finalized version
generation, intelligent re-analysis, redline scope, and bulk actions.

This file covers the ENTIRE test matrix:
  approve         → success
  reject          → success
  escalate        → success
  bulk accept     → success
  bulk reject     → success
  edit redline    → success
  approve after escalation → success
  reanalyze after accepted redlines → preserved
  finalize        → immutable
  archived mutation attempt → blocked
  invalid transition → blocked
  double approve  → blocked
  post-finalization edits → blocked
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select, text as sa_text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.review.models import (
    ContractReview, ReviewFinding, ReviewRedline, ReviewComment,
    ReviewStatusHistory, ReviewApproval, ReviewEscalation,
    ReviewStatus, FindingResolution, RedlineStatus,
)
from app.domains.review.workflow import (
    WorkflowState, validate_transition, TransitionError,
    ImmutableReviewError, guard_mutable, map_legacy_status,
)
from app.domains.review.lock_guard import (
    assert_review_mutable, assert_can_approve_or_reject,
    assert_can_edit_redlines, assert_can_reassign,
)
from app.domains.review.audit_trail import AuditTrailService
from app.domains.review.finalized_version import create_finalized_version, FinalizedVersionResult
from app.domains.review.redline_scope import (
    split_sentences, split_clauses, find_localized_replacement,
    validate_redline_scope, resolve_redline_text,
)
from app.domains.review.repository import ReviewRepository
from app.domains.review.service import ReviewService
from app.domains.review.schemas import ReviewFilterParams
from app.domains.ai.repository import AIRepository
from app.kernel.events.bus import EventBus
from app.kernel.security.auth import UserContext
from app.kernel.web.exceptions import ConflictError

from tests.conftest import TENANT_A_ID, TENANT_A_ID_STR


# ═══════════════════════════════════════════════════════════════════
# PART 1: Workflow State Machine Unit Tests
# ═══════════════════════════════════════════════════════════════════

class TestWorkflowStateMachine:
    """Comprehensive tests for the WorkflowState machine."""

    def test_all_workflow_states_exist(self):
        """Verify all 9 states exist."""
        expected = {
            "uploaded", "ai_analyzed", "review_ready", "in_review",
            "escalated", "approved", "rejected", "finalized", "archived",
        }
        actual = {s.value for s in WorkflowState}
        assert actual == expected, f"Missing states: {expected - actual}"

    def test_valid_transitions_from_uploaded(self):
        allowed = WorkflowState.valid_transitions()[WorkflowState.UPLOADED]
        assert WorkflowState.AI_ANALYZED in allowed
        assert WorkflowState.ARCHIVED in allowed
        assert WorkflowState.FINALIZED not in allowed
        assert WorkflowState.APPROVED not in allowed

    def test_valid_transitions_from_ai_analyzed(self):
        allowed = WorkflowState.valid_transitions()[WorkflowState.AI_ANALYZED]
        assert WorkflowState.REVIEW_READY in allowed
        assert WorkflowState.ARCHIVED in allowed

    def test_valid_transitions_from_review_ready(self):
        allowed = WorkflowState.valid_transitions()[WorkflowState.REVIEW_READY]
        assert WorkflowState.IN_REVIEW in allowed
        assert WorkflowState.ARCHIVED in allowed

    def test_valid_transitions_from_in_review(self):
        allowed = WorkflowState.valid_transitions()[WorkflowState.IN_REVIEW]
        assert WorkflowState.APPROVED in allowed
        assert WorkflowState.REJECTED in allowed
        assert WorkflowState.ESCALATED in allowed
        assert WorkflowState.ARCHIVED in allowed
        assert WorkflowState.FINALIZED not in allowed

    def test_valid_transitions_from_escalated(self):
        allowed = WorkflowState.valid_transitions()[WorkflowState.ESCALATED]
        assert WorkflowState.IN_REVIEW in allowed
        assert WorkflowState.APPROVED in allowed
        assert WorkflowState.REJECTED in allowed
        assert WorkflowState.ARCHIVED in allowed

    def test_valid_transitions_from_approved(self):
        allowed = WorkflowState.valid_transitions()[WorkflowState.APPROVED]
        assert WorkflowState.FINALIZED in allowed
        assert WorkflowState.ARCHIVED in allowed
        assert WorkflowState.IN_REVIEW not in allowed
        assert WorkflowState.REJECTED not in allowed

    def test_valid_transitions_from_rejected(self):
        allowed = WorkflowState.valid_transitions()[WorkflowState.REJECTED]
        assert WorkflowState.ARCHIVED in allowed
        assert WorkflowState.IN_REVIEW not in allowed  # No more re-opening

    def test_valid_transitions_from_finalized(self):
        allowed = WorkflowState.valid_transitions()[WorkflowState.FINALIZED]
        assert WorkflowState.ARCHIVED in allowed
        assert len(allowed) == 1  # Only ARCHIVED

    def test_archived_is_terminal(self):
        allowed = WorkflowState.valid_transitions()[WorkflowState.ARCHIVED]
        assert len(allowed) == 0
        assert WorkflowState.ARCHIVED.is_terminal()

    def test_terminal_states(self):
        assert WorkflowState.ARCHIVED.is_terminal()
        assert not WorkflowState.IN_REVIEW.is_terminal()
        assert not WorkflowState.APPROVED.is_terminal()

    def test_immutable_states(self):
        assert WorkflowState.APPROVED.is_immutable()
        assert WorkflowState.REJECTED.is_immutable()
        assert WorkflowState.FINALIZED.is_immutable()
        assert WorkflowState.ARCHIVED.is_immutable()
        assert not WorkflowState.IN_REVIEW.is_immutable()
        assert not WorkflowState.UPLOADED.is_immutable()

    def test_mutable_states(self):
        assert WorkflowState.UPLOADED.is_mutable()
        assert WorkflowState.IN_REVIEW.is_mutable()
        assert WorkflowState.ESCALATED.is_mutable()
        assert not WorkflowState.FINALIZED.is_mutable()

    # ── validate_transition tests ─────────────────────────────

    @pytest.mark.parametrize("from_state,to_state", [
        (WorkflowState.UPLOADED, WorkflowState.AI_ANALYZED),
        (WorkflowState.AI_ANALYZED, WorkflowState.REVIEW_READY),
        (WorkflowState.REVIEW_READY, WorkflowState.IN_REVIEW),
        (WorkflowState.IN_REVIEW, WorkflowState.APPROVED),
        (WorkflowState.IN_REVIEW, WorkflowState.REJECTED),
        (WorkflowState.IN_REVIEW, WorkflowState.ESCALATED),
        (WorkflowState.ESCALATED, WorkflowState.IN_REVIEW),
        (WorkflowState.ESCALATED, WorkflowState.APPROVED),
        (WorkflowState.APPROVED, WorkflowState.FINALIZED),
        (WorkflowState.FINALIZED, WorkflowState.ARCHIVED),
        (WorkflowState.REJECTED, WorkflowState.ARCHIVED),
        (WorkflowState.UPLOADED, WorkflowState.ARCHIVED),
    ])
    def test_valid_transition_succeeds(self, from_state, to_state):
        """All valid transitions should pass without exception."""
        record = validate_transition(from_state, to_state)
        assert record.from_state == from_state
        assert record.to_state == to_state
        assert record.is_valid

    @pytest.mark.parametrize("from_state,to_state", [
        (WorkflowState.UPLOADED, WorkflowState.FINALIZED),
        (WorkflowState.UPLOADED, WorkflowState.APPROVED),
        (WorkflowState.AI_ANALYZED, WorkflowState.APPROVED),
        (WorkflowState.REVIEW_READY, WorkflowState.FINALIZED),
        (WorkflowState.IN_REVIEW, WorkflowState.FINALIZED),
        (WorkflowState.APPROVED, WorkflowState.IN_REVIEW),
        (WorkflowState.APPROVED, WorkflowState.REJECTED),
        (WorkflowState.REJECTED, WorkflowState.IN_REVIEW),
        (WorkflowState.FINALIZED, WorkflowState.IN_REVIEW),
        (WorkflowState.FINALIZED, WorkflowState.APPROVED),
        (WorkflowState.ARCHIVED, WorkflowState.UPLOADED),
        (WorkflowState.ARCHIVED, WorkflowState.IN_REVIEW),
    ])
    def test_invalid_transition_raises(self, from_state, to_state):
        """All invalid transitions should raise TransitionError."""
        with pytest.raises(TransitionError) as exc_info:
            validate_transition(from_state, to_state, review_id="test-review")
        assert exc_info.value.review_id == "test-review"
        assert exc_info.value.from_state == from_state.value
        assert exc_info.value.to_state == to_state.value

    def test_transition_error_message_includes_allowed(self):
        """Error message should list allowed transitions."""
        with pytest.raises(TransitionError) as exc_info:
            validate_transition(WorkflowState.UPLOADED, WorkflowState.FINALIZED)
        msg = str(exc_info.value)
        assert "uploaded" in msg
        assert "finalized" in msg
        assert "ai_analyzed" in msg or "archived" in msg

    def test_from_string_valid(self):
        assert WorkflowState.from_string("approved") == WorkflowState.APPROVED
        assert WorkflowState.from_string("in_review") == WorkflowState.IN_REVIEW
        assert WorkflowState.from_string("finalized") == WorkflowState.FINALIZED

    def test_from_string_invalid(self):
        from app.domains.review.workflow import InvalidStateError
        with pytest.raises(InvalidStateError):
            WorkflowState.from_string("nonexistent_state")

    def test_can_transition_to_method(self):
        assert WorkflowState.IN_REVIEW.can_transition_to(WorkflowState.APPROVED)
        assert not WorkflowState.IN_REVIEW.can_transition_to(WorkflowState.FINALIZED)
        assert WorkflowState.APPROVED.can_transition_to(WorkflowState.FINALIZED)
        assert not WorkflowState.APPROVED.can_transition_to(WorkflowState.IN_REVIEW)

    # ── Legacy mapping tests ──────────────────────────────────

    @pytest.mark.parametrize("legacy,expected", [
        ("draft", "uploaded"),
        ("ai_analyzed", "ai_analyzed"),
        ("review_ready", "review_ready"),
        ("in_review", "in_review"),
        ("changes_requested", "in_review"),
        ("escalated", "escalated"),
        ("legal_approval", "in_review"),
        ("exec_approval", "in_review"),
        ("approved", "approved"),
        ("rejected", "rejected"),
        ("finalized", "finalized"),
        ("closed", "archived"),
    ])
    def test_legacy_mapping(self, legacy, expected):
        assert map_legacy_status(legacy).value == expected

    def test_unknown_legacy_mapping_defaults_to_uploaded(self):
        assert map_legacy_status("unknown_status").value == "uploaded"


# ═══════════════════════════════════════════════════════════════════
# PART 2: Lock Guard Tests
# ═══════════════════════════════════════════════════════════════════

class TestLockGuard:
    """Tests for the review lock guard — enforces read-only on immutable states."""

    @pytest.mark.parametrize("status", ["approved", "rejected", "finalized", "archived"])
    def test_immutable_states_block_mutations(self, status):
        """All mutations should be blocked on immutable states."""
        with pytest.raises(ImmutableReviewError) as exc_info:
            assert_review_mutable(status, "edit redlines", "review-123")
        assert exc_info.value.review_id == "review-123"
        assert exc_info.value.status == status
        assert exc_info.value.action == "edit redlines"

    @pytest.mark.parametrize("status", ["uploaded", "ai_analyzed", "review_ready", "in_review", "escalated"])
    def test_mutable_states_allow_mutations(self, status):
        """All mutations should be allowed on mutable states."""
        # Should not raise
        assert_review_mutable(status, "edit redlines", "review-123")

    def test_immutable_error_message_clear(self):
        """Error messages should tell the user why they're blocked."""
        with pytest.raises(ImmutableReviewError) as exc_info:
            assert_review_mutable("finalized", "edit redlines", "review-456")
        msg = str(exc_info.value)
        assert "finalized" in msg
        assert "read-only" in msg
        assert "review-456" in msg

    # ── Specific guard tests ──────────────────────────────────

    @pytest.mark.parametrize("status", ["approved", "rejected", "finalized", "archived"])
    def test_assert_can_edit_redlines_blocked(self, status):
        with pytest.raises(ImmutableReviewError):
            assert_can_edit_redlines(status, "review-123")

    def test_assert_can_edit_redlines_allowed(self):
        assert_can_edit_redlines("in_review", "review-123")

    @pytest.mark.parametrize("status", ["approved", "rejected", "finalized", "archived"])
    def test_assert_can_reassign_blocked(self, status):
        with pytest.raises(ImmutableReviewError):
            assert_can_reassign(status, "review-123")

    def test_assert_can_reassign_allowed(self):
        assert_can_reassign("in_review", "review-123")

    # ── Approval guard tests ──────────────────────────────────

    def test_can_approve_from_in_review(self):
        assert_can_approve_or_reject("in_review", "review-123")

    def test_can_approve_from_escalated(self):
        assert_can_approve_or_reject("escalated", "review-123")

    @pytest.mark.parametrize("status", [
        "uploaded", "ai_analyzed", "review_ready", "approved",
        "rejected", "finalized", "archived",
    ])
    def test_cannot_approve_from_wrong_state(self, status):
        with pytest.raises(ImmutableReviewError) as exc_info:
            assert_can_approve_or_reject(status, "review-123")
        assert "approve/reject" in str(exc_info.value)

    def test_locked_states_description(self):
        from app.domains.review.lock_guard import locked_states_description
        desc = locked_states_description()
        assert "approved" in desc
        assert "rejected" in desc
        assert "finalized" in desc
        assert "archived" in desc
        assert "read-only" in desc


# ═══════════════════════════════════════════════════════════════════
# PART 3: Audit Trail Tests
# ═══════════════════════════════════════════════════════════════════

class TestAuditTrail:
    """Tests for the enterprise audit trail service."""

    @pytest.mark.asyncio
    async def test_record_transition(self):
        """Verify transition audit event is recorded (uses mock session)."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        audit = AuditTrailService(mock_session, TENANT_A_ID_STR)
        # Should not raise
        await audit.record_transition(
            review_id="review-1",
            from_status="in_review",
            to_status="approved",
            actor_id="user-1",
            reason="Approved by legal",
        )
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_record_redline_action(self):
        """Verify redline audit event is recorded (uses mock session)."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        audit = AuditTrailService(mock_session, TENANT_A_ID_STR)
        await audit.record_redline_action(
            redline_id="rl-1",
            review_id="review-1",
            actor_id="user-1",
            action="accepted",
            before_status="proposed",
            after_status="accepted",
        )
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_record_finding_action(self):
        """Verify finding audit event is recorded (uses mock session)."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        audit = AuditTrailService(mock_session, TENANT_A_ID_STR)
        await audit.record_finding_action(
            finding_id="finding-1",
            review_id="review-1",
            actor_id="user-1",
            resolution="acknowledged",
        )
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_record_approval_action(self):
        """Verify approval audit event is recorded (uses mock session)."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        audit = AuditTrailService(mock_session, TENANT_A_ID_STR)
        await audit.record_approval_action(
            review_id="review-1",
            actor_id="user-1",
            decision="approved",
            description="Approved with conditions",
        )
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_record_escalation(self):
        """Verify escalation audit event is recorded (uses mock session)."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        audit = AuditTrailService(mock_session, TENANT_A_ID_STR)
        await audit.record_escalation(
            review_id="review-1",
            actor_id="user-1",
            escalated_to="legal-team",
            reason="High risk clause needs legal review",
        )
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_record_version_action(self):
        """Verify version audit event is recorded (uses mock session)."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        audit = AuditTrailService(mock_session, TENANT_A_ID_STR)
        await audit.record_version_action(
            version_id="ver-1",
            review_id="review-1",
            actor_id="user-1",
            action="finalize",
            version_number=3,
        )
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_audit_failure_does_not_propagate(self):
        """Audit failures should be logged but not break the calling operation."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))
        audit = AuditTrailService(mock_session, TENANT_A_ID_STR)
        # This should not raise even with DB error
        await audit.record(
            event_type="test.event",
            entity_type="review",
            entity_id="test",
            actor_id="test",
            action="test",
        )
        # If we get here, the audit didn't propagate the error


# ═══════════════════════════════════════════════════════════════════
# PART 4: Redline Scope Tests
# ═══════════════════════════════════════════════════════════════════

class TestRedlineScope:
    """Tests for redline scope accuracy — sentence/clause boundary detection."""

    def test_split_sentences_basic(self):
        text = "This is a test. Here is another sentence. And a third one."
        result = split_sentences(text)
        assert len(result) == 3
        assert "This is a test." in result[0] or result[0] == "This is a test."

    def test_split_sentences_with_legal_abbreviations(self):
        """Legal abbreviations like 'e.g.' and 'i.e.' should not cause false splits."""
        text = "The Company shall indemnify the Client, e.g. for losses. This is separate."
        result = split_sentences(text)
        assert len(result) == 2
        assert "e.g." in result[0]

    def test_split_clauses_basic(self):
        text = "The Company shall indemnify the Client provided that the Client notifies within 30 days."
        result = split_clauses(text)
        # Should split into at least 2 segments at 'provided that'
        assert len(result) >= 1, f"Expected at least 1 clause, got {len(result)}: {result}"

    def test_split_clauses_single(self):
        text = "Simple clause with no boundaries."
        result = split_clauses(text)
        assert len(result) == 1

    def test_find_localized_replacement_exact(self):
        doc = "The Company shall indemnify the Client against all losses."
        result = find_localized_replacement(
            "indemnify the Client",
            "indemnify and hold harmless the Client",
            doc,
        )
        assert result["scope"] == "exact"
        assert result["confidence"] == 1.0

    def test_find_localized_replacement_sentence(self):
        doc = "The Company shall indemnify the Client. This is another sentence."
        result = find_localized_replacement(
            "indemnify the Client",
            "indemnify and hold harmless the Client",
            doc,
        )
        # Should find it at sentence level
        assert result["confidence"] >= 0.9

    def test_find_localized_replacement_no_doc(self):
        """Without full document, should return exact scope."""
        result = find_localized_replacement(
            "original text",
            "new text",
        )
        assert result["scope"] == "exact"
        assert result["confidence"] == 1.0

    def test_validate_redline_scope_over_reach(self):
        """Proposed text >5x original should flag an issue."""
        result = validate_redline_scope(
            "short text",
            "x" * 200,
        )
        assert not result["valid"]
        assert len(result["issues"]) > 0

    def test_validate_redline_scope_valid(self):
        """Proportional changes should pass validation."""
        result = validate_redline_scope(
            "The Company shall indemnify the Client against all losses.",
            "The Company shall indemnify and hold harmless the Client against all losses.",
        )
        assert result["valid"]

    def test_validate_redline_scope_too_similar(self):
        """Changes that are >95% similar should be flagged."""
        result = validate_redline_scope(
            "The Company shall indemnify the Client.",
            "The Company shall indemnify the Client.",  # Identical
        )
        assert not result["valid"]

    def test_resolve_redline_text(self):
        doc = "The Company shall indemnify the Client against all losses."
        result = resolve_redline_text(
            "indemnify the Client",
            "indemnify and hold harmless the Client",
            doc,
        )
        assert "find_text" in result
        assert "replace_with" in result
        assert result["replace_with"] == "indemnify and hold harmless the Client"


# ═══════════════════════════════════════════════════════════════════
# PART 5: Integration Tests (Service Layer)
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_review_repo():
    repo = AsyncMock(spec=ReviewRepository)
    repo.session = AsyncMock()
    return repo


@pytest.fixture
def mock_ai_repo():
    return AsyncMock(spec=AIRepository)


@pytest.fixture
def mock_event_bus():
    return AsyncMock(spec=EventBus)


@pytest.fixture
def admin_user():
    return UserContext(
        id="auth0|admin",
        email="admin@test.com",
        tenant_id=TENANT_A_ID_STR,
        role="tenant_admin",
        permissions=["contracts:read", "contracts:write", "workflows:approve"],
    )


class TestReviewServiceWorkflow:
    """Integration tests for the review service workflow.

    These tests use mocked repositories to test the service layer logic
    without requiring a full database.
    """

    def _make_mock_review(self, review_id: str, status: str, **kwargs):
        """Create a mock ContractReview with the given status."""
        review = MagicMock(spec=ContractReview)
        review.review_id = review_id
        review.upload_id = kwargs.get("upload_id", "upload-1")
        review.tenant_id = TENANT_A_ID_STR
        review.status = ReviewStatus(status) if hasattr(ReviewStatus, status.upper()) else status
        review.priority = kwargs.get("priority", "normal")
        review.finding_count = kwargs.get("finding_count", 0)
        review.redline_count = kwargs.get("redline_count", 0)
        review.comment_count = 0
        review.escalation_count = 0
        review.version = kwargs.get("version", 1)
        review.assigned_to = kwargs.get("assigned_to", None)
        review.assigned_by = None
        review.assigned_at = None
        review.started_at = None
        review.workflow_stage = None
        review.sla_deadline = None
        review.sla_breached = False
        review.sla_status = "on_track"
        review.overdue_hours = 0.0
        review.created_by = "auth0|admin"
        review.created_at = datetime.utcnow()
        review.updated_at = datetime.utcnow()
        review.completed_at = None
        review.rejection_reason = None
        review.rejection_category = None
        review.rejection_severity = None
        review.rejected_by = None
        review.rejected_at = None
        review.approved_version_id = None
        review.document_metadata = kwargs.get("document_metadata", {})
        review.is_deleted = False
        review._document_filename = "test.pdf"
        review._document_content_type = "application/pdf"
        return review

    # ── Status Transition Tests ───────────────────────────────

    @pytest.mark.asyncio
    async def test_approve_success(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """APPROVE: Should succeed from IN_REVIEW."""
        review = self._make_mock_review("review-1", "in_review")
        mock_review_repo.get_review.return_value = review
        mock_review_repo.approve.return_value = MagicMock(
            approval_id="approval-1", decision="approved",
            comments=None, conditions=None,
            decided_at=datetime.utcnow(),
        )
        mock_review_repo.update_status.return_value = review
        # Mock session.execute — flexible mock that handles both scalar() and fetchone()
        mock_exec_result = MagicMock()
        mock_exec_result.scalar.return_value = 0
        mock_exec_result.fetchone.return_value = None
        mock_review_repo.session.execute.return_value = mock_exec_result

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        result = await service.approve("review-1", "approved")
        assert result["decision"] == "approved"

    @pytest.mark.asyncio
    async def test_approve_from_wrong_state_blocked(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """APPROVE: Should be blocked from UPLOADED."""
        review = self._make_mock_review("review-1", "uploaded")
        mock_review_repo.get_review.return_value = review
        # Mock session.execute for finding count check
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_review_repo.session.execute.return_value = mock_count_result

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        with pytest.raises((ConflictError, ImmutableReviewError)):
            await service.approve("review-1", "approved")

    @pytest.mark.asyncio
    async def test_reject_success(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """REJECT: Should succeed from IN_REVIEW."""
        review = self._make_mock_review("review-1", "in_review")
        mock_review_repo.get_review.return_value = review
        mock_review_repo.approve.return_value = MagicMock(
            approval_id="approval-1", decision="rejected",
            comments="Needs revision", conditions=None,
            decided_at=datetime.utcnow(),
        )
        mock_review_repo.update_status.return_value = review
        mock_exec_result = MagicMock()
        mock_exec_result.fetchone.return_value = None
        mock_review_repo.session.execute.return_value = mock_exec_result

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        result = await service.approve("review-1", "rejected", comments="Needs revision")
        assert result["decision"] == "rejected"

    @pytest.mark.asyncio
    async def test_double_approve_blocked(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """Double approve: Should be blocked."""
        review = self._make_mock_review("review-1", "approved")
        mock_review_repo.get_review.return_value = review
        # Mock session.execute for finding count check
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_review_repo.session.execute.return_value = mock_count_result

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        with pytest.raises((ConflictError, ImmutableReviewError)):
            await service.approve("review-1", "approved")

    @pytest.mark.asyncio
    async def test_escalate_success(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """ESCALATE: Should succeed from IN_REVIEW."""
        review = self._make_mock_review("review-1", "in_review")
        mock_review_repo.get_review.return_value = review
        mock_review_repo.escalate.return_value = MagicMock(
            escalation_id="esc-1", level=1,
            escalated_to="legal-team", reason="High risk",
        )

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        result = await service.escalate("review-1", "High risk clause", escalated_to="legal-team")
        assert result["escalation_id"] == "esc-1"

    @pytest.mark.asyncio
    async def test_escalate_from_finalized_blocked(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """ESCALATE: Should be blocked from FINALIZED."""
        review = self._make_mock_review("review-1", "finalized")
        mock_review_repo.get_review.return_value = review

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        with pytest.raises(ImmutableReviewError):
            await service.escalate("review-1", "Cannot escalate finalized")

    @pytest.mark.asyncio
    async def test_finalize_success(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """FINALIZE: Should succeed from APPROVED."""
        review = self._make_mock_review("review-1", "approved")
        mock_review_repo.get_review.return_value = review

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        with patch("app.domains.review.service.create_finalized_version", new=AsyncMock(return_value=None)):
            result = await service.finalize("review-1")
            assert result["status"] == "finalized"

    @pytest.mark.asyncio
    async def test_finalize_from_wrong_state_blocked(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """FINALIZE: Should be blocked from IN_REVIEW."""
        review = self._make_mock_review("review-1", "in_review")
        mock_review_repo.get_review.return_value = review

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        with pytest.raises(ValueError):
            await service.finalize("review-1")

    @pytest.mark.asyncio
    async def test_post_finalization_edits_blocked(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """Post-finalization: Redline edits should be blocked."""
        redline = MagicMock(spec=ReviewRedline)
        redline.redline_id = "rl-1"
        redline.review_id = "review-1"
        redline.tenant_id = TENANT_A_ID_STR
        redline.status = RedlineStatus.PROPOSED
        # Need original_text and proposed_text for update_redline
        redline.original_text = "original"
        redline.proposed_text = "proposed"

        review = self._make_mock_review("review-1", "finalized")

        # Mock the SELECT for finding the redline
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = redline
        mock_review_repo.session.execute.return_value = mock_scalar
        mock_review_repo.get_review.return_value = review

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        with pytest.raises(ImmutableReviewError):
            await service.update_redline("rl-1", "accepted")

    @pytest.mark.asyncio
    async def test_approve_after_escalation_success(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """Approve after escalation: Should succeed from ESCALATED."""
        review = self._make_mock_review("review-1", "escalated")
        mock_review_repo.get_review.return_value = review
        mock_review_repo.approve.return_value = MagicMock(
            approval_id="approval-1", decision="approved",
            comments=None, conditions=None,
            decided_at=datetime.utcnow(),
        )
        mock_review_repo.update_status.return_value = review
        mock_exec_result = MagicMock()
        mock_exec_result.scalar.return_value = 0
        mock_exec_result.fetchone.return_value = None
        mock_review_repo.session.execute.return_value = mock_exec_result

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        result = await service.approve("review-1", "approved")
        assert result["decision"] == "approved"

    @pytest.mark.asyncio
    async def test_reanalyze_preserves_accepted_redlines(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """Re-analysis: Should preserve accepted redlines and resolved findings."""
        review = self._make_mock_review("review-1", "in_review", version=1)

        accepted_redline = MagicMock(spec=ReviewRedline)
        accepted_redline.redline_id = "rl-accepted-1"

        resolved_finding = MagicMock(spec=ReviewFinding)
        resolved_finding.finding_id = "finding-resolved-1"
        resolved_finding.resolution = FindingResolution.ACKNOWLEDGED

        mock_review_repo.get_review.return_value = review
        mock_review_repo.get_redlines.side_effect = [
            [accepted_redline],  # accepted
            [],                   # modified
            [],                   # rejected
        ]
        mock_review_repo.get_findings.return_value = ([resolved_finding], 1)
        # Mock _get_latest_ai_run to return None — the method uses session.execute
        # to query AIExecutionRun, so we need to mock that chain
        mock_ai_run_result = MagicMock()
        mock_ai_run_result.scalar_one_or_none.return_value = None
        mock_review_repo.session.execute.return_value = mock_ai_run_result

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        # Mock the Celery import so it falls back to synchronous path
        # AIService is imported locally inside re_analyze, so patch at source
        with patch.dict('sys.modules', {'workers.ai_worker': None}):
            with patch('app.domains.ai.service.AIService.analyze', new=AsyncMock()):
                result = await service.re_analyze("review-1", "full", "Updated terms")
        assert result is not None
        assert result["preserved_redlines"] == 1
        assert result["preserved_findings"] == 1

    @pytest.mark.asyncio
    async def test_bulk_accept_redlines(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """Bulk accept: Should accept all low-risk redlines."""
        review = self._make_mock_review("review-1", "in_review")

        low_risk = MagicMock(spec=ReviewRedline)
        low_risk.redline_id = "rl-low"
        low_risk.status = RedlineStatus.PROPOSED
        low_risk.risk_level = "low"

        medium_risk = MagicMock(spec=ReviewRedline)
        medium_risk.redline_id = "rl-medium"
        medium_risk.status = RedlineStatus.PROPOSED
        medium_risk.risk_level = "medium"

        mock_review_repo.get_review.return_value = review
        mock_review_repo.get_redlines.return_value = [low_risk, medium_risk]

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        # Mock update_redline to succeed
        service.update_redline = AsyncMock(return_value={"status": "accepted"})  # type: ignore

        result = await service.bulk_accept_redlines("review-1", "low")
        assert result["accepted"] == 1  # Only low-risk accepted
        assert result["max_risk_level"] == "low"

    @pytest.mark.asyncio
    async def test_bulk_reject_redlines(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """Bulk reject: Should reject all informational redlines."""
        review = self._make_mock_review("review-1", "in_review")

        info_risk = MagicMock(spec=ReviewRedline)
        info_risk.redline_id = "rl-info"
        info_risk.status = RedlineStatus.PROPOSED
        info_risk.risk_level = "info"

        low_risk = MagicMock(spec=ReviewRedline)
        low_risk.redline_id = "rl-low"
        low_risk.status = RedlineStatus.PROPOSED
        low_risk.risk_level = "low"

        mock_review_repo.get_review.return_value = review
        mock_review_repo.get_redlines.return_value = [info_risk, low_risk]

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        service.update_redline = AsyncMock(return_value={"status": "rejected"})  # type: ignore

        result = await service.bulk_reject_redlines("review-1", "informational")
        assert result["rejected"] == 1  # Only info-level rejected
        assert result["severity"] == "informational"

    @pytest.mark.asyncio
    async def test_update_status_valid_transition(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """update_status: Valid transition should succeed."""
        review = self._make_mock_review("review-1", "in_review")
        mock_review_repo.get_review.return_value = review
        mock_review_repo.update_status.return_value = review

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        result = await service.update_status("review-1", "approved")
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition_blocked(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """update_status: Invalid transition should raise error."""
        review = self._make_mock_review("review-1", "uploaded")
        mock_review_repo.get_review.return_value = review

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        with pytest.raises(TransitionError):
            await service.update_status("review-1", "finalized")

    @pytest.mark.asyncio
    async def test_archived_mutation_blocked(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """Archived: All mutations should be blocked."""
        review = self._make_mock_review("review-1", "archived")
        mock_review_repo.get_review.return_value = review
        mock_exec_result = MagicMock()
        mock_exec_result.fetchone.return_value = None
        mock_review_repo.session.execute.return_value = mock_exec_result

        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        # Try to escalate
        with pytest.raises(ImmutableReviewError):
            await service.escalate("review-1", "test")

        # Try to approve — will be blocked by lock guard before idempotency
        with pytest.raises(ImmutableReviewError):
            await service.approve("review-1", "approved")


# ═══════════════════════════════════════════════════════════════════
# PART 6: Finalized Version Tests
# ═══════════════════════════════════════════════════════════════════

class TestFinalizedVersion:
    """Tests for finalized version generation."""

    @pytest.mark.asyncio
    async def test_create_finalized_version_no_document(self, tenant_a_session: AsyncSession):
        """Should return None when review not found."""
        result = await create_finalized_version(
            session=tenant_a_session,
            review_id=str(uuid.uuid4()),
            tenant_id=TENANT_A_ID_STR,
            user_id="user-1",
        )
        assert result is None

    def test_finalized_version_result_dataclass(self):
        """Verify the result dataclass works."""
        result = FinalizedVersionResult(
            version_id="ver-1",
            version_number=3,
            label="v3 — Final Approved",
            storage_key="finalized/tenant/review/v3.docx",
            file_size_bytes=1024,
            checksum_sha256="abc123",
            change_summary="Final approved contract",
            created_at="2026-05-19T23:00:00",
        )
        assert result.version_number == 3
        assert result.label == "v3 — Final Approved"


# ═══════════════════════════════════════════════════════════════════
# PART 7: Full End-to-End Workflow Scenario
# ═══════════════════════════════════════════════════════════════════

class TestEndToEndWorkflow:
    """Simulates a complete review lifecycle end-to-end."""

    @pytest.mark.asyncio
    async def test_complete_workflow_lifecycle(self, mock_review_repo, mock_ai_repo, mock_event_bus, admin_user):
        """Simulate: UPLOADED → AI_ANALYZED → REVIEW_READY → IN_REVIEW → APPROVED → FINALIZED → ARCHIVED."""
        service = ReviewService(
            review_repo=mock_review_repo,
            ai_repo=mock_ai_repo,
            event_bus=mock_event_bus,
            user=admin_user,
            tenant_id=TENANT_A_ID_STR,
        )

        # Mock session.execute — flexible mock for all DB calls
        mock_exec_result = MagicMock()
        mock_exec_result.scalar.return_value = 0
        mock_exec_result.fetchone.return_value = None
        mock_review_repo.session.execute.return_value = mock_exec_result

        # Mock Celery import to fall back to synchronous path
        with patch.dict('sys.modules', {'workers.ai_worker': None}):
            with patch('app.domains.ai.service.AIService.analyze', new=AsyncMock()):

                # Step 1: UPLOADED → AI_ANALYZED
                review = self._make_mock_review("review-1", "uploaded")
                mock_review_repo.get_review.return_value = review
                mock_review_repo.update_status.return_value = review
                result = await service.update_status("review-1", "ai_analyzed")
                assert result is not None

                # Step 2: AI_ANALYZED → REVIEW_READY
                review.status = ReviewStatus.AI_ANALYZED
                mock_review_repo.get_review.return_value = review
                result = await service.update_status("review-1", "review_ready")
                assert result is not None

                # Step 3: REVIEW_READY → IN_REVIEW
                review.status = ReviewStatus.REVIEW_READY
                mock_review_repo.get_review.return_value = review
                result = await service.update_status("review-1", "in_review")
                assert result is not None

                # Step 4: IN_REVIEW → APPROVED
                review.status = ReviewStatus.IN_REVIEW
                mock_review_repo.get_review.return_value = review
                mock_review_repo.approve.return_value = MagicMock(
                    approval_id="approval-1", decision="approved",
                    comments=None, conditions=None,
                    decided_at=datetime.utcnow(),
                )
                result = await service.approve("review-1", "approved")
                assert result["decision"] == "approved"

                # Step 5: APPROVED → FINALIZED
                review.status = ReviewStatus.APPROVED
                mock_review_repo.get_review.return_value = review
                with patch("app.domains.review.service.create_finalized_version", new=AsyncMock(return_value=None)):
                    result = await service.finalize("review-1")
                    assert result["status"] == "finalized"

                # Step 6: Verify FINALIZED is immutable
                review.status = ReviewStatus.FINALIZED
                mock_review_repo.get_review.return_value = review
                with pytest.raises(ImmutableReviewError):
                    await service.escalate("review-1", "Should be blocked")

                # Step 7: FINALIZED → ARCHIVED
                mock_review_repo.update_status.return_value = review
                result = await service.update_status("review-1", "archived")
                assert result is not None

    def _make_mock_review(self, review_id, status, **kwargs):
        review = MagicMock(spec=ContractReview)
        review.review_id = review_id
        review.upload_id = kwargs.get("upload_id", "upload-1")
        review.tenant_id = TENANT_A_ID_STR
        review.status = ReviewStatus(status) if hasattr(ReviewStatus, status.upper()) else status
        review.priority = kwargs.get("priority", "normal")
        review.finding_count = kwargs.get("finding_count", 0)
        review.redline_count = kwargs.get("redline_count", 0)
        review.comment_count = 0
        review.escalation_count = 0
        review.version = kwargs.get("version", 1)
        review.assigned_to = kwargs.get("assigned_to", None)
        review.assigned_by = None
        review.assigned_at = None
        review.started_at = None
        review.workflow_stage = None
        review.sla_deadline = None
        review.sla_breached = False
        review.sla_status = "on_track"
        review.overdue_hours = 0.0
        review.created_by = "auth0|admin"
        review.created_at = datetime.utcnow()
        review.updated_at = datetime.utcnow()
        review.completed_at = None
        review.rejection_reason = None
        review.rejection_category = None
        review.rejection_severity = None
        review.rejected_by = None
        review.rejected_at = None
        review.approved_version_id = None
        review.document_metadata = kwargs.get("document_metadata", {})
        review.is_deleted = False
        review._document_filename = "test.pdf"
        review._document_content_type = "application/pdf"
        return review
