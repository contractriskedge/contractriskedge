"""Policy Engine service — simulation, dry-run, rule graph, impact analysis, health check.

Extends the playbook domain's PolicyEngine with enterprise-grade policy management.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.domains.playbook.engine import (
    PolicyEngine, EvaluationContext, ExtractedClause,
    RuleEvaluator, DeviationDetector, ClauseRecommender,
    RiskScorer, ApprovalThresholdEvaluator,
)
from app.domains.playbook.models import (
    PolicyRule, ClauseStandard, ApprovalThreshold,
    PolicyEvaluation, EvaluationStatus,
)
from app.domains.playbook.repository import PlaybookRepository
from app.domains.policy.schemas import (
    RuleGraph, RuleGraphNode, RuleGraphEdge,
    SimulationRequest, SimulationResult,
    SimulationRuleResult, SimulationDeviation,
    SimulationContractProfile, SimulationClause, SimulationFinding,
    SimulationRuleOverride, SimulationSummary,
    SimulatedFindingImpact, SimulatedViolationImpact, SimulatedRedlineImpact,
    DryRunRequest, DryRunResult,
    PolicyChange, ImpactedContract, PolicyImpactAnalysis,
    PolicyAuditEvent, PolicyAuditLogResponse,
    PolicyHealthCheck,
)

logger = logging.getLogger(__name__)


def deviation_score_for_rule(rule_result, deviations: list) -> float:
    """Compute aggregate deviation score for a given rule result."""
    if not rule_result.matched:
        return 1.0
    rule_devs = [d for d in deviations if getattr(d, 'clause_category', '') == rule_result.rule_type]
    if not rule_devs:
        return 0.0
    return max(d.score for d in rule_devs)


@dataclass
class PolicySimulationEngine:
    """Simulation engine for what-if policy analysis.

    Evaluates rules against hypothetical contract profiles without
    persisting results or affecting live state.
    """

    repo: PlaybookRepository
    tenant_id: str

    async def simulate(self, request: SimulationRequest) -> SimulationResult:
        """Run a policy simulation against a hypothetical contract profile."""
        # Load playbook rules, standards, thresholds
        rules = await self.repo.get_active_rules_by_playbook(request.playbook_id, self.tenant_id)
        standards = await self.repo.get_active_clauses_by_playbook(request.playbook_id, self.tenant_id)
        thresholds = await self.repo.get_active_thresholds_by_playbook(request.playbook_id, self.tenant_id)

        # Apply rule overrides
        overridden_rule_ids: set[str] = set()
        override_map = {o.rule_id: o for o in request.rule_overrides}
        modified_rules: list[PolicyRule] = []
        original_effects: dict[str, str] = {}

        for rule in rules:
            rule_id_str = str(rule.rule_id)
            if rule_id_str in override_map:
                override = override_map[rule_id_str]
                original_effects[rule_id_str] = rule.effect.value if hasattr(rule.effect, 'value') else str(rule.effect)
                if override.override_effect:
                    rule.effect = override.override_effect  # type: ignore[assignment]
                if override.is_active is not None:
                    rule.is_active = override.is_active
                overridden_rule_ids.add(rule_id_str)
            modified_rules.append(rule)

        # Build evaluation context from contract profile
        profile = request.contract_profile
        ctx = EvaluationContext(
            upload_id=f"simulation_{uuid.uuid4().hex[:12]}",
            tenant_id=self.tenant_id,
            contract_value=profile.contract_value,
            jurisdiction=profile.jurisdiction,
            industry=profile.industry,
            counterparty=profile.counterparty,
            risk_score=profile.risk_score,
            clauses=[
                ExtractedClause(
                    category=c.category,
                    text=c.text,
                    text_snippet=c.text_snippet or c.text[:200],
                    confidence=c.confidence,
                )
                for c in profile.clauses
            ],
            findings=[
                {
                    "severity": f.severity,
                    "clause_type": f.clause_type,
                    "title": f.title,
                    "description": f.description,
                }
                for f in profile.findings
            ],
        )

        # Run evaluation
        eval_result = PolicyEngine.evaluate(modified_rules, standards, thresholds, ctx)

        # Map results to simulation format
        sim_rule_results = []
        for rr in eval_result.rule_results:
            rule_id_str = rr.rule_id
            sim_rule_results.append(SimulationRuleResult(
                rule_id=rule_id_str,
                rule_name=rr.rule_name,
                rule_type=rr.rule_type,
                effect=rr.effect,
                original_effect=original_effects.get(rule_id_str),
                matched=rr.matched,
                priority=rr.priority,
                details=rr.details,
                deviation_severity=rr.deviation_severity,
                was_overridden=rule_id_str in overridden_rule_ids,
            ))

        sim_deviations = [
            SimulationDeviation(
                clause_category=d.clause_category,
                severity=d.severity,
                score=d.score,
                expected=d.expected,
                actual=d.actual,
                recommendation=d.recommendation,
            )
            for d in eval_result.deviations
        ]

        # ── Predicted downstream impacts ─────────────────────────────
        # Translate deviations into predicted finding/violation/redline
        # impacts so the frontend can show what would change.
        predicted_finding_impacts: list[SimulatedFindingImpact] = []
        predicted_violation_impacts: list[SimulatedViolationImpact] = []
        predicted_redline_impacts: list[SimulatedRedlineImpact] = []

        rule_map = {str(r.rule_id): r for r in modified_rules}

        for dev in eval_result.deviations:
            # Finding impact — each deviation maps to a simulated finding
            predicted_finding_impacts.append(SimulatedFindingImpact(
                clause_category=dev.clause_category,
                severity=dev.severity,
                title=f"Policy deviation: {dev.clause_category}",
                description=dev.recommendation or f"Expected '{dev.expected}', got '{dev.actual}'",
                deviation_score=dev.score,
                would_generate_finding=dev.score >= 0.3,
            ))

        for rr in eval_result.rule_results:
            rule = rule_map.get(rr.rule_id)
            if not rule:
                continue
            # Violation impact — rules that didn't match or have deviations
            severity = rr.deviation_severity or "medium"
            would_violate = not rr.matched or (severity in ("critical", "high"))
            predicted_violation_impacts.append(SimulatedViolationImpact(
                rule_id=rr.rule_id,
                rule_name=rr.rule_name,
                clause_category=rr.rule_type,
                severity=severity,
                effect=rr.effect,
                is_mandatory=getattr(rule, "is_mandatory", False),
                would_violate=would_violate,
                deviation_score=deviation_score_for_rule(rr, eval_result.deviations),
            ))

            # Redline impact — for violations that need remediation
            if would_violate and rr.effect in ("block", "restrict"):
                predicted_redline_impacts.append(SimulatedRedlineImpact(
                    clause_category=rr.rule_type,
                    rule_id=rr.rule_id,
                    rule_name=rr.rule_name,
                    suggested_action="modify" if rr.effect == "restrict" else "remove",
                    rationale=f"Rule '{rr.rule_name}' requires {rr.effect} on non-compliant clauses",
                    confidence=0.75 if rr.matched else 0.6,
                ))

        return SimulationResult(
            simulation_id=uuid.uuid4().hex,
            playbook_id=request.playbook_id,
            name=request.name or f"Simulation {datetime.now(timezone.utc).isoformat()}",
            description=request.description,
            contract_profile=profile,
            results=sim_rule_results,
            deviations=sim_deviations,
            rule_overrides_applied=len(overridden_rule_ids),
            total_rules=eval_result.total_rules,
            rules_passed=eval_result.rules_passed,
            rules_failed=eval_result.rules_failed,
            deviations_found=eval_result.deviations_found,
            mandatory_blocks=eval_result.mandatory_blocks,
            approval_required=eval_result.approval_required,
            risk_score=eval_result.risk_score,
            risk_level=eval_result.risk_level,
            created_at=datetime.now(timezone.utc),
            predicted_finding_impacts=predicted_finding_impacts,
            predicted_violation_impacts=predicted_violation_impacts,
            predicted_redline_impacts=predicted_redline_impacts,
        )

    async def dry_run(self, request: DryRunRequest) -> DryRunResult:
        """Dry-run policy evaluation against a real contract without persisting."""
        rules = await self.repo.get_active_rules_by_playbook(request.playbook_id, self.tenant_id)
        standards = await self.repo.get_active_clauses_by_playbook(request.playbook_id, self.tenant_id)
        thresholds = await self.repo.get_active_thresholds_by_playbook(request.playbook_id, self.tenant_id)

        # Filter to specific rules if requested
        if request.rule_ids:
            rule_id_set = set(request.rule_ids)
            rules = [r for r in rules if str(r.rule_id) in rule_id_set]

        # Load contract context from upload
        upload = await self.repo.get_upload(request.upload_id)
        if not upload:
            return DryRunResult(
                playbook_id=request.playbook_id,
                upload_id=request.upload_id,
                warnings=["Upload not found"],
            )

        # Build context from existing analysis
        findings_data = await self.repo.get_upload_findings(request.upload_id)
        clauses_data = await self.repo.get_upload_clauses(request.upload_id)

        ctx = EvaluationContext(
            upload_id=request.upload_id,
            tenant_id=self.tenant_id,
            review_id=request.review_id,
            contract_value=getattr(upload, 'contract_value', None),
            jurisdiction=getattr(upload, 'jurisdiction', None),
            risk_score=getattr(upload, 'risk_score', None),
            clauses=[
                ExtractedClause(
                    category=c.get("clause_type", "other"),
                    text=c.get("text", ""),
                    text_snippet=c.get("text", "")[:200],
                    confidence=c.get("confidence", 1.0),
                )
                for c in clauses_data
            ],
            findings=findings_data if isinstance(findings_data, list) else [],
        )

        eval_result = PolicyEngine.evaluate(rules, standards, thresholds, ctx)

        sim_results = [
            SimulationRuleResult(
                rule_id=rr.rule_id,
                rule_name=rr.rule_name,
                rule_type=rr.rule_type,
                effect=rr.effect,
                matched=rr.matched,
                priority=rr.priority,
                details=rr.details,
                deviation_severity=rr.deviation_severity,
            )
            for rr in eval_result.rule_results
        ]

        sim_deviations = [
            SimulationDeviation(
                clause_category=d.clause_category,
                severity=d.severity,
                score=d.score,
                expected=d.expected,
                actual=d.actual,
                recommendation=d.recommendation,
            )
            for d in eval_result.deviations
        ]

        warnings: list[str] = []
        if not clauses_data:
            warnings.append("No clause data found for this upload")
        if not findings_data:
            warnings.append("No AI findings found for this upload")

        return DryRunResult(
            playbook_id=request.playbook_id,
            upload_id=request.upload_id,
            evaluation_id=request.review_id,
            results=sim_results,
            deviations=sim_deviations,
            total_rules=eval_result.total_rules,
            rules_passed=eval_result.rules_passed,
            rules_failed=eval_result.rules_failed,
            deviations_found=eval_result.deviations_found,
            mandatory_blocks=eval_result.mandatory_blocks,
            approval_required=eval_result.approval_required,
            risk_score=eval_result.risk_score,
            risk_level=eval_result.risk_level,
            warnings=warnings,
        )


@dataclass
class PolicyRuleGraphBuilder:
    """Builds dependency graphs of policy rules for visualization and analysis."""

    repo: PlaybookRepository

    async def build_graph(self, playbook_id: str) -> RuleGraph:
        """Construct a full dependency graph of all rules in a playbook."""
        rules = await self.repo.get_active_rules_by_playbook(playbook_id, self.repo.tenant_id)
        sorted_rules = sorted(rules, key=lambda r: r.priority)

        nodes: list[RuleGraphNode] = []
        edges: list[RuleGraphEdge] = []
        mandatory_count = 0
        blocking_count = 0
        approval_count = 0

        # Build nodes
        rule_ids_in_order: list[str] = []
        for i, rule in enumerate(sorted_rules):
            rid = str(rule.rule_id)
            rule_ids_in_order.append(rid)
            effect_str = rule.effect.value if hasattr(rule.effect, 'value') else str(rule.effect)

            if rule.is_mandatory:
                mandatory_count += 1
            if effect_str == "block":
                blocking_count += 1
            if effect_str == "require_approval":
                approval_count += 1

            # Summarize conditions
            conditions = rule.conditions or {}
            cond_summary = self._summarize_conditions(conditions)

            nodes.append(RuleGraphNode(
                rule_id=rid,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                effect=effect_str,
                priority=rule.priority,
                is_mandatory=rule.is_mandatory,
                target_category=rule.target_category,
                conditions_summary=cond_summary,
            ))

        # Build priority-order edges
        for i in range(len(rule_ids_in_order) - 1):
            edges.append(RuleGraphEdge(
                source_rule_id=rule_ids_in_order[i],
                target_rule_id=rule_ids_in_order[i + 1],
                edge_type="priority_order",
                label=f"priority {sorted_rules[i].priority} → {sorted_rules[i+1].priority}",
            ))

        # Detect same-category rules (potential conflicts)
        category_map: dict[str, list[str]] = {}
        for rule in sorted_rules:
            if rule.target_category:
                cat = rule.target_category
                if cat not in category_map:
                    category_map[cat] = []
                category_map[cat].append(str(rule.rule_id))

        for cat, rids in category_map.items():
            for i in range(len(rids)):
                for j in range(i + 1, len(rids)):
                    edges.append(RuleGraphEdge(
                        source_rule_id=rids[i],
                        target_rule_id=rids[j],
                        edge_type="conflicts_with",
                        label=f"same category: {cat}",
                    ))

        return RuleGraph(
            nodes=nodes,
            edges=edges,
            total_rules=len(nodes),
            mandatory_count=mandatory_count,
            blocking_count=blocking_count,
            approval_count=approval_count,
        )

    def _summarize_conditions(self, conditions: dict) -> str:
        """Create a human-readable summary of rule conditions."""
        operator = conditions.get("operator", "and")
        field = conditions.get("field")
        value = conditions.get("value")
        nested = conditions.get("conditions", [])

        if nested:
            parts = [self._summarize_conditions(c) for c in nested[:3]]
            summary = f" {operator.upper()} ".join(parts)
            if len(nested) > 3:
                summary += f" (+{len(nested) - 3} more)"
            return summary

        if field and value is not None:
            return f"{field} {operator} {value}"
        if field:
            return f"{field} {operator}"
        return "always"


@dataclass
class PolicyImpactAnalyzer:
    """Analyzes the impact of policy changes across all evaluated contracts."""

    repo: PlaybookRepository
    tenant_id: str

    async def analyze_impact(
        self,
        playbook_id: str,
        changes: list[PolicyChange],
        description: str = "",
    ) -> PolicyImpactAnalysis:
        """Analyze how proposed policy changes would affect existing evaluations."""
        # Load current rules
        current_rules = await self.repo.get_active_rules_by_playbook(playbook_id, self.repo.tenant_id)
        standards = await self.repo.get_active_clauses_by_playbook(playbook_id, self.repo.tenant_id)
        thresholds = await self.repo.get_active_thresholds_by_playbook(playbook_id, self.repo.tenant_id)

        # Get recent evaluations to test against
        evaluations = await self.repo.get_recent_evaluations(playbook_id, limit=20)

        impacted_contracts: list[ImpactedContract] = []
        contracts_with_new = 0
        contracts_with_resolved = 0
        total_risk_delta = 0.0

        for eval_record in evaluations:
            eval_data = eval_record.results or {}
            current_risk = eval_record.risk_score

            # Build context from stored evaluation
            ctx = EvaluationContext(
                upload_id=str(eval_record.upload_id),
                tenant_id=self.tenant_id,
                review_id=str(eval_record.review_id) if eval_record.review_id else None,
                risk_score=current_risk,
                clauses=[
                    ExtractedClause(
                        category=d.get("clause_category", "other"),
                        text=d.get("clause_text_snippet", ""),
                        text_snippet=d.get("clause_text_snippet", "")[:200],
                    )
                    for d in (eval_data.get("deviations", []) if isinstance(eval_data, dict) else [])
                ],
                findings=[],
            )

            # Apply changes to rules
            modified_rules = list(current_rules)
            change_map = {c.rule_id: c for c in changes}
            for i, rule in enumerate(modified_rules):
                rid = str(rule.rule_id)
                if rid in change_map:
                    change = change_map[rid]
                    if change.change_type == "deactivate":
                        modified_rules[i].is_active = False
                    elif change.change_type == "update":
                        for field, val in change.field_changes.items():
                            if hasattr(rule, field):
                                setattr(rule, field, val)

            # Re-evaluate
            new_result = PolicyEngine.evaluate(modified_rules, standards, thresholds, ctx)

            new_deviation_count = len(new_result.deviations)
            old_deviation_count = eval_record.deviations_found or 0
            deviation_diff = new_deviation_count - old_deviation_count

            if deviation_diff > 0:
                contracts_with_new += 1
            elif deviation_diff < 0:
                contracts_with_resolved += 1

            if new_result.risk_score is not None and current_risk is not None:
                total_risk_delta += new_result.risk_score - current_risk

            impacted_contracts.append(ImpactedContract(
                upload_id=str(eval_record.upload_id),
                review_id=str(eval_record.review_id) if eval_record.review_id else None,
                current_risk_score=current_risk,
                current_risk_level=eval_record.risk_level,
                simulated_risk_score=new_result.risk_score,
                simulated_risk_level=new_result.risk_level,
                new_deviations=max(0, deviation_diff),
                resolved_deviations=max(0, -deviation_diff),
            ))

        avg_risk_delta = total_risk_delta / len(impacted_contracts) if impacted_contracts else None

        return PolicyImpactAnalysis(
            analysis_id=uuid.uuid4().hex,
            playbook_id=playbook_id,
            change_description=description,
            changes=changes,
            impacted_contracts=impacted_contracts,
            total_impacted=len(impacted_contracts),
            contracts_with_new_deviations=contracts_with_new,
            contracts_with_resolved_deviations=contracts_with_resolved,
            overall_risk_delta=round(avg_risk_delta, 4) if avg_risk_delta is not None else None,
            created_at=datetime.now(timezone.utc),
        )


@dataclass
class PolicyHealthChecker:
    """Validates policy configuration health and detects issues."""

    repo: PlaybookRepository

    async def check_health(self, playbook_id: str) -> PolicyHealthCheck:
        """Run a health check on a playbook's policy configuration."""
        rules = await self.repo.get_all_rules(playbook_id)
        playbook = await self.repo.get_playbook(playbook_id)

        warnings: list[str] = []
        issues: list[str] = []
        conflicting_rules: list[str] = []
        orphaned_rules: list[str] = []
        rules_with_errors = 0
        rules_without_effect = 0

        active_rules = [r for r in rules if r.is_active]
        inactive_rules = [r for r in rules if not r.is_active]

        # Check for rules without conditions
        for rule in rules:
            conditions = rule.conditions or {}
            if not conditions.get("field") and not conditions.get("conditions"):
                rules_without_effect += 1
                warnings.append(f"Rule '{rule.name}' has no conditions — always matches")

        # Check for conflicting rules (same category, opposite effects)
        category_effects: dict[str, list[tuple[str, str]]] = {}
        for rule in active_rules:
            if rule.target_category:
                cat = rule.target_category
                effect_str = rule.effect.value if hasattr(rule.effect, 'value') else str(rule.effect)
                category_effects.setdefault(cat, []).append((str(rule.rule_id), effect_str))

        for cat, effects in category_effects.items():
            blocking = [rid for rid, e in effects if e == "block"]
            allowing = [rid for rid, e in effects if e == "allow"]
            if blocking and allowing:
                conflict_name = f"Category '{cat}': block({len(blocking)}) vs allow({len(allowing)})"
                conflicting_rules.append(conflict_name)
                issues.append(f"Conflicting rules for category '{cat}': blocking and allowing simultaneously")

        # Check for orphaned rules (targeting non-existent clauses)
        standards = await self.repo.get_active_clauses_by_playbook(playbook_id, self.repo.tenant_id)
        standard_categories = {s.category.value if hasattr(s.category, 'value') else str(s.category) for s in standards}
        for rule in active_rules:
            if rule.target_category and rule.target_category not in standard_categories:
                orphaned_rules.append(f"Rule '{rule.name}' targets non-existent category '{rule.target_category}'")
                warnings.append(f"Rule '{rule.name}' references category '{rule.target_category}' with no active clause standards")

        # Determine overall status
        status = "healthy"
        if issues:
            status = "issues"
        elif warnings:
            status = "warnings"

        return PolicyHealthCheck(
            playbook_id=playbook_id,
            playbook_name=playbook.name if playbook else "Unknown",
            status=status,
            total_rules=len(rules),
            active_rules=len(active_rules),
            inactive_rules=len(inactive_rules),
            rules_with_errors=rules_with_errors,
            rules_without_effect=rules_without_effect,
            conflicting_rules=conflicting_rules,
            orphaned_rules=orphaned_rules,
            warnings=warnings,
            issues=issues,
        )
