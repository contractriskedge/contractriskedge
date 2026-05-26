// ── Enterprise Analytics Center Types ───────────────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";

export interface AnalyticsKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[]; tooltip: string;
}

export interface ExecutiveInsight {
  id: string; title: string; description: string; severity: "critical" | "warning" | "info" | "success";
  confidence: number; businessImpact: string; affectedEntities: string[];
  recommendedAction: string; category: string; quickActions: { label: string; action: string }[];
}

export interface RiskTrend {
  month: string; critical: number; high: number; medium: number; low: number; totalExposure: number;
}

export interface DepartmentAnalytics {
  department: string; contracts: number; avgRisk: number; highRiskCount: number; exposure: number;
  cycleTime: number; complianceScore: number; slaScore: number;
}

export interface VendorAnalytics {
  vendor: string; totalSpend: number; contracts: number; avgRisk: number; slaScore: number;
  savings: number; complianceScore: number; trend: number;
}

export interface ComplianceAnalytics {
  standard: string; score: number; marketAvg: number; gap: number; status: string; trend: number;
}

export interface ForecastPoint {
  period: string; actual: number; forecast: number; upperBound: number; lowerBound: number;
}

export interface ReportTemplate {
  id: string; name: string; description: string; category: string;
  charts: string[]; sections: string[]; lastGenerated: string; format: string;
}

export interface LegalOpsMetric {
  metric: string; value: string; trend: number; trendDir: "up" | "down"; benchmark: string;
}

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
