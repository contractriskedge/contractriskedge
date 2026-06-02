"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { ShoppingCart, Download, RefreshCw, ShieldCheck, Zap, ListChecks, Users, Sparkles, Bell, Loader2, AlertCircle } from "lucide-react";
import { ProcurementKpiCards } from "./ProcurementKpiCards";
import { SpendTrendChart, VendorCategoryChart, GeoRiskChart, SupplierRiskTrendChart, SpendConcentrationChart } from "./RiskAnalytics";
import { ProcurementAiInsights, SavingsWidget } from "./AiInsights";
import { SupplierTable } from "./SupplierTable";
import { SupplierDrawer } from "./SupplierDrawer";
import { ProcurementWorkflows } from "./Workflows";
import { ProcurementFilterBar } from "./FilterBar";
import { useProcurementDashboard, useSuppliers } from "@/services/hooks/useProcurement";
import type { SupplierRecord, WorkflowItem } from "./types";

interface ProcurementFilters {
  category: string; geography: string; riskLevel: string; spendRange: string;
  complianceStatus: string; owner: string; businessUnit: string;
}

const defaultFilters: ProcurementFilters = {
  category: "", geography: "", riskLevel: "", spendRange: "",
  complianceStatus: "", owner: "", businessUnit: "",
};

function VendorPulseSummary({ totalSuppliers, criticalCount, complianceAlerts, aiAlerts, highRiskSpend }: { totalSuppliers: number; criticalCount: number; complianceAlerts: number; aiAlerts: number; highRiskSpend: number }) {
  return (
    <div className="rounded-3xl bg-slate-950 text-white p-6 shadow-xl border border-white/10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Vendor 360 Health</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Enterprise supplier relationship intelligence</h2>
          <p className="mt-2 text-sm text-slate-300">A unified view of risk, spend, compliance and vendor readiness across the procurement portfolio.</p>
        </div>
        <div className="rounded-3xl bg-white/5 px-4 py-3 text-right">
          <p className="text-[10px] uppercase tracking-[0.24em] text-slate-400">AI Insights</p>
          <p className="mt-1 text-3xl font-semibold text-white">{aiAlerts}</p>
          <p className="text-[11px] text-slate-400">active alerts</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 mt-6 sm:grid-cols-4">
        {[
          { label: "Total vendors", value: `${totalSuppliers}`, icon: <Users className="w-4 h-4" /> },
          { label: "Critical risk", value: `${criticalCount}`, icon: <ShieldCheck className="w-4 h-4" /> },
          { label: "Compliance alerts", value: `${complianceAlerts}`, icon: <ListChecks className="w-4 h-4" /> },
          { label: "Risk exposure", value: `$${highRiskSpend.toFixed(1)}M`, icon: <Zap className="w-4 h-4" /> },
        ].map((item) => (
          <div key={item.label} className="rounded-3xl bg-white/5 p-3 border border-white/10">
            <div className="flex items-center gap-2 text-slate-300">{item.icon}<span className="text-[10px] uppercase tracking-[0.24em]">{item.label}</span></div>
            <p className="mt-3 text-2xl font-semibold text-white">{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function TopVendorPulse({ highlightSuppliers }: { highlightSuppliers: SupplierRecord[] }) {
  return (
    <div className="rounded-3xl bg-white border border-gray-200 shadow-sm p-5">
      <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-navy-900"><Sparkles className="w-4 h-4 text-navy-700" /> Top vendor risk signals</div>
      <div className="space-y-3">
        {highlightSuppliers.map((supplier) => (
          <div key={supplier.id} className="rounded-2xl border border-gray-100 p-3 hover:border-navy-200 transition-colors">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-navy-900">{supplier.name}</p>
                <p className="text-[11px] text-gray-500">{supplier.category} • {supplier.country}</p>
              </div>
              <span className="text-[10px] font-bold text-white bg-red-600 px-2 py-1 rounded-full">Risk {supplier.riskScore}/10</span>
            </div>
            <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-gray-600">
              <span>{supplier.activeContracts} contracts</span>
              <span>${supplier.totalSpend}M spend</span>
              <span>{supplier.slaPerformance}% SLA</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function VendorAgenda({ workflows }: { workflows: WorkflowItem[] }) {
  const topItems = workflows.slice(0, 3);
  return (
    <div className="rounded-3xl bg-white border border-gray-200 shadow-sm p-5">
      <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-navy-900"><Bell className="w-4 h-4 text-orange-500" /> Action agenda</div>
      <div className="space-y-3">
        {topItems.map((item) => (
          <div key={item.id} className="rounded-2xl border border-gray-100 p-3 hover:border-orange-200 transition-colors">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-navy-900">{item.title}</p>
              <span className={`text-[10px] font-semibold px-2 py-1 rounded-full ${item.status === "pending" ? "bg-orange-50 text-orange-700" : item.status === "in_progress" ? "bg-blue-50 text-blue-700" : "bg-green-50 text-green-700"}`}>{item.status.replace("_", " ")}</span>
            </div>
            <p className="text-[11px] text-gray-500 mt-1">{item.description}</p>
            <div className="mt-3 flex items-center justify-between text-[10px] text-gray-500">
              <span>Owner: {item.assignee}</span>
              <span>{item.dueDate}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ProcurementDashboard() {
  const [filters, setFilters] = useState<ProcurementFilters>({ ...defaultFilters });
  const [selectedSupplier, setSelectedSupplier] = useState<SupplierRecord | null>(null);

  // Real API hooks replacing mockData
  const { data: dashboardData, isLoading: dashboardLoading, error: dashboardError, refetch: refetchDashboard } = useProcurementDashboard();
  const { data: suppliersData, isLoading: suppliersLoading } = useSuppliers();

  const isLoading = dashboardLoading || suppliersLoading;

  const supplierRecords: SupplierRecord[] = suppliersData?.data ?? dashboardData?.suppliers ?? [];
  const procurementInsights = dashboardData?.kpis ?? [];
  const totalSuppliers = dashboardData?.total_suppliers ?? supplierRecords.length;
  const criticalSuppliers = dashboardData?.high_risk_suppliers ?? supplierRecords.filter((s: any) => (s.riskScore ?? 0) >= 8).length;
  const complianceAlerts = supplierRecords.filter((s: any) => (s as any).complianceStatus !== "compliant").length;
  const aiAlerts = procurementInsights.length;
  const highRiskSpend = supplierRecords.filter((s: any) => (s.riskScore ?? 0) >= 8).reduce((sum: number, s: any) => sum + (s.totalSpend ?? 0), 0);
  const topRiskSuppliers = [...supplierRecords].sort((a: any, b: any) => (b.riskScore ?? 0) - (a.riskScore ?? 0)).slice(0, 3);

  const handleFilterChange = (key: keyof ProcurementFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };
  const resetFilters = () => setFilters({ ...defaultFilters });

  const filteredSuppliers = useMemo(() => {
    return supplierRecords.filter((s: any) => {
      if (filters.category && s.category !== filters.category) return false;
      if (filters.geography && s.country !== filters.geography) return false;
      if (filters.riskLevel) {
        if (filters.riskLevel === "critical" && (s.riskScore ?? 0) < 8) return false;
        else if (filters.riskLevel === "high" && ((s.riskScore ?? 0) < 6 || (s.riskScore ?? 0) >= 8)) return false;
        else if (filters.riskLevel === "medium" && ((s.riskScore ?? 0) < 4 || (s.riskScore ?? 0) >= 6)) return false;
        else if (filters.riskLevel === "low" && (s.riskScore ?? 0) >= 4) return false;
      }
      if (filters.complianceStatus && s.complianceStatus !== filters.complianceStatus) return false;
      return true;
    });
  }, [filters, supplierRecords]);

  // Loading state
  if (isLoading && supplierRecords.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-gold-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading procurement data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (dashboardError && supplierRecords.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load procurement data</p>
          <p className="text-xs text-gray-500 mb-4">{(dashboardError as Error)?.message || "An unexpected error occurred"}</p>
          <button onClick={() => refetchDashboard()} className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5 pb-24">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="grid gap-4 lg:grid-cols-[1.7fr_0.9fr]">
        <div className="rounded-3xl bg-white border border-gray-200 shadow-sm p-6">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full bg-sky-100 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">Vendor 360 Intelligence</div>
              <h1 className="mt-4 text-3xl font-semibold tracking-tight text-navy-900">Enterprise supplier relationship intelligence workspace</h1>
              <p className="mt-3 max-w-2xl text-sm text-gray-600">Correlate spend, risk, compliance and vendor performance with AI-driven insights and a proactive supplier action agenda.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button className="inline-flex items-center gap-2 rounded-full bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800 transition">Refresh data</button>
              <button className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition">Export portfolio</button>
            </div>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Total spend", value: "$142.8M", detail: "Portfolio value", icon: <Download className="w-4 h-4 text-navy-700" /> },
              { label: "High-risk vendors", value: `${criticalSuppliers}`, detail: "Score ≥ 8", icon: <ShieldCheck className="w-4 h-4 text-orange-500" /> },
              { label: "AI alerts", value: `${aiAlerts}`, detail: "Active insights", icon: <Sparkles className="w-4 h-4 text-emerald-500" /> },
              { label: "Compliance gaps", value: `${complianceAlerts}`, detail: "Non-compliant suppliers", icon: <ListChecks className="w-4 h-4 text-sky-500" /> },
            ].map((metric) => (
              <div key={metric.label} className="rounded-3xl border border-gray-200 bg-slate-50 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">{metric.label}</p>
                  <div className="rounded-2xl bg-white p-2 shadow-sm">{metric.icon}</div>
                </div>
                <p className="mt-4 text-2xl font-semibold text-navy-900">{metric.value}</p>
                <p className="mt-1 text-[11px] text-gray-500">{metric.detail}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <div className="rounded-3xl border border-gray-200 bg-slate-50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-500">Portfolio readiness</p>
              <div className="mt-4 space-y-3">
                <ProgressRow label="Contract coverage" value={92} tone="success" />
                <ProgressRow label="Renewal readiness" value={78} tone="warning" />
                <ProgressRow label="AI monitored" value={84} tone="info" />
              </div>
            </div>
            <div className="rounded-3xl border border-gray-200 bg-white p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-500">Vendor concentration</p>
              <p className="mt-3 text-sm text-gray-600">Top 5 suppliers represent 42% of total portfolio spend. Diversification is recommended for critical services.</p>
              <div className="mt-4 space-y-3">
                <ConcentrationMetric label="Top cloud suppliers" value="62%" />
                <ConcentrationMetric label="Renewal exposure" value="$18.6M" />
              </div>
            </div>
            <div className="rounded-3xl border border-gray-200 bg-white p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-gray-500">Risk pulse</p>
              <p className="mt-3 text-sm text-gray-600">AI has surfaced 5 critical vendor alerts and 12 event-based escalation triggers for your executive team.</p>
              <div className="mt-4 space-y-3">
                <PulseMetric label="Critical insights" value="5" color="red" />
                <PulseMetric label="Near-term renewals" value="8" color="amber" />
              </div>
            </div>
          </div>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-6">
          <VendorPulseSummary totalSuppliers={totalSuppliers} criticalCount={criticalSuppliers} complianceAlerts={complianceAlerts} aiAlerts={aiAlerts} highRiskSpend={highRiskSpend} />
          <TopVendorPulse highlightSuppliers={topRiskSuppliers} />
          <VendorAgenda workflows={workflowItems} />
        </aside>
      </motion.div>

      <ProcurementKpiCards metrics={procurementKpis} />
      <ProcurementFilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} />

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <SpendTrendChart data={spendTrendData} />
            <VendorCategoryChart data={vendorCategoryData} />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <GeoRiskChart data={geoRiskData} />
            <SupplierRiskTrendChart data={riskTrendData} />
            <SpendConcentrationChart data={vendorCategoryData} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <ProcurementAiInsights insights={procurementInsights} />
            <SavingsWidget opportunities={savingsOpportunities} />
          </div>
          <SupplierTable suppliers={filteredSuppliers} onSelect={setSelectedSupplier} />
        </div>
        <div className="space-y-4">
          <ProcurementWorkflows workflows={workflowItems} />
          <TopVendorPulse highlightSuppliers={topRiskSuppliers} />
        </div>
      </div>

      <SupplierDrawer supplier={selectedSupplier} onClose={() => setSelectedSupplier(null)} />
    </div>
  );
}

function ProgressRow({ label, value, tone }: { label: string; value: number; tone: "success" | "warning" | "info" }) {
  const colors = {
    success: "bg-emerald-500",
    warning: "bg-amber-500",
    info: "bg-sky-500",
  };
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{label}</span>
        <span className="font-semibold text-slate-900">{value}%</span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-slate-200 overflow-hidden">
        <div className={`${colors[tone]} h-full`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function ConcentrationMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-3 border border-slate-100">
      <p className="text-[11px] text-gray-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-navy-900">{value}</p>
    </div>
  );
}

function PulseMetric({ label, value, color }: { label: string; value: string; color: "red" | "amber" | "blue" }) {
  const map = {
    red: "bg-red-50 text-red-700",
    amber: "bg-amber-50 text-amber-700",
    blue: "bg-sky-50 text-sky-700",
  };
  return (
    <div className="flex items-center justify-between rounded-2xl border border-gray-100 bg-slate-50 p-3">
      <p className="text-[11px] text-gray-500">{label}</p>
      <span className={`rounded-full px-3 py-1 text-[11px] font-semibold ${map[color]}`}>{value}</span>
    </div>
  );
}
