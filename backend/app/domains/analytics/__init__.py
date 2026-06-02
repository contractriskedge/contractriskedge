"""Usage Analytics Platform — tracks how enterprises actually use the system.

Provides intelligence on:
- Reviewer behavior and patterns
- Override patterns (where humans disagree with AI)
- Workflow abandonment
- Search usage
- SLA breaches
- AI trust scores
- Replay frequency
- Escalation frequency
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class UsageAnalytics:
    """Usage analytics and intelligence for enterprise adoption tracking."""

    session: AsyncSession
    tenant_id: str

    async def get_reviewer_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get reviewer behavior analytics."""
        sql = sa_text("""
            SELECT
                assigned_to,
                COUNT(*) as total_assignments,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'escalated') as escalated,
                AVG(CASE WHEN status = 'completed' THEN EXTRACT(EPOCH FROM (completed_at - assigned_at))/3600.0 END) as avg_hours,
                COUNT(*) FILTER (WHERE sla_deadline < NOW() AND status IN ('assigned', 'in_progress')) as sla_breaches
            FROM review_assignments
            WHERE tenant_id = :tid AND created_at >= CURRENT_DATE - :days
            GROUP BY assigned_to
            ORDER BY total_assignments DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "days": days})
        reviewers = []
        for row in result.fetchall():
            total = row.total_assignments or 0
            completed = row.completed or 0
            reviewers.append({
                "reviewer_id": str(row.assigned_to)[:8],
                "total_assignments": total,
                "completed": completed,
                "completion_rate": round(completed / max(total, 1) * 100, 1),
                "escalated": row.escalated or 0,
                "avg_completion_hours": round(row.avg_hours or 0.0, 1),
                "sla_breaches": row.sla_breaches or 0,
            })

        return {
            "total_reviewers": len(reviewers),
            "total_assignments": sum(r["total_assignments"] for r in reviewers),
            "overall_completion_rate": round(
                sum(r["completed"] for r in reviewers) / max(sum(r["total_assignments"] for r in reviewers), 1) * 100, 1
            ),
            "reviewers": reviewers,
        }

    async def get_override_patterns(self, days: int = 30) -> dict[str, Any]:
        """Get patterns in human overrides of AI recommendations."""
        sql = sa_text("""
            SELECT override_type, COUNT(*) as count,
                   COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as pct
            FROM ai_override_log
            WHERE tenant_id = :tid AND created_at >= CURRENT_DATE - :days
            GROUP BY override_type
            ORDER BY count DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "days": days})
        by_type = {}
        for row in result.fetchall():
            by_type[row.override_type] = {
                "count": row.count,
                "percentage": round(row.pct, 1),
            }

        sql = sa_text("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT review_id) as affected_reviews,
                   COUNT(DISTINCT overridden_by) as unique_reviewers
            FROM ai_override_log
            WHERE tenant_id = :tid AND created_at >= CURRENT_DATE - :days
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "days": days})
        totals = result.fetchone()

        return {
            "total_overrides": totals.total or 0,
            "affected_reviews": totals.affected_reviews or 0,
            "unique_reviewers": totals.unique_reviewers or 0,
            "override_rate": round(
                (totals.total or 0) / max(totals.affected_reviews or 1, 1), 2
            ),
            "by_type": by_type,
        }

    async def get_ai_trust_score(self, days: int = 30) -> dict[str, Any]:
        """Calculate AI trust score based on override patterns and consistency."""
        overrides = await self.get_override_patterns(days)
        total_overrides = overrides["total_overrides"]
        total_reviews = overrides["affected_reviews"]

        # Trust score: 1.0 - (overrides / max(decisions, 1))
        ai_decisions = total_reviews * 5  # Approximate findings per review
        trust_score = 1.0 - (total_overrides / max(ai_decisions, 1))
        trust_score = max(0.0, min(1.0, trust_score))

        # Replay consistency
        sql = sa_text("""
            SELECT COUNT(*) as replays,
                   COUNT(*) FILTER (WHERE drift_score > 0.15) as drifted
            FROM replay_comparisons
            WHERE tenant_id = :tid AND created_at >= CURRENT_DATE - :days
        """)
        try:
            result = await self.session.execute(sql, {"tid": self.tenant_id, "days": days})
            row = result.fetchone()
            replay_consistency = 1.0 - ((row.drifted or 0) / max(row.replays or 1, 1))
        except Exception:
            replay_consistency = 1.0

        return {
            "overall_trust_score": round((trust_score + replay_consistency) / 2, 4),
            "override_trust_score": round(trust_score, 4),
            "replay_consistency_score": round(replay_consistency, 4),
            "total_overrides": total_overrides,
            "total_ai_decisions": ai_decisions,
            "override_rate": overrides["override_rate"],
            "grade": self._trust_grade((trust_score + replay_consistency) / 2),
        }

    def _trust_grade(self, score: float) -> str:
        if score >= 0.95:
            return "A+"
        elif score >= 0.85:
            return "A"
        elif score >= 0.70:
            return "B"
        elif score >= 0.50:
            return "C"
        else:
            return "D"

    async def get_workflow_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get workflow analytics including abandonment and SLA breaches."""
        sql = sa_text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE completed_at IS NOT NULL) as completed,
                COUNT(*) FILTER (WHERE status = 'rejected') as abandoned,
                0::int as escalated,
                AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600.0)
                    FILTER (WHERE completed_at IS NOT NULL) as avg_duration_hours
            FROM contract_reviews
            WHERE tenant_id = :tid AND created_at >= CURRENT_DATE - CAST(:days AS integer)
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "days": days})
        row = result.fetchone()
        total = row.total or 0

        return {
            "total_reviews": total,
            "completed": row.completed or 0,
            "abandoned": row.abandoned or 0,
            "abandonment_rate": round((row.abandoned or 0) / max(total, 1) * 100, 1),
            "escalated": row.escalated or 0,
            "escalation_rate": round((row.escalated or 0) / max(total, 1) * 100, 1),
            "avg_duration_hours": round(row.avg_duration_hours or 0.0, 1),
        }

    async def get_search_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get search usage analytics."""
        sql = sa_text("""
            SELECT
                COUNT(*) as total_searches,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(latency_ms) as avg_latency_ms
            FROM search_log
            WHERE tenant_id = :tid AND created_at >= CURRENT_DATE - :days
        """)
        try:
            result = await self.session.execute(sql, {"tid": self.tenant_id, "days": days})
            row = result.fetchone()
            return {
                "total_searches": row.total_searches or 0,
                "unique_users": row.unique_users or 0,
                "avg_latency_ms": round(row.avg_latency_ms or 0.0, 1),
                "searches_per_user": round(
                    (row.total_searches or 0) / max(row.unique_users or 1, 1), 1
                ),
            }
        except Exception:
            return {"total_searches": 0, "unique_users": 0, "avg_latency_ms": 0.0, "searches_per_user": 0.0}

    async def get_escalation_analytics(self, days: int = 30) -> dict[str, Any]:
        """Get escalation frequency and patterns."""
        sql = sa_text("""
            SELECT
                COUNT(*) as total_escalations,
                COUNT(DISTINCT review_id) as affected_reviews,
                COUNT(DISTINCT escalated_to) as unique_escalators,
                AVG(EXTRACT(EPOCH FROM (escalated_at - created_at))/3600.0) as avg_time_to_escalate_hours
            FROM review_escalations
            WHERE tenant_id = :tid AND created_at >= CURRENT_DATE - :days
        """)
        try:
            result = await self.session.execute(sql, {"tid": self.tenant_id, "days": days})
            row = result.fetchone()
            return {
                "total_escalations": row.total_escalations or 0,
                "affected_reviews": row.affected_reviews or 0,
                "unique_escalators": row.unique_escalators or 0,
                "avg_time_to_escalate_hours": round(row.avg_time_to_escalate_hours or 0.0, 1),
            }
        except Exception:
            return {"total_escalations": 0, "affected_reviews": 0, "unique_escalators": 0, "avg_time_to_escalate_hours": 0.0}

    async def get_comprehensive_report(self, days: int = 30) -> dict[str, Any]:
        """Get a comprehensive usage analytics report."""
        return {
            "tenant_id": self.tenant_id,
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat(),
            "reviewer_analytics": await self.get_reviewer_analytics(days),
            "override_patterns": await self.get_override_patterns(days),
            "ai_trust_score": await self.get_ai_trust_score(days),
            "workflow_analytics": await self.get_workflow_analytics(days),
            "search_analytics": await self.get_search_analytics(days),
            "escalation_analytics": await self.get_escalation_analytics(days),
        }
