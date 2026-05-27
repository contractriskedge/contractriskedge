"""SLA Prediction Engine — predictive analytics for workflow intelligence.

Uses historical telemetry to predict:
  - SLA breach probability per review
  - Expected completion time per stage
  - Escalation probability
  - Bottleneck/stall probability
  - Reviewer overload risk

All predictions are computed from existing data (ReviewStatusHistory durations,
reviewer workload, clause complexity, risk scores) — no ML infrastructure needed.

Predictions are consumed by:
  - sla_check.py daemon (enhanced with probability scores)
  - Review routing engine (intelligent assignment)
  - Notification service (predictive warnings before breach)
  - Admin diagnostics dashboard
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func as sa_func, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ── Default Duration Percentiles (fallback when no historical data) ──
# These are reasonable defaults for a contract review platform.
# They are overridden once historical data accumulates.

_DEFAULT_STAGE_DURATIONS_HOURS: dict[str, dict[str, float]] = {
    "draft": {"p50": 2.0, "p75": 6.0, "p95": 24.0},
    "ai_analyzed": {"p50": 0.5, "p75": 1.0, "p95": 4.0},
    "in_review": {"p50": 8.0, "p75": 24.0, "p95": 72.0},
    "pending_approval": {"p50": 4.0, "p75": 12.0, "p95": 48.0},
}

# ── Risk Weights for SLA Breach Probability ──

_RISK_WEIGHTS = {
    "critical": 1.5,
    "high": 1.2,
    "medium": 1.0,
    "low": 0.7,
}

_PRIORITY_WEIGHTS = {
    "urgent": 2.0,
    "high": 1.5,
    "normal": 1.0,
    "low": 0.6,
}


# ── Prediction Models ────────────────────────────────────────────


@dataclass
class SLAViolationRisk:
    """Predicted SLA breach risk for a single review."""
    review_id: str
    probability: float  # 0.0 to 1.0
    expected_remaining_hours: float
    sla_remaining_hours: float
    risk_factors: list[str] = field(default_factory=list)
    recommended_action: str = ""


@dataclass
class StageDurationPrediction:
    """Predicted duration for a workflow stage."""
    stage: str
    p50_hours: float
    p75_hours: float
    p95_hours: float
    sample_count: int = 0


@dataclass
class EscalationRisk:
    """Predicted escalation risk for a review."""
    review_id: str
    probability: float
    expected_escalation_level: int
    risk_factors: list[str] = field(default_factory=list)


@dataclass
class BottleneckPrediction:
    """Predicted workflow bottleneck."""
    resource_type: str  # 'review', 'reviewer', 'queue'
    resource_id: str
    probability: float
    expected_delay_hours: float
    contributing_factors: list[str] = field(default_factory=list)


@dataclass
class ReviewerWorkloadRisk:
    """Predicted overload risk for a reviewer."""
    reviewer_id: str
    active_review_count: int
    max_capacity: int
    overload_probability: float
    avg_completion_hours: float
    predicted_backlog_hours: float


# ── Prediction Engine ────────────────────────────────────────────


class PredictionEngine:
    """Core prediction engine for workflow intelligence.

    All predictions are computed from existing database telemetry.
    No external ML infrastructure required.

    Usage:
        engine = PredictionEngine(session, tenant_id)
        risk = await engine.predict_sla_breach(review_id)
        stages = await engine.get_stage_duration_percentiles()
        routing = await engine.predict_reviewer_workload()
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    # ── Stage Duration Percentiles ───────────────────────────────

    async def get_stage_duration_percentiles(
        self,
        stage: Optional[str] = None,
        days_lookback: int = 90,
    ) -> dict[str, StageDurationPrediction]:
        """Compute P50/P75/P95 duration percentiles for each workflow stage.

        Queries ReviewStatusHistory to find how long each stage actually takes.
        Falls back to reasonable defaults when insufficient data exists.

        Args:
            stage: Optional stage name to filter (e.g. 'in_review').
            days_lookback: How many days of history to consider.

        Returns:
            Dict mapping stage name → StageDurationPrediction.
        """
        from app.domains.review.models import ReviewStatusHistory

        cutoff = datetime.now(timezone.utc) - timedelta(days=days_lookback)

        # Get all status transitions within the lookback window
        query = select(
            ReviewStatusHistory.from_status,
            ReviewStatusHistory.to_status,
            ReviewStatusHistory.created_at,
            ReviewStatusHistory.review_id,
        ).where(
            ReviewStatusHistory.tenant_id == self.tenant_id,
            ReviewStatusHistory.created_at >= cutoff,
        ).order_by(ReviewStatusHistory.review_id, ReviewStatusHistory.created_at)

        if stage:
            query = query.where(ReviewStatusHistory.from_status == stage)

        result = await self.session.execute(query)
        rows = result.fetchall()

        # Group transitions by review_id to compute stage durations
        review_transitions: dict[str, list[tuple[str, str, datetime]]] = {}
        for row in rows:
            rid = str(row.review_id)
            if rid not in review_transitions:
                review_transitions[rid] = []
            review_transitions[rid].append(
                (row.from_status, row.to_status, row.created_at)
            )

        # Compute durations per stage
        stage_durations: dict[str, list[float]] = {}
        for rid, transitions in review_transitions.items():
            for i in range(len(transitions) - 1):
                from_stage = transitions[i][0]
                to_stage = transitions[i][1]
                start_time = transitions[i][2]
                end_time = transitions[i + 1][2]

                duration_hours = (end_time - start_time).total_seconds() / 3600
                if duration_hours < 0 or duration_hours > 720:  # Sanity: < 30 days
                    continue

                if from_stage not in stage_durations:
                    stage_durations[from_stage] = []
                stage_durations[from_stage].append(duration_hours)

        # Compute percentiles
        predictions: dict[str, StageDurationPrediction] = {}
        all_stages = set(stage_durations.keys()) | set(_DEFAULT_STAGE_DURATIONS_HOURS.keys())

        for s in sorted(all_stages):
            durations = stage_durations.get(s, [])
            if len(durations) >= 3:
                predictions[s] = StageDurationPrediction(
                    stage=s,
                    p50_hours=round(statistics.median(durations), 2),
                    p75_hours=round(statistics.quantiles(durations, n=4)[2], 2),
                    p95_hours=round(statistics.quantiles(durations, n=20)[18], 2),
                    sample_count=len(durations),
                )
            else:
                # Fall back to defaults
                defaults = _DEFAULT_STAGE_DURATIONS_HOURS.get(s, {})
                predictions[s] = StageDurationPrediction(
                    stage=s,
                    p50_hours=defaults.get("p50", 4.0),
                    p75_hours=defaults.get("p75", 12.0),
                    p95_hours=defaults.get("p95", 48.0),
                    sample_count=len(durations),
                )

        return predictions

    # ── SLA Breach Probability ───────────────────────────────────

    async def predict_sla_breach(
        self,
        review_id: str,
    ) -> SLAViolationRisk:
        """Predict the probability of SLA breach for a review.

        Combines:
        - Historical stage duration percentiles
        - Current elapsed time in current stage
        - Remaining SLA time
        - Risk score and priority weights
        - Escalation history

        Args:
            review_id: The review to evaluate.

        Returns:
            SLAViolationRisk with probability and contributing factors.
        """
        from app.domains.review.models import ContractReview

        # Get review data
        result = await self.session.execute(
            select(ContractReview).where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == self.tenant_id,
            )
        )
        review = result.scalar_one_or_none()
        if not review:
            return SLAViolationRisk(
                review_id=review_id,
                probability=0.0,
                expected_remaining_hours=0,
                sla_remaining_hours=0,
                risk_factors=["Review not found"],
                recommended_action="N/A",
            )

        now = datetime.now(timezone.utc)
        risk_factors: list[str] = []
        probability = 0.0

        # Factor 1: SLA deadline proximity
        sla_remaining_hours = 0.0
        if review.sla_deadline:
            sla_remaining = (review.sla_deadline - now).total_seconds() / 3600
            sla_remaining_hours = max(0, sla_remaining)

            if sla_remaining <= 0:
                probability += 0.5  # Already past deadline
                risk_factors.append("SLA deadline already passed")
            elif sla_remaining <= 1:
                probability += 0.4
                risk_factors.append("Less than 1 hour to SLA deadline")
            elif sla_remaining <= 4:
                probability += 0.3
                risk_factors.append("Less than 4 hours to SLA deadline")
            elif sla_remaining <= 24:
                probability += 0.15
                risk_factors.append("Less than 24 hours to SLA deadline")
        else:
            risk_factors.append("No SLA deadline set")

        # Factor 2: Current elapsed time vs historical stage duration
        stage_percentiles = await self.get_stage_duration_percentiles(
            stage=review.status
        )
        stage_pred = stage_percentiles.get(review.status)

        if stage_pred and review.updated_at:
            elapsed_hours = (now - review.updated_at).total_seconds() / 3600
            if elapsed_hours > stage_pred.p95_hours:
                probability += 0.3
                risk_factors.append(
                    f"Already past P95 duration for '{review.status}' "
                    f"({elapsed_hours:.1f}h vs {stage_pred.p95_hours:.1f}h expected)"
                )
            elif elapsed_hours > stage_pred.p75_hours:
                probability += 0.2
                risk_factors.append(
                    f"Past P75 duration for '{review.status}' "
                    f"({elapsed_hours:.1f}h vs {stage_pred.p75_hours:.1f}h expected)"
                )
            elif elapsed_hours > stage_pred.p50_hours:
                probability += 0.1
        else:
            elapsed_hours = 0
            if review.updated_at:
                elapsed_hours = (now - review.updated_at).total_seconds() / 3600
            if elapsed_hours > 24:
                probability += 0.15
                risk_factors.append(f"No historical data but {elapsed_hours:.1f}h elapsed")

        # Factor 3: Risk score weight
        risk_level = "medium"
        if hasattr(review, 'risk_score') and review.risk_score:
            if review.risk_score >= 70:
                risk_level = "critical"
            elif review.risk_score >= 50:
                risk_level = "high"
            elif review.risk_score >= 30:
                risk_level = "medium"
            else:
                risk_level = "low"

        risk_weight = _RISK_WEIGHTS.get(risk_level, 1.0)
        if risk_weight > 1.0:
            probability += (risk_weight - 1.0) * 0.2
            risk_factors.append(f"Risk level '{risk_level}' (weight {risk_weight}x)")

        # Factor 4: Priority weight
        priority = getattr(review, 'priority', 'normal') or 'normal'
        priority_weight = _PRIORITY_WEIGHTS.get(priority, 1.0)
        if priority_weight > 1.0:
            probability += (priority_weight - 1.0) * 0.15
            risk_factors.append(f"Priority '{priority}' (weight {priority_weight}x)")

        # Factor 5: Escalation history
        if hasattr(review, 'escalation_count') and review.escalation_count:
            probability += min(review.escalation_count * 0.1, 0.3)
            risk_factors.append(f"{review.escalation_count} previous escalation(s)")

        # Factor 6: Already breached
        if review.sla_breached:
            probability = min(probability + 0.2, 1.0)
            risk_factors.append("SLA already breached")

        # Clamp probability
        probability = min(max(probability, 0.0), 1.0)

        # Expected remaining hours (weighted by stage prediction)
        expected_remaining = stage_pred.p50_hours if stage_pred else 24.0
        if sla_remaining_hours > 0:
            expected_remaining = min(expected_remaining, sla_remaining_hours)

        # Recommended action
        recommended_action = self._recommend_action(
            probability, sla_remaining_hours, risk_level, priority
        )

        return SLAViolationRisk(
            review_id=review_id,
            probability=round(probability, 3),
            expected_remaining_hours=round(expected_remaining, 1),
            sla_remaining_hours=round(sla_remaining_hours, 1),
            risk_factors=risk_factors,
            recommended_action=recommended_action,
        )

    # ── Batch SLA Breach Prediction ──────────────────────────────

    async def predict_batch_sla_breaches(
        self,
        limit: int = 100,
    ) -> list[SLAViolationRisk]:
        """Predict SLA breach probability for all active reviews.

        Used by the SLA check daemon to prioritize which reviews need
        attention and by the dashboard for at-a-glance risk view.

        Args:
            limit: Maximum reviews to evaluate.

        Returns:
            List of SLAViolationRisk sorted by probability descending.
        """
        from app.domains.review.models import ContractReview

        result = await self.session.execute(
            select(ContractReview).where(
                ContractReview.tenant_id == self.tenant_id,
                ContractReview.is_deleted.is_(False),
                ContractReview.status.notin_(["approved", "rejected", "closed"]),
            ).order_by(
                ContractReview.sla_deadline.asc().nullslast()
            ).limit(limit)
        )
        reviews = result.scalars().all()

        predictions = []
        for review in reviews:
            risk = await self.predict_sla_breach(str(review.review_id))
            predictions.append(risk)

        # Sort by probability descending
        predictions.sort(key=lambda r: r.probability, reverse=True)
        return predictions

    # ── Escalation Probability ───────────────────────────────────

    async def predict_escalation_risk(
        self,
        review_id: str,
    ) -> EscalationRisk:
        """Predict the probability that a review will be escalated.

        Factors:
        - Historical escalation rate for similar reviews
        - Current SLA status
        - Risk score
        - Reviewer workload
        - Time in current stage

        Args:
            review_id: The review to evaluate.

        Returns:
            EscalationRisk with probability and expected level.
        """
        from app.domains.review.models import ContractReview, ReviewEscalation

        # Get review
        result = await self.session.execute(
            select(ContractReview).where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == self.tenant_id,
            )
        )
        review = result.scalar_one_or_none()
        if not review:
            return EscalationRisk(
                review_id=review_id, probability=0.0, expected_escalation_level=0
            )

        risk_factors: list[str] = []
        probability = 0.0

        # Factor 1: Current SLA status
        sla_status = getattr(review, 'sla_status', 'on_track') or 'on_track'
        if sla_status == 'critical_overdue':
            probability += 0.4
            risk_factors.append("Critical SLA overdue")
        elif sla_status == 'overdue':
            probability += 0.25
            risk_factors.append("SLA overdue")

        # Factor 2: Risk score
        risk_score = getattr(review, 'risk_score', 0) or 0
        if risk_score >= 70:
            probability += 0.2
            risk_factors.append(f"High risk score ({risk_score})")
        elif risk_score >= 50:
            probability += 0.1

        # Factor 3: Existing escalation count
        esc_count = getattr(review, 'escalation_count', 0) or 0
        if esc_count > 0:
            probability += min(esc_count * 0.1, 0.3)
            risk_factors.append(f"{esc_count} previous escalation(s)")

        # Factor 4: Historical escalation rate for this tenant
        try:
            count_result = await self.session.execute(
                sa_text("""
                    SELECT
                        COUNT(*)::int AS total,
                        COUNT(*) FILTER (WHERE status != 'resolved')::int AS active
                    FROM review_escalations
                    WHERE tenant_id = :tid
                      AND created_at > NOW() - INTERVAL '30 days'
                """),
                {"tid": self.tenant_id},
            )
            row = count_result.fetchone()
            if row and row.total > 5:
                escalation_rate = row.active / max(row.total, 1)
                if escalation_rate > 0.3:
                    probability += 0.1
                    risk_factors.append(
                        f"Tenant escalation rate {escalation_rate:.0%}"
                    )
        except Exception:
            pass

        # Clamp
        probability = min(max(probability, 0.0), 1.0)

        # Expected escalation level
        expected_level = 1
        if probability > 0.6:
            expected_level = 3
        elif probability > 0.3:
            expected_level = 2

        return EscalationRisk(
            review_id=review_id,
            probability=round(probability, 3),
            expected_escalation_level=expected_level,
            risk_factors=risk_factors,
        )

    # ── Bottleneck Prediction ────────────────────────────────────

    async def predict_bottlenecks(
        self,
    ) -> list[BottleneckPrediction]:
        """Predict workflow bottlenecks before they occur.

        Analyzes:
        - Reviews stuck longer than expected per stage
        - Reviewers approaching capacity
        - Queue depth trends

        Returns:
            List of BottleneckPrediction sorted by probability.
        """
        from app.domains.review.models import ContractReview

        bottlenecks: list[BottleneckPrediction] = []
        now = datetime.now(timezone.utc)

        # Get stage percentiles for comparison
        stage_preds = await self.get_stage_duration_percentiles()

        # Find reviews exceeding P75 for their current stage
        result = await self.session.execute(
            select(ContractReview).where(
                ContractReview.tenant_id == self.tenant_id,
                ContractReview.is_deleted.is_(False),
                ContractReview.status.notin_(["approved", "rejected", "closed"]),
            )
        )
        reviews = result.scalars().all()

        for review in reviews:
            stage = review.status
            pred = stage_preds.get(stage)
            if not pred or not review.updated_at:
                continue

            elapsed = (now - review.updated_at).total_seconds() / 3600

            if elapsed > pred.p95_hours:
                probability = min(elapsed / (pred.p95_hours * 2), 0.95)
                bottlenecks.append(BottleneckPrediction(
                    resource_type="review",
                    resource_id=str(review.review_id),
                    probability=round(probability, 3),
                    expected_delay_hours=round(elapsed - pred.p50_hours, 1),
                    contributing_factors=[
                        f"Elapsed {elapsed:.1f}h vs P95 {pred.p95_hours:.1f}h in '{stage}'",
                    ],
                ))

        # Reviewer workload bottlenecks
        try:
            reviewer_result = await self.session.execute(
                sa_text("""
                    SELECT
                        assigned_to,
                        COUNT(*)::int AS active_count
                    FROM contract_reviews
                    WHERE tenant_id = :tid
                      AND is_deleted = FALSE
                      AND status IN ('in_review', 'pending_approval')
                      AND assigned_to IS NOT NULL
                    GROUP BY assigned_to
                    ORDER BY active_count DESC
                """),
                {"tid": self.tenant_id},
            )
            for row in reviewer_result.fetchall():
                if row.active_count >= 5:
                    bottlenecks.append(BottleneckPrediction(
                        resource_type="reviewer",
                        resource_id=row.assigned_to,
                        probability=min(row.active_count / 10.0, 0.9),
                        expected_delay_hours=row.active_count * 4.0,
                        contributing_factors=[
                            f"{row.active_count} active reviews assigned",
                        ],
                    ))
        except Exception:
            pass

        # Sort by probability descending
        bottlenecks.sort(key=lambda b: b.probability, reverse=True)
        return bottlenecks

    # ── Reviewer Workload Prediction ─────────────────────────────

    async def predict_reviewer_workload(
        self,
    ) -> list[ReviewerWorkloadRisk]:
        """Predict workload risk for all active reviewers.

        Returns:
            List of ReviewerWorkloadRisk sorted by overload probability.
        """
        from app.domains.review.models import ContractReview, ReviewAssignment

        workloads: list[ReviewerWorkloadRisk] = []

        # Get active review counts per reviewer
        result = await self.session.execute(
            sa_text("""
                SELECT
                    assigned_to,
                    COUNT(*)::int AS active_count
                FROM contract_reviews
                WHERE tenant_id = :tid
                  AND is_deleted = FALSE
                  AND status IN ('in_review', 'pending_approval')
                  AND assigned_to IS NOT NULL
                GROUP BY assigned_to
            """),
            {"tid": self.tenant_id},
        )
        reviewer_counts = {row.assigned_to: row.active_count for row in result.fetchall()}

        # Get historical completion times per reviewer
        reviewer_speeds: dict[str, list[float]] = {}
        try:
            speed_result = await self.session.execute(
                sa_text("""
                    SELECT
                        ra.assignee_id,
                        EXTRACT(EPOCH FROM (ra.completed_at - ra.created_at)) / 3600 AS duration_hours
                    FROM review_assignments ra
                    WHERE ra.tenant_id = :tid
                      AND ra.completed_at IS NOT NULL
                      AND ra.created_at > NOW() - INTERVAL '90 days'
                """),
                {"tid": self.tenant_id},
            )
            for row in speed_result.fetchall():
                if row.assignee_id not in reviewer_speeds:
                    reviewer_speeds[row.assignee_id] = []
                if row.duration_hours > 0 and row.duration_hours < 720:
                    reviewer_speeds[row.assignee_id].append(row.duration_hours)
        except Exception:
            pass

        for reviewer_id, active_count in reviewer_counts.items():
            speeds = reviewer_speeds.get(reviewer_id, [])
            avg_speed = statistics.median(speeds) if len(speeds) >= 3 else 24.0
            max_capacity = 10  # Configurable per tenant

            overload_prob = min(active_count / max_capacity, 1.0)
            predicted_backlog = active_count * avg_speed

            workloads.append(ReviewerWorkloadRisk(
                reviewer_id=reviewer_id,
                active_review_count=active_count,
                max_capacity=max_capacity,
                overload_probability=round(overload_prob, 3),
                avg_completion_hours=round(avg_speed, 1),
                predicted_backlog_hours=round(predicted_backlog, 1),
            ))

        workloads.sort(key=lambda w: w.overload_probability, reverse=True)
        return workloads

    # ── Helpers ──────────────────────────────────────────────────

    def _recommend_action(
        self,
        probability: float,
        sla_remaining_hours: float,
        risk_level: str,
        priority: str,
    ) -> str:
        """Generate a recommended action based on prediction factors."""
        if probability >= 0.8:
            return "IMMEDIATE: Escalate to senior reviewer or reassign"
        elif probability >= 0.6:
            return "ALERT: Notify reviewer and manager of approaching SLA breach"
        elif probability >= 0.4:
            return "WARN: Send SLA warning notification to reviewer"
        elif probability >= 0.2:
            return "MONITOR: Check back in {} hours".format(
                max(1, int(sla_remaining_hours / 2))
            )
        else:
            return "OK: On track for SLA compliance"


# ── Factory ──────────────────────────────────────────────────────

def get_prediction_engine(session: AsyncSession, tenant_id: str) -> PredictionEngine:
    """Create a PredictionEngine for the given tenant."""
    return PredictionEngine(session=session, tenant_id=tenant_id)
