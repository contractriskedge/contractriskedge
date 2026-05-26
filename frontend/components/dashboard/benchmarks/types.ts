// ── Enterprise Benchmark Intelligence Types ─────────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";
export type DeviationDirection = "above_market" | "below_market" | "at_market" | "far_above" | "far_below";

export interface BenchmarkKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[]; tooltip: string;
}

export interface ClauseBenchmark {
  clauseType: string;
  yourScore: number;
  marketMedian: number;
  marketP25: number;
  marketP75: number;
  deviation: number;
  deviationPercent: number;
  direction: DeviationDirection;
  percentile: number;
  sampleSize: number;
  confidence: number;
  trend: number;
  category: string;
}

export interface BenchmarkDistribution {
  clauseType: string;
  values: number[];
  yourValue: number;
  marketMedian: number;
}

export interface IndustryComparison {
  industry: string;
  yourScore: number;
  industryAvg: number;
  industryP10: number;
  industryP90: number;
  deviation: number;
  sampleSize: number;
}

export interface MarketInsight {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "warning" | "info" | "success";
  confidence: number;
  percentile: number;
  affectedClauses: string[];
  recommendation: string;
  fallbackLanguage?: string;
  category: string;
  quickActions: { label: string; action: string }[];
}

export interface VendorBenchmark {
  vendor: string;
  aggressivenessScore: number;
  deviationCount: number;
  avgDeviation: number;
  topDeviations: { clause: string; deviation: number }[];
  trend: number;
  contractsAnalyzed: number;
}

export interface NegotiationIntel {
  clauseType: string;
  leverageScore: number;
  marketPosition: string;
  recommendedPosition: string;
  fallbackPositions: string[];
  vendorFavorability: number;
  confidence: number;
}

export interface ComplianceBenchmark {
  regulation: string;
  yourCoverage: number;
  marketCoverage: number;
  gap: number;
  severity: RiskLevel;
  affectedClauses: string[];
}

export interface ClauseLibrary {
  clauseType: string;
  frequency: number;
  trend: number;
  riskScore: number;
  industryStandard: string;
  commonVariations: number;
  lastUpdated: string;
}

export interface BenchmarkFilterState {
  industry: string; geography: string; contractType: string;
  clauseCategory: string; vendorType: string; companySize: string;
  regulation: string; dateRange: string;
}

export const CLAUSE_TYPES = [
  "Indemnification", "Liability Cap", "Termination", "Confidentiality",
  "Data Privacy", "Compliance", "Payment Terms", "Force Majeure",
  "Assignment", "Governing Law", "Non-Compete", "IP Ownership",
  "Auto-Renewal", "SLA", "Insurance", "Audit Rights",
];

export const INDUSTRIES = ["Technology", "Financial Services", "Healthcare", "Manufacturing", "Retail", "Energy", "Telecom", "Pharmaceutical"];
export const GEOGRAPHIES = ["North America", "EMEA", "APAC", "LATAM", "Global"];
export const CONTRACT_TYPES = ["MSA", "SOW", "NDA", "License", "Service Agreement", "Partnership", "SaaS Agreement"];
export const REGULATIONS = ["GDPR", "CCPA", "HIPAA", "SOX", "PCI-DSS", "FCRA"];

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
