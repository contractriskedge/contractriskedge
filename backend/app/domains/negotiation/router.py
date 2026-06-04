"""Negotiation API router — full CRUD, stage transitions, redline/issue/participant management.

All endpoints prefixed with /api/v1/negotiations (registered in main.py).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.negotiation.repository import NegotiationRepository
from app.domains.negotiation.service import NegotiationService, set_workflow_engine
from app.domains.negotiation.schemas import (
    CommentCreateRequest,
    IssueCreateRequest,
    IssueUpdateRequest,
    NegotiationCreateRequest,
    NegotiationKpiResponse,
    NegotiationSessionResponse,
    NegotiationSessionSummary,
    NegotiationUpdateRequest,
    PaginatedNegotiationResponse,
    ParticipantCreateRequest,
    ParticipantUpdateRequest,
    RedlineCreateRequest,
    RedlineStatusUpdateRequest,
)
from app.domains.workflow_packs.repository import WorkflowRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/negotiations", tags=["Negotiations"])

# Workflow engine reference (lazy-initialized)
_workflow_engine: Optional["WorkflowExecutionEngine"] = None


def init_workflow_engine(engine: "WorkflowExecutionEngine") -> None:
    """Initialize the workflow engine reference for negotiation integration."""
    global _workflow_engine
    _workflow_engine = engine
    set_workflow_engine(engine)


# Auto-initialize workflow engine from the runtime module
try:
    from app.domains.workflows.runtime.router import get_engine as _get_wf_engine
    from app.domains.workflows.runtime.persistence import WorkflowPersistenceAdapter
    from app.domains.workflow_packs.repository import WorkflowRepository
    _wf_engine = _get_wf_engine()
    init_workflow_engine(_wf_engine)
    # Wire persistence adapter into the engine for completion/failure tracking
    # Use a lazy session — the engine will get persistence on first workflow start
    logger.info("Negotiation workflow engine initialized")
except ImportError:
    logger.warning("Workflow runtime not available — negotiation workflow sync disabled")
except Exception:
    logger.warning("Could not initialize workflow engine — will retry on first use")


async def get_repo(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> NegotiationRepository:
    return NegotiationRepository(session, tenant_id)


async def get_workflow_repo(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> WorkflowRepository:
    return WorkflowRepository(session, tenant_id)


async def get_service(
    repo: NegotiationRepository = Depends(get_repo),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
    user: UserContext = Depends(get_current_user),
) -> NegotiationService:
    return NegotiationService(repo, actor_id=user.id, workflow_repo=workflow_repo)


# ── Session CRUD ────────────────────────────────────────────────


@router.get("/kpis", response_model=NegotiationKpiResponse)
async def get_negotiation_kpis(
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get cross-session KPI aggregates."""
    return await service.get_kpis()


@router.get("", response_model=PaginatedNegotiationResponse)
@router.get("/", response_model=PaginatedNegotiationResponse)
async def list_negotiations(
    stage: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List negotiation sessions with pagination and optional text search."""
    sessions, total = await service.list_sessions(
        stage=stage, search=search, page=page, page_size=page_size
    )
    return {
        "data": sessions,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.post("", response_model=NegotiationSessionResponse, status_code=201)
@router.post("/", response_model=NegotiationSessionResponse, status_code=201)
async def create_negotiation(
    body: NegotiationCreateRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new negotiation session."""
    return await service.create_session(body)


@router.get("/{session_id}", response_model=NegotiationSessionResponse)
async def get_negotiation(
    session_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get full negotiation session detail."""
    result = await service.get_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return result


@router.patch("/{session_id}", response_model=NegotiationSessionResponse)
async def update_negotiation(
    session_id: str,
    body: NegotiationUpdateRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update negotiation session (stage, health score)."""
    try:
        result = await service.update_session(session_id, body)
        if not result:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{session_id}", status_code=204)
async def delete_negotiation(
    session_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Delete a negotiation session and all cascaded data."""
    deleted = await service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


# ── Redlines ────────────────────────────────────────────────────


@router.get("/{session_id}/redlines", response_model=list[dict])
async def list_redlines(
    session_id: str,
    clause_id: Optional[str] = Query(None, alias="clauseId"),
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List redlines for a session, optionally filtered by clause."""
    return await service.list_redlines(session_id, clause_id)


@router.post("/{session_id}/redlines", response_model=dict, status_code=201)
async def create_redline(
    session_id: str,
    body: RedlineCreateRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new redline on a session."""
    result = await service.create_redline(session_id, body)
    if not result:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return result


@router.patch("/{session_id}/redlines/{redline_id}", response_model=dict)
async def update_redline_status(
    session_id: str,
    redline_id: str,
    body: RedlineStatusUpdateRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Accept, reject, or supersede a redline."""
    result = await service.update_redline_status(redline_id, body.status)
    if not result:
        raise HTTPException(status_code=404, detail=f"Redline {redline_id} not found")
    return result


# ── Issues ──────────────────────────────────────────────────────


@router.get("/{session_id}/issues", response_model=list[dict])
async def list_issues(
    session_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List issues for a session."""
    return await service.list_issues(session_id)


@router.post("/{session_id}/issues", response_model=dict, status_code=201)
async def create_issue(
    session_id: str,
    body: IssueCreateRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a new issue on a session."""
    result = await service.create_issue(session_id, body)
    if not result:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return result


@router.patch("/{session_id}/issues/{issue_id}", response_model=dict)
async def update_issue(
    session_id: str,
    issue_id: str,
    body: IssueUpdateRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update issue status, severity, escalation level."""
    kwargs = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    result = await service.update_issue(issue_id, **kwargs)
    if not result:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    return result


# ── Comments ────────────────────────────────────────────────────


@router.get("/{session_id}/comments", response_model=list[dict])
async def list_comments(
    session_id: str,
    redline_id: Optional[str] = Query(None, alias="redlineId"),
    issue_id: Optional[str] = Query(None, alias="issueId"),
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List comments for a session."""
    return await service.list_comments(session_id, redline_id, issue_id)


@router.post("/{session_id}/comments", response_model=dict, status_code=201)
async def create_comment(
    session_id: str,
    body: CommentCreateRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Create a comment on a redline, issue, or as a reply."""
    result = await service.create_comment(session_id, body)
    if not result:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return result


@router.patch("/{session_id}/comments/{comment_id}/resolve", response_model=dict)
async def resolve_comment(
    session_id: str,
    comment_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Mark a comment as resolved."""
    result = await service.resolve_comment(comment_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Comment {comment_id} not found")
    return result


# ── Participants ────────────────────────────────────────────────


@router.get("/{session_id}/participants", response_model=list[dict])
async def list_participants(
    session_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """List participants in a session."""
    return await service.list_participants(session_id)


@router.post("/{session_id}/participants", response_model=dict, status_code=201)
async def add_participant(
    session_id: str,
    body: ParticipantCreateRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Add a participant to a session."""
    result = await service.add_participant(session_id, body)
    if not result:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return result


@router.patch("/{session_id}/participants/{participant_id}", response_model=dict)
async def update_participant_role(
    session_id: str,
    participant_id: str,
    body: ParticipantUpdateRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Update a participant's role."""
    result = await service.update_participant_role(participant_id, body.role)
    if not result:
        raise HTTPException(status_code=404, detail=f"Participant {participant_id} not found")
    return result


@router.delete("/{session_id}/participants/{participant_id}", status_code=204)
async def remove_participant(
    session_id: str,
    participant_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Remove a participant from a session."""
    deleted = await service.remove_participant(participant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Participant {participant_id} not found")


# ── Activities / Audit Log ──────────────────────────────────────


@router.get("/{session_id}/activities", response_model=list[dict])
async def get_activities(
    session_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get activity/audit log for a session."""
    return await service.get_activities(session_id)
