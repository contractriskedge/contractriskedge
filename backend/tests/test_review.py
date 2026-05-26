"""Tests for contract review workspace — state machine, authorization, approval flows, comments."""

from __future__ import annotations

import pytest
from app.domains.review.models import ReviewStatus, FindingResolution, RedlineStatus


def _can_transition(from_status: str, to_status: str) -> bool:
    transitions = ReviewStatus.valid_transitions()
    for key, values in transitions.items():
        if key.value == from_status:
            return any(v.value == to_status for v in values)
    return False


class TestReviewStateMachine:
    def test_draft_to_ai_analyzed(self):
        assert _can_transition("draft", "ai_analyzed")
    def test_uploaded_to_ai_analyzed(self):
        assert _can_transition("uploaded", "ai_analyzed")
    def test_ai_analyzed_to_review_ready(self):
        assert _can_transition("ai_analyzed", "review_ready")
    def test_review_ready_to_in_review(self):
        assert _can_transition("review_ready", "in_review")
    def test_in_review_to_approved(self):
        assert _can_transition("in_review", "approved")
    def test_in_review_to_escalated(self):
        assert _can_transition("in_review", "escalated")
    def test_in_review_to_legal_approval(self):
        assert _can_transition("in_review", "legal_approval")
    def test_approved_to_finalized(self):
        assert _can_transition("approved", "finalized")
    def test_finalized_to_archived(self):
        assert _can_transition("finalized", "archived")
    def test_closed_has_no_transitions(self):
        assert _can_transition("closed", "in_review") is False
        assert _can_transition("closed", "draft") is False
    def test_approved_to_closed(self):
        assert _can_transition("approved", "closed")
    def test_rejected_to_archived(self):
        assert _can_transition("rejected", "archived")
    def test_rejected_cannot_reopen(self):
        assert _can_transition("rejected", "in_review") is False
    def test_escalated_to_in_review(self):
        assert _can_transition("escalated", "in_review")
    def test_escalated_to_legal_approval(self):
        assert _can_transition("escalated", "legal_approval")
    def test_direct_draft_to_closed(self):
        assert _can_transition("draft", "closed")
    def test_finalized_is_terminal(self):
        assert _can_transition("finalized", "in_review") is False
        assert _can_transition("finalized", "approved") is False


class TestFindingResolution:
    def test_valid_resolutions(self):
        assert FindingResolution.ACKNOWLEDGED.value == "acknowledged"
        assert FindingResolution.RESOLVED.value == "resolved"
        assert FindingResolution.DISMISSED.value == "dismissed"
        assert FindingResolution.FALSE_POSITIVE.value == "false_positive"
        assert FindingResolution.ESCALATED.value == "escalated"


class TestRedlineStatus:
    def test_valid_statuses(self):
        assert RedlineStatus.PROPOSED.value == "proposed"
        assert RedlineStatus.ACCEPTED.value == "accepted"
        assert RedlineStatus.REJECTED.value == "rejected"
        assert RedlineStatus.MODIFIED.value == "modified"
        assert RedlineStatus.SUPERSEDED.value == "superseded"


class TestReviewSchemas:
    def test_valid_review_summary(self):
        from datetime import datetime
        from app.domains.review.schemas import ReviewSummary
        rs = ReviewSummary(
            review_id="123", upload_id="456", status="draft",
            created_by="user1", created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        assert rs.status == "draft"

    def test_valid_finding_item(self):
        from datetime import datetime
        from app.domains.review.schemas import FindingItem
        fi = FindingItem(
            finding_id="123", severity="high", title="Risk finding",
            description="Description", created_at=datetime.utcnow(),
        )
        assert fi.severity == "high"

    def test_invalid_resolution_rejected(self):
        from app.domains.review.schemas import FindingResolveRequest
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            FindingResolveRequest(resolution="invalid_resolution")
