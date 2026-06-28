"""Workflow Simulator Engine — pure function simulator for workflow versions.

Given a workflow version and contract data, computes the exact approval path:
which stages fire, who gets assigned, which rules match, and why.
Supports sandbox mode (no side effects) and dry run (against real contracts).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.domains.workflow.json_logic import json_logic, RuleEvaluator

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────


@dataclass
class SimulationInput:
    """Input to the workflow simulator."""
    workflow_version: Any
    contract_data: dict[str, Any] = field(default_factory=dict)
    sandbox_mode: bool = True


@dataclass
class SimulatedStage:
    """A single simulated stage in the workflow execution path."""
    name: str = ""
    stage_type: str = ""
    sla_hours: Optional[int] = None
    calendar_id: Optional[str] = None
    assigned_to: Optional[str] = None
    approval_mode: str = "auto"
    resolution_strategy: str = "auto_proceed"
    resolved_user: Optional[str] = None
    candidates: list[str] = field(default_factory=list)
    selection_reason: str = ""
    matched_conditions: list[dict[str, Any]] = field(default_factory=list)
    escalation_chain: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RuleMatch:
    """A rule that matched during simulation."""
    rule_id: str = ""
    rule_summary: str = ""
    reason: str = ""
    execution_time_ms: float = 0.0


@dataclass
class RuleSkip:
    """A rule that was skipped during simulation."""
    rule_id: str = ""
    rule_summary: str = ""
    reason: str = ""


@dataclass
class SimulationResult:
    """Result of a workflow simulation."""
    stages: list[SimulatedStage] = field(default_factory=list)
    total_sla_hours: float = 0.0
    matched_rules: list[RuleMatch] = field(default_factory=list)
    skipped_rules: list[RuleSkip] = field(default_factory=list)
    execution_context: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SimulationLog:
    """Audit log entry for a simulation run."""
    simulation_id: str = ""
    version_id: str = ""
    user_id: str = ""
    input: SimulationInput | None = None
    output: SimulationResult | None = None
    matched_rules: int = 0
    created_at: str = ""
    led_to_publish: bool = False


@dataclass
class DryRunResult:
    """Result of a dry run against real contracts."""
    total_contracts: int = 0
    would_route_differently: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)


# ── Workflow Simulator ─────────────────────────────────────────────


class WorkflowSimulator:
    """Pure function simulator for workflow versions.

    Given a workflow version definition and contract data, computes
    the exact execution path without side effects.
    """

    def __init__(self) -> None:
        self.evaluator = RuleEvaluator()

    def simulate(self, input_data: SimulationInput) -> SimulationResult:
        """Simulate a workflow version against contract data.

        Args:
            input_data: The simulation input with version and contract data.

        Returns:
            SimulationResult with all stages, rule matches, and warnings.
        """
        result = SimulationResult()
        version = input_data.workflow_version
        contract = input_data.contract_data

        # Build execution context from contract data and metadata
        context = self._build_context(version, contract)
        result.execution_context = context

        # Extract stages definition
        stages_def = self._safe_get(version, "stages_definition", [])
        if not stages_def:
            result.warnings.append("No stages defined in workflow version.")
            return result

        # Extract rules definition
        rules_def = self._safe_get(version, "rules_definition", [])

        # Evaluate rules against context
        self._evaluate_rules(rules_def, context, result)

        # Simulate each stage in order
        total_sla = 0.0
        for stage_def in stages_def:
            simulated = self._simulate_stage(stage_def, context, result)
            result.stages.append(simulated)
            if simulated.sla_hours:
                total_sla += simulated.sla_hours

        result.total_sla_hours = total_sla

        logger.info(
            "Simulation complete: %d stages, %d matched rules, %.1f total SLA hours",
            len(result.stages),
            len(result.matched_rules),
            total_sla,
        )
        return result

    def batch_simulate(
        self,
        version: Any,
        contracts: list[dict[str, Any]],
    ) -> list[SimulationResult]:
        """Run simulation against multiple contracts.

        Args:
            version: The workflow version to simulate.
            contracts: List of contract data dicts.

        Returns:
            List of SimulationResult, one per contract.
        """
        results: list[SimulationResult] = []
        for contract in contracts:
            input_data = SimulationInput(
                workflow_version=version,
                contract_data=contract,
                sandbox_mode=True,
            )
            results.append(self.simulate(input_data))
        return results

    def dry_run(
        self,
        version: Any,
        recent_contracts: list[dict[str, Any]],
    ) -> DryRunResult:
        """Dry run — simulate how many contracts would route differently.

        Compares the simulated routing against the actual routing
        that occurred for each contract.

        Args:
            version: The proposed workflow version to test.
            recent_contracts: List of recent contract data dicts with
                              an 'actual_routing' key.

        Returns:
            DryRunResult showing how many would route differently.
        """
        dry_result = DryRunResult()
        dry_result.total_contracts = len(recent_contracts)

        for contract in recent_contracts:
            input_data = SimulationInput(
                workflow_version=version,
                contract_data=contract,
                sandbox_mode=True,
            )
            sim_result = self.simulate(input_data)
            actual_routing = contract.get("actual_routing", [])

            sim_stage_names = [s.name for s in sim_result.stages]
            if sim_stage_names != actual_routing:
                dry_result.would_route_differently += 1
                dry_result.details.append({
                    "contract_id": contract.get("contract_id", "unknown"),
                    "simulated_routing": sim_stage_names,
                    "actual_routing": actual_routing,
                    "matched_rules": [r.rule_id for r in sim_result.matched_rules],
                })

        logger.info(
            "Dry run: %d/%d contracts would route differently",
            dry_result.would_route_differently,
            dry_result.total_contracts,
        )
        return dry_result

    # ── Private Methods ─────────────────────────────────────────

    def _build_context(
        self,
        version: Any,
        contract: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the evaluation context from version variables and contract data."""
        context: dict[str, Any] = dict(contract)

        # Merge version variables into context
        variables = self._safe_get(version, "variables", {})
        if isinstance(variables, dict):
            context.update(variables)

        # Add workflow metadata
        context.setdefault("workflow", {})
        context["workflow"]["version_id"] = self._safe_get(version, "version_id", "")
        context["workflow"]["version_number"] = self._safe_get(version, "version_number", 1)

        return context

    def _evaluate_rules(
        self,
        rules_def: list[dict[str, Any]],
        context: dict[str, Any],
        result: SimulationResult,
    ) -> None:
        """Evaluate all rules and populate matched/skipped lists."""
        for rule in (rules_def or []):
            rule_name = rule.get("rule_name", "unnamed")
            conditions = rule.get("conditions", {})

            if not conditions:
                result.skipped_rules.append(RuleSkip(
                    rule_id=rule_name,
                    rule_summary=rule.get("description", ""),
                    reason="No conditions defined on rule.",
                ))
                continue

            start_time = time.monotonic()
            try:
                matched = json_logic(conditions, context)
                elapsed = (time.monotonic() - start_time) * 1000

                if matched:
                    result.matched_rules.append(RuleMatch(
                        rule_id=rule_name,
                        rule_summary=rule.get("description", ""),
                        reason=f"Conditions evaluated to true against context.",
                        execution_time_ms=elapsed,
                    ))
                else:
                    result.skipped_rules.append(RuleSkip(
                        rule_id=rule_name,
                        rule_summary=rule.get("description", ""),
                        reason="Conditions evaluated to false.",
                    ))
            except Exception as exc:
                elapsed = (time.monotonic() - start_time) * 1000
                result.skipped_rules.append(RuleSkip(
                    rule_id=rule_name,
                    rule_summary=rule.get("description", ""),
                    reason=f"Evaluation error: {exc}",
                ))
                logger.warning("Rule '%s' evaluation failed: %s", rule_name, exc)

    def _simulate_stage(
        self,
        stage_def: dict[str, Any],
        context: dict[str, Any],
        result: SimulationResult,
    ) -> SimulatedStage:
        """Simulate a single stage and determine its resolution."""
        stage_name = stage_def.get("name", "unnamed")
        stage_type = stage_def.get("stage_type", "")
        on_entry = stage_def.get("on_entry", [])
        sla_hours = stage_def.get("sla_hours")
        required_role = stage_def.get("required_role")
        assignee = stage_def.get("assignee")
        transitions = stage_def.get("transitions", [])
        escalation = stage_def.get("escalation_chain", [])

        simulated = SimulatedStage(
            name=stage_name,
            stage_type=stage_type,
            sla_hours=sla_hours,
            calendar_id=stage_def.get("calendar_id"),
            assigned_to=assignee,
        )

        # Determine approval mode from on_entry actions
        if "require_approval" in on_entry:
            simulated.approval_mode = "required"
            simulated.resolution_strategy = "require_approval"
        elif "require_review" in on_entry:
            simulated.approval_mode = "review"
            simulated.resolution_strategy = "require_review"
        elif "auto_proceed" in on_entry:
            simulated.approval_mode = "auto"
            simulated.resolution_strategy = "auto_proceed"
        elif "block" in on_entry:
            simulated.approval_mode = "blocked"
            simulated.resolution_strategy = "block"

        # Resolve assignee / candidates
        if assignee:
            simulated.resolved_user = assignee
            simulated.selection_reason = "Explicitly assigned in stage definition."
        elif required_role:
            # In sandbox mode, we note the role but don't resolve a specific user
            simulated.candidates = [f"any:{required_role}"]
            simulated.selection_reason = f"Resolved by role '{required_role}'."
        else:
            simulated.selection_reason = "No assignee or role specified — stage may not proceed."

        # Check transition conditions
        for transition in transitions:
            condition = transition.get("condition", {})
            target = transition.get("target", "")
            if condition:
                try:
                    if json_logic(condition, context):
                        simulated.matched_conditions.append({
                            "transition": transition.get("name", ""),
                            "target": target,
                            "condition": condition,
                            "matched": True,
                        })
                    else:
                        simulated.matched_conditions.append({
                            "transition": transition.get("name", ""),
                            "target": target,
                            "condition": condition,
                            "matched": False,
                        })
                except Exception as exc:
                    result.warnings.append(
                        f"Condition evaluation failed for transition '{target}' "
                        f"in stage '{stage_name}': {exc}"
                    )

        # Capture escalation chain
        if escalation:
            simulated.escalation_chain = list(escalation)

        return simulated

    def _safe_get(self, obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get an attribute from an object or dict."""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)
