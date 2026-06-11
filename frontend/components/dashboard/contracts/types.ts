// ── Enterprise Contract Repository Types ────────────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info" | "warning";
export type ContractStatus = "active" | "expiring_soon" | "expired" | "draft" | "pending_review" | "pending_signature" | "under_review" | "awaiting_legal" | "ai_review_failed" | "compliance_needed" | "renewal_at_risk";
export type WorkflowStage = "draft" | "review" | "approval" | "negotiation" | "executed" | "renewal" | "archived";
export type AiFlag = "critical" | "review_needed" | "benchmark_deviation" | "auto_renewal_risk" | "compliance_issue" | "missing_clause" | "ai_review_failed";

export interface ContractKpi {
  id: string;
  label: string;
  value: string;
  subtitle?: string;
  trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string;
  severity: "critical" | "warning" | "success" | "info";
  tooltip: string;
}

export interface ContractRecord {
  id: string;
  name: string;
  originalFilename: string;
  contractNumber: string;
  contractType: string;
  vendor: string;
  businessUnit: string;
  geography: string;
  department: string;
  description: string;
  tags: string[];
  riskScore: number;
  riskLevel: RiskLevel;
  financialValue: number;
  currency: string;
  status: ContractStatus;
  /** Raw review workflow status from the backend (e.g. executed, approved, archived). */
  reviewStatus?: string;
  effectiveDate: string;
  expirationDate: string;
  renewalDate: string;
  lastReviewDate: string;
  autoRenew: boolean;
  topRisk: string;
  aiConfidence: number;
  aiFindingsCount: number;
  openFindings: number;
  clauseCount: number;
  unresolvedRisks: number;
  owner: string;
  ownerId: string;
  workflowStage: WorkflowStage;
  lastActivity: string;
  lastModified: string;
  createdAt: string;
  missingClauses: string[];
  aiFlags: AiFlag[];
  aiSummary: string;
  obligationsDue: number;
  hasRedlines: boolean;
  hasDpa: boolean;
  totalPages: number;
  slaCompliant: boolean;
  slaStatus: string;
  slaDeadline: string;
  /** health bucket derived from risk/expiry/SLA — drives the row health dot */
  health: "healthy" | "needs_review" | "high_risk" | "expired" | "expiring_soon";
  /** legacy convenience alias */
  renewalRisk: "low" | "medium" | "high";
  /** legacy convenience alias */
  counterparty: string;
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

export const AI_FLAG_CONFIG: Record<AiFlag, { label: string; color: string; bg: string; darkColor: string; darkBg: string; icon: string }> = {
  critical: { label: "Critical", color: "text-red-700", bg: "bg-red-50", darkColor: "dark:text-red-400", darkBg: "dark:bg-red-900/20", icon: "AlertTriangle" },
  review_needed: { label: "Review Needed", color: "text-orange-700", bg: "bg-orange-50", darkColor: "dark:text-orange-400", darkBg: "dark:bg-orange-900/20", icon: "AlertCircle" },
  benchmark_deviation: { label: "Benchmark Deviation", color: "text-purple-700", bg: "bg-purple-50", darkColor: "dark:text-purple-400", darkBg: "dark:bg-purple-900/20", icon: "BarChart3" },
  auto_renewal_risk: { label: "Auto-Renewal Risk", color: "text-yellow-700", bg: "bg-yellow-50", darkColor: "dark:text-yellow-400", darkBg: "dark:bg-yellow-900/20", icon: "RefreshCw" },
  compliance_issue: { label: "Compliance Issue", color: "text-blue-700", bg: "bg-blue-50", darkColor: "dark:text-blue-400", darkBg: "dark:bg-blue-900/20", icon: "Shield" },
  missing_clause: { label: "Missing Clause", color: "text-pink-700", bg: "bg-pink-50", darkColor: "dark:text-pink-400", darkBg: "dark:bg-pink-900/20", icon: "FileX" },
  ai_review_failed: { label: "AI Review Failed", color: "text-red-700", bg: "bg-red-50", darkColor: "dark:text-red-400", darkBg: "dark:bg-red-900/20", icon: "AlertTriangle" },
};

export const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; darkColor: string; darkBg: string }> = {
  active: { label: "Active", color: "text-green-700", bg: "bg-green-100", darkColor: "dark:text-green-400", darkBg: "dark:bg-green-900/20" },
  expiring_soon: { label: "Expiring Soon", color: "text-yellow-700", bg: "bg-yellow-100", darkColor: "dark:text-yellow-400", darkBg: "dark:bg-yellow-900/20" },
  under_review: { label: "Under Review", color: "text-blue-700", bg: "bg-blue-100", darkColor: "dark:text-blue-400", darkBg: "dark:bg-blue-900/20" },
  pending_signature: { label: "Pending Signature", color: "text-purple-700", bg: "bg-purple-100", darkColor: "dark:text-purple-400", darkBg: "dark:bg-purple-900/20" },
  expired: { label: "Expired", color: "text-red-700", bg: "bg-red-100", darkColor: "dark:text-red-400", darkBg: "dark:bg-red-900/20" },
  draft: { label: "Draft", color: "text-gray-600", bg: "bg-gray-100", darkColor: "dark:text-gray-400", darkBg: "dark:bg-gray-900/20" },
  awaiting_legal: { label: "Awaiting Legal", color: "text-indigo-700", bg: "bg-indigo-100", darkColor: "dark:text-indigo-400", darkBg: "dark:bg-indigo-900/20" },
  ai_review_failed: { label: "AI Review Failed", color: "text-red-700", bg: "bg-red-100", darkColor: "dark:text-red-400", darkBg: "dark:bg-red-900/20" },
  compliance_needed: { label: "Compliance Review", color: "text-cyan-700", bg: "bg-cyan-100", darkColor: "dark:text-cyan-400", darkBg: "dark:bg-cyan-900/20" },
  renewal_at_risk: { label: "Renewal At Risk", color: "text-orange-700", bg: "bg-orange-100", darkColor: "dark:text-orange-400", darkBg: "dark:bg-orange-900/20" },
};

export const WORKFLOW_STAGES: Record<WorkflowStage, { label: string; color: string; bg: string; darkColor: string; darkBg: string }> = {
  draft: { label: "Draft", color: "text-gray-600", bg: "bg-gray-100", darkColor: "dark:text-gray-400", darkBg: "dark:bg-gray-900/20" },
  review: { label: "Under Review", color: "text-blue-700", bg: "bg-blue-50", darkColor: "dark:text-blue-400", darkBg: "dark:bg-blue-900/20" },
  approval: { label: "Pending Approval", color: "text-yellow-700", bg: "bg-yellow-50", darkColor: "dark:text-yellow-400", darkBg: "dark:bg-yellow-900/20" },
  negotiation: { label: "Negotiation", color: "text-purple-700", bg: "bg-purple-50", darkColor: "dark:text-purple-400", darkBg: "dark:bg-purple-900/20" },
  executed: { label: "Executed", color: "text-green-700", bg: "bg-green-50", darkColor: "dark:text-green-400", darkBg: "dark:bg-green-900/20" },
  renewal: { label: "Renewal", color: "text-orange-700", bg: "bg-orange-50", darkColor: "dark:text-orange-400", darkBg: "dark:bg-orange-900/20" },
  archived: { label: "Archived", color: "text-gray-500", bg: "bg-gray-100", darkColor: "dark:text-gray-400", darkBg: "dark:bg-gray-900/20" },
};

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
export const RISK_DARK_BG = { critical: "dark:bg-red-900/20", high: "dark:bg-orange-900/20", medium: "dark:bg-yellow-900/20", low: "dark:bg-green-900/20", info: "dark:bg-blue-900/20" };
export const RISK_DARK_TEXT = { critical: "dark:text-red-400", high: "dark:text-orange-400", medium: "dark:text-yellow-400", low: "dark:text-green-400", info: "dark:text-blue-400" };
