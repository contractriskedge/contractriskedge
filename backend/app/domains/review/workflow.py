"""Workflow State Machine — strict lifecycle enforcement for contract reviews.

Provides:
- Allowed transition matrix
- Transition validation
- Immutable audit logging
- Actor tracking
- Status-based permission guards
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class WorkflowState(str, enum.Enum):
    """Strict lifecycle states for a contract review.

    Enterprise flow:

    UPLOADED → ANALYZING → AI_REVIEWED → PROCUREMENT_REVIEW ─→ LEGAL_REVIEW ─→ APPROVED → FINALIZED → ARCHIVED
                   ↓                         ↓                    ↓                              ↓
              (analyze failed)          NEGOTIATION ←────── SECURITY_REVIEW                 EXECUTED
                                            ↓                    ↓
                                       (loop back to         ESCALATED → IN_REVIEW
                                        PROCUREMENT_REVIEW       ↓
                                        or LEGAL_REVIEW)     REJECTED → ARCHIVED

    REJECTED → ARCHIVED (from PROCUREMENT_REVIEW, SECURITY_REVIEW, LEGAL_REVIEW, NEGOTIATION, ESCALATED)
    """
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    AI_REVIEWED = "ai_reviewed"
    PROCUREMENT_REVIEW = "procurement_review"
    LEGAL_REVIEW = "legal_review"
    SECURITY_REVIEW = "security_review"
    NEGOTIATION = "negotiation"
    IN_REVIEW = "in_review"
    ESCALATED = "escalated"
    EXEC_APPROVAL = "exec_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FINALIZED = "finalized"
    EXECUTED = "executed"
    ARCHIVED = "archived"

    @classmethod
    def valid_transitions(cls) -> dict[WorkflowState, set[WorkflowState]]:
        """Centralized allowed transition matrix.

        Every valid state change MUST be defined here.
        Any transition not listed is automatically rejected.
        """
        return {
            cls.UPLOADED: {cls.ANALYZING, cls.ARCHIVED},
            cls.ANALYZING: {cls.AI_REVIEWED, cls.UPLOADED, cls.ARCHIVED},
            cls.AI_REVIEWED: {cls.PROCUREMENT_REVIEW, cls.LEGAL_REVIEW, cls.IN_REVIEW, cls.ARCHIVED},
            cls.PROCUREMENT_REVIEW: {
                cls.LEGAL_REVIEW, cls.SECURITY_REVIEW,
                cls.NEGOTIATION, cls.REJECTED, cls.ARCHIVED,
            },
            cls.LEGAL_REVIEW: {
                cls.EXEC_APPROVAL, cls.APPROVED, cls.NEGOTIATION, cls.REJECTED,
                cls.PROCUREMENT_REVIEW, cls.ESCALATED, cls.ARCHIVED,
            },
            cls.SECURITY_REVIEW: {
                cls.LEGAL_REVIEW, cls.NEGOTIATION, cls.REJECTED,
                cls.PROCUREMENT_REVIEW, cls.ESCALATED, cls.ARCHIVED,
            },
            cls.NEGOTIATION: {
                cls.PROCUREMENT_REVIEW, cls.LEGAL_REVIEW,
                cls.APPROVED, cls.REJECTED, cls.ARCHIVED,
            },
            cls.IN_REVIEW: {
                cls.PROCUREMENT_REVIEW, cls.LEGAL_REVIEW, cls.SECURITY_REVIEW,
                cls.LEGAL_REVIEW, cls.EXEC_APPROVAL,
                cls.APPROVED, cls.ESCALATED, cls.REJECTED, cls.ARCHIVED,
            },
            cls.ESCALATED: {
                cls.IN_REVIEW, cls.PROCUREMENT_REVIEW, cls.LEGAL_REVIEW,
                cls.SECURITY_REVIEW, cls.EXEC_APPROVAL,
                cls.APPROVED, cls.REJECTED, cls.ARCHIVED,
            },
            cls.EXEC_APPROVAL: {cls.APPROVED, cls.LEGAL_REVIEW, cls.IN_REVIEW, cls.REJECTED, cls.ARCHIVED},
            cls.APPROVED: {cls.FINALIZED, cls.EXECUTED, cls.ARCHIVED},
            cls.REJECTED: {cls.ARCHIVED},
            cls.FINALIZED: {cls.EXECUTED, cls.ARCHIVED},
            cls.EXECUTED: {cls.ARCHIVED},
            cls.ARCHIVED: set(),  # Terminal state — no transitions out
        }

    def can_transition_to(self, target: WorkflowState) -> bool:
        """Check if a transition is allowed by the state machine."""
        allowed = self.valid_transitions().get(self, set())
        return target in allowed

    def is_terminal(self) -> bool:
        """A terminal state has no outgoing transitions."""
        return len(self.valid_transitions().get(self, set())) == 0

    def is_immutable(self) -> bool:
        """States where the review content is locked (read-only)."""
        return self in (self.APPROVED, self.REJECTED, self.FINALIZED, self.EXECUTED, self.ARCHIVED)

    def is_mutable(self) -> bool:
        """States where review content can still be edited."""
        return not self.is_immutable()

    @classmethod
    def from_string(cls, value: str) -> WorkflowState:
        """Safely convert a string to a WorkflowState."""
        try:
            return cls(value)
        except ValueError:
            raise InvalidStateError(f"Unknown workflow state: {value}")


# ── Transition Record ──────────────────────────────────────────────


@dataclass
class TransitionRecord:
    """Immutable record of a single state transition."""
    review_id: str
    from_state: WorkflowState
    to_state: WorkflowState
    actor_id: str
    timestamp: datetime
    reason: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.from_state.can_transition_to(self.to_state)


# ── Transition Validation ─────────────────────────────────────────


class TransitionError(Exception):
    """Raised when a state transition is invalid."""
    def __init__(self, message: str, review_id: Optional[str] = None,
                 from_state: Optional[str] = None, to_state: Optional[str] = None):
        self.review_id = review_id
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(message)


class InvalidStateError(Exception):
    """Raised when a state value is not recognized."""
    pass


class ImmutableReviewError(Exception):
    """Raised when attempting to mutate a review in an immutable state."""
    def __init__(self, review_id: str, status: str, action: str):
        self.review_id = review_id
        self.status = status
        self.action = action
        super().__init__(
            f"Cannot {action}: review {review_id} is in '{status}' state (read-only). "
            f"Content is locked after approval, rejection, or finalization."
        )


def validate_transition(
    current_state: WorkflowState,
    target_state: WorkflowState,
    review_id: Optional[str] = None,
) -> TransitionRecord:
    """Validate and return a transition record.

    Raises TransitionError if the transition is not allowed.
    Returns a TransitionRecord (without actor/timestamp — caller fills those).
    """
    if not isinstance(current_state, WorkflowState):
        current_state = WorkflowState.from_string(str(current_state))
    if not isinstance(target_state, WorkflowState):
        target_state = WorkflowState.from_string(str(target_state))

    if not current_state.can_transition_to(target_state):
        raise TransitionError(
            message=(
                f"Invalid state transition: '{current_state.value}' → '{target_state.value}'. "
                f"Allowed transitions from '{current_state.value}': "
                f"{[s.value for s in current_state.valid_transitions().get(current_state, set())]}"
            ),
            review_id=review_id,
            from_state=current_state.value,
            to_state=target_state.value,
        )

    record = TransitionRecord(
        review_id=review_id or "",
        from_state=current_state,
        to_state=target_state,
        actor_id="",  # Caller must fill
        timestamp=datetime.utcnow(),
    )
    return record


def guard_mutable(review_status: str, action: str, review_id: str) -> None:
    """Raise ImmutableReviewError if the review is in a locked state.

    Call this before any mutation operation (redline edit, finding resolve,
    reassignment, etc.) to enforce read-only semantics on immutable states.
    """
    try:
        state = WorkflowState.from_string(review_status)
    except InvalidStateError:
        # If we don't recognize the state, allow the operation
        return

    if state.is_immutable():
        raise ImmutableReviewError(
            review_id=review_id,
            status=review_status,
            action=action,
        )


# ── Legacy Status Mapping ─────────────────────────────────────────

# Map legacy ReviewStatus values to the new WorkflowState
LEGACY_STATUS_MAP = {
    "draft": WorkflowState.UPLOADED,
    "uploaded": WorkflowState.UPLOADED,
    "analyzing": WorkflowState.ANALYZING,
    "ai_analyzed": WorkflowState.AI_REVIEWED,
    "ai_reviewed": WorkflowState.AI_REVIEWED,
    "review_ready": WorkflowState.AI_REVIEWED,
    "in_review": WorkflowState.IN_REVIEW,
    "changes_requested": WorkflowState.IN_REVIEW,
    "pending_approval": WorkflowState.IN_REVIEW,
    "procurement_review": WorkflowState.PROCUREMENT_REVIEW,
    "legal_review": WorkflowState.LEGAL_REVIEW,
    "legal_approval": WorkflowState.LEGAL_REVIEW,
    "security_review": WorkflowState.SECURITY_REVIEW,
    "negotiation": WorkflowState.NEGOTIATION,
    "escalated": WorkflowState.ESCALATED,
    "exec_approval": WorkflowState.EXEC_APPROVAL,
    "approved": WorkflowState.APPROVED,
    "rejected": WorkflowState.REJECTED,
    "finalized": WorkflowState.FINALIZED,
    "executed": WorkflowState.EXECUTED,
    "closed": WorkflowState.ARCHIVED,
    "archived": WorkflowState.ARCHIVED,
}

# Reverse map: WorkflowState → DB-persistable ReviewStatus string.
# Some WorkflowState values cannot be stored directly in the DB because:
#   - 'ai_reviewed' is not in the DB enum; use 'ai_analyzed' instead
#   - 'negotiation' is not in the DB enum; negotiation is tracked via
#     the separate negotiation_sessions table; persist as 'in_review'
WORKFLOW_TO_DB_STATUS = {
    WorkflowState.UPLOADED: "uploaded",
    WorkflowState.ANALYZING: "analyzing",
    WorkflowState.AI_REVIEWED: "ai_analyzed",       # mapped: ai_reviewed → ai_analyzed
    WorkflowState.PROCUREMENT_REVIEW: "procurement_review",
    WorkflowState.LEGAL_REVIEW: "legal_review",
    WorkflowState.SECURITY_REVIEW: "security_review",
    WorkflowState.NEGOTIATION: "in_review",          # mapped: negotiation → in_review
    WorkflowState.IN_REVIEW: "in_review",
    WorkflowState.ESCALATED: "escalated",
    WorkflowState.EXEC_APPROVAL: "exec_approval",
    WorkflowState.APPROVED: "approved",
    WorkflowState.REJECTED: "rejected",
    WorkflowState.FINALIZED: "finalized",
    WorkflowState.EXECUTED: "executed",
    WorkflowState.ARCHIVED: "archived",
}


def map_legacy_status(legacy_status: str) -> WorkflowState:
    """Map a legacy ReviewStatus string to the new WorkflowState."""
    return LEGACY_STATUS_MAP.get(legacy_status, WorkflowState.UPLOADED)


def to_db_status(workflow_state: WorkflowState) -> str:
    """Map a WorkflowState to a DB-persistable ReviewStatus string.

    This is the reverse of map_legacy_status(). It ensures that
    WorkflowState values not present in the PostgreSQL review_status
    enum are mapped to equivalent DB values before persistence.
    """
    return WORKFLOW_TO_DB_STATUS.get(workflow_state, workflow_state.value)
