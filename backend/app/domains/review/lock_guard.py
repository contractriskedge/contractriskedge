"""Review Lock Guard — enforces read-only mode after approval/rejection/finalization.

Provides middleware and decorator-style guards that prevent mutations on
reviews in immutable states.

Locked operations:
- Redline edits (accept/reject/modify)
- Finding resolution
- Reassignment
- Status transitions (except ARCHIVED)
- Escalation
- Comments (optional — can allow comments in locked state)
"""

from __future__ import annotations

from typing import Optional

from app.domains.review.workflow import (
    WorkflowState,
    guard_mutable,
    ImmutableReviewError,
    map_legacy_status,
)


# ── Public Guard Functions ────────────────────────────────────────


def assert_review_mutable(review_status: str, action: str, review_id: str) -> None:
    """Assert that a review is in a mutable state for the given action.

    Raises ImmutableReviewError if the review is locked.
    """
    guard_mutable(review_status=review_status, action=action, review_id=review_id)


def assert_can_transition(current_status: str, target_status: str, review_id: str) -> None:
    """Assert that a status transition is valid according to the state machine."""
    from app.domains.review.workflow import validate_transition, WorkflowState

    current = WorkflowState.from_string(current_status)
    target = WorkflowState.from_string(target_status)

    validate_transition(current, target, review_id=review_id)


def assert_can_edit_redlines(review_status: str, review_id: str) -> None:
    """Assert redlines can be edited in the current state."""
    assert_review_mutable(review_status, "edit redlines", review_id)


def assert_can_resolve_findings(review_status: str, review_id: str) -> None:
    """Assert findings can be resolved in the current state."""
    assert_review_mutable(review_status, "resolve findings", review_id)


def assert_can_reassign(review_status: str, review_id: str) -> None:
    """Assert the review can be reassigned in the current state."""
    assert_review_mutable(review_status, "reassign", review_id)


def assert_can_escalate(review_status: str, review_id: str) -> None:
    """Assert the review can be escalated in the current state."""
    assert_review_mutable(review_status, "escalate", review_id)


def assert_can_approve_or_reject(review_status: str, review_id: str) -> None:
    """Assert the review can be approved or rejected in the current state.

    Approval/rejection is only allowed from PROCUREMENT_REVIEW, LEGAL_REVIEW,
    SECURITY_REVIEW, NEGOTIATION, IN_REVIEW, and ESCALATED states.
    """
    state = map_legacy_status(review_status)
    allowed = {
        WorkflowState.PROCUREMENT_REVIEW, WorkflowState.LEGAL_REVIEW,
        WorkflowState.SECURITY_REVIEW, WorkflowState.NEGOTIATION,
        WorkflowState.IN_REVIEW, WorkflowState.ESCALATED,
        WorkflowState.EXEC_APPROVAL, WorkflowState.APPROVED,
    }
    if state not in allowed:
        raise ImmutableReviewError(
            review_id=review_id,
            status=review_status,
            action=f"approve/reject (only allowed from {[s.value for s in allowed]})",
        )


def locked_states_description() -> str:
    """Return a human-readable description of which states are locked."""
    immutable = [s.value for s in WorkflowState if s.is_immutable()]
    return (
        f"Reviews in the following states are locked (read-only): {', '.join(immutable)}. "
        f"No edits, redline changes, finding resolutions, reassignments, or escalations allowed."
    )
