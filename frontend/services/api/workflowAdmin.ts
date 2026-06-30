"use client";

import { api } from "@/services/api/client";

// ── Types ──────────────────────────────────────────────────────────

export type WorkflowPackStatus = "draft" | "published" | "archived";
export type WorkflowPackCategory =
  | "legal" | "sales" | "procurement" | "hr" | "privacy"
  | "government" | "healthcare" | "manufacturing" | "financial" | "custom";

export interface WorkflowPackSummary {
  pack_id: string;
  name: string;
  description: string;
  category: WorkflowPackCategory;
  is_built_in: boolean;
  is_favorite: boolean;
  status: WorkflowPackStatus;
  version: number;
  health_score: number;
  usage_count: number;
  running_instances: number;
  stage_count: number;
  warning_count: number;
  last_published: string | null;
  last_published_by: string | null;
  owner: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowVersionSummary {
  version_id: string;
  pack_id: string;
  version_number: number;
  status: WorkflowPackStatus;
  health_score: number;
  stage_count: number;
  rule_count: number;
  published_by: string | null;
  published_at: string | null;
  created_at: string;
  change_summary: string | null;
}

export interface WorkflowPackDetail extends WorkflowPackSummary {
  versions: WorkflowVersionSummary[];
  stages: StageDefinition[];
  rules: RuleDefinition[];
  templates_using: number;
  contracts_running: number;
  contract_types: string[];
  default_for_template: string | null;
  referenced_rule_count: number;
  referenced_action_count: number;
  owner: string;
  industry: string | null;
  region: string | null;
  jurisdiction: string | null;
}

export interface StageDefinition {
  name: string;
  stage_type: "start" | "end" | "approval" | "review" | "automatic" | "condition" | "notification" | "escalation";
  sla_hours?: number;
  calendar_id?: string;
  assignee_role?: string;
  assignee_user?: string;
  resolution_strategy?: string;
  approval_mode?: string;
  transitions?: string[];
  escalation_chain?: EscalationLevel[];
  requires_approval?: boolean;
  min_approvals?: number;
}

export interface EscalationLevel {
  level: number;
  after_hours: number;
  notify_role: string;
}

export interface RuleDefinition {
  rule_id: string;
  name: string;
  logic: Record<string, unknown>;
  priority: number;
  assignee_role: string;
  approval_mode: string;
  resolution_strategy: string;
}

export interface ValidationIssue {
  severity: "error" | "warning";
  code: string;
  stage: string | null;
  message: string;
  suggestion: string;
}

export interface ValidationResult {
  score: number;
  is_valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface ImpactAnalysis {
  template_count: number;
  active_contract_count: number;
  future_contract_count: number;
  departments: string[];
  regions: string[];
}

export interface SimulationInput {
  risk_score: number;
  jurisdiction: string;
  contract_type: string;
  value: number;
  department: string;
  has_redlines: boolean;
}

export interface SimulatedStage {
  name: string;
  stage_type: string;
  sla_hours: number;
  assigned_to: string;
  approval_mode: string;
  resolution_strategy: string;
  resolved_user: string | null;
  candidates: string[];
  selection_reason: string;
  estimated_completion: string;
  matched_rules: string[];
}

export interface SimulationResult {
  stages: SimulatedStage[];
  total_sla_hours: number;
  matched_rules: RuleMatch[];
  skipped_rules: RuleSkip[];
  estimated_completion: string;
}

export interface RuleMatch {
  rule_id: string;
  rule_summary: string;
  reason: string;
}

export interface RuleSkip {
  rule_id: string;
  rule_summary: string;
  reason: string;
}

export interface WorkflowAnalytics {
  volume: {
    running_now: number;
    completed_today: number;
    completed_week: number;
    new_week: number;
    cancelled_week: number;
  };
  performance: {
    avg_completion_hours: number;
    avg_stage_hours: number;
    p95_completion_hours: number;
    p99_completion_hours: number;
    longest_stage: string;
  };
  quality: {
    rejected_rate: number;
    auto_approve_rate: number;
    escalated_rate: number;
    sla_breach_rate: number;
    approval_success_rate: number;
  };
  bottlenecks: {
    stage: string;
    avg_hours: number;
    rejection_rate: number;
  }[];
  most_used: {
    name: string;
    pack_id: string;
    runs: number;
    avg_hours: number;
  }[];
  comparison: {
    pack_id: string;
    name: string;
    running: number;
    avg_time_hours: number;
    sla_breaches: number;
    rejected_rate: number;
  }[];
}

// ── API Calls ──────────────────────────────────────────────────────

export async function fetchWorkflowPacks(params?: {
  category?: string;
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<{ items: WorkflowPackSummary[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set("category", params.category);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  const qs = searchParams.toString();
  const result = await api.get<WorkflowPackSummary[]>(`/workflow-packs${qs ? `?${qs}` : ""}`);
  // Backend returns a plain array; wrap it in the expected shape
  return { items: Array.isArray(result) ? result : [], total: Array.isArray(result) ? result.length : 0 };
}

export async function fetchWorkflowPack(packId: string): Promise<WorkflowPackDetail> {
  return api.get(`/workflow-packs/${packId}`);
}

export async function createWorkflowPack(data: {
  name: string;
  description?: string;
  category: string;
  clone_from?: string;
}): Promise<{ pack_id: string }> {
  return api.post("/workflow-packs", data);
}

export async function updateWorkflowPack(
  packId: string,
  data: Partial<WorkflowPackDetail>
): Promise<WorkflowPackDetail> {
  return api.put(`/workflow-packs/${packId}`, data);
}

export async function deleteWorkflowPack(packId: string): Promise<void> {
  return api.delete(`/workflow-packs/${packId}`);
}

export async function archiveWorkflowPack(packId: string): Promise<{ status: string }> {
  return api.post(`/workflow-packs/${packId}/archive`);
}

export async function restoreWorkflowPack(packId: string): Promise<{ status: string }> {
  return api.post(`/workflow-packs/${packId}/restore`);
}

export async function cloneWorkflowPack(
  packId: string,
  name?: string
): Promise<{ pack_id: string }> {
  return api.post(`/workflow-packs/${packId}/clone`, { name });
}

export async function exportWorkflowPack(packId: string): Promise<Blob> {
  return api.downloadFile(`/workflow-packs/${packId}/export`, `workflow-${packId}.json`);
}

export async function importWorkflowPack(file: File): Promise<{ pack_id: string }> {
  return api.uploadFile("/workflow-packs/import", file);
}

export async function toggleFavorite(packId: string): Promise<{ is_favorite: boolean }> {
  return api.post(`/workflow-packs/${packId}/favorite`);
}

// ── Versions ───────────────────────────────────────────────────────

export async function fetchVersions(packId: string): Promise<WorkflowVersionSummary[]> {
  return api.get(`/workflow-packs/${packId}/versions`);
}

export async function createVersion(
  packId: string,
  data: { stages: StageDefinition[]; rules: RuleDefinition[]; change_summary?: string }
): Promise<{ version_id: string; version_number: number }> {
  return api.post(`/workflow-packs/${packId}/versions`, data);
}

export async function publishVersion(
  packId: string,
  versionId: string,
  data?: { effective_date?: string; change_summary?: string }
): Promise<WorkflowVersionSummary> {
  return api.post(`/workflow-packs/${packId}/versions/${versionId}/publish`, data || {});
}

export async function compareVersions(
  packId: string,
  versionIdA: string,
  versionIdB: string
): Promise<{
  stages_added: string[];
  stages_removed: string[];
  stages_modified: { name: string; changes: string[] }[];
  rules_added: string[];
  rules_removed: string[];
  rules_modified: { name: string; changes: string[] }[];
  health_change: number;
}> {
  return api.get(`/workflow-packs/${packId}/versions/${versionIdA}/compare/${versionIdB}`);
}

// ── Validation & Impact ────────────────────────────────────────────

export async function validateWorkflowPack(
  packId: string,
  versionId: string
): Promise<ValidationResult> {
  return api.get(`/workflow-packs/${packId}/versions/${versionId}/validate`);
}

export async function analyzeImpact(
  packId: string,
  versionId: string
): Promise<ImpactAnalysis> {
  return api.get(`/workflow-packs/${packId}/versions/${versionId}/impact`);
}

// ── Simulation ─────────────────────────────────────────────────────

export async function simulateWorkflow(
  packId: string,
  versionId: string,
  input: SimulationInput
): Promise<SimulationResult> {
  return api.post(`/workflow-packs/${packId}/versions/${versionId}/simulate`, input);
}

// ── Analytics ──────────────────────────────────────────────────────

export async function fetchWorkflowAnalytics(params?: {
  days?: number;
}): Promise<WorkflowAnalytics> {
  const qs = params?.days ? `?days=${params.days}` : "";
  return api.get(`/workflow-analytics${qs}`);
}

export async function fetchPackAnalytics(packId: string): Promise<{
  running_instances: number;
  completed_instances: number;
  avg_completion_hours: number;
  avg_approval_hours: number;
  sla_breach_rate: number;
  rejected_rate: number;
  escalated_rate: number;
  auto_approve_rate: number;
  trend_data: { date: string; completed: number; avg_hours: number }[];
}> {
  return api.get(`/workflow-packs/${packId}/analytics`);
}

// ── Operations / Monitoring ────────────────────────────────────────

export interface InstanceSummary {
  workflow_id: string;
  pack_name: string;
  contract_name: string;
  current_stage: string;
  status: string;
  assigned_to: string | null;
  sla_remaining_hours: number;
  sla_breached: boolean;
  created_at: string;
  updated_at: string;
  version_number: number;
}

export interface InstanceDetail extends InstanceSummary {
  stages: InstanceStage[];
  execution_context: Record<string, unknown>;
  matched_rules: { rule_name: string; matched: boolean }[];
  timeline: TimelineEvent[];
}

export interface InstanceStage {
  step_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  assigned_to: string | null;
  sla_hours: number;
}

export interface TimelineEvent {
  event_type: string;
  actor_id: string;
  timestamp: string;
  details: string;
}

export interface TaskSummary {
  task_id: string;
  workflow_id: string;
  stage_name: string;
  assigned_to: string;
  status: string;
  created_at: string;
  sla_deadline: string;
  sla_remaining_hours: number;
  priority: string;
}

export interface BottleneckData {
  stage_name: string;
  avg_duration_hours: number;
  instance_count: number;
  rejection_rate: number;
  escalation_rate: number;
  queue_length: number;
}

export interface WorkflowHealthRow {
  pack_id: string;
  name: string;
  running: number;
  avg_duration_hours: number;
  failures: number;
  health_score: number;
}

export interface AuditEvent {
  event_id: string;
  workflow_id: string;
  event_type: string;
  actor_id: string;
  timestamp: string;
  details: string;
  stage_name: string | null;
}

export async function fetchInstances(params?: {
  status?: string;
  pack_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
}): Promise<{ items: InstanceSummary[]; total: number }> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.pack_id) qs.set("pack_id", params.pack_id);
  if (params?.search) qs.set("search", params.search);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  return api.get(`/workflow-instances${qs.toString() ? `?${qs}` : ""}`);
}

export async function fetchInstanceDetail(workflowId: string): Promise<InstanceDetail> {
  return api.get(`/workflow-instances/${workflowId}`);
}

export async function fetchTasks(params?: {
  assigned_to?: string;
  status?: string;
}): Promise<TaskSummary[]> {
  const qs = new URLSearchParams();
  if (params?.assigned_to) qs.set("assigned_to", params.assigned_to);
  if (params?.status) qs.set("status", params.status);
  return api.get(`/workflow-tasks${qs.toString() ? `?${qs}` : ""}`);
}

export async function fetchBottlenecks(days?: number): Promise<BottleneckData[]> {
  return api.get(`/workflow-analytics/bottlenecks${days ? `?days=${days}` : ""}`);
}

export async function fetchWorkflowHealth(): Promise<WorkflowHealthRow[]> {
  return api.get("/workflow-analytics/health");
}

export async function fetchAuditEvents(params?: {
  workflow_id?: string;
  event_type?: string;
  limit?: number;
}): Promise<AuditEvent[]> {
  const qs = new URLSearchParams();
  if (params?.workflow_id) qs.set("workflow_id", params.workflow_id);
  if (params?.event_type) qs.set("event_type", params.event_type);
  if (params?.limit) qs.set("limit", String(params.limit));
  return api.get(`/workflow-audit${qs.toString() ? `?${qs}` : ""}`);
}
