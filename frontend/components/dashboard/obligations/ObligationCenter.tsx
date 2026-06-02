"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { ClipboardCheck, Download, RefreshCw, Search, Filter, Bell, AlertTriangle, Loader2, AlertCircle, Eye, Save } from "lucide-react";
import { ObligationKpiCards } from "./ObligationKpiCards";
import { ObligationTable } from "./ObligationTable";
import { ObligationAiInsights } from "./AiInsights";
import { SlaPerformanceChart, SlaVendorTable, FinancialExposurePanel, ObligationTimeline } from "./SlaCenter";
import { ObligationDetailDrawer } from "./ObligationDetailDrawer";
import { ObligationFilterBar } from "./ObligationFilterBar";
import type { ObligationRecord, ObligationKpi, ObligationInsight, SlaMetric, FinancialExposure, TimelineEvent } from "./types";
import type { ObligationResponse, SlaMetricResponse, FinancialExposureResponse } from "@/services/api/obligations";
import {
  useObligations, useObligationKpis, useSlaPerformance, useSlaBreaches,
  useVendorRisk, useSlaPredictions, useOverdue, useUpcoming,
  useFinancialExposure, useValueAtRisk, useAnomalies, useEscalations,
  useUpdateObligation,
} from "@/services/hooks/useObligations";

// ── Mappers ──────────────────────────────────────────────────────

function toObligationRecord(o: ObligationResponse): ObligationRecord {
  return {
    id: o.id,
    name: o.name,
    contractId: o.contract_id ?? "",
    contractName: o.contract_name ?? "",
    vendor: o.vendor ?? "",
    type: (o.obligation_type as ObligationRecord["type"]) ?? "sla",
    owner: o.owner ?? "",
    assignee: o.assignee ?? "",
    dueDate: o.due_date ?? "",
    completedDate: o.completed_date ?? undefined,
    status: (o.status as ObligationRecord["status"]) ?? "pending",
    riskLevel: (o.risk_level as ObligationRecord["riskLevel"]) ?? "info",
    riskScore: o.risk_score ?? 0,
    slaStatus: (o.sla_status as ObligationRecord["slaStatus"]) ?? "not_applicable",
    slaRemaining: o.sla_remaining_hours ?? 0,
    financialImpact: o.financial_impact ?? 0,
    currency: o.currency ?? "USD",
    escalationLevel: o.escalation_level ?? 0,
    aiRiskPrediction: o.ai_risk_prediction ?? 0,
    aiConfidence: o.ai_confidence ?? 0,
    description: o.description ?? "",
    clauseReference: o.clause_reference ?? "",
    attachments: o.attachments_count ?? 0,
    reminders: o.reminders_count ?? 0,
    notes: o.notes ?? "",
    department: o.department ?? "",
    businessUnit: o.business_unit ?? "",
    geography: o.geography ?? "",
    createdAt: o.created_at ?? "",
    lastModified: o.updated_at ?? o.created_at ?? "",
  };
}

function toSlaMetric(s: SlaMetricResponse): SlaMetric {
  return {
    vendor: s.vendor,
    contractType: s.contract_type ?? "",
    slaTarget: s.sla_target,
    performance: s.performance,
    trend: s.trend ?? 0,
    breachCount: s.breach_count ?? 0,
    status: (s.status as SlaMetric["status"]) ?? "on_track",
  };
}

function toFinancialExposure(f: FinancialExposureResponse): FinancialExposure {
  return {
    category: f.category,
    totalExposure: f.total_exposure,
    overdueAmount: f.overdue_amount ?? 0,
    atRiskAmount: f.at_risk_amount ?? 0,
    recoveredAmount: f.recovered_amount ?? 0,
    trend: f.trend ?? 0,
  };
}

function toTimelineEvent(t: { id: string; title: string; description?: string; event_date: string; status: string; vendor?: string; obligation_id: string }): TimelineEvent {
  return {
    id: t.id,
    date: t.event_date,
    type: "sla" as ObligationRecord["type"],
    title: t.title,
    description: t.description ?? "",
    status: (t.status as ObligationRecord["status"]) ?? "pending",
    vendor: t.vendor ?? "",
    contractId: t.obligation_id,
  };
}

// ── Saved Views ──────────────────────────────────────────────────

interface SavedView {
  id: string;
  name: string;
  filters: Record<string, string>;
}

const DEFAULT_VIEWS: SavedView[] = [
  { id: "all", name: "All Obligations", filters: {} },
  { id: "overdue", name: "Overdue", filters: { status: "overdue" } },
  { id: "escalated", name: "Escalated", filters: { status: "escalated" } },
  { id: "breached", name: "SLA Breached", filters: { slaStatus: "breached" } },
  { id: "at-risk", name: "At Risk", filters: { slaStatus: "at_risk" } },
];

interface ObligationFilters {
  type: string; status: string; vendor: string; slaStatus: string; riskLevel: string; department: string;
}

const defaultFilters: ObligationFilters = { type: "", status: "", vendor: "", slaStatus: "", riskLevel: "", department: "" };

export function ObligationCenter() {
  const [filters, setFilters] = useState<ObligationFilters>({ ...defaultFilters });
  const [selectedObligation, setSelectedObligation] = useState<ObligationRecord | null>(null);
  const [activeView, setActiveView] = useState("all");
  const [showSavedViews, setShowSavedViews] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // ── Live API Queries ──────────────────────────────────────────
  const { data: obligationsData, isLoading, isError, refetch } = useObligations({
    status: filters.status || undefined,
    obligation_type: filters.type || undefined,
    sla_status: filters.slaStatus || undefined,
    risk_level: filters.riskLevel || undefined,
    search: searchQuery || undefined,
  });
  const { data: kpisData } = useObligationKpis();
  const { data: slaData } = useSlaPerformance();
  const { data: breachData } = useSlaBreaches();
  const { data: vendorRiskData } = useVendorRisk();
  const { data: predictionData } = useSlaPredictions();
  const { data: overdueData } = useOverdue();
  const { data: upcomingData } = useUpcoming(30);
  const { data: financialData } = useFinancialExposure();
  const { data: varData } = useValueAtRisk();
  const { data: anomalyData } = useAnomalies();
  const { data: escalationData } = useEscalations();
  const updateMutation = useUpdateObligation(selectedObligation?.id ?? "");

  // ── Derived Data ──────────────────────────────────────────────
  const obligations: ObligationRecord[] = useMemo(
    () => (obligationsData?.data ?? []).map(toObligationRecord),
    [obligationsData],
  );

  const filteredObligations = useMemo(() => {
    let list = obligations;
    if (filters.vendor) list = list.filter((o) => o.vendor.toLowerCase().includes(filters.vendor.toLowerCase()));
    if (filters.department) list = list.filter((o) => o.department.toLowerCase().includes(filters.department.toLowerCase()));
    return list;
  }, [obligations, filters]);

  const slaMetrics: SlaMetric[] = useMemo(
    () => (slaData?.data ?? []).map(toSlaMetric),
    [slaData],
  );

  const financialExposureData: FinancialExposure[] = useMemo(
    () => (financialData?.data ?? []).map(toFinancialExposure),
    [financialData],
  );

  const timelineEvents: TimelineEvent[] = useMemo(() => {
    const overdue = (overdueData?.data ?? []).map((o: ObligationResponse) => ({
      id: o.id, title: `Overdue: ${o.name}`, description: `Overdue obligation with ${o.vendor}`,
      event_date: o.due_date ?? "", status: "overdue", vendor: o.vendor ?? "", obligation_id: o.id,
    }));
    const upcoming = (upcomingData?.data ?? []).map((o: ObligationResponse) => ({
      id: o.id, title: `Due: ${o.name}`, description: `Due ${o.due_date}`,
      event_date: o.due_date ?? "", status: "pending", vendor: o.vendor ?? "", obligation_id: o.id,
    }));
    return [...overdue, ...upcoming].slice(0, 20).map(toTimelineEvent);
  }, [overdueData, upcomingData]);

  // ── KPI Cards ─────────────────────────────────────────────────
  const clauseKpis: ObligationKpi[] = useMemo(() => {
    if (!kpisData) return [];
    return [
      { id: "total", label: "Total Obligations", value: kpisData.total_obligations.toString(), trend: 0, trendDirection: "neutral" as const, icon: "ClipboardCheck", color: "from-navy-600 to-navy-800", severity: "info" as const, sparklineData: [10, 20, 15, 25, 30, 28, kpisData.total_obligations], tooltip: "Total obligations in registry" },
      { id: "active", label: "Active", value: kpisData.active_count.toString(), trend: 5, trendDirection: "up" as const, icon: "ArrowUpCircle", color: "from-blue-500 to-blue-700", severity: "info" as const, sparklineData: [5, 8, 6, 10, 12, 11, kpisData.active_count], tooltip: "Active obligations in progress" },
      { id: "overdue", label: "Overdue", value: kpisData.overdue_count.toString(), trend: -8, trendDirection: "down" as const, icon: "AlertTriangle", color: "from-red-500 to-red-700", severity: "critical" as const, sparklineData: [8, 10, 7, 9, 6, 5, kpisData.overdue_count], tooltip: "Overdue obligations requiring attention" },
      { id: "escalated", label: "Escalated", value: kpisData.escalated_count.toString(), trend: 12, trendDirection: "up" as const, icon: "AlertOctagon", color: "from-purple-500 to-purple-700", severity: "warning" as const, sparklineData: [2, 3, 5, 4, 6, 7, kpisData.escalated_count], tooltip: "Escalated obligations" },
      { id: "completed", label: "Completed", value: kpisData.completed_count.toString(), trend: 15, trendDirection: "up" as const, icon: "CheckCircle", color: "from-emerald-500 to-emerald-700", severity: "success" as const, sparklineData: [5, 8, 10, 12, 15, 18, kpisData.completed_count], tooltip: "Completed obligations this period" },
      { id: "breached", label: "SLA Breaches", value: kpisData.breached_count.toString(), trend: -5, trendDirection: "down" as const, icon: "Flag", color: "from-rose-500 to-rose-700", severity: "critical" as const, sparklineData: [4, 6, 3, 5, 2, 3, kpisData.breached_count], tooltip: "SLA breaches this period" },
      { id: "exposure", label: "At Risk ($M)", value: `$${kpisData.at_risk_amount.toFixed(1)}M`, trend: 3, trendDirection: "up" as const, icon: "DollarSign", color: "from-amber-500 to-amber-700", severity: "warning" as const, sparklineData: [10, 12, 15, 14, 18, 16, kpisData.at_risk_amount], tooltip: "Financial amount at risk" },
      { id: "compliance", label: "Compliance", value: `${(kpisData.compliance_rate * 100).toFixed(0)}%`, trend: 2, trendDirection: "up" as const, icon: "Shield", color: "from-teal-500 to-teal-700", severity: kpisData.compliance_rate > 0.8 ? "success" : "warning", sparklineData: [70, 72, 75, 73, 78, 76, kpisData.compliance_rate * 100], tooltip: "Overall compliance rate" },
    ];
  }, [kpisData]);

  // ── AI Insights ───────────────────────────────────────────────
  const obligationInsights: ObligationInsight[] = useMemo(() => {
    const insights: ObligationInsight[] = [];
    const breached = breachData?.data ?? [];
    const anomalies = anomalyData?.data ?? [];
    const escalations = escalationData?.data ?? [];
    const overdue = overdueData?.data ?? [];
    const predictions = predictionData?.data ?? [];

    if (breached.length > 0) {
      insights.push({
        id: "sla-breaches", title: `${breached.length} SLA Breaches Detected`, description: `${breached.length} vendors have breached SLA targets. Immediate action required to mitigate penalties.`,
        severity: "critical", confidence: 92, impactedObligations: breached.map((b: any) => b.vendor), suggestedAction: "Review breach details and initiate escalation procedures for affected vendors.",
        category: "sla", quickActions: [{ label: "View Breaches", action: "view_breaches" }, { label: "Escalate All", action: "escalate_all" }],
      });
    }
    if (anomalies.length > 0) {
      insights.push({
        id: "anomalies", title: `${anomalies.length} Anomalies Flagged`, description: `AI detected ${anomalies.length} unusual patterns in obligation status or SLA compliance.`,
        severity: "warning", confidence: 85, impactedObligations: anomalies.map((a: any) => a.obligation_id), suggestedAction: "Review anomaly details and investigate root causes.",
        category: "ai", quickActions: [{ label: "Review Anomalies", action: "view_anomalies" }],
      });
    }
    if (escalations.length > 0) {
      insights.push({
        id: "escalations", title: `${escalations.length} Active Escalations`, description: `${escalations.length} obligations currently at escalation level ${Math.max(...escalations.map((e: any) => e.escalation_level))}.`,
        severity: "critical", confidence: 95, impactedObligations: escalations.map((e: any) => e.obligation_id), suggestedAction: "Prioritize resolution of escalated obligations.",
        category: "operations", quickActions: [{ label: "View Escalations", action: "view_escalations" }],
      });
    }
    if (overdue.length > 0) {
      insights.push({
        id: "overdue", title: `${overdue.length} Overdue Obligations`, description: `${overdue.length} obligations past due date. Total financial exposure at risk.`,
        severity: "warning", confidence: 88, impactedObligations: overdue.map((o: any) => o.id), suggestedAction: "Assign owners and escalate overdue items.",
        category: "compliance", quickActions: [{ label: "View Overdue", action: "view_overdue" }],
      });
    }
    if (predictions.length > 0) {
      const highRisk = predictions.filter((p: any) => p.breach_probability > 0.7);
      if (highRisk.length > 0) {
        insights.push({
          id: "predictions", title: `${highRisk.length} Vendors at High Breach Risk`, description: `AI predicts ${highRisk.length} vendors have >70% breach probability. Proactive measures recommended.`,
          severity: "warning", confidence: 78, impactedObligations: highRisk.map((p: any) => p.vendor), suggestedAction: "Review predictive analytics and engage vendors proactively.",
          category: "ai", quickActions: [{ label: "View Predictions", action: "view_predictions" }],
        });
      }
    }
    return insights;
  }, [breachData, anomalyData, escalationData, overdueData, predictionData]);

  // ── Handlers ──────────────────────────────────────────────────
  const handleFilterChange = useCallback((key: keyof ObligationFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);
  const resetFilters = useCallback(() => setFilters({ ...defaultFilters }), []);
  const applyView = useCallback((view: SavedView) => {
    setActiveView(view.id);
    setFilters({ ...defaultFilters, ...view.filters });
  }, []);

  const toggleFavorite = useCallback((id: string) => {
    const obligation = obligations.find((o) => o.id === id);
    if (obligation) {
      updateMutation.mutate({ isFavorite: true });
    }
  }, [obligations, updateMutation]);

  // ── Loading / Error ───────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-navy-600 animate-spin" />
          <p className="text-sm text-gray-500">Loading obligation management center...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertCircle className="w-10 h-10 text-red-400" />
          <p className="text-sm font-medium text-gray-700">Failed to load obligation data</p>
          <button onClick={() => refetch()} className="px-4 py-2 text-xs font-medium text-white bg-navy-700 rounded-lg hover:bg-navy-800 transition-colors">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-700 flex items-center justify-center shadow-sm">
            <ClipboardCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Obligation Management Center</h1>
            <p className="text-xs text-gray-500 mt-0.5">Enterprise post-signature operational intelligence and SLA governance</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Saved Views */}
          <div className="relative">
            <button onClick={() => setShowSavedViews(!showSavedViews)} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
              <Eye className="w-3.5 h-3.5" /> {DEFAULT_VIEWS.find((v) => v.id === activeView)?.name || "Views"}
            </button>
            {showSavedViews && (
              <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="absolute right-0 mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-1">
                {DEFAULT_VIEWS.map((v) => (
                  <button key={v.id} onClick={() => { applyView(v); setShowSavedViews(false); }}
                    className={`w-full text-left px-3 py-1.5 text-[11px] hover:bg-gray-50 ${activeView === v.id ? "text-navy-900 font-semibold bg-navy-50" : "text-gray-600"}`}>{v.name}</button>
                ))}
                <div className="border-t border-gray-100 mt-1 pt-1">
                  <button className="w-full text-left px-3 py-1.5 text-[11px] text-gray-500 hover:bg-gray-50 flex items-center gap-1.5"><Save className="w-3 h-3" /> Save Current View</button>
                </div>
              </motion.div>
            )}
          </div>
          <button onClick={() => refetch()} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Download className="w-3.5 h-3.5" /> Export Report
          </button>
        </div>
      </motion.div>

      {/* Urgency Alert Bar */}
      {(kpisData && (kpisData.overdue_count > 0 || kpisData.breached_count > 0)) && (
        <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
          className={`flex items-center gap-3 px-4 py-2 rounded-lg border ${kpisData.overdue_count > 0 ? "bg-red-50 border-red-200" : "bg-amber-50 border-amber-200"}`}>
          <AlertTriangle className={`w-4 h-4 ${kpisData.overdue_count > 0 ? "text-red-500" : "text-amber-500"}`} />
          <span className={`text-xs font-medium ${kpisData.overdue_count > 0 ? "text-red-800" : "text-amber-800"}`}>
            {kpisData.overdue_count > 0 ? `${kpisData.overdue_count} overdue obligations` : ""}
            {kpisData.overdue_count > 0 && kpisData.breached_count > 0 ? " and " : ""}
            {kpisData.breached_count > 0 ? `${kpisData.breached_count} SLA breaches` : ""} require immediate attention
          </span>
          <button className="ml-auto text-xs font-medium text-navy-700 bg-white px-2.5 py-1 rounded-md border border-gray-200 hover:bg-gray-50 transition-colors">
            View All
          </button>
        </motion.div>
      )}

      {/* KPI Row */}
      <ObligationKpiCards metrics={clauseKpis} />

      {/* Filter Bar */}
      <ObligationFilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} />

      {/* Section 1: AI Insights + Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <ObligationAiInsights insights={obligationInsights} />
        </div>
        <div className="lg:col-span-1">
          <ObligationTimeline events={timelineEvents} />
        </div>
      </div>

      {/* Section 2: Obligation Table */}
      <ObligationTable obligations={filteredObligations} onSelect={setSelectedObligation} onToggleFavorite={toggleFavorite} />

      {/* Section 3: SLA + Financial */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SlaPerformanceChart data={slaMetrics} predictions={predictionData?.data ?? []} />
        <FinancialExposurePanel data={financialExposureData} valueAtRisk={varData ?? undefined} />
      </div>
      <SlaVendorTable data={slaMetrics} breaches={breachData?.data ?? []} />

      {/* Detail Drawer */}
      <ObligationDetailDrawer obligation={selectedObligation} onClose={() => setSelectedObligation(null)} onToggleFavorite={toggleFavorite} />
    </div>
  );
}
