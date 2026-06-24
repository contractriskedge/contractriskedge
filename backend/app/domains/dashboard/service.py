"""Executive Dashboard service — aggregates KPIs across all contract lifecycle domains."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DashboardService:
    """Aggregates KPIs across contracts, reviews, approvals, signatures, obligations."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def _execute(self, stmt, params=None):
        """Execute a statement with transaction recovery."""
        try:
            return await self.session.execute(stmt, params or {})
        except Exception:
            try:
                await self.session.rollback()
            except Exception:
                pass
            raise

    # ── Executive Summary ───────────────────────────────────────

    async def get_executive_summary(self) -> dict:
        """Return top-level counts for the executive dashboard."""
        total = await self._count_total_contracts()
        active = await self._count_active_contracts()
        this_month = await self._count_contracts_this_month()
        pending_approval = await self._count_pending_approvals()
        pending_signature = await self._count_pending_signatures()
        high_risk = await self._count_high_risk_contracts()
        renewals = await self._count_upcoming_renewals()
        open_obligations = await self._count_open_obligations()
        return {
            "total_contracts": total,
            "active_contracts": active,
            "contracts_this_month": this_month,
            "pending_approvals": pending_approval,
            "pending_signatures": pending_signature,
            "high_risk_contracts": high_risk,
            "upcoming_renewals": renewals,
            "open_obligations": open_obligations,
        }

    async def _count_total_contracts(self) -> int:
        try:
            row = await self.session.execute(
                sa_text("SELECT COUNT(*)::int FROM contract_reviews WHERE tenant_id = :tid"),
                {"tid": self.tenant_id},
            )
            return row.scalar() or 0
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to count total contracts: %s", exc)
            return 0

    async def _count_active_contracts(self) -> int:
        try:
            row = await self.session.execute(
                sa_text("""
                    SELECT COUNT(*)::int FROM contract_reviews
                    WHERE tenant_id = :tid
                      AND status::text NOT IN ('rejected', 'closed', 'archived')
                """),
                {"tid": self.tenant_id},
            )
            return row.scalar() or 0
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to count active contracts: %s", exc)
            return 0

    async def _count_contracts_this_month(self) -> int:
        try:
            start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            row = await self.session.execute(
                sa_text("""
                    SELECT COUNT(*)::int FROM contract_reviews
                    WHERE tenant_id = :tid AND created_at >= :start
                """),
                {"tid": self.tenant_id, "start": start},
            )
            return row.scalar() or 0
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to count contracts this month: %s", exc)
            return 0

    async def _count_pending_approvals(self) -> int:
        try:
            row = await self.session.execute(
                sa_text("""
                    SELECT COUNT(*)::int FROM contract_reviews
                    WHERE tenant_id = :tid AND status::text IN ('pending_approval', 'legal_approval', 'exec_approval')
                """),
                {"tid": self.tenant_id},
            )
            return row.scalar() or 0
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to count pending approvals: %s", exc)
            return 0

    async def _count_pending_signatures(self) -> int:
        """Count pending signatures from signature_requests table."""
        try:
            row = await self.session.execute(
                sa_text("""
                    SELECT COUNT(*)::int FROM signature_requests
                    WHERE tenant_id = :tid AND status IN ('sent', 'delivered', 'viewed', 'partially_signed')
                """),
                {"tid": self.tenant_id},
            )
            return row.scalar() or 0
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to count pending signatures: %s", exc)
            return 0

    async def _count_high_risk_contracts(self) -> int:
        """Count contracts with critical/high severity findings.

        Since contract_reviews has no risk_score column, we derive
        high-risk from review_findings: contracts with at least one
        critical or high severity finding.
        """
        try:
            row = await self.session.execute(
                sa_text("""
                    SELECT COUNT(DISTINCT cr.review_id)::int
                    FROM contract_reviews cr
                    JOIN review_findings rf ON rf.review_id = cr.review_id
                    WHERE cr.tenant_id = :tid
                      AND rf.severity IN ('critical', 'high')
                """),
                {"tid": self.tenant_id},
            )
            return row.scalar() or 0
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to count high risk contracts: %s", exc)
            return 0

    async def _count_upcoming_renewals(self) -> int:
        """Count contracts expiring within 30 days.

        Uses sla_deadline as a proxy for contract expiry when
        no dedicated expiry_date column exists.
        """
        try:
            thirty_days = datetime.now(timezone.utc) + timedelta(days=30)
            row = await self.session.execute(
                sa_text("""
                    SELECT COUNT(*)::int FROM contract_reviews
                    WHERE tenant_id = :tid
                      AND sla_deadline IS NOT NULL
                      AND sla_deadline BETWEEN NOW() AND :thirty_days
                """),
                {"tid": self.tenant_id, "thirty_days": thirty_days},
            )
            return row.scalar() or 0
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to count upcoming renewals: %s", exc)
            return 0

    async def _count_open_obligations(self) -> int:
        try:
            row = await self.session.execute(
                sa_text("""
                    SELECT COUNT(*)::int FROM obligations
                    WHERE tenant_id = :tid AND status IN ('open', 'pending')
                """),
                {"tid": self.tenant_id},
            )
            return row.scalar() or 0
        except Exception as exc:
            logger.warning("Failed to count open obligations: %s", exc)
            return 0

    # ── Risk Dashboard ──────────────────────────────────────────

    async def get_risk_distribution(self) -> dict:
        """Return risk distribution by finding severity from review_findings."""
        try:
            rows = await self.session.execute(
                sa_text("""
                    SELECT
                        COALESCE(severity, 'unknown') AS level,
                        COUNT(*)::int AS count
                    FROM review_findings
                    WHERE tenant_id = :tid
                    GROUP BY severity
                    ORDER BY level
                """),
                {"tid": self.tenant_id},
            )
            distribution = {row.level: row.count for row in rows}
            return {
                "critical": distribution.get("critical", 0),
                "high": distribution.get("high", 0),
                "medium": distribution.get("medium", 0),
                "low": distribution.get("low", 0),
                "unknown": distribution.get("unknown", 0),
            }
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to get risk distribution: %s", exc)
            return {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}

    async def get_risk_trend(self, months: int = 12) -> list[dict]:
        """Return monthly average risk_score from review_findings."""
        try:
            start = datetime.now(timezone.utc) - timedelta(days=months * 30)
            rows = await self.session.execute(
                sa_text("""
                    SELECT
                        DATE_TRUNC('month', rf.created_at) AS month,
                        AVG(rf.risk_score) AS avg_risk
                    FROM review_findings rf
                    WHERE rf.tenant_id = :tid
                      AND rf.created_at >= :start
                      AND rf.risk_score IS NOT NULL
                    GROUP BY month
                    ORDER BY month
                """),
                {"tid": self.tenant_id, "start": start},
            )
            return [
                {
                    "month": row.month.isoformat() if hasattr(row.month, 'isoformat') else str(row.month),
                    "avg_risk_score": round(float(row.avg_risk), 4) if row.avg_risk else 0,
                }
                for row in rows
            ]
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to get risk trend: %s", exc)
            return []

    # ── Workflow Dashboard ──────────────────────────────────────

    async def get_workflow_distribution(self) -> dict:
        """Return contract counts grouped by lifecycle stage."""
        try:
            rows = await self.session.execute(
                sa_text("""
                    SELECT
                        CASE
                            WHEN status::text IN ('procurement_review', 'legal_review', 'security_review', 'in_review') THEN 'in_review'
                            WHEN status::text IN ('negotiation', 'changes_requested') THEN 'in_negotiation'
                            WHEN status::text IN ('pending_approval', 'legal_approval', 'exec_approval') THEN 'pending_approval'
                            WHEN status::text IN ('approved', 'finalized') THEN 'approved'
                            WHEN status::text IN ('executed') THEN 'executed'
                            ELSE 'other'
                        END AS stage,
                        COUNT(*)::int AS count
                    FROM contract_reviews
                    WHERE tenant_id = :tid
                    GROUP BY stage
                    ORDER BY stage
                """),
                {"tid": self.tenant_id},
            )
            result: dict[str, int] = {}
            for row in rows:
                result[row.stage] = row.count
            return result
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to get workflow distribution: %s", exc)
            return {}

    # ── Renewal Dashboard ───────────────────────────────────────

    async def get_renewal_buckets(self) -> dict:
        """Return contract counts by renewal window using sla_deadline."""
        try:
            rows = await self.session.execute(
                sa_text("""
                    SELECT
                        CASE
                            WHEN sla_deadline BETWEEN NOW() AND NOW() + INTERVAL '30 days' THEN '30_days'
                            WHEN sla_deadline BETWEEN NOW() + INTERVAL '30 days' AND NOW() + INTERVAL '60 days' THEN '60_days'
                            WHEN sla_deadline BETWEEN NOW() + INTERVAL '60 days' AND NOW() + INTERVAL '90 days' THEN '90_days'
                            WHEN sla_deadline < NOW() THEN 'expired'
                            ELSE 'beyond_90'
                        END AS bucket,
                        COUNT(*)::int AS count
                    FROM contract_reviews
                    WHERE tenant_id = :tid AND sla_deadline IS NOT NULL
                    GROUP BY bucket
                    ORDER BY bucket
                """),
                {"tid": self.tenant_id},
            )
            result = {"30_days": 0, "60_days": 0, "90_days": 0, "expired": 0, "beyond_90": 0}
            for row in rows:
                result[row.bucket] = row.count
            return result
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to get renewal buckets: %s", exc)
            return {"30_days": 0, "60_days": 0, "90_days": 0, "expired": 0, "beyond_90": 0}

    # ── Signature Dashboard ─────────────────────────────────────

    async def get_signature_status_counts(self) -> dict:
        """Return signature request counts by status."""
        try:
            rows = await self.session.execute(
                sa_text("""
                    SELECT status, COUNT(*)::int AS count
                    FROM signature_requests
                    WHERE tenant_id = :tid
                    GROUP BY status
                    ORDER BY status
                """),
                {"tid": self.tenant_id},
            )
            result = {"draft": 0, "preparing": 0, "sent": 0, "viewed": 0,
                      "partially_signed": 0, "completed": 0, "declined": 0,
                      "expired": 0, "voided": 0}
            for row in rows:
                result[row.status] = row.count
            return result
        except Exception as exc:
            await self.session.rollback()
            logger.warning("Failed to get signature status counts: %s", exc)
            return {"sent": 0, "viewed": 0, "signed": 0, "declined": 0, "expired": 0}

