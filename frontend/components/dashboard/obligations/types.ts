// ── Enterprise Obligation Management Types ──────────────────────────────────

export type ObligationType = "payment" | "deliverable" | "milestone" | "sla" | "renewal" | "compliance" | "reporting" | "insurance";
export type ObligationStatus = "draft" | "pending" | "in_progress" | "active" | "completed" | "overdue" | "cancelled" | "archived" | "waived" | "escalated";
export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";
export type SlaStatus = "on_track" | "at_risk" | "breached" | "not_applicable";

export interface AuditLogEntry {
  id: string;
  obligation_id: string;
  action: string;
  actor: string | null;
  changes: Record<string, unknown> | null;
  comment: string | null;
  created_at: string;
}

export interface ComplianceAction {
  status: string;
  dueDate: string;
  owner: string;
  daysRemaining: number;
  actionRequired: string;
}

export interface ObligationKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[]; tooltip: string;
}

export interface ObligationRecord {
  id: string;
  name: string;
  contractId: string;
  contractName: string;
  vendor: string;
  type: ObligationType;
  owner: string;
  assignee: string;
  dueDate: string;
  completedDate?: string;
  status: ObligationStatus;
  riskLevel: RiskLevel;
  riskScore: number;
  slaStatus: SlaStatus;
  slaRemaining: number;
  financialImpact: number;
  sourceContract?: string;
  sourceClause?: string;
  extractedByAi?: boolean;
  contractOwner?: string;
  daysRemaining?: number;
  actionRequired?: string;
  currency: string;
  escalationLevel: number;
  aiRiskPrediction: number;
  aiConfidence: number;
  description: string;
  clauseReference: string;
  attachments: number;
  reminders: number;
  notes: string;
  department: string;
  businessUnit: string;
  geography: string;
  createdAt: string;
  lastModified: string;
  isFavorite?: boolean;
}

export interface ObligationInsight {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "warning" | "info" | "success";
  confidence: number;
  impactedObligations: string[];
  suggestedAction: string;
  category: string;
  quickActions: { label: string; action: string }[];
}

export interface SlaMetric {
  vendor: string;
  contractType: string;
  slaTarget: string;
  performance: number;
  trend: number;
  breachCount: number;
  status: SlaStatus;
}

export interface FinancialExposure {
  category: string;
  totalExposure: number;
  overdueAmount: number;
  atRiskAmount: number;
  recoveredAmount: number;
  trend: number;
}

export interface TimelineEvent {
  id: string;
  date: string;
  type: ObligationType;
  title: string;
  description: string;
  status: ObligationStatus;
  vendor: string;
  contractId: string;
}

// ── API Response Types (snake_case, matching backend) ────────────

export interface ObligationKpiResponse {
  total_obligations: number;
  active_count: number;
  overdue_count: number;
  escalated_count: number;
  completed_count: number;
  breached_count: number;
  avg_risk_score: number;
  total_exposure: number;
  at_risk_amount: number;
  pending_review: number;
  upcoming_due: number;
  compliance_rate: number;
}

export interface SlaBreachResponse {
  id: string;
  vendor: string;
  contract_type: string | null;
  performance: number;
  target: string;
  breached_at: string;
  status: string;
}

export interface VendorRiskResponse {
  vendor: string;
  score: number;
  risk_level: string;
  breach_count: number;
  contract_count: number;
  trend: number;
  predicted_risk: number;
}

export interface SlaPredictionResponse {
  vendor: string;
  current_performance: number;
  predicted_performance: number;
  breach_probability: number;
  risk_level: string;
  recommendation: string;
}

export interface RiskAnalysisResponse {
  obligation_id: string;
  risk_score: number;
  risk_level: string;
  breach_probability: number;
  escalation_recommended: boolean;
  recommended_action: string;
  confidence: number;
  analysis: string;
}

export interface AnomalyResponse {
  id: string;
  obligation_id: string;
  anomaly_type: string;
  severity: string;
  description: string;
  detected_at: string;
  score: number;
}

export interface FinancialExposureSummaryResponse {
  total_exposure: number;
  overdue_amount: number;
  at_risk_amount: number;
  recovered_amount: number;
  by_category: FinancialExposure[];
  trend: number;
}

export interface ValueAtRiskResponse {
  total_var: number;
  probability: number;
  confidence_level: number;
  by_category: { category: string; var: number; probability: number }[];
}

export const OBLIGATION_TYPES: { id: ObligationType; label: string; icon: string }[] = [
  { id: "payment", label: "Payment", icon: "DollarSign" },
  { id: "deliverable", label: "Deliverable", icon: "FileText" },
  { id: "milestone", label: "Milestone", icon: "Flag" },
  { id: "sla", label: "SLA", icon: "Activity" },
  { id: "renewal", label: "Renewal", icon: "RefreshCw" },
  { id: "compliance", label: "Compliance", icon: "Shield" },
  { id: "reporting", label: "Reporting", icon: "BarChart3" },
  { id: "insurance", label: "Insurance", icon: "Shield" },
];

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
export const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  draft: { color: "text-gray-500", bg: "bg-gray-50", label: "Draft" },
  pending: { color: "text-yellow-700", bg: "bg-yellow-50", label: "Pending" },
  in_progress: { color: "text-blue-700", bg: "bg-blue-50", label: "In Progress" },
  active: { color: "text-blue-700", bg: "bg-blue-50", label: "Active" },
  completed: { color: "text-green-700", bg: "bg-green-50", label: "Completed" },
  overdue: { color: "text-red-700", bg: "bg-red-50", label: "Overdue" },
  cancelled: { color: "text-gray-600", bg: "bg-gray-100", label: "Cancelled" },
  archived: { color: "text-gray-500", bg: "bg-gray-50", label: "Archived" },
  waived: { color: "text-gray-600", bg: "bg-gray-100", label: "Waived" },
  escalated: { color: "text-purple-700", bg: "bg-purple-50", label: "Escalated" },
  open: { color: "text-blue-700", bg: "bg-blue-50", label: "Open" },
  closed: { color: "text-gray-600", bg: "bg-gray-100", label: "Closed" },
};
