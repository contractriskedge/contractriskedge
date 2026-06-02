"""Human Review Operations Platform — reviewer queues, SLA management, workload balancing, approval chains.

Provides:
- ReviewerQueueManager — manage reviewer assignments and queues
- SLAManager — SLA tracking and breach detection for reviews
- EscalationWorkflow — automatic escalation for overdue reviews
- WorkloadBalancer — distribute reviews across reviewers
- ApprovalChain — multi-level approval chains
- ReviewerAnalytics — reviewer performance metrics
- OverrideAnalytics — track and analyze human overrides of AI recommendations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Core Types ─────────────────────────────────────────────────────

class ReviewPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewAssignmentStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    REASSIGNED = "reassigned"


class ReviewerRole(str, Enum):
    PROCUREMENT = "procurement"
    LEGAL = "legal"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    EXECUTIVE = "executive"
    PARALEGAL = "paralegal"


@dataclass
class Reviewer:
    """A human reviewer with skills, workload, and availability."""
    user_id: str
    name: str
    roles: list[ReviewerRole]
    max_concurrent_reviews: int = 5
    current_reviews: int = 0
    is_available: bool = True
    skills: list[str] = field(default_factory=list)
    avg_review_time_hours: float = 0.0
    accuracy_score: float = 1.0
    tenant_id: str = ""


@dataclass
class ReviewAssignment:
    """A review task assigned to a reviewer."""
    assignment_id: str
    review_id: str
    upload_id: str
    tenant_id: str
    assigned_to: str
    assigned_by: str
    role: ReviewerRole
    priority: ReviewPriority
    status: ReviewAssignmentStatus
    sla_deadline: str = ""
    assigned_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    escalation_level: int = 0
    notes: str = ""


# ── Reviewer Queue Manager ─────────────────────────────────────────

@dataclass
class ReviewerQueueManager:
    """Manages reviewer assignments and queues.

    Handles:
    - Assignment of reviews to reviewers
    - Queue priority ordering
    - Load-aware distribution
    - Reassignment on unavailability
    """

    session: AsyncSession
    tenant_id: str

    async def assign_review(
        self,
        review_id: str,
        upload_id: str,
        role: ReviewerRole,
        priority: ReviewPriority = ReviewPriority.MEDIUM,
        assigned_by: str = "system",
        preferred_reviewer: str | None = None,
    ) -> ReviewAssignment:
        """Assign a review to the best available reviewer."""
        if preferred_reviewer:
            reviewer = await self._get_reviewer(preferred_reviewer)
            if reviewer and reviewer.is_available:
                return await self._create_assignment(review_id, upload_id, reviewer.user_id, assigned_by, role, priority)

        # Find best available reviewer
        reviewer = await self._find_best_reviewer(role)
        if not reviewer:
            raise NoAvailableReviewerError(f"No available reviewer for role {role.value}")

        return await self._create_assignment(review_id, upload_id, reviewer.user_id, assigned_by, role, priority)

    async def _find_best_reviewer(self, role: ReviewerRole) -> Reviewer | None:
        """Find the best available reviewer for a role."""
        sql = sa_text("""
            SELECT user_id, name, current_reviews, max_concurrent_reviews,
                   avg_review_time_hours, accuracy_score
            FROM reviewers
            WHERE :role = ANY(roles)
              AND is_available = true
              AND current_reviews < max_concurrent_reviews
              AND tenant_id = :tid
            ORDER BY current_reviews ASC, accuracy_score DESC
            LIMIT 1
        """)
        result = await self.session.execute(sql, {"role": role.value, "tid": self.tenant_id})
        row = result.fetchone()
        if not row:
            return None
        return Reviewer(
            user_id=str(row.user_id),
            name=row.name,
            roles=[role],
            current_reviews=row.current_reviews or 0,
            max_concurrent_reviews=row.max_concurrent_reviews or 5,
            avg_review_time_hours=row.avg_review_time_hours or 0.0,
            accuracy_score=row.accuracy_score or 1.0,
            tenant_id=self.tenant_id,
        )

    async def _create_assignment(
        self, review_id: str, upload_id: str, assigned_to: str,
        assigned_by: str, role: ReviewerRole, priority: ReviewPriority,
    ) -> ReviewAssignment:
        """Create a review assignment."""
        import uuid
        assignment_id = str(uuid.uuid4())

        sla_map = {
            ReviewPriority.CRITICAL: 4,    # 4 hours
            ReviewPriority.HIGH: 8,         # 8 hours
            ReviewPriority.MEDIUM: 24,      # 24 hours
            ReviewPriority.LOW: 72,         # 72 hours
        }
        sla_hours = sla_map.get(priority, 24)
        deadline = datetime.utcnow() + timedelta(hours=sla_hours)

        sql = sa_text("""
            INSERT INTO review_assignments (assignment_id, review_id, upload_id, tenant_id,
                assigned_to, assigned_by, role, priority, status, sla_deadline)
            VALUES (:aid, :rid, :uid, :tid,
                :assigned_to, :assigned_by, :role, :priority, 'assigned', :deadline)
            RETURNING assignment_id, review_id, upload_id, tenant_id,
                assigned_to, assigned_by, role, priority, status, sla_deadline, assigned_at
        """)
        result = await self.session.execute(sql, {
            "aid": assignment_id,
            "rid": review_id,
            "uid": upload_id,
            "tid": self.tenant_id,
            "assigned_to": assigned_to,
            "assigned_by": assigned_by,
            "role": role.value,
            "priority": priority.value,
            "deadline": deadline.isoformat(),
        })
        row = result.fetchone()

        # Update reviewer's current count
        sql_upd = sa_text("UPDATE reviewers SET current_reviews = current_reviews + 1 WHERE user_id = :uid")
        await self.session.execute(sql_upd, {"uid": assigned_to})

        logger.info(
            "Assigned review %s to %s (role=%s, priority=%s, SLA=%dh)",
            review_id[:8], assigned_to[:8], role.value, priority.value, sla_hours,
        )

        return ReviewAssignment(
            assignment_id=str(row.assignment_id),
            review_id=str(row.review_id),
            upload_id=str(row.upload_id),
            tenant_id=str(row.tenant_id),
            assigned_to=str(row.assigned_to),
            assigned_by=str(row.assigned_by),
            role=ReviewerRole(row.role),
            priority=ReviewPriority(row.priority),
            status=ReviewAssignmentStatus(row.status),
            sla_deadline=str(row.sla_deadline),
            assigned_at=str(row.assigned_at),
        )

    async def get_reviewer_queue(self, user_id: str) -> list[ReviewAssignment]:
        """Get the queue of assignments for a reviewer."""
        sql = sa_text("""
            SELECT assignment_id, review_id, upload_id, tenant_id,
                   assigned_to, assigned_by, role, priority, status,
                   sla_deadline, assigned_at, started_at
            FROM review_assignments
            WHERE assigned_to = :uid AND tenant_id = :tid
              AND status IN ('assigned', 'in_progress')
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                sla_deadline ASC
        """)
        result = await self.session.execute(sql, {"uid": user_id, "tid": self.tenant_id})
        return [
            ReviewAssignment(
                assignment_id=str(row.assignment_id),
                review_id=str(row.review_id),
                upload_id=str(row.upload_id),
                tenant_id=str(row.tenant_id),
                assigned_to=str(row.assigned_to),
                assigned_by=str(row.assigned_by),
                role=ReviewerRole(row.role),
                priority=ReviewPriority(row.priority),
                status=ReviewAssignmentStatus(row.status),
                sla_deadline=str(row.sla_deadline),
                assigned_at=str(row.assigned_at),
                started_at=str(row.started_at) if row.started_at else None,
            )
            for row in result.fetchall()
        ]

    async def complete_assignment(self, assignment_id: str, notes: str = "") -> None:
        """Mark an assignment as completed."""
        sql = sa_text("""
            UPDATE review_assignments
            SET status = 'completed', completed_at = NOW(), notes = :notes
            WHERE assignment_id = :aid
            RETURNING assigned_to
        """)
        result = await self.session.execute(sql, {"aid": assignment_id, "notes": notes})
        row = result.fetchone()
        if row:
            sql_upd = sa_text("UPDATE reviewers SET current_reviews = GREATEST(current_reviews - 1, 0) WHERE user_id = :uid")
            await self.session.execute(sql_upd, {"uid": str(row.assigned_to)})

    async def reassign_review(self, assignment_id: str, new_reviewer: str, reason: str = "") -> None:
        """Reassign a review to a different reviewer."""
        sql = sa_text("""
            UPDATE review_assignments
            SET status = 'reassigned', notes = :reason
            WHERE assignment_id = :aid
            RETURNING assigned_to, review_id, upload_id, role, priority
        """)
        result = await self.session.execute(sql, {"aid": assignment_id, "reason": reason})
        row = result.fetchone()
        if row:
            # Decrement old reviewer count
            sql_upd = sa_text("UPDATE reviewers SET current_reviews = GREATEST(current_reviews - 1, 0) WHERE user_id = :uid")
            await self.session.execute(sql_upd, {"uid": str(row.assigned_to)})

            # Create new assignment
            await self._create_assignment(
                review_id=str(row.review_id),
                upload_id=str(row.upload_id),
                assigned_to=new_reviewer,
                assigned_by="system",
                role=ReviewerRole(row.role),
                priority=ReviewPriority(row.priority),
            )


class NoAvailableReviewerError(Exception):
    """Raised when no reviewer is available for assignment."""


# ── SLA Manager ────────────────────────────────────────────────────

@dataclass
class SLAManager:
    """SLA tracking and breach detection for review assignments."""

    session: AsyncSession
    tenant_id: str

    async def check_sla_breaches(self) -> list[ReviewAssignment]:
        """Find all assignments that have breached their SLA."""
        sql = sa_text("""
            SELECT assignment_id, review_id, upload_id, tenant_id,
                   assigned_to, assigned_by, role, priority, status,
                   sla_deadline, assigned_at, escalation_level
            FROM review_assignments
            WHERE tenant_id = :tid
              AND status IN ('assigned', 'in_progress')
              AND sla_deadline < NOW()
              AND escalation_level < 3
            ORDER BY sla_deadline ASC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [
            ReviewAssignment(
                assignment_id=str(row.assignment_id),
                review_id=str(row.review_id),
                upload_id=str(row.upload_id),
                tenant_id=str(row.tenant_id),
                assigned_to=str(row.assigned_to),
                assigned_by=str(row.assigned_by),
                role=ReviewerRole(row.role),
                priority=ReviewPriority(row.priority),
                status=ReviewAssignmentStatus(row.status),
                sla_deadline=str(row.sla_deadline),
                assigned_at=str(row.assigned_at),
                escalation_level=row.escalation_level or 0,
            )
            for row in result.fetchall()
        ]

    async def get_sla_health(self) -> dict[str, Any]:
        """Get SLA health metrics."""
        sql = sa_text("""
            SELECT
                COUNT(*) FILTER (WHERE status IN ('assigned', 'in_progress')) as active,
                COUNT(*) FILTER (WHERE status IN ('assigned', 'in_progress') AND sla_deadline < NOW()) as breached,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                AVG(CASE WHEN status = 'completed' THEN EXTRACT(EPOCH FROM (completed_at - assigned_at))/3600.0 END) as avg_completion_hours
            FROM review_assignments
            WHERE tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        row = result.fetchone()
        active = row.active or 0
        breached = row.breached or 0
        return {
            "active_assignments": active,
            "breached_sla": breached,
            "sla_compliance_pct": round(((active - breached) / max(active, 1)) * 100, 1),
            "completed": row.completed or 0,
            "avg_completion_hours": round(row.avg_completion_hours or 0.0, 1),
        }


# ── Workload Balancer ──────────────────────────────────────────────

@dataclass
class WorkloadBalancer:
    """Balances review workload across available reviewers."""

    session: AsyncSession
    tenant_id: str

    async def get_workload_report(self) -> dict[str, Any]:
        """Get workload distribution across reviewers."""
        sql = sa_text("""
            SELECT r.user_id, r.name, r.current_reviews, r.max_concurrent_reviews,
                   r.is_available,
                   COUNT(a.assignment_id) FILTER (WHERE a.status IN ('assigned', 'in_progress')) as active_assignments
            FROM reviewers r
            LEFT JOIN review_assignments a ON a.assigned_to = r.user_id AND a.tenant_id = r.tenant_id
            WHERE r.tenant_id = :tid
            GROUP BY r.user_id, r.name, r.current_reviews, r.max_concurrent_reviews, r.is_available
            ORDER BY r.current_reviews DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        reviewers = []
        total_capacity = 0
        total_load = 0
        for row in result.fetchall():
            load = row.active_assignments or 0
            capacity = row.max_concurrent_reviews or 5
            total_load += load
            total_capacity += capacity
            reviewers.append({
                "user_id": str(row.user_id),
                "name": row.name,
                "current_load": load,
                "max_capacity": capacity,
                "utilization_pct": round((load / max(capacity, 1)) * 100, 1),
                "available": row.is_available,
            })

        return {
            "reviewers": reviewers,
            "total_load": total_load,
            "total_capacity": total_capacity,
            "overall_utilization_pct": round((total_load / max(total_capacity, 1)) * 100, 1),
            "overloaded_reviewers": sum(1 for r in reviewers if r["utilization_pct"] > 80),
            "available_reviewers": sum(1 for r in reviewers if r["available"]),
        }

    async def rebalance(self) -> list[dict[str, Any]]:
        """Rebalance workload by reassigning from overloaded to underloaded reviewers."""
        report = await self.get_workload_report()
        reassignments = []

        overloaded = [r for r in report["reviewers"] if r["utilization_pct"] > 80 and r["available"]]
        underloaded = [r for r in report["reviewers"] if r["utilization_pct"] < 50 and r["available"]]

        for overloaded_rev in overloaded:
            if not underloaded:
                break
            underloaded_rev = underloaded.pop(0)

            # Find assignments to reassign
            sql = sa_text("""
                SELECT assignment_id FROM review_assignments
                WHERE assigned_to = :uid AND tenant_id = :tid
                  AND status = 'assigned'
                ORDER BY priority DESC, sla_deadline ASC
                LIMIT 1
            """)
            result = await self.session.execute(sql, {
                "uid": overloaded_rev["user_id"],
                "tid": self.tenant_id,
            })
            row = result.fetchone()
            if row:
                reassignments.append({
                    "assignment_id": str(row.assignment_id),
                    "from": overloaded_rev["user_id"],
                    "to": underloaded_rev["user_id"],
                })

        return reassignments


# ── Approval Chain ─────────────────────────────────────────────────

@dataclass
class ApprovalChainStep:
    """A single step in an approval chain."""
    step: int
    role: ReviewerRole
    min_approvers: int = 1
    timeout_hours: int = 24
    escalation_step: int | None = None  # Next step if timed out


@dataclass
class ApprovalChain:
    """Multi-level approval chain for review decisions.

    Example: Procurement -> Legal -> Executive for high-risk contracts.
    """
    chain_id: str
    name: str
    steps: list[ApprovalChainStep] = field(default_factory=list)
    trigger_condition: str = ""  # e.g., "risk_score > 0.7"

    @classmethod
    def standard_review_chain(cls) -> ApprovalChain:
        """Standard 3-step approval chain for contract reviews."""
        return ApprovalChain(
            chain_id="standard_review",
            name="Standard Review Approval",
            steps=[
                ApprovalChainStep(step=1, role=ReviewerRole.PROCUREMENT, min_approvers=1, timeout_hours=24),
                ApprovalChainStep(step=2, role=ReviewerRole.LEGAL, min_approvers=1, timeout_hours=48),
                ApprovalChainStep(step=3, role=ReviewerRole.EXECUTIVE, min_approvers=1, timeout_hours=72),
            ],
            trigger_condition="risk_score >= 0.3",
        )

    @classmethod
    def high_risk_chain(cls) -> ApprovalChain:
        """Elevated approval chain for high-risk contracts."""
        return ApprovalChain(
            chain_id="high_risk",
            name="High Risk Approval Chain",
            steps=[
                ApprovalChainStep(step=1, role=ReviewerRole.LEGAL, min_approvers=2, timeout_hours=24),
                ApprovalChainStep(step=2, role=ReviewerRole.COMPLIANCE, min_approvers=1, timeout_hours=48),
                ApprovalChainStep(step=3, role=ReviewerRole.EXECUTIVE, min_approvers=1, timeout_hours=72),
            ],
            trigger_condition="risk_score >= 0.7",
        )


# ── Reviewer Analytics ─────────────────────────────────────────────

@dataclass
class ReviewerAnalytics:
    """Reviewer performance metrics and analytics."""

    session: AsyncSession
    tenant_id: str

    async def get_reviewer_performance(self, user_id: str) -> dict[str, Any]:
        """Get performance metrics for a reviewer."""
        sql = sa_text("""
            SELECT
                COUNT(*) as total_reviews,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'escalated') as escalated,
                AVG(CASE WHEN status = 'completed' THEN EXTRACT(EPOCH FROM (completed_at - assigned_at))/3600.0 END) as avg_hours,
                COUNT(*) FILTER (WHERE sla_deadline < NOW() AND status IN ('assigned', 'in_progress')) as sla_breaches
            FROM review_assignments
            WHERE assigned_to = :uid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"uid": user_id, "tid": self.tenant_id})
        row = result.fetchone()
        total = row.total_reviews or 0
        return {
            "total_reviews": total,
            "completed": row.completed or 0,
            "escalated": row.escalated or 0,
            "avg_completion_hours": round(row.avg_hours or 0.0, 1),
            "sla_breaches": row.sla_breaches or 0,
            "completion_rate": round((row.completed or 0) / max(total, 1) * 100, 1),
            "sla_compliance_pct": round(((total - (row.sla_breaches or 0)) / max(total, 1)) * 100, 1),
        }

    async def get_team_performance(self) -> dict[str, Any]:
        """Get aggregate team performance metrics."""
        sql = sa_text("""
            SELECT
                COUNT(DISTINCT assigned_to) as active_reviewers,
                COUNT(*) as total_assignments,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'escalated') as escalated,
                COUNT(*) FILTER (WHERE sla_deadline < NOW() AND status IN ('assigned', 'in_progress')) as sla_breaches
            FROM review_assignments
            WHERE tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        row = result.fetchone()
        total = row.total_assignments or 0
        return {
            "active_reviewers": row.active_reviewers or 0,
            "total_assignments": total,
            "completed": row.completed or 0,
            "escalated": row.escalated or 0,
            "sla_breaches": row.sla_breaches or 0,
            "completion_rate": round((row.completed or 0) / max(total, 1) * 100, 1),
            "escalation_rate": round((row.escalated or 0) / max(total, 1) * 100, 1),
            "sla_compliance_pct": round(((total - (row.sla_breaches or 0)) / max(total, 1)) * 100, 1),
        }


# ── Override Analytics ─────────────────────────────────────────────

@dataclass
class OverrideAnalytics:
    """Track and analyze human overrides of AI recommendations.

    This is critical for:
    - Measuring AI accuracy in production
    - Identifying patterns where AI is wrong
    - Training data collection for improvement
    """

    session: AsyncSession
    tenant_id: str

    async def record_override(
        self,
        review_id: str,
        finding_id: str,
        override_type: str,  # "accepted", "rejected", "modified", "dismissed"
        original_ai_value: str,
        human_value: str,
        reason: str,
        overridden_by: str,
    ) -> None:
        """Record a human override of an AI recommendation."""
        sql = sa_text("""
            INSERT INTO ai_override_log (review_id, finding_id, tenant_id,
                override_type, original_ai_value, human_value, reason, overridden_by)
            VALUES (:rid, :fid, :tid,
                :otype, :ai_val, :human_val, :reason, :by)
        """)
        await self.session.execute(sql, {
            "rid": review_id,
            "fid": finding_id,
            "tid": self.tenant_id,
            "otype": override_type,
            "ai_val": original_ai_value,
            "human_val": human_value,
            "reason": reason,
            "by": overridden_by,
        })

    async def get_override_stats(self) -> dict[str, Any]:
        """Get override statistics."""
        sql = sa_text("""
            SELECT
                override_type, COUNT(*) as count,
                COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as pct
            FROM ai_override_log
            WHERE tenant_id = :tid
            GROUP BY override_type
            ORDER BY count DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        type_breakdown = {}
        for row in result.fetchall():
            type_breakdown[row.override_type] = {
                "count": row.count,
                "percentage": round(row.pct, 1),
            }

        sql = sa_text("""
            SELECT
                COUNT(*) as total_overrides,
                COUNT(DISTINCT review_id) as affected_reviews,
                COUNT(DISTINCT overridden_by) as unique_reviewers
            FROM ai_override_log
            WHERE tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        row = result.fetchone()

        return {
            "total_overrides": row.total_overrides or 0,
            "affected_reviews": row.affected_reviews or 0,
            "unique_reviewers": row.unique_reviewers or 0,
            "override_rate": round((row.total_overrides or 0) / max(row.affected_reviews or 1, 1), 2),
            "by_type": type_breakdown,
        }
