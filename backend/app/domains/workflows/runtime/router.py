"""Workflow Runtime API router — start, manage, and monitor workflow instances.

Provides endpoints for the full workflow lifecycle:
- Start/cancel workflow instances
- List and filter instances
- Resolve approval gates
- Dashboard and metrics
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.workflow_packs.repository import WorkflowRepository
from app.domains.workflow_packs.schemas import WorkflowPackCategory
from app.domains.workflows.runtime import WorkflowExecutionEngine, WorkflowStatus
from app.domains.workflows.runtime.persistence import WorkflowPersistenceAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflow Runtime"])

# Global engine instance (singleton)
_engine: Optional[WorkflowExecutionEngine] = None


def get_engine() -> WorkflowExecutionEngine:
    """Get or create the global workflow execution engine."""
    global _engine
    if _engine is None:
        _engine = WorkflowExecutionEngine()
        # Register standard workflow definitions
        from app.domains.workflows.runtime import WorkflowDefinition, WorkflowStep

        async def _noop_handler(ctx):
            return {"status": "completed", "message": f"Step {ctx.data.get('_step_name', 'unknown')} completed"}

        _engine.register_definition(WorkflowDefinition(
            workflow_type="contract_review",
            version="1.0",
            description="Standard contract review workflow",
            steps=[
                WorkflowStep(name="intake", handler=_noop_handler, sla_seconds=3600),
                WorkflowStep(name="ai_analysis", handler=_noop_handler, sla_seconds=7200),
                WorkflowStep(name="legal_review", handler=_noop_handler, requires_approval=True, sla_seconds=14400),
                WorkflowStep(name="approval", handler=_noop_handler, requires_approval=True, sla_seconds=7200),
                WorkflowStep(name="finalize", handler=_noop_handler, sla_seconds=3600),
            ],
            sla_seconds=86400,
        ))
        _engine.register_definition(WorkflowDefinition(
            workflow_type="procurement_review",
            version="1.0",
            description="Procurement contract review workflow",
            steps=[
                WorkflowStep(name="intake", handler=_noop_handler, sla_seconds=3600),
                WorkflowStep(name="vendor_assessment", handler=_noop_handler, sla_seconds=14400),
                WorkflowStep(name="legal_review", handler=_noop_handler, requires_approval=True, sla_seconds=14400),
                WorkflowStep(name="exec_approval", handler=_noop_handler, requires_approval=True, sla_seconds=7200),
            ],
            sla_seconds=86400,
        ))
        _engine.register_definition(WorkflowDefinition(
            workflow_type="negotiation_review",
            version="1.0",
            description="Negotiation workflow — tracks stage progression through drafting, review, negotiating, approval, execution",
            steps=[
                WorkflowStep(name="intake", handler=_noop_handler, sla_seconds=7200),
                WorkflowStep(name="legal_review", handler=_noop_handler, requires_approval=True, sla_seconds=14400),
                WorkflowStep(name="negotiation", handler=_noop_handler, sla_seconds=86400),
                WorkflowStep(name="final_approval", handler=_noop_handler, requires_approval=True, sla_seconds=7200),
                WorkflowStep(name="execution", handler=_noop_handler, sla_seconds=3600),
            ],
            sla_seconds=172800,
        ))
    return _engine


async def get_repo(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> WorkflowRepository:
    return WorkflowRepository(session, tenant_id)


async def get_persistence(
    repo: WorkflowRepository = Depends(get_repo),
) -> WorkflowPersistenceAdapter:
    return WorkflowPersistenceAdapter(repo)


# ── Schemas ──────────────────────────────────────────────────────


class WorkflowStartRequest(BaseModel):
    workflow_type: str = Field(..., description="Type of workflow to start")
    pack_id: Optional[str] = Field(None, description="Optional pack ID")
    data: dict = Field(default_factory=dict, description="Workflow input data")
    metadata: dict = Field(default_factory=dict, description="Workflow metadata")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")


class WorkflowStartResponse(BaseModel):
    workflow_id: str
    status: str
    message: str


class ApprovalActionRequest(BaseModel):
    gate_id: str = Field(..., description="Approval gate ID")
    action: str = Field(..., pattern="^(approve|reject)$", description="Action: approve or reject")
    reason: Optional[str] = Field(None, description="Reason for rejection")


class WorkflowListParams(BaseModel):
    status: Optional[str] = None
    workflow_type: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class PaginatedWorkflowResponse(BaseModel):
    data: list[dict]
    pagination: dict


class DashboardResponse(BaseModel):
    total: int = 0
    by_status: dict[str, int] = {}
    pending_approvals: int = 0
    sla_compliance_rate: float = 0.0
    sla_total: int = 0
    sla_ok: int = 0


# ── Endpoints ────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardResponse)
async def get_workflow_dashboard(
    repo: WorkflowRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get aggregated workflow dashboard statistics."""
    return await repo.get_dashboard_stats()


@router.get("", response_model=PaginatedWorkflowResponse)
@router.get("/", response_model=PaginatedWorkflowResponse)
async def list_workflows(
    status: Optional[str] = Query(None),
    workflow_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    repo: WorkflowRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List workflow instances with pagination and filtering."""
    instances, total = await repo.list_instances(
        status=status,
        workflow_type=workflow_type,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return {
        "data": [
            {
                "workflow_id": i.workflow_id,
                "workflow_type": i.workflow_type,
                "version": i.version,
                "status": i.status,
                "current_step": i.current_step,
                "correlation_id": i.correlation_id,
                "sla_deadline": i.sla_deadline.isoformat() if i.sla_deadline else None,
                "sla_breached": i.sla_breached,
                "error_count": i.error_count,
                "started_at": i.started_at.isoformat() if i.started_at else None,
                "completed_at": i.completed_at.isoformat() if i.completed_at else None,
                "created_at": i.created_at.isoformat() if i.created_at else None,
                "steps": [
                    {
                        "step_id": s.step_id,
                        "step_name": s.step_name,
                        "step_order": s.step_order,
                        "status": s.status,
                        "requires_approval": s.requires_approval,
                        "approval_status": s.approval_status,
                        "started_at": s.started_at.isoformat() if s.started_at else None,
                        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    }
                    for s in (i.steps or [])
                ],
            }
            for i in instances
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.get("/{workflow_id}", response_model=dict)
async def get_workflow(
    workflow_id: str,
    repo: WorkflowRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a single workflow instance with all details."""
    instance = await repo.get_instance(workflow_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    # Get execution logs
    logs = await repo.get_logs(workflow_id=workflow_id)

    return {
        "workflow_id": instance.workflow_id,
        "tenant_id": instance.tenant_id,
        "pack_id": instance.pack_id,
        "workflow_type": instance.workflow_type,
        "version": instance.version,
        "status": instance.status,
        "current_step": instance.current_step,
        "correlation_id": instance.correlation_id,
        "context": instance.context_data,
        "metadata": instance.metadata_json,
        "sla_deadline": instance.sla_deadline.isoformat() if instance.sla_deadline else None,
        "sla_breached": instance.sla_breached,
        "error_count": instance.error_count,
        "started_at": instance.started_at.isoformat() if instance.started_at else None,
        "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
        "steps": [
            {
                "step_id": s.step_id,
                "step_name": s.step_name,
                "step_type": s.step_type,
                "step_order": s.step_order,
                "status": s.status,
                "result": s.result_data,
                "error": s.error_data,
                "attempt_count": s.attempt_count,
                "requires_approval": s.requires_approval,
                "approval_status": s.approval_status,
                "approved_by": s.approved_by,
                "approval_reason": s.approval_reason,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in (instance.steps or [])
        ],
        "execution_logs": [
            {
                "log_id": log.log_id,
                "event_type": log.event_type,
                "step_name": log.step_name,
                "actor_id": log.actor_id,
                "previous_status": log.previous_status,
                "new_status": log.new_status,
                "details": log.details,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.post("/start", response_model=WorkflowStartResponse, status_code=201)
async def start_workflow(
    body: WorkflowStartRequest,
    repo: WorkflowRepository = Depends(get_repo),
    persistence: WorkflowPersistenceAdapter = Depends(get_persistence),
    engine: WorkflowExecutionEngine = Depends(get_engine),
    user: UserContext = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Start a new workflow instance."""
    try:
        runtime_instance = await engine.start_workflow(
            workflow_type=body.workflow_type,
            tenant_id=tenant_id,
            actor_id=user.id,
            data=body.data,
            metadata=body.metadata,
            correlation_id=body.correlation_id,
        )

        # Persist to database
        await persistence.save_workflow_start(
            instance=runtime_instance,
            pack_id=body.pack_id,
        )

        return WorkflowStartResponse(
            workflow_id=runtime_instance.workflow_id,
            status=runtime_instance.status.value,
            message=f"Workflow {body.workflow_type} started successfully",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AttributeError as e:
        raise HTTPException(status_code=500, detail=f"Attribute error: {str(e)}")
    except Exception as e:
        logger.exception("Failed to start workflow")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


@router.post("/{workflow_id}/cancel", response_model=dict)
async def cancel_workflow(
    workflow_id: str,
    engine: WorkflowExecutionEngine = Depends(get_engine),
    persistence: WorkflowPersistenceAdapter = Depends(get_persistence),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Cancel a running workflow."""
    instance = await engine.get_workflow(workflow_id)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    await engine.cancel_workflow(workflow_id)
    await persistence.save_workflow_completion(
        workflow_id=workflow_id,
        status=WorkflowStatus.CANCELLED.value,
    )

    return {"workflow_id": workflow_id, "status": "cancelled", "message": "Workflow cancelled"}


@router.post("/approvals/resolve", response_model=dict)
async def resolve_approval(
    body: ApprovalActionRequest,
    engine: WorkflowExecutionEngine = Depends(get_engine),
    persistence: WorkflowPersistenceAdapter = Depends(get_persistence),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Resolve an approval gate (approve or reject)."""
    try:
        result = await engine.resolve_approval(
            gate_id=body.gate_id,
            user_id=user.id,
            action=body.action,
            reason=body.reason,
        )

        # Find the workflow_id from the gate
        gate = engine._approval_gates.get(body.gate_id)
        workflow_id = gate.workflow_id if gate else "unknown"

        await persistence.save_approval_decision(
            workflow_id=workflow_id,
            step_name=gate.step_name if gate else "unknown",
            user_id=user.id,
            action=body.action,
            reason=body.reason,
        )

        return {
            "gate_id": body.gate_id,
            "action": body.action,
            "approved": result,
            "message": f"Approval {body.action}d",
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/approvals/pending", response_model=list[dict])
async def get_pending_approvals(
    engine: WorkflowExecutionEngine = Depends(get_engine),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get all pending approval gates for the current user."""
    gates = engine.get_pending_approvals(user_id=user.id)
    return [
        {
            "gate_id": g.gate_id,
            "workflow_id": g.workflow_id,
            "step_name": g.step_name,
            "status": g.status,
            "required_roles": g.required_roles,
            "created_at": g.created_at,
        }
        for g in gates
    ]


@router.get("/metrics/summary", response_model=dict)
async def get_workflow_metrics(
    repo: WorkflowRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get workflow metrics summary."""
    stats = await repo.get_dashboard_stats()

    # Get recent logs for activity feed
    recent_logs = await repo.get_logs(limit=20)

    return {
        **stats,
        "recent_activity": [
            {
                "event_type": log.event_type,
                "workflow_id": log.workflow_id,
                "step_name": log.step_name,
                "actor_id": log.actor_id,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in recent_logs
        ],
    }


@router.get("/metrics/stages", response_model=list[dict])
async def get_workflow_stages(
    repo: WorkflowRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get workflow stage distribution metrics."""
    # Get all completed steps to analyze stage durations
    logs = await repo.get_logs(event_type="step.completed", limit=500)

    # Group by step_name and calculate stats
    stage_stats: dict[str, dict] = {}
    for log in logs:
        name = log.step_name or "unknown"
        if name not in stage_stats:
            stage_stats[name] = {"count": 0, "name": name}
        stage_stats[name]["count"] += 1

    return list(stage_stats.values())


@router.get("/metrics/bottlenecks", response_model=list[dict])
async def get_workflow_bottlenecks(
    repo: WorkflowRepository = Depends(get_repo),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Identify workflow bottlenecks based on step failure and approval wait data."""
    # Find steps with high failure rates or long approval waits
    failed_logs = await repo.get_logs(event_type="step.failed", limit=200)
    approval_logs = await repo.get_logs(event_type="approval.pending", limit=200)

    bottlenecks: dict[str, dict] = {}

    for log in failed_logs:
        name = log.step_name or "unknown"
        if name not in bottlenecks:
            bottlenecks[name] = {
                "step_name": name,
                "failure_count": 0,
                "approval_wait_count": 0,
                "severity": "low",
            }
        bottlenecks[name]["failure_count"] += 1

    for log in approval_logs:
        name = log.step_name or "unknown"
        if name not in bottlenecks:
            bottlenecks[name] = {
                "step_name": name,
                "failure_count": 0,
                "approval_wait_count": 0,
                "severity": "low",
            }
        bottlenecks[name]["approval_wait_count"] += 1

    # Calculate severity
    for name, data in bottlenecks.items():
        total_issues = data["failure_count"] + data["approval_wait_count"]
        if total_issues >= 10:
            data["severity"] = "high"
        elif total_issues >= 5:
            data["severity"] = "medium"

    return list(bottlenecks.values())
