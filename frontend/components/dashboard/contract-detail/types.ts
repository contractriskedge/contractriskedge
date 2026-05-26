// ── Enterprise Contract Detail Workspace Types ─────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";
export type ClauseStatus = "acceptable" | "needs_review" | "needs_negotiation" | "unacceptable";
export type ReviewStatus = "not_reviewed" | "in_review" | "reviewed" | "approved" | "rejected";
export type AnnotationType = "risk" | "obligation" | "comment" | "redline" | "ai_insight" | "compliance";

export interface ContractDocument {
  id: string;
  name: string;
  vendor: string;
  contractType: string;
  status: string;
  riskScore: number;
  riskLevel: RiskLevel;
  pages: number;
  clauses: ClauseData[];
  parties: string[];
  effectiveDate: string;
  expiryDate: string;
  governingLaw: string;
  jurisdiction: string;
  value: number;
  currency: string;
  owner: string;
  department: string;
  businessUnit: string;
  aiSummary: string;
  version: number;
  lastModified: string;
  created: string;
}

export interface ClauseData {
  id: string;
  section: string;
  title: string;
  text: string;
  category: string;
  riskScore: number;
  riskLevel: RiskLevel;
  status: ClauseStatus;
  aiExplanation: string;
  benchmarkPercentile: number;
  confidence: number;
  fallbackLanguage?: string;
  annotations: Annotation[];
  comments: ClauseComment[];
  isRedlined: boolean;
  redlinedText?: string;
  obligations: Obligation[];
}

export interface Annotation {
  id: string;
  type: AnnotationType;
  text: string;
  startOffset: number;
  endOffset: number;
  severity?: RiskLevel;
  createdBy: string;
  createdAt: string;
  resolved: boolean;
}

export interface ClauseComment {
  id: string;
  author: string;
  body: string;
  mentions: string[];
  createdAt: string;
  resolved: boolean;
  isResolving: boolean;
}

export interface Obligation {
  id: string;
  description: string;
  type: string;
  dueDate: string;
  owner: string;
  status: "pending" | "completed" | "overdue" | "waived";
  clauseId: string;
}

export interface VersionRecord {
  id: string;
  version: number;
  date: string;
  author: string;
  summary: string;
  changes: number;
  isCurrent: boolean;
}

export interface ActivityEvent {
  id: string;
  type: "comment" | "approval" | "edit" | "ai_action" | "workflow" | "review" | "version";
  user: string;
  action: string;
  details?: string;
  timestamp: string;
}

export interface NegotiationIssue {
  id: string;
  clauseId: string;
  clauseTitle: string;
  issue: string;
  yourPosition: string;
  vendorPosition: string;
  recommendedPosition: string;
  status: "open" | "discussing" | "resolved" | "conceded";
  priority: "high" | "medium" | "low";
  updatedAt: string;
}

export interface WorkflowState {
  currentStage: string;
  stages: { id: string; label: string; status: "completed" | "current" | "pending"; assignee?: string }[];
  slaRemaining: number;
  escalationLevel: number;
  reviewers: { name: string; role: string; status: string }[];
}

export const RISK_BG = { critical: "bg-red-500", high: "bg-orange-500", medium: "bg-yellow-500", low: "bg-green-500", info: "bg-blue-500" };
export const RISK_TEXT = { critical: "text-red-700", high: "text-orange-700", medium: "text-yellow-700", low: "text-green-700", info: "text-blue-700" };
export const RISK_BG_LIGHT = { critical: "bg-red-50", high: "bg-orange-50", medium: "bg-yellow-50", low: "bg-green-50", info: "bg-blue-50" };
