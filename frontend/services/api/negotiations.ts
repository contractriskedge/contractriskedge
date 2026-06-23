/**
 * Negotiation API service — real API client for negotiation operations.
 * Maps 1:1 to backend endpoints at /api/v1/negotiations.
 */

"use client";

import { api } from "@/services/api/client";
import type {
  NegotiationSessionSummary,
  ClauseContent,
  CommentItem,
  RedlineEntry,
  NegotiationIssue,
  Participant,
  NegotiationSession,
  NegotiationKpis,
  AiRewriteResponse,
  AiCoachResponse,
  NegotiationStage,
  IssueSeverity,
  IssueStatus,
  RiskLevel,
} from "./negotiation.types";

// ── API-specific Types (not shared with components) ──────────────

export interface NegotiationKpiData {
  total_sessions: number;
  active_sessions: number;
  by_stage: Record<string, number>;
  escalated_count: number;
  sparkline_data?: Record<string, number[]>;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

// ── Create / Update Request Types ───────────────────────────────

export interface CreateNegotiationRequest {
  contractId?: string;
  contractTitle: string;
  counterparty: string;
  clauses?: ClauseContent[];
}

export interface UpdateNegotiationRequest {
  stage?: NegotiationStage;
  healthScore?: number;
}

export interface CreateRedlineRequest {
  clauseId: string;
  type?: string;
  title: string;
  originalText: string;
  modifiedText?: string;
  riskLevel?: RiskLevel;
}

export interface UpdateRedlineStatusRequest {
  status: string;
}

export interface CreateIssueRequest {
  clauseId?: string;
  title: string;
  description?: string;
  severity?: IssueSeverity;
  assignee?: string;
  dueDate?: string;
  category?: string;
}

export interface UpdateIssueRequest {
  status?: IssueStatus;
  severity?: IssueSeverity;
  assignee?: string;
  escalationLevel?: number;
}

export interface CreateCommentRequest {
  redlineId?: string;
  issueId?: string;
  clauseId?: string;
  parentId?: string;
  content: string;
  mentions?: string[];
}

// ── API Service ─────────────────────────────────────────────────

const NEGOTIATIONS_BASE = "/negotiations";

export const negotiationsService = {
  // ── KPIs ────────────────────────────────────────────────────
  getKpis: () =>
    api.get<NegotiationKpiData>(`${NEGOTIATIONS_BASE}/kpis`),

  // ── Sessions ─────────────────────────────────────────────────
  listSessions: (params?: { stage?: string; search?: string; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.stage) query.set("stage", params.stage);
    if (params?.search) query.set("search", params.search);
    if (params?.page) query.set("page", String(params.page));
    if (params?.page_size) query.set("page_size", String(params.page_size));
    const qs = query.toString();
    return api.get<PaginatedResponse<NegotiationSessionSummary>>(
      qs ? `${NEGOTIATIONS_BASE}/?${qs}` : `${NEGOTIATIONS_BASE}/`,
    );
  },

  getSession: (id: string) =>
    api.get<NegotiationSession>(`${NEGOTIATIONS_BASE}/${id}`),

  createSession: (body: CreateNegotiationRequest) =>
    api.post<NegotiationSession>(`${NEGOTIATIONS_BASE}/`, body),

  resumeOrCreateFromReview: (body: { reviewId: string; counterparty?: string }) =>
    api.post<NegotiationSession>(`${NEGOTIATIONS_BASE}/from-review`, body),

  updateSession: (id: string, body: UpdateNegotiationRequest) =>
    api.patch<NegotiationSession>(`${NEGOTIATIONS_BASE}/${id}`, body),

  deleteSession: (id: string) =>
    api.delete<void>(`${NEGOTIATIONS_BASE}/${id}`),

  // ── Redlines ────────────────────────────────────────────────
  createRedline: (sessionId: string, body: CreateRedlineRequest) =>
    api.post<RedlineEntry>(`${NEGOTIATIONS_BASE}/${sessionId}/redlines`, body),

  updateRedlineStatus: (sessionId: string, redlineId: string, body: UpdateRedlineStatusRequest) =>
    api.patch<RedlineEntry>(`${NEGOTIATIONS_BASE}/${sessionId}/redlines/${redlineId}`, body),

  // ── Issues ──────────────────────────────────────────────────
  createIssue: (sessionId: string, body: CreateIssueRequest) =>
    api.post<NegotiationIssue>(`${NEGOTIATIONS_BASE}/${sessionId}/issues`, body),

  updateIssue: (sessionId: string, issueId: string, body: UpdateIssueRequest) =>
    api.patch<NegotiationIssue>(`${NEGOTIATIONS_BASE}/${sessionId}/issues/${issueId}`, body),

  // ── Comments ────────────────────────────────────────────────
  createComment: (sessionId: string, body: CreateCommentRequest) =>
    api.post<CommentItem>(`${NEGOTIATIONS_BASE}/${sessionId}/comments`, body),

  // ── Activities ──────────────────────────────────────────────
  getActivities: (sessionId: string) =>
    api.get<ActivityEntry[]>(`${NEGOTIATIONS_BASE}/${sessionId}/activities`),

  // ── AI Rewrite ──────────────────────────────────────────────
  aiRewrite: (sessionId: string, clauseId: string, body: {
    clause_text: string;
    strategy?: string;
    context?: string;
  }) =>
    api.post<{
      original_text: string;
      rewritten_text: string;
      strategy: string;
      changes: { description: string }[];
      model_used: string;
    }>(`${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/rewrite`, body),

  // ── AI Explanation ──────────────────────────────────────────
  aiExplain: (sessionId: string, clauseId: string, body: {
    original_text: string;
    rewritten_text: string;
    strategy: string;
  }) =>
    api.post<{
      explanation: string;
      changes: { description: string }[];
      risks_addressed: string[];
      benefits: string[];
    }>(`${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/explain`, body),

  // ── AI Coach ────────────────────────────────────────────────
  aiCoach: (sessionId: string, clauseId: string, body: {
    clause_text: string;
    question: string;
  }) =>
    api.post<{
      risks: string[];
      policy_conflicts: string[];
      recommended_alternative?: string;
      explanation: string;
    }>(`${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/coach`, body),

  // ── Clause Comments ─────────────────────────────────────────
  addClauseComment: (sessionId: string, clauseId: string, body: {
    body: string;
    parent_comment_id?: string;
    finding_id?: string;
  }) =>
    api.post<Record<string, unknown>>(
      `${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/comments`,
      body,
    ),

  getClauseComments: (sessionId: string, clauseId: string, findingId?: string) => {
    const qs = findingId ? `?findingId=${findingId}` : "";
    return api.get<Record<string, unknown>[]>(
      `${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/comments${qs}`,
    );
  },

  resolveClauseComment: (sessionId: string, clauseId: string, commentId: string) =>
    api.post<{ status: string; comment_id: string }>(
      `${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/comments/${commentId}/resolve`,
    ),

  // ── Clause Bundle Apply ─────────────────────────────────────
  applyClauseBundle: (sessionId: string, clauseId: string, body: {
    clause_type: string;
    target_clause_id: string;
  }) =>
    api.post<{
      status: string;
      session_id: string;
      clause_type: string;
      redline_ids: string[];
      templates_applied: number;
      message: string;
    }>(`${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/apply-bundle`, body),

  // ── Voting ──────────────────────────────────────────────────
  castVote: (sessionId: string, body: {
    clause_id: string;
    finding_id?: string;
    voter_name: string;
    voter_role: string;
    vote: string;
    comment?: string;
  }) =>
    api.post<{ vote_id: string; clause_id: string; voter_role: string; vote: string; message: string }>(
      `${NEGOTIATIONS_BASE}/${sessionId}/votes`, body,
    ),

  getClauseVotes: (sessionId: string, clauseId: string) =>
    api.get<Record<string, unknown>[]>(
      `${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/votes`,
    ),

  getVoteSummary: (sessionId: string) =>
    api.get<Record<string, unknown>[]>(`${NEGOTIATIONS_BASE}/${sessionId}/votes/summary`),

  // ── Clause Score ────────────────────────────────────────────
  getClauseScore: (sessionId: string, clauseId: string) =>
    api.get<{
      clause_id: string;
      risk_score: number;
      negotiability_score: number;
      readability_score: number;
      market_standard_score: number;
      overall_score: number;
    }>(`${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/score`),

  // ── Dependency Warnings ─────────────────────────────────────
  getClauseDependencies: (sessionId: string, clauseId: string) =>
    api.get<{
      clause_id: string;
      clause_type: string;
      warnings: { affected_clause: string; relationship: string; impact: string; description: string }[];
    }>(`${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/dependencies`),

  // ── Negotiation History ─────────────────────────────────────
  getClauseHistory: (sessionId: string, clauseId: string) =>
    api.get<{
      version_number: number;
      label: string;
      author: string;
      timestamp: string;
      action: string;
      clause_id: string;
      original_text: string;
      modified_text: string;
      explanation?: string;
    }[]>(`${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/history`),

  // ── Counterparty Comparison ─────────────────────────────────
  getCounterpartyComparison: (sessionId: string, clauseId: string) =>
    api.get<{
      clause_id: string;
      our_position: string;
      vendor_position: string;
      final_position?: string;
      diff_additions: string[];
      diff_deletions: string[];
    }>(`${NEGOTIATIONS_BASE}/${sessionId}/clauses/${clauseId}/comparison`),

  // ── Negotiation Summary ─────────────────────────────────────
  getNegotiationSummary: (sessionId: string) =>
    api.get<{
      session_id: string;
      total_clauses: number;
      clauses_modified: number;
      clauses_accepted: number;
      clauses_pending: number;
      clauses_escalated: number;
      risk_score_before: number;
      risk_score_after: number;
      estimated_time_saved_hours: number;
      votes_cast: number;
      votes_approved: number;
      votes_rejected: number;
      ai_rewrites_used: number;
      generated_at: string;
    }>(`${NEGOTIATIONS_BASE}/${sessionId}/summary`),

  // ── Chat History ────────────────────────────────────────────
  getChatMessages: (sessionId: string) =>
    api.get<{
      id: string;
      session_id: string;
      role: string;
      content: string;
      clause_id?: string;
      metadata?: Record<string, unknown>;
      created_at: string;
    }[]>(`${NEGOTIATIONS_BASE}/${sessionId}/chat`),

  addChatMessage: (sessionId: string, body: {
    role: "user" | "assistant";
    content: string;
    clause_id?: string;
    metadata?: Record<string, unknown>;
  }) =>
    api.post<{
      id: string;
      session_id: string;
      role: string;
      content: string;
      clause_id?: string;
      metadata?: Record<string, unknown>;
      created_at: string;
    }>(`${NEGOTIATIONS_BASE}/${sessionId}/chat`, body),

  clearChatMessages: (sessionId: string) =>
    api.delete<void>(`${NEGOTIATIONS_BASE}/${sessionId}/chat`),

  // ── Strategies ──────────────────────────────────────────────
  getStrategies: () =>
    api.get<{
      strategies: {
        strategy_id: string;
        name: string;
        description: string;
        icon: string;
        prompt_template: string;
        is_default: boolean;
        is_active: boolean;
      }[];
    }>("/negotiations/strategies"),
};
