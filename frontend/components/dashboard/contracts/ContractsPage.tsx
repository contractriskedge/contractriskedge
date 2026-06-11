"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, AlertCircle, RefreshCw, Upload, Download, ExternalLink, X, Check } from "lucide-react";
import { ContractKpiCards } from "./ContractKpiCards";
import { ContractsHeader } from "./ContractsHeader";
import { FilterBar } from "./FilterBar";
import { ContractsTable } from "./ContractsTable";
import { PreviewDrawer } from "./PreviewDrawer";
import { UploadFlow } from "./UploadFlow";
import { useContracts, useContractKpis, useSavedViews } from "@/services/hooks/useContracts";
import type { ContractRecord, ContractFilterState } from "./types";
import { PageHeader } from "@/components/shared/PageHeader";
import { UserPicker } from "@/components/shared/UserPicker";
import { reviewService } from "@/services/api/reviews";
import { useRouter } from "next/navigation";

const defaultFilters: ContractFilterState = {
  search: "", vendor: "", geography: "", contractType: "", businessUnit: "",
  owner: "", riskLevel: "", status: "", workflowStage: "", aiConfidence: "", expirationRange: "",
};

/** Map API KPI response to component ContractKpi type. */
function mapKpis(data: { total_contracts: number; active_reviews: number; pending_reviews: number; high_risk_count: number; expiring_soon: number; avg_risk_score: number; total_value_at_risk: number } | undefined) {
  if (!data) return [];
  return [
    { id: "renewals-due", label: "Renewals Due", value: data.expiring_soon.toString(), trend: 0, trendDirection: "neutral" as const, icon: "Clock", severity: "warning" as const, tooltip: "Contracts expiring within 90 days" },
    { id: "total-contracts", label: "Total Contracts", value: data.total_contracts.toLocaleString(), trend: 0, trendDirection: "neutral" as const, icon: "FileText", severity: "info" as const, tooltip: "Total contracts in repository" },
    { id: "value-at-risk", label: "Value at Risk", value: `$${(data.total_value_at_risk / 1_000_000).toFixed(1)}M`, trend: 0, trendDirection: "neutral" as const, icon: "DollarSign", severity: "critical" as const, tooltip: "Total financial value of high-risk contracts" },
  ];
}

export function ContractsPage() {
  const router = useRouter();
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
  const [assignTarget, setAssignTarget] = useState<string | null>(null);
  const [assignLoading, setAssignLoading] = useState(false);

  const handleAssign = useCallback(async (assigneeId: string, _assigneeName: string) => {
    if (!assignTarget) return;
    setAssignLoading(true);
    try {
      await reviewService.assign(assignTarget, { assignee_id: assigneeId });
      refetchContracts();
    } catch {
      // Silently fail — the review service handles errors
    }
    setAssignLoading(false);
    setAssignTarget(null);
  }, [assignTarget, refetchContracts]);

  const filteredContracts = useMemo(() => {
    return contractRecords.filter((c) => {
      if (search) {
        const q = search.toLowerCase();
        const matchesSearch =
          (c.name || "").toLowerCase().includes(q) ||
          (c.vendor || "").toLowerCase().includes(q) ||
          (c.id || "").toLowerCase().includes(q) ||
          (c.contractNumber || "").toLowerCase().includes(q) ||
          (c.contractType || "").toLowerCase().includes(q) ||
          (c.owner || "").toLowerCase().includes(q);
        if (!matchesSearch) return false;
      }
      if (filters.vendor && c.vendor !== filters.vendor) return false;
      if (filters.geography && c.geography !== filters.geography) return false;
      if (filters.contractType && c.contractType !== filters.contractType) return false;
      if (filters.businessUnit && c.businessUnit !== filters.businessUnit) return false;
      if (filters.owner && c.owner !== filters.owner) return false;
      if (filters.workflowStage && (c.workflowStage || "").toLowerCase() !== filters.workflowStage.toLowerCase()) return false;
      if (filters.riskLevel) {
        const score = c.riskScore || 0;
        if (filters.riskLevel === "critical" && score < 8) return false;
        else if (filters.riskLevel === "high" && (score < 6 || score >= 8)) return false;
        else if (filters.riskLevel === "medium" && (score < 4 || score >= 6)) return false;
        else if (filters.riskLevel === "low" && score >= 4) return false;
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
      {/* Page Header */}
      <div className="px-3 pt-3 pb-1">
        <PageHeader
          title="Contract Repository"
          description="System of record for contract metadata, lifecycle status, and search."
          actions={
            <>
              <button
                onClick={() => setUploadOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gold-500 text-white hover:bg-gold-600 transition-colors"
              >
                <Upload className="w-3.5 h-3.5" />
                Upload Contract
              </button>
              <button
                onClick={() => {}}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Export
              </button>
            </>
          }
        />
      </div>

      {/* Header + Search */}
      <ContractsHeader
        search={search}
        onSearchChange={(v) => { setSearch(v); setFilters((f) => ({ ...f, search: v })); }}
        savedViews={savedViews}
        activeViewId={activeViewId}
        onViewChange={handleViewChange}
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
      <div className="px-3"><FilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} allContracts={contractRecords} /></div>

      {/* Contracts Table */}
      <div className="px-3">
        <ContractsTable
          contracts={filteredContracts}
          onSelectContract={setSelectedContract}
          onAction={(contractId, action) => {
            // Bulk: comma-separated IDs
            if (typeof contractId === "string" && contractId.includes(",")) {
              const ids = contractId.split(",").filter(Boolean);
              if (ids.length === 0) return;
              switch (action) {
                case "analyze-risks":
                  ids.forEach((id) => router.push(`/reviews/ai-workspace?contractId=${id}`));
                  break;
                case "assign-reviewer":
                // Use the first selected contract's detail modal flow but for all
                setAssignTarget(ids[0]);
                break;
                case "export-pdf":
                  ids.forEach((id) => window.open(`/api/v1/export/reviews/${id}/pdf`, "_blank"));
                  break;
                case "archive":
                  if (!confirm(`Archive ${ids.length} contracts?`)) return;
                  Promise.allSettled(ids.map((id) => fetch(`/api/v1/reviews/${id}`, { method: "DELETE" }))).then(() => {
                    refetchContracts();
                  });
                  break;
              }
              return;
            }
            switch (action) {
              case "view-details":
                router.push(`/contracts/${contractId}`);
                break;
              case "analyze-risks":
                router.push(`/reviews/ai-workspace?contractId=${contractId}`);
                break;
              case "generate-redlines":
                router.push(`/reviews/${contractId}/redlines`);
                break;
              case "assign-reviewer": {
                // Open the proper assign modal at the workspace level
                router.push(`/reviews/ai-workspace?contractId=${contractId}&action=assign`);
                break;
              }
              case "add-tags":
                router.push(`/contracts/${contractId}`);
                break;
              case "request-approval":
                router.push(`/reviews/ai-workspace?contractId=${contractId}`);
                break;
              case "export-pdf":
                window.open(`/api/v1/export/reviews/${contractId}/pdf`, "_blank");
                break;
              case "archive":
                if (confirm("Archive this contract?")) {
                  fetch(`/api/v1/reviews/${contractId}`, { method: "DELETE" }).finally(() => {
                    refetchContracts();
                  });
                }
                break;
            }
          }}
        />
      </div>

      {/* Export listener — wires ContractsHeader's Export button to a CSV download */}
      <ExportListener contracts={filteredContracts} />

      {/* Preview Drawer */}
      <PreviewDrawer contract={selectedContract} onClose={() => setSelectedContract(null)} />

      {/* Upload Flow */}
      <UploadFlow isOpen={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  );
}

// ── ExportListener ──────────────────────────────────────────────────────────
//
// Listens for the `contracts:export-csv` custom event fired by the header
// Export button. Serialises the currently filtered set to CSV and triggers
// a browser download. Using a custom event keeps the header free of state.
//
function ExportListener({ contracts }: { contracts: ContractRecord[] }) {
  React.useEffect(() => {
    const handler = () => {
      const headers = [
        "Contract #", "Name", "Vendor", "Type", "Status", "Risk Score",
        "Risk Level", "Financial Value", "Currency", "Owner", "Geography",
        "Effective Date", "Expiration Date", "Renewal Date", "Workflow Stage",
      ];
      const rows = contracts.map((c) => [
        c.contractNumber || "",
        c.name || "",
        c.vendor || "",
        c.contractType || "",
        c.status || "",
        String(c.riskScore ?? 0),
        c.riskLevel || "",
        String(c.financialValue ?? 0),
        c.currency || "USD",
        c.owner || "",
        c.geography || "",
        c.effectiveDate || "",
        c.expirationDate || "",
        c.renewalDate || "",
        c.workflowStage || "",
      ]);
      const csv = [headers, ...rows]
        .map((row) => row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","))
        .join("\n");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `contracts-export-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    };
    window.addEventListener("contracts:export-csv", handler);
    return () => window.removeEventListener("contracts:export-csv", handler);
  }, [contracts]);
  return null;
}
