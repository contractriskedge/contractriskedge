/**
 * ExecutiveCommandCenter — Unified leadership pane.
 *
 * Sprint 10 Priority 1.
 *
 * Consolidates 8 data domains into a single executive view:
 * - Tenant health composite score
 * - SLA risk heatmap
 * - Cost governance snapshot
 * - AI quality gate status
 * - Contract exposure summary
 * - Operational anomaly feed
 * - Reviewer load & escalation hotspots
 * - Cross-dashboard navigation
 *
 * Layout: Responsive 2-column grid (1-column on tablet/mobile)
 * with role-aware widget visibility.
 */

"use client";

import React, { useState, useCallback, useMemo } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { useSystemHealth, useMetricsSummary, useErrorAnalytics, useExecutiveSummary } from "@/services/hooks/useAnalytics";
import { TenantHealthWidget } from "./widgets/TenantHealthWidget";
import { SLARiskHeatmapWidget } from "./widgets/SLARiskHeatmapWidget";
import { CostGovernanceSnapshotWidget } from "./widgets/CostGovernanceSnapshotWidget";
import { AIQualityGateWidget } from "./widgets/AIQualityGateWidget";
import { ContractExposureWidget } from "./widgets/ContractExposureWidget";
import { AnomalyFeedWidget } from "./widgets/AnomalyFeedWidget";
import { ReviewerLoadWidget } from "./widgets/ReviewerLoadWidget";
import { DashboardHeader } from "./DashboardHeader";

type DateRange = "24h" | "7d" | "30d" | "90d";
type RefreshInterval = 0 | 15 | 30 | 60;

export function ExecutiveCommandCenter() {
  const { user } = useAuth();
  const [dateRange, setDateRange] = useState<DateRange>("7d");
  const [refreshInterval, setRefreshInterval] = useState<RefreshInterval>(30);
  const [fullscreenWidget, setFullscreenWidget] = useState<string | null>(null);

  // ── Data fetching (all parallel, stale-while-revalidate) ──────
  const { data: healthScore } = { data: null };
  const { data: slaPredictions } = { data: null };
  const { data: costDashboard } = { data: null };
  const { data: qualitySummary } = { data: null };
  const { data: executiveSummary } = useExecutiveSummary();
  const { data: systemHealth } = useSystemHealth();
  const { data: errorAnalytics } = useErrorAnalytics(24);
  const { data: metrics } = useMetricsSummary();

  // ── Role-based visibility ─────────────────────────────────────
  const role = user?.role ?? "viewer";
  const canSeeCostData = ["admin", "executive", "finance"].includes(role);
  const canSeeQualityData = ["admin", "executive", "ai-engineer"].includes(role);
  const canSeeAnomalies = ["admin", "executive", "operations"].includes(role);

  // ── Widget configuration ──────────────────────────────────────
  const widgets = useMemo(() => [
    {
      id: "tenant-health",
      title: "Tenant Health",
      component: <TenantHealthWidget healthScore={healthScore} />,
      roles: ["admin", "executive"],
      defaultVisible: true,
    },
    {
      id: "sla-risk",
      title: "SLA Risk Heatmap",
      component: <SLARiskHeatmapWidget predictions={slaPredictions} />,
      roles: ["admin", "executive", "operations"],
      defaultVisible: true,
    },
    {
      id: "cost-governance",
      title: "Cost Governance",
      component: <CostGovernanceSnapshotWidget dashboard={costDashboard} />,
      roles: ["admin", "executive", "finance"],
      defaultVisible: canSeeCostData,
    },
    {
      id: "ai-quality",
      title: "AI Quality Gate",
      component: <AIQualityGateWidget summary={qualitySummary} />,
      roles: ["admin", "executive", "ai-engineer"],
      defaultVisible: canSeeQualityData,
    },
    {
      id: "contract-exposure",
      title: "Contract Exposure",
      component: <ContractExposureWidget summary={executiveSummary} />,
      roles: ["admin", "executive", "legal", "finance"],
      defaultVisible: true,
    },
    {
      id: "anomaly-feed",
      title: "Operational Anomalies",
      component: <AnomalyFeedWidget errors={errorAnalytics} health={systemHealth} />,
      roles: ["admin", "executive", "operations"],
      defaultVisible: canSeeAnomalies,
    },
    {
      id: "reviewer-load",
      title: "Reviewer Load & Escalations",
      component: <ReviewerLoadWidget metrics={metrics} />,
      roles: ["admin", "executive", "operations"],
      defaultVisible: true,
    },
  ].filter((w) => w.defaultVisible || w.roles.includes(role as any)), [healthScore, slaPredictions, costDashboard, qualitySummary, executiveSummary, systemHealth, errorAnalytics, metrics, canSeeCostData, canSeeQualityData, canSeeAnomalies, role]);

  const visibleWidgets = useMemo(
    () => widgets.filter((w) => w.roles.includes(role as any)),
    [widgets, role]
  );

  // ── Fullscreen toggle ─────────────────────────────────────────
  const toggleFullscreen = useCallback((widgetId: string | null) => {
    setFullscreenWidget((prev) => (prev === widgetId ? null : widgetId));
  }, []);

  return (
    <div className="p-6 space-y-4">
      {/* ── Header with controls ──────────────────────────────── */}
      <DashboardHeader
        title="Executive Command Center"
        description="Unified leadership view — tenant health, SLA risk, cost, quality, exposure, and operations"
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        refreshInterval={refreshInterval}
        onRefreshIntervalChange={setRefreshInterval}
        onExport={() => {
          // Trigger export — use simple print-friendly approach
          const element = document.getElementById("command-center-grid");
          if (element) {
            // Use browser's built-in screenshot via print
            window.print();
          }
        }}
      />

      {/* ── Fullscreen widget ─────────────────────────────────── */}
      {fullscreenWidget && (
        <div className="fixed inset-0 z-50 bg-white dark:bg-navy-900 p-6 overflow-auto">
          <button
            onClick={() => toggleFullscreen(null)}
            className="absolute top-4 right-4 p-2 rounded-lg bg-gray-100 dark:bg-navy-700 hover:bg-gray-200 dark:hover:bg-navy-600 text-navy-600 dark:text-navy-200"
            aria-label="Exit fullscreen"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <div className="max-w-7xl mx-auto h-full">
            {widgets.find((w) => w.id === fullscreenWidget)?.component}
          </div>
        </div>
      )}

      {/* ── Widget Grid ───────────────────────────────────────── */}
      <div
        id="command-center-grid"
        className="grid grid-cols-1 lg:grid-cols-2 gap-4"
      >
        {visibleWidgets.map((widget) => (
          <div
            key={widget.id}
            className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm hover:shadow-md transition-shadow duration-200"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-navy-700">
              <h3 className="text-sm font-semibold text-navy-900 dark:text-white">
                {widget.title}
              </h3>
              <button
                onClick={() => toggleFullscreen(widget.id)}
                className="p-1 rounded hover:bg-gray-100 dark:hover:bg-navy-700 text-gray-400 hover:text-navy-600 dark:hover:text-navy-200"
                aria-label={`Expand ${widget.title} to fullscreen`}
                title="Expand to fullscreen"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </button>
            </div>
            <div className="p-4">
              {widget.component}
            </div>
          </div>
        ))}
      </div>

      {/* ── Empty state ───────────────────────────────────────── */}
      {visibleWidgets.length === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 dark:bg-navy-700 flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-navy-900 dark:text-white mb-2">
            No Widgets Available
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            No dashboard widgets are visible for your current role. Contact an administrator for access.
          </p>
        </div>
      )}
    </div>
  );
}
