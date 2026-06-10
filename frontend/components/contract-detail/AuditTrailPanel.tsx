/**
 * AuditTrailPanel — enterprise-grade immutable audit trail of all events
 * on a contract, displayed in audit order (newest first).
 *
 * Every row shows:
 *   • User (with avatar initials)
 *   • Role (reviewer / approver / legal ops / executive / system)
 *   • Action (type label, e.g. "Status changed")
 *   • Previous Value → New Value (when applicable)
 *   • Timestamp (relative + absolute on hover)
 *   • Reason (when provided)
 *
 * Source of truth: GET /reviews/{id}/workflow-timeline which returns a
 * merged view of status_history, review_assignments, review_escalations,
 * and review_approvals. The component also tolerates the older activity
 * shape for backwards compatibility.
 */

"use client";

import React, { useMemo } from "react";
import {
  PlusCircle, Upload, Cpu, MessageSquare, AlertTriangle, CheckCircle2, XCircle,
  RefreshCw, Archive, Clock, UserCheck, FileText, Shield, Activity,
  Plus, Edit, Calendar, Link as LinkIcon, ArrowRight, User,
} from "lucide-react";

export interface AuditEvent {
  id: string;
  type: string;
  actor: string;
  role?: string | null;
  action: string;
  timestamp: string;
  /** Previous value (status, assignee, etc.) */
  previous_value?: string | null;
  /** New value (status, assignee, etc.) */
  new_value?: string | null;
  /** Human-readable reason / note */
  reason?: string | null;
  /** Optional arbitrary context */
  meta?: Record<string, unknown>;
}

interface AuditTrailPanelProps {
  events: AuditEvent[];
  /** Max events to render (default 100) */
  maxEvents?: number;
}

const EVENT_CONFIG: Record<string, { icon: React.ElementType; ring: string; bg: string; text: string; label: string }> = {
  contract_created:        { icon: PlusCircle, ring: "ring-blue-200",    bg: "bg-blue-50",    text: "text-blue-700",    label: "Contract Created" },
  contract_uploaded:      { icon: Upload,     ring: "ring-indigo-200",  bg: "bg-indigo-50",  text: "text-indigo-700",  label: "Contract Uploaded" },
  ai_analysis_started:    { icon: Cpu,        ring: "ring-purple-200",  bg: "bg-purple-50",  text: "text-purple-700",  label: "AI Analysis Started" },
  ai_analysis_completed:  { icon: Cpu,        ring: "ring-purple-200",  bg: "bg-purple-50",  text: "text-purple-700",  label: "AI Analysis Completed" },
  ai_analyzed:            { icon: Cpu,        ring: "ring-purple-200",  bg: "bg-purple-50",  text: "text-purple-700",  label: "AI Analysis Completed" },
  finding_resolved:       { icon: CheckCircle2, ring: "ring-green-200", bg: "bg-green-50",   text: "text-green-700",   label: "Finding Resolved" },
  finding_dismissed:      { icon: XCircle,    ring: "ring-gray-200",    bg: "bg-gray-50",    text: "text-gray-700",    label: "Finding Dismissed" },
  comment_added:          { icon: MessageSquare, ring: "ring-teal-200", bg: "bg-teal-50",    text: "text-teal-700",    label: "Comment Added" },
  review_assigned:        { icon: UserCheck,  ring: "ring-cyan-200",    bg: "bg-cyan-50",    text: "text-cyan-700",    label: "Reviewer Assigned" },
  assigned:               { icon: UserCheck,  ring: "ring-cyan-200",    bg: "bg-cyan-50",    text: "text-cyan-700",    label: "Assigned" },
  reassigned:             { icon: UserCheck,  ring: "ring-indigo-200",  bg: "bg-indigo-50",  text: "text-indigo-700",  label: "Reassigned" },
  review_approved:        { icon: CheckCircle2, ring: "ring-emerald-200", bg: "bg-emerald-50", text: "text-emerald-700", label: "Approved" },
  approved:               { icon: CheckCircle2, ring: "ring-emerald-200", bg: "bg-emerald-50", text: "text-emerald-700", label: "Approved" },
  conditionally_approved: { icon: CheckCircle2, ring: "ring-emerald-200", bg: "bg-emerald-50", text: "text-emerald-700", label: "Conditionally Approved" },
  review_rejected:        { icon: XCircle,    ring: "ring-red-200",     bg: "bg-red-50",     text: "text-red-700",     label: "Rejected" },
  rejected:               { icon: XCircle,    ring: "ring-red-200",     bg: "bg-red-50",     text: "text-red-700",     label: "Rejected" },
  status_changed:         { icon: Activity,   ring: "ring-amber-200",   bg: "bg-amber-50",   text: "text-amber-700",   label: "Status Changed" },
  stage_changed:          { icon: Activity,   ring: "ring-amber-200",   bg: "bg-amber-50",   text: "text-amber-700",   label: "Workflow Stage Advanced" },
  obligation_updated:     { icon: Calendar,   ring: "ring-cyan-200",    bg: "bg-cyan-50",    text: "text-cyan-700",    label: "Obligation Updated" },
  renewal_approaching:    { icon: AlertTriangle, ring: "ring-orange-200", bg: "bg-orange-50", text: "text-orange-700", label: "Renewal Approaching" },
  version_created:        { icon: FileText,   ring: "ring-blue-200",    bg: "bg-blue-50",    text: "text-blue-700",    label: "Version Created" },
  metadata_updated:       { icon: Edit,       ring: "ring-gray-200",    bg: "bg-gray-50",    text: "text-gray-700",    label: "Metadata Updated" },
  escalated:              { icon: AlertTriangle, ring: "ring-red-200",  bg: "bg-red-50",     text: "text-red-700",     label: "Escalated" },
  completed:              { icon: Shield,     ring: "ring-green-200",   bg: "bg-green-50",   text: "text-green-700",   label: "Completed" },
};

const DEFAULT_CONFIG = {
  icon: Activity,
  ring: "ring-gray-200",
  bg: "bg-gray-50",
  text: "text-gray-700",
  label: "Event",
};

function getActorInitials(name: string): string {
  if (!name) return "?";
  return name.split(/\s+/).map((p) => p[0] || "").slice(0, 2).join("").toUpperCase();
}

function getActorColor(id: string): string {
  const colors = [
    "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
    "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
    "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
  ];
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = ((hash << 5) - hash) + id.charCodeAt(i);
  return colors[Math.abs(hash) % colors.length];
}

function formatRelativeTime(iso: string): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "—";
  const diff = Date.now() - t;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

function formatAbsolute(iso: string): string {
  if (!iso) return "";
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return "";
  return t.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function AuditTrailPanel({ events, maxEvents = 100 }: AuditTrailPanelProps) {
  const sorted = useMemo(
    () =>
      [...events]
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        .slice(0, maxEvents),
    [events, maxEvents],
  );

  if (sorted.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center p-8">
        <Activity className="w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">No audit events yet</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-sm">
          Status changes, assignments, escalations and approvals will appear here as the contract moves through review.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">
          Audit Trail
        </h3>
        <span className="text-[10px] text-gray-500 dark:text-gray-400">
          {events.length} event{events.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="relative" data-testid="audit-trail">
        {/* Vertical timeline line */}
        <div className="absolute left-[15px] top-2 bottom-2 w-px bg-gray-200 dark:bg-navy-700" aria-hidden="true" />

        <ol className="space-y-2">
          {sorted.map((event) => {
            const config = EVENT_CONFIG[event.type] || DEFAULT_CONFIG;
            const Icon = config.icon;
            return (
              <li key={event.id} className="relative pl-9" data-event-type={event.type}>
                {/* Icon dot */}
                <span className={`absolute left-0 top-1 w-8 h-8 rounded-full flex items-center justify-center ring-4 ${config.ring} ${config.bg}`} aria-hidden="true">
                  <Icon className={`w-3.5 h-3.5 ${config.text}`} />
                </span>

                {/* Card */}
                <div className="rounded-md border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 px-3 py-2">
                  {/* Header row: type label + timestamp */}
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-[10px] font-semibold uppercase tracking-wider ${config.text}`}>
                      {config.label}
                    </span>
                    <span
                      className="text-[10px] text-gray-400 tabular-nums whitespace-nowrap"
                      title={formatAbsolute(event.timestamp)}
                    >
                      {formatRelativeTime(event.timestamp)}
                    </span>
                  </div>

                  {/* User + Role */}
                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-gray-700 dark:text-gray-200">
                    <span className={`w-5 h-5 rounded-full ${getActorColor(event.actor)} flex items-center justify-center text-[8px] font-bold flex-shrink-0`}>
                      {getActorInitials(event.actor)}
                    </span>
                    <User className="w-3 h-3 text-gray-400" />
                    <span className="font-medium">{event.actor || "system"}</span>
                    {event.role && (
                      <span className="text-[9px] text-gray-500 dark:text-gray-400 italic">
                        ({event.role})
                      </span>
                    )}
                  </div>

                  {/* Action description */}
                  {event.action && event.action !== config.label && (
                    <p className="text-[10.5px] text-gray-600 dark:text-gray-300 mt-1">
                      {event.action}
                    </p>
                  )}

                  {/* Previous → New value */}
                  {(event.previous_value || event.new_value) && (
                    <div className="mt-1.5 flex items-center gap-1 text-[10px] flex-wrap">
                      {event.previous_value && (
                        <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300 line-through opacity-70">
                          {event.previous_value.replace(/_/g, " ")}
                        </span>
                      )}
                      {event.previous_value && event.new_value && (
                        <ArrowRight className="w-3 h-3 text-gray-400 flex-shrink-0" />
                      )}
                      {event.new_value && (
                        <span className={`px-1.5 py-0.5 rounded font-medium ${config.bg} ${config.text}`}>
                          {event.new_value.replace(/_/g, " ")}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Reason */}
                  {event.reason && (
                    <p className="mt-1 text-[10px] text-gray-500 dark:text-gray-400 italic">
                      Reason: “{event.reason}”
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
