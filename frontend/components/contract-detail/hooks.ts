/**
 * Contract Detail Workspace — API hooks.
 *
 * Provides TanStack Query hooks for fetching contract detail,
 * findings, clauses, activity, comments, and metadata.
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type {
  ContractDetail,
  AiFinding,
  ClauseDeviation,
  ComplianceIssue,
  ActivityEvent,
  Comment,
  Obligation,
  DocumentVersion,
} from "./types";

// ── Finding / clause normalization ─────────────────────────────────────────

type RawFinding = Record<string, unknown>;

function normalizeAiFinding(raw: RawFinding): AiFinding {
  const pageNumbers = Array.isArray(raw.page_numbers)
    ? (raw.page_numbers as number[])
    : [];
  const resolution = String(raw.resolution ?? "open");
  const status: AiFinding["status"] =
    resolution === "resolved"
      ? "resolved"
      : resolution === "dismissed" || resolution === "false_positive"
        ? "dismissed"
        : "open";

  return {
    id: String(raw.id ?? raw.finding_id ?? ""),
    clause_type: String(raw.clause_type ?? "other"),
    severity: (raw.severity ?? "medium") as AiFinding["severity"],
    confidence: Number(raw.confidence ?? 0),
    title: String(raw.title ?? ""),
    description: String(raw.description ?? ""),
    recommendation: String(raw.recommendation ?? ""),
    page_numbers: pageNumbers,
    chunk_id: String(raw.chunk_id ?? ""),
    clause_text: String(raw.clause_text ?? raw.description ?? ""),
    status,
    category: String(raw.category ?? raw.clause_type ?? "other"),
    remediation: raw.remediation ? String(raw.remediation) : undefined,
    created_at: String(raw.created_at ?? ""),
    resolved_at: raw.resolved_at ? String(raw.resolved_at) : undefined,
    resolved_by: raw.resolved_by ? String(raw.resolved_by) : undefined,
  };
}

function findingsToClauseDeviations(findings: AiFinding[]): ClauseDeviation[] {
  return findings.map((f) => ({
    id: f.id,
    clause_type: f.clause_type,
    expected: f.recommendation || "Playbook / market standard",
    actual: f.description,
    severity: f.severity,
    page_number: f.page_numbers[0] ?? 0,
    recommendation: f.recommendation,
  }));
}

// ── API Response Normalization ──────────────────────────────────────────────
// The backend GET /contracts/{id} endpoint returns camelCase fields
// (e.g. riskScore, contractType) but the frontend ContractDetail type
// uses snake_case (e.g. risk_score, contract_type).
// This function normalizes the response to match the frontend type.

function normalizeContractDetail(raw: Record<string, unknown>): ContractDetail {
  return {
    id: String(raw.id || raw.review_id || ""),
    name: String(raw.name || raw.document_name || "Untitled"),
    filename: String(raw.filename || raw.original_filename || ""),
    vendor: String(raw.vendor ?? raw.counterparty ?? ""),
    counterparty: String(raw.counterparty ?? raw.vendor ?? ""),
    contract_type: String(raw.contract_type ?? raw.contractType ?? ""),
    business_unit: String(raw.business_unit ?? raw.businessUnit ?? ""),
    geography: String(raw.geography ?? ""),
    description: String(raw.description ?? raw.aiSummary ?? ""),
    ai_summary: String(raw.ai_summary ?? raw.aiSummary ?? ""),
    risk_score: Number(raw.risk_score ?? raw.riskScore ?? 0),
    risk_level: (raw.risk_level ?? raw.riskLevel ?? "medium") as ContractDetail["risk_level"],
    financial_value: Number(raw.financial_value ?? raw.financialValue ?? 0),
    currency: String(raw.currency ?? "USD"),
    status: String(raw.status ?? "draft"),
    workflow_stage: String(raw.workflow_stage ?? raw.workflowStage ?? ""),
    effective_date: String(raw.effective_date ?? raw.effectiveDate ?? raw.createdAt ?? ""),
    expiration_date: String(raw.expiration_date ?? raw.expirationDate ?? raw.renewalDate ?? ""),
    renewal_date: String(raw.renewal_date ?? raw.renewalDate ?? ""),
    auto_renew: Boolean(raw.auto_renew ?? raw.autoRenew ?? false),
    has_dpa: Boolean(raw.has_dpa ?? raw.hasDpa ?? false),
    owner: String(raw.owner ?? ""),
    total_pages: Number(raw.total_pages ?? raw.totalPages ?? 0),
    clause_count: Number(raw.clause_count ?? raw.clauseCount ?? 0),
    tags: Array.isArray(raw.tags) ? raw.tags as string[] : [],
    ai_findings_count: Number(raw.ai_findings_count ?? raw.aiFindingsCount ?? 0),
    unresolved_risks: Number(raw.unresolved_risks ?? raw.unresolvedRisks ?? 0),
    obligations_due: Number(raw.obligations_due ?? raw.obligationsDue ?? 0),
    confidence_score: Number(raw.confidence_score ?? raw.aiConfidence ?? 0) / 100,
    document_url: String(raw.document_url ?? raw.documentUrl ?? ""),
    created_at: String(raw.created_at ?? raw.createdAt ?? ""),
    updated_at: String(raw.updated_at ?? raw.updatedAt ?? raw.lastModified ?? ""),
    last_activity: String(raw.last_activity ?? raw.lastActivity ?? raw.updated_at ?? raw.updatedAt ?? ""),
    missing_clauses: Array.isArray(raw.missing_clauses ?? raw.missingClauses) ? (raw.missing_clauses ?? raw.missingClauses) as string[] : [],
    ai_flags: Array.isArray(raw.ai_flags ?? raw.aiFlags) ? (raw.ai_flags ?? raw.aiFlags) as string[] : [],
  };
}

// ── Query Keys ──────────────────────────────────────────────────────────────

export const contractDetailKeys = {
  all: ["contract-detail"] as const,
  detail: (id: string) => [...contractDetailKeys.all, "detail", id] as const,
  findings: (id: string) => [...contractDetailKeys.all, "findings", id] as const,
  clauses: (id: string) => [...contractDetailKeys.all, "clauses", id] as const,
  compliance: (id: string) => [...contractDetailKeys.all, "compliance", id] as const,
  activity: (id: string) => [...contractDetailKeys.all, "activity", id] as const,
  comments: (id: string) => [...contractDetailKeys.all, "comments", id] as const,
  obligations: (id: string) => [...contractDetailKeys.all, "obligations", id] as const,
  versions: (id: string) => [...contractDetailKeys.all, "versions", id] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

/** Fetch full contract detail with camelCase→snake_case normalization. */
export function useContractDetail(contractId: string) {
  return useQuery({
    queryKey: contractDetailKeys.detail(contractId),
    queryFn: async () => {
      const raw = await api.get<Record<string, unknown>>(`/contracts/${contractId}`);
      return normalizeContractDetail(raw);
    },
    enabled: !!contractId,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

/** Fetch AI findings for the contract.
 *  Backend routes findings under /reviews/{review_id}/findings.
 *  Contract ID maps to review ID 1:1.
 */
export function useContractFindings(
  contractId: string,
  params?: { severity?: string; status?: string; page?: number; page_size?: number }
) {
  return useQuery({
    queryKey: contractDetailKeys.findings(contractId),
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.severity) searchParams.set("severity", params.severity);
      if (params?.status) searchParams.set("status", params.status);
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.page_size) searchParams.set("page_size", String(params.page_size));
      const qs = searchParams.toString();
      try {
        const res = await api.get<{ findings: RawFinding[]; total: number }>(
          `/reviews/${contractId}/findings${qs ? `?${qs}` : ""}`,
        );
        const findings = (res.findings ?? []).map(normalizeAiFinding);
        return { findings, total: res.total ?? findings.length };
      } catch {
        return { findings: [], total: 0 };
      }
    },
    enabled: !!contractId,
    staleTime: 30_000,
  });
}

/** Fetch clause deviations derived from AI findings for this contract/review. */
export function useContractClauses(contractId: string) {
  return useQuery({
    queryKey: contractDetailKeys.clauses(contractId),
    queryFn: async () => {
      try {
        const res = await api.get<{ findings: RawFinding[]; total: number }>(
          `/reviews/${contractId}/findings`,
        );
        const findings = (res.findings ?? []).map(normalizeAiFinding);
        return { clauses: findingsToClauseDeviations(findings) };
      } catch {
        return { clauses: [] };
      }
    },
    enabled: !!contractId,
    staleTime: 60_000,
  });
}

/** Fetch compliance issues. */
export function useContractCompliance(contractId: string) {
  return useQuery({
    queryKey: contractDetailKeys.compliance(contractId),
    queryFn: () =>
      api.get<{ issues: ComplianceIssue[] }>(`/contracts/${contractId}/compliance`),
    enabled: !!contractId,
    staleTime: 60_000,
  });
}

/** Fetch activity timeline.
 *  Backend: activity is embedded in GET /reviews/{review_id}/workspace as
 *  `recent_activity` (array of status-history rows). We also synthesize a
 *  few extra entries from `versions` so the timeline never feels empty
 *  even for contracts that haven't had a status transition yet.
 */
export function useContractActivity(contractId: string) {
  return useQuery({
    queryKey: contractDetailKeys.activity(contractId),
    queryFn: async () => {
      try {
        const res = await api.get<{
          recent_activity?: Array<Record<string, unknown>>;
          events?: ActivityEvent[];
          activity?: ActivityEvent[];
          versions?: Array<Record<string, unknown>>;
          review?: Record<string, unknown>;
        }>(`/reviews/${contractId}/workspace`);

        // Fast path: backend already returns the friendly shape
        if (res.events?.length) {
          return { events: res.events };
        }
        if (res.activity?.length) {
          return { events: res.activity };
        }

        // Normalize the actual `recent_activity` payload from
        // GET /reviews/{id}/workspace. The backend returns rows with
        // {activity_id, from_status, to_status, changed_by, reason, created_at}
        // which we map to the ActivityEvent shape used by the UI.
        const statusEvents: ActivityEvent[] = (res.recent_activity ?? []).map(
          (row) => normalizeStatusHistoryRow(row),
        );

        // Synthesize events from the document version list — every new
        // version is a real "version_created" activity that the UI can
        // show. This is what was missing before: a brand-new contract
        // has no status transitions but does have a current version.
        const versionEvents: ActivityEvent[] = (res.versions ?? [])
          .slice(0, 10)
          .map((v) => normalizeVersionRow(v));

        // Fall back to the contract creation if we still have nothing
        // to show (e.g. very old contracts with no version rows).
        const fallback: ActivityEvent[] = [];
        if (statusEvents.length === 0 && versionEvents.length === 0) {
          const createdAt = String(
            res.review?.created_at ?? res.review?.createdAt ?? new Date().toISOString(),
          );
          const createdBy = String(
            res.review?.created_by ?? res.review?.createdBy ?? "system",
          );
          fallback.push({
            id: `fallback-${contractId}-created`,
            type: "contract_created",
            actor: createdBy,
            action: "Contract created",
            timestamp: createdAt,
          });
        }

        return {
          events: [...statusEvents, ...versionEvents, ...fallback].sort(
            (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
          ),
        };
      } catch {
        return { events: [] };
      }
    },
    enabled: !!contractId,
    staleTime: 30_000,
  });
}

/** Map a backend `review_status_history` row to the frontend ActivityEvent shape. */
function normalizeStatusHistoryRow(row: Record<string, unknown>): ActivityEvent {
  const from = row.from_status ? String(row.from_status) : null;
  const to = row.to_status ? String(row.to_status) : null;
  const reason = row.reason ? String(row.reason) : "";
  const actor = row.changed_by ? String(row.changed_by) : "system";
  const timestamp = row.created_at
    ? String(row.created_at)
    : new Date().toISOString();
  const id = row.activity_id
    ? String(row.activity_id)
    : `status-${timestamp}-${actor}`;

  // Derive a friendly `type` and `action` from the transition. We
  // recognise the common ReviewStatus values the backend produces.
  const action = describeTransition(from, to, reason);
  const type = transitionType(from, to);

  return {
    id,
    type,
    actor,
    action,
    timestamp,
    details: reason || undefined,
  };
}

function describeTransition(
  from: string | null,
  to: string | null,
  reason: string,
): string {
  const cleanTo = (to ?? "").replace(/_/g, " ");
  if (from && to) {
    return `Status changed: ${from.replace(/_/g, " ")} → ${cleanTo}${reason ? ` (${reason})` : ""}`;
  }
  if (to) {
    return `Status set to ${cleanTo}${reason ? ` (${reason})` : ""}`;
  }
  return reason || "Status updated";
}

function transitionType(
  from: string | null,
  to: string | null,
): ActivityEvent["type"] {
  if (to === "approved") return "review_approved";
  if (to === "rejected") return "review_rejected";
  if (to === "ai_analyzed" || to === "ai_reviewed") return "ai_analysis_completed";
  if (to === "in_review") return "status_changed";
  if (to === "escalated") return "status_changed";
  if (from && to && from !== to) return "status_changed";
  return "status_changed";
}

/** Map a backend `contract_document_versions` row to an ActivityEvent. */
function normalizeVersionRow(v: Record<string, unknown>): ActivityEvent {
  const versionNumber = v.version_number ?? v.versionNumber ?? 1;
  const createdAt = String(v.created_at ?? v.createdAt ?? new Date().toISOString());
  const createdBy = String(v.created_by ?? v.createdBy ?? "system");
  const changeSummary = v.change_summary ?? v.changeSummary;
  const id = String(v.version_id ?? v.versionId ?? `version-${versionNumber}-${createdAt}`);

  return {
    id,
    type: "version_created",
    actor: createdBy,
    action: `Version v${versionNumber} created${changeSummary ? ` — ${String(changeSummary)}` : ""}`,
    timestamp: createdAt,
  };
}

/** Fetch comments. */
export function useContractComments(contractId: string) {
  return useQuery({
    queryKey: contractDetailKeys.comments(contractId),
    queryFn: () =>
      api.get<{ comments: Comment[] }>(`/contracts/${contractId}/comments`),
    enabled: !!contractId,
    staleTime: 15_000,
  });
}

/** Fetch obligations.
 *  Backend: obligations live under /obligations/ domain (not under contracts).
 *  We query with contract_id filter if supported, otherwise return empty.
 */
export function useContractObligations(contractId: string) {
  return useQuery({
    queryKey: contractDetailKeys.obligations(contractId),
    queryFn: async () => {
      try {
        const res = await api.get<{ obligations: Obligation[] }>(`/obligations/?contract_id=${contractId}`);
        return res;
      } catch {
        try {
          const res = await api.get<Obligation[]>(`/obligations/`);
          const all = Array.isArray(res) ? res : [];
          return { obligations: all };
        } catch {
          return { obligations: [] };
        }
      }
    },
    enabled: !!contractId,
    staleTime: 60_000,
  });
}

/** Fetch document versions.
 *  Backend: versions live under /reviews/{review_id}/versions.
 */
export function useContractVersions(contractId: string) {
  return useQuery({
    queryKey: contractDetailKeys.versions(contractId),
    queryFn: async () => {
      try {
        const res = await api.get<DocumentVersion[]>(`/reviews/${contractId}/versions`);
        const items = Array.isArray(res) ? res : [];
        return { versions: items };
      } catch {
        return { versions: [] };
      }
    },
    enabled: !!contractId,
    staleTime: 60_000,
  });
}

// ── Mutations ───────────────────────────────────────────────────────────────

/** Resolve a finding. */
export function useResolveFinding(contractId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (findingId: string) =>
      api.post(`/reviews/${contractId}/findings/${findingId}/resolve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contractDetailKeys.findings(contractId) });
      queryClient.invalidateQueries({ queryKey: contractDetailKeys.activity(contractId) });
    },
  });
}

/** Dismiss a finding. */
export function useDismissFinding(contractId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (findingId: string) =>
      api.post(`/reviews/${contractId}/findings/${findingId}/dismiss`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contractDetailKeys.findings(contractId) });
      queryClient.invalidateQueries({ queryKey: contractDetailKeys.activity(contractId) });
    },
  });
}

/** Add a comment. */
export function useAddComment(contractId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      content: string;
      parent_id?: string;
      page_number?: number;
      chunk_id?: string;
      mentions?: string[];
    }) => api.post(`/contracts/${contractId}/comments`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contractDetailKeys.comments(contractId) });
      queryClient.invalidateQueries({ queryKey: contractDetailKeys.activity(contractId) });
    },
  });
}

/** Resolve a comment thread. */
export function useResolveComment(contractId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) =>
      api.post(`/contracts/${contractId}/comments/${commentId}/resolve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contractDetailKeys.comments(contractId) });
    },
  });
}
