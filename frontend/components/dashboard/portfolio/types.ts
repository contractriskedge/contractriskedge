// ── Enterprise Portfolio Dashboard Types ────────────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";
export type ContractStatus = "active" | "expiring_soon" | "expired" | "draft" | "pending_review";
export type AlertSeverity = "critical" | "warning" | "info" | "success";

export interface KpiMetric {
  id: string;
  label: string;
  value: string;
  unit?: string;
  trend: number; // percentage change
  trendDirection: "up" | "down" | "neutral";
  icon: string;
  color: string;
  severity: AlertSeverity;
  sparklineData: number[];
  tooltip: string;
  drillDownHref?: string;
}

export interface RiskTrendPoint {
  date: string;
  high: number;
  medium: number;
  low: number;
  critical: number;
  total: number;
}

export interface MonthlyExposure {
  month: string;
  exposure: number;
  liability: number;
  insured: number;
}

export interface VendorRisk {
  vendor: string;
  contracts: number;
  avgRiskScore: number;
  totalExposure: number;
  trend: number;
}

export interface ClauseCategoryRisk {
  category: string;
  highRiskCount: number;
  mediumRiskCount: number;
  lowRiskCount: number;
  totalCount: number;
  avgSeverity: number;
}

export interface DepartmentRisk {
  department: string;
  contracts: number;
  avgRisk: number;
  highRiskCount: number;
  exposure: number;
}

export interface AiInsight {
  id: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  confidence: number; // 0-100
  recommendedAction: string;
  category: "liability" | "expiry" | "compliance" | "financial" | "vendor";
  quickActions: { label: string; action: string }[];
  createdAt: string;
}

export interface PortfolioContract {
  id: string;
  name: string;
  vendor: string;
  riskScore: number;
  riskLevel: RiskLevel;
  financialExposure: number;
  currency: string;
  expiryDate: string;
  topRisk: string;
  aiConfidence: number;
  owner: string;
  status: ContractStatus;
  department: string;
  businessUnit: string;
  geography: string;
  contractType: string;
  clauseCategories: string[];
  autoRenew: boolean;
  slaCompliant: boolean;
  obligationsDue: number;
}

export interface FinancialExposure {
  totalExposure: number;
  insuredAmount: number;
  gapAmount: number;
  currency: string;
  breakdown: { category: string; amount: number; percentage: number }[];
  vendorConcentration: { vendor: string; exposure: number; percentage: number }[];
  insuranceGaps: { area: string; gap: number; risk: RiskLevel }[];
}

export interface WorkflowAlert {
  id: string;
  type: "approval" | "escalation" | "sla_breach" | "task" | "review" | "notification";
  title: string;
  description: string;
  severity: AlertSeverity;
  assignee?: string;
  dueDate?: string;
  createdAt: string;
  status: "pending" | "in_progress" | "completed";
}

export interface DashboardFilters {
  businessUnit: string;
  vendor: string;
  geography: string;
  contractType: string;
  riskLevel: string;
  dateRange: string;
}

export const SEVERITY_COLORS: Record<AlertSeverity, string> = {
  critical: "text-red-600 bg-red-50 border-red-200",
  warning: "text-orange-600 bg-orange-50 border-orange-200",
  info: "text-blue-600 bg-blue-50 border-blue-200",
  success: "text-green-600 bg-green-50 border-green-200",
};

export const RISK_BG_COLORS: Record<RiskLevel, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-green-500",
  info: "bg-blue-500",
};

export const RISK_TEXT_COLORS: Record<RiskLevel, string> = {
  critical: "text-red-700",
  high: "text-orange-700",
  medium: "text-yellow-700",
  low: "text-green-700",
  info: "text-blue-700",
};

export const RISK_BG_LIGHT: Record<RiskLevel, string> = {
  critical: "bg-red-50",
  high: "bg-orange-50",
  medium: "bg-yellow-50",
  low: "bg-green-50",
  info: "bg-blue-50",
};
