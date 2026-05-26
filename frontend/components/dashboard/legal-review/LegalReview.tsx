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

const MOCK_QUEUE: ReviewQueueItem[] = [
  {
    id: "rq-01",
    contractName: "Global MSA – Strategic Vendor",
    vendor: "Neon Systems",
    riskScore: 88,
    priority: "urgent",
    assignedReviewer: "Alice Chen",
    slaRemaining: "5 hr",
    clauseIssues: 7,
    workflowStage: "legal_review",
    aiConfidence: 0.82,
    escalationStatus: "pending",
    contractType: "Master Service Agreement",
    businessUnit: "Digital Procurement",
    lastUpdated: "2h ago",
    notes: "Missing DPA language and indemnity cap requires senior counsel review.",
  },
  {
    id: "rq-02",
    contractName: "North America License Agreement",
    vendor: "Apex Cloud",
    riskScore: 74,
    priority: "high",
    assignedReviewer: "Bob Martinez",
    slaRemaining: "1 d",
    clauseIssues: 4,
    workflowStage: "negotiation",
    aiConfidence: 0.69,
    escalationStatus: "normal",
    contractType: "License Agreement",
    businessUnit: "Legal Ops",
    lastUpdated: "4h ago",
    notes: "Fallback clause recommended for liability and termination.",
  },
  {
    id: "rq-03",
    contractName: "Privacy Addendum – Vendor",
    vendor: "Vector Labs",
    riskScore: 61,
    priority: "medium",
    assignedReviewer: "Carol Singh",
    slaRemaining: "2 d",
    clauseIssues: 3,
    workflowStage: "approval",
    aiConfidence: 0.78,
    escalationStatus: "normal",
    contractType: "Data Processing Addendum",
    businessUnit: "Compliance",
    lastUpdated: "11h ago",
    notes: "Needs fallback language for cross-border data transfer.",
  },
  {
    id: "rq-04",
    contractName: "Consulting Statement of Work",
    vendor: "Helix Partners",
    riskScore: 45,
    priority: "low",
    assignedReviewer: "Alice Chen",
    slaRemaining: "3 d",
    clauseIssues: 1,
    workflowStage: "execution",
    aiConfidence: 0.91,
    escalationStatus: "resolved",
    contractType: "Statement of Work",
    businessUnit: "Enterprise Sales",
    lastUpdated: "1 d ago",
    notes: "Low risk but monitor for onboarding milestones.",
  },
];

const AI_FINDINGS: AIFinding[] = [
  {
    id: "finding-01",
    title: "Liability clause exceeds approved threshold",
    severity: "high",
    description: "The current clause exposes the company to uncapped third-party liability inconsistent with the corporate playbook.",
    recommendation: "Limit indemnity to third-party claims and apply the standard fee cap.",
    benchmarkPercentile: 88,
    confidence: 0.84,
    issueType: "Liability",
  },
  {
    id: "finding-02",
    title: "Fallback clause available from approved playbook",
    severity: "medium",
    description: "A substitute fallback exists for confidentiality indemnity in the legal playbook.",
    recommendation: "Apply the fallback clause and surface it in the redline summary.",
    benchmarkPercentile: 74,
    confidence: 0.79,
    issueType: "Fallback",
  },
  {
    id: "finding-03",
    title: "Missing DPA language detected",
    severity: "critical",
    description: "The contract lacks mandatory data protection language for EU personal data processing.",
    recommendation: "Insert the approved international data transfer addendum before approval.",
    benchmarkPercentile: 91,
    confidence: 0.92,
    issueType: "Data Protection",
  },
];

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
