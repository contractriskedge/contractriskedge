"""Contract Lifecycle Service — central state machine for contract status transitions.

All modules (review, negotiation, approval, signature, obligations) use this
service for status transitions, ensuring consistency across the application.

Status Flow:
```
Draft
  ↓
Uploaded → Analyzing → AI Analyzed → AI Reviewed → Review Ready
  ↓
Procurement Review → Legal Review → Security Review
  ↓
Negotiation
  ↓
Pending Approval → Legal Approval → Exec Approval
  ↓
Approved
  ↓
Preparing Signature
  ↓
Sent for Signature
  ↓
Partially Signed
  ↓
Executed
  ↓
Active
  ↓
Expired
```

Branches:
- Any review stage → Changes Requested → back to review
- Any stage → Escalated → back to previous stage
- Any stage → Rejected (terminal for rejected contracts)
- Approved → Rejected (if approval is overturned)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ContractStatus(str, Enum):
    """Complete set of contract lifecycle statuses."""
    # Upload & Analysis
    DRAFT = "draft"
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    AI_ANALYZED = "ai_analyzed"
    AI_REVIEWED = "ai_reviewed"
    REVIEW_READY = "review_ready"

    # Review Stages
    PROCUREMENT_REVIEW = "procurement_review"
    LEGAL_REVIEW = "legal_review"
    SECURITY_REVIEW = "security_review"

    # Negotiation
    NEGOTIATION = "negotiation"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"

    # Approval
    PENDING_APPROVAL = "pending_approval"
    LEGAL_APPROVAL = "legal_approval"
    EXEC_APPROVAL = "exec_approval"
    APPROVED = "approved"
    REJECTED = "rejected"

    # Signature (Sprint 30)
    PREPARING_SIGNATURE = "preparing_signature"
    SENT_FOR_SIGNATURE = "sent_for_signature"
    PARTIALLY_SIGNED = "partially_signed"

    # Post-Execution
    EXECUTED = "executed"
    FINALIZED = "finalized"
    ACTIVE = "active"
    EXPIRED = "expired"

    # Exception
    ESCALATED = "escalated"


# ── Transition Map ──────────────────────────────────────────────
# Defines all valid status transitions.
# Key: current status → list of valid next statuses

TRANSITION_MAP: dict[ContractStatus, list[ContractStatus]] = {
    # Upload & Analysis
    ContractStatus.DRAFT: [
        ContractStatus.UPLOADED, ContractStatus.REJECTED,
    ],
    ContractStatus.UPLOADED: [
        ContractStatus.ANALYZING, ContractStatus.REJECTED,
    ],
    ContractStatus.ANALYZING: [
        ContractStatus.AI_ANALYZED, ContractStatus.AI_REVIEWED,
        ContractStatus.REVIEW_READY, ContractStatus.REJECTED,
    ],
    ContractStatus.AI_ANALYZED: [
        ContractStatus.AI_REVIEWED, ContractStatus.REVIEW_READY,
        ContractStatus.REJECTED,
    ],
    ContractStatus.AI_REVIEWED: [
        ContractStatus.REVIEW_READY, ContractStatus.REJECTED,
    ],
    ContractStatus.REVIEW_READY: [
        ContractStatus.PROCUREMENT_REVIEW, ContractStatus.LEGAL_REVIEW,
        ContractStatus.SECURITY_REVIEW, ContractStatus.NEGOTIATION,
        ContractStatus.REJECTED,
    ],

    # Review Stages
    ContractStatus.PROCUREMENT_REVIEW: [
        ContractStatus.LEGAL_REVIEW, ContractStatus.SECURITY_REVIEW,
        ContractStatus.NEGOTIATION, ContractStatus.CHANGES_REQUESTED,
        ContractStatus.ESCALATED, ContractStatus.REJECTED,
    ],
    ContractStatus.LEGAL_REVIEW: [
        ContractStatus.SECURITY_REVIEW, ContractStatus.NEGOTIATION,
        ContractStatus.CHANGES_REQUESTED, ContractStatus.ESCALATED,
        ContractStatus.REJECTED,
    ],
    ContractStatus.SECURITY_REVIEW: [
        ContractStatus.NEGOTIATION, ContractStatus.CHANGES_REQUESTED,
        ContractStatus.ESCALATED, ContractStatus.REJECTED,
    ],

    # Negotiation
    ContractStatus.NEGOTIATION: [
        ContractStatus.IN_REVIEW, ContractStatus.PENDING_APPROVAL,
        ContractStatus.CHANGES_REQUESTED, ContractStatus.ESCALATED,
        ContractStatus.REJECTED,
    ],
    ContractStatus.IN_REVIEW: [
        ContractStatus.NEGOTIATION, ContractStatus.PENDING_APPROVAL,
        ContractStatus.CHANGES_REQUESTED, ContractStatus.ESCALATED,
        ContractStatus.REJECTED,
    ],
    ContractStatus.CHANGES_REQUESTED: [
        ContractStatus.PROCUREMENT_REVIEW, ContractStatus.LEGAL_REVIEW,
        ContractStatus.SECURITY_REVIEW, ContractStatus.NEGOTIATION,
        ContractStatus.ESCALATED, ContractStatus.REJECTED,
    ],

    # Approval
    ContractStatus.PENDING_APPROVAL: [
        ContractStatus.LEGAL_APPROVAL, ContractStatus.EXEC_APPROVAL,
        ContractStatus.APPROVED, ContractStatus.CHANGES_REQUESTED,
        ContractStatus.ESCALATED, ContractStatus.REJECTED,
    ],
    ContractStatus.LEGAL_APPROVAL: [
        ContractStatus.EXEC_APPROVAL, ContractStatus.APPROVED,
        ContractStatus.CHANGES_REQUESTED, ContractStatus.REJECTED,
    ],
    ContractStatus.EXEC_APPROVAL: [
        ContractStatus.APPROVED, ContractStatus.CHANGES_REQUESTED,
        ContractStatus.REJECTED,
    ],
    ContractStatus.APPROVED: [
        ContractStatus.PREPARING_SIGNATURE, ContractStatus.REJECTED,
        ContractStatus.NEGOTIATION,
    ],

    # Signature (Sprint 30)
    ContractStatus.PREPARING_SIGNATURE: [
        ContractStatus.SENT_FOR_SIGNATURE, ContractStatus.APPROVED,
        ContractStatus.REJECTED,
    ],
    ContractStatus.SENT_FOR_SIGNATURE: [
        ContractStatus.PARTIALLY_SIGNED, ContractStatus.EXECUTED,
        ContractStatus.REJECTED, ContractStatus.APPROVED,
    ],
    ContractStatus.PARTIALLY_SIGNED: [
        ContractStatus.EXECUTED, ContractStatus.SENT_FOR_SIGNATURE,
        ContractStatus.REJECTED,
    ],

    # Post-Execution
    ContractStatus.EXECUTED: [
        ContractStatus.FINALIZED, ContractStatus.ACTIVE,
    ],
    ContractStatus.FINALIZED: [
        ContractStatus.ACTIVE, ContractStatus.EXPIRED,
    ],
    ContractStatus.ACTIVE: [
        ContractStatus.EXPIRED, ContractStatus.NEGOTIATION,
    ],
    ContractStatus.EXPIRED: [
        ContractStatus.NEGOTIATION, ContractStatus.REJECTED,
    ],

    # Exception
    ContractStatus.ESCALATED: [
        ContractStatus.PROCUREMENT_REVIEW, ContractStatus.LEGAL_REVIEW,
        ContractStatus.SECURITY_REVIEW, ContractStatus.NEGOTIATION,
        ContractStatus.PENDING_APPROVAL, ContractStatus.REJECTED,
    ],

    # Terminal
    ContractStatus.REJECTED: [],
}


# ── Status Groups ───────────────────────────────────────────────

STATUS_GROUPS: dict[str, list[ContractStatus]] = {
    "upload": [
        ContractStatus.DRAFT, ContractStatus.UPLOADED,
        ContractStatus.ANALYZING, ContractStatus.AI_ANALYZED,
        ContractStatus.AI_REVIEWED, ContractStatus.REVIEW_READY,
    ],
    "review": [
        ContractStatus.PROCUREMENT_REVIEW, ContractStatus.LEGAL_REVIEW,
        ContractStatus.SECURITY_REVIEW,
    ],
    "negotiation": [
        ContractStatus.NEGOTIATION, ContractStatus.IN_REVIEW,
        ContractStatus.CHANGES_REQUESTED,
    ],
    "approval": [
        ContractStatus.PENDING_APPROVAL, ContractStatus.LEGAL_APPROVAL,
        ContractStatus.EXEC_APPROVAL, ContractStatus.APPROVED,
    ],
    "signature": [
        ContractStatus.PREPARING_SIGNATURE, ContractStatus.SENT_FOR_SIGNATURE,
        ContractStatus.PARTIALLY_SIGNED,
    ],
    "executed": [
        ContractStatus.EXECUTED, ContractStatus.FINALIZED,
        ContractStatus.ACTIVE, ContractStatus.EXPIRED,
    ],
    "exception": [
        ContractStatus.ESCALATED, ContractStatus.REJECTED,
    ],
}

# Statuses that are considered "active" (not terminal)
ACTIVE_STATUSES = [
    s for group in ["upload", "review", "negotiation", "approval", "signature"]
    for s in STATUS_GROUPS[group]
] + [ContractStatus.ESCALATED]

# Statuses that are considered "terminal"
TERMINAL_STATUSES = [
    ContractStatus.REJECTED, ContractStatus.EXPIRED,
]


class TransitionError(ValueError):
    """Raised when an invalid status transition is attempted."""
    pass


class ContractLifecycleService:
    """Central service for contract status transitions.

    All modules (review, negotiation, approval, signature) must use this
    service to transition contract status. This ensures consistency and
    provides a single audit trail for all status changes.
    """

    def __init__(self, review_service=None, notification_service=None):
        self._review_service = review_service
        self._notification_service = notification_service

    # ── Validation ──────────────────────────────────────────────

    def validate_transition(
        self, current_status: str, new_status: str
    ) -> ContractStatus:
        """Validate and return the target status enum.

        Raises TransitionError if the transition is not allowed.
        """
        try:
            current = ContractStatus(current_status)
            target = ContractStatus(new_status)
        except ValueError as e:
            raise TransitionError(f"Invalid status value: {e}")

        allowed = TRANSITION_MAP.get(current, [])
        if target not in allowed:
            raise TransitionError(
                f"Cannot transition from '{current.value}' to '{target.value}'. "
                f"Allowed transitions: {[s.value for s in allowed]}"
            )
        return target

    def can_transition(self, current_status: str, new_status: str) -> bool:
        """Check if a transition is valid without raising."""
        try:
            self.validate_transition(current_status, new_status)
            return True
        except TransitionError:
            return False

    def get_allowed_transitions(self, current_status: str) -> list[str]:
        """Get all valid next statuses for a given status."""
        try:
            current = ContractStatus(current_status)
            return [s.value for s in TRANSITION_MAP.get(current, [])]
        except ValueError:
            return []

    def is_active(self, status: str) -> bool:
        """Check if a status is considered 'active' (not terminal)."""
        try:
            return ContractStatus(status) in ACTIVE_STATUSES
        except ValueError:
            return False

    def is_terminal(self, status: str) -> bool:
        """Check if a status is terminal."""
        try:
            return ContractStatus(status) in TERMINAL_STATUSES
        except ValueError:
            return False

    def get_group(self, status: str) -> Optional[str]:
        """Get the group name for a status."""
        try:
            s = ContractStatus(status)
            for group, statuses in STATUS_GROUPS.items():
                if s in statuses:
                    return group
            return None
        except ValueError:
            return None

    # ── Transitions ─────────────────────────────────────────────

    async def transition_to(
        self,
        contract_id: str,
        new_status: str,
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Execute a status transition for a contract.

        This is the central method that ALL modules must call.
        It validates the transition, updates the contract, logs audit,
        and dispatches notifications.

        Returns the updated contract data.
        """
        review = await self._get_contract(contract_id)
        if not review:
            raise ValueError(f"Contract {contract_id} not found")

        current_status = self._get_status(review)
        target = self.validate_transition(current_status, new_status)

        # Execute the transition
        old_status = current_status
        await self._update_status(review, target.value, actor_id)

        # Log audit event
        await self._log_transition(
            contract_id=contract_id,
            from_status=old_status,
            to_status=target.value,
            actor_id=actor_id,
            reason=reason,
            metadata=metadata,
        )

        # Dispatch notifications
        await self._dispatch_notifications(
            contract_id=contract_id,
            old_status=old_status,
            new_status=target.value,
        )

        logger.info(
            "Contract %s transitioned: %s → %s (by %s)",
            contract_id, old_status, target.value, actor_id or "system",
        )

        return {
            "contract_id": contract_id,
            "from_status": old_status,
            "to_status": target.value,
            "allowed_transitions": self.get_allowed_transitions(target.value),
        }

    async def batch_transition(
        self,
        contract_ids: list[str],
        new_status: str,
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> list[dict]:
        """Execute the same transition for multiple contracts."""
        results = []
        for cid in contract_ids:
            try:
                result = await self.transition_to(
                    cid, new_status, actor_id=actor_id, reason=reason,
                )
                results.append(result)
            except (ValueError, TransitionError) as e:
                results.append({
                    "contract_id": cid,
                    "error": str(e),
                })
        return results

    # ── Integration Points ──────────────────────────────────────

    async def on_negotiation_complete(self, session_id: str) -> dict:
        """Called when negotiation is complete — moves to pending_approval."""
        # TODO: Look up contract from negotiation session
        # Then: transition_to(contract_id, "pending_approval")
        raise NotImplementedError("Negotiation → Approval integration not yet wired")

    async def on_approval_complete(self, contract_id: str) -> dict:
        """Called when approval is complete — moves to approved."""
        return await self.transition_to(
            contract_id, "approved",
            reason="All approvals received",
        )

    async def on_signature_request_created(self, contract_id: str) -> dict:
        """Called when signature request is created — moves to preparing_signature."""
        return await self.transition_to(
            contract_id, "preparing_signature",
            reason="Signature request created",
        )

    async def on_signature_sent(self, contract_id: str) -> dict:
        """Called when signature request is sent — moves to sent_for_signature."""
        return await self.transition_to(
            contract_id, "sent_for_signature",
            reason="Sent for signature",
        )

    async def on_signature_partial(self, contract_id: str) -> dict:
        """Called when some signers have signed — moves to partially_signed."""
        return await self.transition_to(
            contract_id, "partially_signed",
            reason="Some signers completed",
        )

    async def on_signature_complete(self, contract_id: str) -> dict:
        """Called when all signers have signed — moves to executed."""
        return await self.transition_to(
            contract_id, "executed",
            reason="All signatures received",
        )

    async def on_signature_declined(self, contract_id: str) -> dict:
        """Called when a signer declines — moves to rejected."""
        return await self.transition_to(
            contract_id, "rejected",
            reason="Signer declined",
        )

    async def on_contract_expired(self, contract_id: str) -> dict:
        """Called when a contract reaches its expiry date."""
        return await self.transition_to(
            contract_id, "expired",
            reason="Contract term expired",
        )

    # ── Internal Helpers ────────────────────────────────────────

    async def _get_contract(self, contract_id: str):
        """Get the contract/review by ID."""
        if self._review_service:
            return await self._review_service.get_review(contract_id)
        return None

    def _get_status(self, review) -> str:
        """Extract status from a review object."""
        if hasattr(review, "status"):
            val = review.status
            return val.value if isinstance(val, Enum) else str(val)
        if isinstance(review, dict):
            return str(review.get("status", "draft"))
        return "draft"

    async def _update_status(self, review, new_status: str, actor_id: Optional[str]) -> None:
        """Update the status on the review object."""
        if hasattr(review, "status"):
            review.status = new_status
        if self._review_service:
            await self._review_service.repo.session.flush()

    async def _log_transition(
        self,
        contract_id: str,
        from_status: str,
        to_status: str,
        actor_id: Optional[str],
        reason: Optional[str],
        metadata: Optional[dict],
    ) -> None:
        """Log the transition to the audit trail."""
        # TODO: Write to governance_audit_events table
        logger.debug(
            "Audit: contract %s %s → %s", contract_id, from_status, to_status,
        )

    async def _dispatch_notifications(
        self,
        contract_id: str,
        old_status: str,
        new_status: str,
    ) -> None:
        """Dispatch notifications for the transition."""
        if not self._notification_service:
            return

        notification_map = {
            "preparing_signature": "Contract ready for signature",
            "sent_for_signature": "Contract sent for signature",
            "partially_signed": "Some signers have completed",
            "executed": "Contract fully executed",
            "rejected": "Contract was rejected",
            "expired": "Contract has expired",
            "approved": "Contract approved",
        }

        title = notification_map.get(new_status)
        if title:
            await self._notification_service.send_notification(
                contract_id=contract_id,
                title=title,
                event_type=f"contract.{new_status}",
                metadata={"from_status": old_status, "to_status": new_status},
            )
