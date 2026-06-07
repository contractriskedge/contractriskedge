"""Enterprise Audit Trail — records every review action with before/after state.

Every mutation must go through this service to ensure:
- who did what
- when it happened
- what the before/after state was
- correlation ID for tracing
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, func, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _safe_uuid(value: Any) -> Any:
    """Convert a string to UUID if valid, otherwise return as-is.

    The governance_audit_events.entity_id column is UUID, but some callers
    may pass non-UUID identifiers (e.g. "review-1" in tests).  This helper
    prevents hard crashes while preserving the intent.
    """
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return str(value)


@dataclass
class AuditEntry:
    """An immutable audit record for a single action."""
    tenant_id: str
    event_type: str  # e.g., 'redline.accepted', 'review.approved', 'finding.resolved'
    entity_type: str  # 'review', 'finding', 'redline', 'comment', 'version'
    entity_id: str
    actor_id: str
    action: str  # 'create', 'update', 'transition', 'delete', 'resolve', 'escalate'
    before_state: Optional[dict[str, Any]] = None
    after_state: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)


class AuditTrailService:
    """Enterprise audit trail for the review domain.

    Writes to the governance_audit_events table.
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def record(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor_id: str,
        action: str,
        before_state: Optional[dict[str, Any]] = None,
        after_state: Optional[dict[str, Any]] = None,
        description: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record an audit event.

        This is fire-and-forget — failures are logged but not propagated
        to avoid breaking the calling operation.
        """
        try:
            from sqlalchemy import text as sa_text

            stmt = sa_text("""
                INSERT INTO governance_audit_events (
                    event_id, tenant_id, event_type, entity_type, entity_id,
                    actor_id, actor_role, previous_state, new_state,
                    change_summary, correlation_id, source, metadata, created_at
                ) VALUES (
                    :event_id, :tenant_id, :event_type, :entity_type, :entity_id,
                    :actor_id, :actor_role, :previous_state, :new_state,
                    :change_summary, :correlation_id, :source, :metadata, NOW()
                )
            """)

            await self.session.execute(stmt, {
                "event_id": uuid.uuid4(),
                "tenant_id": uuid.UUID(str(self.tenant_id)),
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": _safe_uuid(entity_id),
                "actor_id": actor_id,
                "actor_role": None,
                "previous_state": json.dumps(before_state) if before_state else None,
                "new_state": json.dumps(after_state) if after_state else None,
                "change_summary": description,
                "correlation_id": correlation_id,
                "source": "review_service",
                "metadata": json.dumps(metadata or {}),
            })
            await self.session.flush()
        except Exception as exc:
            logger.error(
                "Failed to record audit event %s/%s: %s",
                event_type, entity_id, exc, exc_info=True,
            )

    async def record_ai_suggestion(
        self,
        review_id: str,
        actor_id: str,
        suggestion_ids: list[str],
        prompt: str,
        correlation_id: str,
    ) -> None:
        """Record an AI Copilot suggestion event with traceability metadata."""
        await self.record(
            event_type="ai.copilot.suggest",
            entity_type="review",
            entity_id=review_id,
            actor_id=actor_id,
            action="suggest",
            before_state={"prompt": prompt},
            after_state={"suggestion_ids": suggestion_ids},
            description="AI Copilot suggestions generated for review.",
            correlation_id=correlation_id,
            metadata={"source": "review_copilot"},
        )

    async def record_ai_feedback(
        self,
        review_id: str,
        actor_id: str,
        suggestion_id: str,
        helpful: bool,
        feedback: Optional[str],
        correlation_id: str,
    ) -> None:
        """Record reviewer feedback on an AI Copilot suggestion."""
        await self.record(
            event_type="ai.copilot.feedback",
            entity_type="review",
            entity_id=review_id,
            actor_id=actor_id,
            action="feedback",
            before_state={"suggestion_id": suggestion_id, "helpful": helpful},
            after_state={"feedback": feedback, "helpful": helpful},
            description="Reviewer submitted feedback for AI Copilot suggestion.",
            correlation_id=correlation_id,
            metadata={"suggestion_id": suggestion_id},
        )

    async def record_transition(
        self,
        review_id: str,
        from_status: str,
        to_status: str,
        actor_id: str,
        reason: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Convenience method for recording a status transition."""
        await self.record(
            event_type="review.status_transition",
            entity_type="review",
            entity_id=review_id,
            actor_id=actor_id,
            action="transition",
            before_state={"status": from_status},
            after_state={"status": to_status},
            description=reason or f"Transition from {from_status} to {to_status}",
            correlation_id=correlation_id,
            metadata={
                "from_status": from_status,
                "to_status": to_status,
                "reason": reason,
            },
        )

    async def record_assignment(
        self,
        review_id: str,
        assignee_id: str,
        assigned_by: str,
        role: str = "reviewer",
        previous_assignee: Optional[str] = None,
    ) -> None:
        """Record a reviewer assignment event."""
        await self.record(
            event_type="review.assigned",
            entity_type="review",
            entity_id=review_id,
            actor_id=assigned_by,
            action="assigned",
            before_state={"assignee": previous_assignee} if previous_assignee else None,
            after_state={"assignee": assignee_id, "role": role},
            description=f"Assigned {assignee_id} as {role}",
            metadata={
                "assignee_id": assignee_id,
                "role": role,
                "previous_assignee": previous_assignee,
            },
        )

    async def record_redline_action(
        self,
        redline_id: str,
        review_id: str,
        actor_id: str,
        action: str,
        before_status: str,
        after_status: str,
        description: Optional[str] = None,
    ) -> None:
        """Record a redline action (accept/reject/modify)."""
        await self.record(
            event_type=f"redline.{action}",
            entity_type="redline",
            entity_id=redline_id,
            actor_id=actor_id,
            action=action,
            before_state={"redline_id": redline_id, "status": before_status},
            after_state={"redline_id": redline_id, "status": after_status},
            description=description or f"Redline {action}: {before_status} → {after_status}",
            metadata={"review_id": review_id},
        )

    async def record_finding_action(
        self,
        finding_id: str,
        review_id: str,
        actor_id: str,
        resolution: str,
        before_resolution: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Record a finding resolution action."""
        await self.record(
            event_type="finding.resolved",
            entity_type="finding",
            entity_id=finding_id,
            actor_id=actor_id,
            action="resolve",
            before_state={"resolution": before_resolution} if before_resolution else None,
            after_state={"resolution": resolution},
            description=description or f"Finding resolved as {resolution}",
            metadata={"review_id": review_id, "resolution": resolution},
        )

    async def record_approval_action(
        self,
        review_id: str,
        actor_id: str,
        decision: str,
        conditions: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> None:
        """Record an approval/rejection decision."""
        await self.record(
            event_type=f"review.{decision}",
            entity_type="review",
            entity_id=review_id,
            actor_id=actor_id,
            action=decision,
            after_state={"decision": decision, "conditions": conditions},
            description=description or f"Review {decision} by {actor_id}",
            metadata={"decision": decision, "conditions": conditions},
        )

    async def record_escalation(
        self,
        review_id: str,
        actor_id: str,
        escalated_to: Optional[str],
        reason: str,
        target_stage: Optional[str] = None,
    ) -> None:
        """Record an escalation."""
        await self.record(
            event_type="review.escalated",
            entity_type="review",
            entity_id=review_id,
            actor_id=actor_id,
            action="escalate",
            after_state={"escalated_to": escalated_to, "target_stage": target_stage},
            description=reason,
            metadata={
                "escalated_to": escalated_to,
                "target_stage": target_stage,
                "reason": reason,
            },
        )

    async def record_decision_impact(
        self,
        review_id: str,
        finding_id: str,
        actor_id: str,
        decision_type: str,
        previous_state: str,
        new_state: str,
        delta_amount: float = 0.0,
        delta_pct: float = 0.0,
        review_status: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Record a review decision impact — links finding resolution to risk delta.

        This creates a cross-session traceable timeline of decisions and their
        risk impact, enabling the risk delta timeline and version impact views.
        """
        await self.record(
            event_type="review.decision_impact",
            entity_type="finding",
            entity_id=finding_id,
            actor_id=actor_id,
            action="resolve",
            before_state={
                "finding_id": finding_id,
                "resolution": previous_state,
                "review_id": review_id,
            },
            after_state={
                "finding_id": finding_id,
                "resolution": new_state,
                "delta_amount": delta_amount,
                "delta_pct": delta_pct,
                "review_status": review_status,
            },
            description=description or f"Decision impact: {previous_state} → {new_state} (Δ={delta_amount:+.4f})",
            metadata={
                "review_id": review_id,
                "decision_type": decision_type,
                "previous_state": previous_state,
                "new_state": new_state,
                "delta_amount": delta_amount,
                "delta_pct": delta_pct,
                "review_status": review_status,
            },
        )

    async def record_version_action(
        self,
        version_id: str,
        review_id: str,
        actor_id: str,
        action: str,
        version_number: int,
        description: Optional[str] = None,
    ) -> None:
        """Record a document version action (create/finalize)."""
        await self.record(
            event_type=f"version.{action}",
            entity_type="version",
            entity_id=version_id,
            actor_id=actor_id,
            action=action,
            description=description or f"Version v{version_number} {action}",
            metadata={
                "review_id": review_id,
                "version_number": version_number,
            },
        )
