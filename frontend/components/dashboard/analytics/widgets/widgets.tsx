/**
 * Dashboard Widget Components — extracted from AnalyticsCenter into modular widgets.
 *
 * Each widget is a self-contained component that:
 * - Fetches its own data via the useAnalytics hooks
 * - Handles loading, error, and empty states
 * - Renders within a consistent card container
 */

"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Server, Activity, AlertTriangle, Hourglass, Zap, Loader2,
  Upload, Brain, FileText, Search, CheckCircle, XCircle,
  Shield, TrendingUp, BarChart3, Clock,
} from "lucide-react";
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
import {
  AnalyticsChartCard,
  SimpleLineChart,
  SimplePieChart,
  SimpleBarChart,
} from "../SimpleCharts";

// ── Widget Card Wrapper ──────────────────────────────────────────

function WidgetCard({ title, subtitle, children, className = "" }: {
  title: string; subtitle?: string; children: React.ReactNode; className?: string;
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className={`bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden ${className}`}>
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-navy-900">{title}</h3>
        {subtitle && <p className="text-[10px] text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="p-4">{children}</div>
    </motion.div>
  );
}

// ── Status Badge ─────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; text: string; dot: string; label: string }> = {
    healthy:   { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500", label: "Healthy" },
    degraded:  { bg: "bg-yellow-50", text: "text-yellow-700", dot: "bg-yellow-500", label: "Degraded" },
    unhealthy: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", label: "Unhealthy" },
  };
  const c = cfg[status] ?? cfg.unhealthy;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-2 h-2 rounded-full ${c.dot}`} /> {c.label}
    </span>
  );
}

// ── 1. KPI Row Widget ────────────────────────────────────────────

interface KpiWidgetProps {
  healthData?: any;
  metricsData?: any;
  errorsData?: any;
  stuckData?: any;
  onKpiClick?: (kpiId: string) => void;
}

export function KpiRowWidget({ healthData, metricsData, errorsData, stuckData, onKpiClick }: KpiWidgetProps) {
  // This widget is special — it renders inline in the AnalyticsCenter
  // and receives data via props from the parent
  return null;
}

// ── 2. System Health Widget ───────────────────────────────────────

export function SystemHealthWidget() {
  const { data, isLoading } = useSystemHealth();
  if (isLoading) return <WidgetCard title="System Health"><div className="flex justify-center py-8"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div></WidgetCard>;
  if (!data) return <WidgetCard title="System Health"><p className="text-xs text-gray-400 italic">No data</p></WidgetCard>;
  const items = [
    { label: "Status", value: <StatusBadge status={data.status} /> },
    { label: "Active Uploads", value: data.active_uploads, color: data.active_uploads > 10 ? "text-red-600" : "" },
    { label: "Active AI Runs", value: data.active_ai_runs, color: data.active_ai_runs > 20 ? "text-red-600" : "" },
    { label: "Pending Reviews", value: data.pending_reviews, color: data.pending_reviews > 50 ? "text-red-600" : "" },
    { label: "Errors (24h)", value: data.recent_errors_24h, color: data.recent_errors_24h > 5 ? "text-red-600" : "" },
    { label: "SLA Breaches", value: data.sla_breaches ?? 0, color: (data.sla_breaches ?? 0) > 0 ? "text-red-600" : "" },
  ];
  return (
    <WidgetCard title="System Health" subtitle="Active uploads, AI runs, pending reviews">
      <div className="space-y-2.5">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-xs text-gray-500">{item.label}</span>
            <span className={`text-xs font-semibold text-navy-900 ${item.color || ""}`}>{item.value}</span>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}

// ── 3. Stuck Workflows Widget ────────────────────────────────────

export function StuckWorkflowsWidget() {
  const { data, isLoading } = useStuckWorkflows();
  if (isLoading) return <WidgetCard title="Stuck Workflows"><div className="flex justify-center py-8"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div></WidgetCard>;
  if (!data) return <WidgetCard title="Stuck Workflows"><p className="text-xs text-gray-400 italic">No data</p></WidgetCard>;
  const total = (data.stuck_uploads ?? 0) + (data.stuck_ai_runs ?? 0) + (data.stuck_reviews ?? 0);
  if (total === 0) {
    return (
      <WidgetCard title="Stuck Workflows" subtitle="No stuck items detected">
        <div className="flex flex-col items-center py-4 text-center">
          <CheckCircle className="w-8 h-8 text-green-400 mb-2" />
          <p className="text-xs font-medium text-navy-900">All Clear</p>
          <p className="text-[10px] text-gray-400 mt-1">No stuck workflows</p>
        </div>
      </WidgetCard>
    );
  }
  return (
    <WidgetCard title="Stuck Workflows" subtitle={`${total} items need attention`}>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center p-2 rounded-lg bg-orange-50"><p className="text-lg font-bold text-orange-600">{data.stuck_uploads ?? 0}</p><p className="text-[10px] text-gray-500">Uploads</p></div>
        <div className="text-center p-2 rounded-lg bg-purple-50"><p className="text-lg font-bold text-purple-600">{data.stuck_ai_runs ?? 0}</p><p className="text-[10px] text-gray-500">AI Runs</p></div>
        <div className="text-center p-2 rounded-lg bg-blue-50"><p className="text-lg font-bold text-blue-600">{data.stuck_reviews ?? 0}</p><p className="text-[10px] text-gray-500">Reviews</p></div>
      </div>
      {data.items?.slice(0, 3).map((item: any) => (
        <div key={item.resource_id || item.id} className="flex items-center justify-between text-[10px] px-2 py-1 rounded bg-gray-50 mb-1">
          <span className="text-gray-600 truncate max-w-[140px]">{item.resource_type || item.type} — {item.state}</span>
          <span className="font-medium text-orange-600">{item.age_minutes || item.stuck_minutes}m</span>
        </div>
      ))}
    </WidgetCard>
  );
}

// ── 4. Error Breakdown Widget ────────────────────────────────────

export function ErrorBreakdownWidget() {
  const { data, isLoading } = useErrorAnalytics(24);
  if (isLoading) return <WidgetCard title="Error Breakdown"><div className="flex justify-center py-8"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div></WidgetCard>;
  if (!data) return <WidgetCard title="Error Breakdown"><p className="text-xs text-gray-400 italic">No data</p></WidgetCard>;
  const entries = Object.entries(data.by_type ?? {});
  const total = entries.reduce((s, [, v]) => s + v, 0);
  const colors = ["bg-red-500", "bg-orange-500", "bg-yellow-500", "bg-purple-500", "bg-blue-500"];
  return (
    <WidgetCard title="Error Breakdown" subtitle={`${data.total_failures} failures in 24h`}>
      <div className="flex gap-2 mb-3">
        <div className="flex-1 text-center p-1.5 rounded bg-green-50"><p className="text-xs font-semibold text-green-600">{data.retryable_count ?? 0}</p><p className="text-[9px] text-gray-500">Retryable</p></div>
        <div className="flex-1 text-center p-1.5 rounded bg-red-50"><p className="text-xs font-semibold text-red-600">{data.non_retryable_count ?? 0}</p><p className="text-[9px] text-gray-500">Fatal</p></div>
      </div>
      <div className="space-y-2">
        {entries.slice(0, 5).map(([type, count], i) => (
          <div key={type}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-600 capitalize">{type.replace(/_/g, " ")}</span>
              <span className="font-semibold text-navy-900">{count}</span>
            </div>
            <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${colors[i % colors.length]}`} style={{ width: `${(count / total) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}

// ── 5. Upload Trend Widget ───────────────────────────────────────

export function UploadTrendWidget() {
  const { data, isLoading } = useUploadTrend(30);
  return (
    <WidgetCard title="Upload Volume (30d)" subtitle="Uploads per day">
      <div className="h-48">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div>
        ) : !data?.length ? (
          <div className="flex justify-center py-12"><p className="text-xs text-gray-400 italic">No upload data</p></div>
        ) : (
          <SimpleLineChart data={data} xKey="day" lines={[{ key: "count", color: "#3B82F6", name: "Uploads" }]} />
        )}
      </div>
    </WidgetCard>
  );
}

// ── 6. Risk Distribution Widget ──────────────────────────────────

export function RiskDistributionWidget() {
  const { data, isLoading } = useRiskDistribution();
  return (
    <WidgetCard title="Risk Distribution" subtitle="Portfolio risk score breakdown">
      <div className="h-48">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div>
        ) : !data?.length ? (
          <div className="flex justify-center py-12"><p className="text-xs text-gray-400 italic">No risk data</p></div>
        ) : (
          <SimplePieChart
            data={data}
            nameKey="level"
            valueKey="count"
            colors={{ critical: "#DC2626", high: "#EA580C", medium: "#EAB308", low: "#22C55E", info: "#6B7280" }}
          />
        )}
      </div>
    </WidgetCard>
  );
}

// ── 7. Findings by Clause Widget ─────────────────────────────────

export function FindingsByClauseWidget() {
  const { data, isLoading } = useFindingsByClause();
  return (
    <WidgetCard title="Findings by Clause Type" subtitle="AI-identified risk areas across portfolio">
      <div className="h-48">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div>
        ) : !data?.length ? (
          <div className="flex justify-center py-12"><p className="text-xs text-gray-400 italic">No findings data</p></div>
        ) : (
          <SimpleBarChart data={data} xKey="clause_type" barKey="count" color="#8B5CF6" horizontal={true} />
        )}
      </div>
    </WidgetCard>
  );
}

// ── 8. AI Cost Trend Widget ──────────────────────────────────────

export function AiCostTrendWidget() {
  const { data, isLoading } = useAiCostTrend(30);
  return (
    <WidgetCard title="AI Cost & Token Usage (30d)" subtitle="Daily AI processing economics">
      <div className="h-48">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div>
        ) : !data?.length ? (
          <div className="flex justify-center py-12"><p className="text-xs text-gray-400 italic">No AI cost data</p></div>
        ) : (
          <SimpleLineChart
            data={data}
            xKey="day"
            lines={[
              { key: "tokens", color: "#0F766E", name: "Tokens" },
              { key: "cost", color: "#D97706", name: "Cost ($)" },
            ]}
          />
        )}
      </div>
    </WidgetCard>
  );
}

// ── 9. Review Aging Widget ───────────────────────────────────────

export function ReviewAgingWidget() {
  const { data, isLoading } = useReviewAging();
  const mapped = (data ?? []).map((d: any) => ({
    bucket: d.bucket === "under_1d" ? "< 1 day" : d.bucket === "1_3d" ? "1-3 days" : d.bucket === "3_7d" ? "3-7 days" : "> 7 days",
    count: d.count,
  }));
  return (
    <WidgetCard title="Review Aging" subtitle="Pending reviews by age bucket">
      <div className="h-48">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div>
        ) : !mapped.length ? (
          <div className="flex justify-center py-12"><p className="text-xs text-gray-400 italic">No review data</p></div>
        ) : (
          <SimpleBarChart data={mapped} xKey="bucket" barKey="count" color="#F97316" />
        )}
      </div>
    </WidgetCard>
  );
}

// ── 10. Executive Summary Widget ─────────────────────────────────

export function ExecutiveSummaryWidget() {
  const { data, isLoading } = useExecutiveSummary();
  if (isLoading) return <WidgetCard title="Executive Summary"><div className="flex justify-center py-8"><Loader2 className="w-5 h-5 text-gray-400 animate-spin" /></div></WidgetCard>;
  if (!data) return <WidgetCard title="Executive Summary"><p className="text-xs text-gray-400 italic">No data</p></WidgetCard>;
  const metrics = [
    { label: "Portfolio Risk", value: data.portfolio_risk, color: data.portfolio_risk === "HIGH" ? "text-red-600" : data.portfolio_risk === "MODERATE" ? "text-amber-600" : "text-green-600" },
    { label: "Avg Risk Score", value: `${(data.avg_risk_score * 100).toFixed(0)}%`, color: data.avg_risk_score >= 0.5 ? "text-red-600" : "text-navy-900" },
    { label: "Critical Contracts", value: data.critical_contracts, color: data.critical_contracts > 0 ? "text-red-600" : "" },
    { label: "High-Risk Clause Types", value: data.high_risk_clause_types, color: data.high_risk_clause_types > 5 ? "text-orange-600" : "" },
    { label: "Missing Clause Findings", value: data.missing_clause_findings, color: data.missing_clause_findings > 10 ? "text-amber-600" : "" },
    { label: "Avg Review SLA", value: `${data.avg_review_sla_days}d`, color: data.avg_review_sla_days > 3 ? "text-red-600" : "" },
  ];
  return (
    <WidgetCard title="Executive Summary" subtitle="Portfolio-level intelligence">
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="text-center p-2 rounded-lg bg-gray-50">
            <p className={`text-lg font-bold ${m.color || "text-navy-900"}`}>{m.value}</p>
            <p className="text-[9px] text-gray-500 mt-0.5">{m.label}</p>
          </div>
        ))}
      </div>
    </WidgetCard>
  );
}
