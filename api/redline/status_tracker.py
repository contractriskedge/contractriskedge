"""Accept/reject/modify tracking for redline suggestions.

Provides Pydantic models and an in-memory tracker for managing the
lifecycle of redline suggestions through review status changes.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .models import RedlineSuggestion

logger = logging.getLogger(__name__)


class RedlineStatus(str, Enum):
    """Possible statuses for a redline suggestion through its lifecycle."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    SUPERSEDED = "superseded"

    def __str__(self) -> str:
        return self.value


@dataclass
class StatusChangeEvent:
    """A single status change event in a suggestion's history."""

    from_status: Optional[RedlineStatus]
    to_status: RedlineStatus
    changed_by: str
    changed_at: datetime = field(default_factory=datetime.utcnow)
    comment: str = ""
    modified_text: Optional[str] = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class StatusSummary:
    """Summary of status distribution across suggestions."""

    total: int = 0
    pending: int = 0
    accepted: int = 0
    rejected: int = 0
    modified: int = 0
    superseded: int = 0

    @property
    def acceptance_rate(self) -> float:
        """Calculate the acceptance rate.

        Returns:
            Float between 0.0 and 1.0.
        """
        reviewed = self.accepted + self.rejected + self.modified
        if reviewed == 0:
            return 0.0
        return (self.accepted + self.modified) / reviewed

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict.

        Returns:
            Dict representation.
        """
        return {
            "total": self.total,
            "pending": self.pending,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "modified": self.modified,
            "superseded": self.superseded,
            "acceptance_rate": round(self.acceptance_rate, 4),
        }


class StatusTrackerError(Exception):
    """Raised when a status tracking operation fails."""

    def __init__(self, message: str, suggestion_id: Optional[str] = None) -> None:
        self.suggestion_id = suggestion_id
        super().__init__(message)


class StatusTracker:
    """Tracks accept/reject/modify status for redline suggestions.

    Maintains the status lifecycle of each suggestion with full
    audit history. Supports bulk operations and status summaries.

    Usage:
        tracker = StatusTracker()
        tracker.add_suggestion(suggestion)
        tracker.accept("sug-123", "user-456", "Looks good")
        tracker.reject("sug-789", "user-456", "Not applicable")
        summary = tracker.get_summary()
    """

    # Valid status transitions
    VALID_TRANSITIONS: Dict[RedlineStatus, List[RedlineStatus]] = {
        RedlineStatus.PENDING: [
            RedlineStatus.ACCEPTED,
            RedlineStatus.REJECTED,
            RedlineStatus.MODIFIED,
        ],
        RedlineStatus.ACCEPTED: [
            RedlineStatus.MODIFIED,
            RedlineStatus.SUPERSEDED,
        ],
        RedlineStatus.REJECTED: [
            RedlineStatus.PENDING,  # Reconsider
            RedlineStatus.SUPERSEDED,
        ],
        RedlineStatus.MODIFIED: [
            RedlineStatus.ACCEPTED,
            RedlineStatus.REJECTED,
            RedlineStatus.SUPERSEDED,
        ],
        RedlineStatus.SUPERSEDED: [],  # Terminal state
    }

    def __init__(self) -> None:
        """Initialize the status tracker."""
        self._suggestions: Dict[str, RedlineSuggestion] = {}
        self._history: Dict[str, List[StatusChangeEvent]] = {}

    def add_suggestion(self, suggestion: RedlineSuggestion) -> None:
        """Register a new suggestion for tracking.

        Args:
            suggestion: The RedlineSuggestion to track.

        Raises:
            StatusTrackerError: If the suggestion ID already exists.
        """
        if suggestion.suggestion_id in self._suggestions:
            raise StatusTrackerError(
                f"Suggestion {suggestion.suggestion_id} already exists",
                suggestion_id=suggestion.suggestion_id,
            )

        self._suggestions[suggestion.suggestion_id] = suggestion
        self._history[suggestion.suggestion_id] = []

        logger.info(
            "Tracking suggestion %s for contract %s",
            suggestion.suggestion_id,
            suggestion.contract_id,
        )

    def get_suggestion(self, suggestion_id: str) -> Optional[RedlineSuggestion]:
        """Get a suggestion by ID.

        Args:
            suggestion_id: The suggestion identifier.

        Returns:
            The RedlineSuggestion or None if not found.
        """
        return self._suggestions.get(suggestion_id)

    def _transition(
        self,
        suggestion_id: str,
        new_status: RedlineStatus,
        changed_by: str,
        comment: str = "",
        modified_text: Optional[str] = None,
    ) -> RedlineSuggestion:
        """Transition a suggestion to a new status.

        Args:
            suggestion_id: The suggestion to update.
            new_status: The target status.
            changed_by: User making the change.
            comment: Optional comment.
            modified_text: Optional modified text (for MODIFIED status).

        Returns:
            The updated RedlineSuggestion.

        Raises:
            StatusTrackerError: If transition is invalid or suggestion not found.
        """
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion is None:
            raise StatusTrackerError(
                f"Suggestion {suggestion_id} not found",
                suggestion_id=suggestion_id,
            )

        current_status = RedlineStatus(suggestion.status)
        allowed = self.VALID_TRANSITIONS.get(current_status, [])

        if new_status not in allowed:
            raise StatusTrackerError(
                f"Cannot transition from {current_status.value} to "
                f"{new_status.value}. Allowed: {[s.value for s in allowed]}",
                suggestion_id=suggestion_id,
            )

        # Record event
        event = StatusChangeEvent(
            from_status=current_status,
            to_status=new_status,
            changed_by=changed_by,
            comment=comment,
            modified_text=modified_text,
        )
        self._history.setdefault(suggestion_id, []).append(event)

        # Update suggestion
        suggestion.status = new_status.value
        suggestion.status_changed_at = event.changed_at
        suggestion.status_changed_by = changed_by

        if modified_text is not None and new_status == RedlineStatus.MODIFIED:
            # Store modified text in metadata
            suggestion.metadata["user_modified_text"] = modified_text

        logger.info(
            "Suggestion %s: %s -> %s by %s",
            suggestion_id,
            current_status.value,
            new_status.value,
            changed_by,
        )

        return suggestion

    def accept(
        self,
        suggestion_id: str,
        changed_by: str,
        comment: str = "",
    ) -> RedlineSuggestion:
        """Accept a suggestion.

        Args:
            suggestion_id: The suggestion to accept.
            changed_by: User accepting the suggestion.
            comment: Optional acceptance comment.

        Returns:
            The updated RedlineSuggestion.
        """
        return self._transition(
            suggestion_id=suggestion_id,
            new_status=RedlineStatus.ACCEPTED,
            changed_by=changed_by,
            comment=comment,
        )

    def reject(
        self,
        suggestion_id: str,
        changed_by: str,
        comment: str = "",
    ) -> RedlineSuggestion:
        """Reject a suggestion.

        Args:
            suggestion_id: The suggestion to reject.
            changed_by: User rejecting the suggestion.
            comment: Optional rejection reason.

        Returns:
            The updated RedlineSuggestion.
        """
        return self._transition(
            suggestion_id=suggestion_id,
            new_status=RedlineStatus.REJECTED,
            changed_by=changed_by,
            comment=comment,
        )

    def modify(
        self,
        suggestion_id: str,
        changed_by: str,
        modified_text: str,
        comment: str = "",
    ) -> RedlineSuggestion:
        """Mark a suggestion as modified with user's revised text.

        Args:
            suggestion_id: The suggestion to modify.
            changed_by: User modifying the suggestion.
            modified_text: The user's revised text.
            comment: Optional modification comment.

        Returns:
            The updated RedlineSuggestion.
        """
        return self._transition(
            suggestion_id=suggestion_id,
            new_status=RedlineStatus.MODIFIED,
            changed_by=changed_by,
            comment=comment,
            modified_text=modified_text,
        )

    def supersede(
        self,
        suggestion_id: str,
        changed_by: str,
        comment: str = "",
    ) -> RedlineSuggestion:
        """Mark a suggestion as superseded by a newer version.

        Args:
            suggestion_id: The suggestion to supersede.
            changed_by: User marking as superseded.
            comment: Optional explanation.

        Returns:
            The updated RedlineSuggestion.
        """
        return self._transition(
            suggestion_id=suggestion_id,
            new_status=RedlineStatus.SUPERSEDED,
            changed_by=changed_by,
            comment=comment,
        )

    def get_history(
        self, suggestion_id: str
    ) -> List[StatusChangeEvent]:
        """Get the full status change history for a suggestion.

        Args:
            suggestion_id: The suggestion to query.

        Returns:
            List of StatusChangeEvent objects in chronological order.
        """
        return list(self._history.get(suggestion_id, []))

    def get_suggestions_by_status(
        self, status: RedlineStatus
    ) -> List[RedlineSuggestion]:
        """Get all suggestions with a given status.

        Args:
            status: The status to filter by.

        Returns:
            List of matching RedlineSuggestion objects.
        """
        return [
            s for s in self._suggestions.values()
            if s.status == status.value
        ]

    def get_suggestions_by_contract(
        self, contract_id: str
    ) -> List[RedlineSuggestion]:
        """Get all suggestions for a given contract.

        Args:
            contract_id: The contract identifier.

        Returns:
            List of RedlineSuggestion objects for the contract.
        """
        return [
            s for s in self._suggestions.values()
            if s.contract_id == contract_id
        ]

    def get_summary(
        self, contract_id: Optional[str] = None
    ) -> StatusSummary:
        """Get a summary of status distribution.

        Args:
            contract_id: Optional contract filter.

        Returns:
            StatusSummary with counts.
        """
        suggestions = self._suggestions.values()
        if contract_id:
            suggestions = [
                s for s in suggestions if s.contract_id == contract_id
            ]

        summary = StatusSummary(total=len(suggestions))
        for s in suggestions:
            if s.status == RedlineStatus.PENDING.value:
                summary.pending += 1
            elif s.status == RedlineStatus.ACCEPTED.value:
                summary.accepted += 1
            elif s.status == RedlineStatus.REJECTED.value:
                summary.rejected += 1
            elif s.status == RedlineStatus.MODIFIED.value:
                summary.modified += 1
            elif s.status == RedlineStatus.SUPERSEDED.value:
                summary.superseded += 1

        return summary

    def remove_suggestion(self, suggestion_id: str) -> None:
        """Remove a suggestion from tracking.

        Args:
            suggestion_id: The suggestion to remove.

        Raises:
            StatusTrackerError: If suggestion not found.
        """
        if suggestion_id not in self._suggestions:
            raise StatusTrackerError(
                f"Suggestion {suggestion_id} not found",
                suggestion_id=suggestion_id,
            )
        del self._suggestions[suggestion_id]
        if suggestion_id in self._history:
            del self._history[suggestion_id]

    def to_json(self) -> str:
        """Serialize tracker state to JSON.

        Returns:
            JSON string of all suggestions and history.
        """
        data: Dict[str, Any] = {
            "suggestions": {
                sid: s.model_dump() for sid, s in self._suggestions.items()
            },
            "history": {
                sid: [
                    {
                        "event_id": e.event_id,
                        "from_status": e.from_status.value if e.from_status else None,
                        "to_status": e.to_status.value,
                        "changed_by": e.changed_by,
                        "changed_at": e.changed_at.isoformat(),
                        "comment": e.comment,
                        "has_modified_text": e.modified_text is not None,
                    }
                    for e in events
                ]
                for sid, events in self._history.items()
            },
        }
        return json.dumps(data, indent=2, default=str)
