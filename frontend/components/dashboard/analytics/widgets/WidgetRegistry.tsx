/**
 * Dashboard Widget Registry — metadata-driven widget system for AnalyticsCenter.
 *
 * Each widget defines:
 * - id: unique identifier
 * - title: display name
 * - roles: which user roles can see it
 * - defaultVisible: shown by default
 * - category: "operations" | "risk" | "ai" | "executive"
 * - component: the React component to render
 * - minWidth / minHeight: grid constraints
 *
 * Usage:
 *   import { DASHBOARD_WIDGETS, getWidgetsForRole } from "./widgets/WidgetRegistry";
 *   const widgets = getWidgetsForRole(userRole, activeLayout);
 *   widgets.forEach(w => <w.component key={w.id} />);
 */

import React from "react";

// ── Widget Definition ────────────────────────────────────────────

export interface WidgetDefinition {
  id: string;
  title: string;
  subtitle?: string;
  roles: string[];
  defaultVisible: boolean;
  category: "operations" | "risk" | "ai" | "executive";
  component?: React.ComponentType<Record<string, unknown>>;
  minWidth?: number;
  minHeight?: number;
  defaultWidth?: number; // grid columns
}

// ── Widget Layout (persisted per user) ───────────────────────────

export interface WidgetLayout {
  widgetId: string;
  visible: boolean;
  position: number;
  width: number; // grid columns (1-4 in a 4-col layout)
}

// ── Dashboard Template ───────────────────────────────────────────

export interface DashboardTemplate {
  id: string;
  name: string;
  description: string;
  roles: string[];
  layout: WidgetLayout[];
}

// ── Widget Registry ──────────────────────────────────────────────

// Lazy imports — all widgets live in ./widgets.tsx
const widgetLoaders: Record<string, () => Promise<{ default: React.ComponentType<any> }>> = {
  system_health: () => import("./widgets").then(m => ({ default: m.SystemHealthWidget })),
  upload_trend: () => import("./widgets").then(m => ({ default: m.UploadTrendWidget })),
  risk_distribution: () => import("./widgets").then(m => ({ default: m.RiskDistributionWidget })),
  findings_by_clause: () => import("./widgets").then(m => ({ default: m.FindingsByClauseWidget })),
  ai_cost_trend: () => import("./widgets").then(m => ({ default: m.AiCostTrendWidget })),
  review_aging: () => import("./widgets").then(m => ({ default: m.ReviewAgingWidget })),
  error_breakdown: () => import("./widgets").then(m => ({ default: m.ErrorBreakdownWidget })),
  stuck_workflows: () => import("./widgets").then(m => ({ default: m.StuckWorkflowsWidget })),
  executive_summary: () => import("./widgets").then(m => ({ default: m.ExecutiveSummaryWidget })),
  kpi_row: () => import("./widgets").then(m => ({ default: m.KpiRowWidget })),
};

// ── Widget Metadata Registry ─────────────────────────────────────

export const DASHBOARD_WIDGETS: WidgetDefinition[] = [
  {
    id: "kpi_row",
    title: "Key Performance Indicators",
    subtitle: "Core operational metrics at a glance",
    roles: ["admin", "analyst", "viewer"],
    defaultVisible: true,
    category: "operations",
    defaultWidth: 4,
  },
  {
    id: "system_health",
    title: "System Health",
    subtitle: "Active uploads, AI runs, pending reviews, errors",
    roles: ["admin", "analyst"],
    defaultVisible: true,
    category: "operations",
    defaultWidth: 1,
  },
  {
    id: "stuck_workflows",
    title: "Stuck Workflows",
    subtitle: "Uploads, AI runs, or reviews stuck beyond threshold",
    roles: ["admin", "analyst"],
    defaultVisible: true,
    category: "operations",
    defaultWidth: 1,
  },
  {
    id: "error_breakdown",
    title: "Error Breakdown",
    subtitle: "Failures by type, domain, and retryability",
    roles: ["admin", "analyst"],
    defaultVisible: true,
    category: "operations",
    defaultWidth: 1,
  },
  {
    id: "upload_trend",
    title: "Upload Volume (30d)",
    subtitle: "Uploads per day",
    roles: ["admin", "analyst", "viewer"],
    defaultVisible: true,
    category: "operations",
    defaultWidth: 2,
  },
  {
    id: "risk_distribution",
    title: "Risk Distribution",
    subtitle: "Portfolio risk score breakdown",
    roles: ["admin", "analyst", "viewer"],
    defaultVisible: true,
    category: "risk",
    defaultWidth: 2,
  },
  {
    id: "findings_by_clause",
    title: "Findings by Clause Type",
    subtitle: "AI-identified risk areas across portfolio",
    roles: ["admin", "analyst", "viewer"],
    defaultVisible: true,
    category: "risk",
    defaultWidth: 2,
  },
  {
    id: "ai_cost_trend",
    title: "AI Cost & Token Usage (30d)",
    subtitle: "Daily AI processing economics",
    roles: ["admin"],
    defaultVisible: true,
    category: "ai",
    defaultWidth: 2,
  },
  {
    id: "review_aging",
    title: "Review Aging",
    subtitle: "Pending reviews by age bucket",
    roles: ["admin", "analyst"],
    defaultVisible: true,
    category: "operations",
    defaultWidth: 2,
  },
  {
    id: "executive_summary",
    title: "Executive Summary",
    subtitle: "Portfolio risk, critical contracts, SLA metrics",
    roles: ["admin", "analyst", "viewer"],
    defaultVisible: true,
    category: "executive",
    defaultWidth: 4,
  },
];

// ── Dashboard Templates ──────────────────────────────────────────

export const DASHBOARD_TEMPLATES: DashboardTemplate[] = [
  {
    id: "executive",
    name: "Executive View",
    description: "Portfolio risk, critical metrics, and executive intelligence",
    roles: ["admin", "analyst", "viewer"],
    layout: [
      { widgetId: "kpi_row", visible: true, position: 0, width: 4 },
      { widgetId: "executive_summary", visible: true, position: 1, width: 4 },
      { widgetId: "risk_distribution", visible: true, position: 2, width: 2 },
      { widgetId: "findings_by_clause", visible: true, position: 3, width: 2 },
      { widgetId: "upload_trend", visible: true, position: 4, width: 2 },
      { widgetId: "review_aging", visible: true, position: 5, width: 2 },
    ],
  },
  {
    id: "legal_ops",
    name: "Legal Ops View",
    description: "Review workload, SLA breaches, stuck workflows, aging",
    roles: ["admin", "analyst"],
    layout: [
      { widgetId: "kpi_row", visible: true, position: 0, width: 4 },
      { widgetId: "system_health", visible: true, position: 1, width: 1 },
      { widgetId: "stuck_workflows", visible: true, position: 2, width: 1 },
      { widgetId: "error_breakdown", visible: true, position: 3, width: 1 },
      { widgetId: "review_aging", visible: true, position: 4, width: 1 },
      { widgetId: "findings_by_clause", visible: true, position: 5, width: 2 },
      { widgetId: "risk_distribution", visible: true, position: 6, width: 2 },
    ],
  },
  {
    id: "ai_ops",
    name: "AI Operations View",
    description: "AI performance, cost, latency, failure analysis",
    roles: ["admin"],
    layout: [
      { widgetId: "kpi_row", visible: true, position: 0, width: 4 },
      { widgetId: "system_health", visible: true, position: 1, width: 2 },
      { widgetId: "error_breakdown", visible: true, position: 2, width: 2 },
      { widgetId: "ai_cost_trend", visible: true, position: 3, width: 2 },
      { widgetId: "upload_trend", visible: true, position: 4, width: 2 },
    ],
  },
  {
    id: "risk",
    name: "Risk & Compliance View",
    description: "Portfolio risk, clause gaps, vendor exposure",
    roles: ["admin", "analyst", "viewer"],
    layout: [
      { widgetId: "kpi_row", visible: true, position: 0, width: 4 },
      { widgetId: "risk_distribution", visible: true, position: 1, width: 2 },
      { widgetId: "findings_by_clause", visible: true, position: 2, width: 2 },
      { widgetId: "executive_summary", visible: true, position: 3, width: 4 },
    ],
  },
];

// ── Helpers ──────────────────────────────────────────────────────

export function getWidgetsForRole(role: string): WidgetDefinition[] {
  return DASHBOARD_WIDGETS.filter((w) => w.roles.includes(role));
}

export function getDefaultLayout(role: string): WidgetLayout[] {
  return getWidgetsForRole(role)
    .filter((w) => w.defaultVisible)
    .map((w, i) => ({
      widgetId: w.id,
      visible: true,
      position: i,
      width: w.defaultWidth || 2,
    }));
}

export function getTemplateForRole(role: string): DashboardTemplate | null {
  // Return the first template matching the user's role
  for (const t of DASHBOARD_TEMPLATES) {
    if (t.roles.includes(role)) return t;
  }
  return null;
}

export function getWidgetDefinition(id: string): WidgetDefinition | undefined {
  return DASHBOARD_WIDGETS.find((w) => w.id === id);
}

/**
 * Load a widget component by ID (lazy import).
 * Returns null if the widget has no loader registered.
 */
export async function loadWidgetComponent(id: string): Promise<React.ComponentType<Record<string, unknown>> | null> {
  const loader = widgetLoaders[id];
  if (!loader) return null;
  try {
    const mod = await loader();
    return mod.default;
  } catch {
    return null;
  }
}
