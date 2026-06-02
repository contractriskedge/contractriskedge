"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Shield, AlertTriangle, FileText, XCircle } from "lucide-react";
import { ReviewKpiGrid } from "./ReviewKpiGrid";
import { ReviewToolbar } from "./ReviewToolbar";
import { ReviewQueue } from "./ReviewQueue";
import { ClauseWorkspace } from "./ClauseWorkspace";
import { AICopilotDrawer } from "./AICopilotDrawer";
import type { ReviewQueueItem, AIFinding, KpiMetric, QueueFilter, DrawerTabId } from "./types";

const KPI_METRICS: KpiMetric[] = [
  {
    key: "pending-review",
    label: "Contracts Pending Review",
    value: "42",
    trend: 12,
    trendLabel: "week over week",
    severity: "high",
    sparkline: [18, 24, 22, 30, 28, 36, 42],
    icon: FileText,
  },
  {
    key: "high-risk",
    label: "High-Risk Reviews",
    value: "9",
    trend: -8,
    trendLabel: "over threshold",
    severity: "critical",
    sparkline: [8, 12, 11, 13, 11, 10, 9],
    icon: AlertTriangle,
  },
  {
    key: "cycle-time",
    label: "Average Review Cycle Time",
    value: "3.8 d",
    trend: -2,
    trendLabel: "faster",
    severity: "medium",
    sparkline: [40, 38, 35, 37, 36, 34, 32],
    icon: Shield,
  },
  {
    key: "sla-breaches",
    label: "SLA Breaches",
    value: "4",
    trend: 22,
    trendLabel: "risk",
    severity: "critical",
    sparkline: [2, 2, 3, 4, 4, 4, 4],
    icon: XCircle,
  },
];

const MOCK_QUEUE: ReviewQueueItem[] = [];

const AI_FINDINGS: AIFinding[] = [];

const INITIAL_FILTERS: QueueFilter = {
  reviewer: "all",
  riskLevel: "all",
  contractType: "all",
  slaStatus: "all",
  escalationStatus: "all",
  workflowStage: "all",
  vendor: "all",
  businessUnit: "all",
};

export function LegalReview() {
  const [selectedId, setSelectedId] = useState<string | null>(MOCK_QUEUE[0]?.id || null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState<QueueFilter>(INITIAL_FILTERS);
  const [activeDrawerTab, setActiveDrawerTab] = useState<DrawerTabId>("overview");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = window.setTimeout(() => setLoading(false), 300);
    return () => window.clearTimeout(timer);
  }, []);

  const selectedItem = useMemo(() => MOCK_QUEUE.find((item) => item.id === selectedId) ?? null, [selectedId]);

  const filteredQueue = useMemo(() => {
    return MOCK_QUEUE.filter((item) => {
      if (filters.reviewer !== "all" && item.assignedReviewer !== filters.reviewer) return false;
      if (filters.contractType !== "all" && item.contractType !== filters.contractType) return false;
      if (filters.workflowStage !== "all" && item.workflowStage !== filters.workflowStage) return false;
      if (filters.escalationStatus !== "all" && item.escalationStatus !== filters.escalationStatus) return false;
      if (filters.vendor !== "all" && item.vendor !== filters.vendor) return false;
      if (filters.businessUnit !== "all" && item.businessUnit !== filters.businessUnit) return false;
      if (filters.slaStatus === "at-risk" && !item.slaRemaining.includes("hr")) return false;
      if (filters.slaStatus === "breach" && !item.slaRemaining.includes("missed")) return false;
      return true;
    });
  }, [filters]);

  const handleToggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBulkAssign = () => {
    console.log("Bulk assign", Array.from(selectedIds));
  };

  const handleBulkApprove = () => {
    console.log("Bulk approve", Array.from(selectedIds));
  };

  const handleBulkEscalate = () => {
    console.log("Bulk escalate", Array.from(selectedIds));
  };

  const handleOpenAction = (action: string) => {
    console.log("Open action", action);
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 rounded-xl bg-slate-200 dark:bg-navy-700 w-1/3" />
        <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)_420px]">
          <div className="space-y-4">
            <div className="h-72 rounded-3xl bg-slate-200 dark:bg-navy-700" />
            <div className="h-48 rounded-3xl bg-slate-200 dark:bg-navy-700" />
          </div>
          <div className="space-y-4">
            <div className="h-20 rounded-3xl bg-slate-200 dark:bg-navy-700" />
            <div className="h-[32rem] rounded-3xl bg-slate-200 dark:bg-navy-700" />
          </div>
          <div className="h-[40rem] rounded-3xl bg-slate-200 dark:bg-navy-700" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <ReviewKpiGrid metrics={KPI_METRICS} />

      <div className="grid gap-5 xl:grid-cols-[340px_minmax(0,1fr)_420px]">
        <ReviewQueue
          items={filteredQueue}
          selectedId={selectedId}
          selectedIds={selectedIds}
          filters={filters}
          onSelect={setSelectedId}
          onToggleSelect={handleToggleSelect}
          onFilterChange={setFilters}
          onBulkApprove={handleBulkApprove}
          onBulkEscalate={handleBulkEscalate}
          onBulkAssign={handleBulkAssign}
        />

        <div className="space-y-5">
          <ReviewToolbar
            selected={selectedItem}
            selectedCount={selectedIds.size}
            onAssign={() => handleOpenAction("assign reviewer")}
            onEscalate={() => handleOpenAction("escalate issue")}
            onApprove={() => handleOpenAction("approve")}
            onReject={() => handleOpenAction("reject")}
            onGenerateRedline={() => handleOpenAction("generate ai redlines")}
            onCompareVersions={() => handleOpenAction("compare versions")}
          />

          <ClauseWorkspace
            selected={selectedItem}
            aiFindings={AI_FINDINGS}
            onOpenAction={handleOpenAction}
          />
        </div>

        <AICopilotDrawer
          selected={selectedItem}
          activeTab={activeDrawerTab}
          onTabChange={setActiveDrawerTab}
          aiFindings={AI_FINDINGS}
        />
      </div>
    </div>
  );
}
