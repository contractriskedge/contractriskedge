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
  { id: "indemnification", name: "Indemnification", count: 0, icon: "Shield" },
  { id: "limitation_of_liability", name: "Liability & Caps", count: 0, icon: "AlertTriangle" },
  { id: "termination", name: "Termination", count: 0, icon: "XCircle" },
  { id: "confidentiality", name: "Confidentiality", count: 0, icon: "Lock" },
  { id: "data_privacy", name: "Data Privacy", count: 0, icon: "Shield" },
  { id: "compliance", name: "Compliance", count: 0, icon: "CheckCircle" },
  { id: "payment_terms", name: "Payment Terms", count: 0, icon: "DollarSign" },
  { id: "intellectual_property", name: "Intellectual Property", count: 0, icon: "Lightbulb" },
  { id: "force_majeure", name: "Force Majeure", count: 0, icon: "Cloud" },
  { id: "insurance", name: "Insurance", count: 0, icon: "Shield" },
  { id: "sla", name: "SLA", count: 0, icon: "Activity" },
  { id: "governing_law", name: "Governing Law", count: 0, icon: "Scale" },
  { id: "warranty", name: "Warranty", count: 0, icon: "CheckCircle" },
  { id: "dispute_resolution", name: "Dispute Resolution", count: 0, icon: "Scale" },
  { id: "audit_rights", name: "Audit Rights", count: 0, icon: "FileText" },
  { id: "assignment", name: "Assignment", count: 0, icon: "FileText" },
  { id: "non_compete", name: "Non-Compete", count: 0, icon: "Ban" },
  { id: "non_solicit", name: "Non-Solicit", count: 0, icon: "Ban" },
  { id: "escrow", name: "Escrow", count: 0, icon: "Shield" },
  { id: "general", name: "General", count: 0, icon: "FileText" },
];

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
