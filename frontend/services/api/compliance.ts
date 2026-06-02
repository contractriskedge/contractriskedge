/**
 * Compliance API service — real API client for compliance operations.
 * Replaces legacy mockData imports with live backend integration.
 */

"use client";

import { api } from "@/services/api/client";

// ── Types matching backend API responses ────────────────────────────────

export interface ComplianceFramework {
  framework_id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  is_active: boolean;
  control_count: number;
}

export interface ComplianceControl {
  control_id: string;
  framework_id: string;
  control_id_str: string;
  name: string;
  description: string;
  category: string;
  risk_level: string;
  is_active: boolean;
  sort_order: number;
}

export interface ComplianceAssessment {
  assessment_id: string;
  framework_id: string;
  name: string;
  description: string;
  status: string;
  score: number | null;
  total_controls: number;
  passed_controls: number;
  failed_controls: number;
  compliance_percentage: number | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface ComplianceFinding {
  finding_id: string;
  assessment_id: string;
  control_id: string | null;
  title: string;
  description: string;
  severity: string;
  status: string;
  risk_score: number | null;
  due_date: string | null;
  assigned_to: string | null;
}

export interface ComplianceException {
  exception_id: string;
  control_id: string;
  title: string;
  justification: string;
  risk_assessment: string | null;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  expires_at: string | null;
}

export interface ComplianceEvidence {
  evidence_id: string;
  evidence_type: string;
  framework: string;
  control_id: string;
  description: string;
  status: string;
  collected_at: string;
  validated_by: string | null;
  validated_at: string | null;
}

export interface ComplianceDashboardData {
  frameworks: number;
  controls: number;
  open_findings: number;
  critical_findings: number;
  total_findings: number;
  assessments: number;
  completed_assessments: number;
  compliance_score: number | null;
}

export interface ComplianceScanResult {
  frameworks_scanned: number;
  controls_evaluated: number;
  new_findings: number;
  updated_findings: number;
  compliance_score: number;
  frameworks: {
    framework_id: string;
    framework_name: string;
    controls_total: number;
    controls_passed: number;
    controls_failed: number;
    score: number;
  }[];
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

// ── API Fetchers ────────────────────────────────────────────────────────

export async function fetchComplianceDashboard(): Promise<ComplianceDashboardData> {
  return api.get<ComplianceDashboardData>("/compliance/dashboard");
}

export async function fetchComplianceFrameworks(params?: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceFramework>> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString();
  return api.get(`/compliance/frameworks${query ? `?${query}` : ""}`);
}

export async function fetchComplianceControls(params?: {
  framework_id?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceControl>> {
  const qs = new URLSearchParams();
  if (params?.framework_id) qs.set("framework_id", params.framework_id);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString();
  return api.get(`/compliance/controls${query ? `?${query}` : ""}`);
}

export async function fetchComplianceAssessments(params?: {
  framework_id?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceAssessment>> {
  const qs = new URLSearchParams();
  if (params?.framework_id) qs.set("framework_id", params.framework_id);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString();
  return api.get(`/compliance/assessments${query ? `?${query}` : ""}`);
}

export async function fetchComplianceFindings(params?: {
  assessment_id?: string;
  status?: string;
  severity?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceFinding>> {
  const qs = new URLSearchParams();
  if (params?.assessment_id) qs.set("assessment_id", params.assessment_id);
  if (params?.status) qs.set("status", params.status);
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString();
  return api.get(`/compliance/findings${query ? `?${query}` : ""}`);
}

export async function fetchComplianceExceptions(params?: {
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceException>> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString();
  return api.get(`/compliance/exceptions${query ? `?${query}` : ""}`);
}

export async function fetchComplianceEvidence(params?: {
  framework?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceEvidence>> {
  const qs = new URLSearchParams();
  if (params?.framework) qs.set("framework", params.framework);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString();
  return api.get(`/compliance/evidence${query ? `?${query}` : ""}`);
}

export async function fetchComplianceScan(): Promise<ComplianceScanResult> {
  return api.post<ComplianceScanResult>("/compliance/scan");
}
