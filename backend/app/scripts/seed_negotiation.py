"""Seed a complete negotiation test session with all related records.

Creates one negotiation session with:
- 2 document versions (Original Draft, Current Redline)
- 3 redlines (modifications to key clauses)
- 2 issues (one critical, one major)
- 4 comments (on redlines and issues, with a nested reply)
- 3 participants (owner, reviewer, approver)

Usage:
    cd backend
    python -m app.scripts.seed_negotiation
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.domains.negotiation.models import (
    CommentStatus,
    IssueSeverity,
    IssueStatus,
    NegotiationComment,
    NegotiationIssue,
    NegotiationParticipant,
    NegotiationRedline,
    NegotiationSession,
    NegotiationStage,
    NegotiationVersion,
    ParticipantRole,
    RedlineStatus,
    RedlineType,
    RiskLevel,
    VersionStatus,
)
from app.domains.negotiation.repository import NegotiationRepository
from app.kernel.database.orm_registry import register_orm_models

logger = logging.getLogger(__name__)

# Use the same tenant and contract review IDs from existing seed data
TENANT_ID = "00000000-0000-4000-8000-000000000001"
CONTRACT_ID = "53b173ff-c1cd-4f01-a4fe-ba2c23bb6d5a"  # escalated review


async def seed_negotiation() -> None:
    """Create a complete negotiation test session."""
    register_orm_models()

    # Build async engine from the sync DATABASE_URL
    db_url = str(settings.database_url).replace(
        "postgresql+asyncpg://", "postgresql+asyncpg://"
    )
    # If the URL doesn't have +asyncpg, add it
    if "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url)
    session_id = str(uuid.uuid4())

    async with AsyncSession(engine) as session:
        repo = NegotiationRepository(session, tenant_id=TENANT_ID)

        # ── 1. Create the negotiation session ───────────────────
        neg_session = NegotiationSession(
            session_id=session_id,
            tenant_id=TENANT_ID,
            contract_id=CONTRACT_ID,
            contract_title="Master Service Agreement - Acme Corp",
            counterparty="Acme Corporation",
            stage=NegotiationStage.NEGOTIATING.value,
            health_score=72.5,
            started_at=datetime.now(timezone.utc) - timedelta(days=14),
        )
        await repo.create_session(neg_session)
        logger.info("Created session %s", session_id[:8])

        # ── 2. Create document versions ─────────────────────────
        v1 = NegotiationVersion(
            session_id=session_id,
            version_number=1,
            label="Original Draft",
            author="Sarah Chen",
            status=VersionStatus.SUPERSEDED.value,
            clauses=[
                {
                    "clauseId": "c1",
                    "title": "Limitation of Liability",
                    "sectionNumber": "12.1",
                    "content": "Neither party shall be liable to the other for any indirect, incidental, special, consequential or punitive damages, except in the case of gross negligence or willful misconduct. Total liability shall not exceed the total fees paid under this agreement during the twelve months immediately preceding the event giving rise to liability.",
                    "riskLevel": "high",
                    "category": "liability",
                },
                {
                    "clauseId": "c2",
                    "title": "Indemnification",
                    "sectionNumber": "13.2",
                    "content": "Vendor shall indemnify, defend and hold Customer harmless from and against any and all third-party claims arising out of or related to: (a) any breach of this agreement by Vendor; (b) any infringement of third-party intellectual property rights; and (c) any bodily injury or property damage caused by Vendor's personnel.",
                    "riskLevel": "medium",
                    "category": "indemnification",
                },
                {
                    "clauseId": "c3",
                    "title": "Data Protection",
                    "sectionNumber": "18.1",
                    "content": "Each party shall maintain appropriate technical and organizational measures to protect personal data against unauthorized access, disclosure, alteration or destruction. Vendor shall notify Customer within 72 hours of becoming aware of any data breach.",
                    "riskLevel": "critical",
                    "category": "data_privacy",
                },
                {
                    "clauseId": "c4",
                    "title": "Termination for Convenience",
                    "sectionNumber": "15.3",
                    "content": "Either party may terminate this agreement for any reason upon 90 days written notice to the other party.",
                    "riskLevel": "low",
                    "category": "termination",
                },
                {
                    "clauseId": "c5",
                    "title": "Service Level Agreement",
                    "sectionNumber": "8.1",
                    "content": "Vendor shall achieve 99.9% uptime for the platform, measured monthly. If uptime falls below 99.5% in any calendar month, Customer shall receive a service credit equal to 5% of monthly fees.",
                    "riskLevel": "medium",
                    "category": "sla",
                },
            ],
            word_count=2450,
            change_summary="Initial draft provided by vendor legal team",
        )
        await repo.create_version(v1)

        v2 = NegotiationVersion(
            session_id=session_id,
            version_number=2,
            label="Current Redline",
            author="Michael Torres",
            status=VersionStatus.CURRENT.value,
            clauses=[
                {
                    "clauseId": "c1",
                    "title": "Limitation of Liability",
                    "sectionNumber": "12.1",
                    "content": "Neither party shall be liable to the other for any indirect, incidental, special, consequential or punitive damages, except in the case of gross negligence, willful misconduct, or breach of confidentiality obligations. Total liability shall not exceed the total fees paid under this agreement during the twenty-four months immediately preceding the event giving rise to liability, or $5,000,000, whichever is greater.",
                    "riskLevel": "medium",
                    "category": "liability",
                },
                {
                    "clauseId": "c2",
                    "title": "Indemnification",
                    "sectionNumber": "13.2",
                    "content": "Vendor shall indemnify, defend and hold Customer harmless from and against any and all third-party claims arising out of or related to: (a) any breach of this agreement by Vendor; (b) any infringement of third-party intellectual property rights; (c) any bodily injury or property damage caused by Vendor's personnel; and (d) any violation of applicable data protection laws by Vendor.",
                    "riskLevel": "low",
                    "category": "indemnification",
                },
            ],
            word_count=2680,
            change_summary="Customer legal team redlined liability and indemnification clauses",
        )
        await repo.create_version(v2)
        logger.info("Created 2 versions")

        # ── 3. Create redlines ──────────────────────────────────
        r1 = NegotiationRedline(
            session_id=session_id,
            clause_id="c1",
            type=RedlineType.MODIFICATION.value,
            title="Extend liability lookback period and add cap",
            original_text="Total liability shall not exceed the total fees paid under this agreement during the twelve months immediately preceding the event giving rise to liability.",
            modified_text="Total liability shall not exceed the total fees paid under this agreement during the twenty-four months immediately preceding the event giving rise to liability, or $5,000,000, whichever is greater.",
            author="Michael Torres",
            author_avatar="",
            risk_level=RiskLevel.HIGH.value,
            status=RedlineStatus.PENDING.value,
            ai_generated=False,
            negotiation_impact="high",
            benchmark_deviation=15.0,
        )
        await repo.create_redline(r1)

        r2 = NegotiationRedline(
            session_id=session_id,
            clause_id="c2",
            type=RedlineType.ADDITION.value,
            title="Add data protection violation to indemnification",
            original_text="(c) any bodily injury or property damage caused by Vendor's personnel.",
            modified_text="(c) any bodily injury or property damage caused by Vendor's personnel; and (d) any violation of applicable data protection laws by Vendor.",
            author="Sarah Chen",
            author_avatar="",
            risk_level=RiskLevel.MEDIUM.value,
            status=RedlineStatus.ACCEPTED.value,
            ai_generated=True,
            ai_confidence=0.87,
            negotiation_impact="medium",
            benchmark_deviation=8.0,
        )
        await repo.create_redline(r2)

        r3 = NegotiationRedline(
            session_id=session_id,
            clause_id="c3",
            type=RedlineType.MODIFICATION.value,
            title="Reduce data breach notification window",
            original_text="Vendor shall notify Customer within 72 hours of becoming aware of any data breach.",
            modified_text="Vendor shall notify Customer within 24 hours of becoming aware of any data breach, and shall provide a preliminary root cause analysis within 72 hours.",
            author="James Wilson",
            author_avatar="",
            risk_level=RiskLevel.CRITICAL.value,
            status=RedlineStatus.PENDING.value,
            ai_generated=True,
            ai_confidence=0.93,
            negotiation_impact="high",
            benchmark_deviation=22.0,
        )
        await repo.create_redline(r3)
        logger.info("Created 3 redlines")

        # ── 4. Create issues ─────────────────────────────────────
        i1 = NegotiationIssue(
            session_id=session_id,
            clause_id="c1",
            title="Liability cap insufficient for enterprise deal",
            description="The proposed liability cap of fees paid in 12 months is approximately $450K based on current contract value. For an enterprise agreement of this size, industry standard is 12-24 months of fees or a fixed floor of $5M. The counterparty's initial position of 12 months fees is below market for similar enterprises.",
            severity=IssueSeverity.CRITICAL.value,
            status=IssueStatus.IN_REVIEW.value,
            assignee="Michael Torres",
            assignee_avatar="",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            created_by="Sarah Chen",
            category="commercial",
            escalation_level=1,
            tags=["liability", "enterprise", "negotiation"],
        )
        await repo.create_issue(i1)

        i2 = NegotiationIssue(
            session_id=session_id,
            clause_id="c3",
            title="Data breach notification window too long",
            description="The vendor's proposed 72-hour notification window exceeds the 24-hour standard required by our security policy and GDPR best practices. We need to push for 24-hour notification with a follow-up root cause analysis within 72 hours.",
            severity=IssueSeverity.MAJOR.value,
            status=IssueStatus.OPEN.value,
            assignee="James Wilson",
            assignee_avatar="",
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            created_by="Sarah Chen",
            category="compliance",
            escalation_level=0,
            tags=["data_privacy", "gdpr", "security"],
        )
        await repo.create_issue(i2)
        logger.info("Created 2 issues")

        # ── 5. Create comments ──────────────────────────────────
        c1 = NegotiationComment(
            session_id=session_id,
            redline_id=r1.redline_id,
            clause_id="c1",
            author="Sarah Chen",
            author_avatar="",
            author_role="Legal Counsel",
            content="I've reviewed the modified liability clause. The 24-month lookback and $5M floor are consistent with our enterprise agreement playbook. Recommend accepting with a note that this is our final position.",
            status=CommentStatus.ACTIVE.value,
            mentions=["Michael Torres"],
        )
        await repo.create_comment(c1)

        c2 = NegotiationComment(
            session_id=session_id,
            redline_id=r1.redline_id,
            clause_id="c1",
            parent_id=c1.comment_id,
            author="Michael Torres",
            author_avatar="",
            author_role="Lead Negotiator",
            content="Agreed. I'll communicate this as our final position in the next negotiation session. The counterparty's legal team has been signaling they can accept 18 months but 24 is a stretch. We may need to offer a concession elsewhere.",
            status=CommentStatus.ACTIVE.value,
            mentions=["Sarah Chen"],
        )
        await repo.create_comment(c2)

        c3 = NegotiationComment(
            session_id=session_id,
            issue_id=i1.issue_id,
            clause_id="c1",
            author="James Wilson",
            author_avatar="",
            author_role="Security Officer",
            content="From a risk perspective, I'd note that the counterparty has a strong financial position (S&P A-rated), so the credit risk of a higher cap is acceptable. The key exposure is IP infringement, which is covered separately under indemnification.",
            status=CommentStatus.ACTIVE.value,
            mentions=[],
        )
        await repo.create_comment(c3)

        c4 = NegotiationComment(
            session_id=session_id,
            redline_id=r3.redline_id,
            clause_id="c3",
            author="Sarah Chen",
            author_avatar="",
            author_role="Legal Counsel",
            content="The 24-hour notification window with 72-hour RCA is non-negotiable per our data protection policy. If they push back, escalate to VP level.",
            status=CommentStatus.RESOLVED.value,
            resolved_by="Sarah Chen",
            resolved_at=datetime.now(timezone.utc) - timedelta(days=1),
            mentions=[],
        )
        await repo.create_comment(c4)
        logger.info("Created 4 comments (1 nested reply)")

        # ── 6. Create participants ──────────────────────────────
        p1 = NegotiationParticipant(
            session_id=session_id,
            name="Sarah Chen",
            avatar="",
            role=ParticipantRole.OWNER.value,
            department="Legal",
            is_online=True,
            last_active=datetime.now(timezone.utc) - timedelta(minutes=15),
            reviewed_clauses=5,
            pending_approvals=2,
        )
        await repo.create_participant(p1)

        p2 = NegotiationParticipant(
            session_id=session_id,
            name="Michael Torres",
            avatar="",
            role=ParticipantRole.REVIEWER.value,
            department="Contract Operations",
            is_online=True,
            last_active=datetime.now(timezone.utc) - timedelta(hours=1),
            reviewed_clauses=3,
            pending_approvals=1,
        )
        await repo.create_participant(p2)

        p3 = NegotiationParticipant(
            session_id=session_id,
            name="James Wilson",
            avatar="",
            role=ParticipantRole.REVIEWER.value,
            department="Security",
            is_online=False,
            last_active=datetime.now(timezone.utc) - timedelta(days=1),
            reviewed_clauses=2,
            pending_approvals=0,
        )
        await repo.create_participant(p3)

        p4 = NegotiationParticipant(
            session_id=session_id,
            name="Amanda Foster",
            avatar="",
            role=ParticipantRole.APPROVER.value,
            department="Executive",
            is_online=False,
            last_active=datetime.now(timezone.utc) - timedelta(days=3),
            reviewed_clauses=0,
            pending_approvals=1,
        )
        await repo.create_participant(p4)

        p5 = NegotiationParticipant(
            session_id=session_id,
            name="Robert Kim",
            avatar="",
            role=ParticipantRole.EXTERNAL.value,
            department="Acme Corp Legal",
            is_online=False,
            last_active=datetime.now(timezone.utc) - timedelta(days=2),
            reviewed_clauses=0,
            pending_approvals=0,
        )
        await repo.create_participant(p5)
        logger.info("Created 5 participants")

        # ── 7. Log audit events ─────────────────────────────────
        await repo.log_audit(
            session_id=session_id,
            event_type="negotiation.created",
            actor_id="system",
            new_state={
                "stage": "drafting",
                "contract_title": "Master Service Agreement - Acme Corp",
                "counterparty": "Acme Corporation",
            },
            change_summary="Negotiation session created from contract review",
        )
        await repo.log_audit(
            session_id=session_id,
            event_type="negotiation.stage_changed",
            actor_id="Sarah Chen",
            previous_state={"stage": "drafting"},
            new_state={"stage": "review"},
            change_summary="Moved to review stage after initial draft",
        )
        await repo.log_audit(
            session_id=session_id,
            event_type="negotiation.stage_changed",
            actor_id="Michael Torres",
            previous_state={"stage": "review"},
            new_state={"stage": "negotiating"},
            change_summary="Entered active negotiation with counterparty",
        )
        await repo.log_audit(
            session_id=session_id,
            event_type="redline.created",
            actor_id="Michael Torres",
            new_state={"clause_id": "c1", "type": "modification", "status": "pending"},
            change_summary="Redlined liability clause - extended lookback period",
        )
        await repo.log_audit(
            session_id=session_id,
            event_type="issue.escalated",
            actor_id="Sarah Chen",
            previous_state={"severity": "major", "escalation_level": 0},
            new_state={"severity": "critical", "escalation_level": 1},
            change_summary="Escalated liability cap issue - approaching deadline",
        )
        logger.info("Logged 5 audit events")

        await session.commit()

        # ── Summary ─────────────────────────────────────────────
        print()
        print("=" * 60)
        print("NEGOTIATION TEST SESSION CREATED")
        print("=" * 60)
        print(f"  Session ID:     {session_id}")
        print(f"  Short ID:       {session_id[:8]}")
        print(f"  Tenant ID:      {TENANT_ID}")
        print(f"  Contract ID:    {CONTRACT_ID}")
        print(f"  Contract:       Master Service Agreement - Acme Corp")
        print(f"  Counterparty:   Acme Corporation")
        print(f"  Stage:          negotiating")
        print(f"  Health Score:   72.5")
        print()
        print("  Records Created:")
        print(f"    Versions:      2")
        print(f"    Redlines:      3")
        print(f"    Issues:        2")
        print(f"    Comments:      4 (1 nested reply)")
        print(f"    Participants:  5")
        print(f"    Audit Events:  5")
        print()
        print("  Verify with:")
        print(f"    PGPASSWORD=dev_password psql -h localhost -U dev_user -d contract_risk_dev")
        print(f"    SELECT * FROM negotiation_sessions WHERE session_id = '{session_id}';")
        print(f"    SELECT COUNT(*) FROM negotiation_versions WHERE session_id = '{session_id}';")
        print(f"    SELECT COUNT(*) FROM negotiation_redlines WHERE session_id = '{session_id}';")
        print(f"    SELECT COUNT(*) FROM negotiation_issues WHERE session_id = '{session_id}';")
        print(f"    SELECT COUNT(*) FROM negotiation_comments WHERE session_id = '{session_id}';")
        print(f"    SELECT COUNT(*) FROM negotiation_participants WHERE session_id = '{session_id}';")
        print(f"    SELECT * FROM governance_audit_events WHERE entity_id = '{session_id}';")
        print("=" * 60)


def main() -> None:
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    asyncio.run(seed_negotiation())


if __name__ == "__main__":
    main()
