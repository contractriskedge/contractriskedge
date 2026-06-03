/**
 * AuditTrailSection — Activity timeline, reviewer actions, system events.
 *
 * Shows:
 * - Chronological activity feed
 * - Event type icons with semantic colors
 * - Actor names with initials
 * - Relative timestamps
 * - Event details on expand
 * - Filters: user, date, action, severity
 * - Export: CSV/PDF
 * - Status badges: resolved, escalated, approved, rejected
 */

"use client";

import React, { useState, useMemo, useEffect } from "react";
import {
  Activity, Upload, Cpu, User, MessageSquare, AlertTriangle,
  CheckCircle2, XCircle, RefreshCw, UserCheck, ArrowUpRight,
  ThumbsUp, FileText, Clock, Shield, PlusCircle,
  ChevronDown, ChevronUp, Search, Download, Filter,
} from "lucide-react";
import { useReviewContext } from "./ReviewContext";
import { useAuditTrailEvents } from "./hooks";

const EVENT_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  review_created: { icon: PlusCircle, color: "text-blue-500", bg: "bg-blue-100 dark:bg-blue-900/20", label: "Created" },
  ai_analysis_completed: { icon: Cpu, color: "text-purple-500", bg: "bg-purple-100 dark:bg-purple-900/20", label: "AI Analysis" },
  finding_resolved: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-100 dark:bg-green-900/20", label: "Resolved" },
  finding_dismissed: { icon: XCircle, color: "text-gray-500", bg: "bg-gray-100 dark:bg-gray-800", label: "Dismissed" },
  finding_feedback: { icon: ThumbsUp, color: "text-amber-500", bg: "bg-amber-100 dark:bg-amber-900/20", label: "Feedback" },
  comment_added: { icon: MessageSquare, color: "text-teal-500", bg: "bg-teal-100 dark:bg-teal-900/20", label: "Comment" },
  review_assigned: { icon: UserCheck, color: "text-indigo-500", bg: "bg-indigo-100 dark:bg-indigo-900/20", label: "Assigned" },
  review_approved: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-100 dark:bg-green-900/20", label: "Approved" },
  review_rejected: { icon: XCircle, color: "text-red-500", bg: "bg-red-100 dark:bg-red-900/20", label: "Rejected" },
  review_escalated: { icon: AlertTriangle, color: "text-orange-500", bg: "bg-orange-100 dark:bg-orange-900/20", label: "Escalated" },
  status_changed: { icon: Activity, color: "text-amber-500", bg: "bg-amber-100 dark:bg-amber-900/20", label: "Status" },
  re_analysis: { icon: RefreshCw, color: "text-cyan-500", bg: "bg-cyan-100 dark:bg-cyan-900/20", label: "Re-Analysis" },
  policy_waived: { icon: Shield, color: "text-gray-500", bg: "bg-gray-100 dark:bg-gray-800", label: "Waived" },
  recommendation_applied: { icon: CheckCircle2, color: "text-emerald-500", bg: "bg-emerald-100 dark:bg-emerald-900/20", label: "Applied" },
  version_created: { icon: FileText, color: "text-blue-500", bg: "bg-blue-100 dark:bg-blue-900/20", label: "Version" },
};

const DEFAULT_CONFIG = { icon: Activity, color: "text-gray-400", bg: "bg-gray-100 dark:bg-gray-800", label: "Event" };

// ── Status filter types ────────────────────────────────────────────────────

const STATUS_FILTERS = [
  { value: "", label: "All Events" },
  { value: "resolved", label: "Resolved" },
  { value: "escalated", label: "Escalated" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
] as const;

export function AuditTrailSection() {
  const { selectedReviewId, findings } = useReviewContext();
  const { events, isLoading: isActivityLoading, dataSource, hadSampleFallback } = useAuditTrailEvents(
    selectedReviewId ?? "",
    findings,
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [actorFilter, setActorFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    setSearchQuery("");
    setActorFilter("");
    setStatusFilter("");
  }, [selectedReviewId]);

  // ── Unique actors for filter dropdown ───────────────────────────────

  const uniqueActors = useMemo(() => {
    const set = new Set(events.map(e => e.actor));
    return Array.from(set).sort();
  }, [events]);

  // ── Filtered events ─────────────────────────────────────────────────

  const filtered = useMemo(() => {
    let result = events;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(e =>
        (e.action || "").toLowerCase().includes(q) ||
        (e.details && e.details.toLowerCase().includes(q)) ||
        e.type.toLowerCase().includes(q)
      );
    }

    if (actorFilter) {
      result = result.filter(e => e.actor === actorFilter);
    }

    if (statusFilter) {
      result = result.filter(e => e.type.includes(statusFilter));
    }

    return result;
  }, [events, searchQuery, actorFilter, statusFilter]);

  // ── Export to CSV ───────────────────────────────────────────────────

  const handleExportCSV = () => {
    const header = "Timestamp,Actor,Action,Details,Type\n";
    const rows = filtered.map(e =>
      `"${e.timestamp}","${e.actor}","${e.action}","${(e.details || "").replace(/"/g, '""')}","${e.type}"`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = () => {
    // Simple printable version
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;
    const content = filtered.map(e =>
      `<tr><td>${formatTime(e.timestamp)}</td><td>${e.actor}</td><td>${e.action}</td><td>${e.details || ""}</td><td>${e.type}</td></tr>`
    ).join("");
    printWindow.document.write(`
      <html><head><title>Audit Log</title>
      <style>body{font-family:system-ui;font-size:11px;padding:20px}
      table{width:100%;border-collapse:collapse}
      th,td{border:1px solid #ddd;padding:6px;text-align:left}
      th{background:#f5f5f5}</style></head>
      <body><h2>Audit Log — ${new Date().toLocaleDateString()}</h2>
      <table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Details</th><th>Type</th></tr></thead>
      <tbody>${content}</tbody></table></body></html>
    `);
    printWindow.document.close();
    printWindow.print();
  };

  return (
    <div className="p-4">
      {hadSampleFallback && (
        <div className="mb-3 px-3 py-2 rounded-lg border border-amber-200 bg-amber-50 text-[10px] text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-100">
          <span className="font-semibold">Demo audit data is off.</span>{" "}
          Placeholders like Legal Reviewer A / find-009 are mock seed data (not your resolves).
          Your actions are stored on findings and will show here when the audit API returns them.
        </div>
      )}
      {!hadSampleFallback && dataSource === "finding-derived" && (
        <div className="mb-3 px-3 py-2 rounded-lg border border-blue-200 bg-blue-50 text-[10px] text-blue-900 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-100">
          <span className="font-semibold">From your review.</span>{" "}
          Showing resolve/dismiss actions from findings. The server audit API returned no events yet.
        </div>
      )}
      {/* ── Toolbar: Search + Filters + Export ─────────────────────────── */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="relative flex-1 min-w-[160px]">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
          <input type="text" value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search activity..." className="w-full pl-7 pr-2 py-1.5 text-[10px] bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-700 rounded-lg text-navy-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-navy-400" />
        </div>
        <select value={actorFilter} onChange={e => setActorFilter(e.target.value)}
          className="text-[9px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700 text-navy-900 dark:text-white">
          <option value="">All Users</option>
          {uniqueActors.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="text-[9px] px-2 py-1.5 rounded-lg border border-gray-200 dark:border-navy-600 bg-white dark:bg-navy-700 text-navy-900 dark:text-white">
          {STATUS_FILTERS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <div className="flex items-center gap-1">
          <button onClick={handleExportCSV}
            className="flex items-center gap-1 px-2 py-1.5 text-[9px] font-medium rounded-lg bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 transition-colors">
            <Download className="w-3 h-3" /> CSV
          </button>
          <button onClick={handleExportPDF}
            className="flex items-center gap-1 px-2 py-1.5 text-[9px] font-medium rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors">
            <FileText className="w-3 h-3" /> PDF
          </button>
        </div>
      </div>

      {/* ── Timeline ──────────────────────────────────────────────────── */}
      <div className="relative">
        <div className="absolute left-4 top-2 bottom-2 w-px bg-gray-200 dark:bg-navy-700" />
        {isActivityLoading && events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Activity className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2 animate-pulse" />
            <p className="text-xs text-gray-500">Loading activity…</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Activity className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
            <p className="text-xs text-gray-500">
              {events.length > 0 ? "No events match the current filters" : "No activity recorded"}
            </p>
            {events.length > 0 && (searchQuery || actorFilter || statusFilter) && (
              <button
                type="button"
                onClick={() => { setSearchQuery(""); setActorFilter(""); setStatusFilter(""); }}
                className="mt-2 text-[9px] text-navy-600 hover:underline dark:text-navy-300"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-0">
            {filtered.map((event, i) => {
              const config = EVENT_CONFIG[event.type] || DEFAULT_CONFIG;
              const Icon = config.icon;
              return (
                <div key={event.id} className="relative flex gap-2.5 pb-3">
                  <div className="relative z-10 flex-shrink-0">
                    <div className={`w-8 h-8 rounded-full ${config.bg} flex items-center justify-center`}>
                      <Icon className={`w-4 h-4 ${config.color}`} />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0 pt-0.5">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="w-4 h-4 rounded-full bg-gray-100 dark:bg-navy-700 flex items-center justify-center text-[6px] font-bold text-gray-500 flex-shrink-0">
                        {event.actor_initials}
                      </span>
                      <span className="text-[10px] font-medium text-navy-900 dark:text-white">{event.actor}</span>
                      <span className={`text-[7px] px-1 py-0.5 rounded-full ${config.bg} ${config.color} font-medium`}>{config.label}</span>
                      <span className="text-[7px] text-gray-400 ml-auto whitespace-nowrap">{formatTime(event.timestamp)}</span>
                    </div>
                    <p className="text-[9px] text-gray-700 dark:text-gray-300 ml-5">{event.action}</p>
                    {event.details && <p className="text-[8px] text-gray-400 ml-5 mt-0.5">{event.details}</p>}
                    {/* Before / After state changes */}
                    {event.before_state && event.after_state && (
                      <div className="ml-5 mt-1 flex items-center gap-2 text-[7px]">
                        <span className="px-1 py-0.5 rounded bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 line-through font-mono">
                          {event.before_state}
                        </span>
                        <ArrowUpRight className="w-2 h-2 text-gray-400" />
                        <span className="px-1 py-0.5 rounded bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400 font-mono">
                          {event.after_state}
                        </span>
                      </div>
                    )}
                    {/* Object reference */}
                    {event.object_type && event.object_id && (
                      <p className="text-[7px] text-gray-400 ml-5 mt-0.5 font-mono">
                        {event.object_type}: {event.object_id.slice(0, 8)}…
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Summary Bar ────────────────────────────────────────────────── */}
      {filtered.length > 0 && (
        <div className="mt-3 pt-2 border-t border-gray-100 dark:border-navy-700 flex items-center gap-3 text-[8px] text-gray-400">
          <span>{filtered.length} events</span>
          <span>·</span>
          <span className="flex items-center gap-1">
            <CheckCircle2 className="w-2.5 h-2.5 text-green-500" /> {filtered.filter(e => e.type.includes("resolved") || e.type.includes("approved")).length} resolved
          </span>
          <span className="flex items-center gap-1">
            <AlertTriangle className="w-2.5 h-2.5 text-orange-500" /> {filtered.filter(e => e.type.includes("escalated")).length} escalated
          </span>
          <span className="flex items-center gap-1">
            <XCircle className="w-2.5 h-2.5 text-red-500" /> {filtered.filter(e => e.type.includes("rejected")).length} rejected
          </span>
        </div>
      )}
    </div>
  );
}

function formatTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}
