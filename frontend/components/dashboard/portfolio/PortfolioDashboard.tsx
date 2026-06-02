"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Download, RefreshCw, LayoutDashboard, Loader2, AlertCircle } from "lucide-react";
import { KpiGrid } from "./KpiCards";
import {
  RiskTrendChart,
  MonthlyExposureChart,
  VendorRiskChart,
  ClauseCategoryChart,
  DepartmentRiskChart,
  FilterBar,
} from "./RiskAnalytics";
import { AiInsightsPanel } from "./AiInsights";
import { ContractsTable } from "./ContractsTable";
import { FinancialExposurePanel } from "./FinancialExposure";
import { WorkflowAlertsPanel } from "./WorkflowAlerts";
import { useContracts, useContractKpis } from "@/services/hooks/useContracts";

// ── Loading Skeleton ────────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-32 bg-gray-100 rounded-xl" />
        ))}
      </div>
      <div className="h-72 bg-gray-100 rounded-xl" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="h-64 bg-gray-100 rounded-xl" />
        <div className="h-64 bg-gray-100 rounded-xl" />
      </div>
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────────────────────────────

export function PortfolioDashboard() {
  const [filters, setFilters] = useState<Record<string, string>>({
    businessUnit: "all",
    vendor: "all",
    geography: "all",
    contractType: "all",
    riskLevel: "all",
  });
  const [lastRefreshed] = useState(new Date().toLocaleTimeString());

  // Real API hooks replacing mockData
  const { data: contractsData, isLoading, error, refetch } = useContracts();
  const { data: kpisData } = useContractKpis();

  const portfolioContracts = contractsData?.data ?? [];
  const kpiMetrics = kpisData ? [
    { id: "total", label: "Total Contracts", value: kpisData.total_contracts.toLocaleString(), trend: 0, trendDirection: "neutral" as const, icon: "FileText", color: "from-blue-500 to-blue-600" },
    { id: "high-risk", label: "High Risk", value: kpisData.high_risk_count.toString(), trend: 0, trendDirection: "neutral" as const, icon: "AlertTriangle", color: "from-red-500 to-red-600" },
    { id: "expiring", label: "Expiring Soon", value: kpisData.expiring_soon.toString(), trend: 0, trendDirection: "neutral" as const, icon: "Clock", color: "from-amber-500 to-amber-600" },
    { id: "value", label: "Value at Risk", value: `$${(kpisData.total_value_at_risk / 1_000_000).toFixed(1)}M`, trend: 0, trendDirection: "neutral" as const, icon: "DollarSign", color: "from-green-500 to-green-600" },
  ] : [];

  const riskTrendData = [];
  const monthlyExposureData = [];
  const vendorRiskData = [];
  const clauseCategoryData = [];
  const departmentRiskData = [];
  const aiInsights = [];
  const financialExposure = [];
  const workflowAlerts = [];

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  // Apply filters to contracts
  const filteredContracts = useMemo(() => {
    return portfolioContracts.filter((c: any) => {
      if (filters.businessUnit !== "all" && c.businessUnit !== filters.businessUnit) return false;
      if (filters.vendor !== "all" && c.vendor !== filters.vendor) return false;
      if (filters.geography !== "all" && c.geography !== filters.geography) return false;
      if (filters.contractType !== "all" && c.contractType !== filters.contractType) return false;
      if (filters.riskLevel !== "all") {
        if (filters.riskLevel === "critical" && (c.riskScore ?? 0) < 8) return false;
        else if (filters.riskLevel === "high" && (c.riskScore < 6 || c.riskScore >= 8)) return false;
        else if (filters.riskLevel === "medium" && (c.riskScore < 4 || c.riskScore >= 6)) return false;
        else if (filters.riskLevel === "low" && c.riskScore >= 4) return false;
      }
      return true;
    });
  }, [filters]);

  // Loading state
  if (isLoading && portfolioContracts.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-gold-400 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading portfolio data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && portfolioContracts.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 mb-1">Failed to load portfolio data</p>
          <p className="text-xs text-gray-500 mb-4">{(error as Error)?.message || "An unexpected error occurred"}</p>
          <button onClick={() => refetch()} className="inline-flex items-center gap-1.5 text-xs font-medium text-gold-600 hover:text-gold-700">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5 pb-24">
      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-navy-700 to-navy-900 flex items-center justify-center shadow-sm">
            <LayoutDashboard className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Portfolio Risk Command Center</h1>
            <p className="text-xs text-gray-500 mt-0.5">
              Real-time AI-powered risk intelligence • Last refreshed: {lastRefreshed}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Download className="w-3.5 h-3.5" />
            Export Report
          </button>
        </div>
      </motion.div>

      {/* ── KPI Row ── */}
      <KpiGrid metrics={kpiMetrics} />

      {/* ── Filters ── */}
      <FilterBar filters={filters} onChange={handleFilterChange} />

      {/* ── Section 1: Risk Trend Analytics ── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-navy-900">Risk Trend Analytics</h2>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <RiskTrendChart data={riskTrendData} />
          <MonthlyExposureChart data={monthlyExposureData} />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <VendorRiskChart data={vendorRiskData} />
          <DepartmentRiskChart data={departmentRiskData} />
        </div>
        <div className="mt-4">
          <ClauseCategoryChart data={clauseCategoryData} />
        </div>
      </div>

      {/* ── Section 2: AI Insights + Workflow (side by side) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <AiInsightsPanel insights={aiInsights} />
        </div>
        <div className="lg:col-span-1">
          <WorkflowAlertsPanel alerts={workflowAlerts} />
        </div>
      </div>

      {/* ── Section 3: Highest Risk Contracts ── */}
      <ContractsTable contracts={filteredContracts} />

      {/* ── Section 4: Financial Exposure ── */}
      <FinancialExposurePanel data={financialExposure} />
    </div>
  );
}
