"""Enterprise Digital Twin — simulated enterprise workflows, organizational changes, policy impact modeling, vendor disruption modeling, staffing simulations, regulatory scenario testing.

Unifies all simulation primitives into a comprehensive enterprise digital twin.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TwinSimulationType(str, Enum):
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    ORGANIZATIONAL_CHANGE = "organizational_change"
    POLICY_IMPACT = "policy_impact"
    VENDOR_DISRUPTION = "vendor_disruption"
    STAFFING_CHANGE = "staffing_change"
    REGULATORY_SCENARIO = "regulatory_scenario"
    MERGER_IMPACT = "merger_impact"
    BUDGET_CHANGE = "budget_change"


@dataclass
class DigitalTwinState:
    """Current state of the enterprise digital twin."""
    active_workflows: int = 0
    pending_reviews: int = 0
    reviewer_count: int = 0
    avg_cycle_time_hours: float = 0.0
    sla_compliance_rate: float = 0.0
    vendor_count: int = 0
    active_obligations: int = 0
    overdue_obligations: int = 0
    risk_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class TwinSimulationResult:
    """Result of a digital twin simulation."""
    simulation_type: TwinSimulationType
    scenario_name: str
    baseline: DigitalTwinState
    projected: DigitalTwinState
    delta: dict[str, float] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class EnterpriseDigitalTwin:
    """Enterprise digital twin — unified simulation of the entire operational enterprise.

    Capabilities:
    - Simulated enterprise workflows (what-if on workflow changes)
    - Simulated organizational changes (reorg impact)
    - Policy impact modeling (new policy effects)
    - Vendor disruption modeling (vendor failure scenarios)
    - Staffing simulations (add/remove reviewers)
    - Regulatory scenario testing (regulation change effects)
    - Merger impact analysis (acquiree integration)
    - Budget change modeling (cost reduction effects)
    """

    def simulate_workflow_optimization(self, current_state: DigitalTwinState, changes: dict) -> TwinSimulationResult:
        """Simulate the impact of workflow optimizations."""
        cycle_reduction = changes.get("cycle_time_reduction_pct", 10)
        sla_improvement = changes.get("sla_improvement_pct", 5)

        projected = DigitalTwinState(
            active_workflows=current_state.active_workflows,
            pending_reviews=int(current_state.pending_reviews * (1 - cycle_reduction / 100)),
            reviewer_count=current_state.reviewer_count,
            avg_cycle_time_hours=current_state.avg_cycle_time_hours * (1 - cycle_reduction / 100),
            sla_compliance_rate=min(1.0, current_state.sla_compliance_rate * (1 + sla_improvement / 100)),
            vendor_count=current_state.vendor_count,
            active_obligations=current_state.active_obligations,
            overdue_obligations=int(current_state.overdue_obligations * (1 - cycle_reduction / 200)),
            risk_score=current_state.risk_score * (1 - sla_improvement / 200),
        )

        return TwinSimulationResult(
            simulation_type=TwinSimulationType.WORKFLOW_OPTIMIZATION,
            scenario_name=f"Optimize workflows: -{cycle_reduction}% cycle, +{sla_improvement}% SLA",
            baseline=current_state,
            projected=projected,
            delta={"cycle_hours_saved": current_state.avg_cycle_time_hours - projected.avg_cycle_time_hours,
                   "sla_improvement": projected.sla_compliance_rate - current_state.sla_compliance_rate,
                   "backlog_reduction": current_state.pending_reviews - projected.pending_reviews},
            recommendations=[f"Reduce cycle time by {cycle_reduction}% through parallel reviews",
                             f"Improve SLA compliance by {sla_improvement}% with automated triage"],
            confidence=0.85,
        )

    def simulate_staffing_change(self, current_state: DigitalTwinState, add_reviewers: int = 0, remove_reviewers: int = 0) -> TwinSimulationResult:
        """Simulate the impact of staffing changes."""
        new_count = current_state.reviewer_count + add_reviewers - remove_reviewers
        if new_count <= 0:
            return TwinSimulationResult(
                simulation_type=TwinSimulationType.STAFFING_CHANGE,
                scenario_name="Staffing reduction to zero",
                baseline=current_state,
                projected=current_state,
                recommendations=["Cannot reduce to zero reviewers"],
                confidence=0.0,
            )

        capacity_change = (add_reviewers - remove_reviewers) / max(current_state.reviewer_count, 1)
        projected = DigitalTwinState(
            active_workflows=current_state.active_workflows,
            pending_reviews=max(0, int(current_state.pending_reviews * (1 - capacity_change * 0.5))),
            reviewer_count=new_count,
            avg_cycle_time_hours=current_state.avg_cycle_time_hours * (1 - capacity_change * 0.3),
            sla_compliance_rate=min(1.0, current_state.sla_compliance_rate * (1 + capacity_change * 0.1)),
            vendor_count=current_state.vendor_count,
            active_obligations=current_state.active_obligations,
            overdue_obligations=max(0, int(current_state.overdue_obligations * (1 - capacity_change * 0.3))),
            risk_score=current_state.risk_score * (1 - capacity_change * 0.05),
        )

        return TwinSimulationResult(
            simulation_type=TwinSimulationType.STAFFING_CHANGE,
            scenario_name=f"{'+' if add_reviewers > 0 else ''}{add_reviewers - remove_reviewers} reviewers",
            baseline=current_state,
            projected=projected,
            delta={"backlog_change": current_state.pending_reviews - projected.pending_reviews,
                   "cycle_change": current_state.avg_cycle_time_hours - projected.avg_cycle_time_hours},
            recommendations=[f"Adding {add_reviewers} reviewers reduces backlog by {current_state.pending_reviews - projected.pending_reviews}"],
            confidence=0.8,
        )

    def simulate_vendor_disruption(self, current_state: DigitalTwinState, vendor_pct: float = 0.3) -> TwinSimulationResult:
        """Simulate the impact of a major vendor disruption."""
        projected = DigitalTwinState(
            active_workflows=current_state.active_workflows,
            pending_reviews=int(current_state.pending_reviews * (1 + vendor_pct)),
            reviewer_count=current_state.reviewer_count,
            avg_cycle_time_hours=current_state.avg_cycle_time_hours * (1 + vendor_pct * 0.5),
            sla_compliance_rate=current_state.sla_compliance_rate * (1 - vendor_pct * 0.3),
            vendor_count=max(0, current_state.vendor_count - 1),
            active_obligations=current_state.active_obligations,
            overdue_obligations=int(current_state.overdue_obligations * (1 + vendor_pct)),
            risk_score=min(1.0, current_state.risk_score * (1 + vendor_pct * 0.5)),
        )

        return TwinSimulationResult(
            simulation_type=TwinSimulationType.VENDOR_DISRUPTION,
            scenario_name=f"Vendor disruption affecting {vendor_pct:.0%} of operations",
            baseline=current_state,
            projected=projected,
            delta={"risk_increase": projected.risk_score - current_state.risk_score,
                   "backlog_increase": projected.pending_reviews - current_state.pending_reviews},
            recommendations=[f"Develop vendor backup plan to mitigate {vendor_pct:.0%} operational impact",
                             "Increase safety stock of critical vendor services"],
            confidence=0.75,
        )

    def simulate_regulatory_change(self, current_state: DigitalTwinState, regulation_impact: str = "medium") -> TwinSimulationResult:
        """Simulate the impact of a regulatory change."""
        impact_map = {"low": 0.1, "medium": 0.2, "high": 0.35, "critical": 0.5}
        impact = impact_map.get(regulation_impact, 0.2)

        projected = DigitalTwinState(
            active_workflows=current_state.active_workflows,
            pending_reviews=int(current_state.pending_reviews * (1 + impact)),
            reviewer_count=current_state.reviewer_count,
            avg_cycle_time_hours=current_state.avg_cycle_time_hours * (1 + impact * 0.3),
            sla_compliance_rate=current_state.sla_compliance_rate * (1 - impact * 0.2),
            vendor_count=current_state.vendor_count,
            active_obligations=int(current_state.active_obligations * (1 + impact)),
            overdue_obligations=int(current_state.overdue_obligations * (1 + impact)),
            risk_score=min(1.0, current_state.risk_score * (1 + impact)),
        )

        return TwinSimulationResult(
            simulation_type=TwinSimulationType.REGULATORY_SCENARIO,
            scenario_name=f"Regulatory change: {regulation_impact} impact",
            baseline=current_state,
            projected=projected,
            delta={"obligation_increase": projected.active_obligations - current_state.active_obligations,
                   "risk_increase": projected.risk_score - current_state.risk_score},
            recommendations=[f"Begin compliance assessment for {regulation_impact}-impact regulation",
                             "Allocate additional reviewer capacity for expected workload increase"],
            confidence=0.7,
        )

    def run_full_twin_simulation(self, current_state: DigitalTwinState) -> list[TwinSimulationResult]:
        """Run all digital twin simulations and return results."""
        return [
            self.simulate_workflow_optimization(current_state, {"cycle_time_reduction_pct": 15, "sla_improvement_pct": 10}),
            self.simulate_staffing_change(current_state, add_reviewers=2),
            self.simulate_vendor_disruption(current_state, vendor_pct=0.3),
            self.simulate_regulatory_change(current_state, regulation_impact="medium"),
        ]


# ── Global singleton ───────────────────────────────────────────────

digital_twin = EnterpriseDigitalTwin()
