/**
 * Review Activity Timeline — immutable audit trail of all review events.
 *
 * Shows: upload, analysis started/completed, reviewer assignments,
 * comments, escalations, approvals, re-analysis, status changes.
 *
 * Features:
 * - Icons per event type
 * - Colored event badges
 * - Transition arrows (ai_analyzed → in_review)
 * - Actor names with avatar initials
 * - Timestamps with relative formatting
 * - System events mixed with human actions
 *
 * This becomes the audit UI for enterprise compliance.
 */

"use client";

import React from "react";
import {
  Upload, Cpu, User, MessageSquare, AlertTriangle,
  CheckCircle2, XCircle, RefreshCw, Archive, Clock,
  UserCheck, ArrowUpRight, ThumbsUp, ThumbsDown, Activity,
  FileText, Loader2, Shield, FileEdit,
} from "lucide-react";
import { useReviewHistory, useReviewComments } from "@/services/hooks";
import { useActivity } from "@/components/ai-review/hooks";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";

interface ActivityTimelineProps {
  reviewId: string;
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  review_created: <Upload className="h-4 w-4" />,
  ai_analyzed: <Cpu className="h-4 w-4" />,
  under_review: <UserCheck className="h-4 w-4" />,
  legal_review: <FileText className="h-4 w-4" />,
  procurement_review: <Activity className="h-4 w-4" />,
  security_review: <Shield className="h-4 w-4" />,
  approved: <ThumbsUp className="h-4 w-4" />,
  negotiation_sent: <ArrowUpRight className="h-4 w-4" />,
  executed: <CheckCircle2 className="h-4 w-4" />,
  escalated: <AlertTriangle className="h-4 w-4" />,
  archived: <Archive className="h-4 w-4" />,
  comment: <MessageSquare className="h-4 w-4" />,
  re_analysis: <RefreshCw className="h-4 w-4" />,
  // Governance event types
  finding_resolved: <CheckCircle2 className="h-4 w-4" />,
  redline_accepted: <ThumbsUp className="h-4 w-4" />,
  redline_rejected: <XCircle className="h-4 w-4" />,
  redline_modified: <FileText className="h-4 w-4" />,
  redline_updated: <FileEdit className="h-4 w-4" />,
  version_created: <FileText className="h-4 w-4" />,
  recommendation_applied: <Activity className="h-4 w-4" />,
  status_change: <Activity className="h-4 w-4" />,
};

const EVENT_COLORS: Record<string, string> = {
  review_created: "bg-blue-500",
  ai_analyzed: "bg-purple-500",
  under_review: "bg-indigo-500",
  legal_review: "bg-violet-500",
  procurement_review: "bg-teal-500",
  security_review: "bg-cyan-500",
  approved: "bg-green-500",
  negotiation_sent: "bg-emerald-500",
  executed: "bg-emerald-600",
  escalated: "bg-orange-500",
  archived: "bg-gray-500",
  comment: "bg-teal-500",
  re_analysis: "bg-amber-500",
  // Governance event types
  finding_resolved: "bg-green-500",
  redline_accepted: "bg-emerald-500",
  redline_rejected: "bg-red-500",
  redline_modified: "bg-amber-500",
  redline_updated: "bg-amber-500",
  version_created: "bg-blue-500",
  recommendation_applied: "bg-purple-500",
  status_change: "bg-gray-500",
};

const EVENT_BADGE_COLORS: Record<string, string> = {
  review_created: "bg-blue-100 text-blue-700",
  ai_analyzed: "bg-purple-100 text-purple-700",
  under_review: "bg-indigo-100 text-indigo-700",
  legal_review: "bg-violet-100 text-violet-700",
  procurement_review: "bg-teal-100 text-teal-700",
  security_review: "bg-cyan-100 text-cyan-700",
  approved: "bg-green-100 text-green-700",
  negotiation_sent: "bg-emerald-100 text-emerald-700",
  executed: "bg-emerald-100 text-emerald-700",
  escalated: "bg-orange-100 text-orange-700",
  archived: "bg-gray-100 text-gray-600",
  comment: "bg-teal-100 text-teal-700",
  re_analysis: "bg-amber-100 text-amber-700",
  // Governance event types
  finding_resolved: "bg-green-100 text-green-700",
  redline_accepted: "bg-emerald-100 text-emerald-700",
  redline_rejected: "bg-red-100 text-red-700",
  redline_modified: "bg-amber-100 text-amber-700",
  redline_updated: "bg-amber-100 text-amber-700",
  version_created: "bg-blue-100 text-blue-700",
  recommendation_applied: "bg-purple-100 text-purple-700",
  status_change: "bg-gray-100 text-gray-600",
};

const DEFAULT_COLOR = "bg-gray-400";
const DEFAULT_BADGE = "bg-gray-100 text-gray-600";

function formatTimestamp(ts: string | null | undefined): string {
  if (!ts) return "";
  const d = new Date(ts);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}

function formatStatusLabel(status: string): string {
  return status
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
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
    "bg-blue-100 text-blue-700",
    "bg-purple-100 text-purple-700",
    "bg-green-100 text-green-700",
    "bg-amber-100 text-amber-700",
    "bg-indigo-100 text-indigo-700",
    "bg-rose-100 text-rose-700",
  ];
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash) + id.charCodeAt(i);
  }
  return colors[Math.abs(hash) % colors.length];
}

function eventLabel(type: string): string {
  const labels: Record<string, string> = {
    review_created: "Created",
    ai_analyzed: "AI Analysis",
    review_ready: "Ready",
    in_review: "Assigned",
    approved: "Approved",
    rejected: "Rejected",
    escalated: "Escalated",
    closed: "Closed",
    comment: "Comment",
    re_analysis: "Re-Analysis",
  };
  return labels[type] || formatStatusLabel(type);
}

/** Map governance audit event types to display types. */
function mapGovEventType(eventType: string): string {
  if (eventType.includes("finding") || eventType.includes("feedback")) return "finding_resolved";
  if (eventType.includes("redline.accepted")) return "redline_accepted";
  if (eventType.includes("redline.rejected")) return "redline_rejected";
  if (eventType.includes("redline.modified")) return "redline_modified";
  if (eventType.includes("redline")) return "redline_updated";
  if (eventType.includes("review.approved")) return "approved";
  if (eventType.includes("review.rejected")) return "rejected";
  if (eventType.includes("review.escalated")) return "escalated";
  if (eventType.includes("review.status")) return eventType.split(".").pop() || "status_change";
  if (eventType.includes("review.deleted")) return "archived";
  if (eventType.includes("version")) return "version_created";
  if (eventType.includes("recommendation")) return "recommendation_applied";
  if (eventType.includes("ai.copilot")) return "ai_analyzed";
  return "status_change";
}

export function ActivityTimeline({ reviewId }: ActivityTimelineProps) {
  const historyQuery = useReviewHistory(reviewId);
  const commentsQuery = useReviewComments(reviewId);

  const activityQuery = useActivity(reviewId);
  const history = historyQuery.data?.history ?? [];
  const comments = commentsQuery.data?.comments ?? [];
  const activityEvents = activityQuery.data ?? [];

  // Merge and sort events
  const events: Array<{
    id: string;
    type: string;
    description: string;
    actor: string | null;
    timestamp: string;
    details?: string;
    fromStatus?: string;
    toStatus?: string;
  }> = [];

  // Add history events (status transitions)
  for (const h of history) {
    events.push({
      id: `history-${h.created_at}-${h.to_status}`,
      type: h.to_status,
      description: `Status changed to "${h.to_status.replace(/_/g, " ")}"`,
      actor: h.changed_by,
      timestamp: h.created_at,
      details: h.reason || undefined,
      fromStatus: h.from_status,
      toStatus: h.to_status,
    });
  }

  // Add governance activity events (finding resolutions, redline actions, feedback, etc.)
  for (const ae of activityEvents) {
    const eventType = ae.type || "unknown";
    events.push({
      id: `gov-${ae.id || Math.random()}`,
      type: mapGovEventType(eventType),
      description: ae.details || ae.action || `${eventType}`,
      actor: ae.actor || null,
      timestamp: ae.timestamp || new Date().toISOString(),
      details: ae.action || undefined,
    });
  }

  // Add comment events
  for (const c of comments) {
    events.push({
      id: `comment-${c.comment_id}`,
      type: "comment",
      description: c.body.slice(0, 120) + (c.body.length > 120 ? "..." : ""),
      actor: c.author_id,
      timestamp: c.created_at,
    });
  }

  // Sort by timestamp descending
  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  // Show spinner only when history (the primary data source) is still loading
  const isLoading = historyQuery.isLoading;

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <div className="border-b border-gray-100 px-5 py-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Activity Timeline</h2>
        </div>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      {/* Header */}
      <div className="border-b border-gray-100 px-5 py-4 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Activity Timeline
          </h2>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-400">
            {events.length} events
          </span>
        </div>
      </div>

      {/* Body */}
      <AsyncBoundary
        isLoading={false}
        error={historyQuery.error}
        isEmpty={events.length === 0}
        loadingSkeleton={<CardSkeleton count={4} />}
        emptyMessage="No activity recorded"
        emptyDescription="Review activity will appear here as the review progresses."
        onRetry={() => historyQuery.refetch()}
      >
        <div className="relative px-5 py-4">
          {/* Timeline line */}
          <div className="absolute left-[26px] top-0 h-full w-0.5 bg-gray-200 dark:bg-gray-700" />

          <div className="space-y-0">
            {events.map((event, idx) => {
              const isSystem = event.actor === "system" || event.actor === "routing_engine";
              return (
                <div key={event.id} className="relative flex gap-4 pb-6 last:pb-0">
                  {/* Icon circle */}
                  <div className={`relative z-10 flex h-9 w-9 flex-shrink-0 items-center justify-center text-white ${
                    EVENT_COLORS[event.type] || DEFAULT_COLOR
                  }`}>
                    {EVENT_ICONS[event.type] || <Activity className="h-4 w-4" />}
                  </div>

                  {/* Content */}
                  <div className="min-w-0 flex-1 pt-0.5">
                    {/* Badge + Transition */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        EVENT_BADGE_COLORS[event.type] || DEFAULT_BADGE
                      }`}>
                        {eventLabel(event.type)}
                      </span>
                      {event.fromStatus && event.toStatus && (
                        <span className="text-[11px] text-gray-500 font-mono flex items-center gap-1">
                          <span>{formatStatusLabel(event.fromStatus)}</span>
                          <span className="text-gray-300">→</span>
                          <span className="font-semibold text-gray-700">{formatStatusLabel(event.toStatus)}</span>
                        </span>
                      )}
                    </div>

                    {/* Description */}
                    <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">
                      {event.description}
                      {event.details && (
                        <span className="text-gray-400 italic ml-1">— {event.details}</span>
                      )}
                    </p>

                    {/* Actor + Timestamp */}
                    <div className="mt-1 flex items-center gap-2">
                      <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-semibold ${
                        isSystem ? "bg-gray-100 text-gray-500" : getActorColor(event.actor || "")
                      }`}>
                        {isSystem ? (
                          <Clock className="w-3 h-3" />
                        ) : (
                          getActorInitials(event.actor || "")
                        )}
                      </div>
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                        {isSystem ? "System" : event.actor}
                      </span>
                      <span className="text-[10px] text-gray-400 dark:text-gray-500">
                        {formatTimestamp(event.timestamp)}
                      </span>
                      <span className="text-[10px] text-gray-400 dark:text-gray-500">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </AsyncBoundary>
    </div>
  );
}
