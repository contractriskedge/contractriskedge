// ── Enterprise Procurement Intelligence Types ──────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";
export type ComplianceStatus = "compliant" | "at_risk" | "non_compliant" | "pending_review";
export type SupplierStatus = "active" | "onboarding" | "under_review" | "blocked" | "inactive";

export interface ProcurementKpi {
  id: string;
  label: string;
  value: string;
  trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string;
  color: string;
  severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[];
  tooltip: string;
}

export interface SupplierRecord {
  id: string;
  name: string;
  riskScore: number;
  riskLevel: RiskLevel;
  totalSpend: number;
  currency: string;
  activeContracts: number;
  renewalExposure: number;
  slaPerformance: number;
  complianceStatus: ComplianceStatus;
  topRiskArea: string;
  procurementOwner: string;
  country: string;
  financialStability: "strong" | "stable" | "weak" | "distressed";
  lastAssessment: string;
  aiConfidence: number;
  category: string;
  businessUnit: string;
  contractValue: number;
  avgContractTerm: number;
  insuranceCompliant: boolean;
  hasSla: boolean;
  onboardingDate: string;
  dunsNumber: string;
  taxId: string;
  aiFlags: string[];
  missingClauses: string[];
  negotiationHistory: number;
  relationshipAge: number;
}

export interface SupplierKpi {
  id: string;
  label: string;
  value: string;
  trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string;
  color: string;
  severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[];
  tooltip: string;
}

export interface SpendTrend {
  month: string;
  total: number;
  cloud: number;
  software: number;
  consulting: number;
  hardware: number;
  services: number;
}

export interface VendorCategory {
  category: string;
  suppliers: number;
  totalSpend: number;
  avgRisk: number;
  highRiskCount: number;
}

export interface GeoRisk {
  country: string;
  suppliers: number;
  avgRisk: number;
  totalExposure: number;
  code: string;
}

export interface RiskTrend {
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface ProcurementInsight {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "warning" | "info" | "success";
  confidence: number;
  impactedSuppliers: string[];
  suggestedAction: string;
  category: "liability" | "savings" | "compliance" | "risk" | "renewal";
  quickActions: { label: string; action: string }[];
  savings?: number;
}

export interface WorkflowItem {
  id: string;
  type: "approval" | "sourcing" | "onboarding" | "review" | "escalation" | "renewal";
  title: string;
  description: string;
  severity: "critical" | "warning" | "info";
  assignee?: string;
  dueDate?: string;
  status: "pending" | "in_progress" | "completed";
  slaRemaining?: number;
}

export interface SavingsOpportunity {
  id: string;
  title: string;
  potentialSavings: number;
  category: string;
  confidence: number;
  effort: "low" | "medium" | "high";
  suppliers: string[];
  description: string;
}

export interface SupplierDetail {
  overview: {
    aiSummary: string;
    relationshipAge: number;
    totalContracts: number;
    totalSpend: number;
    avgRiskScore: number;
    financialHealth: string;
    geopoliticalRisk: string;
  };
  contracts: { id: string; name: string; value: number; status: string; expiry: string }[];
  riskAnalysis: { category: string; score: number; level: RiskLevel; details: string }[];
  spendAnalytics: { year: number; q1: number; q2: number; q3: number; q4: number }[];
  slaPerformance: { metric: string; target: number; actual: number; status: string }[];
  compliance: { requirement: string; status: ComplianceStatus; notes: string }[];
  relationships: { supplier: string; type: string; strength: number }[];
  auditHistory: { date: string; event: string; user: string }[];
}

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
export const COMPLIANCE_CONFIG: Record<ComplianceStatus, { label: string; color: string; bg: string }> = {
  compliant: { label: "Compliant", color: "text-green-700", bg: "bg-green-50" },
  at_risk: { label: "At Risk", color: "text-orange-700", bg: "bg-orange-50" },
  non_compliant: { label: "Non-Compliant", color: "text-red-700", bg: "bg-red-50" },
  pending_review: { label: "Pending Review", color: "text-blue-700", bg: "bg-blue-50" },
};
