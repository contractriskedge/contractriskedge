/**
 * Negotiation API service — real API client for negotiation operations.
 * Maps 1:1 to backend endpoints at /api/v1/negotiations.
 */

"use client";

import { api } from "@/services/api/client";

// ── Types ────────────────────────────────────────────────────────

export interface NegotiationSessionSummary {
  id: string;
  contractTitle: string;
  counterparty: string;
  stage: string;
  healthScore: number;
  startedAt: string;
  updatedAt: string;
}

export interface ClauseContent {
  clauseId: string;
  title: string;
  sectionNumber: string;
  content: string;
  riskLevel: string;
  category: string;
}

export interface DocumentVersion {
  id: string;
  label: string;
  timestamp: string;
  author: string;
  authorAvatar: string;
  status: string;
  content: ClauseContent[];
  wordCount: number;
  changeSummary: string;
}

export interface CommentItem {
  id: string;
  author: string;
  authorAvatar: string;
  authorRole: string;
  content: string;
  timestamp: string;
  status: string;
  mentions: string[];
  replies: CommentItem[];
  clauseId?: string;
  resolvedBy?: string;
  resolvedAt?: string;
}

export interface RedlineEntry {
  id: string;
  type: string;
  clauseId: string;
  sectionNumber: string;
  title: string;
  originalText: string;
  modifiedText: string;
  author: string;
  authorAvatar: string;
  timestamp: string;
  riskLevel: string;
  category: string;
  status: string;
  aiGenerated: boolean;
  aiConfidence?: number;
  negotiationImpact?: string;
  benchmarkDeviation?: number;
  comments: CommentItem[];
}

export interface NegotiationIssue {
  id: string;
  title: string;
  description: string;
  clauseId: string;
  sectionNumber: string;
  severity: string;
  status: string;
  assignee: string;
  assigneeAvatar: string;
  dueDate: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  category: string;
  escalationLevel: number;
  comments: CommentItem[];
  tags: string[];
}

export interface Participant {
  id: string;
  name: string;
  avatar: string;
  role: string;
  department: string;
  isOnline: boolean;
  lastActive: string;
  reviewedClauses: number;
  pendingApprovals: number;
}

export interface ActivityEntry {
  id: string;
  type: string;
  user: string;
  userAvatar: string;
  action: string;
  description: string;
  timestamp: string;
  clauseId?: string;
  versionId?: string;
}

export interface NegotiationSession {
  id: string;
  contractTitle: string;
  counterparty: string;
  stage: string;
  versions: DocumentVersion[];
  currentVersionId: string;
  redlines: RedlineEntry[];
  issues: NegotiationIssue[];
  participants: Participant[];
  insights: unknown[];
  playbooks: unknown[];
  workflow: Record<string, unknown>;
  analytics: Record<string, unknown>;
  activities: ActivityEntry[];
  healthScore: number;
  startedAt: string;
  updatedAt: string;
}

export interface NegotiationKpiData {
  total_sessions: number;
  active_sessions: number;
  by_stage: Record<string, number>;
  escalated_count: number;
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
  contractTitle: string;
  counterparty: string;
  clauses?: ClauseContent[];
}

export interface UpdateNegotiationRequest {
  stage?: string;
  healthScore?: number;
}

export interface CreateRedlineRequest {
  clauseId: string;
  type?: string;
  title: string;
  originalText: string;
  modifiedText?: string;
  riskLevel?: string;
}

export interface UpdateRedlineStatusRequest {
  status: string;
}

export interface CreateIssueRequest {
  clauseId?: string;
  title: string;
  description?: string;
  severity?: string;
  assignee?: string;
  dueDate?: string;
  category?: string;
}

export interface UpdateIssueRequest {
  status?: string;
  severity?: string;
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

export interface AddParticipantRequest {
  name: string;
  role?: string;
  department?: string;
}

export interface UpdateParticipantRequest {
  role?: string;
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

  updateSession: (id: string, body: UpdateNegotiationRequest) =>
    api.patch<NegotiationSession>(`${NEGOTIATIONS_BASE}/${id}`, body),

  deleteSession: (id: string) =>
    api.delete<void>(`${NEGOTIATIONS_BASE}/${id}`),

  // ── Redlines ────────────────────────────────────────────────
  listRedlines: (sessionId: string, clauseId?: string) => {
    const query = new URLSearchParams();
    if (clauseId) query.set("clauseId", clauseId);
    const qs = query.toString();
    return api.get<RedlineEntry[]>(
      qs ? `${NEGOTIATIONS_BASE}/${sessionId}/redlines?${qs}` : `${NEGOTIATIONS_BASE}/${sessionId}/redlines`,
    );
  },

  createRedline: (sessionId: string, body: CreateRedlineRequest) =>
    api.post<RedlineEntry>(`${NEGOTIATIONS_BASE}/${sessionId}/redlines`, body),

  updateRedlineStatus: (sessionId: string, redlineId: string, body: UpdateRedlineStatusRequest) =>
    api.patch<RedlineEntry>(`${NEGOTIATIONS_BASE}/${sessionId}/redlines/${redlineId}`, body),

  // ── Issues ──────────────────────────────────────────────────
  listIssues: (sessionId: string) =>
    api.get<NegotiationIssue[]>(`${NEGOTIATIONS_BASE}/${sessionId}/issues`),

  createIssue: (sessionId: string, body: CreateIssueRequest) =>
    api.post<NegotiationIssue>(`${NEGOTIATIONS_BASE}/${sessionId}/issues`, body),

  updateIssue: (sessionId: string, issueId: string, body: UpdateIssueRequest) =>
    api.patch<NegotiationIssue>(`${NEGOTIATIONS_BASE}/${sessionId}/issues/${issueId}`, body),

  // ── Comments ────────────────────────────────────────────────
  listComments: (sessionId: string, params?: { redlineId?: string; issueId?: string }) => {
    const query = new URLSearchParams();
    if (params?.redlineId) query.set("redlineId", params.redlineId);
    if (params?.issueId) query.set("issueId", params.issueId);
    const qs = query.toString();
    return api.get<CommentItem[]>(
      qs ? `${NEGOTIATIONS_BASE}/${sessionId}/comments?${qs}` : `${NEGOTIATIONS_BASE}/${sessionId}/comments`,
    );
  },

  createComment: (sessionId: string, body: CreateCommentRequest) =>
    api.post<CommentItem>(`${NEGOTIATIONS_BASE}/${sessionId}/comments`, body),

  resolveComment: (sessionId: string, commentId: string) =>
    api.patch<CommentItem>(`${NEGOTIATIONS_BASE}/${sessionId}/comments/${commentId}/resolve`),

  // ── Participants ────────────────────────────────────────────
  listParticipants: (sessionId: string) =>
    api.get<Participant[]>(`${NEGOTIATIONS_BASE}/${sessionId}/participants`),

  addParticipant: (sessionId: string, body: AddParticipantRequest) =>
    api.post<Participant>(`${NEGOTIATIONS_BASE}/${sessionId}/participants`, body),

  updateParticipant: (sessionId: string, participantId: string, body: UpdateParticipantRequest) =>
    api.patch<Participant>(`${NEGOTIATIONS_BASE}/${sessionId}/participants/${participantId}`, body),

  removeParticipant: (sessionId: string, participantId: string) =>
    api.delete<void>(`${NEGOTIATIONS_BASE}/${sessionId}/participants/${participantId}`),

  // ── Activities ──────────────────────────────────────────────
  getActivities: (sessionId: string) =>
    api.get<ActivityEntry[]>(`${NEGOTIATIONS_BASE}/${sessionId}/activities`),
};
