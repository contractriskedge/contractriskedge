// ── Enterprise Workflow Center Types ────────────────────────────────────────

export type WorkflowStageType =
  | "intake" | "ai_review" | "legal_review" | "procurement_review"
  | "security_review" | "finance_approval" | "executive_approval"
  | "signature" | "completed";

export type Priority = "critical" | "high" | "medium" | "low";
export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";

export interface WorkflowKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[]; tooltip: string;
}

export interface WorkflowItem {
  id: string;
  contractName: string;
  vendor: string;
  contractType: string;
  currentStage: WorkflowStageType;
  assignedTo: string;
  priority: Priority;
  slaRemaining: number; // hours
  riskLevel: RiskLevel;
  riskScore: number;
  status: "active" | "on_hold" | "escalated" | "completed";
  lastAction: string;
  lastActionBy: string;
  lastActionDate: string;
  dueDate: string;
  escalationLevel: number;
  aiRecommendation: string;
  aiConfidence: number;
  comments: WorkflowComment[];
  attachments: number;
  value: number;
  department: string;
  geography: string;
  createdAt: string;
  completedAt?: string;
}

export interface WorkflowComment {
  id: string;
  author: string;
  body: string;
  mentions: string[];
  createdAt: string;
  resolved: boolean;
}

export interface WorkflowInsight {
  id: string;
  title: string;
  description: string;
  severity: "critical" | "warning" | "info" | "success";
  confidence: number;
  impactedWorkflows: string[];
  suggestedAction: string;
  category: string;
  quickActions: { label: string; action: string }[];
}

export interface SlaMetric {
  stage: WorkflowStageType;
  targetHours: number;
  actualHours: number;
  breachCount: number;
  breachRate: number;
  trend: number;
}

export interface AutomationRule {
  id: string;
  name: string;
  description: string;
  trigger: string;
  action: string;
  enabled: boolean;
  priority: number;
  successRate: number;
  executions: number;
}

export interface TeamMember {
  id: string;
  name: string;
  role: string;
  avatar: string;
  activeWorkflows: number;
  completedToday: number;
  avgCompletionTime: number;
  online: boolean;
}

export const WORKFLOW_STAGES: { id: WorkflowStageType; label: string; color: string; bg: string; icon: string }[] = [
  { id: "intake", label: "Intake", color: "text-gray-600", bg: "bg-gray-100", icon: "Inbox" },
  { id: "ai_review", label: "AI Review", color: "text-purple-700", bg: "bg-purple-50", icon: "Brain" },
  { id: "legal_review", label: "Legal Review", color: "text-blue-700", bg: "bg-blue-50", icon: "Scale" },
  { id: "procurement_review", label: "Procurement Review", color: "text-teal-700", bg: "bg-teal-50", icon: "ShoppingCart" },
  { id: "security_review", label: "Security Review", color: "text-orange-700", bg: "bg-orange-50", icon: "Shield" },
  { id: "finance_approval", label: "Finance Approval", color: "text-green-700", bg: "bg-green-50", icon: "DollarSign" },
  { id: "executive_approval", label: "Executive Approval", color: "text-red-700", bg: "bg-red-50", icon: "UserCheck" },
  { id: "signature", label: "Signature", color: "text-indigo-700", bg: "bg-indigo-50", icon: "PenSquare" },
  { id: "completed", label: "Completed", color: "text-emerald-700", bg: "bg-emerald-50", icon: "CheckCircle" },
];

export const STAGE_ORDER: WorkflowStageType[] = [
  "intake", "ai_review", "legal_review", "procurement_review",
  "security_review", "finance_approval", "executive_approval",
  "signature", "completed",
];

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
export const PRIORITY_CONFIG = {
  critical: { color: "text-red-700", bg: "bg-red-50", label: "Critical" },
  high: { color: "text-orange-700", bg: "bg-orange-50", label: "High" },
  medium: { color: "text-yellow-700", bg: "bg-yellow-50", label: "Medium" },
  low: { color: "text-green-700", bg: "bg-green-50", label: "Low" },
};
