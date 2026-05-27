"""Analytics service — error aggregation, failure analytics, stuck workflow detection, system metrics."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text as sa_text

from app.kernel.datetime_utils import age_minutes, ensure_utc, utc_now
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analytics.schemas import (
    FailureSummary, ErrorAnalyticsResponse, StuckWorkflowItem,
    StuckWorkflowsResponse, SystemHealthResponse, MetricsSummaryResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsService:
    """Aggregates system-wide analytics from failure tables, metrics, and workflow state."""

    session: AsyncSession
    tenant_id: str

    async def get_error_analytics(self, period_hours: int = 24) -> ErrorAnalyticsResponse:
        """Aggregate failures across all failure tables."""
        # Collect failures from ai_failures
        ai_failures = await self._query_ai_failures(period_hours)
        # Collect failures from upload_sessions
        upload_failures = await self._query_upload_failures(period_hours)

        all_failures = ai_failures + upload_failures

        # Aggregate by type
        by_type: dict[str, int] = {}
        by_domain: dict[str, int] = {}
        last_occurred: dict[str, datetime] = {}

        for f in all_failures:
            ftype = f.get("failure_type", "unknown")
            domain = f.get("domain", "unknown")
            by_type[ftype] = by_type.get(ftype, 0) + 1
            by_domain[domain] = by_domain.get(domain, 0) + 1
            ts = ensure_utc(f.get("created_at"))
            if ts and (ftype not in last_occurred or ts > last_occurred[ftype]):
                last_occurred[ftype] = ts

        # Build failure summaries
        failures_by_type = [
            FailureSummary(
                failure_type=ftype,
                count=count,
                last_occurred=last_occurred.get(ftype),
                domain=self._infer_domain(ftype),
            )
            for ftype, count in sorted(by_type.items(), key=lambda x: -x[1])
        ]

        # Top failing uploads
        top_failing = await self._query_top_failing_uploads(period_hours)

        # Retryable vs non-retryable
        from app.kernel.web.error_codes import is_retryable, ErrorCode

        retryable = 0
        non_retryable = 0
        for f in all_failures:
            try:
                ec = ErrorCode(f.get("failure_type", ""))
                if is_retryable(ec):
                    retryable += 1
                else:
                    non_retryable += 1
            except (ValueError, KeyError):
                non_retryable += 1

        return ErrorAnalyticsResponse(
            total_failures=len(all_failures),
            failures_by_type=failures_by_type,
            failures_by_domain=by_domain,
            retryable_failures=retryable,
            non_retryable_failures=non_retryable,
            retryable_count=retryable,
            non_retryable_count=non_retryable,
            by_type=by_type,
            by_domain=by_domain,
            top_failing_uploads=top_failing,
            period_hours=period_hours,
        )

    async def get_stuck_workflows(self) -> StuckWorkflowsResponse:
        """Detect potentially stuck workflows across the system."""
        items: list[StuckWorkflowItem] = []
        recovery_actions: list[str] = []
        now = utc_now()

        # 1. Stuck uploads (in a non-terminal state for too long)
        stuck_uploads_sql = sa_text("""
            SELECT upload_id, ingestion_state, retry_count, ingestion_error,
                   created_at, updated_at
            FROM upload_sessions
            WHERE tenant_id = :tenant_id
              AND ingestion_state NOT IN ('review_ready', 'failed', 'cancelled', 'quarantined')
              AND updated_at < NOW() - INTERVAL '30 minutes'
            ORDER BY updated_at ASC
        """)
        result = await self.session.execute(stuck_uploads_sql, {"tenant_id": self.tenant_id})
        for row in result.fetchall():
            age = age_minutes(now, row.updated_at)
            items.append(StuckWorkflowItem(
                resource_id=str(row.upload_id),
                resource_type="upload",
                state=row.ingestion_state,
                age_minutes=int(age),
                retry_count=row.retry_count or 0,
                error_message=row.ingestion_error,
                created_at=row.created_at,
                updated_at=row.updated_at,
            ))

        # 2. Stuck AI runs (processing for >30 min)
        stuck_ai_sql = sa_text("""
            SELECT run_id, status, retry_count, error_message,
                   created_at, started_at
            FROM ai_execution_runs
            WHERE tenant_id = :tenant_id
              AND status IN ('processing', 'pending')
              AND started_at IS NOT NULL
              AND started_at < NOW() - INTERVAL '30 minutes'
            ORDER BY started_at ASC
        """)
        result = await self.session.execute(stuck_ai_sql, {"tenant_id": self.tenant_id})
        for row in result.fetchall():
            ref_time = row.started_at or row.created_at
            age = age_minutes(now, ref_time)
            items.append(StuckWorkflowItem(
                resource_id=str(row.run_id),
                resource_type="ai_run",
                state=row.status,
                age_minutes=int(age),
                retry_count=row.retry_count or 0,
                error_message=row.error_message,
                created_at=row.created_at,
                updated_at=ref_time,
            ))

        # 3. Stuck reviews (in draft or ai_analyzed for >24h)
        stuck_review_sql = sa_text("""
            SELECT review_id, status, assigned_to,
                   created_at, updated_at
            FROM contract_reviews
            WHERE tenant_id = :tenant_id
              AND is_deleted = FALSE
              AND status IN ('draft', 'ai_analyzed')
              AND updated_at < NOW() - INTERVAL '24 hours'
            ORDER BY updated_at ASC
        """)
        result = await self.session.execute(stuck_review_sql, {"tenant_id": self.tenant_id})
        for row in result.fetchall():
            age = age_minutes(now, row.updated_at)
            items.append(StuckWorkflowItem(
                resource_id=str(row.review_id),
                resource_type="review",
                state=row.status,
                age_minutes=int(age),
                created_at=row.created_at,
                updated_at=row.updated_at,
            ))

        # Build recovery actions
        if items:
            recovery_actions = [
                "Retry failed uploads (POST /uploads/{id}/retry)",
                "Cancel stuck AI runs (manual admin action)",
                "Assign unassigned reviews to available reviewers",
                "Escalate reviews stuck in draft for >48h",
            ]

        stuck_uploads = sum(1 for i in items if i.resource_type == "upload")
        stuck_ai_runs = sum(1 for i in items if i.resource_type == "ai_run")
        stuck_reviews = sum(1 for i in items if i.resource_type == "review")

        return StuckWorkflowsResponse(
            items=items,
            total=len(items),
            stuck_uploads=stuck_uploads,
            stuck_ai_runs=stuck_ai_runs,
            stuck_reviews=stuck_reviews,
            recovery_actions=recovery_actions,
        )

    async def get_system_health(self) -> SystemHealthResponse:
        """Get overall system health status."""
        # Active uploads
        active_uploads_sql = sa_text("""
            SELECT COUNT(*)::int FROM upload_sessions
            WHERE tenant_id = :tenant_id
              AND ingestion_state NOT IN ('review_ready', 'failed', 'cancelled', 'quarantined')
        """)
        result = await self.session.execute(active_uploads_sql, {"tenant_id": self.tenant_id})
        active_uploads = result.scalar() or 0

        # Active AI runs
        active_ai_sql = sa_text("""
            SELECT COUNT(*)::int FROM ai_execution_runs
            WHERE tenant_id = :tenant_id
              AND status IN ('processing', 'pending')
        """)
        result = await self.session.execute(active_ai_sql, {"tenant_id": self.tenant_id})
        active_ai = result.scalar() or 0

        # Pending reviews
        pending_reviews_sql = sa_text("""
            SELECT COUNT(*)::int FROM contract_reviews
            WHERE tenant_id = :tenant_id
              AND is_deleted = FALSE
              AND status IN ('draft', 'ai_analyzed', 'in_review', 'pending_approval')
        """)
        result = await self.session.execute(pending_reviews_sql, {"tenant_id": self.tenant_id})
        pending_reviews = result.scalar() or 0

        # Recent errors (24h)
        recent_errors_sql = sa_text("""
            SELECT COUNT(*)::int FROM ai_failures
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
        result = await self.session.execute(recent_errors_sql, {"tenant_id": self.tenant_id})
        recent_errors = result.scalar() or 0

        # SLA breaches
        sla_sql = sa_text("""
            SELECT COUNT(*)::int FROM contract_reviews
            WHERE tenant_id = :tenant_id
              AND sla_breached = TRUE
              AND updated_at > NOW() - INTERVAL '24 hours'
        """)
        result = await self.session.execute(sla_sql, {"tenant_id": self.tenant_id})
        sla_breaches = result.scalar() or 0

        status = "healthy"
        if recent_errors > 10 or sla_breaches > 5:
            status = "degraded"
        if recent_errors > 50:
            status = "unhealthy"

        return SystemHealthResponse(
            status=status,
            active_uploads=active_uploads,
            active_ai_runs=active_ai,
            pending_reviews=pending_reviews,
            recent_errors_24h=recent_errors,
            sla_breaches_24h=sla_breaches,
            sla_breaches=sla_breaches,
            upload_success_rate=100.0,  # Placeholder — computed in metrics
            ai_success_rate=100.0,      # Placeholder — computed in metrics
        )

    async def get_metrics_summary(self) -> MetricsSummaryResponse:
        """Get key system metrics for the metrics dashboard."""
        # Upload success rate (last 24h)
        upload_stats_sql = sa_text("""
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE ingestion_state = 'review_ready')::int AS success,
                COUNT(*) FILTER (WHERE ingestion_state = 'failed')::int AS failed
            FROM upload_sessions
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
        result = await self.session.execute(upload_stats_sql, {"tenant_id": self.tenant_id})
        row = result.fetchone()
        total_uploads = row.total if row else 0
        upload_success = row.success if row else 0
        upload_success_rate = (upload_success / total_uploads * 100) if total_uploads > 0 else 0.0

        # AI success rate
        ai_stats_sql = sa_text("""
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE status = 'completed')::int AS success,
                COUNT(*) FILTER (WHERE status = 'failed')::int AS failed,
                COALESCE(AVG(latency_ms), 0)::float AS avg_latency
            FROM ai_execution_runs
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
        result = await self.session.execute(ai_stats_sql, {"tenant_id": self.tenant_id})
        row = result.fetchone()
        total_ai = row.total if row else 0
        ai_success = row.success if row else 0
        ai_success_rate = (ai_success / total_ai * 100) if total_ai > 0 else 0.0
        avg_ai_latency = row.avg_latency if row else 0.0

        # Token usage
        token_sql = sa_text("""
            SELECT COALESCE(SUM(total_tokens), 0)::int AS total_tokens,
                   COALESCE(SUM(cost_usd), 0)::float AS total_cost
            FROM ai_execution_runs
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
        result = await self.session.execute(token_sql, {"tenant_id": self.tenant_id})
        row = result.fetchone()
        total_tokens = row.total_tokens if row else 0
        total_cost = row.total_cost if row else 0.0

        # Reviews in 24h
        review_sql = sa_text("""
            SELECT COUNT(*)::int AS total_reviews
            FROM contract_reviews
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
        result = await self.session.execute(review_sql, {"tenant_id": self.tenant_id})
        total_reviews = result.scalar() or 0

        # Findings in 24h
        findings_sql = sa_text("""
            SELECT COUNT(*)::int FROM review_findings
            WHERE tenant_id = :tenant_id
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
        result = await self.session.execute(findings_sql, {"tenant_id": self.tenant_id})
        total_findings = result.scalar() or 0

        return MetricsSummaryResponse(
            upload_success_rate=round(upload_success_rate, 1),
            ai_success_rate=round(ai_success_rate, 1),
            avg_ai_latency_ms=round(avg_ai_latency, 1),
            avg_upload_latency_ms=0.0,
            total_tokens_used=total_tokens,
            total_ai_cost_usd=round(total_cost, 4),
            total_cost_usd=round(total_cost, 4),
            total_uploads_24h=total_uploads,
            total_reviews_24h=total_reviews,
            total_findings_24h=total_findings,
        )

    # ── Chart Data ────────────────────────────────────────────────

    async def get_upload_trend(self, days: int = 30) -> list[dict]:
        """Upload volume per day for trend chart."""
        sql = sa_text("""
            SELECT DATE(created_at) AS day, COUNT(*)::int AS count
            FROM upload_sessions
            WHERE tenant_id = :tid AND created_at > :since
            GROUP BY DATE(created_at)
            ORDER BY day ASC
        """)
        result = await self.session.execute(sql, {
            "tid": self.tenant_id,
            "since": self._days_start(days),
        })
        return [{"day": str(r.day), "count": r.count} for r in result.fetchall()]

    async def get_risk_distribution(self) -> list[dict]:
        """Risk score distribution across reviews."""
        sql = sa_text("""
            SELECT
                CASE
                    WHEN (metadata->>'risk_score')::numeric >= 0.7 THEN 'critical'
                    WHEN (metadata->>'risk_score')::numeric >= 0.5 THEN 'high'
                    WHEN (metadata->>'risk_score')::numeric >= 0.3 THEN 'medium'
                    WHEN (metadata->>'risk_score')::numeric >= 0.1 THEN 'low'
                    ELSE 'info'
                END AS level,
                COUNT(*)::int AS count
            FROM contract_reviews
            WHERE tenant_id = :tid AND metadata->>'risk_score' IS NOT NULL
            GROUP BY level
            ORDER BY level
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [{"level": r.level, "count": r.count} for r in result.fetchall()]

    async def get_findings_by_clause(self) -> list[dict]:
        """Findings count grouped by clause type."""
        sql = sa_text("""
            SELECT clause_type, COUNT(*)::int AS count
            FROM review_findings
            WHERE tenant_id = :tid AND clause_type IS NOT NULL
            GROUP BY clause_type
            ORDER BY count DESC
            LIMIT 15
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [{"clause_type": r.clause_type, "count": r.count} for r in result.fetchall()]

    async def get_ai_cost_trend(self, days: int = 30) -> list[dict]:
        """AI cost and tokens per day."""
        sql = sa_text("""
            SELECT DATE(created_at) AS day,
                   COUNT(*)::int AS run_count,
                   COALESCE(SUM(total_tokens), 0)::int AS tokens,
                   COALESCE(SUM(cost_usd), 0)::float AS cost
            FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at > :since
            GROUP BY DATE(created_at)
            ORDER BY day ASC
        """)
        result = await self.session.execute(sql, {
            "tid": self.tenant_id,
            "since": self._days_start(days),
        })
        return [{"day": str(r.day), "runs": r.run_count, "tokens": r.tokens, "cost": round(r.cost, 4)} for r in result.fetchall()]

    async def get_review_aging(self) -> list[dict]:
        """Review aging buckets for workflow intelligence."""
        sql = sa_text("""
            SELECT
                CASE
                    WHEN NOW() - updated_at < INTERVAL '1 day' THEN 'under_1d'
                    WHEN NOW() - updated_at < INTERVAL '3 days' THEN '1_3d'
                    WHEN NOW() - updated_at < INTERVAL '7 days' THEN '3_7d'
                    ELSE 'over_7d'
                END AS bucket,
                COUNT(*)::int AS count
            FROM contract_reviews
            WHERE tenant_id = :tid
              AND is_deleted = FALSE
              AND status IN ('draft', 'ai_analyzed', 'in_review', 'pending_approval')
            GROUP BY bucket
            ORDER BY bucket
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [{"bucket": r.bucket, "count": r.count} for r in result.fetchall()]

    async def get_executive_summary(self) -> dict:
        """Executive-level portfolio intelligence."""
        # Total contracts with reviews
        total = await self.session.execute(
            sa_text("SELECT COUNT(*)::int FROM contract_reviews WHERE tenant_id = :tid AND is_deleted = FALSE"),
            {"tid": self.tenant_id},
        )
        total_contracts = total.scalar() or 0

        # Critical contracts (risk_score >= 0.7)
        critical = await self.session.execute(
            sa_text("SELECT COUNT(*)::int FROM contract_reviews WHERE tenant_id = :tid AND is_deleted = FALSE AND (metadata->>'risk_score')::numeric >= 0.7"),
            {"tid": self.tenant_id},
        )
        critical_count = critical.scalar() or 0

        # High-risk vendors — unique clause_types with critical findings
        high_risk = await self.session.execute(
            sa_text("SELECT COUNT(DISTINCT clause_type)::int FROM review_findings WHERE tenant_id = :tid AND severity IN ('critical', 'high')"),
            {"tid": self.tenant_id},
        )
        high_risk_count = high_risk.scalar() or 0

        # Missing clauses — findings about missing/absent clauses
        missing = await self.session.execute(
            sa_text("SELECT COUNT(*)::int FROM review_findings WHERE tenant_id = :tid AND (title ILIKE '%missing%' OR title ILIKE '%absent%' OR title ILIKE '%lack%')"),
            {"tid": self.tenant_id},
        )
        missing_count = missing.scalar() or 0

        # Avg SLA / review age for pending reviews
        avg_age = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (NOW() - updated_at)) / 86400), 0)::float AS avg_days
                FROM contract_reviews
                WHERE tenant_id = :tid AND is_deleted = FALSE AND status IN ('draft', 'ai_analyzed', 'in_review', 'pending_approval')
            """),
            {"tid": self.tenant_id},
        )
        avg_sla_days = round(avg_age.scalar() or 0, 1)

        # Avg risk score
        avg_risk = await self.session.execute(
            sa_text("SELECT COALESCE(AVG((metadata->>'risk_score')::numeric), 0)::float FROM contract_reviews WHERE tenant_id = :tid AND metadata->>'risk_score' IS NOT NULL"),
            {"tid": self.tenant_id},
        )
        avg_risk_score = round(avg_risk.scalar() or 0, 2)

        return {
            "total_contracts": total_contracts,
            "critical_contracts": critical_count,
            "high_risk_clause_types": high_risk_count,
            "missing_clause_findings": missing_count,
            "avg_review_sla_days": avg_sla_days,
            "avg_risk_score": avg_risk_score,
            "portfolio_risk": "HIGH" if avg_risk_score >= 0.5 else "MODERATE" if avg_risk_score >= 0.3 else "LOW",
        }

    # ── Private Helpers ──

    def _period_start(self, period_hours: int) -> datetime:
        return utc_now() - timedelta(hours=period_hours)

    def _days_start(self, days: int) -> datetime:
        """UTC cutoff for chart queries; asyncpg rejects interval strings as bind params."""
        return utc_now() - timedelta(days=days)

    async def _query_ai_failures(self, period_hours: int) -> list[dict]:
        sql = sa_text("""
            SELECT failure_type, error_message, retry_count, created_at
            FROM ai_failures
            WHERE tenant_id = :tenant_id
              AND created_at > :since
            ORDER BY created_at DESC
        """)
        result = await self.session.execute(sql, {
            "tenant_id": self.tenant_id,
            "since": self._period_start(period_hours),
        })
        return [
            {
                "failure_type": row.failure_type,
                "error_message": row.error_message,
                "retry_count": row.retry_count,
                "created_at": row.created_at,
                "domain": "ai",
            }
            for row in result.fetchall()
        ]

    async def _query_upload_failures(self, period_hours: int) -> list[dict]:
        sql = sa_text("""
            SELECT upload_id, ingestion_error, retry_count, updated_at
            FROM upload_sessions
            WHERE tenant_id = :tenant_id
              AND ingestion_state = 'failed'
              AND updated_at > :since
            ORDER BY updated_at DESC
        """)
        result = await self.session.execute(sql, {
            "tenant_id": self.tenant_id,
            "since": self._period_start(period_hours),
        })
        return [
            {
                "failure_type": "INGESTION_FAILURE",
                "error_message": row.ingestion_error,
                "retry_count": row.retry_count,
                "created_at": row.updated_at,
                "domain": "ingestion",
                "upload_id": str(row.upload_id),
            }
            for row in result.fetchall()
        ]

    async def _query_top_failing_uploads(self, period_hours: int) -> list[dict]:
        sql = sa_text("""
            SELECT upload_id, filename, ingestion_error, retry_count, updated_at
            FROM upload_sessions
            WHERE tenant_id = :tenant_id
              AND ingestion_state = 'failed'
              AND updated_at > :since
            ORDER BY retry_count DESC
            LIMIT 10
        """)
        result = await self.session.execute(sql, {
            "tenant_id": self.tenant_id,
            "since": self._period_start(period_hours),
        })
        return [
            {
                "upload_id": str(row.upload_id),
                "filename": row.filename,
                "error": row.ingestion_error,
                "retry_count": row.retry_count,
                "last_attempt": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in result.fetchall()
        ]

    @staticmethod
    def _infer_domain(failure_type: str) -> str:
        ft = failure_type.upper()
        if "OCR" in ft or "EXTRACTION" in ft:
            return "extraction"
        if "EMBEDDING" in ft or "CHUNK" in ft or "VECTOR" in ft:
            return "vectors"
        if "ANALYSIS" in ft or "AI_" in ft or "MODEL" in ft or "PROMPT" in ft:
            return "ai"
        if "UPLOAD" in ft or "STORAGE" in ft or "INGESTION" in ft:
            return "ingestion"
        if "RATE_LIMIT" in ft or "TIMEOUT" in ft:
            return "infrastructure"
        return "unknown"

    # ── Prediction Engine Integration ──────────────────────────────

    async def predict_sla_breach(self, review_id: str) -> dict:
        """Predict SLA breach probability for a single review.

        Delegates to PredictionEngine. Returns a serializable dict
        for API consumption.
        """
        from app.domains.analytics.prediction import PredictionEngine

        engine = PredictionEngine(self.session, self.tenant_id)
        risk = await engine.predict_sla_breach(review_id)
        return {
            "review_id": risk.review_id,
            "probability": risk.probability,
            "expected_remaining_hours": risk.expected_remaining_hours,
            "sla_remaining_hours": risk.sla_remaining_hours,
            "risk_factors": risk.risk_factors,
            "recommended_action": risk.recommended_action,
        }

    async def predict_batch_sla_breaches(self, limit: int = 100) -> list[dict]:
        """Predict SLA breach probability for all active reviews.

        Returns list sorted by probability descending.
        """
        from app.domains.analytics.prediction import PredictionEngine

        engine = PredictionEngine(self.session, self.tenant_id)
        risks = await engine.predict_batch_sla_breaches(limit=limit)
        return [
            {
                "review_id": r.review_id,
                "probability": r.probability,
                "expected_remaining_hours": r.expected_remaining_hours,
                "sla_remaining_hours": r.sla_remaining_hours,
                "risk_factors": r.risk_factors,
                "recommended_action": r.recommended_action,
            }
            for r in risks
        ]

    async def get_stage_duration_percentiles(self) -> dict:
        """Get P50/P75/P95 duration percentiles per workflow stage."""
        from app.domains.analytics.prediction import PredictionEngine

        engine = PredictionEngine(self.session, self.tenant_id)
        preds = await engine.get_stage_duration_percentiles()
        return {
            stage: {
                "p50_hours": p.p50_hours,
                "p75_hours": p.p75_hours,
                "p95_hours": p.p95_hours,
                "sample_count": p.sample_count,
            }
            for stage, p in preds.items()
        }

    async def predict_escalation_risk(self, review_id: str) -> dict:
        """Predict escalation probability for a review."""
        from app.domains.analytics.prediction import PredictionEngine

        engine = PredictionEngine(self.session, self.tenant_id)
        risk = await engine.predict_escalation_risk(review_id)
        return {
            "review_id": risk.review_id,
            "probability": risk.probability,
            "expected_escalation_level": risk.expected_escalation_level,
            "risk_factors": risk.risk_factors,
        }

    async def predict_bottlenecks(self) -> list[dict]:
        """Predict workflow bottlenecks."""
        from app.domains.analytics.prediction import PredictionEngine

        engine = PredictionEngine(self.session, self.tenant_id)
        bottlenecks = await engine.predict_bottlenecks()
        return [
            {
                "resource_type": b.resource_type,
                "resource_id": b.resource_id,
                "probability": b.probability,
                "expected_delay_hours": b.expected_delay_hours,
                "contributing_factors": b.contributing_factors,
            }
            for b in bottlenecks
        ]

    async def predict_reviewer_workload(self) -> list[dict]:
        """Predict workload risk for all active reviewers."""
        from app.domains.analytics.prediction import PredictionEngine

        engine = PredictionEngine(self.session, self.tenant_id)
        workloads = await engine.predict_reviewer_workload()
        return [
            {
                "reviewer_id": w.reviewer_id,
                "active_review_count": w.active_review_count,
                "max_capacity": w.max_capacity,
                "overload_probability": w.overload_probability,
                "avg_completion_hours": w.avg_completion_hours,
                "predicted_backlog_hours": w.predicted_backlog_hours,
            }
            for w in workloads
        ]
