"""Workflow Simulation Engine — what-if analysis for policy and routing changes.

Enables enterprise users to simulate the impact of:
  - Approval chain changes ("What if Legal approval is removed?")
  - Threshold adjustments ("What if Procurement threshold changes?")
  - Routing changes ("What if clause X routes to specialist Y?")
  - SLA policy changes ("What if we tighten SLA from 24h to 12h?")

All simulations use historical telemetry to project realistic outcomes.
No actual data is modified — simulations are read-only projections.

Usage:
    simulator = WorkflowSimulator(session, tenant_id)
    result = await simulator.simulate_policy_change(
        removed_approval_role="legal_ops",
    )
    result = await simulator.simulate_threshold_change(
        risk_threshold=50,
        new_routing_role="compliance",
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, func as sa_func, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Simulation Models ────────────────────────────────────────────


@dataclass
class SimulationComparison:
    """Comparison between current and projected metrics."""
    metric: str
    current_value: float
    projected_value: float
    delta_pct: float  # positive = increase, negative = decrease
    explanation: str = ""


@dataclass
class PolicyChangeResult:
    """Result of a policy change simulation."""
    scenario_name: str
    description: str
    comparisons: list[SimulationComparison] = field(default_factory=list)
    affected_reviews_count: int = 0
    projected_avg_turnaround_hours: float = 0.0
    risk_warnings: list[str] = field(default_factory=list)


@dataclass
class ThresholdChangeResult:
    """Result of a threshold change simulation."""
    scenario_name: str
    description: str
    reviews_rerouted: int = 0
    from_role: str = ""
    to_role: str = ""
    projected_sla_impact_hours: float = 0.0
    comparisons: list[SimulationComparison] = field(default_factory=list)
    risk_warnings: list[str] = field(default_factory=list)


@dataclass
class SLAPolicyChangeResult:
    """Result of an SLA policy change simulation."""
    scenario_name: str
    description: str
    reviews_affected: int = 0
    current_on_track: int = 0
    projected_on_track: int = 0
    projected_breaches: int = 0
    comparisons: list[SimulationComparison] = field(default_factory=list)


# ── Simulation Engine ────────────────────────────────────────────


class WorkflowSimulator:
    """Read-only workflow simulation engine for what-if analysis.

    All simulations query historical data and project outcomes
    without modifying any records.

    Usage:
        sim = WorkflowSimulator(session, tenant_id)
        result = await sim.simulate_policy_change(
            removed_approval_role="legal_ops",
        )
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def simulate_policy_change(
        self,
        removed_approval_role: Optional[str] = None,
        added_approval_role: Optional[str] = None,
        changed_escalation_hours: Optional[int] = None,
    ) -> PolicyChangeResult:
        """Simulate the impact of changing approval chain policies.

        Args:
            removed_approval_role: Role to remove from approval chain.
            added_approval_role: Role to add to approval chain.
            changed_escalation_hours: New escalation timeout in hours.

        Returns:
            PolicyChangeResult with projected metrics.
        """
        from app.domains.analytics.prediction import PredictionEngine

        engine = PredictionEngine(self.session, self.tenant_id)
        stage_preds = await engine.get_stage_duration_percentiles()

        comparisons: list[SimulationComparison] = []
        risk_warnings: list[str] = []
        scenario_name = "Policy Change"
        description_parts = []

        # Current baseline
        current_avg_turnaround = stage_preds.get("in_review", stage_preds.get("draft"))
        current_p95 = current_avg_turnaround.p95_hours if current_avg_turnaround else 72.0
        current_p50 = current_avg_turnaround.p50_hours if current_avg_turnaround else 8.0

        if removed_approval_role:
            description_parts.append(f"Remove '{removed_approval_role}' from approval chain")

            # Estimate time saved by removing a step
            removed_stage_duration = stage_preds.get("pending_approval")
            if removed_stage_duration:
                time_saved = removed_stage_duration.p50_hours
                projected_avg = max(1.0, current_avg_turnaround.p50_hours - time_saved)

                comparisons.append(SimulationComparison(
                    metric="Avg turnaround (P50)",
                    current_value=round(current_avg_turnaround.p50_hours, 1),
                    projected_value=round(projected_avg, 1),
                    delta_pct=round((projected_avg - current_avg_turnaround.p50_hours)
                                    / current_avg_turnaround.p50_hours * 100, 1),
                    explanation=f"Removing {removed_approval_role} saves ~{time_saved:.1f}h",
                ))

                # Risk: might miss compliance issues
                risk_warnings.append(
                    f"Removing {removed_approval_role} may reduce compliance oversight. "
                    f"Consider adding automated compliance checks."
                )
            else:
                projected_avg = current_avg_turnaround.p50_hours

        elif added_approval_role:
            description_parts.append(f"Add '{added_approval_role}' to approval chain")

            # Estimate time added by adding a step
            added_duration = stage_preds.get("pending_approval")
            time_added = added_duration.p50_hours if added_duration else 4.0
            projected_avg = current_avg_turnaround.p50_hours + time_added

            comparisons.append(SimulationComparison(
                metric="Avg turnaround (P50)",
                current_value=round(current_avg_turnaround.p50_hours, 1),
                projected_value=round(projected_avg, 1),
                delta_pct=round((projected_avg - current_avg_turnaround.p50_hours)
                                / current_avg_turnaround.p50_hours * 100, 1),
                explanation=f"Adding {added_approval_role} adds ~{time_added:.1f}h",
            ))

            risk_warnings.append(
                f"Adding {added_approval_role} increases avg turnaround by "
                f"{time_added:.1f}h. Ensure SLA targets are adjusted accordingly."
            )
        else:
            projected_avg = current_avg_turnaround.p50_hours

        if changed_escalation_hours:
            description_parts.append(f"Change escalation timeout to {changed_escalation_hours}h")

            # Count reviews that would be affected
            result = await self.session.execute(
                sa_text("""
                    SELECT COUNT(*)::int AS affected
                    FROM contract_reviews
                    WHERE tenant_id = :tid
                      AND is_deleted = FALSE
                      AND status NOT IN ('approved', 'rejected', 'closed')
                      AND (
                          EXTRACT(EPOCH FROM (NOW() - updated_at)) / 3600 > :hours
                      )
                """),
                {"tid": self.tenant_id, "hours": changed_escalation_hours},
            )
            row = result.fetchone()
            affected = row.affected if row else 0

            comparisons.append(SimulationComparison(
                metric="Reviews triggering escalation",
                current_value=0,  # Would need current threshold
                projected_value=float(affected),
                delta_pct=0,
                explanation=f"{affected} reviews would trigger escalation at {changed_escalation_hours}h",
            ))

        # Count affected active reviews
        count_result = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS total
                FROM contract_reviews
                WHERE tenant_id = :tid
                  AND is_deleted = FALSE
                  AND status NOT IN ('approved', 'rejected', 'closed')
            """),
            {"tid": self.tenant_id},
        )
        total_active = count_result.fetchone().total or 0

        return PolicyChangeResult(
            scenario_name=scenario_name,
            description="; ".join(description_parts) or "No changes specified",
            comparisons=comparisons,
            affected_reviews_count=total_active,
            projected_avg_turnaround_hours=round(projected_avg, 1),
            risk_warnings=risk_warnings,
        )

    async def simulate_threshold_change(
        self,
        risk_threshold: int = 50,
        new_routing_role: str = "compliance",
        current_routing_role: str = "reviewer",
    ) -> ThresholdChangeResult:
        """Simulate the impact of changing routing thresholds.

        Example: "What if all reviews with risk score >= 50 go to Compliance?"

        Args:
            risk_threshold: New risk score threshold.
            new_routing_role: Role to route high-risk reviews to.
            current_routing_role: Current routing role for comparison.

        Returns:
            ThresholdChangeResult with projected impact.
        """
        comparisons: list[SimulationComparison] = []
        risk_warnings: list[str] = []

        # Count reviews that would be rerouted
        result = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS rerouted
                FROM contract_reviews
                WHERE tenant_id = :tid
                  AND is_deleted = FALSE
                  AND status NOT IN ('approved', 'rejected', 'closed')
                  AND (risk_score >= :threshold OR risk_score IS NULL)
            """),
            {"tid": self.tenant_id, "threshold": risk_threshold},
        )
        row = result.fetchone()
        rerouted = row.rerouted if row else 0

        # Get current workload for the target role
        workload_result = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS active
                FROM contract_reviews cr
                JOIN admin_users au ON au.user_id = cr.assigned_to
                WHERE cr.tenant_id = :tid
                  AND cr.is_deleted = FALSE
                  AND cr.status IN ('in_review', 'pending_approval')
                  AND au.role = :role
            """),
            {"tid": self.tenant_id, "role": new_routing_role},
        )
        current_workload = workload_result.fetchone().active or 0

        # Estimate SLA impact
        from app.domains.analytics.prediction import PredictionEngine

        engine = PredictionEngine(self.session, self.tenant_id)
        stage_preds = await engine.get_stage_duration_percentiles()
        review_stage_p50 = stage_preds.get("in_review", stage_preds.get("draft"))
        avg_hours = review_stage_p50.p50_hours if review_stage_p50 else 8.0

        # Projected additional workload
        additional_load = rerouted * avg_hours
        sla_impact = additional_load / max(current_workload, 1) * avg_hours

        comparisons.append(SimulationComparison(
            metric="Reviews rerouted",
            current_value=0,
            projected_value=float(rerouted),
            delta_pct=100,
            explanation=f"{rerouted} reviews with risk >= {risk_threshold} would route to {new_routing_role}",
        ))
        comparisons.append(SimulationComparison(
            metric="Additional workload (hours)",
            current_value=0,
            projected_value=round(additional_load, 1),
            delta_pct=100,
            explanation=f"Estimated {additional_load:.1f}h additional work for {new_routing_role}",
        ))
        comparisons.append(SimulationComparison(
            metric="SLA impact per review (hours)",
            current_value=round(avg_hours, 1),
            projected_value=round(avg_hours + sla_impact, 1),
            delta_pct=round(sla_impact / avg_hours * 100, 1),
            explanation=f"SLA may increase by ~{sla_impact:.1f}h due to workload shift",
        ))

        if rerouted > 0:
            risk_warnings.append(
                f"Routing {rerouted} reviews to {new_routing_role} may increase "
                f"their workload by ~{additional_load:.1f}h. Consider adding reviewers "
                f"or adjusting capacity."
            )

        return ThresholdChangeResult(
            scenario_name=f"Threshold Change: Risk >= {risk_threshold}",
            description=f"Route reviews with risk score >= {risk_threshold} to {new_routing_role}",
            reviews_rerouted=rerouted,
            from_role=current_routing_role,
            to_role=new_routing_role,
            projected_sla_impact_hours=round(sla_impact, 1),
            comparisons=comparisons,
            risk_warnings=risk_warnings,
        )

    async def simulate_sla_policy_change(
        self,
        new_sla_hours: int = 24,
        workflow_type: str = "legal_review",
        priority: str = "normal",
    ) -> SLAPolicyChangeResult:
        """Simulate the impact of changing SLA policy targets.

        Example: "What if we tighten SLA from 48h to 24h for normal priority?"

        Args:
            new_sla_hours: Proposed new SLA target in hours.
            workflow_type: Type of workflow affected.
            priority: Priority level affected.

        Returns:
            SLAPolicyChangeResult with projected breach impact.
        """
        comparisons: list[SimulationComparison] = []
        from app.domains.analytics.prediction import PredictionEngine

        engine = PredictionEngine(self.session, self.tenant_id)
        stage_preds = await engine.get_stage_duration_percentiles()

        # Get current SLA policy
        current_sla_hours = 48  # Default fallback
        try:
            from app.domains.notify.models import SLAPolicy

            result = await self.session.execute(
                select(SLAPolicy).where(
                    SLAPolicy.tenant_id == self.tenant_id,
                    SLAPolicy.workflow_type == workflow_type,
                    SLAPolicy.priority == priority,
                )
            )
            policy = result.scalar_one_or_none()
            if policy:
                current_sla_hours = policy.target_minutes / 60
        except Exception:
            pass

        # Count currently active reviews that would be affected
        result = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (
                        WHERE EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600 > :new_sla
                    )::int AS would_be_overdue
                FROM contract_reviews
                WHERE tenant_id = :tid
                  AND is_deleted = FALSE
                  AND status NOT IN ('approved', 'rejected', 'closed')
                  AND (priority = :priority OR :priority = 'normal')
            """),
            {
                "tid": self.tenant_id,
                "new_sla": new_sla_hours,
                "priority": priority,
            },
        )
        row = result.fetchone()
        total_active = row.total if row else 0
        would_be_overdue = row.would_be_overdue if row else 0

        # Current overdue count
        current_overdue_result = await self.session.execute(
            sa_text("""
                SELECT COUNT(*)::int AS overdue
                FROM contract_reviews
                WHERE tenant_id = :tid
                  AND is_deleted = FALSE
                  AND status NOT IN ('approved', 'rejected', 'closed')
                  AND sla_breached = TRUE
            """),
            {"tid": self.tenant_id},
        )
        current_overdue = current_overdue_result.fetchone().overdue or 0

        # Projected P50 completion vs new SLA
        review_stage = stage_preds.get("in_review", stage_preds.get("draft"))
        p50_completion = review_stage.p50_hours if review_stage else 8.0
        p95_completion = review_stage.p95_hours if review_stage else 72.0

        comparisons.append(SimulationComparison(
            metric="SLA target (hours)",
            current_value=float(current_sla_hours),
            projected_value=float(new_sla_hours),
            delta_pct=round((new_sla_hours - current_sla_hours) / current_sla_hours * 100, 1),
            explanation=f"Change from {current_sla_hours}h to {new_sla_hours}h",
        ))
        comparisons.append(SimulationComparison(
            metric="P50 completion vs SLA",
            current_value=round(p50_completion, 1),
            projected_value=round(p50_completion, 1),
            delta_pct=round((p50_completion - new_sla_hours) / new_sla_hours * 100, 1),
            explanation=f"P50 completion ({p50_completion:.1f}h) vs new SLA ({new_sla_hours}h)",
        ))
        comparisons.append(SimulationComparison(
            metric="Reviews exceeding SLA",
            current_value=float(current_overdue),
            projected_value=float(would_be_overdue),
            delta_pct=round(
                (would_be_overdue - current_overdue) / max(current_overdue, 1) * 100, 1
            ),
            explanation=f"{would_be_overdue} reviews would exceed {new_sla_hours}h SLA",
        ))

        risk_warnings = []
        if p50_completion > new_sla_hours:
            risk_warnings.append(
                f"P50 completion ({p50_completion:.1f}h) exceeds proposed SLA ({new_sla_hours}h). "
                f"More than 50% of reviews would miss SLA."
            )
        if would_be_overdue > total_active * 0.3:
            risk_warnings.append(
                f"Over {would_be_overdue}/{total_active} ({would_be_overdue/max(total_active,1)*100:.0f}%) "
                f"active reviews would exceed the proposed SLA."
            )

        return SLAPolicyChangeResult(
            scenario_name=f"SLA Policy: {workflow_type}/{priority} → {new_sla_hours}h",
            description=f"Change SLA target from {current_sla_hours}h to {new_sla_hours}h "
                        f"for {workflow_type}/{priority}",
            reviews_affected=total_active,
            current_on_track=total_active - current_overdue,
            projected_on_track=max(0, total_active - would_be_overdue),
            projected_breaches=would_be_overdue,
            comparisons=comparisons,
        )


# ── Factory ──────────────────────────────────────────────────────

def get_simulator(session: AsyncSession, tenant_id: str) -> WorkflowSimulator:
    """Create a WorkflowSimulator for the given tenant."""
    return WorkflowSimulator(session=session, tenant_id=tenant_id)
