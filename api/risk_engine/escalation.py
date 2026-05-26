"""Low-confidence escalation workflow and attorney review queue.

Provides escalation workflows for low-confidence risk flags, an attorney
review queue for human-in-the-loop validation, and endpoints for
managing the review lifecycle.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EscalationReason(str, Enum):
    """Reasons for escalating a risk flag."""

    LOW_CONFIDENCE = "low_confidence"
    HIGH_SEVERITY = "high_severity"
    AMBIGUOUS_CLAUSE = "ambiguous_clause"
    JURISDICTIONAL_COMPLEXITY = "jurisdictional_complexity"
    CROSS_CATEGORY = "cross_category"
    USER_REQUESTED = "user_requested"

    def __str__(self) -> str:
        return self.value


class EscalationStatus(str, Enum):
    """Status of an escalation item."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    REVIEWED = "reviewed"
    OVERRIDDEN = "overridden"
    DISMISSED = "dismissed"

    def __str__(self) -> str:
        return self.value


@dataclass
class EscalationItem:
    """An item in the escalation queue requiring attorney review."""

    escalation_id: str
    contract_id: str
    clause_text: str
    risk_category: str
    severity_score: int
    confidence_score: float
    escalation_reason: EscalationReason
    status: EscalationStatus
    ai_rationale: str
    created_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    override_score: Optional[int] = None
    tenant_id: str = "default"


class EscalationWorkflow:
    """Manages escalation of low-confidence risk flags for attorney review.

    Provides:
    1. Automatic escalation of low-confidence or high-severity flags.
    2. Attorney review queue with status tracking.
    3. Review submission with override capability.
    4. Integration with confidence calibration engine.

    Usage:
        workflow = EscalationWorkflow()
        item = workflow.create_escalation(
            contract_id="c0001",
            clause_text="...",
            risk_category="indemnification",
            severity_score=8,
            confidence_score=0.25,
            reason=EscalationReason.LOW_CONFIDENCE,
            ai_rationale="...",
        )
        pending = workflow.get_pending_escalations()
        workflow.review_escalation(
            escalation_id=item.escalation_id,
            reviewed_by="attorney@firm.com",
            status=EscalationStatus.REVIEWED,
            comment="Confirmed - high risk",
            override_score=9,
        )
    """

    def __init__(self) -> None:
        """Initialize the escalation workflow."""
        self._escalations: Dict[str, EscalationItem] = {}
        self._auto_escalate_confidence_threshold: float = 0.4
        self._auto_escalate_severity_threshold: int = 8

    def should_escalate(
        self,
        confidence_score: float,
        severity_score: int,
    ) -> Optional[EscalationReason]:
        """Determine if a risk flag should be escalated.

        Args:
            confidence_score: The confidence score (0.0-1.0).
            severity_score: The severity score (1-10).

        Returns:
            EscalationReason if escalation needed, None otherwise.
        """
        if confidence_score < self._auto_escalate_confidence_threshold:
            return EscalationReason.LOW_CONFIDENCE

        if severity_score >= self._auto_escalate_severity_threshold:
            return EscalationReason.HIGH_SEVERITY

        return None

    def create_escalation(
        self,
        contract_id: str,
        clause_text: str,
        risk_category: str,
        severity_score: int,
        confidence_score: float,
        escalation_reason: EscalationReason,
        ai_rationale: str,
        tenant_id: str = "default",
    ) -> EscalationItem:
        """Create a new escalation item for attorney review.

        Args:
            contract_id: The contract identifier.
            clause_text: The clause text that was flagged.
            risk_category: The risk category.
            severity_score: The severity score (1-10).
            confidence_score: The confidence score (0.0-1.0).
            escalation_reason: Why this was escalated.
            ai_rationale: The AI-generated rationale.
            tenant_id: Tenant identifier.

        Returns:
            The created EscalationItem.
        """
        item = EscalationItem(
            escalation_id=str(uuid.uuid4()),
            contract_id=contract_id,
            clause_text=clause_text[:1000],
            risk_category=risk_category,
            severity_score=severity_score,
            confidence_score=confidence_score,
            escalation_reason=escalation_reason,
            status=EscalationStatus.PENDING,
            ai_rationale=ai_rationale[:2000],
            created_at=datetime.utcnow(),
            tenant_id=tenant_id,
        )
        self._escalations[item.escalation_id] = item
        logger.info(
            "Escalation created: id=%s, reason=%s, confidence=%.3f, severity=%d",
            item.escalation_id,
            escalation_reason.value,
            confidence_score,
            severity_score,
        )
        return item

    def get_pending_escalations(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[EscalationItem]:
        """Get all pending escalation items.

        Args:
            tenant_id: Optional tenant filter.
            limit: Maximum items to return.

        Returns:
            List of pending EscalationItems.
        """
        items = [
            e
            for e in self._escalations.values()
            if e.status in (EscalationStatus.PENDING, EscalationStatus.IN_REVIEW)
            and (tenant_id is None or e.tenant_id == tenant_id)
        ]
        items.sort(key=lambda e: e.created_at, reverse=True)
        return items[:limit]

    def get_escalation_by_id(
        self,
        escalation_id: str,
    ) -> Optional[EscalationItem]:
        """Get an escalation item by ID.

        Args:
            escalation_id: The escalation identifier.

        Returns:
            EscalationItem if found, None otherwise.
        """
        return self._escalations.get(escalation_id)

    def review_escalation(
        self,
        escalation_id: str,
        reviewed_by: str,
        status: EscalationStatus,
        comment: Optional[str] = None,
        override_score: Optional[int] = None,
    ) -> Optional[EscalationItem]:
        """Submit a review for an escalation item.

        Args:
            escalation_id: The escalation to review.
            reviewed_by: Who performed the review.
            status: New status (REVIEWED, OVERRIDDEN, DISMISSED).
            comment: Optional review comment.
            override_score: Optional severity score override.

        Returns:
            Updated EscalationItem if found, None otherwise.
        """
        item = self._escalations.get(escalation_id)
        if item is None:
            logger.warning("Escalation not found for review: %s", escalation_id)
            return None

        item.status = status
        item.reviewed_by = reviewed_by
        item.reviewed_at = datetime.utcnow()
        item.review_comment = comment
        item.override_score = override_score

        logger.info(
            "Escalation reviewed: id=%s, status=%s, reviewer=%s, override=%s",
            escalation_id,
            status.value,
            reviewed_by,
            override_score,
        )
        return item

    def get_statistics(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get escalation queue statistics.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            Dict with queue statistics.
        """
        items = list(self._escalations.values())
        if tenant_id:
            items = [e for e in items if e.tenant_id == tenant_id]

        total = len(items)
        pending = sum(
            1 for e in items if e.status == EscalationStatus.PENDING
        )
        in_review = sum(
            1 for e in items if e.status == EscalationStatus.IN_REVIEW
        )
        reviewed = sum(
            1 for e in items if e.status == EscalationStatus.REVIEWED
        )
        overridden = sum(
            1 for e in items if e.status == EscalationStatus.OVERRIDDEN
        )
        dismissed = sum(
            1 for e in items if e.status == EscalationStatus.DISMISSED
        )

        reasons: Dict[str, int] = {}
        for e in items:
            reasons[e.escalation_reason.value] = (
                reasons.get(e.escalation_reason.value, 0) + 1
            )

        return {
            "total": total,
            "pending": pending,
            "in_review": in_review,
            "reviewed": reviewed,
            "overridden": overridden,
            "dismissed": dismissed,
            "by_reason": reasons,
            "auto_escalate_confidence_threshold": self._auto_escalate_confidence_threshold,
            "auto_escalate_severity_threshold": self._auto_escalate_severity_threshold,
        }

    def update_thresholds(
        self,
        confidence_threshold: Optional[float] = None,
        severity_threshold: Optional[int] = None,
    ) -> None:
        """Update auto-escalation thresholds.

        Args:
            confidence_threshold: New confidence threshold (0.0-1.0).
            severity_threshold: New severity threshold (1-10).
        """
        if confidence_threshold is not None:
            self._auto_escalate_confidence_threshold = max(
                0.0, min(1.0, confidence_threshold)
            )
        if severity_threshold is not None:
            self._auto_escalate_severity_threshold = max(
                1, min(10, severity_threshold)
            )
        logger.info(
            "Escalation thresholds updated: confidence=%.2f, severity=%d",
            self._auto_escalate_confidence_threshold,
            self._auto_escalate_severity_threshold,
        )
