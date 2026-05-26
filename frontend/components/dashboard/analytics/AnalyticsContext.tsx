/**
 * AnalyticsContext — shared state for cross-widget filtering and coordination.
 *
 * Provides:
 * - timeRange: "24h" | "7d" | "30d" | "90d"
 * - riskFilter: string (severity level)
 * - clauseType: string (clause type filter)
 * - selectedContractId: string | null
 * - Filter change handlers
 *
 * All widgets subscribe to this context for coordinated filtering.
 */

"use client";

import React, { createContext, useContext, useState, useCallback, useMemo } from "react";

// ── Types ────────────────────────────────────────────────────────

export type TimeRange = "24h" | "7d" | "30d" | "90d";

export interface AnalyticsFilters {
  timeRange: TimeRange;
  riskFilter: string;
  clauseType: string;
  selectedContractId: string | null;
}

export interface AnalyticsContextValue {
  filters: AnalyticsFilters;
  setTimeRange: (range: TimeRange) => void;
  setRiskFilter: (risk: string) => void;
  setClauseType: (clause: string) => void;
  setSelectedContractId: (id: string | null) => void;
  resetFilters: () => void;
  /** Convert current filters to API query params */
  toQueryParams: () => Record<string, string>;
}

const defaultFilters: AnalyticsFilters = {
  timeRange: "30d",
  riskFilter: "",
  clauseType: "",
  selectedContractId: null,
};

// ── Context ──────────────────────────────────────────────────────

const AnalyticsContext = createContext<AnalyticsContextValue | null>(null);

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const [filters, setFilters] = useState<AnalyticsFilters>(defaultFilters);

  const setTimeRange = useCallback((timeRange: TimeRange) => {
    setFilters((prev) => ({ ...prev, timeRange }));
  }, []);

  const setRiskFilter = useCallback((riskFilter: string) => {
    setFilters((prev) => ({ ...prev, riskFilter }));
  }, []);

  const setClauseType = useCallback((clauseType: string) => {
    setFilters((prev) => ({ ...prev, clauseType }));
  }, []);

  const setSelectedContractId = useCallback((selectedContractId: string | null) => {
    setFilters((prev) => ({ ...prev, selectedContractId }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(defaultFilters);
  }, []);

  const toQueryParams = useCallback((): Record<string, string> => {
    const params: Record<string, string> = {};
    if (filters.timeRange !== "30d") {
      const daysMap: Record<TimeRange, string> = { "24h": "1", "7d": "7", "30d": "30", "90d": "90" };
      params.days = daysMap[filters.timeRange];
    }
    if (filters.riskFilter) params.severity = filters.riskFilter;
    if (filters.clauseType) params.clause_type = filters.clauseType;
    return params;
  }, [filters]);

  const value = useMemo<AnalyticsContextValue>(() => ({
    filters,
    setTimeRange,
    setRiskFilter,
    setClauseType,
    setSelectedContractId,
    resetFilters,
    toQueryParams,
  }), [filters, setTimeRange, setRiskFilter, setClauseType, setSelectedContractId, resetFilters, toQueryParams]);

  return (
    <AnalyticsContext.Provider value={value}>
      {children}
    </AnalyticsContext.Provider>
  );
}

export function useAnalyticsContext(): AnalyticsContextValue {
  const ctx = useContext(AnalyticsContext);
  if (!ctx) {
    throw new Error("useAnalyticsContext must be used within an AnalyticsProvider");
  }
  return ctx;
}

// ── Time Range Selector Component ───────────────────────────────

export function TimeRangeSelector() {
  const { filters, setTimeRange } = useAnalyticsContext();
  const options: { value: TimeRange; label: string }[] = [
    { value: "24h", label: "24H" },
    { value: "7d", label: "7D" },
    { value: "30d", label: "30D" },
    { value: "90d", label: "90D" },
  ];
  return (
    <div className="flex items-center gap-0.5 bg-gray-100 rounded-lg p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => setTimeRange(opt.value)}
          className={`px-2.5 py-1 text-[10px] font-medium rounded-md transition-colors ${
            filters.timeRange === opt.value
              ? "bg-white text-navy-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
