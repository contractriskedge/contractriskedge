"""Workflow ORM repository — typed CRUD for workflow models.

Replaces raw SQL in WorkflowPackService with proper SQLAlchemy ORM queries.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, delete, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.workflow_packs.models import (
    PackActivation,
    WorkflowExecutionLog,
    WorkflowInstance,
    WorkflowInstanceStep,
    WorkflowPack,
    WorkflowStatus,
    WorkflowStepStatus,
    WorkflowVersion,
)

logger = logging.getLogger(__name__)


class WorkflowRepository:
    """Typed ORM repository for all workflow operations."""

    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    # ── Workflow Packs ───────────────────────────────────────────

    async def list_packs(
        self,
        category: Optional[str] = None,
        include_builtin: bool = True,
        tenant_only: bool = False,
    ) -> list[WorkflowPack]:
        """List tenant-created workflow packs from DB."""
        query = select(WorkflowPack).where(
            WorkflowPack.tenant_id == self.tenant_id
        )
        if category:
            query = query.where(WorkflowPack.category == category)
        query = query.order_by(WorkflowPack.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pack(self, pack_id: str) -> Optional[WorkflowPack]:
        """Get a workflow pack by ID."""
        query = select(WorkflowPack).where(
            and_(
                WorkflowPack.pack_id == pack_id,
                WorkflowPack.tenant_id == self.tenant_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_pack(self, pack: WorkflowPack) -> WorkflowPack:
        """Create a new workflow pack."""
        self.session.add(pack)
        await self.session.flush()
        return pack

    async def update_pack(self, pack_id: str, **kwargs: Any) -> Optional[WorkflowPack]:
        """Update a workflow pack."""
        kwargs["updated_at"] = datetime.now(timezone.utc)
        query = (
            update(WorkflowPack)
            .where(
                and_(
                    WorkflowPack.pack_id == pack_id,
                    WorkflowPack.tenant_id == self.tenant_id,
                )
            )
            .values(**kwargs)
            .returning(WorkflowPack)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete_pack(self, pack_id: str) -> bool:
        """Delete a workflow pack."""
        query = delete(WorkflowPack).where(
            and_(
                WorkflowPack.pack_id == pack_id,
                WorkflowPack.tenant_id == self.tenant_id,
            )
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount > 0

    async def increment_usage(self, pack_id: str) -> None:
        """Increment the usage count for a pack."""
        query = (
            update(WorkflowPack)
            .where(WorkflowPack.pack_id == pack_id)
            .values(usage_count=WorkflowPack.usage_count + 1, updated_at=datetime.now(timezone.utc))
        )
        await self.session.execute(query)
        await self.session.flush()

    # ── Pack Activations ─────────────────────────────────────────

    async def get_active_activations(self) -> list[PackActivation]:
        """Get all active pack activations for the tenant."""
        query = select(PackActivation).where(
            and_(
                PackActivation.tenant_id == self.tenant_id,
                PackActivation.is_active == True,
            )
        ).order_by(PackActivation.activated_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_activation(
        self, pack_id: str, business_unit: Optional[str] = None
    ) -> Optional[PackActivation]:
        """Get an active activation for a specific pack."""
        conditions = [
            PackActivation.pack_id == pack_id,
            PackActivation.tenant_id == self.tenant_id,
            PackActivation.is_active == True,
        ]
        if business_unit:
            conditions.append(PackActivation.business_unit == business_unit)
        query = select(PackActivation).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_activation(self, activation: PackActivation) -> PackActivation:
        """Create a pack activation."""
        self.session.add(activation)
        await self.session.flush()
        return activation

    async def deactivate_activation(
        self, pack_id: str, business_unit: Optional[str] = None
    ) -> bool:
        """Deactivate a pack activation."""
        conditions = [
            PackActivation.pack_id == pack_id,
            PackActivation.tenant_id == self.tenant_id,
            PackActivation.is_active == True,
        ]
        if business_unit:
            conditions.append(PackActivation.business_unit == business_unit)
        query = (
            update(PackActivation)
            .where(and_(*conditions))
            .values(is_active=False, deactivated_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount > 0

    # ── Workflow Versions ────────────────────────────────────────

    async def create_version(self, version: WorkflowVersion) -> WorkflowVersion:
        """Create a workflow version snapshot."""
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_versions(self, pack_id: str) -> list[WorkflowVersion]:
        """Get all versions for a pack."""
        query = select(WorkflowVersion).where(
            WorkflowVersion.pack_id == pack_id
        ).order_by(WorkflowVersion.version_number.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ── Workflow Instances ───────────────────────────────────────

    async def create_instance(self, instance: WorkflowInstance) -> WorkflowInstance:
        """Create a workflow instance."""
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get_instance(self, workflow_id: str) -> Optional[WorkflowInstance]:
        """Get a workflow instance with steps and logs."""
        query = (
            select(WorkflowInstance)
            .options(
                selectinload(WorkflowInstance.steps),
                selectinload(WorkflowInstance.execution_logs),
            )
            .where(WorkflowInstance.workflow_id == workflow_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_instances(
        self,
        status: Optional[str] = None,
        workflow_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[WorkflowInstance], int]:
        """List workflow instances with pagination and filtering."""
        conditions = [WorkflowInstance.tenant_id == self.tenant_id]
        if status:
            conditions.append(WorkflowInstance.status == status)
        if workflow_type:
            conditions.append(WorkflowInstance.workflow_type == workflow_type)

        # Count total
        count_query = select(func.count()).select_from(WorkflowInstance).where(and_(*conditions))
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch page
        query = (
            select(WorkflowInstance)
            .where(and_(*conditions))
            .options(selectinload(WorkflowInstance.steps))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        # Apply sorting
        sort_col = getattr(WorkflowInstance, sort_by, WorkflowInstance.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update_instance(self, workflow_id: str, **kwargs: Any) -> Optional[WorkflowInstance]:
        """Update a workflow instance."""
        kwargs["updated_at"] = datetime.now(timezone.utc)
        query = (
            update(WorkflowInstance)
            .where(WorkflowInstance.workflow_id == workflow_id)
            .values(**kwargs)
            .returning(WorkflowInstance)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def get_running_instances(self) -> list[WorkflowInstance]:
        """Get all running/paused/waiting instances for recovery."""
        query = select(WorkflowInstance).where(
            and_(
                WorkflowInstance.tenant_id == self.tenant_id,
                WorkflowInstance.status.in_([
                    WorkflowStatus.RUNNING.value,
                    WorkflowStatus.PAUSED.value,
                    WorkflowStatus.WAITING_APPROVAL.value,
                ]),
            )
        ).options(selectinload(WorkflowInstance.steps))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ── Workflow Instance Steps ──────────────────────────────────

    async def create_step(self, step: WorkflowInstanceStep) -> WorkflowInstanceStep:
        """Create a workflow step record."""
        self.session.add(step)
        await self.session.flush()
        return step

    async def get_steps(self, workflow_id: str) -> list[WorkflowInstanceStep]:
        """Get all steps for a workflow instance."""
        query = select(WorkflowInstanceStep).where(
            WorkflowInstanceStep.workflow_id == workflow_id
        ).order_by(WorkflowInstanceStep.step_order)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_step(self, step_id: str, **kwargs: Any) -> Optional[WorkflowInstanceStep]:
        """Update a workflow step."""
        query = (
            update(WorkflowInstanceStep)
            .where(WorkflowInstanceStep.step_id == step_id)
            .values(**kwargs)
            .returning(WorkflowInstanceStep)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def get_pending_approvals(
        self, user_id: Optional[str] = None
    ) -> list[WorkflowInstanceStep]:
        """Get all steps waiting for approval."""
        conditions = [
            WorkflowInstanceStep.requires_approval == True,
            WorkflowInstanceStep.approval_status == "pending",
        ]
        query = (
            select(WorkflowInstanceStep)
            .where(and_(*conditions))
            .options(selectinload(WorkflowInstanceStep.workflow_instance))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ── Workflow Execution Logs ──────────────────────────────────

    async def create_log(self, log: WorkflowExecutionLog) -> WorkflowExecutionLog:
        """Create an execution log entry."""
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_logs(
        self,
        workflow_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[WorkflowExecutionLog]:
        """Get execution logs with optional filtering."""
        conditions = [WorkflowExecutionLog.tenant_id == self.tenant_id]
        if workflow_id:
            conditions.append(WorkflowExecutionLog.workflow_id == workflow_id)
        if event_type:
            conditions.append(WorkflowExecutionLog.event_type == event_type)
        query = (
            select(WorkflowExecutionLog)
            .where(and_(*conditions))
            .order_by(WorkflowExecutionLog.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ── Dashboard / Metrics ──────────────────────────────────────

    async def get_dashboard_stats(self) -> dict[str, Any]:
        """Get aggregated workflow statistics for the dashboard."""
        base = select(WorkflowInstance).where(WorkflowInstance.tenant_id == self.tenant_id)

        # Count by status
        status_counts = {}
        for status_value in ["pending", "running", "paused", "waiting_approval", "completed", "failed", "cancelled", "timed_out", "compensated"]:
            query = select(func.count()).select_from(WorkflowInstance).where(
                and_(WorkflowInstance.tenant_id == self.tenant_id, WorkflowInstance.status == status_value)
            )
            result = await self.session.execute(query)
            count = result.scalar() or 0
            if count > 0:
                status_counts[status_value] = count

        # Total
        total_query = select(func.count()).select_from(WorkflowInstance).where(
            WorkflowInstance.tenant_id == self.tenant_id
        )
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        # SLA compliance
        sla_ok_query = select(func.count()).select_from(WorkflowInstance).where(
            and_(
                WorkflowInstance.tenant_id == self.tenant_id,
                WorkflowInstance.sla_breached == False,
                WorkflowInstance.status.in_(["completed", "running"]),
            )
        )
        sla_ok_result = await self.session.execute(sla_ok_query)
        sla_ok = sla_ok_result.scalar() or 0

        sla_total_query = select(func.count()).select_from(WorkflowInstance).where(
            and_(
                WorkflowInstance.tenant_id == self.tenant_id,
                WorkflowInstance.sla_deadline.isnot(None),
            )
        )
        sla_total_result = await self.session.execute(sla_total_query)
        sla_total = sla_total_result.scalar() or 0

        sla_compliance = round((sla_ok / sla_total * 100) if sla_total > 0 else 100.0, 1)

        # Pending approvals
        pending_query = select(func.count()).select_from(WorkflowInstanceStep).where(
            and_(
                WorkflowInstanceStep.requires_approval == True,
                WorkflowInstanceStep.approval_status == "pending",
            )
        )
        pending_result = await self.session.execute(pending_query)
        pending_approvals = pending_result.scalar() or 0

        return {
            "total": total,
            "by_status": status_counts,
            "pending_approvals": pending_approvals,
            "sla_compliance_rate": sla_compliance,
            "sla_total": sla_total,
            "sla_ok": sla_ok,
        }
