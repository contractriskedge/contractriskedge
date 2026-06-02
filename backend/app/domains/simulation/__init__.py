"""Simulation & Scenario Engine — what-if workflow simulation, SLA impact, reviewer load, vendor risk, compliance, negotiation.

Very few platforms do this well. Massive moat potential.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SimulationType(str, Enum):
    WORKFLOW_WHAT_IF = "workflow_what_if"
    SLA_IMPACT = "sla_impact"
    REVIEWER_LOAD = "reviewer_load"
    VENDOR_RISK = "vendor_risk"
    COMPLIANCE_EXPOSURE = "compliance_exposure"
    NEGOTIATION_STRATEGY = "negotiation_strategy"
    COST_OPTIMIZATION = "cost_optimization"


@dataclass
class SimulationInput:
    """Input parameters for a simulation."""
    simulation_type: SimulationType
    parameters: dict[str, Any] = field(default_factory=dict)
    scenario_name: str = ""


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    simulation_type: SimulationType
    scenario_name: str
    baseline: dict[str, Any] = field(default_factory=dict)
    projected: dict[str, Any] = field(default_factory=dict)
    delta: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    executed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SimulationEngine:
    """Enterprise simulation engine for what-if analysis.

    Capabilities:
    - What-if workflow simulation (change stage SLA, add reviewers)
    - SLA impact simulation (what happens if SLA changes)
    - Reviewer load simulation (add/remove reviewers)
    - Vendor risk simulation (what if vendor fails)
    - Compliance exposure simulation (what if regulation changes)
    - Negotiation strategy simulation (what if we change approach)
    """

    def simulate_workflow_what_if(self, params: dict[str, Any]) -> SimulationResult:
        """Simulate the impact of workflow changes."""
        current_stages = params.get("stages", [])
        sla_changes = params.get("sla_changes", {})  # stage_name -> new_sla_hours
        additional_reviewers = params.get("additional_reviewers", 0)

        baseline_total = sum(s.get("sla_hours", 8) for s in current_stages)
        baseline_bottlenecks = sum(1 for s in current_stages if s.get("sla_hours", 8) > 24)

        projected_stages = []
        for s in current_stages:
            new_sla = sla_changes.get(s.get("name", ""), s.get("sla_hours", 8))
            projected_stages.append({**s, "sla_hours": new_sla})

        projected_total = sum(s.get("sla_hours", 8) for s in projected_stages)
        projected_bottlenecks = sum(1 for s in projected_stages if s.get("sla_hours", 8) > 24)

        # Reviewer impact
        if additional_reviewers > 0:
            projected_total *= 0.9  # 10% reduction per additional reviewer
            projected_bottlenecks = max(0, projected_bottlenecks - additional_reviewers)

        recommendations = []
        if projected_bottlenecks < baseline_bottlenecks:
            recommendations.append(f"Reduce cycle time by {baseline_total - projected_total:.0f}h by adjusting SLAs")
        if additional_reviewers > 0:
            recommendations.append(f"Adding {additional_reviewers} reviewers reduces bottlenecks by {baseline_bottlenecks - projected_bottlenecks}")

        return SimulationResult(
            simulation_type=SimulationType.WORKFLOW_WHAT_IF,
            scenario_name=params.get("scenario_name", "Workflow Optimization"),
            baseline={"total_hours": baseline_total, "bottlenecks": baseline_bottlenecks},
            projected={"total_hours": projected_total, "bottlenecks": projected_bottlenecks},
            delta={"hours_saved": baseline_total - projected_total, "bottlenecks_resolved": baseline_bottlenecks - projected_bottlenecks},
            recommendations=recommendations,
            confidence=0.85,
        )

    def simulate_reviewer_load(self, params: dict[str, Any]) -> SimulationResult:
        """Simulate the impact of reviewer staffing changes."""
        current_reviewers = params.get("current_reviewers", 10)
        current_backlog = params.get("current_backlog", 100)
        avg_review_time_hours = params.get("avg_review_time_hours", 4)
        new_reviews_per_day = params.get("new_reviews_per_day", 10)
        add_reviewers = params.get("add_reviewers", 0)
        remove_reviewers = params.get("remove_reviewers", 0)

        total_reviewers = current_reviewers + add_reviewers - remove_reviewers
        if total_reviewers <= 0:
            return SimulationResult(
                simulation_type=SimulationType.REVIEWER_LOAD,
                scenario_name=params.get("scenario_name", "Staffing Impact"),
                baseline={"backlog": current_backlog, "reviewers": current_reviewers},
                projected={"backlog": current_backlog, "reviewers": 0},
                delta={},
                recommendations=["Cannot reduce to zero reviewers"],
                confidence=0.0,
            )

        daily_capacity = total_reviewers * (8 / avg_review_time_hours)
        daily_net_change = daily_capacity - new_reviews_per_day

        days_to_clear = current_backlog / max(daily_net_change, 0.1) if daily_net_change > 0 else float("inf")
        backlog_after_30d = max(0, current_backlog + (new_reviews_per_day - daily_capacity) * 30)

        recommendations = []
        if daily_net_change <= 0:
            recommendations.append(f"Backlog growing by {abs(daily_net_change):.0f} reviews/day — add {int(abs(daily_net_change)) + 1} more reviewers")
        else:
            recommendations.append(f"Backlog clearing in {days_to_clear:.0f} days at current capacity")
        if backlog_after_30d > current_backlog:
            recommendations.append(f"Projected backlog of {backlog_after_30d:.0f} in 30 days — plan for additional capacity")

        return SimulationResult(
            simulation_type=SimulationType.REVIEWER_LOAD,
            scenario_name=params.get("scenario_name", "Staffing Impact"),
            baseline={"backlog": current_backlog, "reviewers": current_reviewers, "daily_capacity": daily_capacity},
            projected={"backlog_30d": backlog_after_30d, "reviewers": total_reviewers, "daily_capacity": daily_capacity},
            delta={"backlog_change_30d": backlog_after_30d - current_backlog, "reviewer_change": add_reviewers - remove_reviewers},
            recommendations=recommendations,
            confidence=0.8,
        )

    def simulate_vendor_risk(self, params: dict[str, Any]) -> SimulationResult:
        """Simulate the impact of a vendor failure or concentration change."""
        vendor_name = params.get("vendor_name", "Unknown")
        contract_count = params.get("contract_count", 0)
        total_value = params.get("total_value", 0)
        disruption_pct = params.get("disruption_pct", 1.0)  # 0.0-1.0
        has_alternative = params.get("has_alternative", False)

        financial_impact = total_value * disruption_pct
        operational_impact = contract_count * disruption_pct * (0.5 if has_alternative else 1.0)
        recovery_days = 30 if has_alternative else 90

        recommendations = []
        if not has_alternative:
            recommendations.append(f"CRITICAL: No alternative vendor for {vendor_name} — develop backup plan")
        if financial_impact > 100000:
            recommendations.append(f"Financial exposure of ${financial_impact:,.0f} — consider diversifying")
        if recovery_days > 60:
            recommendations.append(f"Recovery would take {recovery_days} days — unacceptable for critical vendor")

        return SimulationResult(
            simulation_type=SimulationType.VENDOR_RISK,
            scenario_name=f"Vendor Failure: {vendor_name}",
            baseline={"contracts": contract_count, "value": total_value, "recovery_days": recovery_days},
            projected={"financial_impact": financial_impact, "operational_impact": operational_impact},
            delta={"exposed_value": financial_impact, "risk_score": round(financial_impact / max(total_value, 1), 4)},
            recommendations=recommendations,
            confidence=0.75,
        )

    def simulate_compliance_exposure(self, params: dict[str, Any]) -> SimulationResult:
        """Simulate compliance exposure under regulatory changes."""
        regulation = params.get("regulation", "Unknown")
        current_compliance_rate = params.get("compliance_rate", 0.5)
        new_requirement_severity = params.get("new_requirement_severity", 0.3)
        affected_contracts = params.get("affected_contracts", 0)

        projected_compliance = max(0, current_compliance_rate - new_requirement_severity)
        newly_non_compliant = int(affected_contracts * new_requirement_severity)
        remediation_cost = newly_non_compliant * 5000

        recommendations = []
        if projected_compliance < 0.7:
            recommendations.append(f"New {regulation} requirements would make {newly_non_compliant} contracts non-compliant")
            recommendations.append(f"Estimated remediation cost: ${remediation_cost:,}")
        if new_requirement_severity > 0.5:
            recommendations.append(f"Major regulatory change detected — engage compliance team immediately")

        return SimulationResult(
            simulation_type=SimulationType.COMPLIANCE_EXPOSURE,
            scenario_name=f"Regulatory Change: {regulation}",
            baseline={"compliance_rate": current_compliance_rate, "compliant_contracts": affected_contracts},
            projected={"compliance_rate": projected_compliance, "newly_non_compliant": newly_non_compliant},
            delta={"compliance_drop": current_compliance_rate - projected_compliance, "remediation_cost": remediation_cost},
            recommendations=recommendations,
            confidence=0.7,
        )

    def run_scenario(self, input_data: SimulationInput) -> SimulationResult:
        """Run a simulation scenario based on type."""
        mapping = {
            SimulationType.WORKFLOW_WHAT_IF: self.simulate_workflow_what_if,
            SimulationType.REVIEWER_LOAD: self.simulate_reviewer_load,
            SimulationType.VENDOR_RISK: self.simulate_vendor_risk,
            SimulationType.COMPLIANCE_EXPOSURE: self.simulate_compliance_exposure,
        }
        simulator = mapping.get(input_data.simulation_type)
        if not simulator:
            raise ValueError(f"Unknown simulation type: {input_data.simulation_type}")
        return simulator(input_data.parameters)


# ── Global singleton ───────────────────────────────────────────────

simulation_engine = SimulationEngine()
