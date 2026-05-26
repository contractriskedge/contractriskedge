"use client";

import React, { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Download, RefreshCw, LayoutDashboard } from "lucide-react";
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
import {
  kpiMetrics,
  riskTrendData,
  monthlyExposureData,
  vendorRiskData,
  clauseCategoryData,
  departmentRiskData,
  aiInsights,
  portfolioContracts,
  financialExposure,
  workflowAlerts,
} from "./mockData";

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
  const [loading] = useState(false);
  const [filters, setFilters] = useState<Record<string, string>>({
    businessUnit: "all",
    vendor: "all",
    geography: "all",
    contractType: "all",
    riskLevel: "all",
  });
  const [lastRefreshed] = useState(new Date().toLocaleTimeString());

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  // Apply filters to contracts
  const filteredContracts = useMemo(() => {
    return portfolioContracts.filter((c) => {
      if (filters.businessUnit !== "all" && c.businessUnit !== filters.businessUnit) return false;
      if (filters.vendor !== "all" && c.vendor !== filters.vendor) return false;
      if (filters.geography !== "all" && c.geography !== filters.geography) return false;
      if (filters.contractType !== "all" && c.contractType !== filters.contractType) return false;
      if (filters.riskLevel !== "all") {
        if (filters.riskLevel === "critical" && c.riskScore < 8) return false;
        else if (filters.riskLevel === "high" && (c.riskScore < 6 || c.riskScore >= 8)) return false;
        else if (filters.riskLevel === "medium" && (c.riskScore < 4 || c.riskScore >= 6)) return false;
        else if (filters.riskLevel === "low" && c.riskScore >= 4) return false;
      }
      return true;
    });
  }, [filters]);

  if (loading) return <DashboardSkeleton />;

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
