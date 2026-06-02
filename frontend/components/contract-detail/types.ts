/**
 * Contract Detail Workspace — type definitions.
 */

import type { RiskLevel } from "@/components/dashboard/contracts/types";

// ── AI Finding ──────────────────────────────────────────────────────────────

export interface AiFinding {
  id: string;
  clause_type: string;
  severity: RiskLevel;
  confidence: number;
  title: string;
  description: string;
  recommendation: string;
  page_numbers: number[];
  chunk_id: string;
  clause_text: string;
  status: "open" | "resolved" | "dismissed" | "accepted_risk";
  category: string;
  remediation?: string;
  created_at: string;
  resolved_at?: string;
  resolved_by?: string;
}

// ── Clause Deviation ────────────────────────────────────────────────────────

export interface ClauseDeviation {
  id: string;
  clause_type: string;
  expected: string;
  actual: string;
  severity: RiskLevel;
  page_number: number;
  recommendation: string;
}

// ── Compliance Issue ────────────────────────────────────────────────────────

export interface ComplianceIssue {
  id: string;
  regulation: string;
  description: string;
  severity: RiskLevel;
  clause_reference: string;
  remediation: string;
}

// ── Activity Event ──────────────────────────────────────────────────────────

export type ActivityEventType =
  | "contract_created"
  | "contract_uploaded"
  | "ai_analysis_started"
  | "ai_analysis_completed"
  | "finding_resolved"
  | "finding_dismissed"
  | "comment_added"
  | "review_assigned"
  | "review_approved"
  | "review_rejected"
  | "status_changed"
  | "obligation_updated"
  | "renewal_approaching"
  | "version_created"
  | "metadata_updated";

export interface ActivityEvent {
  id: string;
  type: ActivityEventType;
  actor: string;
  action: string;
  timestamp: string;
  details?: string;
  metadata?: Record<string, unknown>;
}

// ── Comment / Thread ────────────────────────────────────────────────────────

export interface Comment {
  id: string;
  contract_id: string;
  author: string;
  author_avatar?: string;
  content: string;
  mentions: string[];
  parent_id?: string;
  replies: Comment[];
  page_number?: number;
  chunk_id?: string;
  status: "active" | "resolved";
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  resolved_by?: string;
}

// ── Obligation ──────────────────────────────────────────────────────────────

export interface Obligation {
  id: string;
  description: string;
  category: string;
  owner: string;
  due_date: string;
  status: "pending" | "in_progress" | "completed" | "overdue";
  priority: "low" | "medium" | "high";
}

// ── Contract Detail (Extended) ──────────────────────────────────────────────

export interface ContractDetail {
  id: string;
  name: string;
  filename: string;
  vendor: string;
  counterparty: string;
  contract_type: string;
  business_unit: string;
  geography: string;
  description: string;
  ai_summary: string;
  risk_score: number;
  risk_level: RiskLevel;
  financial_value: number;
  currency: string;
  status: string;
  workflow_stage: string;
  effective_date: string;
  expiration_date: string;
  renewal_date: string;
  auto_renew: boolean;
  has_dpa: boolean;
  owner: string;
  total_pages: number;
  clause_count: number;
  tags: string[];
  ai_findings_count: number;
  unresolved_risks: number;
  obligations_due: number;
  confidence_score: number;
  document_url: string;
  created_at: string;
  updated_at: string;
  last_activity: string;
  missing_clauses: string[];
  ai_flags: string[];
}

// ── Document Version ────────────────────────────────────────────────────────

export interface DocumentVersion {
  id: string;
  version_number: number;
  label: string;
  status: "current" | "previous" | "finalized";
  uploaded_by: string;
  uploaded_at: string;
  file_size: number;
  page_count: number;
}

// ── Panel State ─────────────────────────────────────────────────────────────

export type PanelVisibility = {
  left: boolean;
  center: boolean;
  right: boolean;
};

// ── Highlight Region ────────────────────────────────────────────────────────

export interface HighlightRegion {
  finding_id: string;
  page_number: number;
  chunk_id: string;
  rects: { x: number; y: number; width: number; height: number }[];
  severity: RiskLevel;
  color: string;
}
