"use client";

import React, { useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  BarChart3, Download, RefreshCw, Search, AlertTriangle, Clock,
  Upload, FileText, CheckCircle, XCircle, Brain, Activity, Zap,
  AlertOctagon, Loader2, Server, Ban, Play, Repeat, Hourglass,
  TrendingUp,
} from "lucide-react";
import { AnalyticsKpiCards } from "./AnalyticsKpiCards";
import { ExecutiveAiInsights } from "./ExecutiveInsights";
import { ReportBuilder } from "./ReportBuilder";
import { AnalyticsFilterBar } from "./AnalyticsFilterBar";
import {
  AnalyticsChartCard,
  SimpleLineChart,
  SimplePieChart,
  SimpleBarChart,
} from "./SimpleCharts";
import {
  useSystemHealth,
  useMetricsSummary,
  useErrorAnalytics,
  useStuckWorkflows,
  useUploadTrend,
  useRiskDistribution,
  useFindingsByClause,
  useAiCostTrend,
  useReviewAging,
  useExecutiveSummary,
} from "@/services/hooks/useAnalytics";
import type { AnalyticsKpi, ExecutiveInsight, ReportTemplate } from "./types";

// ── Helpers ─────────────────────────────────────────────────────────────────

function severityForRate(rate: number): "success" | "warning" | "critical" {
  if (rate >= 95) return "success";
  if (rate >= 80) return "warning";
  return "critical";
}

function trendDirForRate(rate: number): "up" | "down" | "neutral" {
  if (rate >= 95) return "up";
  if (rate >= 80) return "down";
  return "down";
}

function sparklinePlaceholder(val: number): number[] {
  const base = Math.max(val * 0.85, 0);
  return Array.from({ length: 8 }, (_, i) =>
    Math.round(base + (val - base) * (i / 7) + (Math.random() - 0.5) * val * 0.08)
  );
}

// ── Status Badge ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; text: string; dot: string; label: string }> = {
    healthy:   { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500", label: "Healthy" },
    degraded:  { bg: "bg-yellow-50", text: "text-yellow-700", dot: "bg-yellow-500", label: "Degraded" },
    unhealthy: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", label: "Unhealthy" },
  };
  const c = cfg[status] ?? cfg.unhealthy;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-2 h-2 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

// ── Stat Card ───────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, sub, accent }: {
  icon: React.ReactNode; label: string; value: string | number;
  sub?: string; accent: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 hover:shadow-md transition-all"
    >
      <div className="flex items-start justify-between mb-2">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center bg-gradient-to-br ${accent} text-white shadow-xs`}>
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold text-navy-900 tabular-nums tracking-tight">{Number.isFinite(Number(value)) ? value : "—"}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-[10px] text-gray-400 mt-0.5">{sub}</p>}
    </motion.div>
  );
}

// ── Error Type Breakdown ────────────────────────────────────────────────────

function ErrorTypeBreakdown({ byType }: { byType: Record<string, number> }) {
  const entries = Object.entries(byType);
  if (entries.length === 0) return <p className="text-xs text-gray-400 italic">No error data</p>;
  const total = entries.reduce((s, [, v]) => s + v, 0);
  const colors = ["bg-red-500", "bg-orange-500", "bg-yellow-500", "bg-purple-500", "bg-blue-500"];
  return (
    <div className="space-y-2">
      {entries.map(([type, count], i) => (
        <div key={type}>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-gray-600 capitalize">{type.replace(/_/g, " ")}</span>
            <span className="font-semibold text-navy-900">{count}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${colors[i % colors.length]}`}
              style={{ width: `${(count / total) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Top Failing Uploads ─────────────────────────────────────────────────────

function TopFailingUploads({ items }: { items: Array<{ upload_id: string; filename: string; error: string; count: number }> }) {
  if (items.length === 0) return <p className="text-xs text-gray-400 italic">No failing uploads</p>;
  return (
    <div className="space-y-2 max-h-52 overflow-y-auto">
      {items.map((item) => (
        <div key={item.upload_id} className="flex items-start gap-2 p-2 rounded-lg bg-red-50 border border-red-100">
          <AlertTriangle className="w-3.5 h-3.5 text-red-500 mt-0.5 flex-shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-navy-900 truncate">{item.filename}</p>
            <p className="text-[10px] text-red-600 truncate">{item.error}</p>
            <p className="text-[10px] text-gray-400">×{item.count} occurrences</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Stuck Workflows Card ────────────────────────────────────────────────────

function StuckWorkflowsCard({ stuckUploads, stuckAiRuns, stuckReviews, items }: {
  stuckUploads: number; stuckAiRuns: number; stuckReviews: number;
  items: Array<{ id: string; type: string; state: string; stuck_minutes: number }>;
}) {
  const total = stuckUploads + stuckAiRuns + stuckReviews;
  if (total === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col items-center justify-center text-center">
        <CheckCircle className="w-8 h-8 text-green-400 mb-2" />
        <p className="text-sm font-medium text-navy-900">All Workflows Running Smoothly</p>
        <p className="text-xs text-gray-400 mt-1">No stuck uploads, AI runs, or reviews detected.</p>
      </div>
    );
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <h3 className="text-xs font-semibold text-navy-900 mb-3 flex items-center gap-2">
        <Hourglass className="w-4 h-4 text-orange-500" /> Stuck Workflows ({total})
      </h3>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center p-2 rounded-lg bg-orange-50">
          <p className="text-lg font-bold text-orange-600">{stuckUploads}</p>
          <p className="text-[10px] text-gray-500">Uploads</p>
        </div>
        <div className="text-center p-2 rounded-lg bg-purple-50">
          <p className="text-lg font-bold text-purple-600">{stuckAiRuns}</p>
          <p className="text-[10px] text-gray-500">AI Runs</p>
        </div>
        <div className="text-center p-2 rounded-lg bg-blue-50">
          <p className="text-lg font-bold text-blue-600">{stuckReviews}</p>
          <p className="text-[10px] text-gray-500">Reviews</p>
        </div>
      </div>
      {items.length > 0 && (
        <div className="space-y-1.5 max-h-36 overflow-y-auto">
          {items.slice(0, 5).map((item) => (
            <div key={item.id} className="flex items-center justify-between text-[10px] px-2 py-1 rounded bg-gray-50">
              <span className="text-gray-600 truncate max-w-[140px]">{item.type} — {item.state}</span>
              <span className="font-medium text-orange-600 flex-shrink-0">{item.stuck_minutes}m</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Latency / Token Card ────────────────────────────────────────────────────

function LatencyTokenCard({ avgUploadLatencyMs, avgAiLatencyMs, totalTokensUsed, totalCostUsd }: {
  avgUploadLatencyMs: number; avgAiLatencyMs: number;
  totalTokensUsed: number; totalCostUsd: number;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <h3 className="text-xs font-semibold text-navy-900 mb-3 flex items-center gap-2">
        <Zap className="w-4 h-4 text-yellow-500" /> Performance & Cost
      </h3>
      <div className="grid grid-cols-2 gap-3">
        <div className="p-2.5 rounded-lg bg-indigo-50">
          <p className="text-xs text-indigo-600 font-medium">{avgUploadLatencyMs}ms</p>
          <p className="text-[10px] text-gray-500">Avg Upload Latency</p>
        </div>
        <div className="p-2.5 rounded-lg bg-cyan-50">
          <p className="text-xs text-cyan-600 font-medium">{avgAiLatencyMs}ms</p>
          <p className="text-[10px] text-gray-500">Avg AI Latency</p>
        </div>
        <div className="p-2.5 rounded-lg bg-amber-50">
          <p className="text-xs text-amber-600 font-medium">{(totalTokensUsed / 1_000_000).toFixed(1)}M</p>
          <p className="text-[10px] text-gray-500">Tokens Used</p>
        </div>
        <div className="p-2.5 rounded-lg bg-emerald-50">
          <p className="text-xs text-emerald-600 font-medium">${totalCostUsd.toFixed(2)}</p>
          <p className="text-[10px] text-gray-500">Total Cost</p>
        </div>
      </div>
    </div>
  );
}

// ── Loading Skeleton ────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-4 pb-24">
      <div className="flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-navy-400 animate-spin" />
          <p className="text-sm text-gray-500">Loading analytics data…</p>
        </div>
      </div>
    </div>
  );
}

// ── Error State ─────────────────────────────────────────────────────────────

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="space-y-4 pb-24">
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center mb-4">
          <AlertOctagon className="w-7 h-7 text-red-500" />
        </div>
        <p className="text-lg font-semibold text-navy-900 mb-1">Failed to Load Analytics</p>
        <p className="text-sm text-gray-500 mb-4 max-w-md text-center">{message}</p>
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm"
        >
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    </div>
  );
}

// ── Empty State ─────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="space-y-4 pb-24">
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center mb-4">
          <Activity className="w-7 h-7 text-gray-400" />
        </div>
        <p className="text-lg font-semibold text-navy-900 mb-1">No Analytics Data Available</p>
        <p className="text-sm text-gray-500 max-w-md text-center">
          Start uploading contracts and running AI analyses to see your analytics dashboard populate with insights.
        </p>
      </div>
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

interface AnalyticsFilters {
  businessUnit: string; geography: string; department: string; dateRange: string; riskLevel: string;
}

const defaultFilters: AnalyticsFilters = {
  businessUnit: "", geography: "", department: "", dateRange: "", riskLevel: "",
};

interface AnalyticsCenterProps {
  onNavigate?: (view: string, params?: Record<string, string>) => void;
}

export function AnalyticsCenter({ onNavigate }: AnalyticsCenterProps) {
  const [filters, setFilters] = useState<AnalyticsFilters>({ ...defaultFilters });

  const handleFilterChange = useCallback((key: keyof AnalyticsFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);
  const resetFilters = useCallback(() => setFilters({ ...defaultFilters }), []);

  // ── KPI drill-down navigation ─────────────────────────────────
  const handleKpiClick = useCallback((kpi: AnalyticsKpi) => {
    if (!onNavigate) return;
    switch (kpi.id) {
      case "pending-reviews":
        onNavigate("review");
        break;
      case "errors-24h":
        // Scroll to error section — already visible on analytics page
        document.getElementById("error-analytics-section")?.scrollIntoView({ behavior: "smooth" });
        break;
      case "stuck-workflows-insight":
      case "active-uploads":
        onNavigate("ingestion");
        break;
      case "active-ai-runs":
      case "ai-success-rate":
        onNavigate("analytics");
        break;
      case "total-uploads-24h":
        onNavigate("ingestion");
        break;
      case "total-reviews-24h":
        onNavigate("review");
        break;
      case "upload-success-rate":
        document.getElementById("error-analytics-section")?.scrollIntoView({ behavior: "smooth" });
        break;
      default:
        break;
    }
  }, [onNavigate]);

  // ── Data hooks ──────────────────────────────────────────────────────────
  const health = useSystemHealth();
  const metrics = useMetricsSummary();
  const errors = useErrorAnalytics(24);
  const stuck = useStuckWorkflows();
  const uploadTrend = useUploadTrend(30);
  const riskDist = useRiskDistribution();
  const findingsByClause = useFindingsByClause();
  const aiCost = useAiCostTrend(30);
  const reviewAging = useReviewAging();

  const isLoading = health.isLoading || metrics.isLoading || errors.isLoading || stuck.isLoading;
  const isError   = health.isError   || metrics.isError   || errors.isError   || stuck.isError;
  const errorMsg  = health.error?.message ?? metrics.error?.message ?? errors.error?.message ?? stuck.error?.message ?? "An unexpected error occurred.";

  // ── Build KPI data from real hooks ──────────────────────────────────────
  const healthData = health.data;
  const metricsData = metrics.data;
  const errorsData = errors.data;
  const stuckData = stuck.data;

  const hasData = !!(healthData || metricsData);

  const kpis: AnalyticsKpi[] = React.useMemo(() => {
    const list: AnalyticsKpi[] = [];
    if (healthData) {
      list.push({
        id: "system-health",
        label: "System Status",
        value: healthData.status === "healthy" ? "Healthy" : healthData.status === "degraded" ? "Degraded" : "Unhealthy",
        trend: healthData.upload_success_rate > 95 ? 2 : healthData.upload_success_rate > 80 ? -3 : -8,
        trendDirection: healthData.status === "healthy" ? "up" : "down",
        icon: "Shield",
        color: healthData.status === "healthy"
          ? "from-green-500 to-emerald-600"
          : healthData.status === "degraded"
            ? "from-yellow-500 to-orange-600"
            : "from-red-500 to-rose-600",
        severity: healthData.status === "healthy" ? "success" : healthData.status === "degraded" ? "warning" : "critical",
        sparklineData: sparklinePlaceholder(healthData.upload_success_rate),
        tooltip: `System is ${healthData.status}. Upload success rate: ${healthData.upload_success_rate}%`,
      });
      list.push({
        id: "active-uploads",
        label: "Active Uploads",
        value: String(healthData.active_uploads),
        trend: 0,
        trendDirection: "neutral",
        icon: "Upload",
        color: "from-blue-500 to-indigo-600",
        severity: healthData.active_uploads > 10 ? "warning" : "success",
        sparklineData: sparklinePlaceholder(healthData.active_uploads),
        tooltip: `${healthData.active_uploads} uploads currently in progress`,
      });
      list.push({
        id: "active-ai-runs",
        label: "Active AI Runs",
        value: String(healthData.active_ai_runs),
        trend: 0,
        trendDirection: "neutral",
        icon: "Brain",
        color: "from-purple-500 to-violet-600",
        severity: healthData.active_ai_runs > 20 ? "warning" : "success",
        sparklineData: sparklinePlaceholder(healthData.active_ai_runs),
        tooltip: `${healthData.active_ai_runs} AI analyses running`,
      });
      list.push({
        id: "pending-reviews",
        label: "Pending Reviews",
        value: String(healthData.pending_reviews),
        trend: 0,
        trendDirection: "neutral",
        icon: "ClipboardCheck",
        color: "from-amber-500 to-orange-600",
        severity: healthData.pending_reviews > 50 ? "critical" : healthData.pending_reviews > 20 ? "warning" : "success",
        sparklineData: sparklinePlaceholder(healthData.pending_reviews),
        tooltip: `${healthData.pending_reviews} reviews awaiting action`,
      });
      list.push({
        id: "upload-success-rate",
        label: "Upload Success",
        value: `${healthData.upload_success_rate}%`,
        trend: healthData.upload_success_rate - 92,
        trendDirection: trendDirForRate(healthData.upload_success_rate),
        icon: "Upload",
        color: "from-green-500 to-emerald-600",
        severity: severityForRate(healthData.upload_success_rate),
        sparklineData: sparklinePlaceholder(healthData.upload_success_rate),
        tooltip: `Upload success rate: ${healthData.upload_success_rate}%`,
      });
      list.push({
        id: "ai-success-rate",
        label: "AI Success",
        value: `${healthData.ai_success_rate}%`,
        trend: healthData.ai_success_rate - 90,
        trendDirection: trendDirForRate(healthData.ai_success_rate),
        icon: "Brain",
        color: "from-cyan-500 to-teal-600",
        severity: severityForRate(healthData.ai_success_rate),
        sparklineData: sparklinePlaceholder(healthData.ai_success_rate),
        tooltip: `AI analysis success rate: ${healthData.ai_success_rate}%`,
      });
    }
    if (metricsData) {
      list.push({
        id: "total-uploads-24h",
        label: "Uploads (24h)",
        value: String(metricsData.total_uploads_24h),
        trend: 0,
        trendDirection: "neutral",
        icon: "Upload",
        color: "from-sky-500 to-blue-600",
        severity: "info",
        sparklineData: sparklinePlaceholder(metricsData.total_uploads_24h),
        tooltip: `${metricsData.total_uploads_24h} uploads in the last 24 hours`,
      });
      list.push({
        id: "total-reviews-24h",
        label: "Reviews (24h)",
        value: String(metricsData.total_reviews_24h),
        trend: 0,
        trendDirection: "neutral",
        icon: "ClipboardCheck",
        color: "from-indigo-500 to-blue-600",
        severity: "info",
        sparklineData: sparklinePlaceholder(metricsData.total_reviews_24h),
        tooltip: `${metricsData.total_reviews_24h} reviews in the last 24 hours`,
      });
    }
    if (healthData?.recent_errors_24h != null) {
      list.push({
        id: "errors-24h",
        label: "Errors (24h)",
        value: String(healthData.recent_errors_24h),
        trend: healthData.recent_errors_24h > 5 ? 12 : -5,
        trendDirection: healthData.recent_errors_24h > 5 ? "up" : "down",
        icon: "AlertTriangle",
        color: healthData.recent_errors_24h > 5
          ? "from-red-500 to-rose-600"
          : "from-green-500 to-emerald-600",
        severity: healthData.recent_errors_24h > 10 ? "critical" : healthData.recent_errors_24h > 3 ? "warning" : "success",
        sparklineData: sparklinePlaceholder(healthData.recent_errors_24h),
        tooltip: `${healthData.recent_errors_24h} errors in the last 24 hours`,
      });
    }
    return list;
  }, [healthData, metricsData]);

  // ── Derived data for insight cards (must run before any early return) ───
  const derivedInsights: ExecutiveInsight[] = React.useMemo(() => {
    const list: ExecutiveInsight[] = [];
    if (healthData && healthData.status !== "healthy") {
      list.push({
        id: "system-health-warning",
        title: `System Status: ${healthData.status}`,
        description: `The system is currently ${healthData.status === "degraded" ? "experiencing degraded performance" : "unhealthy"}. Upload success rate is ${healthData.upload_success_rate}% and AI success rate is ${healthData.ai_success_rate}%.`,
        severity: healthData.status === "unhealthy" ? "critical" : "warning",
        confidence: 95,
        businessImpact: "May affect contract processing and review SLAs",
        affectedEntities: ["Upload Pipeline", "AI Analysis Engine"],
        recommendedAction: "Review recent error logs and check infrastructure health",
        category: "system",
        quickActions: [{ label: "View Logs", action: "view_logs" }],
      });
    }
    if (errorsData && errorsData.total_failures > 0) {
      list.push({
        id: "error-analytics-summary",
        title: `${errorsData.total_failures} Failures Detected (24h)`,
        description: `${errorsData.retryable_count} retryable and ${errorsData.non_retryable_count} non-retryable failures recorded. Top error types: ${Object.entries(errorsData.by_type).slice(0, 3).map(([t, c]) => `${t} (${c})`).join(", ")}.`,
        severity: errorsData.total_failures > 20 ? "critical" : errorsData.total_failures > 5 ? "warning" : "info",
        confidence: 90,
        businessImpact: "May increase processing delays and require manual intervention",
        affectedEntities: Object.keys(errorsData.by_domain),
        recommendedAction: "Investigate top error types and review failing uploads",
        category: "errors",
        quickActions: [{ label: "Review Errors", action: "view_errors" }],
      });
    }
    const su = stuckData?.stuck_uploads ?? 0;
    const sa = stuckData?.stuck_ai_runs ?? 0;
    const sr = stuckData?.stuck_reviews ?? 0;
    if (Number.isFinite(su + sa + sr) && (su + sa + sr) > 0) {
      const totalStuck = su + sa + sr;
      list.push({
        id: "stuck-workflows-insight",
        title: `${totalStuck} Stuck Workflows Require Attention`,
        description: `${su} stuck uploads, ${sa} stuck AI runs, ${sr} stuck reviews.`,
        severity: totalStuck > 10 ? "critical" : "warning",
        confidence: 95,
        businessImpact: "Blocked workflows may delay contract reviews and approvals",
        affectedEntities: ["Upload Pipeline", "AI Analysis", "Review Queue"],
        recommendedAction: "Review and resolve stuck items to unblock the pipeline",
        category: "workflows",
        quickActions: [{ label: "View Stuck Items", action: "view_stuck" }],
      });
    }
    if (metricsData && metricsData.upload_success_rate < 90) {
      list.push({
        id: "low-upload-success",
        title: "Low Upload Success Rate",
        description: `Upload success rate is ${metricsData.upload_success_rate}%, below the 95% target. Average upload latency is ${metricsData.avg_upload_latency_ms}ms.`,
        severity: "warning",
        confidence: 85,
        businessImpact: "Failed uploads require re-processing, increasing operational costs",
        affectedEntities: ["Upload Pipeline"],
        recommendedAction: "Investigate upload failures and optimize pipeline",
        category: "performance",
        quickActions: [{ label: "View Uploads", action: "view_uploads" }],
      });
    }
    if (metricsData && metricsData.ai_success_rate < 90) {
      list.push({
        id: "low-ai-success",
        title: "Low AI Analysis Success Rate",
        description: `AI analysis success rate is ${metricsData.ai_success_rate}%, below the 90% target. Average AI latency is ${metricsData.avg_ai_latency_ms}ms.`,
        severity: "warning",
        confidence: 85,
        businessImpact: "Failed AI analyses may leave contracts unreviewed",
        affectedEntities: ["AI Analysis Engine"],
        recommendedAction: "Review AI model performance and error logs",
        category: "performance",
        quickActions: [{ label: "View AI Runs", action: "view_ai" }],
      });
    }
    if (healthData && healthData.sla_breaches > 0) {
      list.push({
        id: "sla-breaches",
        title: `${healthData.sla_breaches} SLA Breaches Detected`,
        description: `${healthData.sla_breaches} service level agreement breaches have been recorded. This may indicate systemic issues in processing pipelines.`,
        severity: healthData.sla_breaches > 5 ? "critical" : "warning",
        confidence: 95,
        businessImpact: "SLA breaches may result in contractual penalties and client dissatisfaction",
        affectedEntities: ["Upload Pipeline", "Review Queue"],
        recommendedAction: "Prioritize resolution of underlying issues causing SLA breaches",
        category: "compliance",
        quickActions: [{ label: "View SLA Report", action: "view_sla" }],
      });
    }
    return list;
  }, [healthData, metricsData, errorsData, stuckData]);

  // ── Loading state ───────────────────────────────────────────────────────
  if (isLoading) {
    return <LoadingSkeleton />;
  }

  // ── Error state ─────────────────────────────────────────────────────────
  if (isError) {
    return <ErrorState message={errorMsg} onRetry={() => { health.refetch(); metrics.refetch(); errors.refetch(); stuck.refetch(); }} />;
  }

  // ── Empty state ─────────────────────────────────────────────────────────
  if (!hasData) {
    return <EmptyState />;
  }

  const emptyTemplates: ReportTemplate[] = [];

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-800 flex items-center justify-center shadow-sm">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Reporting & Executive Analytics</h1>
            <p className="text-xs text-gray-500 mt-0.5">
              Enterprise intelligence, forecasting, and board-ready reporting
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <Search className="w-3.5 h-3.5" /> Natural Language Query
          </button>
          <button
            onClick={() => { health.refetch(); metrics.refetch(); errors.refetch(); stuck.refetch(); }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Download className="w-3.5 h-3.5" /> Export Dashboard
          </button>
        </div>
      </motion.div>

      {/* System Status Banner */}
      {healthData && healthData.status !== "healthy" && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${
            healthData.status === "degraded"
              ? "bg-yellow-50 border-yellow-200 text-yellow-800"
              : "bg-red-50 border-red-200 text-red-800"
          }`}
        >
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold">
              System {healthData.status === "degraded" ? "Degraded" : "Unhealthy"}
            </p>
            <p className="text-xs opacity-80">
              Upload success: {healthData.upload_success_rate}% &middot; AI success: {healthData.ai_success_rate}% &middot;{" "}
              {healthData.sla_breaches} SLA breaches &middot; {healthData.recent_errors_24h} errors (24h)
            </p>
          </div>
          <StatusBadge status={healthData.status} />
        </motion.div>
      )}

      {/* KPI Row */}
      <AnalyticsKpiCards metrics={kpis} onKpiClick={handleKpiClick} />

      {/* Filter Bar */}
      <AnalyticsFilterBar
        filters={filters}
        onChange={handleFilterChange}
        onReset={resetFilters}
      />

      {/* Section 1: System Health & Metrics */}
      <div>
        <h2 className="text-sm font-semibold text-navy-900 mb-3 flex items-center gap-2">
          <Activity className="w-4 h-4 text-navy-500" /> System Health &amp; Performance
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Health Status */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 h-full">
              <h3 className="text-xs font-semibold text-navy-900 mb-3 flex items-center gap-2">
                <Server className="w-4 h-4 text-navy-500" /> System Status
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Status</span>
                  <StatusBadge status={healthData?.status ?? "unknown"} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Active Uploads</span>
                  <span className="text-sm font-semibold text-navy-900">{healthData?.active_uploads ?? 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Active AI Runs</span>
                  <span className="text-sm font-semibold text-navy-900">{healthData?.active_ai_runs ?? 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Pending Reviews</span>
                  <span className="text-sm font-semibold text-navy-900">{healthData?.pending_reviews ?? 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">SLA Breaches</span>
                  <span className={`text-sm font-semibold ${(healthData?.sla_breaches ?? 0) > 0 ? "text-red-600" : "text-navy-900"}`}>
                    {healthData?.sla_breaches ?? 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Errors (24h)</span>
                  <span className={`text-sm font-semibold ${(healthData?.recent_errors_24h ?? 0) > 5 ? "text-red-600" : "text-navy-900"}`}>
                    {healthData?.recent_errors_24h ?? 0}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Stuck Workflows */}
          <div className="lg:col-span-1">
            {stuckData ? (
              <StuckWorkflowsCard
                stuckUploads={stuckData.stuck_uploads}
                stuckAiRuns={stuckData.stuck_ai_runs}
                stuckReviews={stuckData.stuck_reviews}
                items={stuckData.items}
              />
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex items-center justify-center h-full">
                <p className="text-xs text-gray-400">Workflow data unavailable</p>
              </div>
            )}
          </div>

          {/* Latency & Cost */}
          <div className="lg:col-span-1">
            {metricsData ? (
              <LatencyTokenCard
                avgUploadLatencyMs={metricsData.avg_upload_latency_ms}
                avgAiLatencyMs={metricsData.avg_ai_latency_ms}
                totalTokensUsed={metricsData.total_tokens_used}
                totalCostUsd={metricsData.total_cost_usd}
              />
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex items-center justify-center h-full">
                <p className="text-xs text-gray-400">Performance data unavailable</p>
              </div>
            )}
          </div>

          {/* Error Breakdown */}
          <div id="error-analytics-section" className="lg:col-span-1">
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 h-full">
              <h3 className="text-xs font-semibold text-navy-900 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500" /> Error Breakdown
              </h3>
              {errorsData ? (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-gray-500">Total Failures</span>
                    <span className="text-lg font-bold text-red-600">{errorsData.total_failures}</span>
                  </div>
                  <div className="flex gap-2 mb-3">
                    <div className="flex-1 text-center p-1.5 rounded bg-green-50">
                      <p className="text-xs font-semibold text-green-600">{errorsData.retryable_count}</p>
                      <p className="text-[9px] text-gray-500">Retryable</p>
                    </div>
                    <div className="flex-1 text-center p-1.5 rounded bg-red-50">
                      <p className="text-xs font-semibold text-red-600">{errorsData.non_retryable_count}</p>
                      <p className="text-[9px] text-gray-500">Non-retryable</p>
                    </div>
                  </div>
                  <ErrorTypeBreakdown byType={errorsData.by_type} />
                </>
              ) : (
                <p className="text-xs text-gray-400 italic">Error data unavailable</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Top Failing Uploads + Stuck Items Detail */}
      {errorsData && errorsData.top_failing_uploads.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-navy-900 mb-3 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-red-500" /> Top Failing Uploads
          </h2>
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <TopFailingUploads items={errorsData.top_failing_uploads} />
          </div>
        </div>
      )}

      {/* Section 3: Analytics Charts */}
      <div>
        <h2 className="text-sm font-semibold text-navy-900 mb-3 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-navy-500" /> Portfolio Analytics
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AnalyticsChartCard
            title="Upload Volume (30d)"
            subtitle="Uploads per day"
            loading={uploadTrend.isLoading}
            isEmpty={!uploadTrend.data?.length}
          >
            <SimpleLineChart
              data={uploadTrend.data ?? []}
              xKey="day"
              lines={[{ key: "count", color: "#3B82F6", name: "Uploads" }]}
            />
          </AnalyticsChartCard>

          <AnalyticsChartCard
            title="Risk Distribution"
            subtitle="Portfolio risk score breakdown"
            loading={riskDist.isLoading}
            isEmpty={!riskDist.data?.length}
          >
            <SimplePieChart
              data={riskDist.data ?? []}
              nameKey="level"
              valueKey="count"
              colors={{ critical: "#DC2626", high: "#EA580C", medium: "#EAB308", low: "#22C55E", info: "#6B7280" }}
            />
          </AnalyticsChartCard>

          <AnalyticsChartCard
            title="Findings by Clause Type"
            subtitle="AI-identified risk areas across portfolio"
            loading={findingsByClause.isLoading}
            isEmpty={!findingsByClause.data?.length}
          >
            <SimpleBarChart
              data={findingsByClause.data ?? []}
              xKey="clause_type"
              barKey="count"
              color="#8B5CF6"
              horizontal={true}
            />
          </AnalyticsChartCard>

          <AnalyticsChartCard
            title="AI Cost & Token Usage (30d)"
            subtitle="Daily AI processing economics"
            loading={aiCost.isLoading}
            isEmpty={!aiCost.data?.length}
          >
            <SimpleLineChart
              data={aiCost.data ?? []}
              xKey="day"
              lines={[
                { key: "tokens", color: "#0F766E", name: "Tokens" },
                { key: "cost", color: "#D97706", name: "Cost ($)" },
              ]}
            />
          </AnalyticsChartCard>

          <AnalyticsChartCard
            title="Review Aging"
            subtitle="Pending reviews by age bucket"
            loading={reviewAging.isLoading}
            isEmpty={!reviewAging.data?.length}
          >
            <SimpleBarChart
              data={reviewAging.data?.map((d) => ({
                bucket: d.bucket === "under_1d" ? "< 1 day" : d.bucket === "1_3d" ? "1-3 days" : d.bucket === "3_7d" ? "3-7 days" : "> 7 days",
                count: d.count,
              })) ?? []}
              xKey="bucket"
              barKey="count"
              color="#F97316"
            />
          </AnalyticsChartCard>
        </div>
      </div>

      {/* Section 4: AI Executive Insights + Report Builder */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <ExecutiveAiInsights insights={derivedInsights} />
        </div>
        <div className="lg:col-span-1">
          <ReportBuilder templates={emptyTemplates} />
        </div>
      </div>

      {/* Section 4: Metrics Summary Cards */}
      {metricsData && (
        <div>
          <h2 className="text-sm font-semibold text-navy-900 mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-navy-500" /> 24-Hour Activity Summary
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <StatCard
              icon={<Upload className="w-4 h-4" />}
              label="Total Uploads"
              value={metricsData.total_uploads_24h}
              accent="from-sky-500 to-blue-600"
            />
            <StatCard
              icon={<FileText className="w-4 h-4" />}
              label="Total Reviews"
              value={metricsData.total_reviews_24h}
              accent="from-indigo-500 to-blue-600"
            />
            <StatCard
              icon={<Search className="w-4 h-4" />}
              label="Total Findings"
              value={metricsData.total_findings_24h}
              accent="from-purple-500 to-violet-600"
            />
            <StatCard
              icon={<CheckCircle className="w-4 h-4" />}
              label="Upload Success"
              value={`${metricsData.upload_success_rate}%`}
              sub={`${metricsData.avg_upload_latency_ms}ms avg latency`}
              accent="from-green-500 to-emerald-600"
            />
            <StatCard
              icon={<Brain className="w-4 h-4" />}
              label="AI Success"
              value={`${metricsData.ai_success_rate}%`}
              sub={`${metricsData.avg_ai_latency_ms}ms avg latency`}
              accent="from-cyan-500 to-teal-600"
            />
            <StatCard
              icon={<Zap className="w-4 h-4" />}
              label="Tokens Used"
              value={`${(metricsData.total_tokens_used / 1_000_000).toFixed(1)}M`}
              sub={`$${metricsData.total_cost_usd.toFixed(2)} total cost`}
              accent="from-amber-500 to-orange-600"
            />
          </div>
        </div>
      )}

      {/* Section 5: Trend Analytics — board-ready executive trends */}
      <div>
        <h2 className="text-sm font-semibold text-navy-900 mb-3 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-navy-500" /> Trend Analytics
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <AnalyticsChartCard
            title="Upload Volume Trend (30d)"
            subtitle="Daily upload count over time"
            loading={uploadTrend.isLoading}
            isEmpty={!uploadTrend.data?.length}
          >
            <SimpleLineChart
              data={uploadTrend.data ?? []}
              xKey="day"
              lines={[{ key: "count", color: "#3B82F6", name: "Uploads" }]}
            />
          </AnalyticsChartCard>

          <AnalyticsChartCard
            title="AI Cost Trend (30d)"
            subtitle="Daily AI processing cost"
            loading={aiCost.isLoading}
            isEmpty={!aiCost.data?.length}
          >
            <SimpleLineChart
              data={aiCost.data ?? []}
              xKey="day"
              lines={[
                { key: "cost", color: "#D97706", name: "Cost ($)" },
                { key: "tokens", color: "#0F766E", name: "Tokens" },
              ]}
            />
          </AnalyticsChartCard>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <AnalyticsChartCard
            title="Review Aging Distribution"
            subtitle="Pending reviews by age bucket"
            loading={reviewAging.isLoading}
            isEmpty={!reviewAging.data?.length}
          >
            <SimpleBarChart
              data={reviewAging.data?.map((d) => ({
                bucket: d.bucket === "under_1d" ? "< 1 day" : d.bucket === "1_3d" ? "1-3 days" : d.bucket === "3_7d" ? "3-7 days" : "> 7 days",
                count: d.count,
              })) ?? []}
              xKey="bucket"
              barKey="count"
              color="#F97316"
            />
          </AnalyticsChartCard>

          <AnalyticsChartCard
            title="Risk Distribution"
            subtitle="Portfolio risk score breakdown"
            loading={riskDist.isLoading}
            isEmpty={!riskDist.data?.length}
          >
            <SimplePieChart
              data={riskDist.data ?? []}
              nameKey="level"
              valueKey="count"
              colors={{ critical: "#DC2626", high: "#EA580C", medium: "#EAB308", low: "#22C55E", info: "#6B7280" }}
            />
          </AnalyticsChartCard>
        </div>
      </div>

      {/* Section 6: Forecasting — predictive analytics */}
      <div>
        <h2 className="text-sm font-semibold text-navy-900 mb-3 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-navy-500" /> Forecasting &amp; Projections
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Projected Review Volume */}
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-4 h-4 text-blue-500" />
              <span className="text-[10px] font-semibold text-gray-500 uppercase">Projected Review Volume</span>
            </div>
            <p className="text-2xl font-bold text-navy-900 dark:text-white">
              {metricsData ? Math.round(metricsData.total_reviews_24h * 30 * 1.15).toLocaleString() : "—"}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">Next 30 days (est.)</p>
            <div className="mt-2 flex items-center gap-1 text-xs">
              <TrendingUp className="w-3 h-3 text-amber-500" />
              <span className="text-amber-600 font-medium">+15%</span>
              <span className="text-gray-400">vs current run rate</span>
            </div>
          </div>

          {/* Projected AI Usage */}
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-purple-500" />
              <span className="text-[10px] font-semibold text-gray-500 uppercase">Projected AI Usage</span>
            </div>
            <p className="text-2xl font-bold text-navy-900 dark:text-white">
              {healthData ? Math.round(healthData.active_ai_runs * 30 * 1.1).toLocaleString() : "—"}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">AI runs next 30 days (est.)</p>
            <div className="mt-2 flex items-center gap-1 text-xs">
              <TrendingUp className="w-3 h-3 text-purple-500" />
              <span className="text-purple-600 font-medium">+10%</span>
              <span className="text-gray-400">growth trend</span>
            </div>
          </div>

          {/* Projected SLA Risk */}
          <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span className="text-[10px] font-semibold text-gray-500 uppercase">Projected SLA Breaches</span>
            </div>
            <p className="text-2xl font-bold text-red-600">
              {healthData && healthData.sla_breaches > 0 ? Math.round(healthData.sla_breaches * 4.3).toLocaleString() : "0"}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">Next 30 days (est.)</p>
            <div className="mt-2 flex items-center gap-1 text-xs">
              {healthData && healthData.sla_breaches > 0 ? (
                <>
                  <TrendingUp className="w-3 h-3 text-red-500" />
                  <span className="text-red-600 font-medium">↑ {Math.round(healthData.sla_breaches * 4.3)} projected</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-3 h-3 text-green-500" />
                  <span className="text-green-600 font-medium">No breaches projected</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Section 7: Executive Summary */}
      <div className="bg-white dark:bg-navy-800 rounded-xl border border-gray-200 dark:border-navy-700 shadow-sm p-4">
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="w-4 h-4 text-navy-500" />
          <span className="text-xs font-semibold text-gray-500 uppercase">Executive Summary</span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Portfolio Summary */}
          <div className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
            <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Portfolio Health</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">System Status</span>
                <StatusBadge status={healthData?.status ?? "unknown"} />
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Upload Success</span>
                <span className="font-semibold text-navy-900">{healthData?.upload_success_rate ?? "—"}%</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">AI Success Rate</span>
                <span className="font-semibold text-navy-900">{healthData?.ai_success_rate ?? "—"}%</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Active Reviews</span>
                <span className="font-semibold text-navy-900">{healthData?.pending_reviews ?? 0}</span>
              </div>
            </div>
          </div>

          {/* Risk Movement */}
          <div className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
            <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Risk Movement</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">SLA Breaches</span>
                <span className={`font-semibold ${(healthData?.sla_breaches ?? 0) > 0 ? "text-red-600" : "text-green-600"}`}>
                  {healthData?.sla_breaches ?? 0}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Errors (24h)</span>
                <span className={`font-semibold ${(healthData?.recent_errors_24h ?? 0) > 5 ? "text-red-600" : "text-green-600"}`}>
                  {healthData?.recent_errors_24h ?? 0}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Stuck Workflows</span>
                <span className="font-semibold text-navy-900">
                  {(stuckData?.stuck_uploads ?? 0) + (stuckData?.stuck_ai_runs ?? 0) + (stuckData?.stuck_reviews ?? 0)}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Pending Reviews</span>
                <span className="font-semibold text-navy-900">{healthData?.pending_reviews ?? 0}</span>
              </div>
            </div>
          </div>

          {/* Operational Performance */}
          <div className="p-3 rounded-lg bg-gray-50 dark:bg-navy-700">
            <p className="text-[10px] font-semibold text-gray-500 uppercase mb-2">Operational Performance</p>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Avg Upload Latency</span>
                <span className="font-semibold text-navy-900">{metricsData?.avg_upload_latency_ms ?? "—"}ms</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Avg AI Latency</span>
                <span className="font-semibold text-navy-900">{metricsData?.avg_ai_latency_ms ?? "—"}ms</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Total Tokens</span>
                <span className="font-semibold text-navy-900">{metricsData ? `${(metricsData.total_tokens_used / 1_000_000).toFixed(1)}M` : "—"}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Total Cost</span>
                <span className="font-semibold text-navy-900">${metricsData?.total_cost_usd.toFixed(2) ?? "—"}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
