"use client";

import React, { useMemo, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  FileSearch, Download, RefreshCw, Loader2, AlertCircle,
  CheckCircle2, XCircle, ShieldAlert, Filter,
} from "lucide-react";
import {
  fetchAdminAuditLogs,
  fetchAuditSummary,
  exportAuditPdf,
  createImmutableAuditExport,
  downloadImmutableAuditExport,
  type AuditEventRecord,
  type AuditOutcomeStatus,
} from "@/services/api/audit";

const STATUS_OPTIONS: Array<{ id: "" | AuditOutcomeStatus; label: string }> = [
  { id: "", label: "All statuses" },
  { id: "success", label: "Success" },
  { id: "failure", label: "Failure" },
  { id: "blocked", label: "Blocked" },
];

const PERIOD_OPTIONS = [
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
];

function statusBadge(status: string) {
  switch (status) {
    case "failure":
      return "bg-orange-50 text-orange-700";
    case "blocked":
      return "bg-red-50 text-red-700";
    default:
      return "bg-green-50 text-green-700";
  }
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function AuditReportsPanel() {
  const [page, setPage] = useState(1);
  const [days, setDays] = useState(30);
  const [status, setStatus] = useState<"" | AuditOutcomeStatus>("");
  const [eventType, setEventType] = useState("");
  const [actorId, setActorId] = useState("");
  const [exportMessage, setExportMessage] = useState<string | null>(null);

  const queryParams = useMemo(
    () => ({
      page,
      page_size: 50,
      days,
      status: status || undefined,
      event_type: eventType || undefined,
      actor_id: actorId || undefined,
    }),
    [page, days, status, eventType, actorId],
  );

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["admin", "audit-reports", queryParams],
    queryFn: () => fetchAdminAuditLogs(queryParams),
    staleTime: 30_000,
  });

  const { data: summary } = useQuery({
    queryKey: ["admin", "audit-summary", days],
    queryFn: () => fetchAuditSummary(days),
    staleTime: 60_000,
  });

  const exportCsvMutation = useMutation({
    mutationFn: async () => {
      const job = await createImmutableAuditExport({
        output_format: "csv",
        event_type: eventType || undefined,
        actor_id: actorId || undefined,
        export_reason: `Admin CSV export (${days} day window)`,
      });
      const artifactId = job.artifacts?.[0]?.artifact_id;
      if (!artifactId) {
        throw new Error("No export artifact available");
      }
      await downloadImmutableAuditExport(
        job.job_id,
        artifactId,
        `audit-export-${new Date().toISOString().slice(0, 10)}.csv`,
      );
      return job;
    },
    onSuccess: () => setExportMessage("CSV export downloaded successfully."),
    onError: (err: Error) => setExportMessage(err.message || "CSV export failed."),
  });

  const exportPdfMutation = useMutation({
    mutationFn: () => exportAuditPdf(days),
    onSuccess: () => setExportMessage("PDF audit report downloaded successfully."),
    onError: (err: Error) => setExportMessage(err.message || "PDF export failed."),
  });

  const events = data?.events ?? [];
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SummaryCard label="Total events" value={summary?.total_events ?? data?.total ?? 0} />
        <SummaryCard label="Unique actors" value={summary?.unique_actors ?? 0} />
        <SummaryCard label="On page (failures)" value={events.filter((e) => e.status === "failure").length} accent="text-orange-600" />
        <SummaryCard label="On page (blocked)" value={events.filter((e) => e.status === "blocked").length} accent="text-red-600" />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 mr-2">
            <FileSearch className="w-4 h-4 text-navy-700" />
            <h3 className="text-sm font-semibold text-navy-900">Enterprise Audit Log</h3>
          </div>

          <div className="flex items-center gap-1 text-[10px] text-gray-500">
            <Filter className="w-3 h-3" />
            Period:
          </div>
          {PERIOD_OPTIONS.map((p) => (
            <button
              key={p.days}
              onClick={() => { setDays(p.days); setPage(1); }}
              className={`text-[10px] px-2 py-1 rounded-full ${days === p.days ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
            >
              {p.label}
            </button>
          ))}

          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value as "" | AuditOutcomeStatus); setPage(1); }}
            className="text-[10px] border border-gray-200 rounded-lg px-2 py-1 bg-white"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.id || "all"} value={opt.id}>{opt.label}</option>
            ))}
          </select>

          <input
            value={eventType}
            onChange={(e) => { setEventType(e.target.value); setPage(1); }}
            placeholder="Event type…"
            className="text-[10px] border border-gray-200 rounded-lg px-2 py-1 w-36"
          />
          <input
            value={actorId}
            onChange={(e) => { setActorId(e.target.value); setPage(1); }}
            placeholder="Actor ID…"
            className="text-[10px] border border-gray-200 rounded-lg px-2 py-1 w-32"
          />

          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              {isFetching ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
              Refresh
            </button>
            <button
              onClick={() => exportPdfMutation.mutate()}
              disabled={exportPdfMutation.isPending}
              className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              {exportPdfMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
              PDF
            </button>
            <button
              onClick={() => exportCsvMutation.mutate()}
              disabled={exportCsvMutation.isPending}
              className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800"
            >
              {exportCsvMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
              Export CSV
            </button>
          </div>
        </div>

        {exportMessage && (
          <div className="mx-4 mt-3 px-3 py-2 rounded-lg bg-blue-50 text-[11px] text-blue-800 border border-blue-100">
            {exportMessage}
          </div>
        )}

        {error && (
          <div className="mx-4 mt-3 px-3 py-2 rounded-lg bg-red-50 text-[11px] text-red-700 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            Failed to load audit logs. Sign in as Admin (audit:read permission required).
          </div>
        )}

        <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
          <table className="w-full text-left">
            <thead className="sticky top-0 bg-gray-50 border-b border-gray-100">
              <tr className="text-[10px] uppercase tracking-wide text-gray-500">
                <th className="px-4 py-2 font-semibold">Time</th>
                <th className="px-4 py-2 font-semibold">Status</th>
                <th className="px-4 py-2 font-semibold">Event</th>
                <th className="px-4 py-2 font-semibold">Actor</th>
                <th className="px-4 py-2 font-semibold">Resource</th>
                <th className="px-4 py-2 font-semibold">Details / Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-[11px] text-gray-500">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                    Loading audit events…
                  </td>
                </tr>
              )}
              {!isLoading && events.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-[11px] text-gray-500">
                    No audit events match the current filters.
                  </td>
                </tr>
              )}
              {events.map((event) => (
                <AuditRow key={event.event_id} event={event} />
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between text-[10px] text-gray-500">
          <span>
            Page {data?.page ?? page} of {totalPages} · {data?.total ?? 0} events
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-2 py-1 rounded border border-gray-200 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-2 py-1 rounded border border-gray-200 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="p-3 bg-white border border-gray-200 rounded-lg">
      <p className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-xl font-semibold mt-1 ${accent ?? "text-navy-900"}`}>{value}</p>
    </div>
  );
}

function AuditRow({ event }: { event: AuditEventRecord }) {
  const StatusIcon =
    event.status === "failure" ? XCircle :
    event.status === "blocked" ? ShieldAlert :
    CheckCircle2;

  return (
    <tr className="hover:bg-gray-50 text-[11px]">
      <td className="px-4 py-2 text-gray-500 whitespace-nowrap">{formatTimestamp(event.created_at)}</td>
      <td className="px-4 py-2">
        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium ${statusBadge(event.status)}`}>
          <StatusIcon className="w-3 h-3" />
          {event.status}
        </span>
      </td>
      <td className="px-4 py-2 font-medium text-gray-800">{event.event_type}</td>
      <td className="px-4 py-2 text-gray-600">{event.actor_id || "—"}</td>
      <td className="px-4 py-2 text-gray-600">
        {event.resource_type}
        {event.resource_id ? ` · ${event.resource_id.slice(0, 8)}…` : ""}
      </td>
      <td className="px-4 py-2 text-gray-500 max-w-xs truncate" title={event.error_message || event.description || ""}>
        {event.error_message || event.description || event.action}
      </td>
    </tr>
  );
}
