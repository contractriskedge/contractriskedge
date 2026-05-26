// ── Enterprise Clause Library & Playbooks Types ────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";
export type ClauseStatus = "approved" | "pending_review" | "deprecated" | "draft";
export type PlaybookType = "negotiation" | "compliance" | "jurisdiction" | "vendor_type";

export interface ClauseKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[]; tooltip: string;
}

export interface ClauseRecord {
  id: string;
  name: string;
  category: string;
  text: string;
  riskScore: number;
  riskLevel: RiskLevel;
  jurisdiction: string;
  contractTypes: string[];
  benchmarkPercentile: number;
  usageFrequency: number;
  approvalStatus: ClauseStatus;
  lastUpdated: string;
  owner: string;
  aiConfidence: number;
  negotiationStrength: number;
  fallbackVariants: ClauseVariant[];
  versions: number;
  isFavorite: boolean;
  tags: string[];
  aiExplanation: string;
  negotiationGuidance: string;
  governanceNotes: string;
}

export interface ClauseVariant {
  id: string;
  label: string;
  text: string;
  riskScore: number;
  negotiationStrength: number;
  usageRate: number;
  isPreferred: boolean;
}

export interface Playbook {
  id: string;
  name: string;
  description: string;
  type: PlaybookType;
  jurisdiction: string;
  contractTypes: string[];
  clauses: string[];
  rules: PlaybookRule[];
  successRate: number;
  usageCount: number;
  lastUpdated: string;
  owner: string;
}

export interface PlaybookRule {
  id: string;
  condition: string;
  action: string;
  priority: number;
  enabled: boolean;
}

export interface ClauseCategory {
  id: string;
  name: string;
  count: number;
  icon: string;
}

export interface BenchmarkData {
  clauseType: string;
  yourScore: number;
  marketMedian: number;
  marketP25: number;
  marketP75: number;
  percentile: number;
  sampleSize: number;
}

export const CLAUSE_CATEGORIES: ClauseCategory[] = [
  { id: "indemnification", name: "Indemnification", count: 24, icon: "Shield" },
  { id: "liability", name: "Liability & Caps", count: 18, icon: "AlertTriangle" },
  { id: "termination", name: "Termination", count: 22, icon: "XCircle" },
  { id: "confidentiality", name: "Confidentiality", count: 16, icon: "Lock" },
  { id: "data_privacy", name: "Data Privacy", count: 20, icon: "Shield" },
  { id: "compliance", name: "Compliance", count: 15, icon: "CheckCircle" },
  { id: "payment", name: "Payment Terms", count: 14, icon: "DollarSign" },
  { id: "ip", name: "Intellectual Property", count: 12, icon: "Lightbulb" },
  { id: "force_majeure", name: "Force Majeure", count: 10, icon: "Cloud" },
  { id: "insurance", name: "Insurance", count: 8, icon: "Shield" },
  { id: "sla", name: "SLA", count: 11, icon: "Activity" },
  { id: "governing_law", name: "Governing Law", count: 9, icon: "Scale" },
];

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
