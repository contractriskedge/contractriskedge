/**
 * Human Oversight API service — approval workflows, policy exceptions, acknowledgments.
 */

"use client";

import { api } from "@/services/api/client";

// ── Types matching backend API responses ────────────────────────────────

export interface ApprovalSummary {
  approval_id: string;
  review_id: string;
  approval_type: string;
  title: string;
  status: string;
  priority: string;
  confidence: number;
  requested_by: string;
  requested_at: string;
  expires_at: string | null;
  decided_by: string | null;
  decided_at: string | null;
  approval_level: number;
}

export interface PolicyExceptionRequest {
  exception_id: string;
  review_id: string;
  upload_id: string;
  rule_id: string | null;
  rule_name: string;
  policy_name: string;
  clause_category: string;
  severity: string;
  justification: string;
  proposed_alternative: string | null;
  risk_assessment: string;
  status: string;
  requested_by: string;
  requested_at: string;
  effective_date: string | null;
  expiration_date: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  approval_level: number;
  previous_exception_id: string | null;
  correlation_id: string | null;
}

export interface HumanOversightDashboard {
  pending_approvals: number;
  pending_exceptions: number;
  pending_acknowledgments: number;
  overdue_approvals: number;
  total_decisions_today: number;
  approval_slat_breaches: number;
  recent_approvals: ApprovalSummary[];
  recent_exceptions: PolicyExceptionRequest[];
  by_type: Record<string, number>;
  by_priority: Record<string, number>;
}

// ── API Fetchers ────────────────────────────────────────────────────────

export async function fetchPendingExceptions(): Promise<PolicyExceptionRequest[]> {
  return api.get<PolicyExceptionRequest[]>("/human-oversight/exceptions/pending");
}

export async function fetchPendingApprovals(): Promise<ApprovalSummary[]> {
  return api.get<ApprovalSummary[]>("/human-oversight/approvals/pending");
}

export async function fetchHumanOversightDashboard(): Promise<HumanOversightDashboard> {
  return api.get<HumanOversightDashboard>("/human-oversight/dashboard");
}

// ── Mutation Fetchers ───────────────────────────────────────────────────

export interface ApprovalDecisionRequest {
  decision: "approved" | "rejected" | "conditionally_approved";
  notes?: string;
  conditions?: Record<string, unknown>;
}

export interface ExceptionReviewRequest {
  decision: "approved" | "rejected" | "conditionally_approved";
  review_notes?: string;
  expiration_date?: string | null;
}

/**
 * Decide on an approval request.
 * POST /api/v1/human-oversight/approvals/{approval_id}/decide
 */
export async function decideApproval(
  approvalId: string,
  body: ApprovalDecisionRequest,
  token?: string,
): Promise<unknown> {
  return api.post(`/human-oversight/approvals/${approvalId}/decide`, body, { token });
}

/**
 * Review a policy exception.
 * POST /api/v1/human-oversight/exceptions/{exception_id}/review
 */
export async function reviewException(
  exceptionId: string,
  body: ExceptionReviewRequest,
  token?: string,
): Promise<unknown> {
  return api.post(`/human-oversight/exceptions/${exceptionId}/review`, body, { token });
}
