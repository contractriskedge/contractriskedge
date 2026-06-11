/**
 * Obligation Management API service — obligation tracking, SLA monitoring,
 * vendor performance, financial exposure, risk analysis, and audit logging.
 *
 * Maps to backend endpoints under `/api/v1/obligations/`.
 *
 * Provides typed API client methods for:
 * - Obligation CRUD (list, get, create, update, delete)
 * - KPIs, calendar, upcoming, overdue
 * - Financial exposure, penalties, value at risk
 * - Risk analysis, escalations, anomalies, AI review
 * - Reminders, escalations, notification history
 * - SLA performance, breaches, vendor risk, predictions
 *
 * Usage:
 *   import { obligationsService } from '@/services/api/obligations';
 *   const obligations = await obligationsService.listObligations({ page: 1, pageSize: 20 });
 *   const kpis = await obligationsService.getKpis();
 *   const review = await obligationsService.aiReview({ obligation_id: '...', include_predictions: true });
 */

"use client";

import { api } from "@/services/api/client";

// ── Enums / Literal Types ──────────────────────────────────────────

export type SortOrder = "asc" | "desc";

// ── Request DTOs (camelCase for frontend use) ──────────────────────

export interface ObligationCreateRequest {
  name: string;
  description?: string;
  obligationType: string;
  status?: string;
  contractId?: string;
  contractUuidId?: string;
  contractName?: string;
  vendor?: string;
  owner?: string;
  assignee?: string;
  dueDate?: string;
  riskScore?: number;
  riskLevel?: string;
  financialImpact?: number;
  currency?: string;
  clauseReference?: string;
  department?: string;
  businessUnit?: string;
  geography?: string;
  isRecurring?: boolean;
  recurrencePattern?: string;
  notes?: string;
  tags?: string[];
}

export interface ObligationUpdateRequest {
  name?: string;
  description?: string;
  obligationType?: string;
  status?: string;
  contractId?: string;
  contractName?: string;
  vendor?: string;
  owner?: string;
  assignee?: string;
  dueDate?: string;
  completedDate?: string;
  riskScore?: number;
  riskLevel?: string;
  slaStatus?: string;
  slaRemainingHours?: number;
  financialImpact?: number;
  currency?: string;
  escalationLevel?: number;
  clauseReference?: string;
  department?: string;
  businessUnit?: string;
  geography?: string;
  isRecurring?: boolean;
  recurrencePattern?: string;
  recurrenceNextDate?: string;
  notes?: string;
  isFavorite?: boolean;
  tags?: string[];
}

export interface ObligationReminderCreateRequest {
  obligationId: string;
  reminderType: string;
  remindAt: string;
  message?: string;
}

export interface ObligationEscalationCreateRequest {
  obligationId: string;
  escalationLevel: number;
  escalatedTo: string;
  reason?: string;
}

export interface AiReviewRequest {
  obligationId: string;
  includePredictions?: boolean;
}

// ── Response DTOs (snake_case, matching backend Pydantic schemas) ──

export interface ObligationResponse {
  id: string;
  tenant_id: string | null;
  name: string;
  description: string | null;
  obligation_type: string;
  status: string;
  contract_id: string | null;
  contract_uuid_id: string | null;
  contract_name: string | null;
  contract_number: string | null;
  vendor: string | null;
  owner: string | null;
  assignee: string | null;
  due_date: string | null;
  completed_date: string | null;
  risk_score: number;
  risk_level: string;
  sla_status: string;
  sla_remaining_hours: number;
  financial_impact: number;
  currency: string;
  escalation_level: number;
  ai_risk_prediction: number;
  ai_confidence: number;
  clause_reference: string | null;
  department: string | null;
  business_unit: string | null;
  geography: string | null;
  is_recurring: boolean;
  recurrence_pattern: string | null;
  recurrence_next_date: string | null;
  attachments_count: number;
  reminders_count: number;
  notes: string | null;
  is_favorite: boolean;
  tags: string[];
  extra_metadata: Record<string, unknown> | null;
  // Completion auditability fields (V1.1)
  completion_notes: string | null;
  completion_date: string | null;
  completed_by: string | null;
  evidence_attachment_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ObligationInstanceResponse {
  id: string;
  tenant_id: string | null;
  obligation_id: string;
  instance_date: string | null;
  due_date: string | null;
  completed_date: string | null;
  status: string;
  financial_impact: number;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ObligationKpiResponse {
  total_obligations: number;
  active_count: number;
  overdue_count: number;
  escalated_count: number;
  completed_count: number;
  breached_count: number;
  avg_risk_score: number;
  total_exposure: number;
  at_risk_amount: number;
  pending_review: number;
  upcoming_due: number;
  compliance_rate: number;
}

export interface SlaMetricResponse {
  id: string;
  tenant_id: string | null;
  obligation_id: string | null;
  vendor: string;
  contract_type: string | null;
  sla_target: string;
  performance: number;
  trend: number;
  breach_count: number;
  status: string;
  measured_at: string | null;
  created_at: string | null;
}

export interface SlaBreachResponse {
  id: string;
  vendor: string;
  contract_type: string | null;
  performance: number;
  target: string;
  breached_at: string;
  status: string;
}

export interface VendorRiskResponse {
  vendor: string;
  score: number;
  risk_level: string;
  breach_count: number;
  contract_count: number;
  trend: number;
  predicted_risk: number;
}

export interface SlaPredictionResponse {
  vendor: string;
  current_performance: number;
  predicted_performance: number;
  breach_probability: number;
  risk_level: string;
  recommendation: string;
}

export interface TimelineEventResponse {
  id: string;
  obligation_id: string;
  title: string;
  description: string | null;
  event_type: string;
  event_date: string;
  status: string;
  vendor: string | null;
}

export interface FinancialExposureResponse {
  id: string;
  tenant_id: string | null;
  category: string;
  total_exposure: number;
  overdue_amount: number;
  at_risk_amount: number;
  recovered_amount: number;
  trend: number;
  currency: string;
  as_of_date: string | null;
}

export interface FinancialExposureSummaryResponse {
  total_exposure: number;
  overdue_amount: number;
  at_risk_amount: number;
  recovered_amount: number;
  by_category: FinancialExposureResponse[];
  trend: number;
}

export interface ValueAtRiskResponse {
  total_var: number;
  probability: number;
  confidence_level: number;
  by_category: Record<string, unknown>[];
}

export interface RiskAnalysisResponse {
  obligation_id: string;
  risk_score: number;
  risk_level: string;
  breach_probability: number;
  escalation_recommended: boolean;
  recommended_action: string;
  confidence: number;
  analysis: string;
}

export interface AnomalyResponse {
  id: string;
  obligation_id: string;
  anomaly_type: string;
  severity: string;
  description: string;
  detected_at: string;
  score: number;
}

export interface ObligationReminderResponse {
  id: string;
  tenant_id: string | null;
  obligation_id: string;
  reminder_type: string;
  remind_at: string;
  sent_at: string | null;
  message: string | null;
  status: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface ObligationEscalationResponse {
  id: string;
  tenant_id: string | null;
  obligation_id: string;
  escalation_level: number;
  escalated_to: string;
  reason: string | null;
  status: string;
  resolved_at: string | null;
  resolution_notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface NotificationHistoryResponse {
  id: string;
  notification_type: string;
  recipient: string;
  message: string;
  status: string;
  sent_at: string | null;
  created_at: string;
}

export interface ObligationEvidenceResponse {
  id: string;
  tenant_id: string | null;
  obligation_id: string;
  instance_id: string | null;
  file_name: string;
  file_type: string;
  file_url: string | null;
  uploaded_by: string | null;
  description: string | null;
  created_at: string | null;
}

// ── Evidence Item (from list endpoint) ──────────────────────────────

export interface EvidenceItem {
  id: string;
  file_name: string;
  file_type: string;
  file_url: string | null;
  uploaded_by: string | null;
  description: string | null;
  created_at: string | null;
}

// ── Completion Request (V1.1) ──────────────────────────────────────

export interface ObligationCompleteRequest {
  completionNotes: string;
  completionDate?: string;
  evidenceAttachmentIds?: string[];
}

export interface VendorPerformanceResponse {
  id: string;
  tenant_id: string | null;
  vendor: string;
  category: string;
  score: number;
  trend: number;
  contract_count: number;
  breach_count: number;
  risk_level: string;
  predicted_risk: number;
  last_assessed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ObligationAuditLogResponse {
  id: string;
  tenant_id: string | null;
  obligation_id: string;
  action: string;
  actor: string | null;
  changes: Record<string, unknown> | null;
  comment: string | null;
  created_at: string | null;
}

export interface ObligationsByContractResponse {
  total: number;
  open: number;
  completed: number;
  overdue: number;
  obligations: ObligationResponse[];
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface PaginatedObligations {
  data: ObligationResponse[];
  pagination: PaginationMeta;
}

export interface ObligationListParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  obligation_type?: string;
  risk_level?: string;
  sla_status?: string;
  vendor?: string;
  owner?: string;
  assignee?: string;
  department?: string;
  business_unit?: string;
  geography?: string;
  is_favorite?: boolean;
  is_recurring?: boolean;
  sort_by?: string;
  sort_order?: SortOrder;
}

// ── Query Key Factory ─────────────────────────────────────────────

export const obligationKeys = {
  all: ["obligations"] as const,
  lists: () => [...obligationKeys.all, "list"] as const,
  list: (params?: ObligationListParams) => [...obligationKeys.lists(), params] as const,
  details: () => [...obligationKeys.all, "detail"] as const,
  detail: (id: string) => [...obligationKeys.details(), id] as const,
  kpis: () => [...obligationKeys.all, "kpis"] as const,
  slaPerformance: () => [...obligationKeys.all, "sla-performance"] as const,
  slaBreaches: () => [...obligationKeys.all, "sla-breaches"] as const,
  vendorRisk: () => [...obligationKeys.all, "vendor-risk"] as const,
  slaPredictions: () => [...obligationKeys.all, "sla-predictions"] as const,
  calendar: () => [...obligationKeys.all, "calendar"] as const,
  upcoming: () => [...obligationKeys.all, "upcoming"] as const,
  overdue: () => [...obligationKeys.all, "overdue"] as const,
  financialExposure: () => [...obligationKeys.all, "financial-exposure"] as const,
  penalties: () => [...obligationKeys.all, "penalties"] as const,
  valueAtRisk: () => [...obligationKeys.all, "value-at-risk"] as const,
  riskAnalysis: (id: string) => [...obligationKeys.all, "risk-analysis", id] as const,
  escalations: () => [...obligationKeys.all, "escalations"] as const,
  anomalies: () => [...obligationKeys.all, "anomalies"] as const,
  notificationHistory: () => [...obligationKeys.all, "notification-history"] as const,
};

// ── Service ───────────────────────────────────────────────────────

const OBLIGATIONS_BASE = "/obligations";

export const obligationsService = {
  // ── List / Paginated ──────────────────────────────────────────

  /** List obligations with pagination and filtering */
  listObligations: (params?: ObligationListParams) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    if (params?.search) query.set("search", params.search);
    if (params?.status) query.set("status", params.status);
    if (params?.obligation_type) query.set("obligation_type", params.obligation_type);
    if (params?.risk_level) query.set("risk_level", params.risk_level);
    if (params?.sla_status) query.set("sla_status", params.sla_status);
    if (params?.vendor) query.set("vendor", params.vendor);
    if (params?.owner) query.set("owner", params.owner);
    if (params?.assignee) query.set("assignee", params.assignee);
    if (params?.department) query.set("department", params.department);
    if (params?.business_unit) query.set("business_unit", params.business_unit);
    if (params?.geography) query.set("geography", params.geography);
    if (params?.is_favorite !== undefined) query.set("is_favorite", String(params.is_favorite));
    if (params?.is_recurring !== undefined) query.set("is_recurring", String(params.is_recurring));
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.sort_order) query.set("sort_order", params.sort_order);
    const qs = query.toString();
    return api.get<PaginatedObligations>(
      qs ? `${OBLIGATIONS_BASE}/?${qs}` : `${OBLIGATIONS_BASE}/`,
    );
  },

  // ── KPIs / Analytics ──────────────────────────────────────────

  /** Get obligation KPIs (totals, averages, counts) */
  getKpis: () =>
    api.get<ObligationKpiResponse>(`${OBLIGATIONS_BASE}/kpis`),

  // ── CRUD ──────────────────────────────────────────────────────

  /** Get a single obligation by ID */
  getObligation: (id: string) =>
    api.get<ObligationResponse>(`${OBLIGATIONS_BASE}/${id}`),

  /** Create a new obligation — maps camelCase frontend fields to snake_case backend */
  createObligation: (body: ObligationCreateRequest) => {
    // Map camelCase → snake_case for backend compatibility
    const snake: Record<string, unknown> = {
      name: body.name,
      obligation_type: body.obligationType,
      status: body.status,
    };
    if (body.description !== undefined) snake.description = body.description;
    if (body.contractId !== undefined) snake.contract_id = body.contractId;
    if (body.contractUuidId !== undefined) snake.contract_uuid_id = body.contractUuidId;
    if (body.contractName !== undefined) snake.contract_name = body.contractName;
    if (body.vendor !== undefined) snake.vendor = body.vendor;
    if (body.owner !== undefined) snake.owner = body.owner;
    if (body.assignee !== undefined) snake.assignee = body.assignee;
    if (body.dueDate !== undefined) snake.due_date = body.dueDate;
    if (body.riskScore !== undefined) snake.risk_score = body.riskScore;
    if (body.riskLevel !== undefined) snake.risk_level = body.riskLevel;
    if (body.financialImpact !== undefined) snake.financial_impact = body.financialImpact;
    if (body.currency !== undefined) snake.currency = body.currency;
    if (body.clauseReference !== undefined) snake.clause_reference = body.clauseReference;
    if (body.department !== undefined) snake.department = body.department;
    if (body.businessUnit !== undefined) snake.business_unit = body.businessUnit;
    if (body.geography !== undefined) snake.geography = body.geography;
    if (body.isRecurring !== undefined) snake.is_recurring = body.isRecurring;
    if (body.recurrencePattern !== undefined) snake.recurrence_pattern = body.recurrencePattern;
    if (body.notes !== undefined) snake.notes = body.notes;
    if (body.tags !== undefined) snake.tags = body.tags;
    return api.post<ObligationResponse>(`${OBLIGATIONS_BASE}/`, snake);
  },

  /** Update an existing obligation */
  updateObligation: (id: string, body: ObligationUpdateRequest) =>
    api.put<ObligationResponse>(`${OBLIGATIONS_BASE}/${id}`, body),

  /** Delete an obligation */
  deleteObligation: (id: string) =>
    api.delete<void>(`${OBLIGATIONS_BASE}/${id}`),

  // ── Lifecycle Actions ────────────────────────────────────────

  /** Complete an obligation (requires completion notes) */
  completeObligation: (id: string) =>
    api.post<ObligationResponse>(`${OBLIGATIONS_BASE}/${id}/complete`, {
      completion_notes: "Completed via quick action.",
    }),

  /** Complete an obligation with audit evidence (V1.1) */
  completeObligationWithEvidence: (id: string, body: ObligationCompleteRequest) =>
    api.post<ObligationResponse>(`${OBLIGATIONS_BASE}/${id}/complete`, {
      completion_notes: body.completionNotes,
      completion_date: body.completionDate,
      evidence_attachment_ids: body.evidenceAttachmentIds,
    }),

  /** List evidence attachments for an obligation */
  listEvidence: (id: string) =>
    api.get<EvidenceItem[]>(`${OBLIGATIONS_BASE}/${id}/evidence`),

  /** Upload an evidence file for an obligation (multipart) */
  uploadEvidence: (id: string, file: File) => {
    return api.uploadFile<{ id: string; file_name: string; file_type: string; file_url: string | null; description: string | null; created_at: string | null }>(
      `${OBLIGATIONS_BASE}/${id}/evidence`,
      file,
    );
  },

  /** Cancel an obligation */
  cancelObligation: (id: string) =>
    api.post<ObligationResponse>(`${OBLIGATIONS_BASE}/${id}/cancel`),

  /** Archive an obligation (soft-delete) */
  archiveObligation: (id: string) =>
    api.post<ObligationResponse>(`${OBLIGATIONS_BASE}/${id}/archive`),

  /** Reopen a completed or cancelled obligation */
  reopenObligation: (id: string) =>
    api.post<ObligationResponse>(`${OBLIGATIONS_BASE}/${id}/reopen`),

  /** Get audit history for an obligation */
  getAuditHistory: (id: string) =>
    api.get<ObligationAuditLogResponse[]>(`${OBLIGATIONS_BASE}/${id}/audit`),

  // ── Calendar / Upcoming / Overdue ─────────────────────────────

  /** Get obligation calendar events within a date range */
  getCalendar: (startDate: string, endDate: string) => {
    const query = new URLSearchParams();
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);
    const qs = query.toString();
    return api.get<{ data: TimelineEventResponse[] }>(
      qs ? `${OBLIGATIONS_BASE}/calendar?${qs}` : `${OBLIGATIONS_BASE}/calendar`,
    );
  },

  /** Get upcoming obligations within a given number of days */
  getUpcoming: (days: number) => {
    const query = new URLSearchParams();
    if (days !== undefined && days !== null) query.set("days", String(days));
    const qs = query.toString();
    return api.get<{ data: ObligationResponse[] }>(
      qs ? `${OBLIGATIONS_BASE}/upcoming?${qs}` : `${OBLIGATIONS_BASE}/upcoming`,
    );
  },

  /** Get overdue obligations */
  getOverdue: () =>
    api.get<{ data: ObligationResponse[] }>(`${OBLIGATIONS_BASE}/overdue`),

  // ── Financial Exposure / Penalties / Value at Risk ────────────

  /** Get financial exposure breakdown */
  getFinancialExposure: () =>
    api.get<{ data: FinancialExposureResponse[] }>(`${OBLIGATIONS_BASE}/financial-exposure`),

  /** Get penalty data */
  getPenalties: () =>
    api.get<{ data: FinancialExposureResponse[] }>(`${OBLIGATIONS_BASE}/penalties`),

  /** Get value at risk analysis */
  getValueAtRisk: () =>
    api.get<ValueAtRiskResponse>(`${OBLIGATIONS_BASE}/value-at-risk`),

  // ── Risk Analysis / Escalations / Anomalies / AI Review ───────

  /** Get risk analysis for a specific obligation */
  getRiskAnalysis: (id: string) =>
    api.get<RiskAnalysisResponse>(`${OBLIGATIONS_BASE}/${id}/risk-analysis`),

  /** Get all escalations */
  getEscalations: () =>
    api.get<{ data: ObligationEscalationResponse[] }>(`${OBLIGATIONS_BASE}/escalations`),

  /** Get detected anomalies */
  getAnomalies: () =>
    api.get<{ data: AnomalyResponse[] }>(`${OBLIGATIONS_BASE}/anomalies`),

  /** Run AI review on an obligation */
  aiReview: (body: AiReviewRequest) =>
    api.post<RiskAnalysisResponse>(`${OBLIGATIONS_BASE}/ai-review`, body),

  // ── Reminders / Escalations / Notifications ───────────────────

  /** Create a reminder for an obligation */
  createReminder: (body: ObligationReminderCreateRequest) =>
    api.post<ObligationReminderResponse>(`${OBLIGATIONS_BASE}/reminders`, body),

  /** Create an escalation for an obligation */
  createEscalation: (body: ObligationEscalationCreateRequest) =>
    api.post<ObligationEscalationResponse>(`${OBLIGATIONS_BASE}/escalations`, body),

  /** Get notification history */
  getNotificationHistory: () =>
    api.get<{ data: NotificationHistoryResponse[] }>(`${OBLIGATIONS_BASE}/notification-history`),

  // ── SLA Performance / Breaches / Vendor Risk / Predictions ────

  /** Get SLA performance metrics */
  getSlaPerformance: () =>
    api.get<{ data: SlaMetricResponse[] }>(`${OBLIGATIONS_BASE}/sla-performance`),

  /** Get SLA breaches */
  getSlaBreaches: () =>
    api.get<{ data: SlaBreachResponse[] }>(`${OBLIGATIONS_BASE}/sla-breaches`),

  /** Get vendor risk scores */
  getVendorRisk: () =>
    api.get<{ data: VendorRiskResponse[] }>(`${OBLIGATIONS_BASE}/vendor-risk`),

  /** Get SLA predictions */
  getSlaPredictions: () =>
    api.get<{ data: SlaPredictionResponse[] }>(`${OBLIGATIONS_BASE}/sla-predictions`),

  /** Get obligations by contract (counts + list) */
  getByContract: (contractId: string) =>
    api.get<ObligationsByContractResponse>(`${OBLIGATIONS_BASE}/by-contract/${contractId}`),
};
