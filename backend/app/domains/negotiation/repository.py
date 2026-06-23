"""Negotiation ORM repository — typed CRUD for all negotiation models.

Follows the same pattern as WorkflowRepository from Sprint 17.
Uses governance_audit_events for audit logging (no separate audit table).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.negotiation.models import (
    CommentStatus,
    IssueStatus,
    NegotiationComment,
    NegotiationIssue,
    NegotiationParticipant,
    NegotiationRedline,
    NegotiationSession,
    NegotiationVersion,
    RedlineStatus,
)

logger = logging.getLogger(__name__)


class NegotiationRepository:
    """Typed CRUD repository for negotiation domain models."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    # ── Sessions ─────────────────────────────────────────────────

    async def create_session(self, session_obj: NegotiationSession) -> NegotiationSession:
        """Create a new negotiation session."""
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def get_latest_session_for_contract(
        self, contract_id: str,
    ) -> Optional[NegotiationSession]:
        """Return the most recently updated session linked to a review/contract."""
        query = (
            select(NegotiationSession)
            .where(
                and_(
                    NegotiationSession.tenant_id == self.tenant_id,
                    NegotiationSession.contract_id == contract_id,
                )
            )
            .order_by(NegotiationSession.updated_at.desc())
            .limit(1)
            .options(
                selectinload(NegotiationSession.versions),
                selectinload(NegotiationSession.redlines),
                selectinload(NegotiationSession.issues),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        """Get a session with all nested children loaded."""
        query = (
            select(NegotiationSession)
            .where(
                and_(
                    NegotiationSession.session_id == session_id,
                    NegotiationSession.tenant_id == self.tenant_id,
                )
            )
            .options(
                selectinload(NegotiationSession.versions),
                selectinload(NegotiationSession.redlines),
                selectinload(NegotiationSession.issues),
                selectinload(NegotiationSession.comments),
                selectinload(NegotiationSession.participants),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        stage: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: Optional[str] = None,
    ) -> tuple[list[NegotiationSession], int]:
        """List sessions with pagination and optional stage/text filter."""
        conditions = [NegotiationSession.tenant_id == self.tenant_id]
        if stage:
            conditions.append(NegotiationSession.stage == stage)
        if search:
            from sqlalchemy import or_
            conditions.append(
                or_(
                    NegotiationSession.contract_title.ilike(f"%{search}%"),
                    NegotiationSession.counterparty.ilike(f"%{search}%"),
                )
            )

        # Count
        count_query = select(func.count()).select_from(NegotiationSession).where(and_(*conditions))
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch
        query = (
            select(NegotiationSession)
            .where(and_(*conditions))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        sort_col = getattr(NegotiationSession, sort_by, NegotiationSession.created_at)
        query = query.order_by(sort_col.asc() if sort_order == "asc" else sort_col.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update_session(
        self, session_id: str, **kwargs: Any
    ) -> Optional[NegotiationSession]:
        """Update a negotiation session."""
        kwargs["updated_at"] = datetime.now(timezone.utc)
        query = (
            update(NegotiationSession)
            .where(
                and_(
                    NegotiationSession.session_id == session_id,
                    NegotiationSession.tenant_id == self.tenant_id,
                )
            )
            .values(**kwargs)
            .returning(NegotiationSession)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session (cascades to children)."""
        query = (
            delete(NegotiationSession)
            .where(
                and_(
                    NegotiationSession.session_id == session_id,
                    NegotiationSession.tenant_id == self.tenant_id,
                )
            )
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount > 0

    # ── Sessions — KPIs ──────────────────────────────────────────

    async def get_kpis(self) -> dict[str, Any]:
        """Get cross-session KPI aggregates."""
        base = select(NegotiationSession).where(
            NegotiationSession.tenant_id == self.tenant_id
        )

        # Total sessions
        total_query = select(func.count()).select_from(NegotiationSession).where(
            NegotiationSession.tenant_id == self.tenant_id
        )
        total = (await self.session.execute(total_query)).scalar() or 0

        # Active (not approved/executed)
        active_query = select(func.count()).select_from(NegotiationSession).where(
            and_(
                NegotiationSession.tenant_id == self.tenant_id,
                NegotiationSession.stage.notin_(["approved", "executed"]),
            )
        )
        active = (await self.session.execute(active_query)).scalar() or 0

        # By stage
        stages = ["drafting", "review", "negotiating", "approved", "executed", "escalated"]
        by_stage = {}
        for s in stages:
            q = select(func.count()).select_from(NegotiationSession).where(
                and_(NegotiationSession.tenant_id == self.tenant_id, NegotiationSession.stage == s)
            )
            c = (await self.session.execute(q)).scalar() or 0
            if c > 0:
                by_stage[s] = c

        # Escalated count
        escalated_query = select(func.count()).select_from(NegotiationSession).where(
            and_(
                NegotiationSession.tenant_id == self.tenant_id,
                NegotiationSession.stage == "escalated",
            )
        )
        escalated = (await self.session.execute(escalated_query)).scalar() or 0

        # Generate sparkline data (weekly session creation counts for last 12 weeks)
        from datetime import timedelta
        sparkline_data: dict[str, list[int]] = {
            "sessions_created": [],
            "redlines_created": [],
            "issues_resolved": [],
        }
        now = datetime.now(timezone.utc)
        for week_offset in range(11, -1, -1):
            week_start = now - timedelta(weeks=week_offset + 1)
            week_end = now - timedelta(weeks=week_offset)

            # Sessions created in this week
            sq = select(func.count()).select_from(NegotiationSession).where(
                and_(
                    NegotiationSession.tenant_id == self.tenant_id,
                    NegotiationSession.created_at >= week_start,
                    NegotiationSession.created_at < week_end,
                )
            )
            sparkline_data["sessions_created"].append((await self.session.execute(sq)).scalar() or 0)

            # Redlines created in this week
            try:
                rq = select(func.count()).select_from(NegotiationRedline).where(
                    and_(
                        NegotiationRedline.created_at >= week_start,
                        NegotiationRedline.created_at < week_end,
                    )
                )
                sparkline_data["redlines_created"].append((await self.session.execute(rq)).scalar() or 0)
            except Exception:
                sparkline_data["redlines_created"].append(0)

            # Issues resolved in this week
            try:
                iq = select(func.count()).select_from(NegotiationIssue).where(
                    and_(
                        NegotiationIssue.status.in_(["resolved", "accepted"]),
                        NegotiationIssue.updated_at >= week_start,
                        NegotiationIssue.updated_at < week_end,
                    )
                )
                sparkline_data["issues_resolved"].append((await self.session.execute(iq)).scalar() or 0)
            except Exception:
                sparkline_data["issues_resolved"].append(0)

        return {
            "total_sessions": total,
            "active_sessions": active,
            "by_stage": by_stage,
            "escalated_count": escalated,
            "sparkline_data": sparkline_data,
        }

    # ── Versions ─────────────────────────────────────────────────

    async def create_version(self, version: NegotiationVersion) -> NegotiationVersion:
        """Create a new document version."""
        self.session.add(version)
        await self.session.flush()
        return version

    async def update_version_status(self, version_id: str, status: str) -> Optional[NegotiationVersion]:
        """Update the status of a version (e.g. CURRENT → SUPERSEDED)."""
        query = (
            update(NegotiationVersion)
            .where(NegotiationVersion.version_id == version_id)
            .values(status=status)
            .returning(NegotiationVersion)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def update_version_clauses(
        self,
        version_id: str,
        clauses: list[dict],
        *,
        change_summary: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Optional[NegotiationVersion]:
        """Replace clause snapshots on a document version."""
        word_count = sum(len(str(c.get("content", "")).split()) for c in clauses)
        values: dict[str, Any] = {
            "clauses": clauses,
            "word_count": word_count,
        }
        if change_summary is not None:
            values["change_summary"] = change_summary
        if label is not None:
            values["label"] = label
        query = (
            update(NegotiationVersion)
            .where(NegotiationVersion.version_id == version_id)
            .values(**values)
            .returning(NegotiationVersion)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def list_versions(self, session_id: str) -> list[NegotiationVersion]:
        """List all versions for a session, scoped to tenant."""
        query = (
            select(NegotiationVersion)
            .join(NegotiationSession, NegotiationSession.session_id == NegotiationVersion.session_id)
            .where(
                and_(
                    NegotiationVersion.session_id == session_id,
                    NegotiationSession.tenant_id == self.tenant_id,
                )
            )
            .order_by(NegotiationVersion.version_number.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ── Redlines ─────────────────────────────────────────────────

    async def create_redline(self, redline: NegotiationRedline) -> NegotiationRedline:
        """Create a new redline."""
        self.session.add(redline)
        await self.session.flush()
        return redline

    async def list_redlines(
        self, session_id: str, clause_id: Optional[str] = None
    ) -> list[NegotiationRedline]:
        """List redlines for a session, scoped to tenant."""
        conditions = [NegotiationRedline.session_id == session_id]
        if clause_id:
            conditions.append(NegotiationRedline.clause_id == clause_id)
        query = (
            select(NegotiationRedline)
            .join(NegotiationSession, NegotiationSession.session_id == NegotiationRedline.session_id)
            .where(and_(*conditions, NegotiationSession.tenant_id == self.tenant_id))
            .order_by(NegotiationRedline.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_redline_status(
        self, redline_id: str, status: str
    ) -> Optional[NegotiationRedline]:
        """Update a redline's status, scoped to tenant."""
        query = (
            update(NegotiationRedline)
            .where(
                and_(
                    NegotiationRedline.redline_id == redline_id,
                    NegotiationRedline.session_id.in_(
                        select(NegotiationSession.session_id).where(
                            NegotiationSession.tenant_id == self.tenant_id
                        )
                    ),
                )
            )
            .values(status=status, updated_at=datetime.now(timezone.utc))
            .returning(NegotiationRedline)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete_redline(self, redline_id: str) -> bool:
        """Delete a redline, scoped to tenant."""
        query = (
            delete(NegotiationRedline)
            .where(
                and_(
                    NegotiationRedline.redline_id == redline_id,
                    NegotiationRedline.session_id.in_(
                        select(NegotiationSession.session_id).where(
                            NegotiationSession.tenant_id == self.tenant_id
                        )
                    ),
                )
            )
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount > 0

    # ── Issues ───────────────────────────────────────────────────

    async def create_issue(self, issue: NegotiationIssue) -> NegotiationIssue:
        """Create a new issue."""
        self.session.add(issue)
        await self.session.flush()
        return issue

    async def list_issues(self, session_id: str) -> list[NegotiationIssue]:
        """List all issues for a session, scoped to tenant."""
        query = (
            select(NegotiationIssue)
            .join(NegotiationSession, NegotiationSession.session_id == NegotiationIssue.session_id)
            .where(
                and_(
                    NegotiationIssue.session_id == session_id,
                    NegotiationSession.tenant_id == self.tenant_id,
                )
            )
            .order_by(NegotiationIssue.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_issue(
        self, issue_id: str, **kwargs: Any
    ) -> Optional[NegotiationIssue]:
        """Update an issue, scoped to tenant."""
        kwargs["updated_at"] = datetime.now(timezone.utc)
        query = (
            update(NegotiationIssue)
            .where(
                and_(
                    NegotiationIssue.issue_id == issue_id,
                    NegotiationIssue.session_id.in_(
                        select(NegotiationSession.session_id).where(
                            NegotiationSession.tenant_id == self.tenant_id
                        )
                    ),
                )
            )
            .values(**kwargs)
            .returning(NegotiationIssue)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    # ── Comments ─────────────────────────────────────────────────

    async def create_comment(self, comment: NegotiationComment) -> NegotiationComment:
        """Create a new comment."""
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def list_comments(
        self,
        session_id: str,
        redline_id: Optional[str] = None,
        issue_id: Optional[str] = None,
    ) -> list[NegotiationComment]:
        """List comments for a session, scoped to tenant."""
        conditions = [NegotiationComment.session_id == session_id]
        if redline_id:
            conditions.append(NegotiationComment.redline_id == redline_id)
        if issue_id:
            conditions.append(NegotiationComment.issue_id == issue_id)
        query = (
            select(NegotiationComment)
            .join(NegotiationSession, NegotiationSession.session_id == NegotiationComment.session_id)
            .where(and_(*conditions, NegotiationSession.tenant_id == self.tenant_id))
            .order_by(NegotiationComment.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def resolve_comment(
        self, comment_id: str, resolved_by: str
    ) -> Optional[NegotiationComment]:
        """Mark a comment as resolved, scoped to tenant."""
        query = (
            update(NegotiationComment)
            .where(
                and_(
                    NegotiationComment.comment_id == comment_id,
                    NegotiationComment.session_id.in_(
                        select(NegotiationSession.session_id).where(
                            NegotiationSession.tenant_id == self.tenant_id
                        )
                    ),
                )
            )
            .values(
                status=CommentStatus.RESOLVED.value,
                resolved_by=resolved_by,
                resolved_at=datetime.now(timezone.utc),
            )
            .returning(NegotiationComment)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    # ── Participants ─────────────────────────────────────────────

    async def create_participant(
        self, participant: NegotiationParticipant
    ) -> NegotiationParticipant:
        """Add a participant to a session."""
        self.session.add(participant)
        await self.session.flush()
        return participant

    async def list_participants(self, session_id: str) -> list[NegotiationParticipant]:
        """List all participants in a session, scoped to tenant."""
        query = (
            select(NegotiationParticipant)
            .join(NegotiationSession, NegotiationSession.session_id == NegotiationParticipant.session_id)
            .where(
                and_(
                    NegotiationParticipant.session_id == session_id,
                    NegotiationSession.tenant_id == self.tenant_id,
                )
            )
            .order_by(NegotiationParticipant.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_participant_role(
        self, participant_id: str, role: str
    ) -> Optional[NegotiationParticipant]:
        """Update a participant's role, scoped to tenant."""
        query = (
            update(NegotiationParticipant)
            .where(
                and_(
                    NegotiationParticipant.participant_id == participant_id,
                    NegotiationParticipant.session_id.in_(
                        select(NegotiationSession.session_id).where(
                            NegotiationSession.tenant_id == self.tenant_id
                        )
                    ),
                )
            )
            .values(role=role)
            .returning(NegotiationParticipant)
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete_participant(self, participant_id: str) -> bool:
        """Remove a participant, scoped to tenant."""
        query = (
            delete(NegotiationParticipant)
            .where(
                and_(
                    NegotiationParticipant.participant_id == participant_id,
                    NegotiationParticipant.session_id.in_(
                        select(NegotiationSession.session_id).where(
                            NegotiationSession.tenant_id == self.tenant_id
                        )
                    ),
                )
            )
        )
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount > 0

    # ── Votes ────────────────────────────────────────────────────

    async def create_vote(self, vote: "NegotiationVote") -> "NegotiationVote":
        """Create a new vote."""
        self.session.add(vote)
        await self.session.flush()
        return vote

    async def list_votes(
        self, session_id: str, clause_id: Optional[str] = None
    ) -> list["NegotiationVote"]:
        """List votes for a session, optionally filtered by clause, scoped to tenant."""
        from app.domains.negotiation.models import NegotiationVote as VoteModel

        conditions = [VoteModel.session_id == session_id]
        if clause_id:
            conditions.append(VoteModel.clause_id == clause_id)
        query = (
            select(VoteModel)
            .join(NegotiationSession, NegotiationSession.session_id == VoteModel.session_id)
            .where(and_(*conditions, NegotiationSession.tenant_id == self.tenant_id))
            .order_by(VoteModel.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ── Activity / Audit Log ─────────────────────────────────────
    # Uses governance_audit_events table (reuse, not duplicate)

    async def log_audit(
        self,
        session_id: str,
        event_type: str,
        actor_id: str,
        previous_state: Optional[dict] = None,
        new_state: Optional[dict] = None,
        change_summary: Optional[str] = None,
    ) -> None:
        """Create an audit event in the shared governance_audit_events table."""
        from app.domains.playbook.models import GovernanceAuditEvent

        event = GovernanceAuditEvent(
            event_id=str(uuid.uuid4()),
            tenant_id=self.tenant_id,
            event_type=event_type,
            entity_type="negotiation_session",
            entity_id=session_id,
            actor_id=actor_id,
            previous_state=previous_state,
            new_state=new_state,
            change_summary=change_summary,
            source="negotiation",
        )
        self.session.add(event)
        await self.session.flush()
