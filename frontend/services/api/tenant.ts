/**
 * Tenant Customization API service — tenant configuration, feature flags, branding.
 *
 * Sprint 7 Priority 5.
 *
 * Provides typed API client methods for:
 * - Tenant configuration (branding, risk weights, workflows)
 * - Feature flag management with tenant overrides
 * - Custom risk weight configuration
 * - Workflow definition per tenant
 * - Compliance pack registry
 * - White-label branding
 *
 * Usage:
 *   import { tenantService } from '@/services/api/tenant';
 *   const config = await tenantService.getConfig('tenant-123');
 *   await tenantService.updateBranding('tenant-123', { logo: '...', primary_color: '#...' });
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

export interface CompliancePack {
  pack_id: string;
  name: string;
  jurisdiction: string;
  regulations: string[];
  clause_requirements: Record<string, string>[];
  version: string;
  enabled: boolean;
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

export interface FeatureFlag {
  flag_id: string;
  key: string;
  name: string;
  description: string;
  default_value: boolean;
  tenant_overrides: Record<string, boolean>;
  category: string;
  dependencies: string[];
}

// ── Query Key Factory ─────────────────────────────────────────────

export const tenantKeys = {
  all: ["tenant"] as const,
  config: (tenantId: string) => [...tenantKeys.all, "config", tenantId] as const,
  features: (tenantId: string) => [...tenantKeys.all, "features", tenantId] as const,
  compliancePacks: () => [...tenantKeys.all, "compliance-packs"] as const,
  workflows: (tenantId: string) => [...tenantKeys.all, "workflows", tenantId] as const,
};

// ── Service ───────────────────────────────────────────────────────

export const tenantService = {
  /** Get tenant configuration */
  getConfig: (tenantId: string) =>
    api.get<TenantConfiguration>(`/tenants/${tenantId}/config`),

  /** Update tenant branding */
  updateBranding: (tenantId: string, branding: Partial<TenantBranding>) =>
    api.put<TenantBranding>(`/tenants/${tenantId}/branding`, branding),

  /** Update tenant risk weights */
  updateRiskWeights: (tenantId: string, weights: Record<string, number>) =>
    api.put<{ risk_weights: Record<string, number> }>(`/tenants/${tenantId}/risk-weights`, { risk_weights: weights }),

  /** Get feature flags for a tenant */
  getFeatures: (tenantId: string) =>
    api.get<{ data: FeatureFlag[] }>(`/tenants/${tenantId}/features`),

  /** Update a feature flag override for a tenant */
  updateFeatureOverride: (tenantId: string, flagKey: string, value: boolean) =>
    api.put<FeatureFlag>(`/tenants/${tenantId}/features/${flagKey}`, { value }),

  /** Get tenant workflows */
  getWorkflows: (tenantId: string) =>
    api.get<{ data: WorkflowDefinition[] }>(`/tenants/${tenantId}/workflows`),

  /** Create or update a workflow for a tenant */
  upsertWorkflow: (tenantId: string, workflow: WorkflowDefinition) =>
    api.post<WorkflowDefinition>(`/tenants/${tenantId}/workflows`, workflow, { idempotencyKey: api.generateIdempotencyKey() }),

  /** Get available compliance packs */
  getCompliancePacks: () =>
    api.get<{ data: CompliancePack[] }>("/compliance-packs"),

  /** Enable a compliance pack for a tenant */
  enableCompliancePack: (tenantId: string, packId: string) =>
    api.post(`/tenants/${tenantId}/compliance-packs/${packId}/enable`),

  /** Disable a compliance pack for a tenant */
  disableCompliancePack: (tenantId: string, packId: string) =>
    api.post(`/tenants/${tenantId}/compliance-packs/${packId}/disable`),

  /** Get tenant routing rules */
  getRoutingRules: (tenantId: string) =>
    api.get<{ data: RoutingRule[] }>(`/tenants/${tenantId}/routing-rules`),

  /** Update tenant routing rules */
  updateRoutingRules: (tenantId: string, rules: RoutingRule[]) =>
    api.put<{ data: RoutingRule[] }>(`/tenants/${tenantId}/routing-rules`, { rules }),
};
