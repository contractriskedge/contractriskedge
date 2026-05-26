// ── Enterprise Obligation Management Types ──────────────────────────────────

export type ObligationType = "payment" | "deliverable" | "milestone" | "sla" | "renewal" | "compliance" | "reporting" | "insurance";
export type ObligationStatus = "pending" | "in_progress" | "completed" | "overdue" | "waived" | "escalated";
export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";
export type SlaStatus = "on_track" | "at_risk" | "breached" | "not_applicable";

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
export const STATUS_CONFIG: Record<ObligationStatus, { color: string; bg: string; label: string }> = {
  pending: { color: "text-yellow-700", bg: "bg-yellow-50", label: "Pending" },
  in_progress: { color: "text-blue-700", bg: "bg-blue-50", label: "In Progress" },
  completed: { color: "text-green-700", bg: "bg-green-50", label: "Completed" },
  overdue: { color: "text-red-700", bg: "bg-red-50", label: "Overdue" },
  waived: { color: "text-gray-600", bg: "bg-gray-100", label: "Waived" },
  escalated: { color: "text-purple-700", bg: "bg-purple-50", label: "Escalated" },
};
