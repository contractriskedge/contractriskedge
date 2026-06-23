// ── Shared Negotiation Types ───────────────────────────────────────────
// Single source of truth for negotiation data types.
// Used by both the API service layer and UI components.

// ── Enums / Union Literals ────────────────────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info";
export type RedlineType = "addition" | "deletion" | "modification" | "suggestion" | "comment";
export type RedlineStatus = "pending" | "accepted" | "rejected" | "superseded";
export type IssueStatus = "open" | "in_review" | "negotiating" | "accepted" | "resolved" | "rejected" | "dismissed" | "escalated" | "verified" | "closed";
export type IssueSeverity = "blocker" | "critical" | "major" | "minor" | "info";
export type NegotiationStage = "drafting" | "review" | "negotiating" | "approved" | "executed" | "escalated";
export type ParticipantRole = "owner" | "reviewer" | "approver" | "viewer" | "external";
export type VoteValue = "approve" | "reject" | "abstain";
export type CommentStatus = "active" | "resolved";
export type ActivityEventType = "edit" | "comment" | "approval" | "rejection" | "ai_action" | "escalation" | "status_change" | "version_create";

// ── Core Data Types ───────────────────────────────────────────────────

export interface ClauseContent {
  clauseId: string;
  title: string;
  sectionNumber: string;
  content: string;
  riskLevel: RiskLevel;
  category: string;
  negotiabilityScore?: number | null;
  readabilityScore?: number | null;
  marketStandardScore?: number | null;
  // Counterparty negotiation fields (Sprint 28)
  counterpartyPosition?: string | null;
  vendorVersion?: string | null;
  negotiatedPosition?: string | null;
  finalAgreed?: string | null;
}

export interface RedlineEntry {
  id: string;
  type: RedlineType;
  clauseId: string;
  sectionNumber: string;
  title: string;
  originalText: string;
  modifiedText: string | null;
  author: string;
  authorAvatar: string;
  timestamp: string;
  riskLevel: RiskLevel;
  category: string;
  status: RedlineStatus;
  aiGenerated: boolean;
  aiConfidence?: number | null;
  negotiationImpact?: string | null;
  benchmarkDeviation?: number | null;
  comments?: CommentItem[];
}

export interface NegotiationIssue {
  id: string;
  clauseId: string;
  sectionNumber: string;
  title: string;
  description: string;
  severity: IssueSeverity;
  status: IssueStatus;
  category: string;
  riskLevel: RiskLevel;
  assignee: string | null;
  escalationLevel: number;
  comments: CommentItem[];
  createdAt: string;
  updatedAt: string;
  // Assignment fields
  dueDate?: string | null;
  priority?: "low" | "medium" | "high" | "critical" | null;
  watchers?: string[];
}

export interface CommentItem {
  id: string;
  comment_id?: string;
  author: string;
  authorAvatar: string;
  authorRole?: string;
  content: string;
  timestamp: string;
  status: CommentStatus;
  mentions?: string[];
  replies?: CommentItem[];
  parentCommentId?: string | null;
}

export interface Participant {
  id: string;
  name: string;
  avatar: string;
  role: ParticipantRole;
  isOnline: boolean;
  pendingApprovals: number;
  department?: string | null;
}

export interface ActivityItem {
  id: string;
  type: ActivityEventType;
  actor: string;
  actorAvatar: string;
  description: string;
  timestamp: string;
  clauseId?: string | null;
  findingId?: string | null;
  metadata?: Record<string, unknown>;
}

export interface DocumentVersion {
  id: string;
  sessionId: string;
  versionNumber: number;
  label: string;
  content: ClauseContent[];
  status: string;
  createdBy: string;
  createdAt: string;
  changeSummary?: string | null;
}

export interface NegotiationVote {
  id: string;
  sessionId: string;
  clauseId: string;
  voterName: string;
  voterRole: ParticipantRole;
  vote: VoteValue;
  comment: string | null;
  createdAt: string;
}

// ── Response Types ────────────────────────────────────────────────────

export interface NegotiationSession {
  id: string;
  contractTitle: string;
  counterparty: string;
  stage: NegotiationStage;
  healthScore: number;
  versions: DocumentVersion[];
  currentVersionId: string;
  redlines: RedlineEntry[];
  issues: NegotiationIssue[];
  participants: Participant[];
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface NegotiationSessionSummary {
  id: string;
  contractTitle: string;
  counterparty: string;
  stage: NegotiationStage;
  healthScore: number;
  createdAt: string;
  updatedAt: string;
}

export interface NegotiationKpis {
  totalSessions: number;
  activeSessions: number;
  escalatedCount: number;
  byStage: Record<string, number>;
  avgResolutionTime?: number;
  aiSuccessRate?: number;
  clauseAcceptanceRate?: number;
}

export interface ClauseScoreData {
  clauseId: string;
  riskScore: number;
  negotiabilityScore: number;
  readabilityScore: number;
  marketStandardScore: number;
  overallScore: number;
}

export interface AiRewriteResponse {
  rewrittenText: string;
  explanation: string;
  changes: Array<{
    type: "addition" | "deletion" | "modification";
    original: string;
    modified: string;
    reason: string;
  }>;
  riskScore?: number;
  readabilityScore?: number;
}

export interface AiCoachResponse {
  explanation: string;
  reasoning: string[];
  sources?: string[];
  followUpQuestions?: string[];
}

export interface ApplyBundleResponse {
  status: string;
  sessionId: string;
  clauseType: string;
  redlineIds: string[];
  templatesApplied: number;
  message: string;
}

export interface VoteSummary {
  clauseId: string;
  totalVotes: number;
  approveCount: number;
  rejectCount: number;
  abstainCount: number;
  voters: NegotiationVote[];
}

export interface ClauseDependency {
  clause: string;
  relationship: "direct" | "implied" | "related";
  impact: "high" | "medium" | "low";
  description: string;
}

export interface PositionComparison {
  clauseId: string;
  originalText: string;
  ourPosition: string;
  vendorPosition: string | null;
  finalAgreed: string | null;
}

// ── API Generic ───────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  total?: number;
  page?: number;
  pageSize?: number;
}
