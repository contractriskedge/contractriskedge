"""Executive Reporting Automation — scheduled reports, anomaly detection, trend narratives, digests."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analytics.executive_service import ExecutiveAnalyticsService
from app.domains.analytics.reporting_schemas import (
    ReportFrequency, ReportDay, DigestStyle, AnomalySeverity, AnomalyCategory,
    ScheduledReportCreate, ScheduledReportUpdate, ScheduledReportResponse,
    ReportGenerationRecord,
    AnomalyDetectionResult, AnomalyItem,
    TrendNarrative, TrendNarrativeSet,
    ExecutiveDigest, PortfolioSnapshot, KeyMetricsSummary,
)

logger = logging.getLogger(__name__)


@dataclass
class ReportScheduler:
    """Manages scheduled executive report configurations."""

    session: AsyncSession
    tenant_id: str

    async def create_schedule(self, schedule: ScheduledReportCreate, actor: str) -> ScheduledReportResponse:
        """Create a scheduled report configuration."""
        now = datetime.now(timezone.utc)
        report_id = uuid.uuid4().hex[:12]

        next_scheduled = self._compute_next_run(schedule.frequency, schedule.day_of_week, schedule.day_of_month, schedule.time_of_day)

        sql = sa_text("""
            INSERT INTO scheduled_reports (report_id, tenant_id, name, description,
                frequency, day_of_week, day_of_month, time_of_day, digest_style,
                period_days, recipients, include_trends, include_recommendations,
                is_active, channels, next_scheduled_at, created_by, created_at, updated_at)
            VALUES (:rid, :tid, :name, :desc,
                :freq, :dow, :dom, :tod, :style,
                :period, :recipients, :trends, :recs,
                :active, :channels, :next, :actor, :now, :now)
            RETURNING report_id, name, description, frequency, day_of_week, day_of_month,
                time_of_day, digest_style, period_days, recipients, include_trends,
                include_recommendations, is_active, channels, last_generated_at,
                next_scheduled_at, total_generations, created_by, created_at, updated_at
        """)
        result = await self.session.execute(sql, {
            "rid": report_id,
            "tid": self.tenant_id,
            "name": schedule.name,
            "desc": schedule.description,
            "freq": schedule.frequency.value if hasattr(schedule.frequency, 'value') else schedule.frequency,
            "dow": schedule.day_of_week.value if schedule.day_of_week and hasattr(schedule.day_of_week, 'value') else schedule.day_of_week,
            "dom": schedule.day_of_month,
            "tod": schedule.time_of_day,
            "style": schedule.digest_style.value if hasattr(schedule.digest_style, 'value') else schedule.digest_style,
            "period": schedule.period_days,
            "recipients": schedule.recipients,
            "trends": schedule.include_trends,
            "recs": schedule.include_recommendations,
            "active": schedule.is_active,
            "channels": schedule.channels,
            "next": next_scheduled,
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return self._row_to_schedule_response(row)

    async def list_schedules(self) -> list[ScheduledReportResponse]:
        """List all scheduled reports for the tenant."""
        sql = sa_text("""
            SELECT * FROM scheduled_reports
            WHERE tenant_id = :tid
            ORDER BY next_scheduled_at ASC NULLS LAST
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [self._row_to_schedule_response(r) for r in result.fetchall()]

    async def get_schedule(self, report_id: str) -> Optional[ScheduledReportResponse]:
        """Get a specific scheduled report."""
        sql = sa_text("""
            SELECT * FROM scheduled_reports WHERE report_id = :rid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"rid": report_id, "tid": self.tenant_id})
        row = result.fetchone()
        return self._row_to_schedule_response(row) if row else None

    async def update_schedule(self, report_id: str, update: ScheduledReportUpdate) -> Optional[ScheduledReportResponse]:
        """Update a scheduled report configuration."""
        existing = await self.get_schedule(report_id)
        if not existing:
            return None

        now = datetime.now(timezone.utc)
        updates: list[str] = []
        params: dict = {"rid": report_id, "tid": self.tenant_id, "now": now}

        for field, value in update.model_dump(exclude_none=True).items():
            col = field
            if field == "frequency":
                col = "frequency"
                value = value.value if hasattr(value, 'value') else value
            elif field == "day_of_week":
                col = "day_of_week"
                value = value.value if hasattr(value, 'value') else value
            elif field == "digest_style":
                col = "digest_style"
                value = value.value if hasattr(value, 'value') else value
            elif field == "day_of_month":
                col = "day_of_month"

            updates.append(f"{col} = :{col}")
            params[col] = value

        if updates:
            updates.append("updated_at = :now")
            # Recompute next scheduled run if frequency-related fields changed
            freq = update.frequency or existing.frequency
            dow = update.day_of_week or existing.day_of_week
            dom = update.day_of_month or existing.day_of_month
            tod = update.time_of_day or existing.time_of_day
            params["next_scheduled"] = self._compute_next_run(freq, dow, dom, tod)
            updates.append("next_scheduled_at = :next_scheduled")

            set_clause = ", ".join(updates)
            sql = sa_text(f"""
                UPDATE scheduled_reports SET {set_clause}
                WHERE report_id = :rid AND tenant_id = :tid
                RETURNING report_id, name, description, frequency, day_of_week, day_of_month,
                    time_of_day, digest_style, period_days, recipients, include_trends,
                    include_recommendations, is_active, channels, last_generated_at,
                    next_scheduled_at, total_generations, created_by, created_at, updated_at
            """)
            result = await self.session.execute(sql, params)
            await self.session.commit()
            row = result.fetchone()
            return self._row_to_schedule_response(row) if row else None

        return existing

    async def delete_schedule(self, report_id: str) -> bool:
        """Delete a scheduled report."""
        sql = sa_text("""
            DELETE FROM scheduled_reports WHERE report_id = :rid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"rid": report_id, "tid": self.tenant_id})
        await self.session.commit()
        return result.rowcount > 0

    async def get_due_reports(self) -> list[ScheduledReportResponse]:
        """Get all reports that are due for generation now."""
        sql = sa_text("""
            SELECT * FROM scheduled_reports
            WHERE tenant_id = :tid AND is_active = TRUE
              AND next_scheduled_at <= NOW()
            ORDER BY next_scheduled_at ASC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [self._row_to_schedule_response(r) for r in result.fetchall()]

    async def record_generation(self, report_id: str) -> None:
        """Record that a report was generated and update the next scheduled time."""
        now = datetime.now(timezone.utc)
        schedule = await self.get_schedule(report_id)
        if not schedule:
            return

        next_run = self._compute_next_run(
            schedule.frequency,
            schedule.day_of_week,
            schedule.day_of_month,
            schedule.time_of_day,
        )

        sql = sa_text("""
            UPDATE scheduled_reports
            SET last_generated_at = :now, next_scheduled_at = :next,
                total_generations = total_generations + 1, updated_at = :now
            WHERE report_id = :rid AND tenant_id = :tid
        """)
        await self.session.execute(sql, {
            "rid": report_id,
            "tid": self.tenant_id,
            "now": now,
            "next": next_run,
        })
        await self.session.commit()

    def _compute_next_run(
        self,
        frequency: ReportFrequency | str,
        day_of_week: Optional[ReportDay | str] = None,
        day_of_month: Optional[int] = None,
        time_of_day: str = "08:00",
    ) -> datetime:
        """Compute the next scheduled run time."""
        now = datetime.now(timezone.utc)
        freq_str = frequency.value if hasattr(frequency, 'value') else str(frequency)
        hour, minute = map(int, time_of_day.split(":"))

        if freq_str == "daily":
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run

        if freq_str in ("weekly", "biweekly"):
            dow_str = day_of_week.value if hasattr(day_of_week, 'value') else str(day_of_week) if day_of_week else "monday"
            day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
            target_dow = day_map.get(dow_str, 0)
            days_ahead = (target_dow - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # next week
            next_run = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
            return next_run

        if freq_str == "monthly":
            dom = day_of_month or 1
            next_run = now.replace(day=min(dom, 28), hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)
            return next_run

        if freq_str == "quarterly":
            dom = day_of_month or 1
            current_quarter = (now.month - 1) // 3
            next_quarter_start = (current_quarter + 1) * 3 + 1
            if next_quarter_start > 12:
                next_run = now.replace(year=now.year + 1, month=1, day=min(dom, 28), hour=hour, minute=minute, second=0, microsecond=0)
            else:
                next_run = now.replace(month=next_quarter_start, day=min(dom, 28), hour=hour, minute=minute, second=0, microsecond=0)
            return next_run

        # Default: daily
        return (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _row_to_schedule_response(self, row) -> ScheduledReportResponse:
        return ScheduledReportResponse(
            report_id=str(row.report_id),
            name=row.name,
            description=row.description,
            frequency=row.frequency,
            day_of_week=row.day_of_week,
            day_of_month=row.day_of_month,
            time_of_day=row.time_of_day,
            digest_style=row.digest_style,
            period_days=row.period_days,
            recipients=row.recipients or [],
            include_trends=row.include_trends,
            include_recommendations=row.include_recommendations,
            is_active=row.is_active,
            channels=row.channels or [],
            last_generated_at=row.last_generated_at,
            next_scheduled_at=row.next_scheduled_at,
            total_generations=row.total_generations or 0,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


# Module-level in-memory cache for anomaly deduplication.
# Keyed by tenant_id -> signature -> {current_value, last_seen}.
# An anomaly is re-emitted only if its current_value changes by >20%.
_anomaly_cache: dict[str, dict[str, dict]] = {}


@dataclass
class AnomalyDetector:
    """Detects anomalies in tenant metrics.

    Uses an in-memory cache to avoid re-emitting the same anomaly
    on every poll cycle. An anomaly is re-emitted only if its
    current_value changes by more than 20% from the last emission.
    """

    session: AsyncSession
    tenant_id: str

    def _should_emit(self, signature: str, current_value: float) -> bool:
        """Check if an anomaly should be emitted (dedup logic).

        Returns True if:
        - No previous emission for this signature, OR
        - current_value changed by >20% from last emission
        """
        tenant_cache = _anomaly_cache.setdefault(self.tenant_id, {})
        last = tenant_cache.get(signature)
        if last is None:
            tenant_cache[signature] = {"current_value": current_value, "last_seen": datetime.now(timezone.utc)}
            return True
        # Re-emit only if value changed significantly
        old_val = abs(last["current_value"])
        new_val = abs(current_value)
        if old_val > 0 and new_val > 0:
            change_pct = abs(new_val - old_val) / max(old_val, 0.01)
            if change_pct < 0.2:
                return False
        tenant_cache[signature] = {"current_value": current_value, "last_seen": datetime.now(timezone.utc)}
        return True

    async def detect_anomalies(self, lookback_hours: int = 24) -> AnomalyDetectionResult:
        """Detect anomalies across tenant metrics."""
        now = datetime.now(timezone.utc)
        anomalies: list[AnomalyItem] = []

        # 1. SLA breach anomalies
        sla_anomalies = await self._detect_sla_anomalies(lookback_hours)
        anomalies.extend(sla_anomalies)

        # 2. Volume anomalies
        vol_anomalies = await self._detect_volume_anomalies(lookback_hours)
        anomalies.extend(vol_anomalies)

        # 3. Risk anomalies
        risk_anomalies = await self._detect_risk_anomalies(lookback_hours)
        anomalies.extend(risk_anomalies)

        # 4. Performance anomalies
        perf_anomalies = await self._detect_performance_anomalies(lookback_hours)
        anomalies.extend(perf_anomalies)

        critical = sum(1 for a in anomalies if a.severity == AnomalySeverity.CRITICAL)
        high = sum(1 for a in anomalies if a.severity == AnomalySeverity.HIGH)

        return AnomalyDetectionResult(
            anomalies=anomalies,
            total_anomalies=len(anomalies),
            critical_count=critical,
            high_count=high,
            period=f"last_{lookback_hours}h",
            generated_at=now,
        )

    async def _detect_sla_anomalies(self, lookback_hours: int) -> list[AnomalyItem]:
        """Detect SLA-related anomalies."""
        anomalies: list[AnomalyItem] = []

        # Check for sudden increase in SLA breaches
        recent = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS breaches FROM contract_reviews
                WHERE tenant_id = :tid AND sla_breached = TRUE
                  AND updated_at > NOW() - CAST(:lookback AS interval)
            """),
            {"tid": self.tenant_id, "lookback": timedelta(hours=lookback_hours)},
        )
        recent_breaches = recent.scalar() or 0

        # Compare to previous period
        previous = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS breaches FROM contract_reviews
                WHERE tenant_id = :tid AND sla_breached = TRUE
                  AND updated_at > NOW() - CAST(:lookback AS interval)
                  AND updated_at <= NOW() - CAST(:lookback_half AS interval)
            """),
            {
                "tid": self.tenant_id,
                "lookback": timedelta(hours=lookback_hours * 2),
                "lookback_half": timedelta(hours=lookback_hours),
            },
        )
        prev_breaches = previous.scalar() or 0

        if recent_breaches > prev_breaches * 1.5 and prev_breaches > 0:
            signature = f"sla_breach_spike::{self.tenant_id}"
            if self._should_emit(signature, recent_breaches):
                anomalies.append(AnomalyItem(
                    anomaly_id=uuid.uuid4().hex[:12],
                    category=AnomalyCategory.SLA,
                    severity=AnomalySeverity.HIGH if recent_breaches > prev_breaches * 2 else AnomalySeverity.MEDIUM,
                    title="SLA breach spike detected",
                    description=f"SLA breaches increased from {prev_breaches} to {recent_breaches}",
                    metric_name="sla_breaches",
                    current_value=recent_breaches,
                    expected_value=prev_breaches,
                    deviation_pct=round((recent_breaches - prev_breaches) / prev_breaches * 100, 1),
                    trend_direction="increasing",
                    affected_area="review_workflow",
                    recommendation="Review reviewer capacity and redistribute workload",
                    detected_at=datetime.now(timezone.utc),
                ))

        return anomalies

    async def _detect_volume_anomalies(self, lookback_hours: int) -> list[AnomalyItem]:
        """Detect volume-related anomalies."""
        anomalies: list[AnomalyItem] = []

        # Check for sudden drop in review completions (completed_at, not invalid status enum)
        recent = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS completed FROM contract_reviews
                WHERE tenant_id = :tid AND completed_at IS NOT NULL
                  AND updated_at > NOW() - CAST(:lookback AS interval)
            """),
            {"tid": self.tenant_id, "lookback": timedelta(hours=lookback_hours)},
        )
        recent_completed = recent.scalar() or 0

        previous = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS completed FROM contract_reviews
                WHERE tenant_id = :tid AND completed_at IS NOT NULL
                  AND updated_at > NOW() - CAST(:lookback AS interval)
                  AND updated_at <= NOW() - CAST(:lookback_half AS interval)
            """),
            {
                "tid": self.tenant_id,
                "lookback": timedelta(hours=lookback_hours * 2),
                "lookback_half": timedelta(hours=lookback_hours),
            },
        )
        prev_completed = previous.scalar() or 0

        if recent_completed < prev_completed * 0.5 and prev_completed > 3:
            signature = f"completion_rate_drop::{self.tenant_id}"
            if self._should_emit(signature, recent_completed):
                anomalies.append(AnomalyItem(
                    anomaly_id=uuid.uuid4().hex[:12],
                    category=AnomalyCategory.VOLUME,
                    severity=AnomalySeverity.HIGH,
                    title="Review completion rate drop",
                    description=f"Completed reviews dropped from {prev_completed} to {recent_completed}",
                    metric_name="reviews_completed",
                    current_value=recent_completed,
                    expected_value=prev_completed,
                    deviation_pct=round((prev_completed - recent_completed) / prev_completed * 100, 1),
                    trend_direction="decreasing",
                    affected_area="review_workflow",
                    recommendation="Investigate potential bottlenecks in review pipeline",
                    detected_at=datetime.now(timezone.utc),
                ))

        return anomalies

    async def _detect_risk_anomalies(self, lookback_hours: int) -> list[AnomalyItem]:
        """Detect risk-related anomalies."""
        anomalies: list[AnomalyItem] = []

        # Check for sudden increase in high-severity findings
        recent = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS critical FROM review_findings
                WHERE tenant_id = :tid AND severity IN ('critical', 'high')
                  AND created_at > NOW() - CAST(:lookback AS interval)
            """),
            {"tid": self.tenant_id, "lookback": timedelta(hours=lookback_hours)},
        )
        recent_critical = recent.scalar() or 0

        previous = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS critical FROM review_findings
                WHERE tenant_id = :tid AND severity IN ('critical', 'high')
                  AND created_at > NOW() - CAST(:lookback AS interval)
                  AND created_at <= NOW() - CAST(:lookback_half AS interval)
            """),
            {
                "tid": self.tenant_id,
                "lookback": timedelta(hours=lookback_hours * 2),
                "lookback_half": timedelta(hours=lookback_hours),
            },
        )
        prev_critical = previous.scalar() or 0

        if recent_critical > prev_critical * 1.5 and prev_critical > 2:
            signature = f"finding_spike::{self.tenant_id}"
            if self._should_emit(signature, recent_critical):
                anomalies.append(AnomalyItem(
                    anomaly_id=uuid.uuid4().hex[:12],
                    category=AnomalyCategory.RISK,
                    severity=AnomalySeverity.CRITICAL if recent_critical > prev_critical * 2 else AnomalySeverity.HIGH,
                    title="High-severity finding spike",
                    description=f"Critical/high findings increased from {prev_critical} to {recent_critical}",
                    metric_name="critical_findings",
                    current_value=recent_critical,
                    expected_value=prev_critical,
                    deviation_pct=round((recent_critical - prev_critical) / prev_critical * 100, 1),
                    trend_direction="increasing",
                    affected_area="contract_risk",
                    recommendation="Review recent contracts for systemic risk patterns",
                    detected_at=datetime.now(timezone.utc),
                ))

        return anomalies

    async def _detect_performance_anomalies(self, lookback_hours: int) -> list[AnomalyItem]:
        """Detect performance-related anomalies."""
        anomalies: list[AnomalyItem] = []

        # Check for AI latency spikes
        recent = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG(latency_ms), 0)::float AS avg_latency
                FROM ai_execution_runs
                WHERE tenant_id = :tid AND status = 'completed'
                  AND created_at > NOW() - CAST(:lookback AS interval)
            """),
            {"tid": self.tenant_id, "lookback": timedelta(hours=lookback_hours)},
        )
        recent_latency = recent.scalar() or 0.0

        previous = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG(latency_ms), 0)::float AS avg_latency
                FROM ai_execution_runs
                WHERE tenant_id = :tid AND status = 'completed'
                  AND created_at > NOW() - CAST(:lookback AS interval)
                  AND created_at <= NOW() - CAST(:lookback_half AS interval)
            """),
            {
                "tid": self.tenant_id,
                "lookback": timedelta(hours=lookback_hours * 2),
                "lookback_half": timedelta(hours=lookback_hours),
            },
        )
        prev_latency = previous.scalar() or 0.0

        if recent_latency > prev_latency * 1.5 and prev_latency > 100:
            signature = f"ai_latency_spike::{self.tenant_id}"
            if self._should_emit(signature, recent_latency):
                anomalies.append(AnomalyItem(
                    anomaly_id=uuid.uuid4().hex[:12],
                    category=AnomalyCategory.PERFORMANCE,
                    severity=AnomalySeverity.MEDIUM,
                    title="AI latency increase detected",
                    description=f"Average AI latency increased from {prev_latency:.0f}ms to {recent_latency:.0f}ms",
                    metric_name="ai_latency_ms",
                    current_value=round(recent_latency, 1),
                    expected_value=round(prev_latency, 1),
                    deviation_pct=round((recent_latency - prev_latency) / prev_latency * 100, 1),
                    trend_direction="increasing",
                    affected_area="ai_pipeline",
                    recommendation="Check AI provider status and queue depth",
                    detected_at=datetime.now(timezone.utc),
                ))

        return anomalies


@dataclass
class NarrativeGenerator:
    """Generates natural-language trend narratives from analytics data."""

    session: AsyncSession
    tenant_id: str

    async def generate_narratives(self, period_days: int = 30) -> TrendNarrativeSet:
        """Generate trend narratives from analytics data."""
        narratives: list[TrendNarrative] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Cycle time trend
        ct_narrative = await self._generate_cycle_time_narrative(cutoff)
        if ct_narrative:
            narratives.append(ct_narrative)

        # Volume trend
        vol_narrative = await self._generate_volume_narrative(cutoff)
        if vol_narrative:
            narratives.append(vol_narrative)

        # Risk trend
        risk_narrative = await self._generate_risk_narrative(cutoff)
        if risk_narrative:
            narratives.append(risk_narrative)

        # SLA trend
        sla_narrative = await self._generate_sla_narrative(cutoff)
        if sla_narrative:
            narratives.append(sla_narrative)

        positive = sum(1 for n in narratives if n.direction == "improving")
        negative = sum(1 for n in narratives if n.direction == "worsening")

        return TrendNarrativeSet(
            narratives=narratives,
            total_narratives=len(narratives),
            positive_trends=positive,
            negative_trends=negative,
            period=f"last_{period_days}_days",
        )

    async def _generate_cycle_time_narrative(self, cutoff: datetime) -> Optional[TrendNarrative]:
        """Generate narrative about cycle time trends."""
        current = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400), 0)::float AS avg_days
                FROM contract_reviews
                WHERE tenant_id = :tid AND completed_at IS NOT NULL AND created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        current_avg = current.scalar() or 0.0

        older_cutoff = cutoff - timedelta(days=30)
        previous = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400), 0)::float AS avg_days
                FROM contract_reviews
                WHERE tenant_id = :tid AND completed_at IS NOT NULL
                  AND created_at >= :older AND created_at < :cutoff
            """),
            {"tid": self.tenant_id, "older": older_cutoff, "cutoff": cutoff},
        )
        prev_avg = previous.scalar() or 0.0

        if prev_avg == 0:
            return None

        change_pct = round((current_avg - prev_avg) / prev_avg * 100, 1)
        direction = "improving" if current_avg < prev_avg else "worsening" if current_avg > prev_avg else "stable"

        return TrendNarrative(
            narrative_id=uuid.uuid4().hex[:12],
            title="Contract Review Cycle Time",
            summary=f"Average review cycle time is {current_avg:.1f} days, "
                    f"{'decreased' if direction == 'improving' else 'increased' if direction == 'worsening' else 'stable'} "
                    f"by {abs(change_pct):.0f}% compared to previous period",
            metric="cycle_time_days",
            direction=direction,
            change_pct=change_pct,
            period="last_30_days",
            supporting_data={"current_avg": current_avg, "previous_avg": prev_avg},
        )

    async def _generate_volume_narrative(self, cutoff: datetime) -> Optional[TrendNarrative]:
        """Generate narrative about contract volume trends."""
        current = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        current_count = current.scalar() or 0

        older_cutoff = cutoff - timedelta(days=30)
        previous = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND created_at >= :older AND created_at < :cutoff
            """),
            {"tid": self.tenant_id, "older": older_cutoff, "cutoff": cutoff},
        )
        prev_count = previous.scalar() or 0

        if prev_count == 0:
            return None

        change_pct = round((current_count - prev_count) / prev_count * 100, 1)
        direction = "improving" if current_count > prev_count else "worsening" if current_count < prev_count else "stable"

        return TrendNarrative(
            narrative_id=uuid.uuid4().hex[:12],
            title="Contract Review Volume",
            summary=f"Review volume is {current_count} contracts, "
                    f"{'up' if direction == 'improving' else 'down' if direction == 'worsening' else 'stable'} "
                    f"{abs(change_pct):.0f}% from previous period",
            metric="review_volume",
            direction=direction,
            change_pct=change_pct,
            period="last_30_days",
            supporting_data={"current_count": current_count, "previous_count": prev_count},
        )

    async def _generate_risk_narrative(self, cutoff: datetime) -> Optional[TrendNarrative]:
        """Generate narrative about risk score trends."""
        current = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG((metadata->>'risk_score')::numeric), 0)::float
                FROM contract_reviews
                WHERE tenant_id = :tid AND metadata->>'risk_score' IS NOT NULL AND created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        current_avg = current.scalar() or 0.0

        older_cutoff = cutoff - timedelta(days=30)
        previous = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG((metadata->>'risk_score')::numeric), 0)::float
                FROM contract_reviews
                WHERE tenant_id = :tid AND metadata->>'risk_score' IS NOT NULL
                  AND created_at >= :older AND created_at < :cutoff
            """),
            {"tid": self.tenant_id, "older": older_cutoff, "cutoff": cutoff},
        )
        prev_avg = previous.scalar() or 0.0

        if prev_avg == 0:
            return None

        change_pct = round((current_avg - prev_avg) / prev_avg * 100, 1)
        direction = "improving" if current_avg < prev_avg else "worsening" if current_avg > prev_avg else "stable"

        return TrendNarrative(
            narrative_id=uuid.uuid4().hex[:12],
            title="Portfolio Risk Score",
            summary=f"Average portfolio risk score is {current_avg:.2f}, "
                    f"{'decreased' if direction == 'improving' else 'increased' if direction == 'worsening' else 'stable'} "
                    f"by {abs(change_pct):.0f}% compared to previous period",
            metric="avg_risk_score",
            direction=direction,
            change_pct=change_pct,
            period="last_30_days",
            supporting_data={"current_avg": current_avg, "previous_avg": prev_avg},
        )

    async def _generate_sla_narrative(self, cutoff: datetime) -> Optional[TrendNarrative]:
        """Generate narrative about SLA compliance trends."""
        current = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE sla_breached = TRUE)::int AS breached
                FROM contract_reviews
                WHERE tenant_id = :tid AND created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        row = current.fetchone()
        current_total = row.total if row else 0
        current_breached = row.breached if row else 0
        current_rate = ((current_total - current_breached) / current_total * 100) if current_total > 0 else 100.0

        older_cutoff = cutoff - timedelta(days=30)
        previous = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE sla_breached = TRUE)::int AS breached
                FROM contract_reviews
                WHERE tenant_id = :tid AND created_at >= :older AND created_at < :cutoff
            """),
            {"tid": self.tenant_id, "older": older_cutoff, "cutoff": cutoff},
        )
        prev_row = previous.fetchone()
        prev_total = prev_row.total if prev_row else 0
        prev_breached = prev_row.breached if prev_row else 0
        prev_rate = ((prev_total - prev_breached) / prev_total * 100) if prev_total > 0 else 100.0

        if prev_total == 0:
            return None

        change_pct = round(current_rate - prev_rate, 1)
        direction = "improving" if current_rate > prev_rate else "worsening" if current_rate < prev_rate else "stable"

        return TrendNarrative(
            narrative_id=uuid.uuid4().hex[:12],
            title="SLA Compliance Rate",
            summary=f"SLA compliance is {current_rate:.0f}%, "
                    f"{'up' if direction == 'improving' else 'down' if direction == 'worsening' else 'stable'} "
                    f"{abs(change_pct):.1f} percentage points from previous period",
            metric="sla_compliance_rate",
            direction=direction,
            change_pct=change_pct,
            period="last_30_days",
            supporting_data={"current_rate": current_rate, "previous_rate": prev_rate},
        )


@dataclass
class DigestGenerator:
    """Generates executive digests — the daily/weekly briefing."""

    session: AsyncSession
    tenant_id: str

    async def generate_digest(
        self,
        style: DigestStyle = DigestStyle.STANDARD,
        period_days: int = 7,
    ) -> ExecutiveDigest:
        """Generate an executive digest."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=period_days)

        # Portfolio snapshot
        snapshot = await self._build_portfolio_snapshot(cutoff)

        # Key metrics
        metrics = await self._build_key_metrics(cutoff)

        # Anomalies
        detector = AnomalyDetector(self.session, self.tenant_id)
        anomaly_result = await detector.detect_anomalies(lookback_hours=period_days * 24)

        # Narratives
        narrator = NarrativeGenerator(self.session, self.tenant_id)
        narrative_set = await narrator.generate_narratives(period_days=period_days)

        # Top recommendations
        recommendations: list[str] = []
        if snapshot.at_risk_count > 3:
            recommendations.append(f"Address {snapshot.at_risk_count} at-risk reviews approaching SLA deadlines")
        if anomaly_result.critical_count > 0:
            recommendations.append(f"Investigate {anomaly_result.critical_count} critical anomalies detected")

        # Critical alerts
        critical_alerts = [
            a.title for a in anomaly_result.anomalies
            if a.severity in (AnomalySeverity.CRITICAL, AnomalySeverity.HIGH)
        ]

        return ExecutiveDigest(
            digest_id=uuid.uuid4().hex[:12],
            title=f"Executive Briefing — {now.strftime('%A, %B %d, %Y')}",
            style=style,
            generated_at=now,
            period=f"last_{period_days}_days",
            portfolio_snapshot=snapshot,
            key_metrics=metrics,
            anomalies=anomaly_result.anomalies[:5],  # Top 5 anomalies
            narratives=narrative_set.narratives,
            top_recommendations=recommendations[:3],
            critical_alerts=critical_alerts[:5],
            full_report_available=style != DigestStyle.BRIEF,
        )

    async def _build_portfolio_snapshot(self, cutoff: datetime) -> PortfolioSnapshot:
        """Build a quick portfolio snapshot."""
        total = await self.session.execute(
            sa_text("SELECT COUNT(*)::int FROM contract_reviews WHERE tenant_id = :tid AND is_deleted = FALSE"),
            {"tid": self.tenant_id},
        )
        total_contracts = total.scalar() or 0

        active = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND is_deleted = FALSE
                  AND status IN ('draft', 'ai_analyzed', 'in_review', 'pending_approval')
            """),
            {"tid": self.tenant_id},
        )
        active_reviews = active.scalar() or 0

        critical = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND is_deleted = FALSE
                  AND (metadata->>'risk_score')::numeric >= 0.7
            """),
            {"tid": self.tenant_id},
        )
        critical_count = critical.scalar() or 0

        avg_risk = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG((metadata->>'risk_score')::numeric), 0)::float
                FROM contract_reviews WHERE tenant_id = :tid AND metadata->>'risk_score' IS NOT NULL
            """),
            {"tid": self.tenant_id},
        )
        avg_risk_score = round(avg_risk.scalar() or 0, 2)

        sla = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND sla_breached = TRUE
            """),
            {"tid": self.tenant_id},
        )
        sla_breaches = sla.scalar() or 0

        at_risk = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND is_deleted = FALSE
                  AND status IN ('draft', 'ai_analyzed', 'in_review')
                  AND sla_deadline IS NOT NULL AND sla_deadline < NOW() + INTERVAL '24 hours'
            """),
            {"tid": self.tenant_id},
        )
        at_risk_count = at_risk.scalar() or 0

        new_today = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND created_at >= CURRENT_DATE
            """),
            {"tid": self.tenant_id},
        )
        new_today_count = new_today.scalar() or 0

        completed_today = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int FROM contract_reviews
                WHERE tenant_id = :tid AND completed_at >= CURRENT_DATE
            """),
            {"tid": self.tenant_id},
        )
        completed_today_count = completed_today.scalar() or 0

        return PortfolioSnapshot(
            total_contracts=total_contracts,
            active_reviews=active_reviews,
            critical_contracts=critical_count,
            avg_risk_score=avg_risk_score,
            sla_breaches=sla_breaches,
            at_risk_count=at_risk_count,
            new_contracts_today=new_today_count,
            completed_reviews_today=completed_today_count,
        )

    async def _build_key_metrics(self, cutoff: datetime) -> KeyMetricsSummary:
        """Build key metrics summary."""
        # Cycle time
        ct = await self.session.execute(
            sa_text("""
                SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 86400), 0)::float
                FROM contract_reviews
                WHERE tenant_id = :tid AND completed_at IS NOT NULL AND created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        cycle_time = round(ct.scalar() or 0, 1)

        # AI accuracy (approximated by success rate)
        ai = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE status = 'completed')::int AS success
                FROM ai_execution_runs
                WHERE tenant_id = :tid AND created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        ai_row = ai.fetchone()
        ai_accuracy = round((ai_row.success / ai_row.total * 100) if ai_row and ai_row.total > 0 else 0, 1)

        # SLA compliance
        sla = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE sla_breached = FALSE OR sla_breached IS NULL)::int AS compliant
                FROM contract_reviews
                WHERE tenant_id = :tid AND created_at >= :cutoff
            """),
            {"tid": self.tenant_id, "cutoff": cutoff},
        )
        sla_row = sla.fetchone()
        sla_compliance = round((sla_row.compliant / sla_row.total * 100) if sla_row and sla_row.total > 0 else 100, 1)

        return KeyMetricsSummary(
            cycle_time_avg_days=cycle_time,
            ai_accuracy=ai_accuracy,
            sla_compliance_rate=sla_compliance,
            portfolio_exposure=0.0,
            cost_per_review=0.0,
            reviewer_throughput=0.0,
            negotiation_success_rate=0.0,
        )
