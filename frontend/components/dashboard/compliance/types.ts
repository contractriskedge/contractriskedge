// ── Enterprise Compliance & Regulatory Intelligence Center Types ─────────

export type RiskLevel = "critical" | "high" | "medium" | "low" | "info" | "warning" | "success";
export type ComplianceStatus = "compliant" | "non_compliant" | "at_risk" | "pending" | "not_applicable";
export type RemediationStatus = "open" | "in_progress" | "resolved" | "overdue" | "escalated";
export type AuditStatus = "scheduled" | "in_progress" | "completed" | "failed" | "pending";

// ── Compliance KPI ───────────────────────────────────────────────────────

export interface ComplianceKpi {
  id: string; label: string; value: string; trend: number;
  trendDirection: "up" | "down" | "neutral";
  icon: string; color: string; severity: "critical" | "warning" | "success" | "info";
  sparklineData: number[]; tooltip: string;
}

// ── Regulation ───────────────────────────────────────────────────────────

export interface Regulation {
  id: string;
  name: string;
  shortName: string;
  description: string;
  jurisdiction: string;
  category: "privacy" | "security" | "financial" | "industry" | "regional";
  complianceScore: number;
  contractCoverage: number;
  totalRequirements: number;
  metRequirements: number;
  gapCount: number;
  status: ComplianceStatus;
  lastAssessed: string;
  icon: string;
}

// ── Compliance Finding ───────────────────────────────────────────────────

export interface ComplianceFinding {
  id: string;
  title: string;
  description: string;
  regulationId: string;
  regulationName: string;
  severity: RiskLevel;
  status: RemediationStatus;
  impactedContracts: number;
  impactedVendors: number;
  assignee: string;
  dueDate: string;
  createdAt: string;
  remediationSteps: string[];
  aiConfidence: number;
  regulatoryReference: string;
  category: string;
}

// ── Remediation Task ─────────────────────────────────────────────────────

export interface RemediationTask {
  id: string;
  findingId: string;
  title: string;
  description: string;
  assignee: string;
  assigneeAvatar: string;
  status: RemediationStatus;
  priority: "critical" | "high" | "medium" | "low";
  dueDate: string;
  slaRemaining: number;
  isOverdue: boolean;
  escalationLevel: number;
  evidenceRequired: boolean;
  evidenceProvided: boolean;
  createdAt: string;
  updatedAt: string;
}

// ── Vendor Compliance ────────────────────────────────────────────────────

export interface VendorCompliance {
  id: string;
  vendorName: string;
  overallScore: number;
  certifications: VendorCertification[];
  riskLevel: RiskLevel;
  contractCount: number;
  lastAssessed: string;
  status: ComplianceStatus;
}

export interface VendorCertification {
  id: string;
  name: string;
  standard: string;
  issueDate: string;
  expirationDate: string;
  status: "active" | "expiring" | "expired" | "pending";
  score: number;
}

// ── Audit ────────────────────────────────────────────────────────────────

export interface ComplianceAudit {
  id: string;
  title: string;
  regulationId: string;
  regulationName: string;
  status: AuditStatus;
  scope: string[];
  findings: number;
  passed: number;
  failed: number;
  readinessScore: number;
  evidenceCompleteness: number;
  startDate: string;
  endDate?: string;
  auditor: string;
  businessUnits: string[];
}

// ── AI Compliance Insight ────────────────────────────────────────────────

export interface AiComplianceInsight {
  id: string;
  type: "gap" | "risk" | "remediation" | "change" | "recommendation" | "conflict";
  title: string;
  description: string;
  severity: RiskLevel;
  confidence: number;
  impactedContracts: number;
  impactedRegulation: string;
  remediationSuggestion: string;
  regulatoryReference: string;
}

// ── Policy ───────────────────────────────────────────────────────────────

export interface CompliancePolicy {
  id: string;
  title: string;
  description: string;
  regulationId: string;
  version: string;
  status: "active" | "draft" | "archived" | "review";
  lastReviewed: string;
  nextReview: string;
  acknowledgements: number;
  totalRequired: number;
}

// ── Compliance Analytics ─────────────────────────────────────────────────

export interface ComplianceAnalytics {
  overallScore: number;
  auditReadiness: number;
  remediationProgress: number;
  scoreHistory: { date: string; score: number; }[];
  regulationCoverage: { regulation: string; coverage: number; }[];
  regionalExposure: { region: string; riskScore: number; contractCount: number; }[];
  remediationTrend: { date: string; open: number; resolved: number; }[];
  vendorComplianceDistribution: { status: string; count: number; }[];
  findingCategories: { category: string; count: number; }[];
  topViolations: { clause: string; regulation: string; count: number; }[];
}

// ── Compliance Detail ────────────────────────────────────────────────────

export interface ComplianceDetail {
  overview: {
    regulation: string;
    score: number;
    status: ComplianceStatus;
    lastAssessed: string;
    jurisdiction: string;
    contractsInScope: number;
    vendorsInScope: number;
  };
  regulatoryMapping: { requirement: string; status: string; evidence: string; }[];
  impactedContracts: { id: string; title: string; risk: RiskLevel; clause: string; }[];
  remediationActions: RemediationTask[];
  auditTrail: { action: string; user: string; timestamp: string; }[];
  aiRecommendations: AiComplianceInsight[];
  relatedPolicies: CompliancePolicy[];
  evidence: { id: string; name: string; type: string; status: string; }[];
}
