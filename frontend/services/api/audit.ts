/**
 * Audit API — tenant-wide audit log queries and exports.
 */

"use client";

import { api } from "@/services/api/client";

export type AuditOutcomeStatus = "success" | "failure" | "blocked";

export interface AuditEventRecord {
  event_id: string;
  event_type: string;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  actor_id?: string | null;
  description?: string | null;
  correlation_id?: string | null;
  status: AuditOutcomeStatus | string;
  severity: string;
  source?: string | null;
  ip_address?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface AuditQueryResult {
  events: AuditEventRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AuditSummary {
  total_events: number;
  events_by_type: Array<{ event_type: string; count: number }>;
  unique_actors: number;
  period_days: number;
}

export interface AuditExportJob {
  job_id: string;
  status: string;
  output_format: string;
  artifact_count: number;
  checksum?: string | null;
  artifacts?: Array<{ artifact_id: string; filename: string }>;
}

export interface AuditLogQueryParams {
  page?: number;
  page_size?: number;
  event_type?: string;
  actor_id?: string;
  status?: AuditOutcomeStatus | "";
  days?: number;
  from_date?: string;
  to_date?: string;
}

function buildQuery(params?: AuditLogQueryParams): string {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.event_type) searchParams.set("event_type", params.event_type);
  if (params?.actor_id) searchParams.set("actor_id", params.actor_id);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.days) searchParams.set("days", String(params.days));
  if (params?.from_date) searchParams.set("from_date", params.from_date);
  if (params?.to_date) searchParams.set("to_date", params.to_date);
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchAuditEvents(params?: AuditLogQueryParams): Promise<AuditQueryResult> {
  return api.get<AuditQueryResult>(`/audit/events${buildQuery(params)}`);
}

export async function fetchAdminAuditLogs(params?: AuditLogQueryParams): Promise<AuditQueryResult> {
  return api.get<AuditQueryResult>(`/admin/audit-logs${buildQuery(params)}`);
}

export async function fetchAuditSummary(periodDays = 30): Promise<AuditSummary> {
  return api.get<AuditSummary>(`/audit/summary?period_days=${periodDays}`);
}

export async function exportAuditPdf(periodDays = 30): Promise<void> {
  const filename = `audit-report-${new Date().toISOString().slice(0, 10)}.pdf`;
  await api.downloadFile(`/exports/audit?period_days=${periodDays}`, filename);
}

export async function createImmutableAuditExport(body: {
  output_format?: "csv" | "jsonl";
  event_type?: string;
  actor_id?: string;
  from_date?: string;
  to_date?: string;
  export_reason?: string;
}): Promise<AuditExportJob> {
  return api.post<AuditExportJob>("/exports/audit/immutable", {
    output_format: body.output_format ?? "csv",
    event_type: body.event_type || undefined,
    actor_id: body.actor_id || undefined,
    from_date: body.from_date || undefined,
    to_date: body.to_date || undefined,
    export_reason: body.export_reason || "Admin audit export",
  });
}

export async function getImmutableAuditExportJob(jobId: string): Promise<AuditExportJob> {
  return api.get<AuditExportJob>(`/exports/audit/immutable/${jobId}`);
}

export async function downloadImmutableAuditExport(jobId: string, artifactId: string, filename: string): Promise<void> {
  await api.downloadFile(`/exports/audit/immutable/${jobId}/artifact/${artifactId}`, filename);
}
