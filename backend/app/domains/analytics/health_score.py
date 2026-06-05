"""Tenant Health Scoring — per-tenant operational health intelligence.

Computes a composite health score for each tenant based on:
  - SLA compliance rate (% of reviews meeting SLA)
  - Backlog pressure (pending review volume vs throughput)
  - Escalation rate (% of reviews escalated)
  - Delivery reliability (WebSocket delivery success rate)
  - Replay storm frequency
  - Worker health (stale worker count, queue depth)

Scores range from 0.0 (critical) to 1.0 (healthy).
Used by:
  - Admin diagnostics dashboard (tenant list view)
  - Customer success reviews (30-day trend)
  - Alerting thresholds (score drops trigger notifications)
  - Capacity planning (identify tenants needing more resources)

Usage:
    scorer = TenantHealthScorer(session)
    score = await scorer.score_tenant("tenant-123")
    all_scores = await scorer.score_all_tenants()
    history = await scorer.get_health_history("tenant-123", days=30)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func as sa_func, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analytics.status_constants import ACTIVE_REVIEW_STATUSES

logger = logging.getLogger(__name__)


# ── Scoring Weights ──────────────────────────────────────────────

# Each dimension contributes to the composite score.
# Weights should sum to 1.0.

_SLA_WEIGHT = 0.30
_BACKLOG_WEIGHT = 0.20
_ESCALATION_WEIGHT = 0.15
_DELIVERY_WEIGHT = 0.15
_REPLAY_WEIGHT = 0.10
_WORKER_WEIGHT = 0.10


# ── Thresholds ───────────────────────────────────────────────────

_SLA_TARGET_RATE = 0.95       # 95% of reviews should meet SLA
_MAX_BACKLOG_RATIO = 3.0      # backlog / weekly throughput > 3 → critical
_MAX_ESCALATION_RATE = 0.15   # 15% escalation rate → warning
_MIN_DELIVERY_RATE = 0.98     # 98% delivery success → minimum
_MAX_REPLAY_STORMS = 2        # >2 storms/day → warning
_MAX_STALE_WORKERS = 1        # >1 stale worker → warning


# ── Health Models ────────────────────────────────────────────────


@dataclass
class TenantHealthDimension:
    """Score for a single health dimension."""
    name: str
    score: float  # 0.0 to 1.0
    weight: float
    details: str = ""


@dataclass
class TenantHealthScore:
    """Complete health score for a single tenant."""
    tenant_id: str
    composite_score: float  # 0.0 to 1.0
    status: str  # 'healthy', 'degraded', 'critical', 'unknown'
    dimensions: list[TenantHealthDimension] = field(default_factory=list)
    trend: str = "stable"  # 'improving', 'stable', 'declining'
    summary: str = ""


@dataclass
class TenantHealthHistory:
    """Health score history for trend analysis."""
    tenant_id: str
    scores: list[dict] = field(default_factory=list)  # {date, score, status}
    current_score: float = 0.0
    trend: str = "stable"
    days_analyzed: int = 30


# ── Health Scorer ────────────────────────────────────────────────


class TenantHealthScorer:
    """Computes per-tenant operational health scores.

    Usage:
        scorer = TenantHealthScorer(session)
        score = await scorer.score_tenant("tenant-123")
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def score_tenant(self, tenant_id: str) -> TenantHealthScore:
        """Compute composite health score for a single tenant.

        Evaluates all six dimensions and returns a weighted score.
        """
        dimensions: list[TenantHealthDimension] = []

        # Dimension 1: SLA Compliance
        sla_score = await self._score_sla_compliance(tenant_id)
        dimensions.append(sla_score)

        # Dimension 2: Backlog Pressure
        backlog_score = await self._score_backlog_pressure(tenant_id)
        dimensions.append(backlog_score)

        # Dimension 3: Escalation Rate
        escalation_score = await self._score_escalation_rate(tenant_id)
        dimensions.append(escalation_score)

        # Dimension 4: Delivery Reliability
        delivery_score = await self._score_delivery_reliability(tenant_id)
        dimensions.append(delivery_score)

        # Dimension 5: Replay Storm Frequency
        replay_score = await self._score_replay_storms(tenant_id)
        dimensions.append(replay_score)

        # Dimension 6: Worker Health
        worker_score = await self._score_worker_health(tenant_id)
        dimensions.append(worker_score)

        # Composite: weighted average
        composite = sum(d.score * d.weight for d in dimensions)

        # Status classification
        status = self._classify_status(composite)

        # Trend (simple: compare to historical)
        trend = await self._compute_trend(tenant_id, composite)

        # Summary
        summary = self._build_summary(dimensions, composite, status)

        return TenantHealthScore(
            tenant_id=tenant_id,
            composite_score=round(composite, 3),
            status=status,
            dimensions=dimensions,
            trend=trend,
            summary=summary,
        )

    async def score_all_tenants(self) -> list[TenantHealthScore]:
        """Compute health scores for all active tenants."""
        result = await self.session.execute(
            sa_text("SELECT tenant_id FROM tenants WHERE is_active = TRUE")
        )
        tenants = result.fetchall()

        scores = []
        for (tid,) in tenants:
            try:
                score = await self.score_tenant(str(tid))
                scores.append(score)
            except Exception as exc:
                logger.warning("[HealthScore] Failed to score tenant %s: %s", tid, exc)

        # Sort by score ascending (worst first)
        scores.sort(key=lambda s: s.composite_score)
        return scores

    async def get_health_history(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> TenantHealthHistory:
        """Get health score history for trend analysis.

        Computes daily scores for the lookback period.
        """
        from app.domains.review.models import ReviewStatusHistory

        scores = []
        now = datetime.now(timezone.utc)

        for day_offset in range(days, -1, -1):
            day = now - timedelta(days=day_offset)
            day_end = day + timedelta(days=1)

            # Compute a simplified daily score from available metrics
            # SLA compliance for that day
            sla_result = await self.session.execute(
                sa_text("""
                    SELECT
                        COUNT(*)::int AS total,
                        COUNT(*) FILTER (WHERE to_status IN ('approved', 'rejected'))::int AS completed
                    FROM review_status_history
                    WHERE tenant_id = :tid
                      AND created_at >= :day_start
                      AND created_at < :day_end
                """),
                {
                    "tid": tenant_id,
                    "day_start": day,
                    "day_end": day_end,
                },
            )
            row = sla_result.fetchone()
            daily_completion_rate = (row.completed / max(row.total, 1)) if row else 0.5

            # Simplified score (just SLA + completion for history)
            daily_score = 0.5 + (daily_completion_rate * 0.3)

            scores.append({
                "date": day.strftime("%Y-%m-%d"),
                "score": round(min(daily_score, 1.0), 3),
                "status": self._classify_status(daily_score),
                "reviews_completed": row.completed if row else 0,
                "reviews_total": row.total if row else 0,
            })

        current = scores[-1]["score"] if scores else 0.5
        trend = "stable"
        if len(scores) >= 7:
            recent = sum(s["score"] for s in scores[-7:]) / 7
            previous = sum(s["score"] for s in scores[-14:-7]) / 7 if len(scores) >= 14 else recent
            if recent > previous + 0.05:
                trend = "improving"
            elif recent < previous - 0.05:
                trend = "declining"

        return TenantHealthHistory(
            tenant_id=tenant_id,
            scores=scores,
            current_score=round(current, 3),
            trend=trend,
            days_analyzed=days,
        )

    # ── Dimension Scorers ───────────────────────────────────────

    async def _score_sla_compliance(self, tenant_id: str) -> TenantHealthDimension:
        """Score SLA compliance rate."""
        result = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE sla_breached = TRUE)::int AS breached
                FROM contract_reviews
                WHERE tenant_id = :tid
                  AND is_deleted = FALSE
                  AND created_at > NOW() - INTERVAL '30 days'
            """),
            {"tid": tenant_id},
        )
        row = result.fetchone()
        total = row.total if row else 0
        breached = row.breached if row else 0

        if total == 0:
            return TenantHealthDimension(
                name="SLA Compliance", score=1.0, weight=_SLA_WEIGHT,
                details="No reviews in period",
            )

        compliance_rate = 1.0 - (breached / total)
        score = min(compliance_rate / _SLA_TARGET_RATE, 1.0)

        return TenantHealthDimension(
            name="SLA Compliance",
            score=round(score, 3),
            weight=_SLA_WEIGHT,
            details=f"{breached}/{total} reviews breached SLA ({compliance_rate:.0%} compliance)",
        )

    async def _score_backlog_pressure(self, tenant_id: str) -> TenantHealthDimension:
        """Score backlog pressure."""
        # Active reviews (using shared status constants)
        active_result = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS active
                FROM contract_reviews
                WHERE tenant_id = :tid
                  AND is_deleted = FALSE
                  AND status = ANY(:active_statuses)
            """),
            {"tid": tenant_id, "active_statuses": ACTIVE_REVIEW_STATUSES},
        )
        active = active_result.fetchone().active or 0

        # Weekly throughput (completed reviews in last 7 days)
        throughput_result = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS completed
                FROM review_status_history
                WHERE tenant_id = :tid
                  AND to_status IN ('approved', 'rejected')
                  AND created_at > NOW() - INTERVAL '7 days'
            """),
            {"tid": tenant_id},
        )
        weekly_throughput = throughput_result.fetchone().completed or 1  # Avoid div by 0

        backlog_ratio = active / max(weekly_throughput, 1)

        if backlog_ratio <= 1.0:
            score = 1.0
        elif backlog_ratio <= _MAX_BACKLOG_RATIO:
            score = 1.0 - ((backlog_ratio - 1.0) / (_MAX_BACKLOG_RATIO - 1.0)) * 0.5
        else:
            score = max(0.1, 0.5 - ((backlog_ratio - _MAX_BACKLOG_RATIO) / _MAX_BACKLOG_RATIO) * 0.4)

        return TenantHealthDimension(
            name="Backlog Pressure",
            score=round(score, 3),
            weight=_BACKLOG_WEIGHT,
            details=f"{active} active, {weekly_throughput}/week throughput (ratio {backlog_ratio:.1f})",
        )

    async def _score_escalation_rate(self, tenant_id: str) -> TenantHealthDimension:
        """Score escalation rate."""
        result = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(DISTINCT cr.review_id)::int AS total_reviews,
                    COUNT(DISTINCT re.review_id)::int AS escalated_reviews
                FROM contract_reviews cr
                LEFT JOIN review_escalations re ON re.review_id = cr.review_id
                WHERE cr.tenant_id = :tid
                  AND cr.created_at > NOW() - INTERVAL '30 days'
            """),
            {"tid": tenant_id},
        )
        row = result.fetchone()
        total = row.total_reviews if row else 0
        escalated = row.escalated_reviews if row else 0

        if total == 0:
            return TenantHealthDimension(
                name="Escalation Rate", score=1.0, weight=_ESCALATION_WEIGHT,
                details="No reviews in period",
            )

        escalation_rate = escalated / total
        if escalation_rate <= _MAX_ESCALATION_RATE:
            score = 1.0 - (escalation_rate / _MAX_ESCALATION_RATE) * 0.3
        else:
            score = max(0.1, 0.7 - ((escalation_rate - _MAX_ESCALATION_RATE) / _MAX_ESCALATION_RATE) * 0.6)

        return TenantHealthDimension(
            name="Escalation Rate",
            score=round(score, 3),
            weight=_ESCALATION_WEIGHT,
            details=f"{escalated}/{total} reviews escalated ({escalation_rate:.1%})",
        )

    async def _score_delivery_reliability(self, tenant_id: str) -> TenantHealthDimension:
        """Score WebSocket delivery reliability.

        Uses Prometheus metrics if available, otherwise assumes healthy.
        """
        try:
            from prometheus_client import REGISTRY

            # Try to read delivery metrics
            total_sent = 0
            total_failed = 0

            for metric in REGISTRY.collect():
                if metric.name == "ws_messages_sent_total":
                    for sample in metric.samples:
                        if tenant_id[:8] in str(sample.labels):
                            total_sent += sample.value
                if metric.name == "ws_delivery_failures_total":
                    for sample in metric.samples:
                        if tenant_id[:8] in str(sample.labels):
                            total_failed += sample.value

            if total_sent == 0 and total_failed == 0:
                return TenantHealthDimension(
                    name="Delivery Reliability", score=1.0, weight=_DELIVERY_WEIGHT,
                    details="No WebSocket traffic in period",
                )

            delivery_rate = total_sent / max(total_sent + total_failed, 1)
            score = min(delivery_rate / _MIN_DELIVERY_RATE, 1.0)

            return TenantHealthDimension(
                name="Delivery Reliability",
                score=round(score, 3),
                weight=_DELIVERY_WEIGHT,
                details=f"{total_sent:.0f} delivered, {total_failed:.0f} failed ({delivery_rate:.1%})",
            )
        except Exception:
            return TenantHealthDimension(
                name="Delivery Reliability", score=1.0, weight=_DELIVERY_WEIGHT,
                details="Metrics unavailable — assuming healthy",
            )

    async def _score_replay_storms(self, tenant_id: str) -> TenantHealthDimension:
        """Score replay storm frequency."""
        try:
            from app.kernel.telemetry.diagnostics import diagnostics_service

            reconnect_stats = diagnostics_service.get_reconnect_stats(tenant_id)
            recent = reconnect_stats.get("recent_reconnects", 0)
            storm_detected = reconnect_stats.get("storm_detected", False)

            if storm_detected:
                score = 0.2
            elif recent > _MAX_REPLAY_STORMS:
                score = max(0.3, 1.0 - (recent / 10.0))
            else:
                score = 1.0

            return TenantHealthDimension(
                name="Replay Stability",
                score=round(score, 3),
                weight=_REPLAY_WEIGHT,
                details=f"{recent} recent reconnects{' (STORM)' if storm_detected else ''}",
            )
        except Exception:
            return TenantHealthDimension(
                name="Replay Stability", score=1.0, weight=_REPLAY_WEIGHT,
                details="Diagnostics unavailable",
            )

    async def _score_worker_health(self, tenant_id: str) -> TenantHealthDimension:
        """Score worker health."""
        from app.domains.admin.heartbeat_models import WorkerHeartbeat

        try:
            # Active workers
            active_result = await self.session.execute(
                select(WorkerHeartbeat).where(
                    WorkerHeartbeat.last_heartbeat_at
                    >= sa_func.now() - sa_text("INTERVAL '5 minutes'"),
                )
            )
            active_workers = len(active_result.scalars().all())

            # Stale workers
            stale_result = await self.session.execute(
                select(WorkerHeartbeat).where(
                    WorkerHeartbeat.last_heartbeat_at
                    < sa_func.now() - sa_text("INTERVAL '10 minutes'"),
                    WorkerHeartbeat.status.in_(["active", "idle"]),
                )
            )
            stale_workers = len(stale_result.scalars().all())

            if active_workers == 0 and stale_workers == 0:
                return TenantHealthDimension(
                    name="Worker Health", score=0.5, weight=_WORKER_WEIGHT,
                    details="No worker data — may be unmonitored",
                )

            if stale_workers > _MAX_STALE_WORKERS:
                score = max(0.1, 1.0 - (stale_workers / 5.0))
            elif stale_workers > 0:
                score = 0.6
            else:
                score = 1.0

            return TenantHealthDimension(
                name="Worker Health",
                score=round(score, 3),
                weight=_WORKER_WEIGHT,
                details=f"{active_workers} active, {stale_workers} stale",
            )
        except Exception:
            return TenantHealthDimension(
                name="Worker Health", score=0.7, weight=_WORKER_WEIGHT,
                details="Worker heartbeat table unavailable",
            )

    # ── Helpers ─────────────────────────────────────────────────

    def _classify_status(self, score: float) -> str:
        """Classify a score into a health status."""
        if score >= 0.8:
            return "healthy"
        elif score >= 0.5:
            return "degraded"
        elif score >= 0.2:
            return "critical"
        else:
            return "unknown"

    async def _compute_trend(self, tenant_id: str, current_score: float) -> str:
        """Compute health trend by comparing to historical average."""
        try:
            history = await self.get_health_history(tenant_id, days=14)
            if len(history.scores) >= 7:
                recent_avg = sum(s["score"] for s in history.scores[-7:]) / 7
                if current_score > recent_avg + 0.05:
                    return "improving"
                elif current_score < recent_avg - 0.05:
                    return "declining"
            return "stable"
        except Exception:
            return "stable"

    def _build_summary(
        self,
        dimensions: list[TenantHealthDimension],
        composite: float,
        status: str,
    ) -> str:
        """Build a human-readable health summary."""
        low_scores = [d for d in dimensions if d.score < 0.5]
        if not low_scores:
            return f"All dimensions healthy (score: {composite:.1%})"

        weak_areas = ", ".join(d.name for d in low_scores)
        return f"Score: {composite:.1%} ({status}). Areas needing attention: {weak_areas}"


# ── Factory ──────────────────────────────────────────────────────

def get_health_scorer(session: AsyncSession) -> TenantHealthScorer:
    """Create a TenantHealthScorer."""
    return TenantHealthScorer(session=session)
