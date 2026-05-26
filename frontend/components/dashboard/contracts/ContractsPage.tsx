"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { ContractKpiCards } from "./ContractKpiCards";
import { ContractsHeader } from "./ContractsHeader";
import { FilterBar } from "./FilterBar";
import { ContractsTable } from "./ContractsTable";
import { PreviewDrawer } from "./PreviewDrawer";
import { UploadFlow } from "./UploadFlow";
import { contractRecords, contractKpis, savedViews } from "./mockData";
import type { ContractRecord, ContractFilterState } from "./types";

const defaultFilters: ContractFilterState = {
  search: "", vendor: "", geography: "", contractType: "", businessUnit: "",
  owner: "", riskLevel: "", status: "", workflowStage: "", aiConfidence: "", expirationRange: "",
};

export function ContractsPage() {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<ContractFilterState>({ ...defaultFilters });
  const [activeViewId, setActiveViewId] = useState("view-1");
  const [selectedContract, setSelectedContract] = useState<ContractRecord | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);

  const handleFilterChange = useCallback((key: keyof ContractFilterState, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({ ...defaultFilters });
    setSearch("");
  }, []);

  const handleViewChange = useCallback((viewId: string) => {
    const view = savedViews.find((v) => v.id === viewId);
    if (view) {
      setActiveViewId(viewId);
      setFilters({ ...view.filters });
      setSearch(view.filters.search);
    }
  }, []);

  // Apply filters + search
  const filteredContracts = useMemo(() => {
    return contractRecords.filter((c) => {
      // Search
      if (search) {
        const q = search.toLowerCase();
        const matchesSearch =
          c.name.toLowerCase().includes(q) ||
          c.vendor.toLowerCase().includes(q) ||
          c.id.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q) ||
          c.aiSummary.toLowerCase().includes(q) ||
          c.tags.some((t) => t.toLowerCase().includes(q)) ||
          c.missingClauses.some((m) => m.toLowerCase().includes(q));
        if (!matchesSearch) return false;
      }
      if (filters.vendor && c.vendor !== filters.vendor) return false;
      if (filters.geography && c.geography !== filters.geography) return false;
      if (filters.contractType && c.contractType !== filters.contractType) return false;
      if (filters.businessUnit && c.businessUnit !== filters.businessUnit) return false;
      if (filters.owner && c.owner !== filters.owner) return false;
      if (filters.riskLevel) {
        if (filters.riskLevel === "critical" && c.riskScore < 8) return false;
        else if (filters.riskLevel === "high" && (c.riskScore < 6 || c.riskScore >= 8)) return false;
        else if (filters.riskLevel === "medium" && (c.riskScore < 4 || c.riskScore >= 6)) return false;
        else if (filters.riskLevel === "low" && c.riskScore >= 4) return false;
      }
      if (filters.status && c.status !== filters.status) return false;
      if (filters.workflowStage && c.workflowStage !== filters.workflowStage) return false;
      return true;
    });
  }, [search, filters]);

  return (
    <div className="space-y-4 pb-24">
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
      <ContractKpiCards metrics={contractKpis} />

      {/* Filter Bar */}
      <FilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} />

      {/* Contracts Table */}
      <ContractsTable contracts={filteredContracts} onSelectContract={setSelectedContract} />

      {/* Preview Drawer */}
      <PreviewDrawer contract={selectedContract} onClose={() => setSelectedContract(null)} />

      {/* Upload Flow */}
      <UploadFlow isOpen={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  );
}
