/**
 * ActivityTimelinePanel — Immutable audit trail of all contract events.
 *
 * Shows: contract creation, uploads, AI analysis, findings resolution,
 * comments, approvals, status changes, obligation updates, version history.
 *
 * Features:
 * - Icons per event type with color coding
 * - Actor names with avatar initials
 * - Timestamps with relative formatting
 * - System events mixed with human actions
 * - Event type badges
 * - Evidence file count and metadata
 * - Richer content display (actor, action, evidence, timestamp)
 * - Empty state when no events
 *
 * CON-06: Activity timeline
 */

"use client";

import React from "react";
import {
  Upload,
  Cpu,
  User,
  MessageSquare,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Archive,
  Clock,
  UserCheck,
  FileText,
  Loader2,
  Shield,
  Activity,
  PlusCircle,
  Edit,
  Calendar,
  Link,
  Paperclip,
} from "lucide-react";
import type { ActivityEvent, ActivityEventType } from "./types";

// ── Event Configuration ─────────────────────────────────────────────────────

const EVENT_CONFIG: Record<ActivityEventType, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  contract_created: { icon: PlusCircle, color: "text-blue-500", bg: "bg-blue-100 dark:bg-blue-900/20", label: "Created" },
  contract_uploaded: { icon: Upload, color: "text-indigo-500", bg: "bg-indigo-100 dark:bg-indigo-900/20", label: "Uploaded" },
  ai_analysis_started: { icon: Cpu, color: "text-purple-500", bg: "bg-purple-100 dark:bg-purple-900/20", label: "AI Analysis Started" },
  ai_analysis_completed: { icon: Cpu, color: "text-purple-500", bg: "bg-purple-100 dark:bg-purple-900/20", label: "AI Analysis Completed" },
  finding_resolved: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-100 dark:bg-green-900/20", label: "Finding Resolved" },
  finding_dismissed: { icon: XCircle, color: "text-gray-500", bg: "bg-gray-100 dark:bg-gray-800", label: "Finding Dismissed" },
  comment_added: { icon: MessageSquare, color: "text-teal-500", bg: "bg-teal-100 dark:bg-teal-900/20", label: "Comment Added" },
  review_assigned: { icon: UserCheck, color: "text-indigo-500", bg: "bg-indigo-100 dark:bg-indigo-900/20", label: "Review Assigned" },
  review_approved: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-100 dark:bg-green-900/20", label: "Approved" },
  review_rejected: { icon: XCircle, color: "text-red-500", bg: "bg-red-100 dark:bg-red-900/20", label: "Rejected" },
  status_changed: { icon: Activity, color: "text-gray-500", bg: "bg-gray-100 dark:bg-gray-800", label: "Status Changed" },
  obligation_updated: { icon: Calendar, color: "text-cyan-500", bg: "bg-cyan-100 dark:bg-cyan-900/20", label: "Obligation Updated" },
  obligation_created: { icon: PlusCircle, color: "text-cyan-500", bg: "bg-cyan-100 dark:bg-cyan-900/20", label: "Obligation Created" },
  obligation_completed: { icon: CheckCircle2, color: "text-cyan-500", bg: "bg-cyan-100 dark:bg-cyan-900/20", label: "Obligation Completed" },
  obligation_assigned: { icon: UserCheck, color: "text-cyan-500", bg: "bg-cyan-100 dark:bg-cyan-900/20", label: "Obligation Assigned" },
  obligation_overdue: { icon: AlertTriangle, color: "text-red-500", bg: "bg-red-100 dark:bg-red-900/20", label: "Obligation Overdue" },
  renewal_approaching: { icon: AlertTriangle, color: "text-orange-500", bg: "bg-orange-100 dark:bg-orange-900/20", label: "Renewal Approaching" },
  version_created: { icon: FileText, color: "text-blue-500", bg: "bg-blue-100 dark:bg-blue-900/20", label: "New Version" },
  metadata_updated: { icon: Edit, color: "text-gray-500", bg: "bg-gray-100 dark:bg-gray-800", label: "Metadata Updated" },
};

const DEFAULT_CONFIG = { icon: Activity, color: "text-gray-400", bg: "bg-gray-100 dark:bg-gray-800", label: "Event" };

// ── Props ───────────────────────────────────────────────────────────────────

interface ActivityTimelinePanelProps {
  events: ActivityEvent[];
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatRelativeTime(timestamp: string): string {
  const d = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatAbsoluteTime(timestamp: string): string {
  const d = new Date(timestamp);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getActorInitials(name: string): string {
  return name
    .split(/[\s._-]+/)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
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
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i);
  }
  return colors[Math.abs(hash) % colors.length];
}

// ── Extract metadata helpers ────────────────────────────────────────────────

function getEvidenceCount(event: ActivityEvent): number | null {
  if (event.metadata?.evidence_count != null) return Number(event.metadata.evidence_count);
  if (event.metadata?.file_count != null) return Number(event.metadata.file_count);
  if (event.metadata?.files != null && Array.isArray(event.metadata.files)) return event.metadata.files.length;
  return null;
}

function getObjectName(event: ActivityEvent): string | null {
  if (event.metadata?.object_name) return String(event.metadata.object_name);
  if (event.metadata?.obligation_title) return String(event.metadata.obligation_title);
  if (event.metadata?.finding_title) return String(event.metadata.finding_title);
  if (event.metadata?.document_name) return String(event.metadata.document_name);
  return null;
}

// ── Component ───────────────────────────────────────────────────────────────

export function ActivityTimelinePanel({ events }: ActivityTimelinePanelProps) {
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <Activity className="w-12 h-12 text-gray-300 dark:text-gray-600 mb-3" />
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">No activity yet</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-xs">
          Activity events such as uploads, AI analysis, comments, and approvals will appear here.
        </p>
      </div>
    );
  }

  // Sort events by timestamp (most recent first)
  const sortedEvents = [...events].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-navy-900 dark:text-white">
          Activity Timeline
        </h3>
        <span className="text-[10px] text-gray-500 dark:text-gray-400">
          {events.length} events
        </span>
      </div>

      <div className="relative">
        {/* Timeline vertical line */}
        <div className="absolute left-4 top-2 bottom-2 w-px bg-gray-200 dark:bg-navy-700" aria-hidden="true" />

        <div className="space-y-0">
          {sortedEvents.map((event, index) => {
            const config = EVENT_CONFIG[event.type] || DEFAULT_CONFIG;
            const Icon = config.icon;
            const evidenceCount = getEvidenceCount(event);
            const objectName = getObjectName(event);

            return (
              <div key={event.id} className="relative flex gap-3 pb-4">
                {/* Timeline dot */}
                <div className="relative z-10 flex-shrink-0">
                  <div className={`w-8 h-8 rounded-full ${config.bg} flex items-center justify-center`}>
                    <Icon className={`w-4 h-4 ${config.color}`} />
                  </div>
                </div>

                {/* Event content — enriched */}
                <div className="flex-1 min-w-0 pt-0.5">
                  {/* Header row: actor + badge + time */}
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`w-5 h-5 rounded-full ${getActorColor(event.actor)} flex items-center justify-center text-[9px] font-bold flex-shrink-0`}>
                      {getActorInitials(event.actor)}
                    </span>
                    <span className="text-[11px] font-medium text-navy-900 dark:text-white">
                      {event.actor}
                    </span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${config.bg} ${config.color} font-medium`}>
                      {config.label}
                    </span>
                    <span className="text-[9px] text-gray-400 dark:text-gray-500 ml-auto whitespace-nowrap" title={formatAbsoluteTime(event.timestamp)}>
                      {formatRelativeTime(event.timestamp)}
                    </span>
                  </div>

                  {/* Object name (e.g., "Insurance Certificate") */}
                  {objectName && (
                    <p className="text-[11px] font-semibold text-navy-800 dark:text-navy-200 ml-7 mb-0.5">
                      {objectName}
                    </p>
                  )}

                  {/* Action description */}
                  <p className="text-[11px] text-gray-700 dark:text-gray-300 ml-7">
                    {event.action}
                  </p>

                  {/* Details / reason */}
                  {event.details && (
                    <p className="text-[10px] text-gray-500 dark:text-gray-400 ml-7 mt-0.5 italic">
                      {event.details}
                    </p>
                  )}

                  {/* Evidence / file count */}
                  {evidenceCount !== null && (
                    <div className="flex items-center gap-1 ml-7 mt-1">
                      <Paperclip className="w-3 h-3 text-gray-400" />
                      <span className="text-[9px] text-gray-500 dark:text-gray-400 font-medium">
                        Evidence: {evidenceCount} file{evidenceCount !== 1 ? "s" : ""}
                      </span>
                    </div>
                  )}

                  {/* Completed timestamp for obligation_completed events */}
                  {(event.type === "obligation_completed" || event.type === "review_approved") && (
                    <div className="flex items-center gap-1 ml-7 mt-0.5">
                      <CheckCircle2 className="w-3 h-3 text-green-500" />
                      <span className="text-[9px] text-green-600 dark:text-green-400 font-medium">
                        Completed: {formatAbsoluteTime(event.timestamp)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
