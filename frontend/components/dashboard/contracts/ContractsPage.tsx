"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { ContractKpiCards } from "./ContractKpiCards";
import { ContractsHeader } from "./ContractsHeader";
import { FilterBar } from "./FilterBar";
import { ContractsTable } from "./ContractsTable";
import { PreviewDrawer } from "./PreviewDrawer";
import { UploadFlow } from "./UploadFlow";
import { useContracts, useContractKpis, useSavedViews } from "@/services/hooks/useContracts";
import type { ContractRecord, ContractFilterState } from "./types";

const defaultFilters: ContractFilterState = {
  search: "", vendor: "", geography: "", contractType: "", businessUnit: "",
  owner: "", riskLevel: "", status: "", workflowStage: "", aiConfidence: "", expirationRange: "",
};

/** Map API KPI response to component ContractKpi type. */
function mapKpis(data: { total_contracts: number; active_reviews: number; pending_reviews: number; high_risk_count: number; expiring_soon: number; avg_risk_score: number; total_value_at_risk: number } | undefined) {
  if (!data) return [];
  return [
    { id: "needs-review", label: "Needs Review", value: data.pending_reviews.toString(), subtitle: `${data.active_reviews} active`, trend: 0, trendDirection: "neutral" as const, icon: "Search", severity: "warning" as const, tooltip: "Contracts requiring legal review" },
    { id: "renewals-due", label: "Renewals Due", value: data.expiring_soon.toString(), trend: 0, trendDirection: "neutral" as const, icon: "Clock", severity: "warning" as const, tooltip: "Contracts expiring within 90 days" },
    { id: "high-risk", label: "High Risk", value: data.high_risk_count.toString(), trend: 0, trendDirection: "neutral" as const, icon: "AlertTriangle", severity: "critical" as const, tooltip: "Contracts with critical or high risk scores" },
    { id: "unresolved-findings", label: "Unresolved Findings", value: "0", trend: 0, trendDirection: "neutral" as const, icon: "Brain", severity: "info" as const, tooltip: "Unresolved AI findings across contracts" },
    { id: "total-contracts", label: "Total Contracts", value: data.total_contracts.toLocaleString(), trend: 0, trendDirection: "neutral" as const, icon: "FileText", severity: "info" as const, tooltip: "Total contracts in repository" },
    { id: "value-at-risk", label: "Value at Risk", value: `$${(data.total_value_at_risk / 1_000_000).toFixed(1)}M`, trend: 0, trendDirection: "neutral" as const, icon: "DollarSign", severity: "critical" as const, tooltip: "Total financial value of high-risk contracts" },
  ];
}

export function ContractsPage() {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<ContractFilterState>({ ...defaultFilters });
  const [activeViewId, setActiveViewId] = useState("view-1");
  const [selectedContract, setSelectedContract] = useState<ContractRecord | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);

  // Real API hooks replacing mockData
  const { data: contractsData, isLoading: contractsLoading, error: contractsError, refetch: refetchContracts } = useContracts({
    search: search || undefined,
  });
  const { data: kpisData, isLoading: kpisLoading } = useContractKpis();
  const { data: savedViewsData } = useSavedViews();

  const contractRecords: ContractRecord[] = contractsData?.data ?? [];
  const contractKpis = mapKpis(kpisData);
  const savedViews = savedViewsData ?? [];

  const handleFilterChange = useCallback((key: keyof ContractFilterState, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({ ...defaultFilters });
    setSearch("");
  }, []);

  const handleViewChange = useCallback((viewId: string) => {
    const view = savedViews.find((v: any) => v.id === viewId);
    if (view) {
      setActiveViewId(viewId);
      setFilters({ ...view.filters });
      setSearch(view.filters.search);
    }
  }, [savedViews]);

  // Apply filters + search (client-side for responsive UX)
  const filteredContracts = useMemo(() => {
    return contractRecords.filter((c) => {
      if (search) {
        const q = search.toLowerCase();
        const matchesSearch =
          (c.name || "").toLowerCase().includes(q) ||
          (c.vendor || "").toLowerCase().includes(q) ||
          (c.id || "").toLowerCase().includes(q);
        if (!matchesSearch) return false;
      }
      if (filters.vendor && c.vendor !== filters.vendor) return false;
      if (filters.riskLevel) {
        if (filters.riskLevel === "critical" && (c.riskScore || 0) < 8) return false;
        else if (filters.riskLevel === "high" && ((c.riskScore || 0) < 6 || (c.riskScore || 0) >= 8)) return false;
        else if (filters.riskLevel === "medium" && ((c.riskScore || 0) < 4 || (c.riskScore || 0) >= 6)) return false;
        else if (filters.riskLevel === "low" && (c.riskScore || 0) >= 4) return false;
      }
      if (filters.status && c.status !== filters.status) return false;
      return true;
    });
  }, [search, filters, contractRecords]);

  // Loading state
  if (contractsLoading && contractRecords.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-navy-900">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading contracts...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (contractsError && contractRecords.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-navy-900">
        <div className="text-center max-w-md">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">Failed to load contracts</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">{(contractsError as Error)?.message || "An unexpected error occurred"}</p>
          <button onClick={() => refetchContracts()} className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 pb-24 bg-gray-50 dark:bg-navy-900 min-h-screen">
      {/* Header + Search */}
      <ContractsHeader
        search={search}
        onSearchChange={(v) => { setSearch(v); setFilters((f) => ({ ...f, search: v })); }}
        savedViews={savedViews}
        activeViewId={activeViewId}
        onViewChange={handleViewChange}
        onUploadClick={() => setUploadOpen(true)}
        onBulkUpload={() => setUploadOpen(true)}
        resultCount={filteredContracts.length}
      />

      {/* KPI Row */}
      {kpisLoading ? (
        <div className="grid grid-cols-6 gap-1.5 px-3">
          {[1,2,3,4,5,6].map(i => (
            <div key={i} className="bg-white dark:bg-navy-800 rounded-lg border border-gray-200 dark:border-navy-700 p-3 animate-pulse">
              <div className="h-4 w-12 bg-gray-200 dark:bg-navy-700 rounded mb-2" />
              <div className="h-5 w-16 bg-gray-200 dark:bg-navy-700 rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="px-3"><ContractKpiCards metrics={contractKpis} /></div>
      )}

      {/* Filter Bar */}
      <div className="px-3"><FilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} /></div>

      {/* Contracts Table */}
      <div className="px-3"><ContractsTable contracts={filteredContracts} onSelectContract={setSelectedContract} /></div>

      {/* Preview Drawer */}
      <PreviewDrawer contract={selectedContract} onClose={() => setSelectedContract(null)} />

      {/* Upload Flow */}
      <UploadFlow isOpen={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  );
}
