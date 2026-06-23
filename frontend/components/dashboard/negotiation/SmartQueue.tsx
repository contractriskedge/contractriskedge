"use client";

import React, { useMemo } from "react";
import { motion } from "framer-motion";
import {
  User, AlertTriangle, Clock, ArrowUpCircle, CheckCircle,
  Hourglass, List, Search,
} from "lucide-react";

// ── Types ────────────────────────────────────────────────────────

export interface SmartQueueFinding {
  id: string;
  title: string;
  severity: string;
  status: string;
  riskLevel?: string;
  assignee?: string | null;
  dueDate?: string | null;
  escalationLevel?: number;
  category?: string;
  updatedAt?: string | null;
}

export type SmartQueueFilter =
  | "all"
  | "my-findings"
  | "high-risk"
  | "due-today"
  | "waiting-me"
  | "waiting-vendor"
  | "escalated"
  | "completed-today";

interface SmartQueueProps {
  findings: SmartQueueFinding[];
  activeFilter: SmartQueueFilter;
  onFilterChange: (filter: SmartQueueFilter) => void;
  currentUserId?: string;
  onFindingClick: (findingId: string) => void;
  activeFindingId?: string | null;
}

// ── Filter Definitions ───────────────────────────────────────────

interface FilterDef {
  id: SmartQueueFilter;
  label: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
}

const FILTERS: FilterDef[] = [
  { id: "all", label: "All Findings", icon: <List className="w-3 h-3" />, color: "text-navy-600", bgColor: "bg-navy-50" },
  { id: "my-findings", label: "My Findings", icon: <User className="w-3 h-3" />, color: "text-blue-600", bgColor: "bg-blue-50" },
  { id: "high-risk", label: "High Risk", icon: <AlertTriangle className="w-3 h-3" />, color: "text-red-600", bgColor: "bg-red-50" },
  { id: "due-today", label: "Due Today", icon: <Clock className="w-3 h-3" />, color: "text-amber-600", bgColor: "bg-amber-50" },
  { id: "waiting-me", label: "Waiting on Me", icon: <Hourglass className="w-3 h-3" />, color: "text-purple-600", bgColor: "bg-purple-50" },
  { id: "waiting-vendor", label: "Waiting on Vendor", icon: <Hourglass className="w-3 h-3" />, color: "text-teal-600", bgColor: "bg-teal-50" },
  { id: "escalated", label: "Escalated", icon: <ArrowUpCircle className="w-3 h-3" />, color: "text-red-600", bgColor: "bg-red-50" },
  { id: "completed-today", label: "Completed Today", icon: <CheckCircle className="w-3 h-3" />, color: "text-green-600", bgColor: "bg-green-50" },
];

// ── Helpers ──────────────────────────────────────────────────────

function isToday(dateStr?: string | null): boolean {
  if (!dateStr) return false;
  const d = new Date(dateStr);
  const now = new Date();
  return d.toDateString() === now.toDateString();
}

function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case "blocker":
    case "critical": return "bg-red-500";
    case "high":
    case "major": return "bg-orange-500";
    case "medium": return "bg-yellow-500";
    case "low":
    case "info": return "bg-green-500";
    default: return "bg-gray-400";
  }
}

// ── Component ────────────────────────────────────────────────────

export function SmartQueue({
  findings,
  activeFilter,
  onFilterChange,
  currentUserId,
  onFindingClick,
  activeFindingId,
}: SmartQueueProps) {
  // Compute counts per filter
  const counts = useMemo(() => {
    const today = new Date().toDateString();
    return {
      all: findings.length,
      "my-findings": currentUserId
        ? findings.filter((f) => f.assignee === currentUserId).length
        : 0,
      "high-risk": findings.filter(
        (f) => f.severity === "critical" || f.severity === "high" || f.riskLevel === "critical" || f.riskLevel === "high",
      ).length,
      "due-today": findings.filter(
        (f) => f.dueDate && isToday(f.dueDate) && f.status !== "resolved" && f.status !== "accepted" && f.status !== "closed",
      ).length,
      "waiting-me": currentUserId
        ? findings.filter(
            (f) => f.assignee === currentUserId && f.status !== "resolved" && f.status !== "accepted" && f.status !== "closed",
          ).length
        : 0,
      "waiting-vendor": findings.filter(
        (f) => f.status === "negotiating" || f.status === "in_review",
      ).length,
      escalated: findings.filter((f) => (f.escalationLevel || 0) > 0).length,
      "completed-today": findings.filter(
        (f) => (f.status === "resolved" || f.status === "accepted" || f.status === "closed") && isToday(f.updatedAt || f.dueDate),
      ).length,
    };
  }, [findings, currentUserId]);

  // Filter findings based on active filter
  const filteredFindings = useMemo(() => {
    let filtered = [...findings];
    switch (activeFilter) {
      case "my-findings":
        filtered = filtered.filter((f) => f.assignee === currentUserId);
        break;
      case "high-risk":
        filtered = filtered.filter(
          (f) => f.severity === "critical" || f.severity === "high" || f.riskLevel === "critical" || f.riskLevel === "high",
        );
        break;
      case "due-today":
        filtered = filtered.filter((f) => f.dueDate && isToday(f.dueDate));
        break;
      case "waiting-me":
        filtered = filtered.filter(
          (f) => f.assignee === currentUserId && f.status !== "resolved" && f.status !== "accepted" && f.status !== "closed",
        );
        break;
      case "waiting-vendor":
        filtered = filtered.filter((f) => f.status === "negotiating" || f.status === "in_review");
        break;
      case "escalated":
        filtered = filtered.filter((f) => (f.escalationLevel || 0) > 0);
        break;
      case "completed-today":
        filtered = filtered.filter(
          (f) => (f.status === "resolved" || f.status === "accepted" || f.status === "closed") && isToday(f.updatedAt || f.dueDate),
        );
        break;
    }
    return filtered;
  }, [findings, activeFilter, currentUserId]);

  return (
    <div className="space-y-2">
      {/* Filter pills */}
      <div className="flex flex-wrap gap-1 px-2">
        {FILTERS.map((filter) => {
          const count = counts[filter.id];
          return (
            <button
              key={filter.id}
              onClick={() => onFilterChange(filter.id)}
              className={`flex items-center gap-1 px-2 py-1 rounded-full text-[9px] font-medium transition-all ${
                activeFilter === filter.id
                  ? `${filter.bgColor} ${filter.color} ring-1 ring-inset ring-current`
                  : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              {filter.icon}
              <span>{filter.label}</span>
              {count > 0 && (
                <span className={`ml-0.5 text-[8px] px-1 rounded-full ${
                  activeFilter === filter.id ? "bg-white/50" : "bg-gray-200"
                }`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Finding count */}
      <div className="px-2 text-[9px] text-gray-400">
        {filteredFindings.length} finding{filteredFindings.length !== 1 ? "s" : ""}
        {activeFilter !== "all" && ` in ${FILTERS.find(f => f.id === activeFilter)?.label}`}
      </div>

      {/* Finding list */}
      <div className="space-y-0.5 px-2 max-h-[calc(100vh-400px)] overflow-y-auto">
        {filteredFindings.length === 0 ? (
          <div className="text-center py-6 text-gray-400">
            <Search className="w-5 h-5 mx-auto mb-1 opacity-50" />
            <p className="text-[10px]">No findings match this filter</p>
          </div>
        ) : (
          filteredFindings.map((finding) => (
            <motion.button
              key={finding.id}
              layout
              onClick={() => onFindingClick(finding.id)}
              className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-all text-[10px] ${
                activeFindingId === finding.id
                  ? "bg-navy-50 border border-navy-200"
                  : "hover:bg-gray-50 border border-transparent"
              }`}
              whileHover={{ x: 2 }}
            >
              <div className="flex items-center gap-1.5">
                <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${getSeverityColor(finding.severity)}`} />
                <span className="font-medium text-navy-900 truncate flex-1">{finding.title}</span>
                {(finding.escalationLevel ?? 0) > 0 && (
                  <span className="text-[8px] text-red-500 font-medium">L{finding.escalationLevel}</span>
                )}
                {finding.status === "resolved" && (
                  <CheckCircle className="w-2.5 h-2.5 text-green-500" />
                )}
              </div>
              <div className="flex items-center gap-2 mt-0.5 text-[8px] text-gray-400">
                {finding.assignee && <span>{finding.assignee}</span>}
                {finding.dueDate && (
                  <span className={isToday(finding.dueDate) ? "text-amber-500 font-medium" : ""}>
                    {new Date(finding.dueDate).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </span>
                )}
                <span className="capitalize">{finding.status?.replace(/_/g, " ")}</span>
              </div>
            </motion.button>
          ))
        )}
      </div>
    </div>
  );
}
