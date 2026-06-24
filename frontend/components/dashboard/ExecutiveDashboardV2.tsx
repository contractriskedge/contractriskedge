/**
 * ExecutiveDashboard — Sprint 31.1 leadership pane.
 *
 * Widgets:
 * - Executive Summary KPI cards (total, active, pending approvals/signatures, high-risk, obligations)
 * - Risk Distribution (donut chart)
 * - Workflow Distribution (bar/stacked)
 * - Signature Status
 * - Risk Trend (12-month line chart)
 * - Renewal Pipeline (30/60/90 day buckets)
 *
 * All data comes from the real backend API at /api/v1/dashboard/*.
 * No mock data.
 */

"use client";

import React, { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FileText, AlertTriangle, CheckCircle2, Clock,
  Users, Activity, BarChart3, RefreshCw, PenSquare,
  FileSignature, TrendingUp, CalendarDays,
} from "lucide-react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line, Legend,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services";
import { AsyncBoundary } from "@/components/shared/AsyncBoundary";
import { CardSkeleton } from "@/components/shared/LoadingSkeleton";
import { KpiCard } from "@/components/shared/KpiCard";

// ── Types ──────────────────────────────────────────────────────

interface ExecutiveSummary {
  total_contracts: number;
  active_contracts: number;
  contracts_this_month: number;
  pending_approvals: number;
  pending_signatures: number;
  high_risk_contracts: number;
  upcoming_renewals: number;
  open_obligations: number;
}

interface RiskDistribution {
  critical: number;
  high: number;
  medium: number;
  low: number;
  unknown: number;
}

interface RiskTrendPoint {
  month: string;
  avg_risk_score: number;
}

interface WorkflowDistribution {
  in_review?: number;
  in_negotiation?: number;
  pending_approval?: number;
  approved?: number;
  executed?: number;
  other?: number;
  [key: string]: number | undefined;
}

interface RenewalBuckets {
  "30_days": number;
  "60_days": number;
  "90_days": number;
  expired: number;
  beyond_90: number;
}

interface SignatureStatus {
  sent: number;
  viewed: number;
  signed: number;
  declined: number;
  expired: number;
}

// ── Query Hooks ────────────────────────────────────────────────

function useExecutiveSummary() {
  return useQuery<ExecutiveSummary>({
    queryKey: ["dashboard", "executive-summary"],
    queryFn: () => api.get("/api/v1/dashboard/executive-summary"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    refetchOnWindowFocus: true,
  });
}

function useRiskDistribution() {
  return useQuery<RiskDistribution>({
    queryKey: ["dashboard", "risk-distribution"],
    queryFn: () => api.get("/api/v1/dashboard/risk-distribution"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

function useRiskTrend(months = 12) {
  return useQuery<RiskTrendPoint[]>({
    queryKey: ["dashboard", "risk-trend", months],
    queryFn: () => api.get(`/api/v1/dashboard/risk-trend?months=${months}`),
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
  });
}

function useWorkflowDistribution() {
  return useQuery<WorkflowDistribution>({
    queryKey: ["dashboard", "workflow-distribution"],
    queryFn: () => api.get("/api/v1/dashboard/workflow-distribution"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

function useRenewalBuckets() {
  return useQuery<RenewalBuckets>({
    queryKey: ["dashboard", "renewal-buckets"],
    queryFn: () => api.get("/api/v1/dashboard/renewal-buckets"),
    staleTime: 5 * 60_000,
    gcTime: 10 * 60_000,
  });
}

function useSignatureStatus() {
  return useQuery<SignatureStatus>({
    queryKey: ["dashboard", "signature-status"],
    queryFn: () => api.get("/api/v1/dashboard/signature-status"),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

// ── Color Palette ──────────────────────────────────────────────

const RISK_COLORS: Record<string, string> = {
  critical: "#EF4444",
  high: "#F97316",
  medium: "#F59E0B",
  low: "#6B7280",
  unknown: "#D1D5DB",
};

const WORKFLOW_COLORS: Record<string, string> = {
  in_review: "#8B5CF6",
  in_negotiation: "#F59E0B",
  pending_approval: "#3B82F6",
  approved: "#10B981",
  executed: "#059669",
  other: "#9CA3AF",
};

const SIGNATURE_COLORS: Record<string, string> = {
  sent: "#3B82F6",
  viewed: "#F59E0B",
  signed: "#10B981",
  declined: "#EF4444",
  expired: "#6B7280",
};

const RENEWAL_COLORS: Record<string, string> = {
  "30_days": "#EF4444",
  "60_days": "#F97316",
  "90_days": "#F59E0B",
  expired: "#6B7280",
  beyond_90: "#10B981",
};

// ── Chart Wrappers ─────────────────────────────────────────────

function RiskDonutChart({ data }: { data: RiskDistribution }) {
  const chartData = Object.entries(data)
    .filter(([_, v]) => v > 0)
    .map(([key, value]) => ({ name: key.charAt(0).toUpperCase() + key.slice(1), value, color: RISK_COLORS[key] }));

  if (chartData.length === 0) {
    return <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-8">No risk data</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={90}
          paddingAngle={2}
          dataKey="value"
          stroke="none"
        >
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            borderRadius: "8px",
            border: "1px solid #e5e7eb",
            boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)",
          }}
          formatter={(value, name) => [value, name] as [number, string]}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

function WorkflowBarChart({ data }: { data: WorkflowDistribution }) {
  const chartData = Object.entries(data)
    .filter(([_, v]) => typeof v === 'number' && v > 0)
    .map(([key, value]) => ({
      name: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      value: value as number,
      fill: WORKFLOW_COLORS[key] || "#9CA3AF",
    }));

  if (chartData.length === 0) {
    return <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-8">No workflow data</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis type="number" tick={{ fontSize: 12 }} />
        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            borderRadius: "8px",
            border: "1px solid #e5e7eb",
          }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function SignatureBarChart({ data }: { data: SignatureStatus }) {
  const chartData = Object.entries(data)
    .filter(([_, v]) => v > 0)
    .map(([key, value]) => ({
      name: key.charAt(0).toUpperCase() + key.slice(1),
      value,
      fill: SIGNATURE_COLORS[key] || "#9CA3AF",
    }));

  if (chartData.length === 0) {
    return <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-8">No signature data</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            borderRadius: "8px",
            border: "1px solid #e5e7eb",
          }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function RiskTrendChart({ data }: { data: RiskTrendPoint[] }) {
  if (!data || data.length === 0) {
    return <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-8">No trend data</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => {
            const d = new Date(v);
            return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
          }}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          domain={[0, 1]}
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip
          contentStyle={{
            borderRadius: "8px",
            border: "1px solid #e5e7eb",
          }}
          formatter={(value) => [`${(Number(value) * 100).toFixed(1)}%`, "Avg Risk Score"] as [string, string]}
          labelFormatter={(v) => new Date(v).toLocaleDateString("en-US", { month: "long", year: "numeric" })}
        />
        <Line
          type="monotone"
          dataKey="avg_risk_score"
          stroke="#8B5CF6"
          strokeWidth={2}
          dot={{ r: 3, fill: "#8B5CF6" }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function RenewalBarChart({ data }: { data: RenewalBuckets }) {
  const labels: Record<string, string> = {
    "30_days": "30 Days",
    "60_days": "60 Days",
    "90_days": "90 Days",
    expired: "Expired",
    beyond_90: "Beyond 90",
  };

  const chartData = Object.entries(data)
    .filter(([_, v]) => v > 0)
    .map(([key, value]) => ({
      name: labels[key] || key,
      value,
      fill: RENEWAL_COLORS[key] || "#9CA3AF",
    }));

  if (chartData.length === 0) {
    return <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-8">No renewal data</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            borderRadius: "8px",
            border: "1px solid #e5e7eb",
          }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Legend Component ───────────────────────────────────────────

function ColorLegend({ items }: { items: { label: string; color: string; key: string }[] }) {
  return (
    <div className="flex flex-wrap gap-3 mt-2">
      {items.map((item) => (
        <div key={item.key} className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
          {item.label}
        </div>
      ))}
    </div>
  );
}

// ── Chart Card Shell ───────────────────────────────────────────

function ChartCard({
  title,
  icon,
  children,
  className = "",
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <span className="text-gray-500 dark:text-gray-400">{icon}</span>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
      </div>
      {children}
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────

export function ExecutiveDashboard() {
  const router = useRouter();
  const [refreshing, setRefreshing] = useState(false);

  const summaryQuery = useExecutiveSummary();
  const riskQuery = useRiskDistribution();
  const riskTrendQuery = useRiskTrend(12);
  const workflowQuery = useWorkflowDistribution();
  const renewalQuery = useRenewalBuckets();
  const signatureQuery = useSignatureStatus();

  const allQueries = [summaryQuery, riskQuery, riskTrendQuery, workflowQuery, renewalQuery, signatureQuery];
  const isLoading = allQueries.some((q) => q.isLoading);
  const anyError = allQueries.find((q) => q.error);
  const isEmpty = summaryQuery.isFetched && !summaryQuery.data;

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all(allQueries.map((q) => q.refetch()));
    setRefreshing(false);
  }, []);

  const summary = summaryQuery.data;

  // Build risk legend items
  const riskLegendItems = Object.entries(RISK_COLORS).map(([key, color]) => ({
    key,
    label: key.charAt(0).toUpperCase() + key.slice(1),
    color,
  }));

  // Build workflow legend items
  const workflowLabels: Record<string, string> = {
    in_review: "In Review",
    in_negotiation: "Negotiation",
    pending_approval: "Pending Approval",
    approved: "Approved",
    executed: "Executed",
    other: "Other",
  };
  const workflowLegendItems = Object.entries(WORKFLOW_COLORS).map(([key, color]) => ({
    key,
    label: workflowLabels[key] || key,
    color,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Executive Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Contract lifecycle KPIs — real-time aggregate view
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <AsyncBoundary
        isLoading={isLoading}
        error={anyError?.error}
        isEmpty={isEmpty}
        emptyMessage="No dashboard data available"
        emptyDescription="Upload contracts and run AI analysis to see aggregate KPIs."
        emptyIcon={<BarChart3 className="h-12 w-12 text-gray-300" />}
        loadingSkeleton={<CardSkeleton count={6} columns={3} />}
        onRetry={handleRefresh}
      >
        {/* Row 1: Executive Summary KPI Cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            title="Total Contracts"
            value={summary?.total_contracts ?? 0}
            subtitle={`${summary?.contracts_this_month ?? 0} this month`}
            icon={<FileText className="h-5 w-5 text-white" />}
            color="bg-blue-500"
            onClick={() => router.push("/contracts")}
          />
          <KpiCard
            title="Active Contracts"
            value={summary?.active_contracts ?? 0}
            subtitle="Non-terminal status"
            icon={<Activity className="h-5 w-5 text-white" />}
            color="bg-green-500"
            onClick={() => router.push("/contracts")}
          />
          <KpiCard
            title="Pending Approvals"
            value={summary?.pending_approvals ?? 0}
            subtitle="Awaiting decision"
            icon={<Clock className="h-5 w-5 text-white" />}
            color="bg-amber-500"
            onClick={() => router.push("/reviews")}
          />
          <KpiCard
            title="Pending Signatures"
            value={summary?.pending_signatures ?? 0}
            subtitle="Awaiting signature"
            icon={<FileSignature className="h-5 w-5 text-white" />}
            color="bg-purple-500"
            onClick={() => router.push("/signatures")}
          />
          <KpiCard
            title="High Risk Contracts"
            value={summary?.high_risk_contracts ?? 0}
            subtitle="Risk score ≥ 0.7"
            icon={<AlertTriangle className="h-5 w-5 text-white" />}
            color="bg-red-500"
            onClick={() => router.push("/contracts?risk=high")}
          />
          <KpiCard
            title="Upcoming Renewals"
            value={summary?.upcoming_renewals ?? 0}
            subtitle="Within 30 days"
            icon={<CalendarDays className="h-5 w-5 text-white" />}
            color="bg-orange-500"
            onClick={() => router.push("/contracts?renewals=upcoming")}
          />
          <KpiCard
            title="Open Obligations"
            value={summary?.open_obligations ?? 0}
            subtitle="Active commitments"
            icon={<CheckCircle2 className="h-5 w-5 text-white" />}
            color="bg-teal-500"
            onClick={() => router.push("/obligations")}
          />
          <KpiCard
            title="Contracts This Month"
            value={summary?.contracts_this_month ?? 0}
            subtitle="New this month"
            icon={<TrendingUp className="h-5 w-5 text-white" />}
            color="bg-indigo-500"
            onClick={() => router.push("/contracts")}
          />
        </div>

        {/* Row 2: Risk Distribution + Workflow Distribution + Signature Status */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <ChartCard title="Risk Distribution" icon={<AlertTriangle className="h-4 w-4" />}>
            <RiskDonutChart data={riskQuery.data ?? { critical: 0, high: 0, medium: 0, low: 0, unknown: 0 }} />
            <ColorLegend items={riskLegendItems} />
          </ChartCard>

          <ChartCard title="Workflow Distribution" icon={<BarChart3 className="h-4 w-4" />}>
            <WorkflowBarChart data={workflowQuery.data ?? {}} />
            <ColorLegend items={workflowLegendItems} />
          </ChartCard>

          <ChartCard title="Signature Status" icon={<FileSignature className="h-4 w-4" />}>
            <SignatureBarChart data={signatureQuery.data ?? { sent: 0, viewed: 0, signed: 0, declined: 0, expired: 0 }} />
          </ChartCard>
        </div>

        {/* Row 3: Risk Trend + Renewal Pipeline */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ChartCard title="Risk Trend (12 Months)" icon={<TrendingUp className="h-4 w-4" />}>
            <RiskTrendChart data={riskTrendQuery.data ?? []} />
          </ChartCard>

          <ChartCard title="Renewal Pipeline" icon={<CalendarDays className="h-4 w-4" />}>
            <RenewalBarChart data={renewalQuery.data ?? { "30_days": 0, "60_days": 0, "90_days": 0, expired: 0, beyond_90: 0 }} />
          </ChartCard>
        </div>
      </AsyncBoundary>
    </div>
  );
}
