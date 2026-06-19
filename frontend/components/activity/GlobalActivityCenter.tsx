/**
 * GlobalActivityCenter — Cross-contract activity feed showing all
 * platform events in a single chronological timeline.
 *
 * Shows:
 * - Contract approvals
 * - Review assignments
 * - Obligation completions
 * - Policy updates
 * - AI analysis completions
 * - Escalations
 *
 * Located under Operations → Activity Center in the sidebar.
 */

"use client";

import React, { useState, useMemo } from "react";
import {
  Activity,
  CheckCircle2,
  Clock,
  UserCheck,
  FileText,
  Brain,
  AlertTriangle,
  Shield,
  RefreshCw,
  Loader2,
  Calendar,
  ArrowRight,
  Filter,
  Search,
  ChevronDown,
} from "lucide-react";
import { useReviewDashboard } from "@/services/hooks";
import { StatusBadge } from "@/components/shared/StatusBadge";

// ── Types ───────────────────────────────────────────────────────────────────

interface ActivityItem {
  id: string;
  type: "contract_approved" | "review_assigned" | "obligation_completed" | "policy_updated" | "ai_completed" | "escalated" | "finding_resolved" | "review_rejected" | "contract_uploaded";
  title: string;
  description: string;
  actor: string;
  timestamp: string;
  contractName?: string;
  severity?: "info" | "success" | "warning" | "error";
}

// ── Event config ────────────────────────────────────────────────────────────

const ACTIVITY_CONFIG: Record<ActivityItem["type"], { icon: React.ElementType; color: string; bg: string; label: string }> = {
  contract_approved: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-100 dark:bg-green-900/20", label: "Contract Approved" },
  review_assigned: { icon: UserCheck, color: "text-indigo-500", bg: "bg-indigo-100 dark:bg-indigo-900/20", label: "Review Assigned" },
  obligation_completed: { icon: Calendar, color: "text-cyan-500", bg: "bg-cyan-100 dark:bg-cyan-900/20", label: "Obligation Completed" },
  policy_updated: { icon: Shield, color: "text-purple-500", bg: "bg-purple-100 dark:bg-purple-900/20", label: "Policy Updated" },
  ai_completed: { icon: Brain, color: "text-purple-500", bg: "bg-purple-100 dark:bg-purple-900/20", label: "AI Complete" },
  escalated: { icon: AlertTriangle, color: "text-red-500", bg: "bg-red-100 dark:bg-red-900/20", label: "Escalated" },
  finding_resolved: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-100 dark:bg-green-900/20", label: "Finding Resolved" },
  review_rejected: { icon: AlertTriangle, color: "text-red-500", bg: "bg-red-100 dark:bg-red-900/20", label: "Rejected" },
  contract_uploaded: { icon: FileText, color: "text-blue-500", bg: "bg-blue-100 dark:bg-blue-900/20", label: "Uploaded" },
};

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatTime(ts: string): string {
  const d = new Date(ts);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function formatDate(ts: string): string {
  const d = new Date(ts);
  if (isNaN(d.getTime())) return "—";
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const days = Math.floor(diff / 86400000);

  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function mapActivityType(type: string): ActivityItem["type"] {
  if (type.includes("approved") || type === "review_approved") return "contract_approved";
  if (type.includes("assigned") || type === "review_assigned") return "review_assigned";
  if (type.includes("obligation") && type.includes("completed")) return "obligation_completed";
  if (type.includes("policy")) return "policy_updated";
  if (type.includes("ai") && type.includes("completed")) return "ai_completed";
  if (type.includes("escalated")) return "escalated";
  if (type.includes("finding") && type.includes("resolved")) return "finding_resolved";
  if (type.includes("rejected")) return "review_rejected";
  if (type.includes("upload")) return "contract_uploaded";
  return "contract_approved";
}

// ── Grouped Activity Component ──────────────────────────────────────────────

function ActivityGroup({ date, items }: { date: string; items: ActivityItem[] }) {
  return (
    <div className="mb-4">
      <div className="sticky top-0 z-10 bg-white dark:bg-navy-800 px-4 py-2 border-b border-gray-100 dark:border-navy-700">
        <span className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          {date}
        </span>
      </div>
      <div className="divide-y divide-gray-50 dark:divide-navy-800">
        {items.map((item) => {
          const config = ACTIVITY_CONFIG[item.type];
          const Icon = config.icon;

          return (
            <div key={item.id} className="flex items-start gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-navy-750 transition-colors">
              {/* Icon */}
              <div className={`w-8 h-8 rounded-full ${config.bg} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                <Icon className={`w-4 h-4 ${config.color}`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[10px] font-semibold text-navy-900 dark:text-white">
                    {item.title}
                  </span>
                  <StatusBadge variant="informational" label={config.label} />
                </div>
                <p className="text-[10px] text-gray-600 dark:text-gray-400">
                  {item.description}
                </p>
                {item.actor && (
                  <p className="text-[9px] text-gray-500 dark:text-gray-500 mt-0.5">
                    by {item.actor}
                    {item.contractName && (
                      <> · {item.contractName}</>
                    )}
                  </p>
                )}
              </div>

              {/* Timestamp */}
              <div className="flex flex-col items-end gap-1 flex-shrink-0">
                <span className="text-[10px] font-medium text-navy-700 dark:text-navy-300 tabular-nums">
                  {formatTime(item.timestamp)}
                </span>
                {item.severity && (
                  <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${
                    item.severity === "error" ? "bg-red-100 text-red-700" :
                    item.severity === "warning" ? "bg-amber-100 text-amber-700" :
                    item.severity === "success" ? "bg-green-100 text-green-700" :
                    "bg-gray-100 text-gray-600"
                  }`}>
                    {item.severity}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

interface GlobalActivityCenterProps {
  className?: string;
}

export function GlobalActivityCenter({ className = "" }: GlobalActivityCenterProps) {
  const { data: dashboard, isLoading, error, refetch } = useReviewDashboard();
  const [filter, setFilter] = useState<ActivityItem["type"] | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // ── Transform dashboard activity into enriched items ──────────
  const allActivities: ActivityItem[] = useMemo(() => {
    if (!dashboard?.recent_activity) return [];

    return dashboard.recent_activity.map((a, i) => {
      const mappedType = mapActivityType(a.activity_type);
      return {
        id: `${a.activity_type}-${a.timestamp}-${i}`,
        type: mappedType,
        title: a.description || a.activity_type.replace(/_/g, " "),
        description: a.description || "",
        actor: a.actor || "System",
        timestamp: a.timestamp,
        contractName: undefined,
        severity: mappedType === "escalated" || mappedType === "review_rejected" ? "error" as const
          : mappedType === "contract_approved" || mappedType === "obligation_completed" ? "success" as const
          : "info" as const,
      };
    });
  }, [dashboard]);

  // ── Filter & Search ───────────────────────────────────────────
  const filteredActivities = useMemo(() => {
    let items = allActivities;
    if (filter !== "all") {
      items = items.filter((a) => a.type === filter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      items = items.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          a.description.toLowerCase().includes(q) ||
          a.actor.toLowerCase().includes(q)
      );
    }
    return items;
  }, [allActivities, filter, searchQuery]);

  // ── Group by date ─────────────────────────────────────────────
  const groupedActivities = useMemo(() => {
    const groups: Record<string, ActivityItem[]> = {};
    filteredActivities.forEach((item) => {
      const dateKey = formatDate(item.timestamp);
      if (!groups[dateKey]) groups[dateKey] = [];
      groups[dateKey].push(item);
    });
    return groups;
  }, [filteredActivities]);

  const activityTypes = Array.from(new Set(allActivities.map((a) => a.type)));

  // ── Loading State ─────────────────────────────────────────────
  if (isLoading && !dashboard) {
    return (
      <div className={`flex items-center justify-center h-64 ${className}`}>
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading activity feed...</p>
        </div>
      </div>
    );
  }

  // ── Error State ───────────────────────────────────────────────
  if (error && !dashboard) {
    return (
      <div className={`flex items-center justify-center h-64 ${className}`}>
        <div className="text-center">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load activity</p>
          <button onClick={() => refetch()} className="text-xs font-medium text-blue-600 hover:text-blue-700">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm ${className}`}>
      {/* ── Header ── */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-navy-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-navy-600 dark:text-navy-300" />
            <h2 className="text-sm font-bold text-navy-900 dark:text-white">Activity Center</h2>
            <span className="text-[10px] text-gray-500 dark:text-gray-400">
              {allActivities.length} events
            </span>
          </div>
          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-2">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search activity..."
            className="w-full pl-8 pr-3 py-1.5 text-[11px] border border-gray-200 dark:border-navy-600 rounded-lg bg-gray-50 dark:bg-navy-900 text-navy-900 dark:text-white placeholder-gray-400 focus:border-navy-400 focus:ring-1 focus:ring-navy-400 outline-none"
          />
        </div>

        {/* Filter chips */}
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => setFilter("all")}
            className={`px-2 py-0.5 rounded text-[9px] font-medium transition-colors ${
              filter === "all" ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-navy-700 dark:text-gray-300 dark:hover:bg-navy-600"
            }`}
          >
            All
          </button>
          {activityTypes.map((type) => {
            const cfg = ACTIVITY_CONFIG[type];
            return (
              <button
                key={type}
                onClick={() => setFilter(type)}
                className={`px-2 py-0.5 rounded text-[9px] font-medium transition-colors capitalize ${
                  filter === type ? "bg-navy-700 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-navy-700 dark:text-gray-300 dark:hover:bg-navy-600"
                }`}
              >
                {cfg.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Activity List ── */}
      <div className="flex-1 overflow-y-auto">
        {filteredActivities.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-12 text-center">
            <Activity className="w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">No activity found</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {searchQuery ? "Try a different search term." : "Events will appear here in real time."}
            </p>
          </div>
        ) : (
          Object.entries(groupedActivities).map(([date, items]) => (
            <ActivityGroup key={date} date={date} items={items} />
          ))
        )}
      </div>

      {/* ── Footer ── */}
      <div className="px-4 py-2 border-t border-gray-100 dark:border-navy-700 text-center">
        <span className="text-[9px] text-gray-400">
          {filteredActivities.length} of {allActivities.length} events
          {dashboard && ` · Last updated ${formatTime(dashboard?.recent_activity?.[0]?.timestamp || "")}`}
        </span>
      </div>
    </div>
  );
}
