/**
 * Policy API service — Policy-as-Code engine.
 *
 * Sprint 7 Priority 1.
 *
 * Provides typed API client methods for:
 * - Policy CRUD (list, get, create, update, delete)
 * - Policy evaluation (dry-run and live)
 * - Policy version management
 * - Policy audit trail
 * - Policy simulation
 *
 * Backend dependency: app/domains/playbook/ (exists)
 *
 * Usage:
 *   import { policyService } from '@/services/api/policy';
 *   const policies = await policyService.list({ tenant_id: 'tenant-123' });
 *   const result = await policyService.evaluate(policyId, contractId);
 */

"use client";

import { api } from "@/services/api/client";

// ── Types ─────────────────────────────────────────────────────────

export type PolicyEffect = "allow" | "block" | "flag_for_review" | "require_approval";

export type RuleOperator =
  | "equals"
  | "not_equals"
  | "contains"
  | "not_contains"
  | "greater_than"
  | "less_than"
  | "greater_than_or_equal"
  | "less_than_or_equal"
  | "in"
  | "not_in"
  | "matches_regex"
  | "threshold"
  | "exists"
  | "not_exists";

export type ConditionGroupType = "AND" | "OR";

export interface RuleCondition {
  condition_id?: string;
  field: string;
  operator: RuleOperator;
  value: unknown;
  field_type?: "string" | "number" | "boolean" | "date" | "currency" | "enum";
  label?: string;
}

export interface ConditionGroup {
  group_id?: string;
  type: ConditionGroupType;
  conditions: (RuleCondition | ConditionGroup)[];
}

export interface PolicyDefinition {
  policy_id: string;
  name: string;
  description: string;
  scope: "tenant" | "global";
  tenant_id?: string;
  rules: ConditionGroup;
  effect: PolicyEffect;
  priority: number;
  enabled: boolean;
  version: number;
  category: string;
  tags: string[];
  valid_from: string | null;
  valid_until: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface PolicyCreateRequest {
  name: string;
  description: string;
  scope: "tenant" | "global";
  tenant_id?: string;
  rules: ConditionGroup;
  effect: PolicyEffect;
  priority?: number;
  category?: string;
  tags?: string[];
  valid_from?: string;
  valid_until?: string;
}

export interface PolicyEvaluationRequest {
  policy_id: string;
  contract_id: string;
  simulation_mode?: boolean;
  context?: Record<string, unknown>;
}

export interface TriggeredRule {
  condition_id: string;
  field: string;
  operator: RuleOperator;
  expected_value: unknown;
  actual_value: unknown;
  matched: boolean;
  contribution: number;
}

export interface PolicyEvaluationResult {
  evaluation_id: string;
  policy_id: string;
  policy_name: string;
  contract_id: string;
  contract_name?: string;
  triggered_rules: TriggeredRule[];
  overall_effect: PolicyEffect;
  passed: boolean;
  explanation: string;
  simulation_mode: boolean;
  evaluated_at: string;
  execution_time_ms: number;
}

export interface PolicyVersion {
  version_id: string;
  policy_id: string;
  version_number: number;
  snapshot: PolicyDefinition;
  change_summary: string;
  created_by: string;
  created_at: string;
}

export interface PolicyAuditEntry {
  audit_id: string;
  policy_id: string;
  action: "created" | "updated" | "deleted" | "enabled" | "disabled" | "evaluated" | "simulated";
  actor: string;
  details: string;
  timestamp: string;
}

// ── Query Key Factory ─────────────────────────────────────────────

export const policyKeys = {
  all: ["policies"] as const,
  lists: () => [...policyKeys.all, "list"] as const,
  list: (params?: { tenant_id?: string; scope?: string; enabled?: boolean; category?: string }) =>
    [...policyKeys.lists(), params] as const,
  details: () => [...policyKeys.all, "detail"] as const,
  detail: (id: string) => [...policyKeys.details(), id] as const,
  versions: (id: string) => [...policyKeys.all, "versions", id] as const,
  evaluations: (id: string) => [...policyKeys.all, "evaluations", id] as const,
  audit: (id: string) => [...policyKeys.all, "audit", id] as const,
};

// ── Service ───────────────────────────────────────────────────────

export const policyService = {
  /** List policies with optional filters — maps to playbooks list endpoint */
  list: (params?: {
    tenant_id?: string;
    scope?: string;
    enabled?: boolean;
    category?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.tenant_id) query.set("tenant_id", params.tenant_id);
    if (params?.scope) query.set("scope", params.scope);
    if (params?.enabled !== undefined) query.set("enabled", String(params.enabled));
    if (params?.category) query.set("category", params.category);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const qs = query.toString();
    return api.get<{ data: PolicyDefinition[]; pagination: Record<string, unknown> }>(
      qs ? `/playbooks/?${qs}` : "/playbooks/",
    );
  },

  /** Get a single policy by ID — maps to playbooks get endpoint */
  get: (policyId: string) => api.get<PolicyDefinition>(`/playbooks/${policyId}`),

  /** Create a new policy — maps to playbooks create endpoint */
  create: (body: PolicyCreateRequest) =>
    api.post<PolicyDefinition>("/playbooks/", body, { idempotencyKey: api.generateIdempotencyKey() }),

  /** Update an existing policy — maps to playbooks update endpoint */
  update: (policyId: string, body: Partial<PolicyCreateRequest>) =>
    api.patch<PolicyDefinition>(`/playbooks/${policyId}`, body),

  /** List all policy rules across playbooks for the tenant */
  listRules: (params?: {
    search?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.is_active !== undefined) query.set("is_active", String(params.is_active));
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const qs = query.toString();
    return api.get<{ data: Record<string, unknown>[]; pagination: Record<string, unknown> }>(
      qs ? `/playbooks/rules?${qs}` : "/playbooks/rules",
    );
  },

  /** Policy traceability aggregates (policy → finding → redline chains) */
  getTraceability: () =>
    api.get<{
      chains: Array<{
        playbook_id: string;
        playbook_name: string;
        policy_version: string;
        rule_count: number;
        clause_requirement_count: number;
        finding_count: number;
        redline_count: number;
        resolved_count: number;
        evaluation_count: number;
        deviations_found: number;
      }>;
      total_findings_linked: number;
      total_redlines: number;
    }>("/playbooks/traceability"),

  /** Delete a policy — maps to playbooks archive endpoint */
  delete: (policyId: string) => api.post(`/playbooks/${policyId}/archive`),

  /** Toggle policy enabled/disabled */
  toggle: (policyId: string, enabled: boolean) =>
    api.post<PolicyDefinition>(`/playbooks/${policyId}/toggle`, { enabled }),

  /** Evaluate a policy against a contract (live) — maps to playbooks evaluate endpoint */
  evaluate: (body: PolicyEvaluationRequest) =>
    api.post<PolicyEvaluationResult>("/playbooks/evaluate", body, { idempotencyKey: api.generateIdempotencyKey() }),

  /** Simulate a policy change without saving (dry-run) — maps to policy simulate endpoint */
  simulate: (body: PolicyEvaluationRequest & { proposed_rules: ConditionGroup }) =>
    api.post<PolicyEvaluationResult>("/policy/dry-run", body),

  /** Run a what-if policy simulation against a hypothetical contract profile */
  runSimulation: (body: {
    playbook_id: string;
    name?: string;
    description?: string;
    contract_profile: {
      contract_value?: number;
      jurisdiction?: string;
      industry?: string;
      counterparty?: string;
      risk_score?: number;
      clauses?: Array<{ category: string; text: string; text_snippet?: string; confidence?: number }>;
      findings?: Array<{ severity?: string; clause_type?: string; title?: string; description?: string }>;
    };
    rule_overrides?: Array<{ rule_id: string; override_effect?: string; override_conditions?: Record<string, unknown>; is_active?: boolean }>;
    include_recommendations?: boolean;
    dry_run?: boolean;
  }) => api.post<{
    simulation_id: string;
    playbook_id: string;
    name: string;
    description?: string;
    results: Array<{
      rule_id: string;
      rule_name: string;
      rule_type: string;
      effect: string;
      matched: boolean;
      priority: number;
      details?: string;
      deviation_severity?: string;
      was_overridden: boolean;
    }>;
    deviations: Array<{ clause_category: string; severity: string; score: number; expected: string; actual: string; recommendation?: string }>;
    total_rules: number;
    rules_passed: number;
    rules_failed: number;
    deviations_found: number;
    mandatory_blocks: number;
    approval_required: number;
    risk_score?: number;
    risk_level?: string;
  }>("/policy/simulate", body),

  /** Get policy version history — maps to playbooks versions endpoint */
  listVersions: (policyId: string) =>
    api.get<{ data: PolicyVersion[] }>(`/playbooks/${policyId}/versions`),

  /** Rollback to a specific version — maps to playbooks rollback endpoint */
  rollback: (policyId: string, versionNumber: number) =>
    api.post<PolicyDefinition>(`/playbooks/${policyId}/rollback/${versionNumber}`),

  /** Get policy audit trail — maps to playbooks audit endpoint */
  getAuditLog: (policyId: string) =>
    api.get<{ data: PolicyAuditEntry[] }>(`/playbooks/${policyId}/audit`),

  /** Bulk evaluate multiple policies against a contract — maps to playbooks evaluate endpoint */
  bulkEvaluate: (contractId: string, options?: { tenant_id?: string; simulation_mode?: boolean }) =>
    api.post<{ results: PolicyEvaluationResult[]; summary: { passed: number; failed: number; total: number } }>(
      "/playbooks/evaluate",
      { contract_id: contractId, ...options },
    ),

  /** Get policy health check — maps to policy health endpoint */
  getHealth: (playbookId: string) =>
    api.get<Record<string, unknown>>(`/policy/playbooks/${playbookId}/health`),

  /** Get policy rule graph — maps to policy graph endpoint */
  getRuleGraph: (playbookId: string) =>
    api.get<Record<string, unknown>>(`/policy/playbooks/${playbookId}/graph`),

  /** Get impact analysis — maps to policy impact-analysis endpoint */
  getImpactAnalysis: (playbookId: string) =>
    api.post<Record<string, unknown>>(`/policy/playbooks/${playbookId}/impact-analysis`),

  /** List policy overrides — maps to playbooks overrides endpoint */
  listOverrides: (params?: { status?: string }) => {
    const query = params?.status ? `?status=${params.status}` : "";
    return api.get<{ data: Record<string, unknown>[] }>(`/playbooks/overrides${query}`);
  },
};
