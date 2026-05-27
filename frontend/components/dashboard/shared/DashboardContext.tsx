/**
 * DashboardContext — Shared state for all Sprint 10 dashboards.
 *
 * Manages:
 * - Global date range (24h / 7d / 30d / 90d)
 * - Auto-refresh interval
 * - Active filters (tenant, department, region)
 * - Cross-dashboard navigation history
 * - Dashboard-level loading/error states
 * - Role-based dashboard access
 */

"use client";

import React, { createContext, useContext, useState, useCallback, useMemo } from "react";
import { useAuth } from "@/components/auth/AuthProvider";

export type DateRange = "24h" | "7d" | "30d" | "90d";
export type RefreshInterval = 0 | 15 | 30 | 60;

export type DashboardId =
  | "executive-command-center"
  | "reviewer-operations"
  | "governance-dashboard"
  | "ai-operations-dashboard"
  | "workflow-intelligence-dashboard";

export interface DashboardFilter {
  tenant?: string;
  department?: string;
  region?: string;
}

export interface DashboardNavigationEntry {
  from: DashboardId;
  to: DashboardId;
  timestamp: number;
}

// ── Role → Dashboard permission map ─────────────────────────────────
export const DASHBOARD_PERMISSIONS: Record<string, DashboardId[]> = {
  executive: ["executive-command-center"],
  reviewer: ["reviewer-operations", "workflow-intelligence-dashboard"],
  "compliance-officer": ["governance-dashboard"],
  "ai-engineer": ["ai-operations-dashboard"],
  operations: ["reviewer-operations", "workflow-intelligence-dashboard"],
  finance: ["executive-command-center"],
  admin: [
    "executive-command-center",
    "reviewer-operations",
    "governance-dashboard",
    "ai-operations-dashboard",
    "workflow-intelligence-dashboard",
  ],
};

export const DASHBOARD_LABELS: Record<DashboardId, string> = {
  "executive-command-center": "Command Center",
  "reviewer-operations": "Reviewer Operations",
  "governance-dashboard": "Governance",
  "ai-operations-dashboard": "AI Operations",
  "workflow-intelligence-dashboard": "Workflow Intelligence",
};

export const DASHBOARD_ICONS: Record<DashboardId, string> = {
  "executive-command-center": "layout-dashboard",
  "reviewer-operations": "clipboard-list",
  "governance-dashboard": "shield-check",
  "ai-operations-dashboard": "cpu",
  "workflow-intelligence-dashboard": "bar-chart-3",
};

// ── Context type ────────────────────────────────────────────────────

interface DashboardContextType {
  dateRange: DateRange;
  setDateRange: (range: DateRange) => void;
  refreshInterval: RefreshInterval;
  setRefreshInterval: (interval: RefreshInterval) => void;
  filters: DashboardFilter;
  setFilters: (filters: DashboardFilter) => void;
  navigationHistory: DashboardNavigationEntry[];
  navigateBetweenDashboards: (to: DashboardId) => void;
  accessibleDashboards: DashboardId[];
  hasDashboardAccess: (dashboardId: DashboardId) => boolean;
  dashboardLoading: Record<DashboardId, boolean>;
  setDashboardLoading: (id: DashboardId, loading: boolean) => void;
  dashboardError: Record<DashboardId, string | null>;
  setDashboardError: (id: DashboardId, error: string | null) => void;
}

const DashboardContext = createContext<DashboardContextType | null>(null);

export function useDashboardContext(): DashboardContextType {
  const ctx = useContext(DashboardContext);
  if (!ctx) {
    throw new Error("useDashboardContext must be used within a DashboardProvider");
  }
  return ctx;
}

// ── Provider ────────────────────────────────────────────────────────

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [dateRange, setDateRange] = useState<DateRange>("7d");
  const [refreshInterval, setRefreshInterval] = useState<RefreshInterval>(30);
  const [filters, setFilters] = useState<DashboardFilter>({});
  const [navigationHistory, setNavigationHistory] = useState<DashboardNavigationEntry[]>([]);
  const [dashboardLoading, setDashboardLoadingState] = useState<Record<DashboardId, boolean>>({} as Record<DashboardId, boolean>);
  const [dashboardError, setDashboardErrorState] = useState<Record<DashboardId, string | null>>({} as Record<DashboardId, string | null>);

  // ── Role-based access ─────────────────────────────────────────
  const role = user?.role ?? "viewer";
  const accessibleDashboards = useMemo(
    () => DASHBOARD_PERMISSIONS[role] ?? [],
    [role]
  );

  const hasDashboardAccess = useCallback(
    (dashboardId: DashboardId) => accessibleDashboards.includes(dashboardId),
    [accessibleDashboards]
  );

  const navigateBetweenDashboards = useCallback(
    (to: DashboardId) => {
      setNavigationHistory((prev) => [
        ...prev.slice(-49), // keep last 50 entries
        { from: "executive-command-center" as DashboardId, to, timestamp: Date.now() },
      ]);
    },
    []
  );

  const setDashboardLoading = useCallback((id: DashboardId, loading: boolean) => {
    setDashboardLoadingState((prev) => ({ ...prev, [id]: loading }));
  }, []);

  const setDashboardError = useCallback((id: DashboardId, error: string | null) => {
    setDashboardErrorState((prev) => ({ ...prev, [id]: error }));
  }, []);

  const value = useMemo(
    () => ({
      dateRange,
      setDateRange,
      refreshInterval,
      setRefreshInterval,
      filters,
      setFilters,
      navigationHistory,
      navigateBetweenDashboards,
      accessibleDashboards,
      hasDashboardAccess,
      dashboardLoading,
      setDashboardLoading,
      dashboardError,
      setDashboardError,
    }),
    [
      dateRange, refreshInterval, filters, navigationHistory,
      accessibleDashboards, hasDashboardAccess,
      dashboardLoading, dashboardError,
    ]
  );

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}
