// ── Enterprise Negotiation & Redline Center Types ─────────────────────────
// UI-specific types. Core data types are imported from shared.

import type {
  RiskLevel,
  NegotiationStage,
  RedlineType,
  IssueSeverity,
  IssueStatus,
  ParticipantRole,
  CommentStatus,
  VoteValue,
  ClauseContent,
  RedlineEntry,
  NegotiationIssue,
  CommentItem,
  Participant,
  DocumentVersion,
  NegotiationSession,
  NegotiationVote,
  VoteSummary,
  ClauseScoreData as ClauseScore,
  NegotiationKpis,
  NegotiationSummary,
  HistoryEntry,
  CounterpartyComparison,
  PositionComparison,
  ClauseDependency,
  AiRewriteResponse,
  AiCoachResponse,
  ApplyBundleResponse,
} from "@/services/api/negotiation.types";

// Re-export shared types for convenience
export type {
  RiskLevel,
  NegotiationStage,
  RedlineType,
  IssueSeverity,
  IssueStatus,
  ParticipantRole,
  CommentStatus,
  VoteValue,
  ClauseContent,
  RedlineEntry,
  NegotiationIssue,
  CommentItem,
  Participant,
  DocumentVersion,
  NegotiationSession,
  NegotiationVote,
  VoteSummary,
  ClauseScore,
  NegotiationKpis,
  NegotiationSummary,
  HistoryEntry,
  CounterpartyComparison,
  PositionComparison,
  ClauseDependency,
  AiRewriteResponse,
  AiCoachResponse,
  ApplyBundleResponse,
};

// ── Negotiation KPI (UI-specific) ────────────────────────────────────────

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

export interface ClauseContent {
  clauseId: string;
  title: string;
  sectionNumber: string;
  content: string;
  riskLevel: RiskLevel;
  category: string;
  negotiabilityScore?: number;
  readabilityScore?: number;
  marketStandardScore?: number;
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
  assignee: string | null;
  assigneeAvatar: string | null;
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
  findingId?: string;
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

export type CompareMode = "side-by-side" | "inline" | "unified" | "track-changes";
export type PanelMode = "edit" | "review" | "compare" | "final";

// ── Voting ───────────────────────────────────────────────────────────────

export type VoteValue = "approve" | "reject" | "pending";

export interface NegotiationVote {
  voteId: string;
  sessionId: string;
  clauseId: string;
  findingId?: string;
  voterName: string;
  voterRole: "legal" | "security" | "business" | "procurement" | string;
  vote: VoteValue;
  comment?: string;
  createdAt: string;
  updatedAt: string;
}

export interface VoteSummary {
  clauseId: string;
  total: number;
  approved: number;
  rejected: number;
  pending: number;
  votes: NegotiationVote[];
}

// ── Clause Score ─────────────────────────────────────────────────────────

export interface ClauseScore {
  clauseId: string;
  riskScore: number;
  negotiabilityScore: number;
  readabilityScore: number;
  marketStandardScore: number;
  overallScore: number;
}

// ── AI Explanation ───────────────────────────────────────────────────────

export interface AiExplanation {
  explanation: string;
  changes: { description: string }[];
  risksAddressed: string[];
  benefits: string[];
}

// ── AI Coach ─────────────────────────────────────────────────────────────

export interface CoachResponse {
  risks: string[];
  policyConflicts: string[];
  recommendedAlternative?: string;
  explanation: string;
}

// ── Dependency Warning ───────────────────────────────────────────────────

export interface DependencyWarning {
  affectedClause: string;
  relationship: "direct" | "implied" | "related";
  impact: "high" | "medium" | "low";
  description: string;
}

export interface DependencyWarnings {
  clauseId: string;
  clauseType: string;
  warnings: DependencyWarning[];
}

// ── Negotiation Summary ──────────────────────────────────────────────────

export interface NegotiationSummary {
  sessionId: string;
  totalClauses: number;
  clausesModified: number;
  clausesAccepted: number;
  clausesPending: number;
  clausesEscalated: number;
  riskScoreBefore: number;
  riskScoreAfter: number;
  estimatedTimeSavedHours: number;
  votesCast: number;
  votesApproved: number;
  votesRejected: number;
  aiRewritesUsed: number;
  generatedAt: string;
}

// ── Negotiation History Entry ────────────────────────────────────────────

export interface HistoryEntry {
  versionNumber: number;
  label: string;
  author: string;
  timestamp: string;
  action: "created" | "ai_rewrite" | "legal_edit" | "vendor_edit" | "accepted";
  clauseId: string;
  originalText: string;
  modifiedText: string;
  explanation?: string;
}

// ── Counterparty Comparison ──────────────────────────────────────────────

export interface CounterpartyComparison {
  clauseId: string;
  ourPosition: string;
  vendorPosition: string;
  finalPosition?: string;
  diffAdditions: string[];
  diffDeletions: string[];
}

// ── Negotiation Strategy ─────────────────────────────────────────────────

export interface NegotiationStrategy {
  strategyId: string;
  name: string;
  description: string;
  icon: string;
  promptTemplate: string;
  isDefault: boolean;
  isActive: boolean;
}
