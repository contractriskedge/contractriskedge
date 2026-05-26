// ── Enterprise CFO Risk & Financial Exposure Dashboard Types ────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info" | "warning" | "success";
export type ExposureCategory = "liability" | "renewal" | "vendor" | "operational" | "compliance" | "revenue";
export type ForecastPeriod = "quarterly" | "monthly" | "annual";

// ── CFO KPI ──────────────────────────────────────────────────────────────

export interface CfoKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[]; tooltip: string;
}

// ── Financial Exposure ───────────────────────────────────────────────────

export interface FinancialExposure {
  id: string;
  category: ExposureCategory;
  label: string;
  currentExposure: number;
  projectedExposure: number;
  riskLevel: RiskLevel;
  contractCount: number;
  vendorCount: number;
  trend: number;
  details: ExposureDetail[];
}

export interface ExposureDetail {
  id: string;
  contractTitle: string;
  vendor: string;
  amount: number;
  riskLevel: RiskLevel;
  clause: string;
  dueDate: string;
  status: string;
}

// ── Renewal Forecast ─────────────────────────────────────────────────────

export interface RenewalForecast {
  id: string;
  contractTitle: string;
  vendor: string;
  currentValue: number;
  projectedValue: number;
  renewalDate: string;
  riskLevel: RiskLevel;
  probability: number;
  savingsOpportunity: number;
  autoRenewal: boolean;
  noticeDeadline: string;
  status: string;
}

// ── Vendor Financial Risk ────────────────────────────────────────────────

export interface VendorFinancialRisk {
  id: string;
  vendorName: string;
  totalSpend: number;
  contractCount: number;
  riskScore: number;
  riskLevel: RiskLevel;
  concentration: number;
  liabilityExposure: number;
  slaPenalties: number;
  paymentTerms: string;
  dso: number;
  trend: number;
}

// ── SLA Financial Impact ─────────────────────────────────────────────────

export interface SlaFinancialImpact {
  id: string;
  contractTitle: string;
  vendor: string;
  penaltyType: string;
  penaltyAmount: number;
  incidentCount: number;
  totalImpact: number;
  period: string;
  riskLevel: RiskLevel;
}

// ── Revenue Leakage ──────────────────────────────────────────────────────

export interface RevenueLeakage {
  id: string;
  category: string;
  description: string;
  estimatedLoss: number;
  probability: number;
  riskLevel: RiskLevel;
  affectedContracts: number;
  recoveryPotential: number;
  recommendation: string;
}

// ── Procurement Savings ──────────────────────────────────────────────────

export interface ProcurementSaving {
  id: string;
  category: string;
  description: string;
  currentSpend: number;
  projectedSpend: number;
  savingsAmount: number;
  savingsPercent: number;
  confidence: number;
  timeline: string;
  vendorCount: number;
}

// ── AI Financial Insight ─────────────────────────────────────────────────

export interface AiFinancialInsight {
  id: string;
  type: "exposure" | "forecast" | "anomaly" | "savings" | "risk" | "recommendation";
  title: string;
  description: string;
  severity: RiskLevel;
  confidence: number;
  financialImpact: number;
  impactedContracts: number;
  impactedVendors: number;
  recommendedAction: string;
}

// ── Financial Analytics ──────────────────────────────────────────────────

export interface FinancialAnalytics {
  totalPortfolioValue: number;
  totalExposure: number;
  uncappedLiability: number;
  upcomingRenewals: number;
  vendorConcentration: number;
  revenueLeakage: number;
  slaPenalties: number;
  savingsOpportunities: number;
  exposureByCategory: { category: string; amount: number; }[];
  exposureTrend: { date: string; amount: number; }[];
  renewalForecast: { period: string; amount: number; probability: number; }[];
  vendorConcentrationData: { vendor: string; spend: number; }[];
  businessUnitExposure: { unit: string; exposure: number; contracts: number; }[];
  regionalExposure: { region: string; exposure: number; }[];
  savingsTrend: { date: string; identified: number; realized: number; }[];
  forecastAccuracy: { period: string; predicted: number; actual: number; }[];
}

// ── Financial Detail ─────────────────────────────────────────────────────

export interface FinancialDetail {
  overview: {
    title: string;
    category: string;
    currentExposure: number;
    projectedExposure: number;
    riskLevel: RiskLevel;
    contractCount: number;
    vendorCount: number;
  };
  exposureAnalysis: { item: string; amount: number; risk: RiskLevel; }[];
  forecasting: { period: string; projected: number; confidence: number; }[];
  vendorImpact: { vendor: string; exposure: number; contracts: number; }[];
  obligations: { title: string; amount: number; dueDate: string; status: string; }[];
  aiInsights: AiFinancialInsight[];
  trends: { date: string; value: number; }[];
  auditHistory: { action: string; user: string; timestamp: string; }[];
}
