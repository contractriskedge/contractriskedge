/**
 * WorkflowTimelinePanel — full audit-grade timeline of the contract's
 * workflow journey: stage transitions, assignments, escalations, approvals,
 * rejections, and reviewer changes.
 *
 * Source of truth: the backend's review status history, assignments,
 * escalations, and approvals. Surfaces as a vertical timeline with
 * user/role/action/previous→new/reason/timestamp for every event.
 *
 * The data is gathered by WorkflowTimelinePanel's parent (ContractDetailWorkspace)
 * which already loads assignments/approvals/escalations; the component
 * normalises them into a single timeline.
 */

"use client";

import React, { useMemo } from "react";
import {
  Clock, User, GitBranch, ArrowRight, AlertTriangle, CheckCircle2, XCircle,
  ChevronRight, Shield, Activity,
} from "lucide-react";
import { formatDate, formatTime } from "@/lib/date-utils";

export interface TimelineEvent {
  id: string;
  type:
    | "created"
    | "ai_analyzed"
    | "assigned"
    | "reassigned"
    | "stage_changed"
    | "escalated"
    | "approved"
    | "rejected"
    | "completed"
    | "comment";
  timestamp: string;
  actor: string;
  actorId?: string;
  actorRole?: string;
  fromValue?: string;
  toValue?: string;
  reason?: string;
  meta?: Record<string, unknown>;
}

interface WorkflowTimelinePanelProps {
  events: TimelineEvent[];
  /** Optional cap on events to render (default 50) */
  maxEvents?: number;
}

const ICON_MAP: Record<TimelineEvent["type"], React.ElementType> = {
  created: GitBranch,
  ai_analyzed: Activity,
  assigned: User,
  reassigned: User,
  stage_changed: ChevronRight,
  escalated: AlertTriangle,
  approved: CheckCircle2,
  rejected: XCircle,
  completed: Shield,
  comment: Clock,
};

const COLOR_MAP: Record<TimelineEvent["type"], { ring: string; icon: string; bg: string; text: string }> = {
  created:        { ring: "ring-blue-200",    icon: "text-blue-600",    bg: "bg-blue-50",    text: "text-blue-700" },
  ai_analyzed:    { ring: "ring-purple-200",  icon: "text-purple-600",  bg: "bg-purple-50",  text: "text-purple-700" },
  assigned:       { ring: "ring-cyan-200",    icon: "text-cyan-600",    bg: "bg-cyan-50",    text: "text-cyan-700" },
  reassigned:     { ring: "ring-indigo-200",  icon: "text-indigo-600",  bg: "bg-indigo-50",  text: "text-indigo-700" },
  stage_changed:  { ring: "ring-amber-200",   icon: "text-amber-600",   bg: "bg-amber-50",   text: "text-amber-700" },
  escalated:      { ring: "ring-red-200",     icon: "text-red-600",     bg: "bg-red-50",     text: "text-red-700" },
  approved:       { ring: "ring-emerald-200", icon: "text-emerald-600", bg: "bg-emerald-50", text: "text-emerald-700" },
  rejected:       { ring: "ring-rose-200",    icon: "text-rose-600",    bg: "bg-rose-50",    text: "text-rose-700" },
  completed:      { ring: "ring-green-200",   icon: "text-green-600",   bg: "bg-green-50",   text: "text-green-700" },
  comment:        { ring: "ring-gray-200",    icon: "text-gray-500",    bg: "bg-gray-50",    text: "text-gray-700" },
};

const TYPE_LABEL: Record<TimelineEvent["type"], string> = {
  created: "Contract Created",
  ai_analyzed: "AI Analysis Completed",
  assigned: "Assigned to Reviewer",
  reassigned: "Reassigned",
  stage_changed: "Workflow Stage Advanced",
  escalated: "Escalated",
  approved: "Approved",
  rejected: "Rejected",
  completed: "Completed",
  comment: "Commented",
};

function initials(name: string): string {
  if (!name) return "?";
  return name.split(" ").map((p) => p[0] || "").slice(0, 2).join("").toUpperCase();
}

export function WorkflowTimelinePanel({ events, maxEvents = 50 }: WorkflowTimelinePanelProps) {
  const sorted = useMemo(
    () =>
      [...events]
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
        .slice(0, maxEvents),
    [events, maxEvents],
  );

  if (sorted.length === 0) {
    return (
      <div className="text-center py-6 text-gray-400">
        <Clock className="w-6 h-6 mx-auto mb-2 text-gray-300" />
        <p className="text-xs">No workflow activity yet.</p>
        <p className="text-[10px] text-gray-400 mt-1">
          Status transitions, assignments, and escalations will appear here as the contract moves through review.
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-[15px] top-2 bottom-2 w-px bg-gray-200 dark:bg-navy-700" aria-hidden="true" />

      <ol className="space-y-3" data-testid="workflow-timeline">
        {sorted.map((ev) => {
          const Icon = ICON_MAP[ev.type];
          const colors = COLOR_MAP[ev.type];
          return (
            <li key={ev.id} className="relative pl-9 group" data-event-type={ev.type}>
              {/* Icon dot */}
              <span
                className={`absolute left-0 top-1 w-8 h-8 rounded-full flex items-center justify-center ring-4 ${colors.ring} ${colors.bg}`}
                aria-hidden="true"
              >
                <Icon className={`w-3.5 h-3.5 ${colors.icon}`} />
              </span>

              {/* Card */}
              <div className="rounded-md border border-gray-200 dark:border-navy-700 bg-white dark:bg-navy-800 px-3 py-2 hover:border-gray-300 dark:hover:border-navy-600 transition-colors">
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-[10px] font-semibold uppercase tracking-wider ${colors.text}`}>
                    {TYPE_LABEL[ev.type]}
                  </span>
                  <span className="text-[10px] text-gray-400 tabular-nums whitespace-nowrap" title={formatDate(ev.timestamp)}>
                    {formatTime(ev.timestamp)}
                  </span>
                </div>

                <div className="mt-1 flex items-center gap-1.5 text-[11px] text-gray-700 dark:text-gray-200">
                  <div className="w-5 h-5 rounded-full bg-navy-100 dark:bg-navy-700 text-navy-700 dark:text-navy-200 flex items-center justify-center text-[8px] font-bold flex-shrink-0">
                    {initials(ev.actor)}
                  </div>
                  <span className="font-medium">{ev.actor}</span>
                  {ev.actorRole && (
                    <span className="text-[9px] text-gray-500 dark:text-gray-400">({ev.actorRole})</span>
                  )}
                </div>

                {(ev.fromValue || ev.toValue) && (
                  <div className="mt-1 flex items-center gap-1 text-[10px] text-gray-600 dark:text-gray-300 flex-wrap">
                    {ev.fromValue && (
                      <>
                        <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300">{ev.fromValue}</span>
                        <ArrowRight className="w-2.5 h-2.5 text-gray-400" />
                      </>
                    )}
                    {ev.toValue && (
                      <span className={`px-1.5 py-0.5 rounded ${colors.bg} ${colors.text} font-medium`}>{ev.toValue}</span>
                    )}
                  </div>
                )}

                {ev.reason && (
                  <p className="mt-1 text-[10px] text-gray-500 dark:text-gray-400 italic">
                    “{ev.reason}”
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
