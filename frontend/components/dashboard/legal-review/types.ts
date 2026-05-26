// ── Enterprise Legal Review Types ───────────────────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";

export type SuggestionStatus = "pending" | "accepted" | "rejected" | "escalated";

export type ChangeType = "modify" | "remove" | "add" | "review";

export type DiffViewMode = "side-by-side" | "stacked" | "inline-redline";

export type FilterKey = "risk-level" | "status" | "clause-type";

export interface FilterOption {
  key: FilterKey;
  label: string;
  value: string;
}

export interface Comment {
  id: string;
  author: string;
  authorAvatar?: string;
  body: string;
  mentions: string[];
  createdAt: string; // ISO string
  resolved: boolean;
}

export interface PlaybookPosition {
  standardPosition: string;
  fallbackPositions: string[];
  clauseType: string;
  source?: string;
}

export interface ClauseSuggestion {
  suggestionId: string;
  contractId: string;
  contractName: string;
  clauseType: string;
  originalText: string;
  proposedText: string;
  changeType: ChangeType;
  rationale: string;
  confidence: number; // 0–1
  riskLevel: RiskLevel;
  severityScore: number; // 1–10
  status: SuggestionStatus;
  createdAt: string;
  playbook?: PlaybookPosition;
  comments: Comment[];
  section?: string;
  pageNumber?: number;
}

export const RISK_LEVEL_CONFIG: Record<RiskLevel, { color: string; bg: string; border: string; label: string }> = {
  critical: { color: "text-red-700", bg: "bg-red-50", border: "border-red-200", label: "Critical" },
  high:     { color: "text-orange-700", bg: "bg-orange-50", border: "border-orange-200", label: "High" },
  medium:   { color: "text-yellow-700", bg: "bg-yellow-50", border: "border-yellow-200", label: "Medium" },
  low:      { color: "text-green-700", bg: "bg-green-50", border: "border-green-200", label: "Low" },
  info:     { color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-200", label: "Info" },
};

export const STATUS_CONFIG: Record<SuggestionStatus, { color: string; bg: string; label: string }> = {
  pending:   { color: "text-yellow-800", bg: "bg-yellow-100", label: "Pending" },
  accepted:  { color: "text-green-800", bg: "bg-green-100", label: "Accepted" },
  rejected:  { color: "text-red-800", bg: "bg-red-100", label: "Rejected" },
  escalated: { color: "text-purple-800", bg: "bg-purple-100", label: "Escalated" },
};

export const CLAUSE_TYPE_OPTIONS = [
  { value: "all", label: "All Types" },
  { value: "indemnification", label: "Indemnification" },
  { value: "liability_limitation", label: "Liability Limitation" },
  { value: "termination", label: "Termination" },
  { value: "confidentiality", label: "Confidentiality" },
  { value: "data_privacy", label: "Data Privacy" },
  { value: "compliance", label: "Compliance" },
  { value: "payment_terms", label: "Payment Terms" },
  { value: "force_majeure", label: "Force Majeure" },
  { value: "assignment", label: "Assignment" },
  { value: "governing_law", label: "Governing Law" },
  { value: "non_compete", label: "Non-Compete" },
  { value: "intellectual_property", label: "Intellectual Property" },
];

export type ReviewPriority = "urgent" | "high" | "medium" | "low";
export type SLAStatus = "on-track" | "at-risk" | "breach";
export type EscalationStatus = "normal" | "pending" | "escalated" | "resolved";
export type WorkflowStage = "triage" | "legal_review" | "negotiation" | "approval" | "execution";
export type VendorTier = "strategic" | "preferred" | "standard";

export interface ReviewQueueItem {
  id: string;
  contractName: string;
  vendor: string;
  riskScore: number;
  priority: ReviewPriority;
  assignedReviewer: string;
  slaRemaining: string;
  clauseIssues: number;
  workflowStage: WorkflowStage;
  aiConfidence: number;
  escalationStatus: EscalationStatus;
  contractType: string;
  businessUnit: string;
  lastUpdated: string;
  notes: string;
}

export interface AIFinding {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low";
  description: string;
  recommendation: string;
  benchmarkPercentile: number;
  confidence: number;
  issueType: string;
}

export type DrawerTabId =
  | "overview"
  | "clause-analysis"
  | "benchmark"
  | "guidance"
  | "workflow"
  | "recommendations"
  | "playbooks"
  | "audit";

export interface KpiMetric {
  key: string;
  label: string;
  value: string;
  trend: number;
  trendLabel: string;
  severity: "critical" | "high" | "medium" | "low" | "normal";
  sparkline: number[];
  icon: import("react").ComponentType<import("react").SVGProps<SVGSVGElement>>;
}

export interface QueueFilter {
  reviewer: string;
  riskLevel: string;
  contractType: string;
  slaStatus: SLAStatus | "all";
  escalationStatus: EscalationStatus | "all";
  workflowStage: WorkflowStage | "all";
  vendor: string;
  businessUnit: string;
}

export const RISK_LEVEL_OPTIONS = [
  { value: "all", label: "All Risk Levels" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

export const STATUS_OPTIONS = [
  { value: "all", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
  { value: "escalated", label: "Escalated" },
];

// ── Risk Flag Detail (from 8-field explainability API) ─────────────────────

export interface LinkedEvidence {
  clause_reference: string;
  excerpt: string;
  page_number?: number;
  section?: string;
  relevance_score: number;
}

export interface JurisdictionalConsideration {
  jurisdiction: string;
  rule_reference: string;
  risk_modifier: number;
  explanation: string;
}

export interface SeverityInfo {
  severity_score?: number;
}

export interface RiskFlagDetail {
  clause_text: string;
  risk_category: string;
  why_flagged?: string;
  potential_business_impact?: string;
  market_benchmark_comparison?: string;
  confidence_score?: number;
  confidence_label?: string;
  suggested_remediation?: string;
  linked_evidence?: LinkedEvidence[];
  jurisdictional_considerations?: JurisdictionalConsideration[];
  severity?: SeverityInfo;
  riskLevel?: RiskLevel;
}
