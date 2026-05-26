"use client";

import React, { useState, useMemo, useCallback } from "react";
import { motion } from "framer-motion";
import { ClipboardCheck, Download, RefreshCw, Search } from "lucide-react";
import { ObligationKpiCards } from "./ObligationKpiCards";
import { ObligationTable } from "./ObligationTable";
import { ObligationAiInsights } from "./AiInsights";
import { SlaPerformanceChart, SlaVendorTable, FinancialExposurePanel, ObligationTimeline } from "./SlaCenter";
import { ObligationDetailDrawer } from "./ObligationDetailDrawer";
import { ObligationFilterBar } from "./ObligationFilterBar";
import { obligationKpis, obligationRecords, obligationInsights, slaMetrics, financialExposureData, timelineEvents } from "./mockData";
import type { ObligationRecord } from "./types";

interface ObligationFilters {
  type: string; status: string; vendor: string; slaStatus: string; riskLevel: string; department: string;
}

const defaultFilters: ObligationFilters = { type: "", status: "", vendor: "", slaStatus: "", riskLevel: "", department: "" };

export function ObligationCenter() {
  const [filters, setFilters] = useState<ObligationFilters>({ ...defaultFilters });
  const [selectedObligation, setSelectedObligation] = useState<ObligationRecord | null>(null);

  const handleFilterChange = useCallback((key: keyof ObligationFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);
  const resetFilters = useCallback(() => setFilters({ ...defaultFilters }), []);

  const filteredObligations = useMemo(() => {
    return obligationRecords.filter((o) => {
      if (filters.type && o.type !== filters.type) return false;
      if (filters.status && o.status !== filters.status) return false;
      if (filters.slaStatus && o.slaStatus !== filters.slaStatus) return false;
      if (filters.riskLevel) {
        if (filters.riskLevel === "critical" && o.riskScore < 8) return false;
        else if (filters.riskLevel === "high" && (o.riskScore < 6 || o.riskScore >= 8)) return false;
        else if (filters.riskLevel === "medium" && (o.riskScore < 4 || o.riskScore >= 6)) return false;
      }
      return true;
    });
  }, [filters]);

  return (
    <div className="space-y-4 pb-24">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-700 flex items-center justify-center shadow-sm">
            <ClipboardCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-navy-900">Obligation Management Center</h1>
            <p className="text-xs text-gray-500 mt-0.5">Enterprise post-signature operational intelligence and SLA governance</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-navy-700 text-white hover:bg-navy-800 transition-colors shadow-sm">
            <Download className="w-3.5 h-3.5" /> Export Report
          </button>
        </div>
      </motion.div>

      {/* KPI Row */}
      <ObligationKpiCards metrics={obligationKpis} />

      {/* Filter Bar */}
      <ObligationFilterBar filters={filters} onChange={handleFilterChange} onReset={resetFilters} />

      {/* Section 1: AI Insights + Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <ObligationAiInsights insights={obligationInsights} />
        </div>
        <div className="lg:col-span-1">
          <ObligationTimeline events={timelineEvents} />
        </div>
      </div>

      {/* Section 2: Obligation Table */}
      <ObligationTable obligations={filteredObligations} onSelect={setSelectedObligation} />

      {/* Section 3: SLA + Financial */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SlaPerformanceChart data={slaMetrics} />
        <FinancialExposurePanel data={financialExposureData} />
      </div>
      <SlaVendorTable data={slaMetrics} />

      {/* Detail Drawer */}
      <ObligationDetailDrawer obligation={selectedObligation} onClose={() => setSelectedObligation(null)} />
    </div>
  );
}
