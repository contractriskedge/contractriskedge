"""Tenant Configuration Framework schemas — feature flags, policy packs, custom thresholds."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────


class FeatureFlagScope(str, Enum):
    GLOBAL = "global"
    TENANT = "tenant"
    BUSINESS_UNIT = "business_unit"
    USER = "user"
    ROLE = "role"


class FeatureFlagState(str, Enum):
    DEVELOPMENT = "development"
    BETA = "beta"
    GENERAL_AVAILABILITY = "general_availability"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class RolloutStrategy(str, Enum):
    ALL_OR_NOTHING = "all_or_nothing"
    PERCENTAGE = "percentage"
    TENANT_WHITELIST = "tenant_whitelist"
    PLAN_TIER = "plan_tier"
    CUSTOM = "custom"


class PolicyPackScope(str, Enum):
    GLOBAL = "global"
    REGION = "region"
    INDUSTRY = "industry"
    TENANT = "tenant"
    BUSINESS_UNIT = "business_unit"


class ComplianceRegion(str, Enum):
    US_FEDERAL = "us_federal"
    US_STATE = "us_state"
    EU = "eu"
    UK = "uk"
    APAC = "apac"
    LATAM = "latam"
    GLOBAL = "global"


# ── Feature Flags ───────────────────────────────────────────────────


class FeatureFlagDefinition(BaseModel):
    """Definition of a feature flag."""
    flag_key: str
    name: str
    description: str = ""
    scope: FeatureFlagScope = FeatureFlagScope.GLOBAL
    state: FeatureFlagState = FeatureFlagState.DEVELOPMENT
    rollout_strategy: RolloutStrategy = RolloutStrategy.ALL_OR_NOTHING
    default_enabled: bool = False
    requires_permission: Optional[str] = None
    dependencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeatureFlagOverride(BaseModel):
    """Per-tenant or per-user override for a feature flag."""
    override_id: str = ""
    flag_key: str
    target_type: str  # 'tenant', 'business_unit', 'user', 'role'
    target_id: str
    enabled: bool
    reason: str = ""
    expires_at: Optional[datetime] = None
    created_by: str = ""
    created_at: datetime


class FeatureFlagEvaluation(BaseModel):
    """Result of evaluating a feature flag for a given context."""
    flag_key: str
    enabled: bool
    source: str = "default"  # 'default', 'tenant_override', 'user_override', 'rollout'
    reason: str = ""
    evaluated_at: datetime


class FeatureFlagCreate(BaseModel):
    flag_key: str = Field(..., min_length=1, max_length=200, pattern=r"^[a-z][a-z0-9_]+$")
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    scope: FeatureFlagScope = FeatureFlagScope.GLOBAL
    state: FeatureFlagState = FeatureFlagState.DEVELOPMENT
    rollout_strategy: RolloutStrategy = RolloutStrategy.ALL_OR_NOTHING
    default_enabled: bool = False
    requires_permission: Optional[str] = None
    dependencies: list[str] = Field(default_factory=list)


class FeatureFlagUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    state: Optional[FeatureFlagState] = None
    rollout_strategy: Optional[RolloutStrategy] = None
    default_enabled: Optional[bool] = None
    requires_permission: Optional[str] = None
    dependencies: Optional[list[str]] = None


class FeatureFlagResponse(BaseModel):
    flag_key: str
    name: str
    description: str = ""
    scope: FeatureFlagScope
    state: FeatureFlagState
    rollout_strategy: RolloutStrategy
    default_enabled: bool = False
    requires_permission: Optional[str] = None
    dependencies: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_by: str = ""
    created_at: datetime
    updated_at: datetime


class FeatureOverrideCreate(BaseModel):
    flag_key: str
    target_type: str
    target_id: str
    enabled: bool
    reason: str = ""
    expires_at: Optional[datetime] = None


# ── Tenant Policy Packs ─────────────────────────────────────────────


class PolicyPackCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    scope: PolicyPackScope = PolicyPackScope.TENANT
    region: Optional[ComplianceRegion] = None
    industry: Optional[str] = None
    jurisdiction: Optional[str] = None
    playbook_id: Optional[str] = None
    rule_overrides: list[PolicyPackRuleOverride] = Field(default_factory=list)
    threshold_overrides: list[PolicyPackThresholdOverride] = Field(default_factory=list)
    clause_overrides: list[PolicyPackClauseOverride] = Field(default_factory=list)
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyPackRuleOverride(BaseModel):
    rule_id: str
    override_effect: Optional[str] = None
    override_priority: Optional[int] = None
    is_active: Optional[bool] = None
    effect_config_overrides: Optional[dict[str, Any]] = None


class PolicyPackThresholdOverride(BaseModel):
    threshold_id: str
    override_min_value: Optional[float] = None
    override_max_value: Optional[float] = None
    override_approval_role: Optional[str] = None
    override_approval_level: Optional[int] = None


class PolicyPackClauseOverride(BaseModel):
    clause_id: str
    override_body: Optional[str] = None
    override_risk_level: Optional[str] = None
    is_active: Optional[bool] = None


class PolicyPackResponse(BaseModel):
    pack_id: str
    name: str
    description: Optional[str] = None
    scope: PolicyPackScope
    region: Optional[ComplianceRegion] = None
    industry: Optional[str] = None
    jurisdiction: Optional[str] = None
    playbook_id: Optional[str] = None
    rule_overrides: list[PolicyPackRuleOverride] = Field(default_factory=list)
    threshold_overrides: list[PolicyPackThresholdOverride] = Field(default_factory=list)
    clause_overrides: list[PolicyPackClauseOverride] = Field(default_factory=list)
    is_active: bool = True
    version: int = 1
    created_by: str = ""
    created_at: datetime
    updated_at: datetime


class PolicyPackAssignment(BaseModel):
    """Assignment of a policy pack to a tenant or business unit."""
    assignment_id: str = ""
    pack_id: str
    tenant_id: str
    business_unit: Optional[str] = None
    is_active: bool = True
    assigned_by: str = ""
    assigned_at: datetime
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


# ── Tenant Scoring Overrides ────────────────────────────────────────


class ScoringOverrideCreate(BaseModel):
    clause_type: str
    override_severity: Optional[str] = None
    override_risk_weight: Optional[float] = Field(None, ge=0.0, le=2.0)
    override_risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: bool = True
    reason: str = ""
    applies_to_business_units: Optional[list[str]] = None


class ScoringOverrideResponse(BaseModel):
    override_id: str
    tenant_id: str
    clause_type: str
    override_severity: Optional[str] = None
    override_risk_weight: Optional[float] = None
    override_risk_score: Optional[float] = None
    is_active: bool = True
    reason: str = ""
    applies_to_business_units: list[str] = Field(default_factory=list)
    created_by: str = ""
    created_at: datetime
    updated_at: datetime


# ── Regional Compliance Packs ───────────────────────────────────────


class CompliancePackCreate(BaseModel):
    region: ComplianceRegion
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    regulations: list[ComplianceRegulationRef] = Field(default_factory=list)
    required_clause_categories: list[str] = Field(default_factory=list)
    forbidden_clause_categories: list[str] = Field(default_factory=list)
    jurisdiction_rules: list[JurisdictionRule] = Field(default_factory=list)
    is_active: bool = True


class ComplianceRegulationRef(BaseModel):
    regulation_key: str  # e.g., 'gdpr', 'ccpa', 'hipaa'
    provisions: list[str] = Field(default_factory=list)
    severity_if_missing: str = "high"


class JurisdictionRule(BaseModel):
    clause_category: str
    required_language: str = ""
    forbidden_language: list[str] = Field(default_factory=list)
    min_standard: str = ""


class CompliancePackResponse(BaseModel):
    pack_id: str
    region: ComplianceRegion
    name: str
    description: Optional[str] = None
    regulations: list[ComplianceRegulationRef] = Field(default_factory=list)
    required_clause_categories: list[str] = Field(default_factory=list)
    forbidden_clause_categories: list[str] = Field(default_factory=list)
    jurisdiction_rules: list[JurisdictionRule] = Field(default_factory=list)
    is_active: bool = True
    version: int = 1
    created_by: str = ""
    created_at: datetime
    updated_at: datetime


# ── Tenant Configuration Dashboard ──────────────────────────────────


class TenantConfigurationSummary(BaseModel):
    """Summary of a tenant's full configuration."""
    tenant_id: str
    tenant_name: str = ""
    plan: str = ""
    feature_flags: list[FeatureFlagEvaluation] = Field(default_factory=list)
    active_policy_packs: list[PolicyPackResponse] = Field(default_factory=list)
    scoring_overrides: list[ScoringOverrideResponse] = Field(default_factory=list)
    compliance_packs: list[CompliancePackResponse] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)
    business_units: list[str] = Field(default_factory=list)
    configuration_version: int = 0
    updated_at: Optional[datetime] = None
