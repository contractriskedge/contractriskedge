"""Executive Analytics service — business-level metrics for enterprise buyers.

Builds on existing analytics infrastructure to provide the metrics
that executives and enterprise buyers actually care about.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analytics.executive_schemas import (
    ExecutiveDashboard, PortfolioSummary, RiskDistribution,
    CycleTimeAnalytics, StageCycleTime, CycleTimeTrendPoint,
    ReviewerEfficiency, ReviewerMetric, EfficiencyTrendPoint,
    SLARiskOverview, SLARiskItem, BreachPrediction,
    NegotiationTrends, ClauseNegotiationMetric, NegotiationTrendPoint,
    ContractExposure, CategoryExposure, RiskDriver, ExposureTrendPoint,
    ThroughputBottlenecks, Bottleneck, ThroughputTrendPoint,
    CostGovernance, CostTrendPoint,
    AIQualityGate,
    RiskiestContract,
    BenchmarkAnalytics,
    RiskScoreTrendPoint,
    ReviewVolumeTrendPoint,
    ExecutiveReport, ExecutiveReportRequest,
)
from app.domains.analytics.status_constants import (
    ACTIVE_REVIEW_STATUSES,
    TERMINAL_REVIEW_STATUSES,
)
from app.domains.analytics.benchmark_constants import (
    BENCHMARK_CYCLE_TIME_DAYS,
    BENCHMARK_SLA_PCT,
    BENCHMARK_REVIEWER_LOAD,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutiveAnalyticsService:
    """Produces executive-level analytics from operational data."""

    session: AsyncSession
    tenant_id: str

    async def get_dashboard(
        self,
        period_days: int = 30,
    ) -> ExecutiveDashboard:
        """Build the complete executive dashboard."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        portfolio = await self._build_portfolio_summary(cutoff)
        cycle_time = await self._build_cycle_time_analytics(cutoff)
        reviewer_eff = await self._build_reviewer_efficiency(cutoff)
        sla_risk = await self._build_sla_risk_overview()
        negotiation = await self._build_negotiation_trends(cutoff)
        exposure = await self._build_contract_exposure(cutoff)
        bottlenecks = await self._build_throughput_bottlenecks(cutoff)
        cost_gov = await self._build_cost_governance(cutoff)
        ai_quality = await self._build_ai_quality_gate(cutoff)
        benchmark = await self._build_benchmark_analytics(cutoff)
        risk_trend = await self._build_risk_score_trend(cutoff)
        volume_trend = await self._build_review_volume_trend(cutoff)
        exp_trend = await self._build_exposure_trend(cutoff)
        tp_trend = await self._build_throughput_trend(cutoff)

        return ExecutiveDashboard(
            portfolio_summary=portfolio,
            cycle_time_analytics=cycle_time,
            reviewer_efficiency=reviewer_eff,
            sla_risk_overview=sla_risk,
            negotiation_trends=negotiation,
            contract_exposure=exposure,
            throughput_bottlenecks=bottlenecks,
            cost_governance=cost_gov,
            ai_quality_gate=ai_quality,
            benchmark_analytics=benchmark,
            risk_score_trend=risk_trend,
            review_volume_trend=volume_trend,
            exposure_trend=exp_trend,
            throughput_trend=tp_trend,
            period=f"last_{period_days}_days",
            generated_at=datetime.now(timezone.utc),
        )

    async def generate_report(
        self,
        request: ExecutiveReportRequest,
    ) -> ExecutiveReport:
        """Generate an executive report with findings and recommendations."""
        dashboard = await self.get_dashboard(period_days=request.period_days)

        key_findings = self._generate_key_findings(dashboard)
        recommendations = self._generate_recommendations(dashboard)

        return ExecutiveReport(
            report_id=uuid.uuid4().hex,
            title="Executive Contract Risk Report",
            period_days=request.period_days,
            generated_at=datetime.now(timezone.utc),
            dashboard=dashboard,
            key_findings=key_findings,
            recommendations=recommendations,
            format=request.format,
        )

    async def _build_portfolio_summary(
        self,
        cutoff: datetime,
    ) -> PortfolioSummary:
        """Build portfolio-level summary."""
        # Total contracts
        total = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND is_deleted = FALSE
            """),
            {"tid": self.tenant_id},
        )
        total_contracts = total.scalar() or 0

        # Active reviews
        active = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND is_deleted = FALSE
                  AND status = ANY(:active_statuses)
            """),
            {"tid": self.tenant_id, "active_statuses": ACTIVE_REVIEW_STATUSES},
        )
        active_reviews = active.scalar() or 0

        # Contracts this period
        period_total = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND is_deleted = FALSE AND created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        contracts_this_period = period_total.scalar() or 0

        # Avg risk score
        avg_risk = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG((metadata->>'risk_score')::numeric), 0)::float
                FROM contract_reviews
                WHERE tenant_id = :tid AND metadata->>'risk_score' IS NOT NULL
            """),
            {"tid": self.tenant_id},
        )
        avg_risk_score = round(avg_risk.scalar() or 0, 2)

        # Risk distribution
        risk_dist = await self._get_risk_distribution()

        # Critical contracts
        critical = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND is_deleted = FALSE
                  AND (metadata->>'risk_score')::numeric >= 0.7
            """),
            {"tid": self.tenant_id},
        )
        critical_count = critical.scalar() or 0

        # High-risk vendors
        high_risk_vendors = await self.session.execute(
            sa_text("""
                SELECT COUNT(DISTINCT metadata->>'counterparty')::int FROM upload_sessions
                WHERE tenant_id = :tid
                  AND metadata->>'counterparty' IS NOT NULL
                  AND upload_id IN (
                      SELECT DISTINCT upload_id FROM review_findings
                      WHERE tenant_id = :tid AND severity IN ('critical', 'high')
                  )
            """),
            {"tid": self.tenant_id},
        )
        high_risk_vendor_count = high_risk_vendors.scalar() or 0

        # Total exposure (sum of risk scores)
        total_exposure = await self.session.execute(
            sa_text("""
                SELECT COALESCE(SUM((metadata->>'risk_score')::numeric), 0)::float
                FROM contract_reviews
                WHERE tenant_id = :tid AND metadata->>'risk_score' IS NOT NULL
            """),
            {"tid": self.tenant_id},
        )
        total_exposure_score = round(total_exposure.scalar() or 0, 2)

        # Escalation metrics
        escalation = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(DISTINCT cr.review_id)::int AS total_reviews,
                    COUNT(DISTINCT re.review_id)::int AS escalated_reviews
                FROM contract_reviews cr
                LEFT JOIN review_escalations re ON re.review_id = cr.review_id
                WHERE cr.tenant_id = :tid
                  AND cr.created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        esc_row = escalation.fetchone()
        total_for_esc = esc_row.total_reviews if esc_row else 0
        escalated_count = esc_row.escalated_reviews if esc_row else 0
        escalation_rate = round(escalated_count / total_for_esc, 3) if total_for_esc > 0 else 0.0

        # Escalation trend (weekly)
        escalation_trend = await self._build_escalation_trend(cutoff)

        return PortfolioSummary(
            total_contracts=total_contracts,
            active_reviews=active_reviews,
            contracts_this_period=contracts_this_period,
            avg_risk_score=avg_risk_score,
            risk_distribution=risk_dist,
            total_exposure=total_exposure_score,
            critical_contracts=critical_count,
            high_risk_vendors=high_risk_vendor_count,
            escalation_rate=escalation_rate,
            escalated_reviews=escalated_count,
            escalation_trend=escalation_trend,
        )

    async def _build_escalation_trend(
        self,
        cutoff: datetime,
    ) -> list["EscalationTrendPoint"]:
        """Build weekly escalation trend."""
        from app.domains.analytics.executive_schemas import EscalationTrendPoint

        trend_sql = sa_text("""
            SELECT
                DATE_TRUNC('week', cr.created_at)::date AS week,
                COUNT(DISTINCT cr.review_id)::int AS total_reviews,
                COUNT(DISTINCT re.review_id)::int AS escalated_reviews
            FROM contract_reviews cr
            LEFT JOIN review_escalations re ON re.review_id = cr.review_id
            WHERE cr.tenant_id = :tid
              AND cr.created_at >= :cutoff
            GROUP BY DATE_TRUNC('week', cr.created_at)
            ORDER BY week ASC
        """)
        result = await self.session.execute(trend_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        return [
            EscalationTrendPoint(
                period=row.week.strftime("%Y-%m-%d") if hasattr(row.week, 'strftime') else str(row.week),
                escalated_count=row.escalated_reviews,
                total_reviews=row.total_reviews,
                escalation_rate=round(row.escalated_reviews / row.total_reviews, 3) if row.total_reviews > 0 else 0.0,
            )
            for row in result.fetchall()
        ]

    async def _get_risk_distribution(self) -> RiskDistribution:
        """Get risk score distribution."""
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
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for row in result.fetchall():
            counts[row.level] = row.count
        return RiskDistribution(**counts)

    async def _build_cycle_time_analytics(
        self,
        cutoff: datetime,
    ) -> CycleTimeAnalytics:
        """Build cycle time analytics."""
        # Overall cycle time
        cycle_sql = sa_text("""
            SELECT
                COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400), 0)::float AS avg_days,
                COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400), 0)::float AS median_days,
                COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400), 0)::float AS p95_days
            FROM contract_reviews
            WHERE tenant_id = :tid AND completed_at IS NOT NULL AND created_at >= :cutoff
        """)
        result = await self.session.execute(cycle_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        row = result.fetchone()
        avg_days = round(row.avg_days, 1) if row else 0.0
        median_days = round(row.median_days, 1) if row else 0.0
        p95_days = round(row.p95_days, 1) if row else 0.0

        # Stage-level cycle times
        stages = [
            ("ingestion", "upload_sessions", "created_at", "updated_at"),
            ("ai_analysis", "ai_execution_runs", "created_at", "completed_at"),
        ]
        stage_metrics: list[StageCycleTime] = []
        for stage_name, table, start_col, end_col in stages:
            try:
                stage_sql = sa_text(f"""
                    SELECT
                        COALESCE(AVG(EXTRACT(EPOCH FROM ({end_col} - {start_col})) / 86400), 0)::float AS avg_days,
                        COUNT(*)::int AS count
                    FROM {table}
                    WHERE tenant_id = :tid AND {end_col} IS NOT NULL AND {start_col} >= :cutoff
                """)
                s_result = await self.session.execute(
                    stage_sql, {"tid": self.tenant_id, "cutoff": cutoff},
                )
                s_row = s_result.fetchone()
                if s_row and s_row.count > 0:
                    stage_metrics.append(StageCycleTime(
                        stage=stage_name,
                        avg_days=round(s_row.avg_days, 1),
                        sample_count=s_row.count,
                    ))
            except Exception as exc:
                logger.debug("Could not compute stage cycle time for %s: %s", stage_name, exc)

        # Cycle time trend (weekly)
        trend_sql = sa_text("""
            SELECT
                DATE_TRUNC('week', created_at)::date AS week,
                COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400), 0)::float AS avg_days,
                COUNT(*)::int AS count
            FROM contract_reviews
            WHERE tenant_id = :tid AND completed_at IS NOT NULL AND created_at >= :cutoff
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week ASC
        """)
        trend_result = await self.session.execute(trend_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        trend = [
            CycleTimeTrendPoint(
                period=row.week.strftime("%Y-%m-%d") if hasattr(row.week, 'strftime') else str(row.week),
                avg_days=round(row.avg_days, 1),
                contract_count=row.count,
            )
            for row in trend_result.fetchall()
        ]

        # Benchmark comparison
        benchmark = "at_benchmark"
        if avg_days > 0 and median_days > 0:
            if avg_days < 3:
                benchmark = "faster"
            elif avg_days > 10:
                benchmark = "slower"

        return CycleTimeAnalytics(
            overall_avg_days=avg_days,
            median_days=median_days,
            p95_days=p95_days,
            by_stage=stage_metrics,
            trend=trend,
            comparison_to_benchmark=benchmark,
        )

    async def _build_reviewer_efficiency(
        self,
        cutoff: datetime,
    ) -> ReviewerEfficiency:
        """Build reviewer efficiency metrics."""
        # Reviewer stats with name lookup
        reviewer_sql = sa_text("""
            SELECT
                cr.assigned_to,
                u.name AS reviewer_name,
                COUNT(*) FILTER (WHERE cr.status = ANY(:active_statuses))::int AS active,
                COUNT(*) FILTER (WHERE cr.status = ANY(:terminal_statuses))::int AS completed,
                COALESCE(AVG(EXTRACT(EPOCH FROM (cr.completed_at - cr.created_at)) / 3600), 0)::float AS avg_hours
            FROM contract_reviews cr
            LEFT JOIN admin_users u ON u.user_id = cr.assigned_to AND u.tenant_id = :tid
            WHERE cr.tenant_id = :tid AND cr.assigned_to IS NOT NULL AND cr.created_at >= :cutoff
            GROUP BY cr.assigned_to, u.name
        """)
        result = await self.session.execute(reviewer_sql, {
            "tid": self.tenant_id,
            "cutoff": cutoff,
            "active_statuses": ACTIVE_REVIEW_STATUSES,
            "terminal_statuses": TERMINAL_REVIEW_STATUSES,
        })
        rows = result.fetchall()

        total_reviewers = len(rows)
        active_reviewers = sum(1 for r in rows if r.active > 0)
        total_active = sum(r.active for r in rows)
        total_completed = sum(r.completed for r in rows)
        avg_completion = round(
            sum(r.avg_hours * r.completed for r in rows) / total_completed, 1
        ) if total_completed > 0 else 0.0

        overloaded = 0
        details: list[ReviewerMetric] = []
        for row in rows:
            is_overloaded = row.active > 5  # threshold: >5 active reviews
            if is_overloaded:
                overloaded += 1
            details.append(ReviewerMetric(
                reviewer_id=row.assigned_to,
                reviewer_name=row.reviewer_name or row.assigned_to,
                active_reviews=row.active,
                completed_reviews=row.completed,
                avg_completion_hours=round(row.avg_hours, 1),
                backlog_hours=round(row.active * (row.avg_hours or 8), 1),
                is_overloaded=is_overloaded,
            ))

        return ReviewerEfficiency(
            total_reviewers=total_reviewers,
            active_reviewers=active_reviewers,
            avg_reviews_per_reviewer=round(total_active / total_reviewers, 1) if total_reviewers > 0 else 0.0,
            avg_review_completion_hours=avg_completion,
            reviewer_backlog=total_active,
            overloaded_reviewers=overloaded,
            reviewer_details=details,
            trend=await self._build_reviewer_efficiency_trend(cutoff),
        )

    async def _build_reviewer_efficiency_trend(
        self,
        cutoff: datetime,
    ) -> list[EfficiencyTrendPoint]:
        """Build weekly reviewer efficiency trend."""
        trend_sql = sa_text("""
            SELECT
                DATE_TRUNC('week', created_at)::date AS week,
                COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600), 0)::float AS avg_hours,
                COUNT(*)::int AS completed
            FROM contract_reviews
            WHERE tenant_id = :tid
              AND completed_at IS NOT NULL
              AND created_at >= :cutoff
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week ASC
        """)
        result = await self.session.execute(trend_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        return [
            EfficiencyTrendPoint(
                period=row.week.strftime("%Y-%m-%d") if hasattr(row.week, 'strftime') else str(row.week),
                avg_completion_hours=round(row.avg_hours, 1),
                reviews_completed=row.completed,
            )
            for row in result.fetchall()
        ]

    async def _build_sla_risk_overview(self) -> SLARiskOverview:
        """Build SLA risk overview."""
        # Active reviews with SLA
        sla_sql = sa_text("""
            SELECT review_id, status, assigned_to, sla_deadline,
                   sla_breached, sla_status, created_at,
                   metadata->>'document_name' AS document_name
            FROM contract_reviews
            WHERE tenant_id = :tid
              AND is_deleted = FALSE
              AND status = ANY(:active_statuses)
              AND sla_deadline IS NOT NULL
        """)
        result = await self.session.execute(sla_sql, {"tid": self.tenant_id, "active_statuses": ACTIVE_REVIEW_STATUSES})
        reviews = result.fetchall()

        now = datetime.now(timezone.utc)
        on_track = 0
        at_risk = 0
        critical = 0
        breached = 0
        total_sla_pct = 0.0
        sla_items: list[SLARiskItem] = []
        high_risk_ids: list[str] = []

        for row in reviews:
            deadline = row.sla_deadline
            if not deadline:
                continue

            total_hours = (deadline - now).total_seconds() / 3600
            # Real elapsed hours since review creation
            created = row.created_at if hasattr(row, 'created_at') else now
            elapsed_hours = max(0, (now - created).total_seconds() / 3600)
            remaining_pct = max(0, min(100, (total_hours / 168) * 100))  # 168h = 7d default SLA

            is_breached = row.sla_breached or False
            if is_breached:
                breached += 1
                risk_level = "critical"
            elif remaining_pct < 20:
                critical += 1
                risk_level = "critical"
            elif remaining_pct < 50:
                at_risk += 1
                risk_level = "at_risk"
            else:
                on_track += 1
                risk_level = "on_track"

            total_sla_pct += remaining_pct

            if risk_level in ("at_risk", "critical"):
                high_risk_ids.append(str(row.review_id))

            sla_items.append(SLARiskItem(
                review_id=str(row.review_id),
                document_name=row.document_name or "",
                assigned_to=row.assigned_to or "",
                status=row.status,
                sla_deadline=deadline,
                sla_remaining_pct=round(remaining_pct, 1),
                risk_level=risk_level,
                breach_probability=0.8 if risk_level == "critical" else 0.4 if risk_level == "at_risk" else 0.1,
                days_remaining=round(total_hours / 24, 1),
            ))

        avg_sla = round(total_sla_pct / len(sla_items), 1) if sla_items else 100.0

        return SLARiskOverview(
            total_active_reviews=len(sla_items),
            on_track=on_track,
            at_risk=at_risk,
            critical=critical,
            breached=breached,
            avg_sla_remaining_pct=avg_sla,
            at_risk_reviews=sla_items,
            breach_prediction=BreachPrediction(
                predicted_breaches_next_7d=critical + at_risk,
                predicted_breaches_next_30d=critical + at_risk + breached,
                high_risk_reviews=high_risk_ids[:10],
                primary_risk_factors=[
                    "Reviewer capacity constraints",
                    "Complex contract with multiple high-severity findings",
                    "Pending legal director approval",
                ],
            ),
        )

    async def _build_negotiation_trends(
        self,
        cutoff: datetime,
    ) -> NegotiationTrends:
        """Build negotiation trends from redline data."""
        # Redline stats with rounds and risk reduction
        redline_sql = sa_text("""
            SELECT
                clause_type,
                status,
                risk_level,
                finding_id,
                COUNT(*)::int AS count
            FROM review_redlines
            WHERE tenant_id = :tid AND created_at >= :cutoff
            GROUP BY clause_type, status, risk_level, finding_id
        """)
        result = await self.session.execute(redline_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        redline_rows = result.fetchall()

        # Track per-clause-type metrics
        by_type: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # Track finding_id counts per clause_type to estimate rounds
        finding_counts: dict[str, set[str]] = defaultdict(set)
        # Track risk level changes per clause_type
        risk_levels: dict[str, list[str]] = defaultdict(list)

        for row in redline_rows:
            ct = row.clause_type or "other"
            status = row.status or "proposed"
            by_type[ct][status] = by_type[ct].get(status, 0) + row.count
            if row.finding_id:
                finding_counts[ct].add(str(row.finding_id))
            if row.risk_level:
                risk_levels[ct].append(row.risk_level)

        total_proposed = sum(sum(d.values()) for d in by_type.values())
        total_accepted = sum(d.get("accepted", 0) for d in by_type.values())
        acceptance_rate = round(total_accepted / total_proposed, 2) if total_proposed > 0 else 0.0

        # Compute overall avg_rounds_per_clause
        risk_weight = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.15, "info": 0.0}
        total_rounds_weighted = 0.0
        total_clause_weight = 0

        clause_metrics: list[ClauseNegotiationMetric] = []
        most_contested: list[tuple[str, int]] = []
        for ct, statuses in sorted(by_type.items()):
            proposed = sum(statuses.values())
            accepted = statuses.get("accepted", 0)
            rate = round(accepted / proposed, 2) if proposed > 0 else 0.0

            # avg_rounds: total redlines / unique finding_ids (each unique finding = one negotiation instance)
            unique_findings = len(finding_counts.get(ct, set())) or 1
            avg_rounds = round(proposed / unique_findings, 1)

            # avg_risk_reduction: compare risk_level of accepted vs all proposed
            all_risk = risk_levels.get(ct, [])
            if all_risk:
                avg_risk_before = sum(risk_weight.get(rl, 0.4) for rl in all_risk) / len(all_risk)
                # Accepted redlines likely had their risk mitigated
                accepted_risk = [rl for rl in all_risk if rl in risk_weight]
                avg_risk_after = sum(risk_weight.get(rl, 0.4) for rl in accepted_risk) / len(accepted_risk) if accepted_risk else avg_risk_before
                risk_reduction = round(max(0, avg_risk_before - avg_risk_after), 2)
            else:
                risk_reduction = 0.0

            clause_metrics.append(ClauseNegotiationMetric(
                clause_type=ct,
                proposed=proposed,
                accepted=accepted,
                acceptance_rate=rate,
                avg_rounds=avg_rounds,
                avg_risk_reduction=risk_reduction,
            ))
            most_contested.append((ct, proposed))
            total_rounds_weighted += avg_rounds * proposed
            total_clause_weight += proposed

        most_contested.sort(key=lambda x: -x[1])
        overall_avg_rounds = round(total_rounds_weighted / total_clause_weight, 1) if total_clause_weight > 0 else 1.0

        # Negotiation trend (weekly)
        trend = await self._build_negotiation_trend(cutoff)

        return NegotiationTrends(
            total_redlines_proposed=total_proposed,
            acceptance_rate=acceptance_rate,
            avg_rounds_per_clause=overall_avg_rounds,
            by_clause_type=clause_metrics,
            most_contested_clauses=[c[0] for c in most_contested[:5]],
            trend=trend,
        )

    async def _build_negotiation_trend(
        self,
        cutoff: datetime,
    ) -> list[NegotiationTrendPoint]:
        """Build weekly negotiation trend."""
        trend_sql = sa_text("""
            SELECT
                DATE_TRUNC('week', created_at)::date AS week,
                COUNT(*)::int AS proposed,
                COUNT(*) FILTER (WHERE status = 'accepted')::int AS accepted
            FROM review_redlines
            WHERE tenant_id = :tid AND created_at >= :cutoff
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week ASC
        """)
        result = await self.session.execute(trend_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        return [
            NegotiationTrendPoint(
                period=row.week.strftime("%Y-%m-%d") if hasattr(row.week, 'strftime') else str(row.week),
                proposed=row.proposed,
                accepted=row.accepted,
                acceptance_rate=round(row.accepted / row.proposed, 2) if row.proposed > 0 else 0.0,
            )
            for row in result.fetchall()
        ]

    async def _build_contract_exposure(
        self,
        cutoff: datetime,
    ) -> ContractExposure:
        """Build aggregate contract exposure by category."""
        # Findings by clause type
        finding_sql = sa_text("""
            SELECT clause_type, severity, COUNT(*)::int AS count
            FROM review_findings
            WHERE tenant_id = :tid AND created_at >= :cutoff
            GROUP BY clause_type, severity
        """)
        result = await self.session.execute(finding_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        finding_rows = result.fetchall()

        severity_weight = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.15, "info": 0.0}

        by_category: dict[str, dict[str, float]] = defaultdict(lambda: {"score": 0.0, "count": 0, "max_sev": "info"})
        for row in finding_rows:
            ct = row.clause_type or "other"
            weight = severity_weight.get(row.severity, 0.0)
            by_category[ct]["score"] += weight * row.count
            by_category[ct]["count"] += row.count
            if severity_weight.get(row.severity, 0) > severity_weight.get(by_category[ct]["max_sev"], 0):
                by_category[ct]["max_sev"] = row.severity

        total_exposure = sum(d["score"] for d in by_category.values())
        categories: list[CategoryExposure] = []
        risk_drivers: list[RiskDriver] = []

        for ct, data in sorted(by_category.items(), key=lambda x: -x[1]["score"]):
            share = round((data["score"] / total_exposure * 100), 1) if total_exposure > 0 else 0.0
            categories.append(CategoryExposure(
                category=ct,
                exposure_score=round(data["score"], 2),
                exposure_share_pct=share,
                contract_count=data["count"],
                avg_severity=data["max_sev"],
            ))
            if share > 10:
                risk_drivers.append(RiskDriver(
                    clause_type=ct,
                    contribution_pct=share,
                    severity=data["max_sev"],
                    affected_contracts=data["count"],
                    recommendation=f"Review {ct.replace('_', ' ')} clauses across portfolio",
                ))

        # Concentration risk
        if risk_drivers and risk_drivers[0].contribution_pct > 40:
            concentration = "highly_concentrated"
        elif risk_drivers and risk_drivers[0].contribution_pct > 20:
            concentration = "concentrated"
        else:
            concentration = "diversified"

        # Exposure trend (weekly)
        exposure_trend = await self._build_exposure_trend(cutoff)

        # Top 5 riskiest contracts
        riskiest_sql = sa_text("""
            SELECT
                review_id,
                COALESCE(metadata->>'document_name', '') AS document_name,
                COALESCE((metadata->>'risk_score')::numeric, 0)::float AS risk_score
            FROM contract_reviews
            WHERE tenant_id = :tid
              AND is_deleted = FALSE
              AND metadata->>'risk_score' IS NOT NULL
            ORDER BY (metadata->>'risk_score')::numeric DESC
            LIMIT 5
        """)
        riskiest_result = await self.session.execute(riskiest_sql, {"tid": self.tenant_id})
        riskiest_contracts = [
            RiskiestContract(
                review_id=str(row.review_id),
                document_name=row.document_name,
                risk_score=round(row.risk_score, 2),
                exposure_score=round(row.risk_score * 10, 2),
                top_finding="",
            )
            for row in riskiest_result.fetchall()
        ]

        return ContractExposure(
            total_exposure_score=round(total_exposure, 2),
            by_category=categories,
            top_risk_drivers=risk_drivers[:5],
            exposure_trend=exposure_trend,
            concentration_risk=concentration,
            top_riskiest_contracts=riskiest_contracts,
        )

    async def _build_exposure_trend(
        self,
        cutoff: datetime,
    ) -> list[ExposureTrendPoint]:
        """Build weekly exposure trend from findings."""
        trend_sql = sa_text("""
            SELECT
                DATE_TRUNC('week', created_at)::date AS week,
                COUNT(*)::int AS finding_count,
                COALESCE(SUM(
                    CASE severity
                        WHEN 'critical' THEN 1.0
                        WHEN 'high' THEN 0.7
                        WHEN 'medium' THEN 0.4
                        WHEN 'low' THEN 0.15
                        ELSE 0.0
                    END
                ), 0)::float AS weighted_score
            FROM review_findings
            WHERE tenant_id = :tid AND created_at >= :cutoff
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week ASC
        """)
        result = await self.session.execute(trend_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        return [
            ExposureTrendPoint(
                period=row.week.strftime("%Y-%m-%d") if hasattr(row.week, 'strftime') else str(row.week),
                exposure_score=round(row.weighted_score, 2),
                contract_count=row.finding_count,
            )
            for row in result.fetchall()
        ]

    async def _build_throughput_bottlenecks(
        self,
        cutoff: datetime,
    ) -> ThroughputBottlenecks:
        """Build throughput bottleneck analysis."""
        # Overall throughput (reviews reaching terminal decision state)
        throughput_sql = sa_text("""
            SELECT
                COUNT(*)::int AS completed
            FROM review_status_history
            WHERE tenant_id = :tid
              AND to_status IN ('approved', 'rejected')
              AND created_at >= :cutoff
        """)
        result = await self.session.execute(throughput_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        completed = result.scalar() or 0
        days_span = max(1, (datetime.now(timezone.utc) - cutoff).days)
        throughput = round(completed / days_span, 1)

        # Queue depth (active reviews)
        queue_sql = sa_text("""
            SELECT COUNT(*)::int FROM contract_reviews
            WHERE tenant_id = :tid AND is_deleted = FALSE
              AND status = ANY(:active_statuses)
        """)
        queue_result = await self.session.execute(queue_sql, {"tid": self.tenant_id, "active_statuses": ACTIVE_REVIEW_STATUSES})
        queue_depth = queue_result.scalar() or 0

        # Detect bottlenecks by stage
        bottlenecks: list[Bottleneck] = []

        # Ingestion bottleneck
        ingest_sql = sa_text("""
            SELECT COUNT(*)::int FROM upload_sessions
            WHERE tenant_id = :tid
              AND ingestion_state NOT IN ('review_ready', 'failed', 'cancelled', 'quarantined')
              AND updated_at < NOW() - INTERVAL '30 minutes'
        """)
        ingest_result = await self.session.execute(ingest_sql, {"tid": self.tenant_id})
        stuck_ingestions = ingest_result.scalar() or 0
        if stuck_ingestions > 3:
            bottlenecks.append(Bottleneck(
                stage="ingestion",
                severity="high" if stuck_ingestions > 10 else "medium",
                queue_depth=stuck_ingestions,
                resource_constraint="ai_capacity",
                recommendation="Scale AI analysis workers or investigate stuck ingestions",
                affected_reviews=stuck_ingestions,
            ))

        # Review bottleneck (unassigned or stuck in review)
        stuck_review_statuses = [s for s in ACTIVE_REVIEW_STATUSES if s in ("in_review", "pending_approval")]
        review_bottleneck_sql = sa_text("""
            SELECT COUNT(*)::int FROM contract_reviews
            WHERE tenant_id = :tid AND is_deleted = FALSE
              AND status = ANY(:stuck_statuses)
              AND updated_at < NOW() - INTERVAL '24 hours'
        """)
        review_b_result = await self.session.execute(
            review_bottleneck_sql, {"tid": self.tenant_id, "stuck_statuses": stuck_review_statuses},
        )
        stuck_reviews = review_b_result.scalar() or 0
        if stuck_reviews > 3:
            bottlenecks.append(Bottleneck(
                stage="review",
                severity="high" if stuck_reviews > 10 else "medium",
                queue_depth=stuck_reviews,
                resource_constraint="reviewer_capacity",
                recommendation="Assign additional reviewers or redistribute workload",
                affected_reviews=stuck_reviews,
            ))

        # Throughput trend (weekly)
        throughput_trend = await self._build_throughput_trend(cutoff)

        return ThroughputBottlenecks(
            bottlenecks=bottlenecks,
            overall_throughput=throughput,
            queue_depth=queue_depth,
            avg_wait_time_hours=24.0 if queue_depth > 10 else 8.0,
            trend=throughput_trend,
        )

    async def _build_throughput_trend(
        self,
        cutoff: datetime,
    ) -> list[ThroughputTrendPoint]:
        """Build weekly throughput trend."""
        trend_sql = sa_text("""
            SELECT
                DATE_TRUNC('week', created_at)::date AS week,
                COUNT(*)::int AS completed
            FROM review_status_history
            WHERE tenant_id = :tid
              AND to_status IN ('approved', 'rejected')
              AND created_at >= :cutoff
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week ASC
        """)
        result = await self.session.execute(trend_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        return [
            ThroughputTrendPoint(
                period=row.week.strftime("%Y-%m-%d") if hasattr(row.week, 'strftime') else str(row.week),
                contracts_completed=row.completed,
                avg_cycle_time_days=0.0,
            )
            for row in result.fetchall()
        ]

    # ── Cost Governance ───────────────────────────────────────────

    async def _build_cost_governance(
        self,
        cutoff: datetime,
    ) -> CostGovernance:
        """Build AI cost governance metrics."""
        # Aggregate AI execution costs
        cost_sql = sa_text("""
            SELECT
                COUNT(*)::int AS total_runs,
                COALESCE(SUM(cost_usd), 0)::float AS total_cost
            FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at >= :cutoff
        """)
        result = await self.session.execute(cost_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        row = result.fetchone()
        total_runs = row.total_runs if row else 0
        total_cost = round(row.total_cost, 4) if row else 0.0

        # Total contracts in period for per-contract cost
        contract_count = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND is_deleted = FALSE AND created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        total_contracts = contract_count.scalar() or 1
        cost_per_contract = round(total_cost / total_contracts, 4) if total_contracts > 0 else 0.0

        # Monthly projection
        days_span = max(1, (datetime.now(timezone.utc) - cutoff).days)
        daily_rate = total_cost / days_span if days_span > 0 else 0.0
        monthly_projection = round(daily_rate * 30, 2)

        # Weekly cost trend
        trend_sql = sa_text("""
            SELECT
                DATE_TRUNC('week', created_at)::date AS week,
                COUNT(*)::int AS runs,
                COALESCE(SUM(cost_usd), 0)::float AS cost
            FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at >= :cutoff
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week ASC
        """)
        trend_result = await self.session.execute(trend_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        trend = [
            CostTrendPoint(
                period=row.week.strftime("%Y-%m-%d") if hasattr(row.week, 'strftime') else str(row.week),
                ai_reviews=row.runs,
                estimated_cost=round(row.cost, 4),
            )
            for row in trend_result.fetchall()
        ]

        return CostGovernance(
            total_ai_reviews=total_runs,
            estimated_ai_cost=total_cost,
            cost_per_contract=cost_per_contract,
            monthly_projection=monthly_projection,
            trend=trend,
        )

    # ── AI Quality Gate ───────────────────────────────────────────

    async def _build_ai_quality_gate(
        self,
        cutoff: datetime,
    ) -> AIQualityGate:
        """Build AI quality monitoring metrics."""
        quality_sql = sa_text("""
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE status = 'completed')::int AS completed,
                COUNT(*) FILTER (WHERE status = 'failed')::int AS failed,
                COALESCE(AVG(findings_count), 0)::float AS avg_findings,
                COALESCE(AVG(latency_ms), 0)::float AS avg_latency_ms
            FROM ai_execution_runs
            WHERE tenant_id = :tid AND created_at >= :cutoff
        """)
        result = await self.session.execute(quality_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        row = result.fetchone()
        total = row.total if row else 0
        completed = row.completed if row else 0
        failed = row.failed if row else 0
        avg_findings = round(row.avg_findings, 2) if row else 0.0
        avg_latency_ms = row.avg_latency_ms if row else 0.0
        success_rate = round((completed / total * 100), 1) if total > 0 else 0.0

        return AIQualityGate(
            success_rate=success_rate,
            completed_runs=completed,
            failed_runs=failed,
            avg_findings=avg_findings,
            avg_processing_seconds=round(avg_latency_ms / 1000, 2),
        )

    # ── Benchmark Analytics ───────────────────────────────────────

    async def _build_benchmark_analytics(
        self,
        cutoff: datetime,
    ) -> BenchmarkAnalytics:
        """Build operational benchmarks comparing current performance against targets."""
        # Current cycle time
        ct_sql = sa_text("""
            SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400), 0)::float AS avg_days
            FROM contract_reviews
            WHERE tenant_id = :tid AND completed_at IS NOT NULL AND created_at >= :cutoff
        """)
        ct_result = await self.session.execute(ct_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        ct_row = ct_result.fetchone()
        current_cycle_time = ct_row.avg_days if ct_row else 0.0

        # Current SLA compliance
        sla_sql = sa_text("""
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE sla_breached = FALSE OR sla_breached IS NULL)::int AS compliant
            FROM contract_reviews
            WHERE tenant_id = :tid AND is_deleted = FALSE AND created_at >= :cutoff
        """)
        sla_result = await self.session.execute(sla_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        sla_row = sla_result.fetchone()
        sla_total = sla_row.total if sla_row else 0
        sla_compliant = sla_row.compliant if sla_row else 0
        sla_compliance_pct = round((sla_compliant / sla_total * 100), 1) if sla_total > 0 else -1.0  # -1 means no data

        # Current reviewer load (active reviews / active reviewers)
        load_sql = sa_text("""
            SELECT
                COUNT(*) FILTER (WHERE status = ANY(:active_statuses))::int AS active,
                COUNT(DISTINCT assigned_to) FILTER (WHERE assigned_to IS NOT NULL AND status = ANY(:active_statuses))::int AS reviewers
            FROM contract_reviews
            WHERE tenant_id = :tid AND is_deleted = FALSE
        """)
        load_result = await self.session.execute(load_sql, {"tid": self.tenant_id, "active_statuses": ACTIVE_REVIEW_STATUSES})
        load_row = load_result.fetchone()
        active_reviews = load_row.active if load_row else 0
        active_reviewers = load_row.reviewers if load_row else 1
        current_reviewer_load = round(active_reviews / max(active_reviewers, 1), 1)

        # Compare against benchmarks
        ct_benchmark = "on_track"
        if current_cycle_time > 0:
            if current_cycle_time < BENCHMARK_CYCLE_TIME_DAYS * 0.8:
                ct_benchmark = "ahead"
            elif current_cycle_time > BENCHMARK_CYCLE_TIME_DAYS * 1.2:
                ct_benchmark = "behind"

        sla_benchmark = "on_track"
        if sla_compliance_pct < 0:
            sla_benchmark = "no_data"
        elif sla_compliance_pct < BENCHMARK_SLA_PCT * 0.95:
            sla_benchmark = "behind"
        elif sla_compliance_pct >= BENCHMARK_SLA_PCT:
            sla_benchmark = "ahead"

        load_benchmark = "on_track"
        if current_reviewer_load > 0:
            if current_reviewer_load <= BENCHMARK_REVIEWER_LOAD * 0.8:
                load_benchmark = "ahead"
            elif current_reviewer_load > BENCHMARK_REVIEWER_LOAD:
                load_benchmark = "behind"
        elif active_reviews == 0 and active_reviewers <= 1:
            load_benchmark = "no_data"

        return BenchmarkAnalytics(
            cycle_time_vs_benchmark=ct_benchmark,
            sla_vs_benchmark=sla_benchmark,
            reviewer_efficiency_vs_benchmark=load_benchmark,
            benchmark_cycle_time_days=BENCHMARK_CYCLE_TIME_DAYS,
            benchmark_sla_pct=BENCHMARK_SLA_PCT,
            benchmark_reviewer_load=BENCHMARK_REVIEWER_LOAD,
            current_cycle_time_days=round(current_cycle_time, 1),
            current_sla_pct=round(sla_compliance_pct, 1),
            current_reviewer_load=current_reviewer_load,
        )

    # ── Executive Trends ─────────────────────────────────────────

    async def _build_risk_score_trend(
        self,
        cutoff: datetime,
    ) -> list[RiskScoreTrendPoint]:
        """Build weekly risk score trend."""
        sql = sa_text("""
            SELECT
                DATE_TRUNC('week', created_at)::date AS week,
                COALESCE(AVG((metadata->>'risk_score')::numeric), 0)::float AS avg_risk,
                COUNT(*)::int AS cnt
            FROM contract_reviews
            WHERE tenant_id = :tid
              AND metadata->>'risk_score' IS NOT NULL
              AND created_at >= :cutoff
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week ASC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "cutoff": cutoff})
        return [
            RiskScoreTrendPoint(
                period=row.week.strftime("%Y-%m-%d") if hasattr(row.week, 'strftime') else str(row.week),
                avg_risk_score=round(row.avg_risk, 4),
                contract_count=row.cnt,
            )
            for row in result.fetchall()
        ]

    async def _build_review_volume_trend(
        self,
        cutoff: datetime,
    ) -> list[ReviewVolumeTrendPoint]:
        """Build weekly review volume trend."""
        sql = sa_text("""
            SELECT
                week,
                COALESCE(created_cnt, 0)::int AS created,
                COALESCE(completed_cnt, 0)::int AS completed
            FROM (
                SELECT
                    DATE_TRUNC('week', created_at)::date AS week,
                    COUNT(*)::int AS created_cnt
                FROM contract_reviews
                WHERE tenant_id = :tid AND created_at >= :cutoff
                GROUP BY DATE_TRUNC('week', created_at)
            ) c
            FULL JOIN (
                SELECT
                    DATE_TRUNC('week', completed_at)::date AS week,
                    COUNT(*)::int AS completed_cnt
                FROM contract_reviews
                WHERE tenant_id = :tid
                  AND completed_at IS NOT NULL
                  AND completed_at >= :cutoff
                GROUP BY DATE_TRUNC('week', completed_at)
            ) d USING (week)
            ORDER BY week ASC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "cutoff": cutoff})
        return [
            ReviewVolumeTrendPoint(
                period=row.week.strftime("%Y-%m-%d") if hasattr(row.week, 'strftime') else str(row.week),
                reviews_created=row.created,
                reviews_completed=row.completed,
            )
            for row in result.fetchall()
        ]

    def _generate_key_findings(self, dashboard: ExecutiveDashboard) -> list[str]:
        """Generate key findings from dashboard data."""
        findings: list[str] = []
        ps = dashboard.portfolio_summary

        if ps.critical_contracts > 0:
            findings.append(f"{ps.critical_contracts} contracts with critical risk score require immediate attention")
        if ps.avg_risk_score > 0.5:
            findings.append(f"Portfolio average risk score of {ps.avg_risk_score} indicates elevated overall exposure")

        sla = dashboard.sla_risk_overview
        if sla.critical > 0:
            findings.append(f"{sla.critical} reviews at critical SLA risk — potential breaches within 24 hours")
        if sla.at_risk > 0:
            findings.append(f"{sla.at_risk} reviews approaching SLA deadlines")

        ct = dashboard.cycle_time_analytics
        if ct.overall_avg_days > 7:
            findings.append(f"Average cycle time of {ct.overall_avg_days} days exceeds target — investigate workflow bottlenecks")

        re = dashboard.reviewer_efficiency
        if re.overloaded_reviewers > 0:
            findings.append(f"{re.overloaded_reviewers} reviewers are overloaded — redistribute workload")

        exposure = dashboard.contract_exposure
        if exposure.top_risk_drivers:
            top = exposure.top_risk_drivers[0]
            findings.append(f"Primary risk driver: {top.clause_type} clauses ({top.contribution_pct}% of total exposure)")

        return findings

    def _generate_recommendations(self, dashboard: ExecutiveDashboard) -> list[str]:
        """Generate actionable recommendations from dashboard data."""
        recommendations: list[str] = []

        sla = dashboard.sla_risk_overview
        if sla.critical > 0:
            recommendations.append("Escalate critical SLA reviews to senior reviewers immediately")
        if sla.at_risk > 0:
            recommendations.append("Implement automated SLA breach notifications for at-risk reviews")

        re = dashboard.reviewer_efficiency
        if re.overloaded_reviewers > 0:
            recommendations.append("Add 2-3 additional reviewers to reduce backlog and prevent SLA breaches")

        ct = dashboard.cycle_time_analytics
        if ct.overall_avg_days > 7:
            recommendations.append("Review AI analysis pipeline for optimization opportunities to reduce cycle time")

        exposure = dashboard.contract_exposure
        if exposure.concentration_risk in ("concentrated", "highly_concentrated"):
            recommendations.append(
                f"Develop playbook standards for top risk drivers to reduce portfolio concentration risk"
            )

        recommendations.append("Schedule weekly executive review for contracts with risk score > 0.7")
        recommendations.append("Enable automated policy enforcement for recurring clause deviations")

        return recommendations
