"""Workflow Runtime Persistence Adapter — saves/loads workflow instances to/from DB.

Connects the in-memory WorkflowExecutionEngine to the database,
enabling recovery across restarts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.workflow_packs.models import (
    WorkflowExecutionLog,
    WorkflowInstance,
    WorkflowInstanceStep,
    WorkflowStatus,
    WorkflowStepStatus,
)
from app.domains.workflow_packs.repository import WorkflowRepository
from app.domains.workflows.runtime import (
    ApprovalGate,
    WorkflowContext,
    WorkflowInstance as RuntimeInstance,
    WorkflowStep as RuntimeStep,
)

logger = logging.getLogger(__name__)


class WorkflowPersistenceAdapter:
    """Bridges between in-memory runtime engine and database.

    Saves workflow state changes to DB and loads persisted
    state back into the engine on recovery.
    """

    def __init__(self, repo: WorkflowRepository) -> None:
        self.repo = repo

    # ── Save (Runtime → DB) ─────────────────────────────────────

    async def save_workflow_start(
        self,
        instance: RuntimeInstance,
        pack_id: Optional[str] = None,
    ) -> WorkflowInstance:
        """Persist a new workflow instance when started."""
        db_instance = WorkflowInstance(
            workflow_id=instance.workflow_id,
            tenant_id=instance.context.tenant_id,
            pack_id=pack_id,
            workflow_type=instance.workflow_type,
            version=instance.version,
            status=WorkflowStatus.RUNNING.value,
            context_data=instance.context.data,
            metadata_json=instance.context.metadata,
            correlation_id=instance.context.correlation_id,
            current_step=0,
            sla_deadline=(
                datetime.fromisoformat(instance.sla_deadline)
                if instance.sla_deadline else None
            ),
            started_at=datetime.now(timezone.utc),
        )
        result = await self.repo.create_instance(db_instance)

        # Log the start event
        await self._log_event(
            workflow_id=instance.workflow_id,
            tenant_id=instance.context.tenant_id,
            event_type="workflow.started",
            actor_id=instance.context.actor_id,
            new_status=WorkflowStatus.RUNNING.value,
            details={
                "workflow_type": instance.workflow_type,
                "version": instance.version,
                "pack_id": pack_id,
            },
        )

        return result

    async def save_step_transition(
        self,
        workflow_id: str,
        step_name: str,
        from_status: Optional[str],
        to_status: str,
        step_order: int = 0,
        result_data: Optional[dict[str, Any]] = None,
        error_data: Optional[dict[str, Any]] = None,
        attempt_count: int = 0,
        requires_approval: bool = False,
        sla_seconds: Optional[int] = None,
    ) -> WorkflowInstanceStep:
        """Persist a step status change."""
        # Check if step already exists
        existing_steps = await self.repo.get_steps(workflow_id)
        existing = [s for s in existing_steps if s.step_name == step_name]

        if existing:
            step = existing[0]
            await self.repo.update_step(
                step.step_id,
                status=to_status,
                result_data=result_data,
                error_data=error_data,
                attempt_count=attempt_count,
                approval_status=(
                    "pending" if to_status == WorkflowStepStatus.WAITING_APPROVAL.value
                    else step.approval_status
                ),
                completed_at=datetime.now(timezone.utc) if to_status in (
                    WorkflowStepStatus.COMPLETED.value,
                    WorkflowStepStatus.FAILED.value,
                    WorkflowStepStatus.SKIPPED.value,
                ) else None,
            )
        else:
            step = WorkflowInstanceStep(
                workflow_id=workflow_id,
                step_name=step_name,
                step_order=step_order,
                status=to_status,
                result_data=result_data,
                error_data=error_data,
                attempt_count=attempt_count,
                requires_approval=requires_approval,
                approval_status="pending" if requires_approval and to_status == WorkflowStepStatus.WAITING_APPROVAL.value else None,
                sla_seconds=sla_seconds,
                started_at=datetime.now(timezone.utc) if to_status == WorkflowStepStatus.RUNNING.value else None,
                completed_at=datetime.now(timezone.utc) if to_status in (
                    WorkflowStepStatus.COMPLETED.value,
                    WorkflowStepStatus.FAILED.value,
                ) else None,
            )
            await self.repo.create_step(step)

        # Log the transition
        await self._log_event(
            workflow_id=workflow_id,
            tenant_id="",  # Will be set by caller
            event_type=f"step.{to_status}",
            step_name=step_name,
            previous_status=from_status,
            new_status=to_status,
            details={"attempt": attempt_count} if attempt_count > 0 else None,
            error_message=str(error_data.get("error")) if error_data and "error" in error_data else None,
        )

        return step

    async def save_approval_decision(
        self,
        workflow_id: str,
        step_name: str,
        user_id: str,
        action: str,
        reason: Optional[str] = None,
    ) -> None:
        """Persist an approval or rejection decision."""
        existing_steps = await self.repo.get_steps(workflow_id)
        step = next((s for s in existing_steps if s.step_name == step_name), None)

        if step:
            await self.repo.update_step(
                step.step_id,
                approval_status="approved" if action == "approve" else "rejected",
                approved_by=user_id,
                approval_reason=reason,
                status=WorkflowStepStatus.COMPLETED.value if action == "approve" else WorkflowStepStatus.FAILED.value,
                completed_at=datetime.now(timezone.utc),
            )

        await self._log_event(
            workflow_id=workflow_id,
            tenant_id="",
            event_type=f"approval.{action}",
            step_name=step_name,
            actor_id=user_id,
            details={"reason": reason} if reason else None,
        )

    async def save_workflow_completion(
        self,
        workflow_id: str,
        status: str,
        error_count: int = 0,
        sla_breached: bool = False,
    ) -> None:
        """Persist workflow completion/failure/cancellation."""
        await self.repo.update_instance(
            workflow_id,
            status=status,
            error_count=error_count,
            sla_breached=sla_breached,
            completed_at=datetime.now(timezone.utc),
        )

        await self._log_event(
            workflow_id=workflow_id,
            tenant_id="",
            event_type=f"workflow.{status}",
            new_status=status,
            details={"error_count": error_count, "sla_breached": sla_breached},
        )

    async def save_escalation(
        self,
        workflow_id: str,
        step_name: str,
        escalation_level: int,
        escalated_to: list[str],
    ) -> None:
        """Persist an escalation event."""
        await self._log_event(
            workflow_id=workflow_id,
            tenant_id="",
            event_type="workflow.escalated",
            step_name=step_name,
            details={
                "escalation_level": escalation_level,
                "escalated_to": escalated_to,
            },
        )

    # ── Load (DB → Runtime) ─────────────────────────────────────

    async def load_running_instances(self) -> list[tuple[RuntimeInstance, Optional[str]]]:
        """Load all running/paused/waiting instances for engine recovery."""
        db_instances = await self.repo.get_running_instances()
        result = []

        for db_inst in db_instances:
            runtime_inst = self._db_to_runtime(db_inst)
            result.append((runtime_inst, db_inst.pack_id))

        logger.info("Loaded %d running workflow instances for recovery", len(result))
        return result

    def _db_to_runtime(self, db_inst: WorkflowInstance) -> RuntimeInstance:
        """Convert a DB WorkflowInstance to a runtime WorkflowInstance."""
        context = WorkflowContext(
            workflow_id=db_inst.workflow_id,
            workflow_type=db_inst.workflow_type,
            tenant_id=db_inst.tenant_id,
            correlation_id=db_inst.correlation_id or "",
            trace_id=db_inst.workflow_id,
            actor_id=db_inst.metadata_json.get("actor_id") if db_inst.metadata_json else None,
            data=db_inst.context_data or {},
            metadata=db_inst.metadata_json or {},
            started_at=db_inst.created_at.isoformat() if db_inst.created_at else datetime.now(timezone.utc).isoformat(),
        )

        return RuntimeInstance(
            workflow_id=db_inst.workflow_id,
            workflow_type=db_inst.workflow_type,
            version=db_inst.version,
            tenant_id=db_inst.tenant_id,
            status=WorkflowStatus(db_inst.status) if db_inst.status else WorkflowStatus.PENDING,
            context=context,
            current_step=db_inst.current_step or 0,
            sla_deadline=db_inst.sla_deadline.isoformat() if db_inst.sla_deadline else None,
            created_at=db_inst.created_at.isoformat() if db_inst.created_at else datetime.now(timezone.utc).isoformat(),
            completed_at=db_inst.completed_at.isoformat() if db_inst.completed_at else None,
        )

    # ── Internal ────────────────────────────────────────────────

    async def _log_event(
        self,
        workflow_id: str,
        tenant_id: str,
        event_type: str,
        step_name: Optional[str] = None,
        actor_id: Optional[str] = None,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> WorkflowExecutionLog:
        """Create an execution log entry."""
        # Resolve tenant_id from instance if not provided
        if not tenant_id:
            inst = await self.repo.get_instance(workflow_id)
            if inst:
                tenant_id = inst.tenant_id

        log = WorkflowExecutionLog(
            workflow_id=workflow_id,
            tenant_id=tenant_id or "unknown",
            event_type=event_type,
            step_name=step_name,
            actor_id=actor_id,
            previous_status=previous_status,
            new_status=new_status,
            details=details,
            error_message=error_message,
        )
        return await self.repo.create_log(log)
