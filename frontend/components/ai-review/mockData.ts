/**
 * Enterprise AI Review Platform — seeded realistic enterprise review data.
 *
 * Provides realistic mock data for development and demo purposes.
 * Includes reviews, findings, policy violations, recommendations, workflow states,
 * activity events, comments, and reviewer workloads.
 */

import type {
  ReviewSummary,
  Finding,
  PolicyViolation,
  MissingClause,
  Recommendation,
  WorkflowState,
  ActivityEvent,
  Comment,
  ReviewerWorkload,
  QueueMetrics,
} from "./types";

// ── Helpers ─────────────────────────────────────────────────────────────────

function daysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

function hoursAgo(hours: number): string {
  const d = new Date();
  d.setHours(d.getHours() - hours);
  return d.toISOString();
}

function minutesAgo(minutes: number): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - minutes);
  return d.toISOString();
}

// ── Mock Document Versions ──────────────────────────────────────────────────

export interface MockDocumentVersion {
  version_id: string;
  review_id: string;
  version_number: number;
  label: string | null;
  status: string;
  source_document_id: string | null;
  storage_key: string | null;
  change_summary: string | null;
  accepted_redline_ids: string[];
  file_size_bytes: number | null;
  mime_type: string | null;
  checksum_sha256: string | null;
  created_by: string;
  created_at: string;
}

export const MOCK_VERSIONS: MockDocumentVersion[] = [
  {
    version_id: "ver-001", review_id: "rev-001", version_number: 1, label: "Original Upload", status: "archived",
    source_document_id: "doc-001", storage_key: "uploads/rev-001/original.pdf", change_summary: "Initial contract upload from vendor", accepted_redline_ids: [],
    file_size_bytes: 245760, mime_type: "application/pdf", checksum_sha256: null, created_by: "System", created_at: daysAgo(3),
  },
  {
    version_id: "ver-002", review_id: "rev-001", version_number: 2, label: "AI Redlines Applied", status: "current",
    source_document_id: "doc-001", storage_key: "versions/rev-001/v2.docx", change_summary: "AI-generated redlines applied: liability cap, DPA, SLA, indemnification, term notice", accepted_redline_ids: ["rl-001", "rl-002", "rl-003"],
    file_size_bytes: 312320, mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", checksum_sha256: "a3f5b8c1d2e4f6a7b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1", created_by: "AI Engine", created_at: daysAgo(2),
  },
  {
    version_id: "ver-003", review_id: "rev-001", version_number: 3, label: "Legal Review Updates", status: "draft",
    source_document_id: "doc-001", storage_key: null, change_summary: "Legal Reviewer A modified liability cap to 3x and added IP exclusion", accepted_redline_ids: ["rl-004"],
    file_size_bytes: null, mime_type: null, checksum_sha256: null, created_by: "Legal Reviewer A", created_at: hoursAgo(18),
  },
  {
    version_id: "ver-004", review_id: "rev-001", version_number: 4, label: "Final Approved Copy", status: "finalized",
    source_document_id: "doc-001", storage_key: "versions/rev-001/v4-final.docx", change_summary: "All redlines resolved. Final approved version.", accepted_redline_ids: ["rl-001", "rl-002", "rl-003", "rl-004", "rl-005"],
    file_size_bytes: 289456, mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", checksum_sha256: "b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8", created_by: "Legal Reviewer A", created_at: hoursAgo(4),
  },
];

// ── Mock Risk Breakdown ─────────────────────────────────────────────────────

export interface MockRiskBreakdown {
  overall_risk_score: number;
  overall_label: string;
  original_risk_score: number;
  current_contract_risk: number;
  remaining_exposure: number;
  remaining_label: string;
  exposure_mode: "detected" | "remaining";
  review_started: boolean;
  risk_delta: number;
  status: string;
  breakdown: MockRiskBreakdownItem[];
  risk_reduction: number;
  dismissed_reduction: number;
  accepted_reduction: number;
  mitigated_findings: MockMitigatedFinding[];
  accepted_risk_findings: MockMitigatedFinding[];
  dismissed_findings: MockMitigatedFinding[];
  open_findings: MockMitigatedFinding[];
  delta_explanations: MockDeltaExplanation[];
  exposure_contributors: MockExposureContributor[];
  mitigation_suggestions: MockMitigationSuggestion[];
  top_recommended_actions: MockTopRecommendedActions;
}

export interface MockRiskBreakdownItem {
  category: string;
  label: string;
  contribution: number;
  normalized_contribution: number;
  finding_count: number;
  severity: string;
  mitigated_count: number;
  dismissed_count: number;
  accepted_count: number;
  open_count: number;
  findings: MockRiskBreakdownFinding[];
}

export interface MockRiskBreakdownFinding {
  finding_id: string;
  title: string;
  severity: string;
  risk_score: number | null;
  contribution: number;
  remaining_contribution?: number;
  resolution: string | null;
  resolution_type: string;
  clause_type: string | null;
  recommended_mitigation?: string;
  business_impact?: string;
}

export interface MockMitigatedFinding {
  finding_id?: string;
  title: string;
  clause_type: string | null;
  severity: string;
  resolution: string;
  resolution_label: string;
  remaining_contribution?: number;
  business_impact?: string;
  recommended_mitigation?: string;
  linked_redline_count?: number;
}

export interface MockDeltaExplanation {
  category: string;
  label: string;
  contribution: number;
  details: string[];
}

export interface MockExposureContributor {
  category: string;
  label: string;
  contribution: number;
  normalized_contribution: number;
  details: string[];
}

export interface MockMitigationSuggestion {
  category: string;
  label: string;
  remaining_contribution: number;
  suggested_mitigations: MockMitigationSuggestionItem[];
}

export interface MockMitigationSuggestionItem {
  mitigation_type: string;
  label: string;
  description: string;
  estimated_reduction: number;
  estimated_reduction_pct: number;
  confidence: number;
  source: string;
}

export interface MockTopRecommendedAction {
  category: string;
  label: string;
  mitigation_type: string;
  mitigation_label: string;
  description: string;
  estimated_reduction_pct: number;
  estimated_reduction_abs: number;
  confidence: number;
  source: string;
  remaining_contribution: number;
}

export interface MockTopRecommendedActions {
  top_actions: MockTopRecommendedAction[];
  total_potential_reduction_pct: number;
  total_potential_reduction_abs: number;
  action_count: number;
}

export const MOCK_RISK_BREAKDOWN: MockRiskBreakdown = {
  overall_risk_score: 0.78,
  overall_label: "High Risk",
  original_risk_score: 0.78,
  current_contract_risk: 0.52,
  remaining_exposure: 0.52,
  remaining_label: "Elevated Risk",
  exposure_mode: "remaining",
  review_started: true,
  risk_delta: -0.26,
  status: "analyzed",
  risk_reduction: 0.18,
  dismissed_reduction: 0.08,
  accepted_reduction: 0.05,
  breakdown: [
    { category: "liability", label: "Liability & Indemnification", contribution: 0.28, normalized_contribution: 0.28, finding_count: 2, severity: "critical", mitigated_count: 1, dismissed_count: 0, accepted_count: 0, open_count: 1, findings: [
      { finding_id: "find-001", title: "Unlimited Liability Clause", severity: "critical", risk_score: 0.94, contribution: 0.18, resolution: null, resolution_type: "open", clause_type: "liability", recommended_mitigation: "Add liability cap of 2x annual contract value", business_impact: "Potential exposure of $12.5M+ in uncapped liability" },
      { finding_id: "find-004", title: "Indemnification Without Mutual Coverage", severity: "high", risk_score: 0.91, contribution: 0.10, resolution: "resolved", resolution_type: "mitigated", clause_type: "indemnification", recommended_mitigation: "Add mutual indemnification for breach, confidentiality, and statutory violations", business_impact: "Customer bears all non-IP claim liability" },
    ]},
    { category: "data_protection", label: "Data Protection & Privacy", contribution: 0.20, normalized_contribution: 0.20, finding_count: 1, severity: "critical", mitigated_count: 0, dismissed_count: 0, accepted_count: 0, open_count: 1, findings: [
      { finding_id: "find-002", title: "Missing Data Protection Addendum", severity: "critical", risk_score: 0.97, contribution: 0.20, resolution: null, resolution_type: "open", clause_type: "data_protection", recommended_mitigation: "Add standard DPA addendum covering GDPR Art 28, CCPA, and SCCs", business_impact: "Regulatory fines up to 4% of global annual revenue" },
    ]},
    { category: "sla", label: "Service Levels & Availability", contribution: 0.15, normalized_contribution: 0.15, finding_count: 1, severity: "high", mitigated_count: 0, dismissed_count: 0, accepted_count: 1, open_count: 0, findings: [
      { finding_id: "find-006", title: "Missing Service Level Agreement (SLA)", severity: "high", risk_score: 0.95, contribution: 0.15, resolution: "accepted_risk", resolution_type: "accepted_risk", clause_type: "sla", recommended_mitigation: "Add SLA schedule with 99.9% uptime and 5% service credits", business_impact: "No recourse for service outages" },
    ]},
    { category: "term", label: "Contract Terms & Renewal", contribution: 0.10, normalized_contribution: 0.10, finding_count: 1, severity: "high", mitigated_count: 1, dismissed_count: 0, accepted_count: 0, open_count: 0, findings: [
      { finding_id: "find-003", title: "Auto-Renewal Without Notice Period", severity: "high", risk_score: 0.88, contribution: 0.10, resolution: "mitigated", resolution_type: "mitigated", clause_type: "term", recommended_mitigation: "Extend notice period to 90 days", business_impact: "Insufficient time to evaluate renewal terms" },
    ]},
    { category: "confidentiality", label: "Confidentiality & IP", contribution: 0.05, normalized_contribution: 0.05, finding_count: 1, severity: "high", mitigated_count: 0, dismissed_count: 0, accepted_count: 0, open_count: 1, findings: [
      { finding_id: "find-008", title: "Confidentiality Definition Too Narrow", severity: "high", risk_score: 0.89, contribution: 0.05, resolution: null, resolution_type: "open", clause_type: "confidentiality", recommended_mitigation: "Expand definition to include oral disclosures, pricing, and business terms", business_impact: "Pricing and commercial terms exposed" },
    ]},
  ],
  mitigated_findings: [
    { finding_id: "find-003", title: "Auto-Renewal Without Notice Period", clause_type: "term", severity: "high", resolution: "mitigated", resolution_label: "Mitigated", remaining_contribution: 0, business_impact: "Notice period extended to 90 days per recommendation", recommended_mitigation: "Extend notice period to 90 days" },
    { finding_id: "find-004", title: "Indemnification Without Mutual Coverage", clause_type: "indemnification", severity: "high", resolution: "mitigated", resolution_label: "Mitigated", remaining_contribution: 0, business_impact: "Mutual indemnification added per recommendation", recommended_mitigation: "Add mutual indemnification" },
  ],
  accepted_risk_findings: [
    { finding_id: "find-006", title: "Missing Service Level Agreement (SLA)", clause_type: "sla", severity: "high", resolution: "accepted_risk", resolution_label: "Accepted Exposure", remaining_contribution: 0.15, business_impact: "SLA negotiation deferred to contract renewal", recommended_mitigation: "Add SLA schedule with 99.9% uptime" },
  ],
  dismissed_findings: [
    { finding_id: "find-007", title: "Assignment Clause Restricts M&A Activity", clause_type: "assignment", severity: "medium", resolution: "dismissed", resolution_label: "Removed Exposure", remaining_contribution: 0, business_impact: "M&A activity not currently planned", recommended_mitigation: "Add exception for assignment to affiliates" },
  ],
  open_findings: [
    { finding_id: "find-001", title: "Unlimited Liability Clause", clause_type: "liability", severity: "critical", resolution: "open", resolution_label: "Open", remaining_contribution: 0.18, business_impact: "Potential exposure of $12.5M+ in uncapped liability", recommended_mitigation: "Add liability cap of 2x annual contract value", linked_redline_count: 1 },
    { finding_id: "find-002", title: "Missing Data Protection Addendum", clause_type: "data_protection", severity: "critical", resolution: "open", resolution_label: "Open", remaining_contribution: 0.20, business_impact: "Regulatory fines up to 4% of global annual revenue", recommended_mitigation: "Add standard DPA addendum", linked_redline_count: 1 },
    { finding_id: "find-008", title: "Confidentiality Definition Too Narrow", clause_type: "confidentiality", severity: "high", resolution: "open", resolution_label: "Open", remaining_contribution: 0.05, business_impact: "Pricing and commercial terms exposed", recommended_mitigation: "Expand confidentiality definition" },
  ],
  delta_explanations: [
    { category: "mitigation", label: "Mitigated: Liability & Indemnification", contribution: -0.10, details: ["Indemnification clause mutualized — reduces legal risk exposure", "Auto-renewal notice period extended to 90 days"] },
    { category: "dismissed", label: "Dismissed: Assignment Clause", contribution: -0.08, details: ["Assignment clause risk dismissed — M&A activity not planned"] },
    { category: "accepted", label: "Accepted: SLA Requirements", contribution: 0.05, details: ["SLA negotiation deferred to contract renewal cycle"] },
  ],
  exposure_contributors: [
    { category: "liability", label: "Liability Cap Risk", contribution: 0.18, normalized_contribution: 0.18, details: ["Unlimited liability clause — 96.3% of peers have caps", "Estimated impact: $12.5M uncapped exposure"] },
    { category: "data_protection", label: "Data Protection Compliance", contribution: 0.20, normalized_contribution: 0.20, details: ["Missing DPA — GDPR Art 28 requires written agreement", "Regulatory fines up to 4% of global revenue"] },
    { category: "confidentiality", label: "Confidentiality Scope", contribution: 0.05, normalized_contribution: 0.05, details: ["Narrow definition excludes pricing and oral disclosures"] },
  ],
  mitigation_suggestions: [
    {
      category: "liability", label: "Liability Cap", remaining_contribution: 0.18,
      suggested_mitigations: [
        { mitigation_type: "add_liability_cap", label: "Add Mutual Liability Cap (2x)", description: "Replace unlimited liability with mutual cap of 2x annual contract value", estimated_reduction: 0.15, estimated_reduction_pct: 0.15, confidence: 0.94, source: "enterprise_benchmark" },
        { mitigation_type: "add_liability_cap_3x", label: "Add Mutual Liability Cap (3x)", description: "Strategic partner exception — 3x annual contract value with IP exclusion", estimated_reduction: 0.12, estimated_reduction_pct: 0.12, confidence: 0.88, source: "policy_standard" },
      ],
    },
    {
      category: "data_protection", label: "DPA Addendum", remaining_contribution: 0.20,
      suggested_mitigations: [
        { mitigation_type: "attach_dpa", label: "Attach Standard DPA", description: "Attach enterprise DPA addendum with SCCs for cross-border transfers", estimated_reduction: 0.18, estimated_reduction_pct: 0.18, confidence: 0.97, source: "regulatory_requirement" },
      ],
    },
  ],
  top_recommended_actions: {
    top_actions: [
      { category: "liability", label: "Liability Cap", mitigation_type: "add_liability_cap", mitigation_label: "Add Mutual Liability Cap", description: "Replace unlimited liability with mutual cap of 2x annual contract value ($2.4M)", estimated_reduction_pct: 0.15, estimated_reduction_abs: 0.15, confidence: 0.94, source: "enterprise_benchmark", remaining_contribution: 0.18 },
      { category: "data_protection", label: "DPA Addendum", mitigation_type: "attach_dpa", mitigation_label: "Attach Data Processing Agreement", description: "Attach standard DPA addendum covering GDPR Art 28, CCPA, and cross-border transfers", estimated_reduction_pct: 0.18, estimated_reduction_abs: 0.18, confidence: 0.97, source: "regulatory_requirement", remaining_contribution: 0.20 },
      { category: "confidentiality", label: "Confidentiality", mitigation_type: "broaden_confidentiality", mitigation_label: "Broaden Confidentiality Definition", description: "Expand definition to include oral disclosures, pricing, and business terms", estimated_reduction_pct: 0.04, estimated_reduction_abs: 0.04, confidence: 0.89, source: "policy_standard", remaining_contribution: 0.05 },
    ],
    total_potential_reduction_pct: 0.37,
    total_potential_reduction_abs: 0.37,
    action_count: 3,
  },
};

// ── Mock Redlines ──────────────────────────────────────────────────────────

export interface MockRedlineItem {
  id: string;
  redline_id: string;
  clause_type: string;
  section: string;
  page: number;
  original_text: string;
  proposed_text: string;
  status: "pending" | "accepted" | "rejected" | "modified";
  severity: string;
  finding_id: string | null;
  finding_title: string | null;
  author: string;
  created_at: string;
  comments: { id: string; author: string; text: string; created_at: string }[];
  version: number;
  review_notes?: string;
  modified_text?: string;
}

export const MOCK_REDLINES: MockRedlineItem[] = [
  {
    id: "rl-001", redline_id: "rl-001", clause_type: "liability", section: "12.3", page: 12,
    original_text: "Party A shall be liable for all damages, losses, costs, and expenses arising from any breach of this Agreement, without limitation.",
    proposed_text: "Neither party's aggregate liability arising from this Agreement shall exceed 200% of the total fees paid during the 12 months preceding the claim, except for: (i) IP infringement, (ii) breach of confidentiality, (iii) statutory obligations, and (iv) gross negligence or willful misconduct.",
    status: "pending", severity: "critical", finding_id: "find-001", finding_title: "Unlimited Liability Clause", author: "AI Engine", created_at: daysAgo(2),
    comments: [{ id: "rc-001", author: "Legal Reviewer A", text: "3x annual value might be more appropriate for strategic partner", created_at: hoursAgo(18) }], version: 1,
  },
  {
    id: "rl-002", redline_id: "rl-002", clause_type: "data_protection", section: "8.2", page: 8,
    original_text: "The Parties agree to comply with all applicable data protection laws in the performance of this Agreement.",
    proposed_text: "The Parties agree to comply with all applicable data protection laws. The Parties shall enter into a Data Processing Agreement (DPA) in the form attached as Schedule C, which shall govern all processing of personal data. The DPA includes Standard Contractual Clauses for cross-border transfers.",
    status: "pending", severity: "critical", finding_id: "find-002", finding_title: "Missing Data Protection Addendum", author: "AI Engine", created_at: daysAgo(2),
    comments: [], version: 1,
  },
  {
    id: "rl-003", redline_id: "rl-003", clause_type: "term", section: "4.1", page: 4,
    original_text: "This Agreement shall automatically renew for successive one-year periods unless either party provides written notice of non-renewal at least 15 days prior to the expiration date.",
    proposed_text: "This Agreement shall automatically renew for successive one-year periods unless either party provides written notice of non-renewal at least ninety (90) days prior to the expiration date. Renewal pricing and material terms shall be confirmed in writing no later than 120 days prior to renewal.",
    status: "pending", severity: "high", finding_id: "find-003", finding_title: "Auto-Renewal Without Notice Period", author: "AI Engine", created_at: daysAgo(2),
    comments: [], version: 1,
  },
  {
    id: "rl-004", redline_id: "rl-004", clause_type: "indemnification", section: "8.1", page: 8,
    original_text: "Vendor shall indemnify Customer against third-party claims arising from IP infringement. Customer shall indemnify Vendor against all other claims.",
    proposed_text: "Each party shall indemnify, defend, and hold harmless the other party from and against any third-party claims arising from: (a) breach of confidentiality obligations, (b) violation of applicable law, (c) negligence or willful misconduct, and (d) IP infringement.",
    status: "pending", severity: "high", finding_id: "find-004", finding_title: "Indemnification Without Mutual Coverage", author: "AI Engine", created_at: daysAgo(2),
    comments: [], version: 1,
  },
  {
    id: "rl-005", redline_id: "rl-005", clause_type: "sla", section: "6.1", page: 6,
    original_text: "Vendor shall use commercially reasonable efforts to ensure availability of the Services.",
    proposed_text: "Vendor shall maintain 99.9% service availability, measured monthly. For each 0.5% below the target, Vendor shall issue a service credit equal to 5% of monthly fees. Critical incident response time: 30 minutes. Standard incident response: 4 business hours.",
    status: "pending", severity: "high", finding_id: "find-006", finding_title: "Missing Service Level Agreement (SLA)", author: "AI Engine", created_at: daysAgo(2),
    comments: [], version: 1,
  },
];

// ── Enterprise Reviewers ────────────────────────────────────────────────────

export const MOCK_REVIEWERS: ReviewerWorkload[] = [
  { user_id: "user-001", name: "Legal Reviewer A", email: "reviewer.a@contractedge.com", active_reviews: 3, completed_today: 2, overdue_reviews: 0, avg_review_time_hours: 4.2, workload_pct: 45, sla_breaches: 0, role: "Senior Legal Counsel" },
  { user_id: "user-002", name: "Contract Analyst B", email: "analyst.b@contractedge.com", active_reviews: 5, completed_today: 1, overdue_reviews: 1, avg_review_time_hours: 6.8, workload_pct: 72, sla_breaches: 1, role: "Contract Analyst" },
  { user_id: "user-003", name: "Legal Ops C", email: "ops.c@contractedge.com", active_reviews: 2, completed_today: 3, overdue_reviews: 0, avg_review_time_hours: 3.1, workload_pct: 28, sla_breaches: 0, role: "Legal Operations" },
  { user_id: "user-004", name: "Procurement D", email: "procurement.d@contractedge.com", active_reviews: 4, completed_today: 0, overdue_reviews: 2, avg_review_time_hours: 9.5, workload_pct: 88, sla_breaches: 3, role: "Procurement Manager" },
  { user_id: "user-005", name: "Compliance E", email: "compliance.e@contractedge.com", active_reviews: 1, completed_today: 4, overdue_reviews: 0, avg_review_time_hours: 2.8, workload_pct: 15, sla_breaches: 0, role: "Compliance Officer" },
];

// ── Enterprise Reviews ──────────────────────────────────────────────────────

export const MOCK_REVIEWS: ReviewSummary[] = [
  { review_id: "rev-001", contract_name: "Acme Corp - Master Services Agreement", vendor: "Acme Corp", document_type: "MSA", status: "under_review", workflow_stage: "legal_review", risk_score: 7.8, risk_level: "high", priority: "high", assigned_to: "user-001", assigned_to_name: "Legal Reviewer A", finding_count: 12, critical_findings: 3, high_findings: 5, policy_violations: 4, missing_clauses: 2, sla_status: "warning", sla_deadline: hoursAgo(12), overdue_hours: 0, escalation_level: 0, created_at: daysAgo(3), updated_at: hoursAgo(2), completed_at: null, age_hours: 72 },
  { review_id: "rev-002", contract_name: "TechGlobal - Software License Agreement", vendor: "TechGlobal Inc", document_type: "SLA", status: "ai_analyzed", workflow_stage: "ai_review", risk_score: 6.2, risk_level: "medium", priority: "medium", assigned_to: null, assigned_to_name: null, finding_count: 8, critical_findings: 1, high_findings: 3, policy_violations: 2, missing_clauses: 1, sla_status: "on_track", sla_deadline: hoursAgo(48), overdue_hours: 0, escalation_level: 0, created_at: daysAgo(1), updated_at: hoursAgo(6), completed_at: null, age_hours: 24 },
  { review_id: "rev-003", contract_name: "DataSecure - Data Processing Agreement", vendor: "DataSecure Ltd", document_type: "DPA", status: "escalated", workflow_stage: "escalated", risk_score: 9.1, risk_level: "critical", priority: "critical", assigned_to: "user-004", assigned_to_name: "Procurement D", finding_count: 18, critical_findings: 6, high_findings: 7, policy_violations: 8, missing_clauses: 3, sla_status: "critical_overdue", sla_deadline: hoursAgo(-6), overdue_hours: 6, escalation_level: 2, created_at: daysAgo(5), updated_at: hoursAgo(1), completed_at: null, age_hours: 120 },
  { review_id: "rev-004", contract_name: "BuildRight - Construction Contract", vendor: "BuildRight Partners", document_type: "Construction", status: "under_review", workflow_stage: "procurement_review", risk_score: 5.5, risk_level: "medium", priority: "medium", assigned_to: "user-002", assigned_to_name: "Contract Analyst B", finding_count: 6, critical_findings: 0, high_findings: 2, policy_violations: 1, missing_clauses: 0, sla_status: "on_track", sla_deadline: hoursAgo(36), overdue_hours: 0, escalation_level: 0, created_at: daysAgo(2), updated_at: hoursAgo(4), completed_at: null, age_hours: 48 },
  { review_id: "rev-005", contract_name: "HealthPlus - HIPAA BA Agreement", vendor: "HealthPlus Systems", document_type: "BAA", status: "legal_review", workflow_stage: "legal_review", risk_score: 8.3, risk_level: "high", priority: "high", assigned_to: "user-003", assigned_to_name: "Legal Ops C", finding_count: 15, critical_findings: 4, high_findings: 6, policy_violations: 5, missing_clauses: 2, sla_status: "warning", sla_deadline: hoursAgo(18), overdue_hours: 0, escalation_level: 1, created_at: daysAgo(4), updated_at: hoursAgo(3), completed_at: null, age_hours: 96 },
  { review_id: "rev-006", contract_name: "FinCorp - Banking Services Agreement", vendor: "FinCorp International", document_type: "Services", status: "draft", workflow_stage: "ingestion", risk_score: 4.1, risk_level: "low", priority: "low", assigned_to: null, assigned_to_name: null, finding_count: 3, critical_findings: 0, high_findings: 0, policy_violations: 0, missing_clauses: 0, sla_status: "on_track", sla_deadline: hoursAgo(72), overdue_hours: 0, escalation_level: 0, created_at: hoursAgo(8), updated_at: hoursAgo(2), completed_at: null, age_hours: 8 },
  { review_id: "rev-007", contract_name: "CloudServe - SaaS Agreement", vendor: "CloudServe Inc", document_type: "SaaS", status: "approved", workflow_stage: "completed", risk_score: 3.2, risk_level: "low", priority: "low", assigned_to: "user-005", assigned_to_name: "Compliance E", finding_count: 2, critical_findings: 0, high_findings: 0, policy_violations: 0, missing_clauses: 0, sla_status: "on_track", sla_deadline: null, overdue_hours: 0, escalation_level: 0, created_at: daysAgo(7), updated_at: daysAgo(1), completed_at: daysAgo(1), age_hours: 168 },
  { review_id: "rev-008", contract_name: "GreenEnergy - Supply Agreement", vendor: "GreenEnergy Corp", document_type: "Supply", status: "under_review", workflow_stage: "security_review", risk_score: 7.1, risk_level: "high", priority: "high", assigned_to: "user-002", assigned_to_name: "Contract Analyst B", finding_count: 10, critical_findings: 2, high_findings: 4, policy_violations: 3, missing_clauses: 1, sla_status: "overdue", sla_deadline: hoursAgo(-4), overdue_hours: 4, escalation_level: 1, created_at: daysAgo(4), updated_at: hoursAgo(5), completed_at: null, age_hours: 96 },
  { review_id: "rev-009", contract_name: "MediTech - Clinical Trial Agreement", vendor: "MediTech Research", document_type: "CTA", status: "under_review", workflow_stage: "legal_review", risk_score: 8.9, risk_level: "critical", priority: "critical", assigned_to: "user-001", assigned_to_name: "Legal Reviewer A", finding_count: 20, critical_findings: 7, high_findings: 8, policy_violations: 6, missing_clauses: 4, sla_status: "critical_overdue", sla_deadline: hoursAgo(-12), overdue_hours: 12, escalation_level: 3, created_at: daysAgo(6), updated_at: hoursAgo(1), completed_at: null, age_hours: 144 },
  { review_id: "rev-010", contract_name: "LogiTrans - Logistics Agreement", vendor: "LogiTrans GmbH", document_type: "Logistics", status: "ai_analyzed", workflow_stage: "ai_review", risk_score: 5.8, risk_level: "medium", priority: "medium", assigned_to: null, assigned_to_name: null, finding_count: 7, critical_findings: 1, high_findings: 2, policy_violations: 2, missing_clauses: 1, sla_status: "on_track", sla_deadline: hoursAgo(36), overdue_hours: 0, escalation_level: 0, created_at: daysAgo(1), updated_at: hoursAgo(8), completed_at: null, age_hours: 24 },
];

// ── Findings with Inline Explainability ─────────────────────────────────────

export const MOCK_FINDINGS: Finding[] = [
  { finding_id: "find-001", title: "Unlimited Liability Clause", description: "Section 12.3 contains unlimited liability exposure without cap. Standard market practice is 2x-3x contract value.", severity: "critical", confidence: 0.94, clause_type: "liability", clause_text: "Party A shall be liable for all damages, losses, costs, and expenses arising from any breach of this Agreement, without limitation.", page_numbers: [12], category: "Financial Risk", status: "open", resolution: null, resolution_type: null, created_at: daysAgo(3), resolved_at: null, resolved_by: null, business_impact: "Potential exposure of $12.5M+ in uncapped liability. Industry standard is 2x annual contract value ($2.4M).", recommended_mitigation: "Add liability cap of 2x annual contract value. Include mutual cap and exclude unlimited liability for IP infringement, confidentiality, and statutory obligations.", reasoning: "The clause uses 'all damages' and 'without limitation' which creates unlimited liability. Analysis of 1,247 similar MSA clauses shows 96.3% contain liability caps averaging 2.4x contract value.", similarity_score: 0.96, benchmark_deviation: 0.89, matched_corpus: "Enterprise MSA Benchmark Database v2026.1", confidence_semantic: 0.95, confidence_structural: 0.92, confidence_linguistic: 0.97, confidence_reference: 0.91, supporting_evidence: ["Market standard: 2x-3x annual contract value liability cap (Corpus reference: MSA-BENCH-2026)", "Industry peer group (n=1,247): 96.3% have liability caps", "Jurisdictional requirement: California Civil Code § 1668 restricts unlimited liability waivers"], alternative_interpretations: ["Some enterprise agreements with strategic partners use uncapped liability for IP infringement only", "Financial services contracts may have higher caps (5x-10x) due to regulatory requirements"], feedback: null },
  { finding_id: "find-002", title: "Missing Data Protection Addendum", description: "Contract references data processing activities but lacks required Data Processing Agreement (DPA) addendum.", severity: "critical", confidence: 0.97, clause_type: "data_protection", clause_text: "The Parties agree to comply with all applicable data protection laws in the performance of this Agreement.", page_numbers: [8], category: "Compliance", status: "open", resolution: null, resolution_type: null, created_at: daysAgo(3), resolved_at: null, resolved_by: null, business_impact: "Non-compliance with GDPR Art 28, CCPA, and LGPD. Regulatory fines up to 4% of global annual revenue.", recommended_mitigation: "Add standard DPA addendum covering data processing terms, sub-processor authorization, data breach notification, and cross-border transfer mechanisms (SCCs).", reasoning: "The contract references data processing but contains no DPA. GDPR Article 28 requires a written data processing agreement. CCPA Section 1798.100 mandates specific data protection terms.", similarity_score: 0.98, benchmark_deviation: 1.0, matched_corpus: "Global Privacy Regulation Corpus v2026", confidence_semantic: 0.97, confidence_structural: 0.95, confidence_linguistic: 0.98, confidence_reference: 0.99, supporting_evidence: ["GDPR Art 28(3): Processing shall be governed by a contract binding the processor to the controller", "CCPA §1798.100: Business must disclose data collection and processing purposes", "EU SCCs 2024/914: Required for cross-border data transfers"], alternative_interpretations: ["If no data processing occurs (pure services), DPA may not be required — verify with business team"], feedback: null },
  { finding_id: "find-003", title: "Auto-Renewal Without Notice Period", description: "Section 4.1 contains automatic renewal with only 15 days notice period. Standard is 60-90 days.", severity: "high", confidence: 0.88, clause_type: "term", clause_text: "This Agreement shall automatically renew for successive one-year periods unless either party provides written notice of non-renewal at least 15 days prior to the expiration date.", page_numbers: [4], category: "Contract Terms", status: "open", resolution: null, resolution_type: null, created_at: daysAgo(3), resolved_at: null, resolved_by: null, business_impact: "Insufficient time to evaluate renewal terms or negotiate changes. Risk of unfavorable auto-renewal.", recommended_mitigation: "Extend notice period to 90 days. Add requirement for written renewal confirmation with updated pricing.", reasoning: "15-day notice period is insufficient for enterprise procurement cycles. Average procurement review cycle is 45-60 days.", similarity_score: 0.85, benchmark_deviation: 0.72, matched_corpus: "Contract Term Benchmark Database", confidence_semantic: 0.87, confidence_structural: 0.85, confidence_linguistic: 0.91, confidence_reference: 0.88, supporting_evidence: ["Market standard: 60-90 days notice for enterprise agreements", "Procurement cycle benchmark: 45 days average review time"], alternative_interpretations: ["Short notice periods are common in SMB agreements (<$50K annual value)"], feedback: null },
  { finding_id: "find-004", title: "Indemnification Without Mutual Coverage", description: "Section 8.1 provides one-sided indemnification favoring the vendor only.", severity: "high", confidence: 0.91, clause_type: "indemnification", clause_text: "Vendor shall indemnify Customer against third-party claims arising from IP infringement. Customer shall indemnify Vendor against all other claims.", page_numbers: [9], category: "Legal Risk", status: "open", resolution: null, resolution_type: null, created_at: daysAgo(3), resolved_at: null, resolved_by: null, business_impact: "Customer bears all non-IP claim liability. Should have mutual indemnification for breach, negligence, and statutory violations.", recommended_mitigation: "Add mutual indemnification covering: (1) breach of confidentiality, (2) violation of applicable law, (3) negligence or willful misconduct, (4) IP infringement.", reasoning: "Standard enterprise practice is mutual indemnification. One-sided indemnification shifts disproportionate risk to customer.", similarity_score: 0.93, benchmark_deviation: 0.78, matched_corpus: "Enterprise Indemnification Standards v2026", confidence_semantic: 0.92, confidence_structural: 0.89, confidence_linguistic: 0.94, confidence_reference: 0.90, supporting_evidence: ["Market standard: Mutual indemnification in 94.2% of enterprise agreements >$1M"], alternative_interpretations: ["Vendor-standard forms often start one-sided — this is a negotiation starting point"], feedback: null },
  { finding_id: "find-005", title: "Governing Law - Foreign Jurisdiction", description: "Contract specifies Delaware law but both parties are based in EU/UK, creating enforcement complexity.", severity: "medium", confidence: 0.82, clause_type: "governing_law", clause_text: "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of laws principles.", page_numbers: [15], category: "Legal Risk", status: "open", resolution: null, resolution_type: null, created_at: daysAgo(3), resolved_at: null, resolved_by: null, business_impact: "Enforcement costs 3-5x higher in foreign jurisdiction. EU parties may have rights under Brussels Regulation.", recommended_mitigation: "Change governing law to match primary party jurisdiction or use neutral jurisdiction (e.g., ICC London).", reasoning: "Delaware law for EU-based parties creates enforcement barriers under Brussels I Regulation (Recast) Article 4.", similarity_score: 0.79, benchmark_deviation: 0.45, matched_corpus: "Cross-Border Contract Standards", confidence_semantic: 0.81, confidence_structural: 0.78, confidence_linguistic: 0.85, confidence_reference: 0.83, supporting_evidence: ["EU Brussels I Regulation: Defendants must be sued in member state of domicile", "Enforcement cost analysis: Foreign enforcement averages $85K-150K additional cost"], alternative_interpretations: ["Delaware law is widely understood and has extensive case law — some parties prefer it for predictability"], feedback: null },
  { finding_id: "find-006", title: "Missing Service Level Agreement (SLA)", description: "No uptime guarantees, performance metrics, or service credits specified.", severity: "high", confidence: 0.95, clause_type: "sla", clause_text: "Vendor shall use commercially reasonable efforts to ensure availability of the Services.", page_numbers: [6], category: "Operational Risk", status: "open", resolution: null, resolution_type: null, created_at: daysAgo(3), resolved_at: null, resolved_by: null, business_impact: "No recourse for service outages. Industry standard is 99.9% uptime with 5-10% service credits.", recommended_mitigation: "Add SLA schedule with: 99.9% uptime guarantee, 5% service credit per 0.5% below target, 30-minute response for critical incidents.", reasoning: "Commercially reasonable efforts' is insufficient for enterprise services. 99.9% uptime is market standard.", similarity_score: 0.94, benchmark_deviation: 0.85, matched_corpus: "Enterprise SLA Benchmark Database", confidence_semantic: 0.95, confidence_structural: 0.93, confidence_linguistic: 0.96, confidence_reference: 0.94, supporting_evidence: ["Market standard: 99.9% uptime for SaaS (n=3,456 agreements)", "Service credits: 5-10% per 0.5% below target"], alternative_interpretations: ["Startups and SMB vendors may offer 99.5% — acceptable for non-critical systems"], feedback: null },
  { finding_id: "find-007", title: "Assignment Clause Restricts M&A Activity", description: "Section 10.2 requires consent for assignment including change of control, with consent not to be unreasonably withheld.", severity: "medium", confidence: 0.76, clause_type: "assignment", clause_text: "Neither party may assign this Agreement without the prior written consent of the other party.", page_numbers: [14], category: "Contract Terms", status: "open", resolution: null, resolution_type: null, created_at: daysAgo(3), resolved_at: null, resolved_by: null, business_impact: "May impede future M&A, restructuring, or divestiture activities. Could trigger default in change of control.", recommended_mitigation: "Add exception for assignment to affiliates and in connection with merger/acquisition without consent.", reasoning: "Silence on change of control creates uncertainty. Standard practice is to permit assignment to affiliates.", similarity_score: 0.72, benchmark_deviation: 0.35, matched_corpus: "M&A Contract Review Standards", confidence_semantic: 0.74, confidence_structural: 0.71, confidence_linguistic: 0.79, confidence_reference: 0.78, supporting_evidence: ["Market standard: 87% of enterprise agreements permit assignment to affiliates"], alternative_interpretations: ["Some parties restrict assignment to maintain relationship control — valid for strategic contracts"], feedback: null },
  { finding_id: "find-008", title: "Confidentiality Definition Too Narrow", description: "Confidential information definition excludes pricing, business terms, and oral disclosures.", severity: "high", confidence: 0.89, clause_type: "confidentiality", clause_text: "Confidential Information shall mean written information clearly marked as confidential at the time of disclosure.", page_numbers: [7], category: "Legal Risk", status: "open", resolution: null, resolution_type: null, created_at: daysAgo(3), resolved_at: null, resolved_by: null, business_impact: "Pricing and commercial terms exposed. Oral discussions of sensitive strategy unprotected.", recommended_mitigation: "Expand definition to include: all oral disclosures (summarized in writing within 30 days), pricing, business terms, and proprietary methodology.", reasoning: "Narrow confidentiality definitions are a common risk. 73% of data breaches involve information not clearly marked.", similarity_score: 0.87, benchmark_deviation: 0.68, matched_corpus: "Information Protection Standards", confidence_semantic: 0.88, confidence_structural: 0.85, confidence_linguistic: 0.92, confidence_reference: 0.90, supporting_evidence: ["Industry standard: Broad definition covering oral, visual, and electronic disclosures"], alternative_interpretations: ["Narrow definitions reduce administrative burden of marking — acceptable for low-risk engagements"], feedback: null },
];

// ── Policy Violations ───────────────────────────────────────────────────────

export const MOCK_POLICY_VIOLATIONS: PolicyViolation[] = [
  { id: "pol-001", policy_name: "Enterprise Liability Policy v4.2", policy_version: "4.2", clause_type: "liability", severity: "critical", description: "Unlimited liability exceeds maximum allowable cap of 3x contract value per Enterprise Risk Policy Section 4.1", expected: "Liability cap of 2x-3x annual contract value ($2.4M-$3.6M)", actual: "Unlimited liability with no cap specified", recommendation: "Add liability cap of 2x annual contract value with mutual coverage", page_number: 12, compliance_impact: "critical", regulation: "Enterprise Risk Policy §4.1", status: "open", created_at: daysAgo(3) },
  { id: "pol-002", policy_name: "Data Protection Compliance Policy v3.8", policy_version: "3.8", clause_type: "data_protection", severity: "critical", description: "Mandatory DPA addendum not attached. Policy requires DPA for all contracts involving data processing.", expected: "Signed DPA addendum attached per Data Protection Policy §2.1", actual: "No DPA addendum present in contract package", recommendation: "Attach standard DPA addendum and verify data processing scope", page_number: 8, compliance_impact: "critical", regulation: "GDPR Art 28, CCPA §1798.100, Data Protection Policy §2.1", status: "open", created_at: daysAgo(3) },
  { id: "pol-003", policy_name: "Contract Term Standards v5.1", policy_version: "5.1", clause_type: "term", severity: "high", description: "Auto-renewal notice period of 15 days is below minimum 60-day requirement.", expected: "Minimum 60-day notice period for auto-renewal clauses per Contract Term Policy §3.2", actual: "15-day notice period in Section 4.1", recommendation: "Extend notice period to 90 days per policy standard", page_number: 4, compliance_impact: "high", regulation: "Contract Term Policy §3.2", status: "open", created_at: daysAgo(3) },
  { id: "pol-004", policy_name: "Indemnification Standards v4.0", policy_version: "4.0", clause_type: "indemnification", severity: "high", description: "Non-mutual indemnification violates Enterprise Indemnification Policy requiring mutual coverage.", expected: "Mutual indemnification covering breach, IP, confidentiality, and statutory violations per Indemnification Policy §2.3", actual: "One-sided indemnification favoring vendor only", recommendation: "Add mutual indemnification for breach, confidentiality, and statutory violations", page_number: 9, compliance_impact: "high", regulation: "Indemnification Policy §2.3", status: "open", created_at: daysAgo(3) },
  { id: "pol-005", policy_name: "Service Level Requirements v6.0", policy_version: "6.0", clause_type: "sla", severity: "high", description: "No SLA with uptime guarantees or service credits violates Service Level Policy.", expected: "Minimum 99.9% uptime guarantee with service credits per SLA Policy §1.1", actual: "Only 'commercially reasonable efforts' for availability", recommendation: "Add SLA schedule with 99.9% uptime and 5% service credits", page_number: 6, compliance_impact: "high", regulation: "SLA Policy §1.1", status: "open", created_at: daysAgo(3) },
  { id: "pol-006", policy_name: "Confidentiality Standards v3.2", policy_version: "3.2", clause_type: "confidentiality", severity: "high", description: "Confidentiality definition too narrow, excludes pricing and oral disclosures.", expected: "Broad definition covering all disclosures including oral, visual, pricing, and business terms per Confidentiality Policy §1.4", actual: "Narrow definition limited to written marked disclosures", recommendation: "Expand confidentiality definition per policy standards", page_number: 7, compliance_impact: "high", regulation: "Confidentiality Policy §1.4", status: "open", created_at: daysAgo(3) },
];

// ── Missing Clauses ─────────────────────────────────────────────────────────

export const MOCK_MISSING_CLAUSES: MissingClause[] = [
  { id: "mc-001", clause_type: "Data Processing Agreement (DPA)", importance: "required", reason: "GDPR Art 28 requires written DPA for all data processing activities", risk_if_missing: "Regulatory fines up to 4% of global revenue under GDPR", fallback_recommendation: "Attach standard enterprise DPA addendum with SCCs for cross-border transfers", industry_standard: true },
  { id: "mc-002", clause_type: "Service Level Agreement (SLA)", importance: "required", reason: "Enterprise policy requires SLA for all vendor services over $100K annual value", risk_if_missing: "No recourse for service outages. Estimated impact: $50K/hr for critical systems", fallback_recommendation: "Add SLA with 99.9% uptime, 5% service credits, and 30-min critical incident response", industry_standard: true },
  { id: "mc-003", clause_type: "Audit Rights Clause", importance: "recommended", reason: "No right to audit vendor's security practices, data handling, or compliance controls", risk_if_missing: "Unable to verify vendor compliance. Security incidents undetected for avg 287 days", fallback_recommendation: "Add annual audit right with 30-day notice, scope limited to security and data practices", industry_standard: true },
  { id: "mc-004", clause_type: "Limitation of Liability (Mutual)", importance: "required", reason: "Enterprise Risk Policy requires mutual liability caps for all service agreements", risk_if_missing: "Uncapped liability exposure. Average enterprise claim: $2.8M", fallback_recommendation: "Add mutual liability cap at 2x annual contract value with standard exclusions", industry_standard: true },
];

// ── Recommendations ─────────────────────────────────────────────────────────

export const MOCK_RECOMMENDATIONS: Recommendation[] = [
  { recommendation_id: "rec-001", type: "remediation", clause_type: "liability", title: "Add Mutual Liability Cap", description: "Replace unlimited liability with mutual cap of 2x annual contract value ($2.4M) with standard exclusions for IP infringement, confidentiality, and statutory obligations.", suggested_text: "Neither party's aggregate liability arising from this Agreement shall exceed 200% of the total fees paid during the 12 months preceding the claim, except for: (i) IP infringement, (ii) breach of confidentiality, (iii) statutory obligations, and (iv) gross negligence or willful misconduct.", rationale: "Market standard for enterprise agreements of this size and type. Protects both parties while ensuring adequate remedy for breaches.", confidence: 0.94, impact: "high", effort: "medium", priority: 1, status: "pending", finding_id: "find-001" },
  { recommendation_id: "rec-002", type: "remediation", clause_type: "data_protection", title: "Attach Standard DPA Addendum", description: "Attach enterprise DPA addendum covering GDPR Art 28, CCPA, and cross-border transfer mechanisms (SCCs).", suggested_text: null, rationale: "Required by regulation and enterprise policy. Standard DPA template available in clause library.", confidence: 0.97, impact: "high", effort: "low", priority: 2, status: "pending", finding_id: "find-002" },
  { recommendation_id: "rec-003", type: "negotiation", clause_type: "term", title: "Extend Auto-Renewal Notice Period", description: "Negotiate extension of notice period from 15 to 90 days with requirement for written confirmation of renewal terms.", suggested_text: "This Agreement shall automatically renew for successive one-year periods unless either party provides written notice of non-renewal at least ninety (90) days prior to the expiration date. Renewal pricing and material terms shall be confirmed in writing no later than 120 days prior to renewal.", rationale: "90 days aligns with enterprise procurement cycle. Written confirmation ensures transparency on pricing changes.", confidence: 0.88, impact: "medium", effort: "low", priority: 3, status: "pending", finding_id: "find-003" },
  { recommendation_id: "rec-004", type: "negotiation", clause_type: "indemnification", title: "Mutualize Indemnification", description: "Add mutual indemnification for breach of confidentiality, violation of law, negligence, and willful misconduct.", suggested_text: "Each party shall indemnify, defend, and hold harmless the other party from and against any third-party claims arising from: (a) breach of confidentiality obligations, (b) violation of applicable law, (c) negligence or willful misconduct, and (d) IP infringement.", rationale: "Mutual indemnification is market standard for enterprise agreements and fairly allocates risk.", confidence: 0.91, impact: "high", effort: "medium", priority: 4, status: "pending", finding_id: "find-004" },
  { recommendation_id: "rec-005", type: "remediation", clause_type: "sla", title: "Add SLA Schedule with Service Credits", description: "Add comprehensive SLA with 99.9% uptime, 5% service credits, and incident response times.", suggested_text: "Vendor shall maintain 99.9% service availability. For each 0.5% below target, Vendor shall issue 5% service credit. Critical incident response: 30 minutes. Standard incident response: 4 hours.", rationale: "99.9% uptime with service credits is market standard for enterprise SaaS and cloud services.", confidence: 0.95, impact: "high", effort: "medium", priority: 5, status: "pending", finding_id: "find-006" },
  { recommendation_id: "rec-006", type: "best_practice", clause_type: "confidentiality", title: "Broaden Confidentiality Definition", description: "Expand definition to include oral disclosures, pricing, business terms, and proprietary methodology.", suggested_text: "Confidential Information includes all written, oral, visual, or electronic information disclosed by either party, including but not limited to: pricing, business terms, financial data, technical specifications, business processes, and proprietary methodology.", rationale: "Broad definition provides comprehensive protection. Oral disclosure protection critical for strategy discussions.", confidence: 0.89, impact: "medium", effort: "low", priority: 6, status: "pending", finding_id: "find-008" },
  { recommendation_id: "rec-007", type: "fallback", clause_type: "governing_law", title: "Use Neutral Governing Law", description: "If Delaware law is non-negotiable, add arbitration clause with neutral venue.", suggested_text: "Any disputes arising from this Agreement shall be finally settled under the Rules of Arbitration of the International Chamber of Commerce by one or more arbitrators appointed in accordance with said Rules. The seat of arbitration shall be London, England.", rationale: "ICC London provides neutral, internationally enforceable dispute resolution for cross-border contracts.", confidence: 0.82, impact: "medium", effort: "medium", priority: 7, status: "pending", finding_id: "find-005" },
];

// ── Workflow States ─────────────────────────────────────────────────────────

export const MOCK_WORKFLOW_STATES: Record<string, WorkflowState> = {
  "rev-001": {
    current_stage: "legal_review",
    available_actions: ["approve", "reject", "escalate", "send_to_procurement"],
    stages: [
      { id: "ingestion", label: "Ingestion", status: "completed", completed_at: daysAgo(3), completed_by: "System" },
      { id: "ai_analysis", label: "AI Analysis", status: "completed", completed_at: daysAgo(3), completed_by: "AI Engine" },
      { id: "initial_review", label: "Initial Review", status: "completed", completed_at: daysAgo(2), completed_by: "Legal Reviewer A" },
      { id: "legal_review", label: "Legal Review", status: "current", sla_deadline: hoursAgo(12) },
      { id: "procurement_review", label: "Procurement", status: "pending" },
      { id: "approval", label: "Approval", status: "pending" },
      { id: "execution", label: "Execution", status: "pending" },
    ],
    sla_remaining_hours: 12,
    escalation_level: 0,
    reviewers: [
      { user_id: "user-001", name: "Legal Reviewer A", email: "reviewer.a@contractedge.com", role: "Senior Legal Counsel", assigned_at: daysAgo(2), active_reviews: 3, workload_pct: 45 },
    ],
    queue_position: 3,
    queue_total: 12,
    workload_score: 45,
  },
  "rev-003": {
    current_stage: "escalated",
    available_actions: ["approve", "reject", "de-escalate"],
    stages: [
      { id: "ingestion", label: "Ingestion", status: "completed", completed_at: daysAgo(5), completed_by: "System" },
      { id: "ai_analysis", label: "AI Analysis", status: "completed", completed_at: daysAgo(5), completed_by: "AI Engine" },
      { id: "initial_review", label: "Initial Review", status: "completed", completed_at: daysAgo(4), completed_by: "Procurement D" },
      { id: "legal_review", label: "Legal Review", status: "completed", completed_at: daysAgo(3), completed_by: "Procurement D" },
      { id: "escalated", label: "Escalated (L2)", status: "current", sla_deadline: hoursAgo(-6) },
    ],
    sla_remaining_hours: -6,
    escalation_level: 2,
    reviewers: [
      { user_id: "user-004", name: "Procurement D", email: "procurement.d@contractedge.com", role: "Procurement Manager", assigned_at: daysAgo(4), active_reviews: 4, workload_pct: 88 },
    ],
    queue_position: 1,
    queue_total: 12,
    workload_score: 88,
  },
};

// ── Activity Events ─────────────────────────────────────────────────────────

export const MOCK_ACTIVITY: ActivityEvent[] = [
  { id: "act-001", type: "review_created", actor: "System", actor_initials: "SY", action: "Review created from ingestion pipeline", details: "Document uploaded and parsed. 42 chunks extracted.", timestamp: daysAgo(3) },
  { id: "act-002", type: "ai_analysis_completed", actor: "AI Engine", actor_initials: "AI", action: "AI analysis completed", details: "12 findings identified. 3 critical, 5 high, 3 medium, 1 low. Confidence: 88%", timestamp: daysAgo(3) },
  { id: "act-003", type: "review_assigned", actor: "Contract Analyst B", actor_initials: "CA", action: "Assigned to Legal Reviewer A (Senior Legal Counsel)", details: "Priority: High. SLA: 48 hours.", timestamp: daysAgo(2) },
  { id: "act-004", type: "finding_resolved", actor: "Legal Reviewer A", actor_initials: "LR", action: "Resolved finding: Minor formatting issue in Schedule A", details: "Finding find-009 marked as resolved. Reviewer accepted recommendation.", timestamp: hoursAgo(24) },
  { id: "act-005", type: "comment_added", actor: "Legal Reviewer A", actor_initials: "LR", action: "Added comment on Section 12.3 (Liability)", details: "Need business input on acceptable liability cap. Recommend 2x annual value.", timestamp: hoursAgo(18) },
  { id: "act-006", type: "finding_feedback", actor: "Legal Reviewer A", actor_initials: "LR", action: "Marked AI finding as partially incorrect", details: "Liability clause analysis correct but missing exception for IP infringement. Feedback submitted for retraining.", timestamp: hoursAgo(12) },
  { id: "act-007", type: "review_escalated", actor: "Legal Reviewer A", actor_initials: "LR", action: "Escalated to Legal Director", details: "Unlimited liability requires VP-level approval per delegation of authority policy.", timestamp: hoursAgo(6) },
  { id: "act-008", type: "recommendation_applied", actor: "Legal Reviewer A", actor_initials: "LR", action: "Applied recommendation: Add SLA schedule", details: "Recommendation rec-005 marked as applied. SLA text added to contract.", timestamp: hoursAgo(4) },
  { id: "act-009", type: "status_changed", actor: "System", actor_initials: "SY", action: "SLA status changed to Warning", details: "12 hours remaining. 2 of 3 critical findings still open.", timestamp: hoursAgo(2) },
  { id: "act-010", type: "finding_dismissed", actor: "Legal Reviewer A", actor_initials: "LR", action: "Dismissed finding: Assignment clause risk", details: "Finding find-007 dismissed as accepted risk. M&A activity not planned.", timestamp: hoursAgo(1) },
];

// ── Comments ────────────────────────────────────────────────────────────────

export const MOCK_COMMENTS: Comment[] = [
  {
    comment_id: "cmt-001", review_id: "rev-001", finding_id: "find-001", author: "Legal Reviewer A", author_initials: "LR", content: "This unlimited liability clause needs business input. @Contract Analyst B can you confirm acceptable cap based on our relationship with Acme?", mentions: ["Contract Analyst B"], parent_id: null, replies: [
      { comment_id: "cmt-002", review_id: "rev-001", finding_id: "find-001", author: "Contract Analyst B", author_initials: "CA", content: "Agreed. Acme is a strategic partner. Recommend 3x annual value ($3.6M) with standard IP exclusion.", mentions: [], parent_id: "cmt-001", replies: [], status: "active", created_at: hoursAgo(16), updated_at: hoursAgo(16), resolved_at: null, resolved_by: null },
      { comment_id: "cmt-003", review_id: "rev-001", finding_id: "find-001", author: "Legal Reviewer A", author_initials: "LR", content: "Thanks @Contract Analyst B. I'll proceed with 3x cap. @Compliance E please confirm policy allows this exception.", mentions: ["Contract Analyst B", "Compliance E"], parent_id: "cmt-001", replies: [], status: "active", created_at: hoursAgo(14), updated_at: hoursAgo(14), resolved_at: null, resolved_by: null },
    ], status: "active", created_at: hoursAgo(18), updated_at: hoursAgo(14), resolved_at: null, resolved_by: null },
  { comment_id: "cmt-004", review_id: "rev-001", finding_id: "find-002", author: "Legal Reviewer A", author_initials: "LR", content: "DPA is required per GDPR Art 28. @Compliance E please attach standard DPA template.", mentions: ["Compliance E"], parent_id: null, replies: [
    { comment_id: "cmt-005", review_id: "rev-001", finding_id: "find-002", author: "Compliance E", author_initials: "CE", content: "Standard DPA v4.2 attached. Includes SCCs for cross-border transfers. Please verify data processing scope with Acme.", mentions: [], parent_id: "cmt-004", replies: [], status: "active", created_at: hoursAgo(10), updated_at: hoursAgo(10), resolved_at: null, resolved_by: null },
  ], status: "active", created_at: hoursAgo(17), updated_at: hoursAgo(10), resolved_at: null, resolved_by: null },
  { comment_id: "cmt-006", review_id: "rev-001", finding_id: null, author: "Legal Reviewer A", author_initials: "LR", content: "Overall assessment: 3 critical issues to resolve before approval. Liability cap, DPA, and SLA are blockers.", mentions: [], parent_id: null, replies: [], status: "active", created_at: hoursAgo(2), updated_at: hoursAgo(2), resolved_at: null, resolved_by: null },
];

// ── Queue Metrics ───────────────────────────────────────────────────────────

export const MOCK_QUEUE_METRICS: QueueMetrics = {
  total: 12,
  unassigned: 3,
  in_review: 6,
  overdue: 2,
  critical_overdue: 1,
  escalated: 2,
  sla_at_risk: 3,
  avg_age_hours: 58,
  max_age_hours: 144,
  completed_today: 4,
};
