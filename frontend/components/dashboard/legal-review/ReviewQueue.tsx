"use client";

import { motion } from "framer-motion";
import { Search, ChevronRight, Loader2, Users, Activity, ShieldAlert, Bell, Layers, FileSearch } from "lucide-react";
import type { ReviewQueueItem, QueueFilter } from "./types";

interface ReviewQueueProps {
  items: ReviewQueueItem[];
  selectedId: string | null;
  selectedIds: Set<string>;
  filters: QueueFilter;
  onSelect: (id: string) => void;
  onToggleSelect: (id: string) => void;
  onFilterChange: (next: QueueFilter) => void;
  onBulkApprove: () => void;
  onBulkEscalate: () => void;
  onBulkAssign: () => void;
}

const priorityStyles: Record<string, string> = {
  urgent: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-emerald-100 text-emerald-700",
};

const stageLabels: Record<string, string> = {
  triage: "Triage",
  legal_review: "Legal Review",
  negotiation: "Negotiation",
  approval: "Approval",
  execution: "Execution",
};

export function ReviewQueue({
  items,
  selectedId,
  selectedIds,
  filters,
  onSelect,
  onToggleSelect,
  onFilterChange,
  onBulkApprove,
  onBulkEscalate,
  onBulkAssign,
}: ReviewQueueProps) {
  const filteredItems = items.filter((item) => {
    if (filters.reviewer !== "all" && item.assignedReviewer !== filters.reviewer) return false;
    if (filters.riskLevel !== "all" && item.riskScore.toString() !== filters.riskLevel) return false;
    if (filters.contractType !== "all" && item.contractType !== filters.contractType) return false;
    if (filters.slaStatus !== "all") {
      if (filters.slaStatus === "at-risk" && !item.slaRemaining.includes("hr")) return false;
      if (filters.slaStatus === "breach" && !item.slaRemaining.includes("missed")) return false;
      if (filters.slaStatus === "on-track" && item.slaRemaining.includes("missed")) return false;
    }
    if (filters.escalationStatus !== "all" && item.escalationStatus !== filters.escalationStatus) return false;
    if (filters.workflowStage !== "all" && item.workflowStage !== filters.workflowStage) return false;
    if (filters.vendor !== "all" && item.vendor !== filters.vendor) return false;
    if (filters.businessUnit !== "all" && item.businessUnit !== filters.businessUnit) return false;
    return true;
  });

  const allSelected = filteredItems.length > 0 && filteredItems.every((item) => selectedIds.has(item.id));
  const someSelected = filteredItems.some((item) => selectedIds.has(item.id)) && !allSelected;

  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="flex h-full flex-col rounded-3xl border border-slate-200/70 bg-white/95 shadow-sm shadow-slate-200/20 dark:border-navy-700 dark:bg-navy-900/95"
      aria-labelledby="review-queue-title"
    >
      <div className="flex items-start justify-between gap-4 border-b border-slate-200/70 p-5 dark:border-navy-700">
        <div>
          <p id="review-queue-title" className="text-sm font-semibold text-slate-900 dark:text-white">Review Queue</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Enterprise legal triage and prioritization across contract workflows</p>
        </div>
        <div className="flex items-center gap-2 rounded-2xl border border-slate-200/80 bg-slate-50 px-3 py-2 text-xs text-slate-600 dark:border-navy-700 dark:bg-navy-800 dark:text-slate-300">
          <Layers className="h-4 w-4" aria-hidden="true" />
          {filteredItems.length} items
        </div>
      </div>

      <div className="p-5 space-y-4 border-b border-slate-200/70 dark:border-navy-700">
        <div className="flex gap-3 flex-wrap">
          <select
            value={filters.reviewer}
            onChange={(e) => onFilterChange({ ...filters, reviewer: e.target.value })}
            className="min-w-[140px] rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition hover:border-slate-300 focus:border-slate-400 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
          >
            <option value="all">All reviewers</option>
            <option value="Alice Chen">Alice Chen</option>
            <option value="Bob Martinez">Bob Martinez</option>
            <option value="Carol Singh">Carol Singh</option>
          </select>
          <select
            value={filters.workflowStage}
            onChange={(e) => onFilterChange({ ...filters, workflowStage: e.target.value as QueueFilter["workflowStage"] })}
            className="min-w-[140px] rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition hover:border-slate-300 focus:border-slate-400 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
          >
            <option value="all">All stages</option>
            <option value="triage">Triage</option>
            <option value="legal_review">Legal Review</option>
            <option value="negotiation">Negotiation</option>
            <option value="approval">Approval</option>
            <option value="execution">Execution</option>
          </select>
          <select
            value={filters.escalationStatus}
            onChange={(e) => onFilterChange({ ...filters, escalationStatus: e.target.value as QueueFilter["escalationStatus"] })}
            className="min-w-[140px] rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition hover:border-slate-300 focus:border-slate-400 dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200"
          >
            <option value="all">Escalation status</option>
            <option value="normal">Normal</option>
            <option value="pending">Pending</option>
            <option value="escalated">Escalated</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>

        <div className="relative rounded-3xl border border-slate-200 bg-slate-50 p-3 text-slate-500 dark:border-navy-700 dark:bg-navy-800 dark:text-slate-400">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2" aria-hidden="true" />
          <input
            type="search"
            placeholder="Search contracts, vendors, clauses..."
            className="w-full rounded-3xl border-none bg-transparent pl-10 pr-4 text-sm outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500"
            aria-label="Search review queue"
          />
        </div>

        <div className="grid grid-cols-3 gap-3 text-sm text-slate-600 dark:text-slate-300">
          <div className="rounded-2xl bg-slate-50 p-3 dark:bg-navy-800">
            <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Open</p>
            <p className="mt-2 text-xl font-semibold text-navy-900 dark:text-white">{items.filter((item) => item.workflowStage === "legal_review").length}</p>
          </div>
          <div className="rounded-2xl bg-slate-50 p-3 dark:bg-navy-800">
            <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Escalated</p>
            <p className="mt-2 text-xl font-semibold text-orange-600 dark:text-orange-300">{items.filter((item) => item.escalationStatus === "escalated").length}</p>
          </div>
          <div className="rounded-2xl bg-slate-50 p-3 dark:bg-navy-800">
            <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">SLA at risk</p>
            <p className="mt-2 text-xl font-semibold text-emerald-700 dark:text-emerald-300">{items.filter((item) => item.slaRemaining.includes("hr")).length}</p>
          </div>
        </div>
      </div>

      <div className="overflow-hidden">
        <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 px-5 py-3 text-xs uppercase tracking-[0.18em] text-slate-400 dark:text-slate-500 border-b border-slate-200/70 dark:border-navy-700">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={allSelected}
              aria-checked={someSelected ? "mixed" : allSelected}
              className="h-4 w-4 rounded border-slate-300 text-navy-600 focus:ring-navy-400"
              onChange={(e) => {
                const checked = e.target.checked;
                items.forEach((item) => {
                  if (filteredItems.includes(item)) {
                    if (checked) onToggleSelect(item.id);
                    else onToggleSelect(item.id);
                  }
                });
              }}
            />
            <span>Contract</span>
          </div>
          <span>Priority</span>
          <span className="text-right">SLA</span>
        </div>
        <div className="divide-y divide-slate-200/70 dark:divide-navy-700 max-h-[56vh] overflow-y-auto">
          {filteredItems.length === 0 ? (
            <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 p-12 text-slate-500 dark:text-slate-400">
              <FileSearch className="h-8 w-8" aria-hidden="true" />
              <p className="text-sm font-semibold">No reviews match your filters</p>
              <p className="text-xs">Adjust the queue filters or clear the search field.</p>
            </div>
          ) : (
            filteredItems.map((item) => {
              const active = selectedId === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelect(item.id)}
                  className={`group w-full text-left transition ${
                    active ? "bg-slate-100 dark:bg-navy-800" : "hover:bg-slate-50 dark:hover:bg-navy-850"
                  } p-4 flex items-center gap-4`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(item.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      onToggleSelect(item.id);
                    }}
                    className="h-4 w-4 rounded border-slate-300 text-navy-600 focus:ring-navy-400"
                    aria-label={`Select ${item.contractName}`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{item.contractName}</p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 truncate">{item.vendor} · {item.businessUnit}</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                      <span className="rounded-full border border-slate-200 px-2 py-1 dark:border-navy-700">{stageLabels[item.workflowStage]}</span>
                      <span className="rounded-full border border-slate-200 px-2 py-1 dark:border-navy-700">{item.assignedReviewer}</span>
                      <span className="rounded-full border border-slate-200 px-2 py-1 dark:border-navy-700">{item.contractType}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${priorityStyles[item.priority]}`}>{item.priority}</span>
                    <span className="text-xs text-slate-500 dark:text-slate-400">{item.slaRemaining}</span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      <div className="border-t border-slate-200/70 p-4 dark:border-navy-700">
        <div className="grid gap-3 sm:grid-cols-3">
          <button
            type="button"
            onClick={onBulkAssign}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 transition dark:border-navy-700 dark:bg-navy-800 dark:text-slate-200"
          >
            <Users className="h-4 w-4" aria-hidden="true" />
            Assign batch
          </button>
          <button
            type="button"
            onClick={onBulkApprove}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700 hover:bg-emerald-100 transition dark:border-emerald-400/30 dark:bg-emerald-500/10 dark:text-emerald-200"
          >
            <Activity className="h-4 w-4" aria-hidden="true" />
            Bulk approve
          </button>
          <button
            type="button"
            onClick={onBulkEscalate}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-orange-200 bg-orange-50 px-3 py-2 text-sm font-semibold text-orange-700 hover:bg-orange-100 transition dark:border-orange-400/30 dark:bg-orange-500/10 dark:text-orange-200"
          >
            <ShieldAlert className="h-4 w-4" aria-hidden="true" />
            Bulk escalate
          </button>
        </div>
      </div>
    </motion.section>
  );
}
