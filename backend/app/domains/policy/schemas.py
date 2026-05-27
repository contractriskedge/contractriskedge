"""Policy Engine schemas — simulation, dry-run, rule graph, impact analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Rule Graph ──────────────────────────────────────────────────────


class RuleGraphNode(BaseModel):
    """A node in the policy rule dependency graph."""
    rule_id: str
    rule_name: str
    rule_type: str
    effect: str
    priority: int
    is_mandatory: bool
    target_category: Optional[str] = None
    conditions_summary: str = ""


class RuleGraphEdge(BaseModel):
    """A dependency or ordering edge between rule nodes."""
    source_rule_id: str
    target_rule_id: str
    edge_type: str = "priority_order"  # 'priority_order', 'depends_on', 'conflicts_with', 'supersedes'
    label: Optional[str] = None


class RuleGraph(BaseModel):
    """Complete dependency graph of policy rules."""
    nodes: list[RuleGraphNode] = Field(default_factory=list)
    edges: list[RuleGraphEdge] = Field(default_factory=list)
    total_rules: int = 0
    mandatory_count: int = 0
    blocking_count: int = 0
    approval_count: int = 0


# ── Simulation ──────────────────────────────────────────────────────


class SimulationContractProfile(BaseModel):
    """Contract data profile for simulation."""
    contract_value: Optional[float] = None
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    counterparty: Optional[str] = None
    risk_score: Optional[float] = None
    clauses: list[SimulationClause] = Field(default_factory=list)
    findings: list[SimulationFinding] = Field(default_factory=list)


class SimulationClause(BaseModel):
    """Simulated contract clause."""
    category: str
    text: str
    text_snippet: str = ""
    confidence: float = 1.0


class SimulationFinding(BaseModel):
    """Simulated risk finding."""
    severity: str = "medium"
    clause_type: str = "other"
    title: str = ""
    description: str = ""


class SimulationRuleOverride(BaseModel):
    """Override a rule's effect or conditions for simulation."""
    rule_id: str
    override_effect: Optional[str] = None
    override_conditions: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class SimulationRequest(BaseModel):
    """Request to run a policy simulation."""
    playbook_id: str
    name: str = Field(default="", max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    contract_profile: SimulationContractProfile
    rule_overrides: list[SimulationRuleOverride] = Field(default_factory=list)
    include_recommendations: bool = True
    dry_run: bool = True  # simulations are always dry-runs by default


class SimulationRuleResult(BaseModel):
    """Simulated rule evaluation result."""
    rule_id: str
    rule_name: str
    rule_type: str
    effect: str
    original_effect: Optional[str] = None
    matched: bool
    priority: int
    details: Optional[str] = None
    deviation_severity: Optional[str] = None
    was_overridden: bool = False


class SimulationDeviation(BaseModel):
    """Simulated deviation result."""
    clause_category: str
    severity: str
    score: float
    expected: str
    actual: str
    recommendation: Optional[str] = None


class SimulationResult(BaseModel):
    """Complete simulation output."""
    simulation_id: str
    playbook_id: str
    name: str
    description: Optional[str] = None
    contract_profile: SimulationContractProfile
    results: list[SimulationRuleResult] = Field(default_factory=list)
    deviations: list[SimulationDeviation] = Field(default_factory=list)
    rule_overrides_applied: int = 0
    total_rules: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    deviations_found: int = 0
    mandatory_blocks: int = 0
    approval_required: int = 0
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    created_at: datetime


class SimulationSummary(BaseModel):
    """Summary of a saved simulation for listing."""
    simulation_id: str
    playbook_id: str
    playbook_name: str = ""
    name: str
    description: Optional[str] = None
    total_rules: int = 0
    rules_failed: int = 0
    deviations_found: int = 0
    risk_level: Optional[str] = None
    created_at: datetime


# ── Dry-Run Evaluation ──────────────────────────────────────────────


class DryRunRequest(BaseModel):
    """Request to dry-run a policy evaluation without persisting results."""
    playbook_id: str
    upload_id: str
    review_id: Optional[str] = None
    rule_ids: Optional[list[str]] = None  # subset of rules to test


class DryRunResult(BaseModel):
    """Dry-run evaluation output — no side effects."""
    playbook_id: str
    playbook_name: str = ""
    upload_id: str
    evaluation_id: Optional[str] = None
    results: list[SimulationRuleResult] = Field(default_factory=list)
    deviations: list[SimulationDeviation] = Field(default_factory=list)
    total_rules: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    deviations_found: int = 0
    mandatory_blocks: int = 0
    approval_required: int = 0
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


# ── Impact Analysis ─────────────────────────────────────────────────


class PolicyChange(BaseModel):
    """A proposed change to a policy rule."""
    rule_id: str
    change_type: str  # 'create', 'update', 'activate', 'deactivate', 'delete'
    field_changes: dict[str, Any] = Field(default_factory=dict)
    previous_state: Optional[dict[str, Any]] = None


class ImpactedContract(BaseModel):
    """A contract that would be affected by a policy change."""
    upload_id: str
    review_id: Optional[str] = None
    document_name: Optional[str] = None
    current_risk_score: Optional[float] = None
    current_risk_level: Optional[str] = None
    simulated_risk_score: Optional[float] = None
    simulated_risk_level: Optional[str] = None
    new_deviations: int = 0
    resolved_deviations: int = 0


class PolicyImpactAnalysis(BaseModel):
    """Impact analysis of proposed policy changes."""
    analysis_id: str
    playbook_id: str
    change_description: str = ""
    changes: list[PolicyChange] = Field(default_factory=list)
    impacted_contracts: list[ImpactedContract] = Field(default_factory=list)
    total_impacted: int = 0
    contracts_with_new_deviations: int = 0
    contracts_with_resolved_deviations: int = 0
    overall_risk_delta: Optional[float] = None
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime


# ── Policy Audit Trail ──────────────────────────────────────────────


class PolicyAuditEvent(BaseModel):
    """Enhanced audit event for policy operations."""
    event_id: str
    event_type: str  # 'rule.created', 'rule.updated', 'rule.simulated', 'rule.dry_run', 'policy.impact_analyzed'
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    actor_id: str
    actor_role: Optional[str] = None
    change_summary: str = ""
    previous_state: Optional[dict[str, Any]] = None
    new_state: Optional[dict[str, Any]] = None
    simulation_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class PolicyAuditLogResponse(BaseModel):
    """Paginated policy audit log."""
    events: list[PolicyAuditEvent] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


# ── Policy Health ───────────────────────────────────────────────────


class PolicyHealthCheck(BaseModel):
    """Health check for a playbook's policy configuration."""
    playbook_id: str
    playbook_name: str
    status: str = "healthy"  # 'healthy', 'warnings', 'issues'
    total_rules: int = 0
    active_rules: int = 0
    inactive_rules: int = 0
    rules_with_errors: int = 0
    rules_without_effect: int = 0
    conflicting_rules: list[str] = Field(default_factory=list)
    orphaned_rules: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    last_evaluated: Optional[datetime] = None
