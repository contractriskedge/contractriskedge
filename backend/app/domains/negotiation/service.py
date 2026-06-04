"""Negotiation service layer — business logic for session lifecycle, stage transitions, KPI aggregation.

Uses NegotiationRepository for persistence.
Uses governance_audit_events for audit logging (no separate audit table).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.domains.negotiation.models import (
    NegotiationComment,
    NegotiationIssue,
    NegotiationParticipant,
    NegotiationRedline,
    NegotiationSession,
    NegotiationStage,
    NegotiationVersion,
    VersionStatus,
)
from app.domains.negotiation.repository import NegotiationRepository
from app.domains.negotiation.schemas import (
    NEGOTIATION_STAGES,
    ClauseContentSchema,
    CommentCreateRequest,
    DocumentVersionSchema,
    IssueCreateRequest,
    NegotiationCreateRequest,
    NegotiationIssueSchema,
    NegotiationSessionResponse,
    NegotiationSessionSummary,
    NegotiationUpdateRequest,
    ParticipantCreateRequest,
    ParticipantSchema,
    RedlineCreateRequest,
    RedlineEntrySchema,
)
from app.domains.workflows.runtime import WorkflowExecutionEngine, WorkflowStatus
from app.domains.workflow_packs.repository import WorkflowRepository

logger = logging.getLogger(__name__)

# Global workflow engine reference (set by router on startup)
_workflow_engine: Optional[WorkflowExecutionEngine] = None


def set_workflow_engine(engine: WorkflowExecutionEngine) -> None:
    """Set the global workflow engine for negotiation integration."""
    global _workflow_engine
    _workflow_engine = engine


def get_workflow_engine() -> Optional[WorkflowExecutionEngine]:
    """Get the global workflow engine."""
    return _workflow_engine

logger = logging.getLogger(__name__)

# Valid stage transitions
STAGE_TRANSITIONS = {
    "drafting": ["review"],
    "review": ["negotiating", "approved"],
    "negotiating": ["review", "approved", "escalated"],
    "approved": ["executed"],
    "executed": [],
    "escalated": ["negotiating", "approved"],
}


class NegotiationService:
    """Business logic for negotiation operations."""

    def __init__(
        self,
        repo: NegotiationRepository,
        actor_id: str,
        workflow_repo: Optional[WorkflowRepository] = None,
    ):
        self.repo = repo
        self.actor_id = actor_id
        self.tenant_id = repo.tenant_id
        self.workflow_repo = workflow_repo

    # ── Session Lifecycle ────────────────────────────────────────

    async def create_session(self, body: NegotiationCreateRequest) -> NegotiationSessionResponse:
        """Create a new negotiation session with initial version."""
        session_id = str(uuid.uuid4())

        session = NegotiationSession(
            session_id=session_id,
            tenant_id=self.tenant_id,
            contract_id=body.contract_id,
            contract_title=body.contract_title,
            counterparty=body.counterparty,
            stage=NegotiationStage.DRAFTING.value,
            health_score=50.0,
        )
        await self.repo.create_session(session)

        # Create initial version from provided clauses or empty
        version = NegotiationVersion(
            session_id=session_id,
            version_number=1,
            label="Original Draft",
            author=self.actor_id,
            status=VersionStatus.CURRENT.value,
            clauses=[c.model_dump(by_alias=False) for c in (body.clauses or [])],
            word_count=sum(len(c.content.split()) for c in (body.clauses or [])),
        )
        await self.repo.create_version(version)

        # Log audit
        await self.repo.log_audit(
            session_id=session_id,
            event_type="negotiation.created",
            actor_id=self.actor_id,
            new_state={"stage": "drafting", "contract_title": body.contract_title},
            change_summary=f"Negotiation created for {body.contract_title}",
        )

        # Start a workflow instance for this negotiation
        await self._sync_workflow(session_id, "drafting", body.contract_title)

        return await self._build_session_response(session_id)

    async def get_session(self, session_id: str) -> Optional[NegotiationSessionResponse]:
        """Get full session detail with all children."""
        return await self._build_session_response(session_id)

    async def list_sessions(
        self, stage: Optional[str] = None, page: int = 1, page_size: int = 20,
        search: Optional[str] = None,
    ) -> tuple[list[NegotiationSessionSummary], int]:
        """List sessions with pagination and optional text search."""
        sessions, total = await self.repo.list_sessions(
            stage=stage, page=page, page_size=page_size, search=search,
        )
        summaries = []
        for s in sessions:
            summaries.append(NegotiationSessionSummary(
                id=s.session_id,
                contractTitle=s.contract_title,
                counterparty=s.counterparty,
                stage=s.stage,
                healthScore=s.health_score,
                startedAt=s.started_at,
                updatedAt=s.updated_at,
            ))
        return summaries, total

    async def update_session(
        self, session_id: str, body: NegotiationUpdateRequest
    ) -> Optional[NegotiationSessionResponse]:
        """Update session stage and/or health score."""
        kwargs = {}
        if body.stage is not None:
            # Validate stage transition
            current = await self.repo.get_session(session_id)
            if not current:
                return None
            if body.stage not in STAGE_TRANSITIONS.get(current.stage, []):
                allowed = STAGE_TRANSITIONS.get(current.stage, [])
                raise ValueError(
                    f"Cannot transition from '{current.stage}' to '{body.stage}'. "
                    f"Allowed transitions: {allowed}"
                )
            kwargs["stage"] = body.stage
            if body.stage in ("approved", "executed"):
                kwargs["completed_at"] = datetime.now(timezone.utc)

            await self.repo.log_audit(
                session_id=session_id,
                event_type="negotiation.stage_changed",
                actor_id=self.actor_id,
                previous_state={"stage": current.stage},
                new_state={"stage": body.stage},
                change_summary=f"Stage changed from {current.stage} to {body.stage}",
            )

            # Sync workflow on stage change
            await self._sync_workflow(
                session_id, body.stage, current.contract_title
            )

        if body.health_score is not None:
            kwargs["health_score"] = body.health_score

        if not kwargs:
            return await self._build_session_response(session_id)

        updated = await self.repo.update_session(session_id, **kwargs)
        if not updated:
            return None
        return await self._build_session_response(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all cascaded children."""
        return await self.repo.delete_session(session_id)

    # ── Redlines ─────────────────────────────────────────────────

    async def create_redline(
        self, session_id: str, body: RedlineCreateRequest
    ) -> Optional[dict[str, Any]]:
        """Create a new redline on a session."""
        session = await self.repo.get_session(session_id)
        if not session:
            return None

        redline = NegotiationRedline(
            session_id=session_id,
            clause_id=body.clause_id,
            type=body.type,
            title=body.title,
            original_text=body.original_text,
            modified_text=body.modified_text,
            author=self.actor_id,
            risk_level=body.risk_level,
        )
        created = await self.repo.create_redline(redline)

        await self.repo.log_audit(
            session_id=session_id,
            event_type="redline.created",
            actor_id=self.actor_id,
            new_state={"clause_id": body.clause_id, "type": body.type, "status": "pending"},
            change_summary=f"Redline '{body.title}' created on clause {body.clause_id}",
        )

        return self._redline_to_dict(created)

    async def list_redlines(
        self, session_id: str, clause_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """List redlines for a session."""
        redlines = await self.repo.list_redlines(session_id, clause_id)
        return [self._redline_to_dict(r) for r in redlines]

    async def update_redline_status(
        self, redline_id: str, status: str
    ) -> Optional[dict[str, Any]]:
        """Accept, reject, or supersede a redline."""
        updated = await self.repo.update_redline_status(redline_id, status)
        if not updated:
            return None
        return self._redline_to_dict(updated)

    # ── Issues ───────────────────────────────────────────────────

    async def create_issue(
        self, session_id: str, body: IssueCreateRequest
    ) -> Optional[dict[str, Any]]:
        """Create a new issue on a session."""
        session = await self.repo.get_session(session_id)
        if not session:
            return None

        issue = NegotiationIssue(
            session_id=session_id,
            clause_id=body.clause_id,
            title=body.title,
            description=body.description,
            severity=body.severity,
            created_by=self.actor_id,
            category=body.category,
            assignee=body.assignee,
            due_date=body.due_date,
        )
        created = await self.repo.create_issue(issue)

        await self.repo.log_audit(
            session_id=session_id,
            event_type="issue.created",
            actor_id=self.actor_id,
            new_state={"title": body.title, "severity": body.severity, "status": "open"},
            change_summary=f"Issue '{body.title}' created",
        )

        return self._issue_to_dict(created)

    async def list_issues(self, session_id: str) -> list[dict[str, Any]]:
        """List issues for a session."""
        issues = await self.repo.list_issues(session_id)
        return [self._issue_to_dict(i) for i in issues]

    async def update_issue(
        self, issue_id: str, **kwargs: Any
    ) -> Optional[dict[str, Any]]:
        """Update issue status, severity, escalation, etc."""
        # Log escalation changes
        if "escalation_level" in kwargs:
            current = await self._get_issue_raw(issue_id)
            if current:
                await self.repo.log_audit(
                    session_id=current.session_id,
                    event_type="issue.escalated",
                    actor_id=self.actor_id,
                    previous_state={"escalation_level": current.escalation_level},
                    new_state={"escalation_level": kwargs["escalation_level"]},
                    change_summary=f"Issue escalated to level {kwargs['escalation_level']}",
                )

        updated = await self.repo.update_issue(issue_id, **kwargs)
        if not updated:
            return None
        return self._issue_to_dict(updated)

    # ── Comments ─────────────────────────────────────────────────

    async def create_comment(
        self, session_id: str, body: CommentCreateRequest
    ) -> Optional[dict[str, Any]]:
        """Create a comment on a redline, issue, or as a reply."""
        session = await self.repo.get_session(session_id)
        if not session:
            return None

        comment = NegotiationComment(
            session_id=session_id,
            redline_id=body.redline_id,
            issue_id=body.issue_id,
            clause_id=body.clause_id,
            parent_id=body.parent_id,
            author=self.actor_id,
            content=body.content,
            mentions=body.mentions,
        )
        created = await self.repo.create_comment(comment)

        await self.repo.log_audit(
            session_id=session_id,
            event_type="comment.created",
            actor_id=self.actor_id,
            change_summary=f"Comment added by {self.actor_id}",
        )

        return self._comment_to_dict(created)

    async def list_comments(
        self,
        session_id: str,
        redline_id: Optional[str] = None,
        issue_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List comments for a session."""
        comments = await self.repo.list_comments(session_id, redline_id, issue_id)
        return [self._comment_to_dict(c) for c in comments]

    async def resolve_comment(
        self, comment_id: str
    ) -> Optional[dict[str, Any]]:
        """Mark a comment as resolved."""
        updated = await self.repo.resolve_comment(comment_id, self.actor_id)
        if not updated:
            return None
        return self._comment_to_dict(updated)

    # ── Participants ─────────────────────────────────────────────

    async def add_participant(
        self, session_id: str, body: ParticipantCreateRequest
    ) -> Optional[dict[str, Any]]:
        """Add a participant to a session."""
        session = await self.repo.get_session(session_id)
        if not session:
            return None

        participant = NegotiationParticipant(
            session_id=session_id,
            name=body.name,
            role=body.role,
            department=body.department,
        )
        created = await self.repo.create_participant(participant)
        return self._participant_to_dict(created)

    async def list_participants(self, session_id: str) -> list[dict[str, Any]]:
        """List participants in a session."""
        participants = await self.repo.list_participants(session_id)
        return [self._participant_to_dict(p) for p in participants]

    async def update_participant_role(
        self, participant_id: str, role: str
    ) -> Optional[dict[str, Any]]:
        """Update a participant's role."""
        updated = await self.repo.update_participant_role(participant_id, role)
        if not updated:
            return None
        return self._participant_to_dict(updated)

    async def remove_participant(self, participant_id: str) -> bool:
        """Remove a participant."""
        return await self.repo.delete_participant(participant_id)

    # ── KPIs ─────────────────────────────────────────────────────

    async def get_kpis(self) -> dict[str, Any]:
        """Get cross-session KPI aggregates."""
        return await self.repo.get_kpis()

    # ── Activities / Audit Log ───────────────────────────────────

    async def get_activities(self, session_id: str) -> list[dict[str, Any]]:
        """Get activity log for a session from governance_audit_events."""
        from app.domains.playbook.models import GovernanceAuditEvent
        from sqlalchemy import select

        query = (
            select(GovernanceAuditEvent)
            .where(
                GovernanceAuditEvent.entity_id == session_id,
                GovernanceAuditEvent.entity_type == "negotiation_session",
                GovernanceAuditEvent.tenant_id == self.tenant_id,
            )
            .order_by(GovernanceAuditEvent.created_at.desc())
            .limit(100)
        )
        result = await self.repo.session.execute(query)
        events = result.scalars().all()

        return [
            {
                "id": e.event_id,
                "type": e.event_type,
                "user": e.actor_id or "system",
                "userAvatar": "",
                "action": e.event_type.replace("negotiation.", "").replace("redline.", "").replace("issue.", "").replace("comment.", ""),
                "description": e.change_summary or "",
                "timestamp": e.created_at,
                "clauseId": None,
                "versionId": None,
            }
            for e in events
        ]

    # ── Internal Helpers ─────────────────────────────────────────

    async def _sync_workflow(
        self, session_id: str, stage: str, contract_title: str
    ) -> None:
        """Sync negotiation stage to workflow engine and persist to database.

        Creates a workflow instance on first call (session creation),
        updates metadata on subsequent stage changes.
        Uses WorkflowRepository to persist to workflow_instances table.
        This is fire-and-forget — failures do not block the API.
        """
        engine = get_workflow_engine()
        if not engine:
            logger.debug("No workflow engine available — skipping workflow sync")
            return

        try:
            # Ensure persistence adapter is wired to the engine
            if engine._persistence is None and self.workflow_repo is not None:
                from app.domains.workflows.runtime.persistence import WorkflowPersistenceAdapter
                adapter = WorkflowPersistenceAdapter(self.workflow_repo)
                engine.set_persistence(adapter)
                logger.debug("Wired persistence adapter to workflow engine")

            # Map negotiation stages to workflow steps
            stage_map = {
                "drafting": "intake",
                "review": "legal_review",
                "negotiating": "negotiation",
                "approved": "final_approval",
                "executed": "execution",
                "escalated": "escalation",
            }

            # Check if a workflow instance already exists for this session
            existing = None
            existing_db = None
            for wf_id, inst in engine._instances.items():
                if inst.context.metadata.get("negotiation_id") == session_id:
                    existing = inst
                    break

            # Also check database directly
            if not existing and self.workflow_repo:
                from app.domains.workflow_packs.models import WorkflowInstance as WFInstance
                from sqlalchemy import select

                query = (
                    select(WFInstance)
                    .where(
                        WFInstance.workflow_type == "negotiation_review",
                        WFInstance.correlation_id == session_id,
                    )
                )
                result = await self.workflow_repo.session.execute(query)
                existing_db = result.scalar_one_or_none()

            if existing is None and existing_db is None:
                # Start a new workflow (in-memory)
                runtime_instance = await engine.start_workflow(
                    workflow_type="negotiation_review",
                    tenant_id=self.tenant_id,
                    actor_id=self.actor_id,
                    data={"contract_title": contract_title, "negotiation_stage": stage},
                    metadata={"negotiation_id": session_id},
                    correlation_id=session_id,
                )

                # Persist to database
                if self.workflow_repo and runtime_instance:
                    from app.domains.workflow_packs.models import WorkflowInstance as WFDbModel
                    from datetime import datetime, timezone

                    db_instance = WFDbModel(
                        workflow_id=runtime_instance.workflow_id,
                        tenant_id=self.tenant_id,
                        pack_id=None,
                        workflow_type="negotiation_review",
                        version=runtime_instance.version,
                        status=runtime_instance.status.value,
                        context_data=runtime_instance.context.data,
                        metadata_json=runtime_instance.context.metadata,
                        correlation_id=runtime_instance.context.correlation_id,
                        current_step=0,
                        sla_deadline=(
                            datetime.fromisoformat(runtime_instance.sla_deadline)
                            if runtime_instance.sla_deadline else None
                        ),
                        started_at=datetime.now(timezone.utc),
                    )
                    await self.workflow_repo.create_instance(db_instance)
                    logger.info(
                        "Persisted workflow %s for negotiation %s (stage=%s)",
                        runtime_instance.workflow_id[:8], session_id[:8], stage,
                    )
            else:
                # Update existing workflow stage in metadata
                inst = existing or existing_db
                wf_id = inst.workflow_id if hasattr(inst, 'workflow_id') else inst.workflow_id
                logger.debug(
                    "Workflow already exists for negotiation %s (stage=%s)",
                    session_id[:8], stage,
                )

                # When negotiation reaches executed, complete the workflow
                if stage == "executed":
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)

                    # Update in-memory instance
                    if existing:
                        existing.status = WorkflowStatus.COMPLETED
                        existing.completed_at = now.isoformat()

                    # Update database via persistence adapter
                    if self.workflow_repo:
                        await self.workflow_repo.update_instance(
                            wf_id,
                            status=WorkflowStatus.COMPLETED.value,
                            completed_at=now,
                        )
                        logger.info(
                            "Completed workflow %s for negotiation %s (executed)",
                            wf_id[:8], session_id[:8],
                        )
        except Exception:
            logger.exception(
                "Failed to sync workflow for negotiation %s", session_id[:8],
            )

    async def _build_session_response(
        self, session_id: str
    ) -> Optional[NegotiationSessionResponse]:
        """Build full session response with all nested children."""
        session = await self.repo.get_session(session_id)
        if not session:
            return None

        # Determine current version
        current_version_id = None
        for v in (session.versions or []):
            if v.status == VersionStatus.CURRENT.value:
                current_version_id = v.version_id
                break

        versions = []
        for v in (session.versions or []):
            versions.append(DocumentVersionSchema(
                id=v.version_id,
                label=v.label,
                timestamp=v.created_at,
                author=v.author,
                authorAvatar=v.author_avatar or "",
                status=v.status,
                content=[ClauseContentSchema(**c) for c in (v.clauses or [])],
                wordCount=v.word_count,
                changeSummary=v.change_summary or "",
            ))

        # Group comments by redline_id and issue_id
        redline_comments: dict[str, list[NegotiationComment]] = {}
        issue_comments: dict[str, list[NegotiationComment]] = {}
        for c in (session.comments or []):
            if c.redline_id:
                redline_comments.setdefault(c.redline_id, []).append(c)
            if c.issue_id:
                issue_comments.setdefault(c.issue_id, []).append(c)

        def _build_comment_tree(comments: list[NegotiationComment]) -> list[dict]:
            """Build nested comment tree from flat list."""
            top_level = [c for c in comments if not c.parent_id]
            result = []
            for c in top_level:
                replies = [rc for rc in comments if rc.parent_id == c.comment_id]
                result.append(self._comment_to_dict(c, replies))
            return result

        redlines = []
        for r in (session.redlines or []):
            redlines.append(RedlineEntrySchema(
                id=r.redline_id,
                type=r.type,
                clauseId=r.clause_id,
                sectionNumber="",
                title=r.title,
                originalText=r.original_text,
                modifiedText=r.modified_text,
                author=r.author,
                authorAvatar=r.author_avatar or "",
                timestamp=r.created_at,
                riskLevel=r.risk_level,
                category="",
                status=r.status,
                aiGenerated=r.ai_generated,
                aiConfidence=r.ai_confidence,
                negotiationImpact=r.negotiation_impact,
                benchmarkDeviation=r.benchmark_deviation,
                comments=_build_comment_tree(redline_comments.get(r.redline_id, [])),
            ))

        issues = []
        for i in (session.issues or []):
            issues.append(NegotiationIssueSchema(
                id=i.issue_id,
                title=i.title,
                description=i.description,
                clauseId=i.clause_id,
                sectionNumber="",
                severity=i.severity,
                status=i.status,
                assignee=i.assignee,
                assigneeAvatar=i.assignee_avatar or "",
                dueDate=i.due_date,
                createdBy=i.created_by,
                createdAt=i.created_at,
                updatedAt=i.updated_at,
                category=i.category,
                escalationLevel=i.escalation_level,
                comments=_build_comment_tree(issue_comments.get(i.issue_id, [])),
                tags=i.tags or [],
            ))

        participants = [
            ParticipantSchema(
                id=p.participant_id,
                name=p.name,
                avatar=p.avatar or "",
                role=p.role,
                department=p.department or "",
                isOnline=p.is_online,
                lastActive=p.last_active,
                reviewedClauses=p.reviewed_clauses,
                pendingApprovals=p.pending_approvals,
            )
            for p in (session.participants or [])
        ]

        return NegotiationSessionResponse(
            id=session.session_id,
            contractTitle=session.contract_title,
            counterparty=session.counterparty,
            stage=session.stage,
            versions=versions,
            currentVersionId=current_version_id,
            redlines=redlines,
            issues=issues,
            participants=participants,
            healthScore=session.health_score,
            startedAt=session.started_at,
            updatedAt=session.updated_at,
        )

    def _redline_to_dict(self, r: NegotiationRedline) -> dict[str, Any]:
        return {
            "id": r.redline_id,
            "type": r.type,
            "clauseId": r.clause_id,
            "sectionNumber": "",
            "title": r.title,
            "originalText": r.original_text,
            "modifiedText": r.modified_text,
            "author": r.author,
            "authorAvatar": r.author_avatar or "",
            "timestamp": r.created_at,
            "riskLevel": r.risk_level,
            "category": "",
            "status": r.status,
            "aiGenerated": r.ai_generated,
            "aiConfidence": r.ai_confidence,
            "negotiationImpact": r.negotiation_impact,
            "benchmarkDeviation": r.benchmark_deviation,
            "comments": [],
        }

    def _issue_to_dict(self, i: NegotiationIssue) -> dict[str, Any]:
        return {
            "id": i.issue_id,
            "title": i.title,
            "description": i.description,
            "clauseId": i.clause_id,
            "sectionNumber": "",
            "severity": i.severity,
            "status": i.status,
            "assignee": i.assignee,
            "assigneeAvatar": i.assignee_avatar or "",
            "dueDate": i.due_date,
            "createdBy": i.created_by,
            "createdAt": i.created_at,
            "updatedAt": i.updated_at,
            "category": i.category,
            "escalationLevel": i.escalation_level,
            "comments": [],
            "tags": i.tags or [],
        }

    def _comment_to_dict(
        self, c: NegotiationComment, replies: Optional[list[NegotiationComment]] = None
    ) -> dict[str, Any]:
        result = {
            "id": c.comment_id,
            "author": c.author,
            "authorAvatar": c.author_avatar or "",
            "authorRole": c.author_role or "",
            "content": c.content,
            "timestamp": c.created_at,
            "status": c.status,
            "mentions": c.mentions or [],
            "replies": [],
            "clauseId": c.clause_id,
            "resolvedBy": c.resolved_by,
            "resolvedAt": c.resolved_at,
        }
        if replies:
            result["replies"] = [self._comment_to_dict(r) for r in replies]
        return result

    def _participant_to_dict(self, p: NegotiationParticipant) -> dict[str, Any]:
        return {
            "id": p.participant_id,
            "name": p.name,
            "avatar": p.avatar or "",
            "role": p.role,
            "department": p.department or "",
            "isOnline": p.is_online,
            "lastActive": p.last_active,
            "reviewedClauses": p.reviewed_clauses,
            "pendingApprovals": p.pending_approvals,
        }

    async def _get_issue_raw(self, issue_id: str) -> Optional[NegotiationIssue]:
        """Get raw issue ORM object for internal use."""
        from sqlalchemy import select
        from app.domains.negotiation.models import NegotiationIssue as IssueModel

        query = select(IssueModel).where(IssueModel.issue_id == issue_id)
        result = await self.repo.session.execute(query)
        return result.scalar_one_or_none()


# ── Event Handlers ────────────────────────────────────────────────


async def on_review_finalized(event) -> None:
    """Auto-create a negotiation session when a review is approved or finalized.

    Registered on the event bus at application startup for both
    ReviewApproved and ReviewFinalized events.
    Fire-and-forget — failures are logged but don't block the caller.
    """
    import logging
    logger = logging.getLogger(__name__)
    review_id = event.data.get("review_id")
    tenant_id = event.tenant_id
    logger.info("Handler entered: event_type=%s review_id=%s", event.event_type, review_id[:8] if review_id else None)
    if not review_id or not tenant_id:
        logger.warning("on_review_finalized: missing review_id or tenant_id")
        return
    # Skip if this is a ReviewApproved event but review is not yet approved
    # (the event fires after approval, so this is just a safety check)
    try:
        # Build a NegotiationService instance for the target tenant
        from app.domains.negotiation.repository import NegotiationRepository

        # Build a NegotiationService instance for the target tenant
        from app.domains.negotiation.repository import NegotiationRepository
        from app.domains.workflow_packs.repository import WorkflowRepository
        from app.kernel.database.session import TenantAwareSessionFactory
        from app.config import settings

        factory = TenantAwareSessionFactory(
            database_url=settings.database_url,
            pool_size=2,
            max_overflow=2,
        )
        session = await factory.create_session(
            tenant_id=tenant_id,
            user_id=event.actor_id or "system",
            user_role="admin",
        )
        try:
            repo = NegotiationRepository(session, tenant_id)
            wf_repo = WorkflowRepository(session, tenant_id)
            svc = NegotiationService(
                repo=repo,
                actor_id=event.actor_id or "system",
                workflow_repo=wf_repo,
            )

            # Fetch the review to get its document filename
            from app.domains.ingestion.models import UploadSession
            from app.domains.review.models import ContractReview
            from sqlalchemy import select

            review_row = await session.execute(
                select(ContractReview, UploadSession.filename)
                .outerjoin(UploadSession, ContractReview.upload_id == UploadSession.upload_id)
                .where(ContractReview.review_id == review_id)
            )
            row = review_row.one_or_none()
            if not row:
                logger.warning("on_review_finalized: review %s not found", review_id)
                return

            review, filename = row
            contract_title = filename or f"Review {review_id[:8]}"

            # Check if a negotiation session already exists for this review
            existing = await session.execute(
                select(NegotiationSession.session_id)
                .where(
                    NegotiationSession.tenant_id == tenant_id,
                    NegotiationSession.contract_id == review_id,
                )
            )
            if existing.scalar_one_or_none():
                logger.info(
                    "Negotiation session already exists for review %s — skipping",
                    review_id[:8],
                )
                return

            # Create the negotiation session
            from app.domains.negotiation.schemas import NegotiationCreateRequest

            create_body = NegotiationCreateRequest(
                contract_id=review_id,
                contract_title=contract_title,
                counterparty="",
            )
            result = await svc.create_session(create_body)
            await session.commit()
            logger.info(
                "Auto-created negotiation session %s for review %s (%s)",
                result.id[:8] if hasattr(result, 'id') else "?",
                review_id[:8],
                contract_title,
            )
        finally:
            await session.close()
    except Exception:
        logger.exception("on_review_finalized: failed to create negotiation session")
