"""Negotiation API router — full CRUD, stage transitions, redline/issue/participant management.

All endpoints prefixed with /api/v1/negotiations (registered in main.py).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.negotiation.repository import NegotiationRepository
from app.domains.negotiation.service import NegotiationService, set_workflow_engine
from app.domains.negotiation.schemas import (
    CommentCreateRequest,
    ClauseCommentCreateRequest,
    DEFAULT_STRATEGIES,
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
    ResumeFromReviewRequest,
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


@router.post("/from-review", response_model=NegotiationSessionResponse)
async def resume_negotiation_from_review(
    body: ResumeFromReviewRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Resume or create a negotiation session from an AI contract review."""
    try:
        return await service.resume_or_create_from_review(
            body.review_id, body.counterparty,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
        logger.warning(f"Stage transition rejected: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")


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


# ── AI Rewrite ──────────────────────────────────────────────────


class AIRewriteRequest(BaseModel):
    clause_text: str
    strategy: str = "balanced"
    context: Optional[str] = None


class AIRewriteResponse(BaseModel):
    original_text: str
    rewritten_text: str
    strategy: str
    changes: list[dict | str] = []
    model_used: str = "gpt-4o"

    @field_validator("changes", mode="before")
    @classmethod
    def normalize_changes(cls, v):
        """Ensure each change is a dict — wrap strings in {'description': ...}."""
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append({"description": item})
            elif isinstance(item, dict):
                result.append(item)
        return result


@router.post(
    "/{session_id}/clauses/{clause_id}/rewrite",
    summary="AI rewrite a clause with different negotiation strategies",
)
async def ai_rewrite_clause(
    session_id: str,
    clause_id: str,
    request: AIRewriteRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Rewrite a clause using AI with a specified negotiation strategy.

    Strategies are loaded from DEFAULT_STRATEGIES in schemas.py.
    """
    from app.domains.ai.llm import OpenAIProvider, LLMRequest, StructuredOutputParser
    from app.config import settings

    # Build prompt template lookup from DEFAULT_STRATEGIES
    strategy_map = {s["strategy_id"]: s["prompt_template"] for s in DEFAULT_STRATEGIES}
    system_prompt = strategy_map.get(request.strategy, strategy_map["balanced"])
    prompt = f"""{system_prompt}

Clause to rewrite:
```
{request.clause_text}
```

{f"Context: {request.context}" if request.context else ""}

Respond with a valid JSON object containing:
- rewritten_text: The rewritten clause
- changes: An array of change descriptions (what was modified and why)
"""

    provider = OpenAIProvider(api_key=settings.openai_api_key)
    llm_request = LLMRequest(
        prompt=prompt,
        system_prompt="You are a senior contract negotiation specialist. Always respond with valid JSON.",
        model="gpt-4o",
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        response = await provider.complete(llm_request)
        parsed = StructuredOutputParser.parse_json(response.content)
        rewritten_text = (parsed or {}).get("rewritten_text", "")
        changes = (parsed or {}).get("changes", [])

        try:
            await service.repo.log_audit(
                session_id=session_id,
                event_type="negotiation.ai_rewrite",
                actor_id=service.actor_id,
                new_state={"clause_id": clause_id, "strategy": request.strategy},
                change_summary=f"AI rewrite generated for clause ({request.strategy})",
            )
        except Exception:
            logger.warning("Failed to log AI rewrite audit event", exc_info=True)

        return AIRewriteResponse(
            original_text=request.clause_text,
            rewritten_text=rewritten_text or "AI could not generate a rewrite.",
            strategy=request.strategy,
            changes=changes if isinstance(changes, list) else [],
            model_used=response.model,
        )
    except Exception as exc:
        logger.error(f"AI rewrite failed for session {session_id} clause {clause_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"AI rewrite failed: {exc}")


@router.post(
    "/{session_id}/clauses/{clause_id}/comments",
    summary="Add a comment to a clause in a negotiation session",
    status_code=201,
)
async def add_clause_comment(
    session_id: str,
    clause_id: str,
    body: ClauseCommentCreateRequest,
    service: NegotiationService = Depends(get_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Add a threaded comment to a specific clause in a negotiation session."""
    comment = {
        "comment_id": str(uuid.uuid4()),
        "session_id": session_id,
        "clause_id": clause_id,
        "finding_id": body.finding_id,
        "parent_comment_id": body.parent_comment_id,
        "author_id": user.id,
        "author_name": user.email or user.id,
        "author_role": user.role or "viewer",
        "body": body.body,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved": False,
    }
    session_obj = await service.get_session(session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    metadata = dict(session_obj.metadata or {})
    comments = metadata.get("clause_comments", {})
    clause_comments = comments.get(clause_id, [])
    clause_comments.append(comment)
    comments[clause_id] = clause_comments
    metadata["clause_comments"] = comments

    await service.update_session(session_id, metadata=metadata)

    try:
        await service.repo.log_audit(
            session_id=session_id,
            event_type="comment.created",
            actor_id=user.id,
            new_state={"clause_id": clause_id, "comment_id": comment["comment_id"]},
            change_summary=f"Comment added on clause {clause_id}",
        )
    except Exception:
        logger.warning("Failed to log clause comment audit event", exc_info=True)

    return comment


@router.get(
    "/{session_id}/clauses/{clause_id}/comments",
    summary="Get comments for a clause",
)
async def get_clause_comments(
    session_id: str,
    clause_id: str,
    finding_id: Optional[str] = Query(None, alias="findingId", description="Filter by finding ID"),
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get all threaded comments for a specific clause, optionally filtered by finding."""
    session_obj = await service.get_session(session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    metadata = dict(session_obj.metadata or {})
    comments = metadata.get("clause_comments", {})
    clause_comments = comments.get(clause_id, [])

    if finding_id:
        clause_comments = [c for c in clause_comments if c.get("finding_id") == finding_id]

    return clause_comments


@router.post(
    "/{session_id}/clauses/{clause_id}/comments/{comment_id}/resolve",
    summary="Mark a comment as resolved",
)
async def resolve_clause_comment(
    session_id: str,
    clause_id: str,
    comment_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Mark a comment as resolved."""
    session_obj = await service.get_session(session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    metadata = dict(session_obj.metadata or {})
    comments = metadata.get("clause_comments", {})
    clause_comments = comments.get(clause_id, [])

    for c in clause_comments:
        if c.get("comment_id") == comment_id:
            c["resolved"] = True
            c["resolved_at"] = datetime.now(timezone.utc).isoformat()
            break

    comments[clause_id] = clause_comments
    metadata["clause_comments"] = comments
    await service.update_session(session_id, metadata=metadata)
    return {"status": "resolved", "comment_id": comment_id}


# ── Clause Voting ───────────────────────────────────────────────


class VoteRequest(BaseModel):
    clause_id: str
    finding_id: Optional[str] = None
    voter_name: str
    voter_role: str  # "legal", "security", "business", "procurement"
    vote: str  # "approve", "reject", "pending"
    comment: Optional[str] = None


class VoteResponse(BaseModel):
    vote_id: str
    clause_id: str
    voter_role: str
    vote: str
    message: str = ""


@router.post("/{session_id}/votes", status_code=201)
async def cast_vote(
    session_id: str,
    body: VoteRequest,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Cast a vote on a clause or finding within a negotiation session."""
    from app.domains.negotiation.models import NegotiationVote
    import uuid

    vote = NegotiationVote(
        vote_id=str(uuid.uuid4()),
        session_id=session_id,
        clause_id=body.clause_id,
        finding_id=body.finding_id,
        voter_name=body.voter_name,
        voter_role=body.voter_role,
        vote=body.vote,
        comment=body.comment,
    )
    created = await service.repo.create_vote(vote)
    try:
        await service.repo.log_audit(
            session_id=session_id,
            event_type="negotiation.vote_cast",
            actor_id=service.actor_id,
            new_state={
                "clause_id": body.clause_id,
                "voter_role": body.voter_role,
                "vote": body.vote,
            },
            change_summary=f"{body.voter_role} voted {body.vote} on clause {body.clause_id}",
        )
    except Exception:
        logger.warning("Failed to log vote audit event", exc_info=True)
    return VoteResponse(
        vote_id=created.vote_id,
        clause_id=created.clause_id,
        voter_role=created.voter_role,
        vote=created.vote,
        message="Vote recorded successfully",
    )


@router.get("/{session_id}/clauses/{clause_id}/votes")
async def get_clause_votes(
    session_id: str,
    clause_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get all votes for a specific clause."""
    votes = await service.repo.list_votes(session_id, clause_id=clause_id)
    return [
        {
            "vote_id": v.vote_id,
            "clause_id": v.clause_id,
            "finding_id": v.finding_id,
            "voter_name": v.voter_name,
            "voter_role": v.voter_role,
            "vote": v.vote,
            "comment": v.comment,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in votes
    ]


@router.get("/{session_id}/votes/summary")
async def get_vote_summary(
    session_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a summary of all votes cast in a session."""
    votes = await service.repo.list_votes(session_id)
    total = len(votes)
    approved = sum(1 for v in votes if v.vote == "approve")
    rejected = sum(1 for v in votes if v.vote == "reject")
    pending = sum(1 for v in votes if v.vote == "pending")

    # Breakdown by role
    by_role: dict[str, dict[str, int]] = {}
    for v in votes:
        role = v.voter_role
        if role not in by_role:
            by_role[role] = {"total": 0, "approve": 0, "reject": 0, "pending": 0}
        by_role[role]["total"] += 1
        by_role[role][v.vote] += 1

    return {
        "session_id": session_id,
        "total_votes": total,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "by_role": by_role,
    }


# ── AI Explanation ──────────────────────────────────────────────


class AiExplanationRequest(BaseModel):
    original_text: str
    rewritten_text: str
    strategy: str


class AiExplanationResponse(BaseModel):
    explanation: str
    changes: list[dict] = []
    risks_addressed: list[str] = []
    benefits: list[str] = []


@router.post("/{session_id}/clauses/{clause_id}/explain")
async def ai_explain_rewrite(
    session_id: str,
    clause_id: str,
    request: AiExplanationRequest,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Explain why an AI rewrite was performed — risks addressed, benefits, and changes made."""
    from app.domains.ai.llm import OpenAIProvider, LLMRequest, StructuredOutputParser
    from app.config import settings

    prompt = f"""Analyze the following contract clause rewrite and explain WHY the changes were made.

Original clause:
```
{request.original_text}
```

Rewritten clause:
```
{request.rewritten_text}
```

Strategy used: {request.strategy}

Return a JSON object with:
- explanation: A clear explanation of why the rewrite was performed
- changes: An array of objects each with "description" (what changed) and "reason" (why it changed)
- risks_addressed: An array of risk categories that were addressed (e.g., "unlimited liability", "missing GDPR language")
- benefits: An array of benefits gained from the rewrite
"""

    provider = OpenAIProvider(api_key=settings.openai_api_key)
    llm_request = LLMRequest(
        prompt=prompt,
        system_prompt="You are a senior contract negotiation specialist. Always respond in valid JSON.",
        model="gpt-4o",
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        response = await provider.complete(llm_request)
        parsed = StructuredOutputParser.parse_json(response.content) or {}
        return AiExplanationResponse(
            explanation=parsed.get("explanation", ""),
            changes=parsed.get("changes", []),
            risks_addressed=parsed.get("risks_addressed", []),
            benefits=parsed.get("benefits", []),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI explanation failed: {exc}")


# ── Clause Score ────────────────────────────────────────────────


class ClauseScoreResponse(BaseModel):
    clause_id: str
    risk_score: float
    negotiability_score: float
    readability_score: float
    market_standard_score: float
    overall_score: float


@router.get("/{session_id}/clauses/{clause_id}/score")
async def get_clause_score(
    session_id: str,
    clause_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Compute quality scores for a clause: risk, negotiability, readability, market standard."""
    import textstat

    # Find the clause in the session's current version
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    clause = None
    for v in (getattr(session, "versions", None) or []):
        if getattr(v, "status", "") == "current":
            for c in (getattr(v, "content", None) or []):
                if getattr(c, "clause_id", None) == clause_id or (hasattr(c, "clauseId") and c.clauseId == clause_id):
                    clause = c
                    break
            if clause:
                break

    if not clause:
        raise HTTPException(status_code=404, detail=f"Clause {clause_id} not found")

    content = getattr(clause, "content", None) or getattr(clause, "Content", "") or ""

    # Risk score from risk_level
    risk_map = {"critical": 95, "high": 75, "medium": 50, "low": 25, "info": 5}
    risk_score = risk_map.get(
        (getattr(clause, "risk_level", None) or getattr(clause, "riskLevel", "") or "medium").lower(),
        50,
    )

    # Readability via Flesch-Kincaid (textstat)
    try:
        readability_score = min(100, max(0, textstat.flesch_reading_ease(content) if content else 50))
    except Exception:
        readability_score = 50.0

    # Negotiability — higher risk = more negotiable
    negotiability_score = min(100, max(0, 100 - risk_score + 10))

    # Market standard — placeholder heuristic (could be extended with template DB lookup)
    market_standard_score = 60.0

    overall_score = round(
        (risk_score * 0.3 + negotiability_score * 0.25 + readability_score * 0.25 + market_standard_score * 0.2),
        2,
    )

    return ClauseScoreResponse(
        clause_id=clause_id,
        risk_score=round(risk_score, 2),
        negotiability_score=round(negotiability_score, 2),
        readability_score=round(readability_score, 2),
        market_standard_score=round(market_standard_score, 2),
        overall_score=overall_score,
    )


# ── AI Negotiation Coach ────────────────────────────────────────


class CoachQuestion(BaseModel):
    clause_text: str
    question: str  # e.g. "Why shouldn't I accept this?"


class CoachResponse(BaseModel):
    risks: list[str] = []
    policy_conflicts: list[str] = []
    recommended_alternative: Optional[str] = None
    explanation: str


@router.post("/{session_id}/clauses/{clause_id}/coach")
async def ai_negotiation_coach(
    session_id: str,
    clause_id: str,
    request: CoachQuestion,
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Ask the AI negotiation coach to analyze a clause — risks, policy conflicts, and alternatives."""
    from app.domains.ai.llm import OpenAIProvider, LLMRequest, StructuredOutputParser
    from app.config import settings

    prompt = f"""You are an expert contract negotiation coach. Analyze the following clause and answer the user's question.

Clause text:
```
{request.clause_text}
```

User's question: {request.question}

Return a JSON object with:
- risks: An array of specific risks in this clause (e.g., "uncapped liability", "no data breach notification")
- policy_conflicts: An array of potential policy conflicts (e.g., "GDPR non-compliance", "exceeds delegation of authority")
- recommended_alternative: A brief suggested alternative wording (or null if none)
- explanation: A detailed explanation addressing the user's question
"""

    provider = OpenAIProvider(api_key=settings.openai_api_key)
    llm_request = LLMRequest(
        prompt=prompt,
        system_prompt="You are a senior contract negotiation coach. Always respond in valid JSON.",
        model="gpt-4o",
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    try:
        response = await provider.complete(llm_request)
        parsed = StructuredOutputParser.parse_json(response.content) or {}
        return CoachResponse(
            risks=parsed.get("risks", []),
            policy_conflicts=parsed.get("policy_conflicts", []),
            recommended_alternative=parsed.get("recommended_alternative"),
            explanation=parsed.get("explanation", ""),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI coach failed: {exc}")


# ── Chat Message History ────────────────────────────────────────


class ChatMessageCreateRequest(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    clause_id: Optional[str] = None
    metadata: Optional[dict] = None


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    clause_id: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str


@router.get("/{session_id}/chat", response_model=list[ChatMessageResponse])
async def get_chat_messages(
    session_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get chat message history for a negotiation session."""
    session_obj = await service.get_session(session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    metadata = dict(session_obj.metadata or {})
    chat_history = metadata.get("chat_history", [])
    return chat_history


@router.post("/{session_id}/chat", response_model=ChatMessageResponse, status_code=201)
async def add_chat_message(
    session_id: str,
    body: ChatMessageCreateRequest,
    service: NegotiationService = Depends(get_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Add a chat message to the session's chat history."""
    session_obj = await service.get_session(session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    message = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "role": body.role,
        "content": body.content,
        "clause_id": body.clause_id,
        "metadata": body.metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    metadata = dict(session_obj.metadata or {})
    chat_history = metadata.get("chat_history", [])
    chat_history.append(message)
    metadata["chat_history"] = chat_history

    await service.update_session(session_id, metadata=metadata)
    return message


@router.delete("/{session_id}/chat", status_code=204)
async def clear_chat_messages(
    session_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Clear all chat messages for a session."""
    session_obj = await service.get_session(session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    metadata = dict(session_obj.metadata or {})
    metadata["chat_history"] = []
    await service.update_session(session_id, metadata=metadata)


# ── Clause Dependency Warnings ──────────────────────────────────


class DependencyWarning(BaseModel):
    affected_clause: str
    relationship: str  # "direct", "implied", "related"
    impact: str  # "high", "medium", "low"
    description: str


class DependencyWarningsResponse(BaseModel):
    clause_id: str
    clause_type: str
    warnings: list[DependencyWarning] = []


# Dependency map: clause type → affected clauses
_DEPENDENCY_MAP: dict[str, list[dict[str, str]]] = {
    "liability": [
        {"clause_type": "indemnification", "relationship": "direct", "impact": "high", "description": "Limitation of liability directly caps indemnification obligations"},
        {"clause_type": "insurance", "relationship": "direct", "impact": "high", "description": "Liability caps affect required insurance coverage limits"},
        {"clause_type": "warranty", "relationship": "implied", "impact": "medium", "description": "Warranty disclaimers interact with liability limitations"},
        {"clause_type": "damages", "relationship": "direct", "impact": "high", "description": "Consequential damages exclusion tied to liability cap"},
    ],
    "indemnification": [
        {"clause_type": "liability", "relationship": "direct", "impact": "high", "description": "Indemnification scope limited by liability cap"},
        {"clause_type": "insurance", "relationship": "direct", "impact": "medium", "description": "Insurance requirements must cover indemnification obligations"},
    ],
    "termination": [
        {"clause_type": "notice_period", "relationship": "direct", "impact": "high", "description": "Termination notice period must align with notice clause"},
        {"clause_type": "auto_renewal", "relationship": "direct", "impact": "high", "description": "Auto-renewal terms affect termination timing"},
    ],
    "confidentiality": [
        {"clause_type": "nda", "relationship": "direct", "impact": "high", "description": "NDA scope defines confidentiality obligations"},
        {"clause_type": "return_of_information", "relationship": "direct", "impact": "medium", "description": "Return of information clause enforces confidentiality post-termination"},
    ],
    "gdpr": [
        {"clause_type": "data_privacy", "relationship": "direct", "impact": "high", "description": "GDPR compliance requires robust data privacy provisions"},
        {"clause_type": "cross_border_transfer", "relationship": "direct", "impact": "high", "description": "Cross-border data transfers must comply with GDPR"},
        {"clause_type": "data_breach", "relationship": "direct", "impact": "high", "description": "Data breach notification is a GDPR requirement"},
    ],
}


@router.get("/{session_id}/clauses/{clause_id}/dependencies")
async def get_clause_dependencies(
    session_id: str,
    clause_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get dependency warnings for a clause — which other clauses are affected by changes here."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find the clause to determine its type
    clause = None
    clause_type = "unknown"
    for v in (getattr(session, "versions", None) or []):
        if getattr(v, "status", "") == "current":
            for c in (getattr(v, "content", None) or []):
                cid = getattr(c, "clause_id", None) or getattr(c, "clauseId", None)
                if cid == clause_id:
                    clause = c
                    clause_type = getattr(c, "category", None) or getattr(c, "Category", "") or "unknown"
                    break
            if clause:
                break

    # Check dependency map
    dependency_warnings = _DEPENDENCY_MAP.get(clause_type, [])
    # Also check if any other clause types list this clause_type
    for dep_type, dep_list in _DEPENDENCY_MAP.items():
        if dep_type != clause_type:
            for dep in dep_list:
                if dep["clause_type"] == clause_type:
                    dependency_warnings.append({
                        "clause_type": dep_type,
                        "relationship": "related",
                        "impact": dep["impact"],
                        "description": f"Changes to {clause_type} may affect {dep_type}: {dep['description']}",
                    })

    warnings = [
        DependencyWarning(
            affected_clause=d["clause_type"],
            relationship=d["relationship"],
            impact=d["impact"],
            description=d["description"],
        )
        for d in dependency_warnings
    ]

    return DependencyWarningsResponse(
        clause_id=clause_id,
        clause_type=clause_type,
        warnings=warnings,
    )


# ── Negotiation Summary ────────────────────────────────────────


class NegotiationSummaryResponse(BaseModel):
    session_id: str
    total_clauses: int
    clauses_modified: int
    clauses_accepted: int
    clauses_pending: int
    clauses_escalated: int
    risk_score_before: float = 0
    risk_score_after: float = 0
    estimated_time_saved_hours: float = 0
    votes_cast: int = 0
    votes_approved: int = 0
    votes_rejected: int = 0
    ai_rewrites_used: int = 0
    generated_at: str


@router.get("/{session_id}/summary")
async def get_negotiation_summary(
    session_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get a comprehensive summary of the negotiation session."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Count clauses from current version
    total_clauses = 0
    for v in (getattr(session, "versions", None) or []):
        if getattr(v, "status", "") == "current":
            total_clauses = len(getattr(v, "content", None) or [])
            break

    # Count redline statuses
    redlines = getattr(session, "redlines", None) or []
    clauses_modified = len([r for r in redlines if getattr(r, "type", None) in ("modification", "addition")])
    clauses_accepted = len([r for r in redlines if getattr(r, "status", None) == "accepted"])
    clauses_pending = len([r for r in redlines if getattr(r, "status", None) == "pending"])
    clauses_escalated = len([i for i in (getattr(session, "issues", None) or []) if getattr(i, "escalation_level", 0) > 0])

    # Count votes
    try:
        votes = await service.repo.list_votes(session_id)
        votes_cast = len(votes)
        votes_approved = sum(1 for v in votes if v.vote == "approve")
        votes_rejected = sum(1 for v in votes if v.vote == "reject")
    except Exception:
        votes_cast = 0
        votes_approved = 0
        votes_rejected = 0

    # AI rewrites = ai_generated redlines
    ai_rewrites_used = len([r for r in redlines if getattr(r, "ai_generated", False)])

    # Estimated time saved: each AI rewrite saves ~30 min, each accepted redline saves ~15 min
    estimated_time_saved_hours = round((ai_rewrites_used * 0.5 + clauses_accepted * 0.25), 2)

    return NegotiationSummaryResponse(
        session_id=session_id,
        total_clauses=total_clauses,
        clauses_modified=clauses_modified,
        clauses_accepted=clauses_accepted,
        clauses_pending=clauses_pending,
        clauses_escalated=clauses_escalated,
        estimated_time_saved_hours=estimated_time_saved_hours,
        votes_cast=votes_cast,
        votes_approved=votes_approved,
        votes_rejected=votes_rejected,
        ai_rewrites_used=ai_rewrites_used,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# ── Negotiation History ────────────────────────────────────────


class HistoryEntry(BaseModel):
    version_number: int
    label: str
    author: str
    timestamp: datetime
    action: str  # "created", "ai_rewrite", "legal_edit", "vendor_edit", "accepted"
    clause_id: str
    original_text: str
    modified_text: str
    explanation: Optional[str] = None


@router.get("/{session_id}/clauses/{clause_id}/history")
async def get_clause_history(
    session_id: str,
    clause_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get the version history for a specific clause across all versions."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    versions = getattr(session, "versions", None) or []
    history: list[dict] = []
    previous_content = ""

    for v in sorted(versions, key=lambda x: getattr(x, "version_number", 0) or 0):
        clauses = getattr(v, "clauses", None) or []
        clause = None
        for c in clauses:
            cid = None
            if isinstance(c, dict):
                cid = c.get("clause_id") or c.get("clauseId")
            else:
                cid = getattr(c, "clause_id", None) or getattr(c, "clauseId", None)
            if cid == clause_id:
                clause = c
                break

        if not clause:
            continue

        content = clause.get("content", "") if isinstance(clause, dict) else getattr(clause, "content", "") or ""
        action = "created" if not previous_content else "legal_edit"

        history.append({
            "version_number": getattr(v, "version_number", 0),
            "label": getattr(v, "label", ""),
            "author": getattr(v, "author", ""),
            "timestamp": getattr(v, "created_at", datetime.now(timezone.utc)),
            "action": action,
            "clause_id": clause_id,
            "original_text": previous_content,
            "modified_text": content,
            "explanation": getattr(v, "change_summary", None),
        })
        previous_content = content

    # Also include redline-based history
    redlines = getattr(session, "redlines", None) or []
    for r in redlines:
        if getattr(r, "clause_id", None) == clause_id:
            action_map = {
                "addition": "legal_edit",
                "deletion": "legal_edit",
                "modification": "legal_edit",
                "suggestion": "ai_rewrite" if getattr(r, "ai_generated", False) else "legal_edit",
            }
            history.append({
                "version_number": 0,
                "label": f"Redline: {getattr(r, 'title', '')}",
                "author": getattr(r, "author", ""),
                "timestamp": getattr(r, "created_at", datetime.now(timezone.utc)),
                "action": action_map.get(getattr(r, "type", ""), "legal_edit"),
                "clause_id": clause_id,
                "original_text": getattr(r, "original_text", ""),
                "modified_text": getattr(r, "modified_text", "") or "",
                "explanation": None,
            })

    # Sort by timestamp
    history.sort(key=lambda h: h["timestamp"], reverse=True)
    return history


# ── Counterparty Comparison ────────────────────────────────────


class PositionText(BaseModel):
    text: str
    label: str  # "our_position", "vendor_position", "final_position"


class CounterpartyComparisonResponse(BaseModel):
    clause_id: str
    our_position: str
    vendor_position: str
    final_position: Optional[str] = None
    diff_additions: list[str] = []
    diff_deletions: list[str] = []


@router.get("/{session_id}/clauses/{clause_id}/comparison")
async def get_counterparty_comparison(
    session_id: str,
    clause_id: str,
    service: NegotiationService = Depends(get_service),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Compare our position vs. vendor/counterparty position for a clause."""
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    versions = getattr(session, "versions", None) or []
    sorted_versions = sorted(versions, key=lambda x: getattr(x, "version_number", 0) or 0)

    our_position = ""
    vendor_position = ""
    final_position = None

    for i, v in enumerate(sorted_versions):
        clauses_data = getattr(v, "clauses", None) or []
        clause = None
        for c in clauses_data:
            cid = None
            if isinstance(c, dict):
                cid = c.get("clause_id") or c.get("clauseId")
            else:
                cid = getattr(c, "clause_id", None) or getattr(c, "clauseId", None)
            if cid == clause_id:
                clause = c
                break
        if not clause:
            continue

        content = clause.get("content", "") if isinstance(clause, dict) else getattr(clause, "content", "") or ""
        label = getattr(v, "label", "") or ""

        if "original" in label.lower() or i == 0:
            vendor_position = content
        elif "counter" in label.lower() or i == len(sorted_versions) - 1:
            our_position = content
        else:
            our_position = content

    # If only one version, treat it as vendor position
    if not our_position and vendor_position:
        our_position = vendor_position

    # Compute simple diff
    our_words = set(our_position.split())
    vendor_words = set(vendor_position.split())
    diff_additions = list(our_words - vendor_words)[:20]
    diff_deletions = list(vendor_words - our_words)[:20]

    return CounterpartyComparisonResponse(
        clause_id=clause_id,
        our_position=our_position,
        vendor_position=vendor_position,
        final_position=final_position,
        diff_additions=diff_additions,
        diff_deletions=diff_deletions,
    )


# ── Clause Bundle Apply (Knowledge Center Integration) ──────────


class ApplyBundleRequest(BaseModel):
    clause_type: str
    target_clause_id: str


class BundleApplyResponse(BaseModel):
    status: str
    session_id: str
    clause_type: str
    redline_ids: list[str] = []
    templates_applied: int = 0
    message: str = ""


# Bundle definitions (shared knowledge — same as redline_templates/router.py)
_BUNDLES: dict[str, list[dict[str, str]]] = {
    "gdpr": [
        {"clause_type": "gdpr", "label": "GDPR Compliance", "required": True},
        {"clause_type": "cross_border_transfer", "label": "Cross-Border Transfer", "required": True},
        {"clause_type": "data_breach", "label": "Data Breach Notification", "required": True},
        {"clause_type": "dpa", "label": "Data Processing Agreement", "required": False},
        {"clause_type": "scc", "label": "Standard Contractual Clauses", "required": False},
    ],
    "data_privacy": [
        {"clause_type": "gdpr", "label": "GDPR Compliance", "required": True},
        {"clause_type": "cross_border_transfer", "label": "Cross-Border Transfer", "required": True},
        {"clause_type": "data_breach", "label": "Data Breach Notification", "required": True},
    ],
    "confidentiality": [
        {"clause_type": "confidentiality", "label": "Confidentiality", "required": True},
        {"clause_type": "nda", "label": "Non-Disclosure Agreement", "required": True},
        {"clause_type": "return_of_information", "label": "Return of Information", "required": False},
        {"clause_type": "non_compete", "label": "Non-Compete", "required": False},
    ],
    "indemnification": [
        {"clause_type": "indemnification", "label": "Indemnification", "required": True},
        {"clause_type": "liability", "label": "Limitation of Liability", "required": True},
        {"clause_type": "insurance", "label": "Insurance Requirements", "required": False},
    ],
    "liability": [
        {"clause_type": "liability", "label": "Limitation of Liability", "required": True},
        {"clause_type": "indemnification", "label": "Indemnification", "required": True},
        {"clause_type": "consequential_damages", "label": "Consequential Damages", "required": False},
        {"clause_type": "insurance", "label": "Insurance Requirements", "required": False},
    ],
    "termination": [
        {"clause_type": "termination", "label": "Termination", "required": True},
        {"clause_type": "notice_period", "label": "Notice Period", "required": True},
        {"clause_type": "auto_renewal", "label": "Auto-Renewal", "required": False},
        {"clause_type": "for_cause_termination", "label": "For-Cause Termination", "required": False},
    ],
    "intellectual_property": [
        {"clause_type": "intellectual_property", "label": "Intellectual Property", "required": True},
        {"clause_type": "ip_ownership", "label": "IP Ownership", "required": True},
        {"clause_type": "license", "label": "License Grant", "required": True},
        {"clause_type": "non_compete", "label": "Non-Compete", "required": False},
    ],
}


@router.post(
    "/{session_id}/clauses/{clause_id}/apply-bundle",
    summary="Apply a Knowledge Center clause bundle to a negotiation clause",
)
async def apply_clause_bundle(
    session_id: str,
    clause_id: str,
    request: ApplyBundleRequest,
    service: NegotiationService = Depends(get_service),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Fetch the recommended bundle for a clause type and create suggestion
    redlines for each template in the bundle."""
    from app.domains.redline_templates.repository import RedlineTemplateRepository

    session_obj = await service.get_session(session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find matching bundle
    bundle = _BUNDLES.get(request.clause_type)
    if not bundle:
        for key, items in _BUNDLES.items():
            if any(item["clause_type"] == request.clause_type for item in items):
                bundle = items
                break

    if not bundle:
        raise HTTPException(
            status_code=404,
            detail=f"No bundle found for clause type '{request.clause_type}'",
        )

    # Check which templates exist
    repo = RedlineTemplateRepository(session, tenant_id)
    redline_ids: list[str] = []
    templates_applied = 0

    for item in bundle:
        try:
            templates = await repo.list(clause_type=item["clause_type"], limit=1)
        except Exception:
            templates = []

        has_template = len(templates) > 0
        template_name = templates[0].get("name", item["label"]) if has_template else None

        if not has_template:
            continue

        # Create a suggestion-type redline for each template in the bundle
        redline_data = {
            "clause_id": clause_id,
            "type": "suggestion",
            "title": f"Bundle: {item['label']}",
            "original_text": "",
            "modified_text": f"[Template: {template_name}] Suggested {item['label']} language — apply from Knowledge Center.",
            "risk_level": "medium",
            "ai_generated": True,
        }

        try:
            redline = await service.create_redline(session_id, redline_data)
            if redline:
                rid = getattr(redline, "id", None) or getattr(redline, "redline_id", None) or str(redline)
                redline_ids.append(rid)
                templates_applied += 1
        except Exception:
            continue

    return BundleApplyResponse(
        status="success" if templates_applied > 0 else "partial",
        session_id=session_id,
        clause_type=request.clause_type,
        redline_ids=redline_ids,
        templates_applied=templates_applied,
        message=f"Applied {templates_applied} bundle template(s) to clause {clause_id}",
    )
