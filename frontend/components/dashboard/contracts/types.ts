// ── Enterprise Contract Repository Types ────────────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info" | "warning";
export type ContractStatus = "active" | "expiring_soon" | "expired" | "draft" | "pending_review" | "pending_signature" | "under_review";
export type WorkflowStage = "draft" | "review" | "approval" | "negotiation" | "executed" | "renewal" | "archived";
export type AiFlag = "critical" | "review_needed" | "benchmark_deviation" | "auto_renewal_risk" | "compliance_issue" | "missing_clause";

export interface ContractKpi {
  id: string;
  label: string;
  value: string;
  trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string;
  color: string;
  sparklineData: number[];
  tooltip: string;
}

export interface ContractRecord {
  id: string;
  name: string;
  vendor: string;
  contractType: string;
  businessUnit: string;
  riskScore: number;
  riskLevel: RiskLevel;
  financialValue: number;
  currency: string;
  status: ContractStatus;
  renewalDate: string;
  aiConfidence: number;
  owner: string;
  workflowStage: WorkflowStage;
  lastModified: string;
  tags: string[];
  geography: string;
  counterparty: string;
  description: string;
  aiSummary: string;
  clauseCount: number;
  missingClauses: string[];
  aiFlags: AiFlag[];
  obligationsDue: number;
  hasRedlines: boolean;
  hasDpa: boolean;
  autoRenew: boolean;
  totalPages: number;
  createdAt: string;
}

export interface ContractFilterState {
  search: string;
  vendor: string;
  geography: string;
  contractType: string;
  businessUnit: string;
  owner: string;
  riskLevel: string;
  status: string;
  workflowStage: string;
  aiConfidence: string;
  expirationRange: string;
}

export interface SavedView {
  id: string;
  name: string;
  filters: ContractFilterState;
  isDefault: boolean;
}

export interface UploadState {
  isDragging: boolean;
  isUploading: boolean;
  progress: number;
  fileName: string;
  status: "idle" | "uploading" | "processing" | "complete" | "error";
  error?: string;
  detectedDuplicates: string[];
  extractedMetadata: Record<string, string>;
}

export interface ActivityEvent {
  id: string;
  type: "upload" | "review" | "approval" | "comment" | "redline" | "analysis" | "signature";
  user: string;
  action: string;
  timestamp: string;
  details?: string;
}

export interface ClauseSummary {
  type: string;
  risk: RiskLevel;
  text: string;
  suggestion?: string;
}

export interface Obligation {
  id: string;
  description: string;
  dueDate: string;
  owner: string;
  status: "pending" | "completed" | "overdue";
}

export interface RelatedContract {
  id: string;
  name: string;
  relationship: string;
  riskScore: number;
}

export const AI_FLAG_CONFIG: Record<AiFlag, { label: string; color: string; bg: string; icon: string }> = {
  critical: { label: "Critical", color: "text-red-700", bg: "bg-red-50", icon: "AlertTriangle" },
  review_needed: { label: "Review Needed", color: "text-orange-700", bg: "bg-orange-50", icon: "AlertCircle" },
  benchmark_deviation: { label: "Benchmark Deviation", color: "text-purple-700", bg: "bg-purple-50", icon: "BarChart3" },
  auto_renewal_risk: { label: "Auto-Renewal Risk", color: "text-yellow-700", bg: "bg-yellow-50", icon: "RefreshCw" },
  compliance_issue: { label: "Compliance Issue", color: "text-blue-700", bg: "bg-blue-50", icon: "Shield" },
  missing_clause: { label: "Missing Clause", color: "text-pink-700", bg: "bg-pink-50", icon: "FileX" },
};

export const WORKFLOW_STAGES: Record<WorkflowStage, { label: string; color: string; bg: string }> = {
  draft: { label: "Draft", color: "text-gray-600", bg: "bg-gray-100" },
  review: { label: "Under Review", color: "text-blue-700", bg: "bg-blue-50" },
  approval: { label: "Pending Approval", color: "text-yellow-700", bg: "bg-yellow-50" },
  negotiation: { label: "Negotiation", color: "text-purple-700", bg: "bg-purple-50" },
  executed: { label: "Executed", color: "text-green-700", bg: "bg-green-50" },
  renewal: { label: "Renewal", color: "text-orange-700", bg: "bg-orange-50" },
  archived: { label: "Archived", color: "text-gray-500", bg: "bg-gray-100" },
};

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
