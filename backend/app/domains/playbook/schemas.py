"""Legal Playbook + Policy Engine Pydantic v2 schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Playbook Schemas ────────────────────────────────────────────────


class PlaybookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    jurisdiction: Optional[str] = Field(None, max_length=50)
    practice_area: Optional[str] = Field(None, max_length=50)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlaybookUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    jurisdiction: Optional[str] = Field(None, max_length=50)
    practice_area: Optional[str] = Field(None, max_length=50)
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    deviation_thresholds: Optional[dict[str, Any]] = None
    risk_weights: Optional[dict[str, Any]] = None
    risk_levels: Optional[dict[str, Any]] = None


class PlaybookSummary(BaseModel):
    playbook_id: str
    name: str
    description: Optional[str] = None
    jurisdiction: Optional[str] = None
    practice_area: Optional[str] = None
    status: str
    active_version_id: Optional[str] = None
    version_count: int = 1
    tags: list[str] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    updated_at: datetime


class PlaybookDetail(PlaybookSummary):
    metadata: dict[str, Any] = Field(default_factory=dict)
    deviation_thresholds: Optional[dict[str, Any]] = None
    risk_weights: Optional[dict[str, Any]] = None
    risk_levels: Optional[dict[str, Any]] = None
    archived_at: Optional[datetime] = None


class PlaybookVersionCreate(BaseModel):
    version_label: Optional[str] = Field(None, max_length=100)
    change_notes: Optional[str] = Field(None, max_length=2000)


class PlaybookVersionSummary(BaseModel):
    version_id: str
    playbook_id: str
    version_number: int
    version_label: Optional[str] = None
    change_notes: Optional[str] = None
    is_draft: bool = True
    is_active: bool = False
    published_by: Optional[str] = None
    published_at: Optional[datetime] = None
    created_by: str
    created_at: datetime


# ── Clause Standard Schemas ─────────────────────────────────────────


class ClauseStandardCreate(BaseModel):
    category: str
    clause_type: str
    title: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1)
    summary: Optional[str] = Field(None, max_length=1000)
    fallback_clause_ids: list[str] = Field(default_factory=list)
    min_contract_value: Optional[float] = None
    max_contract_value: Optional[float] = None
    applicable_jurisdictions: list[str] = Field(default_factory=list)
    applicable_industries: list[str] = Field(default_factory=list)
    risk_level: str = "medium"
    risk_score: Optional[float] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class ClauseStandardUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    body: Optional[str] = Field(None, min_length=1)
    summary: Optional[str] = Field(None, max_length=1000)
    fallback_clause_ids: Optional[list[str]] = None
    min_contract_value: Optional[float] = None
    max_contract_value: Optional[float] = None
    applicable_jurisdictions: Optional[list[str]] = None
    applicable_industries: Optional[list[str]] = None
    risk_level: Optional[str] = None
    risk_score: Optional[float] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None


class ClauseStandardItem(BaseModel):
    clause_id: str
    playbook_id: str
    category: str
    clause_type: str
    title: str
    body: str
    summary: Optional[str] = None
    fallback_clause_ids: list[str] = Field(default_factory=list)
    min_contract_value: Optional[float] = None
    max_contract_value: Optional[float] = None
    applicable_jurisdictions: list[str] = Field(default_factory=list)
    applicable_industries: list[str] = Field(default_factory=list)
    risk_level: str = "medium"
    risk_score: Optional[float] = None
    tags: list[str] = Field(default_factory=list)
    is_active: bool = True
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


# ── Policy Rule Schemas ─────────────────────────────────────────────


class FallbackRecommendation(BaseModel):
    """A recommended fallback clause for a given clause type."""
    clause_id: str
    playbook_id: str
    category: str
    clause_type: str  # 'approved', 'preferred', 'fallback'
    title: str
    body: str
    summary: Optional[str] = None
    risk_level: str = "medium"
    tags: list[str] = Field(default_factory=list)
    is_active: bool = True


class FallbackRecommendationResponse(BaseModel):
    clause_category: str
    recommendations: list[FallbackRecommendation] = Field(default_factory=list)
    has_approved: bool = False
    has_preferred: bool = False
    has_fallback: bool = False


class RuleCondition(BaseModel):
    operator: str
    field: str
    value: Any = None
    conditions: list[RuleCondition] = Field(default_factory=list)


class PolicyRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    rule_type: str
    priority: int = 100
    is_mandatory: bool = False
    conditions: RuleCondition
    effect: str
    effect_config: dict[str, Any] = Field(default_factory=dict)
    target_clause_id: Optional[str] = None
    target_category: Optional[str] = None
    applicable_jurisdictions: list[str] = Field(default_factory=list)
    applicable_industries: list[str] = Field(default_factory=list)
    min_contract_value: Optional[float] = None
    max_contract_value: Optional[float] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)
    keyword_patterns: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    is_mandatory: Optional[bool] = None
    conditions: Optional[RuleCondition] = None
    effect: Optional[str] = None
    effect_config: Optional[dict[str, Any]] = None
    target_clause_id: Optional[str] = None
    target_category: Optional[str] = None
    applicable_jurisdictions: Optional[list[str]] = None
    applicable_industries: Optional[list[str]] = None
    min_contract_value: Optional[float] = None
    max_contract_value: Optional[float] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    tags: Optional[list[str]] = None
    keyword_patterns: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None


class PolicyRuleItem(BaseModel):
    rule_id: str
    playbook_id: str
    name: str
    description: Optional[str] = None
    rule_type: str
    priority: int = 100
    is_active: bool = True
    is_mandatory: bool = False
    conditions: dict[str, Any]
    effect: str
    effect_config: dict[str, Any] = Field(default_factory=dict)
    target_clause_id: Optional[str] = None
    target_category: Optional[str] = None
    applicable_jurisdictions: list[str] = Field(default_factory=list)
    applicable_industries: list[str] = Field(default_factory=list)
    min_contract_value: Optional[float] = None
    max_contract_value: Optional[float] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)
    keyword_patterns: list[str] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    updated_at: datetime


class PolicyRuleWithPlaybook(PolicyRuleItem):
    """Policy rule enriched with parent playbook metadata for tenant-wide listings."""
    playbook_name: Optional[str] = None
    playbook_status: Optional[str] = None
    playbook_jurisdiction: Optional[str] = None


class TraceabilityChainItem(BaseModel):
    playbook_id: str
    playbook_name: str
    policy_version: str = "1.0"
    playbook_status: Optional[str] = None
    rule_count: int = 0
    clause_requirement_count: int = 0
    finding_count: int = 0
    redline_count: int = 0
    resolved_count: int = 0
    evaluation_count: int = 0
    deviations_found: int = 0


class TraceabilityResponse(BaseModel):
    chains: list[TraceabilityChainItem] = Field(default_factory=list)
    total_findings_linked: int = 0
    total_redlines: int = 0


# ── Evaluation Schemas ──────────────────────────────────────────────


class RuleEvaluationResult(BaseModel):
    rule_id: str
    rule_name: str
    rule_type: str
    effect: str
    violation_triggered: bool = Field(description="True when the rule's conditions triggered a violation")
    priority: int
    details: Optional[str] = None
    deviation_severity: Optional[str] = None


class DeviationItem(BaseModel):
    clause_category: str
    clause_text_snippet: str
    expected: str
    actual: str
    severity: str
    score: float
    rule_id: Optional[str] = None
    recommendation: Optional[str] = None
    fallback_clause_id: Optional[str] = None


class PolicyEvaluationSummary(BaseModel):
    evaluation_id: str
    upload_id: str
    review_id: Optional[str] = None
    playbook_id: Optional[str] = None
    playbook_version_id: Optional[str] = None
    status: str
    total_rules_evaluated: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    deviations_found: int = 0
    mandatory_blocks: int = 0
    approval_required: int = 0
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class PolicyEvaluationDetail(PolicyEvaluationSummary):
    results: list[RuleEvaluationResult] = Field(default_factory=list)
    deviations: list[DeviationItem] = Field(default_factory=list)
    recommendations: list[ClauseRecommendationItem] = Field(default_factory=list)


# ── Approval Threshold Schemas ──────────────────────────────────────


class ApprovalThresholdCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    threshold_type: str
    operator: str = "greater_than"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    target_category: Optional[str] = None
    approval_role: str
    approval_level: int = 1
    fallback_approval_role: Optional[str] = None
    auto_approve: bool = False
    auto_approve_conditions: Optional[dict[str, Any]] = None
    sla_hours: Optional[int] = None
    priority: int = 100


class ApprovalThresholdUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    operator: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    target_category: Optional[str] = None
    approval_role: Optional[str] = None
    approval_level: Optional[int] = None
    fallback_approval_role: Optional[str] = None
    auto_approve: Optional[bool] = None
    auto_approve_conditions: Optional[dict[str, Any]] = None
    sla_hours: Optional[int] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class ApprovalThresholdItem(BaseModel):
    threshold_id: str
    playbook_id: str
    name: str
    description: Optional[str] = None
    threshold_type: str
    operator: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    target_category: Optional[str] = None
    approval_role: str
    approval_level: int = 1
    fallback_approval_role: Optional[str] = None
    auto_approve: bool = False
    sla_hours: Optional[int] = None
    is_active: bool = True
    priority: int = 100
    created_by: str
    created_at: datetime
    updated_at: datetime


# ── Clause Recommendation Schemas ───────────────────────────────────


class ClauseRecommendationItem(BaseModel):
    recommendation_id: str
    clause_id: Optional[str] = None
    clause_category: str
    clause_type: str
    title: str
    body: str
    rationale: Optional[str] = None
    confidence_score: Optional[float] = None
    risk_reduction: Optional[str] = None
    priority: int = 50
    is_applied: bool = False
    deviation_id: Optional[str] = None
    replaces_clause_text: Optional[str] = None
    created_at: datetime


class ClauseRecommendationResponse(BaseModel):
    recommendations: list[ClauseRecommendationItem]
    total: int


# ── Policy Override Schemas ─────────────────────────────────────────


class OverrideRequest(BaseModel):
    evaluation_id: str
    rule_id: Optional[str] = None
    upload_id: str
    review_id: Optional[str] = None
    override_type: str
    status: Optional[str] = None
    justification: str = Field(..., min_length=10, max_length=5000)
    risk_assessment: Optional[str] = Field(None, max_length=3000)
    proposed_alternative: Optional[str] = Field(None, max_length=5000)
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    correlation_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OverrideReview(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    review_notes: Optional[str] = Field(None, max_length=2000)


class OverrideItem(BaseModel):
    override_id: str
    evaluation_id: str
    rule_id: Optional[str] = None
    upload_id: str
    review_id: Optional[str] = None
    override_type: str
    justification: str
    risk_assessment: Optional[str] = None
    proposed_alternative: Optional[str] = None
    status: str
    requested_by: str
    requested_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    correlation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Governance Audit Schemas ────────────────────────────────────────


class GovernanceAuditEventItem(BaseModel):
    event_id: str
    event_type: str
    entity_type: str
    entity_id: str
    actor_id: str
    actor_role: Optional[str] = None
    previous_state: Optional[dict[str, Any]] = None
    new_state: Optional[dict[str, Any]] = None
    change_summary: Optional[str] = None
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    source: str = "api"
    created_at: datetime


# ── AI Policy Context Schemas ───────────────────────────────────────


class PolicyContextInject(BaseModel):
    """Context for injecting playbook policies into AI prompts."""
    playbook_id: str
    upload_id: str
    clause_categories: Optional[list[str]] = None
    include_rules: bool = True
    include_clauses: bool = True
    include_thresholds: bool = False


class PolicyContextResult(BaseModel):
    playbook_name: str
    playbook_version: Optional[str] = None
    applicable_clauses: list[ClauseStandardItem] = Field(default_factory=list)
    applicable_rules: list[PolicyRuleItem] = Field(default_factory=list)
    applicable_thresholds: list[ApprovalThresholdItem] = Field(default_factory=list)
    context_prompt: str = ""


# ── Filter / Query Schemas ──────────────────────────────────────────


# ── Redline Template Schemas ────────────────────────────────────────


class RedlineTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    clause_type: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="general", max_length=100)
    jurisdiction: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    language: str = Field(default="en", max_length=10)
    risk_level: Optional[str] = Field(None, pattern="^(low|medium|high|critical)?$")
    template_text: str = Field(..., min_length=1)
    variables: Optional[dict[str, Any]] = None
    status: str = Field(default="draft", pattern="^(draft|active|retired)$")
    playbook_id: Optional[str] = None
    effective_date: Optional[datetime] = None


class RedlineTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=300)
    clause_type: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    jurisdiction: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=10)
    risk_level: Optional[str] = Field(None, pattern="^(low|medium|high|critical)?$")
    template_text: Optional[str] = Field(None, min_length=1)
    variables: Optional[dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(draft|active|retired)$")
    playbook_id: Optional[str] = None
    effective_date: Optional[datetime] = None


class RedlineTemplateItem(BaseModel):
    template_id: str
    tenant_id: str
    name: str
    clause_type: str
    category: str = "general"
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    language: str = "en"
    risk_level: Optional[str] = None
    template_text: str
    variables: Optional[dict[str, Any]] = None
    version: int = 1
    status: str = "draft"
    playbook_id: Optional[str] = None
    usage_count: int = 0
    accept_rate: float = 0.0
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    effective_date: Optional[datetime] = None
    retired_date: Optional[datetime] = None
    last_used: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TemplateCoverageByClauseType(BaseModel):
    clause_type: str
    label: str
    findings: int = 0
    has_template: bool = False
    coverage_pct: float = 0.0


class TemplateCoverageResponse(BaseModel):
    total_findings: int = 0
    total_clause_types: int = 0
    templates_found: int = 0
    templates_missing: int = 0
    coverage_pct: float = 0.0
    by_clause_type: list[TemplateCoverageByClauseType] = Field(default_factory=list)


class TemplateGenerateRequest(BaseModel):
    clause_type: str = Field(..., min_length=1, max_length=100)
    jurisdiction: Optional[str] = Field(None, max_length=50)
    industry: Optional[str] = Field(None, max_length=100)
    risk_level: Optional[str] = Field(None, pattern="^(low|medium|high|critical)?$")


class TemplateGenerateResponse(BaseModel):
    clause_type: str
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    generated_text: str
    model_used: str
    provider: str


class TemplateFilterParams(BaseModel):
    clause_type: Optional[str] = None
    category: Optional[str] = None
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# ── Filter / Query Schemas ──────────────────────────────────────────


class PlaybookFilterParams(BaseModel):
    status: Optional[str] = None
    jurisdiction: Optional[str] = None
    practice_area: Optional[str] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class ClauseFilterParams(BaseModel):
    category: Optional[str] = None
    clause_type: Optional[str] = None
    risk_level: Optional[str] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class RuleFilterParams(BaseModel):
    rule_type: Optional[str] = None
    effect: Optional[str] = None
    is_active: Optional[bool] = None
    is_mandatory: Optional[bool] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="priority")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")


class EvaluationFilterParams(BaseModel):
    status: Optional[str] = None
    upload_id: Optional[str] = None
    risk_level: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class OverrideFilterParams(BaseModel):
    status: Optional[str] = None
    override_type: Optional[str] = None
    upload_id: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class AuditFilterParams(BaseModel):
    event_type: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    actor_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
