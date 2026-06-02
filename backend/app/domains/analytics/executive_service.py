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
    ExecutiveReport, ExecutiveReportRequest,
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

        return ExecutiveDashboard(
            portfolio_summary=portfolio,
            cycle_time_analytics=cycle_time,
            reviewer_efficiency=reviewer_eff,
            sla_risk_overview=sla_risk,
            negotiation_trends=negotiation,
            contract_exposure=exposure,
            throughput_bottlenecks=bottlenecks,
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
                  AND status IN ('draft', 'ai_analyzed', 'in_review', 'pending_approval')
            """),
            {"tid": self.tenant_id},
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

        return PortfolioSummary(
            total_contracts=total_contracts,
            active_reviews=active_reviews,
            contracts_this_period=contracts_this_period,
            avg_risk_score=avg_risk_score,
            risk_distribution=risk_dist,
            total_exposure=total_exposure_score,
            critical_contracts=critical_count,
            high_risk_vendors=high_risk_vendor_count,
        )

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
        # Reviewer stats
        reviewer_sql = sa_text("""
            SELECT
                assigned_to,
                COUNT(*) FILTER (WHERE status IN ('draft', 'ai_analyzed', 'in_review', 'pending_approval'))::int AS active,
                COUNT(*) FILTER (WHERE status IN ('approved', 'rejected', 'finalized', 'executed', 'closed'))::int AS completed,
                COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600), 0)::float AS avg_hours
            FROM contract_reviews
            WHERE tenant_id = :tid AND assigned_to IS NOT NULL AND created_at >= :cutoff
            GROUP BY assigned_to
        """)
        result = await self.session.execute(reviewer_sql, {"tid": self.tenant_id, "cutoff": cutoff})
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
                reviewer_name=row.assigned_to,
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
        )

    async def _build_sla_risk_overview(self) -> SLARiskOverview:
        """Build SLA risk overview."""
        # Active reviews with SLA
        sla_sql = sa_text("""
            SELECT review_id, status, assigned_to, sla_deadline,
                   sla_breached, sla_status,
                   metadata->>'document_name' AS document_name
            FROM contract_reviews
            WHERE tenant_id = :tid
              AND is_deleted = FALSE
              AND status IN ('draft', 'ai_analyzed', 'in_review', 'pending_approval')
              AND sla_deadline IS NOT NULL
        """)
        result = await self.session.execute(sla_sql, {"tid": self.tenant_id})
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
            # Estimate elapsed from created_at (approximate)
            elapsed_hours = max(0, 0)  # simplified
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
        # Redline stats
        redline_sql = sa_text("""
            SELECT clause_type, status, COUNT(*)::int AS count
            FROM review_redlines
            WHERE tenant_id = :tid AND created_at >= :cutoff
            GROUP BY clause_type, status
        """)
        result = await self.session.execute(redline_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        redline_rows = result.fetchall()

        by_type: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for row in redline_rows:
            ct = row.clause_type or "other"
            status = row.status or "proposed"
            by_type[ct][status] = row.count

        total_proposed = sum(sum(d.values()) for d in by_type.values())
        total_accepted = sum(d.get("accepted", 0) for d in by_type.values())
        acceptance_rate = round(total_accepted / total_proposed, 2) if total_proposed > 0 else 0.0

        clause_metrics: list[ClauseNegotiationMetric] = []
        most_contested: list[tuple[str, int]] = []
        for ct, statuses in sorted(by_type.items()):
            proposed = sum(statuses.values())
            accepted = statuses.get("accepted", 0)
            rate = round(accepted / proposed, 2) if proposed > 0 else 0.0
            clause_metrics.append(ClauseNegotiationMetric(
                clause_type=ct,
                proposed=proposed,
                accepted=accepted,
                acceptance_rate=rate,
                avg_rounds=1.0,
                avg_risk_reduction=0.0,
            ))
            most_contested.append((ct, proposed))

        most_contested.sort(key=lambda x: -x[1])

        return NegotiationTrends(
            total_redlines_proposed=total_proposed,
            acceptance_rate=acceptance_rate,
            avg_rounds_per_clause=1.0,
            by_clause_type=clause_metrics,
            most_contested_clauses=[c[0] for c in most_contested[:5]],
        )

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

        return ContractExposure(
            total_exposure_score=round(total_exposure, 2),
            by_category=categories,
            top_risk_drivers=risk_drivers[:5],
            concentration_risk=concentration,
        )

    async def _build_throughput_bottlenecks(
        self,
        cutoff: datetime,
    ) -> ThroughputBottlenecks:
        """Build throughput bottleneck analysis."""
        # Overall throughput
        throughput_sql = sa_text("""
            SELECT
                COUNT(*)::int AS completed,
                COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400), 0)::float AS avg_days
            FROM contract_reviews
            WHERE tenant_id = :tid AND completed_at IS NOT NULL AND created_at >= :cutoff
        """)
        result = await self.session.execute(throughput_sql, {"tid": self.tenant_id, "cutoff": cutoff})
        row = result.fetchone()
        completed = row.completed if row else 0
        days_span = max(1, (datetime.now(timezone.utc) - cutoff).days)
        throughput = round(completed / days_span, 1)

        # Queue depth (active reviews)
        queue_sql = sa_text("""
            SELECT COUNT(*)::int FROM contract_reviews
            WHERE tenant_id = :tid AND is_deleted = FALSE
              AND status IN ('draft', 'ai_analyzed', 'in_review', 'pending_approval')
        """)
        queue_result = await self.session.execute(queue_sql, {"tid": self.tenant_id})
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
        review_bottleneck_sql = sa_text("""
            SELECT COUNT(*)::int FROM contract_reviews
            WHERE tenant_id = :tid AND is_deleted = FALSE
              AND status IN ('in_review', 'pending_approval')
              AND updated_at < NOW() - INTERVAL '24 hours'
        """)
        review_b_result = await self.session.execute(
            review_bottleneck_sql, {"tid": self.tenant_id},
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

        return ThroughputBottlenecks(
            bottlenecks=bottlenecks,
            overall_throughput=throughput,
            queue_depth=queue_depth,
            avg_wait_time_hours=24.0 if queue_depth > 10 else 8.0,
        )

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
