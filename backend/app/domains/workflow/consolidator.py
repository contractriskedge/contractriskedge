"""Unified Workflow Consolidation Layer — bridges the Review domain state machine
and the Workflow Runtime Engine into a single canonical representation.

Architecture:
    ReviewService.update_status()  ──→  WorkflowConsolidator.transition()
                                              │
                                    ┌─────────┴──────────┐
                                    ▼                    ▼
                          ReviewDomainState      WorkflowRuntimeEngine
                          (existing, unchanged)  (existing, unchanged)
                                    │                    │
                                    ▼                    ▼
                            contract_reviews      workflow_instances
                            (status column)       (6 workflow tables)

Design Principles:
    1. Backward compatible — existing APIs continue to work unchanged
    2. No data migration — both persistence stores coexist
    3. Read the workflow_packs table — definitions are no longer hardcoded
    4. Synchronous for review transitions, async for background steps
    5. The Review domain remains the source of truth for review.status
    6. Workflow instances are created/updated as a shadow record

This module is the ONLY place that knows about both state machines.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.review.workflow import (
    WorkflowState as ReviewState,
    validate_transition as review_validate_transition,
    TransitionResult,
    map_legacy_status,
    to_db_status,
)
from app.domains.workflow.models import (
    WorkflowInstance,
    WorkflowInstanceStep,
    WorkflowExecutionLog,
    WorkflowPack,
    PackActivation,
)
from app.domains.workflow.engine import WorkflowStepStatus, WorkflowStatus

logger = logging.getLogger(__name__)


# ── Canonical Workflow Type ──────────────────────────────────────

class WorkflowType(str, Enum):
    """All workflow types the platform supports — single source of truth."""
    CONTRACT_REVIEW = "contract_review"
    PROCUREMENT_REVIEW = "procurement_review"
    NEGOTIATION = "negotiation_review"
    APPROVAL = "approval"
    SIGNATURE = "signature"
    OBLIGATION = "obligation"
    RENEWAL = "renewal"


# ── Review State → Canonical Mapping ─────────────────────────────

# Maps every ReviewState to a canonical stage name in the workflow definition.
# This is the BRIDGE between the two state machines.
REVIEW_STATE_TO_STAGE: dict[ReviewState, str] = {
    ReviewState.UPLOADED: "upload",
    ReviewState.ANALYZING: "ai_analysis",
    ReviewState.AI_REVIEWED: "ai_review_complete",
    ReviewState.PROCUREMENT_REVIEW: "procurement_review",
    ReviewState.LEGAL_REVIEW: "legal_review",
    ReviewState.SECURITY_REVIEW: "security_review",
    ReviewState.NEGOTIATION: "negotiation",
    ReviewState.IN_REVIEW: "in_review",
    ReviewState.ESCALATED: "escalated",
    ReviewState.EXEC_APPROVAL: "executive_approval",
    ReviewState.APPROVED: "approved",
    ReviewState.REJECTED: "rejected",
    ReviewState.FINALIZED: "finalized",
    ReviewState.EXECUTED: "executed",
    ReviewState.ARCHIVED: "archived",
}

STAGE_TO_REVIEW_STATE: dict[str, ReviewState] = {
    v: k for k, v in REVIEW_STATE_TO_STAGE.items()
}


# ── Workflow Pack Resolution ─────────────────────────────────────

async def resolve_workflow_pack(
    session: AsyncSession,
    tenant_id: str,
    contract_type: Optional[str] = None,
    business_unit: Optional[str] = None,
) -> Optional[WorkflowPack]:
    """Resolve the active workflow pack for a given context.

    Priority:
        1. Tenant-activated pack matching contract_type
        2. Tenant-activated pack with no type filter (default)
        3. Built-in pack matching contract_type
        4. Fall back to hardcoded definition (no pack)

    This is where contract_type → workflow_type routing happens.
    """
    from sqlalchemy import select, and_

    # 1. Look for tenant-activated packs
    stmt = (
        select(WorkflowPack)
        .join(PackActivation, PackActivation.pack_id == WorkflowPack.id)
        .where(
            PackActivation.tenant_id == tenant_id,
            PackActivation.is_active == True,
            WorkflowPack.is_built_in == True,
        )
        .order_by(WorkflowPack.created_at.desc())
    )
    result = await session.execute(stmt)
    packs = result.scalars().all()

    if not packs:
        return None

    # Try to find a pack matching the contract type
    if contract_type:
        for pack in packs:
            pack_type = getattr(pack, "workflow_type", None) or ""
            if contract_type.lower() in pack_type.lower():
                return pack

    # Return the first active pack as default
    return packs[0] if packs else None


# ── Workflow Consolidator ────────────────────────────────────────

class WorkflowConsolidator:
    """Consolidation layer that bridges Review domain transitions with the
    Workflow Runtime Engine.

    This is the ONLY component that knows about both state machines.
    It ensures every review status transition is reflected in the
    workflow_instances table while keeping the review's own status
    as the source of truth.

    Usage:
        consolidator = WorkflowConsolidator(session, tenant_id)
        await consolidator.record_transition(review_id, from_state, to_state)
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def ensure_workflow_instance(
        self,
        review_id: str,
        upload_id: str,
        workflow_type: str = "contract_review",
        contract_type: Optional[str] = None,
        business_unit: Optional[str] = None,
        title: Optional[str] = None,
        created_by: str = "system",
    ) -> WorkflowInstance:
        """Find or create a workflow instance for a review.

        Called once when the review is first created (UPLOADED state).
        Subsequent transitions use record_transition() instead.
        """
        from sqlalchemy import select

        # Check if instance already exists
        result = await self.session.execute(
            select(WorkflowInstance).where(
                WorkflowInstance.correlation_id == review_id,
                WorkflowInstance.tenant_id == self.tenant_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Resolve workflow pack
        pack = await resolve_workflow_pack(
            self.session, self.tenant_id, contract_type, business_unit,
        )

        # Create workflow instance as shadow record
        now = datetime.now(timezone.utc)
        instance = WorkflowInstance(
            tenant_id=self.tenant_id,
            pack_id=pack.id if pack else None,
            workflow_type=workflow_type,
            status=WorkflowStatus.RUNNING.value,
            current_step="upload",
            correlation_id=review_id,
            context={
                "review_id": review_id,
                "upload_id": upload_id,
                "contract_type": contract_type,
                "business_unit": business_unit,
                "title": title,
            },
            metadata={
                "source": "workflow_consolidator",
                "created_via": "review_create",
            },
            attempt_count=0,
            max_attempts=1,
            created_by=created_by,
            started_at=now,
        )
        self.session.add(instance)
        await self.session.flush()

        # Create initial step record
        step = WorkflowInstanceStep(
            instance_id=instance.id,
            tenant_id=self.tenant_id,
            step_name="upload",
            status=WorkflowStepStatus.COMPLETED.value,
            started_at=now,
            completed_at=now,
            result={"review_id": review_id, "status": "uploaded"},
        )
        self.session.add(step)
        await self.session.flush()

        # Record execution log entry (distinct from review audit trail)
        log = WorkflowExecutionLog(
            instance_id=instance.id,
            tenant_id=self.tenant_id,
            step_name="upload",
            event_type="lifecycle",
            severity="info",
            message=f"Workflow instance created for review {review_id[:12]}",
            metadata={
                "source": "workflow_consolidator",
                "review_id": review_id,
                "workflow_type": workflow_type,
                "action": "instance_created",
            },
        )
        self.session.add(log)
        await self.session.flush()

        logger.info(
            "Created workflow instance %s for review %s (type=%s)",
            instance.id[:12], review_id, workflow_type,
        )
        return instance

    async def record_transition(
        self,
        review_id: str,
        from_state: ReviewState,
        to_state: ReviewState,
        actor_id: str = "system",
        reason: Optional[str] = None,
    ) -> None:
        """Record a review state transition in the workflow instance.

        Called by ReviewService.update_status() AFTER it has:
        1. Validated the transition
        2. Updated contract_reviews.status
        3. Recorded the audit trail

        This method updates the shadow workflow instance to match.
        """
        from sqlalchemy import select

        # Find the workflow instance
        result = await self.session.execute(
            select(WorkflowInstance).where(
                WorkflowInstance.correlation_id == review_id,
                WorkflowInstance.tenant_id == self.tenant_id,
            )
        )
        instance = result.scalar_one_or_none()
        if not instance:
            logger.warning(
                "No workflow instance found for review %s — skipping shadow update",
                review_id,
            )
            return

        # Map to canonical stage names
        from_stage = REVIEW_STATE_TO_STAGE.get(from_state, from_state.value)
        to_stage = REVIEW_STATE_TO_STAGE.get(to_state, to_state.value)

        # Update instance
        now = datetime.now(timezone.utc)
        instance.current_step = to_stage
        instance.updated_at = now

        # Map terminal states
        if to_state in (ReviewState.ARCHIVED,):
            instance.status = WorkflowStatus.COMPLETED.value
            instance.completed_at = now
        elif to_state in (ReviewState.REJECTED,):
            instance.status = WorkflowStatus.FAILED.value
            instance.completed_at = now

        # Complete the previous step and create the next step
        prev_step_result = await self.session.execute(
            select(WorkflowInstanceStep).where(
                WorkflowInstanceStep.instance_id == instance.id,
                WorkflowInstanceStep.step_name == from_stage,
                WorkflowInstanceStep.tenant_id == self.tenant_id,
            )
        )
        prev_step = prev_step_result.scalar_one_or_none()
        if prev_step:
            prev_step.status = WorkflowStepStatus.COMPLETED.value
            prev_step.completed_at = now
            if reason:
                prev_step.result = {
                    **(prev_step.result or {}),
                    "completed_by": actor_id,
                    "reason": reason,
                }

        # Create next step (or mark complete for terminal states)
        if to_state not in (ReviewState.ARCHIVED, ReviewState.REJECTED):
            # Check if step already exists
            existing_step_result = await self.session.execute(
                select(WorkflowInstanceStep).where(
                    WorkflowInstanceStep.instance_id == instance.id,
                    WorkflowInstanceStep.step_name == to_stage,
                    WorkflowInstanceStep.tenant_id == self.tenant_id,
                )
            )
            if not existing_step_result.scalar_one_or_none():
                new_step = WorkflowInstanceStep(
                    instance_id=instance.id,
                    tenant_id=self.tenant_id,
                    step_name=to_stage,
                    status=WorkflowStepStatus.RUNNING.value,
                    started_at=now,
                    result={"entered_via": "review_transition", "actor_id": actor_id},
                )
                self.session.add(new_step)

        await self.session.flush()

        # Record execution log entry (distinct from review audit trail)
        log = WorkflowExecutionLog(
            instance_id=instance.id,
            tenant_id=self.tenant_id,
            step_name=to_stage,
            event_type="transition",
            severity="info",
            message=f"Review transition: {from_stage} → {to_stage}",
            metadata={
                "source": "workflow_consolidator",
                "review_id": review_id,
                "from_stage": from_stage,
                "to_stage": to_stage,
                "from_state": from_state.value,
                "to_state": to_state.value,
                "actor_id": actor_id,
                "reason": reason,
            },
        )
        self.session.add(log)
        await self.session.flush()

        logger.debug(
            "Shadow workflow %s updated: %s → %s",
            instance.id[:12], from_stage, to_stage,
        )

    async def get_workflow_status(
        self,
        review_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get the workflow status for a review.

        Returns consolidated status from both the review and workflow instance.
        """
        from sqlalchemy import select
        from app.domains.review.models import ContractReview

        # Get review
        review_result = await self.session.execute(
            select(ContractReview).where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == self.tenant_id,
            )
        )
        review = review_result.scalar_one_or_none()
        if not review:
            return None

        # Get workflow instance
        instance_result = await self.session.execute(
            select(WorkflowInstance).where(
                WorkflowInstance.correlation_id == review_id,
                WorkflowInstance.tenant_id == self.tenant_id,
            )
        )
        instance = instance_result.scalar_one_or_none()

        # Get steps
        steps = []
        if instance:
            steps_result = await self.session.execute(
                select(WorkflowInstanceStep).where(
                    WorkflowInstanceStep.instance_id == instance.id,
                    WorkflowInstanceStep.tenant_id == self.tenant_id,
                ).order_by(WorkflowInstanceStep.started_at)
            )
            steps = [
                {
                    "step_name": s.step_name,
                    "status": s.status,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                }
                for s in steps_result.scalars().all()
            ]

        return {
            "review_id": str(review.review_id),
            "review_status": review.status.value if hasattr(review.status, "value") else str(review.status),
            "workflow_instance_id": str(instance.id) if instance else None,
            "workflow_status": instance.status if instance else None,
            "current_step": instance.current_step if instance else None,
            "steps": steps,
            "consolidated": True,
        }
