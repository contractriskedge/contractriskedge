// ── Enterprise Negotiation & Redline Center Types ─────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";

export type NegotiationStage = "drafting" | "review" | "negotiating" | "approved" | "executed" | "escalated";
export type RedlineType = "addition" | "deletion" | "modification" | "comment" | "suggestion";
export type IssueSeverity = "blocker" | "critical" | "major" | "minor" | "info";
export type IssueStatus = "open" | "in-review" | "resolved" | "escalated" | "accepted";
export type ParticipantRole = "owner" | "reviewer" | "approver" | "viewer" | "external";
export type CommentStatus = "active" | "resolved" | "archived";

// ── Negotiation KPI ──────────────────────────────────────────────────────

export interface NegotiationKpi {
  id: string;
  label: string;
  value: string;
  trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string;
  color: string;
  severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[];
  tooltip: string;
  drillDownView?: string;
}

// ── Document Version ─────────────────────────────────────────────────────

export interface DocumentVersion {
  id: string;
  label: string;
  timestamp: string;
  author: string;
  authorAvatar: string;
  status: "draft" | "current" | "superseded" | "approved";
  content: ClauseContent[];
  wordCount: number;
  changeSummary: string;
}

export interface ClauseContent {
  clauseId: string;
  title: string;
  sectionNumber: string;
  content: string;
  riskLevel: RiskLevel;
  category: string;
}

// ── Redline / Diff ───────────────────────────────────────────────────────

export interface RedlineEntry {
  id: string;
  type: RedlineType;
  clauseId: string;
  sectionNumber: string;
  title: string;
  originalText: string;
  modifiedText: string;
  author: string;
  authorAvatar: string;
  timestamp: string;
  riskLevel: RiskLevel;
  category: string;
  status: "pending" | "accepted" | "rejected" | "superseded";
  aiGenerated: boolean;
  aiConfidence?: number;
  negotiationImpact?: "high" | "medium" | "low";
  benchmarkDeviation?: number;
  comments: CommentItem[];
}

export interface DiffBlock {
  id: string;
  type: "unchanged" | "added" | "removed" | "modified";
  content: string;
  originalContent?: string;
  lineStart: number;
  lineEnd: number;
  clauseId?: string;
  riskLevel?: RiskLevel;
}

// ── Issue Management ─────────────────────────────────────────────────────

export interface NegotiationIssue {
  id: string;
  title: string;
  description: string;
  clauseId: string;
  sectionNumber: string;
  severity: IssueSeverity;
  status: IssueStatus;
  assignee: string;
  assigneeAvatar: string;
  dueDate: string;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  category: "legal" | "commercial" | "compliance" | "risk" | "vendor";
  escalationLevel: number;
  comments: CommentItem[];
  tags: string[];
}

// ── Comments & Collaboration ─────────────────────────────────────────────

export interface CommentItem {
  id: string;
  author: string;
  authorAvatar: string;
  authorRole: string;
  content: string;
  timestamp: string;
  status: CommentStatus;
  mentions: string[];
  replies: CommentItem[];
  attachmentUrl?: string;
  clauseId?: string;
  resolvedBy?: string;
  resolvedAt?: string;
}

export interface Participant {
  id: string;
  name: string;
  avatar: string;
  role: ParticipantRole;
  department: string;
  isOnline: boolean;
  lastActive: string;
  reviewedClauses: number;
  pendingApprovals: number;
}

// ── AI Insights ──────────────────────────────────────────────────────────

export interface AiNegotiationInsight {
  id: string;
  type: "risk" | "opportunity" | "benchmark" | "strategy" | "compliance";
  title: string;
  description: string;
  confidence: number;
  impact: "high" | "medium" | "low";
  benchmarkPercentile?: number;
  clauseId?: string;
  suggestedResponse?: string;
  fallbackClause?: string;
  severity: "critical" | "warning" | "info" | "success";
  category: string;
}

// ── Negotiation Playbook ─────────────────────────────────────────────────

export interface NegotiationPlaybook {
  id: string;
  title: string;
  description: string;
  clauseCategory: string;
  fallbackClauses: FallbackClause[];
  escalationGuidance: string;
  riskTolerance: "aggressive" | "moderate" | "conservative";
  jurisdictionNotes?: string;
  vendorSpecific?: string;
  aiRecommended: boolean;
}

export interface FallbackClause {
  id: string;
  title: string;
  content: string;
  strength: "strong" | "moderate" | "weak";
  acceptanceRate: number;
  riskReduction: number;
  usageCount: number;
}

// ── Workflow ─────────────────────────────────────────────────────────────

export interface NegotiationWorkflow {
  id: string;
  stage: NegotiationStage;
  slaDeadline: string;
  slaRemaining: number;
  approvers: { name: string; avatar: string; status: "pending" | "approved" | "rejected" }[];
  escalationLevel: number;
  isOverdue: boolean;
  healthScore: number;
}

// ── Analytics ────────────────────────────────────────────────────────────

export interface NegotiationAnalytics {
  totalSessions: number;
  avgCycleTime: number;
  concessionRate: number;
  redlineAcceptanceRate: number;
  clauseDisputeFrequency: { clause: string; count: number }[];
  vendorAggressiveness: { vendor: string; score: number }[];
  cycleBottlenecks: { stage: string; avgDays: number }[];
  timelineData: { date: string; redlines: number; approvals: number; comments: number }[];
  issueHeatmap: { category: string; severity: string; count: number }[];
  reviewThroughput: { reviewer: string; reviewed: number; avgTime: number }[];
}

// ── Activity / Audit ─────────────────────────────────────────────────────

export interface ActivityEntry {
  id: string;
  type: "edit" | "comment" | "approval" | "rejection" | "ai_action" | "escalation" | "status_change" | "version_create";
  user: string;
  userAvatar: string;
  action: string;
  description: string;
  timestamp: string;
  clauseId?: string;
  versionId?: string;
}

// ── Negotiation Session ──────────────────────────────────────────────────

export interface NegotiationSession {
  id: string;
  contractTitle: string;
  counterparty: string;
  stage: NegotiationStage;
  versions: DocumentVersion[];
  currentVersionId: string;
  redlines: RedlineEntry[];
  issues: NegotiationIssue[];
  participants: Participant[];
  insights: AiNegotiationInsight[];
  playbooks: NegotiationPlaybook[];
  workflow: NegotiationWorkflow;
  analytics: NegotiationAnalytics;
  activities: ActivityEntry[];
  healthScore: number;
  startedAt: string;
  updatedAt: string;
}

// ── View Mode ────────────────────────────────────────────────────────────

export type CompareMode = "side-by-side" | "inline" | "unified";
export type PanelMode = "edit" | "review" | "compare" | "final";
