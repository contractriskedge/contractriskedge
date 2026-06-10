/**
 * LifecycleHistoryPanel — derive a contract's lifecycle history from the
 * activity events that the contract-detail endpoint already returns.
 *
 * Surfaces: status transitions, review_started, review_completed, etc.
 * Falls back to a friendly empty state when no lifecycle events exist.
 */

"use client";

import React, { useMemo } from "react";
import { Activity, Clock, CheckCircle2, XCircle, AlertTriangle, GitBranch } from "lucide-react";
import { formatDate } from "@/lib/date-utils";
import type { ActivityEvent } from "./types";

interface LifecycleHistoryPanelProps {
  events: ActivityEvent[];
}

const LIFECYCLE_EVENTS = new Set<ActivityEvent["type"]>([
  "contract_created",
  "contract_uploaded",
  "ai_analysis_started",
  "ai_analysis_completed",
  "status_changed",
  "review_approved",
  "review_rejected",
  "version_created",
  "renewal_approaching",
  "obligation_updated",
  "obligation_created",
  "obligation_completed",
  "obligation_assigned",
  "obligation_overdue",
]);

const ICON_MAP: Record<ActivityEvent["type"], React.ElementType> = {
  contract_created: GitBranch,
  contract_uploaded: GitBranch,
  ai_analysis_started: Activity,
  ai_analysis_completed: Activity,
  finding_resolved: CheckCircle2,
  finding_dismissed: XCircle,
  comment_added: Activity,
  review_assigned: Activity,
  review_approved: CheckCircle2,
  review_rejected: XCircle,
  status_changed: Activity,
  obligation_updated: Clock,
  obligation_created: Clock,
  obligation_completed: CheckCircle2,
  obligation_assigned: Activity,
  obligation_overdue: AlertTriangle,
  renewal_approaching: Clock,
  version_created: GitBranch,
  metadata_updated: Activity,
};

const COLOR_MAP: Record<ActivityEvent["type"], string> = {
  contract_created: "bg-blue-100 text-blue-600",
  contract_uploaded: "bg-indigo-100 text-indigo-600",
  ai_analysis_started: "bg-purple-100 text-purple-600",
  ai_analysis_completed: "bg-purple-100 text-purple-600",
  finding_resolved: "bg-green-100 text-green-600",
  finding_dismissed: "bg-gray-100 text-gray-500",
  comment_added: "bg-teal-100 text-teal-600",
  review_assigned: "bg-blue-100 text-blue-600",
  review_approved: "bg-green-100 text-green-600",
  review_rejected: "bg-red-100 text-red-600",
  status_changed: "bg-gray-100 text-gray-600",
  obligation_updated: "bg-yellow-100 text-yellow-700",
  obligation_created: "bg-cyan-100 text-cyan-600",
  obligation_completed: "bg-green-100 text-green-600",
  obligation_assigned: "bg-blue-100 text-blue-600",
  obligation_overdue: "bg-red-100 text-red-600",
  renewal_approaching: "bg-orange-100 text-orange-600",
  version_created: "bg-blue-100 text-blue-600",
  metadata_updated: "bg-gray-100 text-gray-500",
};

function formatTime(ts: string): string {
  if (!ts) return "—";
  const t = new Date(ts).getTime();
  if (Number.isNaN(t)) return "—";
  const diff = Date.now() - t;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(ts);
}

export function LifecycleHistoryPanel({ events }: LifecycleHistoryPanelProps) {
  const lifecycle = useMemo(
    () =>
      events
        .filter((e) => LIFECYCLE_EVENTS.has(e.type))
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()),
    [events],
  );

  if (lifecycle.length === 0) {
    return (
      <div className="text-center py-6 text-gray-400 text-xs">
        <Clock className="w-6 h-6 mx-auto mb-2 text-gray-300" />
        No lifecycle history yet. Activity will appear here as the contract moves through review.
      </div>
    );
  }

  return (
    <div className="relative pl-6">
      <div className="absolute left-2 top-1 bottom-1 w-px bg-gray-200 dark:bg-navy-700" />
      <ul className="space-y-3">
        {lifecycle.map((event) => {
          const Icon = ICON_MAP[event.type] || Activity;
          const color = COLOR_MAP[event.type] || "bg-gray-100 text-gray-500";
          return (
            <li key={event.id} className="relative flex items-start gap-2.5">
              <div className={`relative z-10 -ml-6 w-5 h-5 rounded-full ${color} flex items-center justify-center flex-shrink-0`}>
                <Icon className="w-3 h-3" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-medium text-navy-900 dark:text-white">{event.action}</p>
                <p className="text-[9px] text-gray-500">
                  {event.actor} · {formatTime(event.timestamp)}
                </p>
                {event.details && (
                  <p className="text-[9px] text-gray-500 mt-0.5">{event.details}</p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
