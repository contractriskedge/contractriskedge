/**
 * Tenant Customization API service — tenant configuration, feature flags, branding.
 *
 * Maps frontend calls to actual backend routes:
 *   - Tenant settings → /api/v1/admin/settings (GET/PUT)
 *   - Feature flags → /api/v1/tenant-config/features/* (GET/POST/DELETE)
 *   - Policy packs → /api/v1/tenant-config/policy-packs (GET/POST/DELETE)
 *   - Compliance packs → /api/v1/tenant-config/compliance-packs (GET/POST)
 *   - Scoring overrides → /api/v1/tenant-config/scoring-overrides (GET/POST/DELETE)
 *   - Config summary → /api/v1/tenant-config/summary (GET)
 */

"use client";

import { api } from "@/services/api/client";

// ── Types ─────────────────────────────────────────────────────────

export interface TenantBranding {
  logo_url: string | null;
  favicon_url: string | null;
  primary_color: string;
  accent_color: string;
  font_family?: string;
  custom_css?: string;
}

export interface WorkflowStep {
  step_id: string;
  name: string;
  type: "review" | "approval" | "escalation" | "notification" | "webhook" | "delay";
  config: Record<string, unknown>;
  timeout_hours: number;
  assignee_role?: string;
  order: number;
}

export interface WorkflowDefinition {
  workflow_id: string;
  name: string;
  description: string;
  trigger: "upload" | "status_change" | "schedule" | "manual";
  steps: WorkflowStep[];
  enabled: boolean;
  version: number;
}

export interface RoutingRule {
  rule_id: string;
  name: string;
  criteria: Record<string, unknown>;
  target_role: string;
  priority: number;
  fallback_role?: string;
}

export interface TenantConfiguration {
  tenant_id: string;
  branding: TenantBranding;
  features: Record<string, boolean>;
  risk_weights: Record<string, number>;
  workflows: WorkflowDefinition[];
  compliance_packs: string[];
  routing_rules: RoutingRule[];
  custom_fields: Record<string, unknown>;
  max_users: number;
  storage_limit_bytes: number;
  updated_at: string;
}

// ── Backend-aligned types ─────────────────────────────────────────

export interface TenantSettingsResponse {
  brand_name: string | null;
  brand_logo_url: string | null;
  brand_primary_color: string;
  brand_accent_color: string;
  ai_model: string;
  ai_temperature: number;
  ai_max_tokens: number;
  ai_embedding_model: string;
  ai_token_budget_daily: number;
  ai_token_budget_monthly: number;
  risk_threshold_critical: number;
  risk_threshold_high: number;
  risk_threshold_medium: number;
  sla_critical_hours: number;
  sla_high_hours: number;
  sla_medium_hours: number;
  sla_low_hours: number;
  default_notification_channel: string;
  email_redirect_enabled: boolean;
  email_redirect_to: string | null;
  features_enabled: Record<string, boolean>;
  created_at: string;
  updated_at: string;
}

export interface TenantSettingsUpdate {
  brand_name?: string;
  brand_logo_url?: string | null;
  brand_primary_color?: string;
  brand_accent_color?: string;
  ai_model?: string;
  ai_temperature?: number;
  ai_max_tokens?: number;
  risk_threshold_critical?: number;
  risk_threshold_high?: number;
  risk_threshold_medium?: number;
  sla_critical_hours?: number;
  sla_high_hours?: number;
  sla_medium_hours?: number;
  sla_low_hours?: number;
  features_enabled?: Record<string, boolean>;
  email_redirect_enabled?: boolean;
  email_redirect_to?: string | null;
}

export interface FeatureFlagDefinition {
  flag_key: string;
  name: string;
  description: string;
  scope: string;
  state: string;
  rollout_strategy: string;
  default_enabled: boolean;
  requires_permission: string | null;
  dependencies: string[];
}

export interface FeatureFlagEvaluation {
  flag_key: string;
  enabled: boolean;
  source: string;
  reason: string;
  evaluated_at: string;
}

export interface FeatureFlagOverride {
  override_id: string;
  flag_key: string;
  target_type: string;
  target_id: string;
  enabled: boolean;
  reason: string;
  expires_at: string | null;
  created_by: string;
  created_at: string;
}

export interface FeatureOverrideCreate {
  flag_key: string;
  target_type: string;
  target_id: string;
  enabled: boolean;
  reason?: string;
  expires_at?: string | null;
}

// ── Policy Pack Types ─────────────────────────────────────────────

export interface PolicyPackRuleOverride {
  rule_id: string;
  override_effect?: string | null;
  override_priority?: number | null;
  is_active?: boolean | null;
  effect_config_overrides?: Record<string, unknown> | null;
}

export interface PolicyPackThresholdOverride {
  threshold_id: string;
  override_min_value?: number | null;
  override_max_value?: number | null;
  override_approval_role?: string | null;
  override_approval_level?: number | null;
}

export interface PolicyPackClauseOverride {
  clause_id: string;
  override_body?: string | null;
  override_risk_level?: string | null;
  is_active?: boolean | null;
}

export interface PolicyPackResponse {
  pack_id: string;
  name: string;
  description?: string | null;
  scope: string;
  region?: string | null;
  industry?: string | null;
  jurisdiction?: string | null;
  playbook_id?: string | null;
  rule_overrides: PolicyPackRuleOverride[];
  threshold_overrides: PolicyPackThresholdOverride[];
  clause_overrides: PolicyPackClauseOverride[];
  is_active: boolean;
  version: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface PolicyPackCreate {
  name: string;
  description?: string | null;
  scope?: string;
  region?: string | null;
  industry?: string | null;
  jurisdiction?: string | null;
  playbook_id?: string | null;
  rule_overrides?: PolicyPackRuleOverride[];
  threshold_overrides?: PolicyPackThresholdOverride[];
  clause_overrides?: PolicyPackClauseOverride[];
  is_active?: boolean;
}

// ── Scoring Override Types ────────────────────────────────────────

export interface ScoringOverrideResponse {
  override_id: string;
  tenant_id: string;
  clause_type: string;
  override_severity?: string | null;
  override_risk_weight?: number | null;
  override_risk_score?: number | null;
  is_active: boolean;
  reason: string;
  applies_to_business_units: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ScoringOverrideCreate {
  clause_type: string;
  override_severity?: string | null;
  override_risk_weight?: number | null;
  override_risk_score?: number | null;
  is_active?: boolean;
  reason?: string;
  applies_to_business_units?: string[] | null;
}

// ── Compliance Pack Types ─────────────────────────────────────────

export interface ComplianceRegulationRef {
  regulation_key: string;
  provisions?: string[];
  severity_if_missing?: string;
}

export interface JurisdictionRule {
  clause_category: string;
  required_language?: string;
  forbidden_language?: string[];
  min_standard?: string;
}

export interface CompliancePackResponse {
  pack_id: string;
  region: string;
  name: string;
  description?: string | null;
  regulations: ComplianceRegulationRef[];
  required_clause_categories: string[];
  forbidden_clause_categories: string[];
  jurisdiction_rules: JurisdictionRule[];
  is_active: boolean;
  version: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CompliancePackCreate {
  region: string;
  name: string;
  description?: string | null;
  regulations?: ComplianceRegulationRef[];
  required_clause_categories?: string[];
  forbidden_clause_categories?: string[];
  jurisdiction_rules?: JurisdictionRule[];
  is_active?: boolean;
}

// ── Tenant Summary Types ──────────────────────────────────────────

export interface TenantSummary {
  tenant_id: string;
  tenant_name: string;
  plan: string;
  feature_flags: FeatureFlagEvaluation[];
  active_policy_packs: PolicyPackResponse[];
  scoring_overrides: ScoringOverrideResponse[];
  compliance_packs: CompliancePackResponse[];
  settings: Record<string, unknown>;
  business_units: string[];
  configuration_version: number;
  updated_at: string | null;
}

// ── Query Key Factory ─────────────────────────────────────────────

export const tenantKeys = {
  all: ["tenant"] as const,
  config: (tenantId: string) => [...tenantKeys.all, "config", tenantId] as const,
  features: (tenantId: string) => [...tenantKeys.all, "features", tenantId] as const,
  featureDefinitions: () => [...tenantKeys.all, "feature-definitions"] as const,
  policyPacks: () => [...tenantKeys.all, "policy-packs"] as const,
  scoringOverrides: () => [...tenantKeys.all, "scoring-overrides"] as const,
  compliancePacks: () => [...tenantKeys.all, "compliance-packs"] as const,
  summary: () => [...tenantKeys.all, "summary"] as const,
  workflows: (tenantId: string) => [...tenantKeys.all, "workflows", tenantId] as const,
};

// ── Service ───────────────────────────────────────────────────────

export const tenantService = {
  /** Get tenant settings (branding, AI, risk thresholds, SLA) */
  getSettings: () =>
    api.get<TenantSettingsResponse>(`/admin/settings`),

  /** Update tenant settings */
  updateSettings: (settings: TenantSettingsUpdate) =>
    api.put<TenantSettingsResponse>(`/admin/settings`, settings),

  /** Get feature flag definitions */
  getFeatureDefinitions: () =>
    api.get<FeatureFlagDefinition[]>(`/tenant-config/features/definitions`),

  /** Evaluate all feature flags for the current context */
  evaluateFeatures: () =>
    api.get<FeatureFlagEvaluation[]>(`/tenant-config/features/evaluate`),

  /** Evaluate a single feature flag */
  evaluateFeature: (flagKey: string) =>
    api.get<FeatureFlagEvaluation>(`/tenant-config/features/evaluate/${flagKey}`),

  /** Create or update a feature flag override */
  setFeatureOverride: (override: FeatureOverrideCreate) =>
    api.post<FeatureFlagOverride>(`/tenant-config/features/overrides`, override),

  /** Delete a feature flag override */
  deleteFeatureOverride: (flagKey: string, targetType: string, targetId: string) =>
    api.delete(`/tenant-config/features/overrides/${flagKey}/${targetType}/${targetId}`),

  // ── Policy Packs ────────────────────────────────────────────────

  /** List all policy packs */
  getPolicyPacks: () =>
    api.get<PolicyPackResponse[]>(`/tenant-config/policy-packs`),

  /** Get a single policy pack */
  getPolicyPack: (packId: string) =>
    api.get<PolicyPackResponse>(`/tenant-config/policy-packs/${packId}`),

  /** Create a policy pack */
  createPolicyPack: (pack: PolicyPackCreate) =>
    api.post<PolicyPackResponse>(`/tenant-config/policy-packs`, pack),

  /** Delete a policy pack */
  deletePolicyPack: (packId: string) =>
    api.delete(`/tenant-config/policy-packs/${packId}`),

  // ── Scoring Overrides ───────────────────────────────────────────

  /** List all scoring overrides */
  getScoringOverrides: () =>
    api.get<ScoringOverrideResponse[]>(`/tenant-config/scoring-overrides`),

  /** Create a scoring override */
  createScoringOverride: (override: ScoringOverrideCreate) =>
    api.post<ScoringOverrideResponse>(`/tenant-config/scoring-overrides`, override),

  /** Delete a scoring override */
  deleteScoringOverride: (overrideId: string) =>
    api.delete(`/tenant-config/scoring-overrides/${overrideId}`),

  // ── Compliance Packs ────────────────────────────────────────────

  /** List all compliance packs */
  getCompliancePacks: () =>
    api.get<CompliancePackResponse[]>(`/tenant-config/compliance-packs`),

  /** Create a compliance pack */
  createCompliancePack: (pack: CompliancePackCreate) =>
    api.post<CompliancePackResponse>(`/tenant-config/compliance-packs`, pack),

  // ── Summary ─────────────────────────────────────────────────────

  /** Get tenant configuration summary */
  getConfigSummary: () =>
    api.get<TenantSummary>(`/tenant-config/summary`),
};
