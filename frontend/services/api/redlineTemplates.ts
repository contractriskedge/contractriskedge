/**
 * Redline Template API service.
 */
import { api } from "@/services/api/client";

export interface RedlineTemplate {
  template_id: string;
  tenant_id: string;
  name: string;
  clause_type: string;
  category: string;
  jurisdiction: string | null;
  industry: string | null;
  language: string;
  risk_level: string | null;
  template_text: string;
  variables: Record<string, unknown> | null;
  version: number;
  status: string;
  playbook_id: string | null;
  usage_count: number;
  accept_rate: number;
  created_by: string | null;
  approved_by: string | null;
  effective_date: string | null;
  retired_date: string | null;
  last_used: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface CoverageItem {
  clause_type: string;
  total_findings: number;
  templates_available: number;
  active_templates: number;
  coverage_pct: number;
  status: "covered" | "partial" | "missing";
}

export interface CoverageResponse {
  total_findings: number;
  total_templates: number;
  templates_used: number;
  templates_missing: number;
  coverage_pct: number;
  by_clause_type: CoverageItem[];
}

export interface MissingTemplate {
  clause_type: string;
  findings: number;
  first_seen: string;
  last_seen: string;
}

export interface AIDraftRequest {
  clause_type: string;
  finding_title: string;
  finding_description: string;
  jurisdiction?: string;
  industry?: string;
  risk_level?: string;
}

export interface AIDraftResponse {
  draft_text: string;
  clause_type: string;
  confidence: number;
  model_used: string;
}

export interface TemplateCreateRequest {
  name: string;
  clause_type: string;
  category: string;
  jurisdiction?: string;
  industry?: string;
  language?: string;
  risk_level?: string;
  template_text: string;
  variables?: Record<string, unknown>;
  playbook_id?: string;
  created_by?: string;
}

export const redlineTemplateApi = {
  // Coverage
  getCoverage: () =>
    api.get<CoverageResponse>("/redline-templates/coverage"),

  getMissing: (limit = 20) =>
    api.get<MissingTemplate[]>(`/redline-templates/missing?limit=${limit}`),

  // Analytics
  getAnalytics: () =>
    api.get<{
      coverage: CoverageResponse;
      total_templates: number;
      total_usage: number;
      avg_accept_rate: number;
      by_status: Record<string, number>;
    }>("/redline-templates/analytics"),

  // CRUD
  list: (params?: { clause_type?: string; category?: string; status?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.clause_type) q.set("clause_type", params.clause_type);
    if (params?.category) q.set("category", params.category);
    if (params?.status) q.set("status", params.status);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    return api.get<RedlineTemplate[]>(`/redline-templates?${q.toString()}`);
  },

  get: (id: string) =>
    api.get<RedlineTemplate>(`/redline-templates/${id}`),

  create: (data: TemplateCreateRequest) =>
    api.post<RedlineTemplate>("/redline-templates", data),

  update: (id: string, data: Partial<TemplateCreateRequest>) =>
    api.patch<RedlineTemplate>(`/redline-templates/${id}`, data),

  delete: (id: string) =>
    api.delete(`/redline-templates/${id}`),

  // AI Draft
  generateDraft: (data: AIDraftRequest) =>
    api.post<AIDraftResponse>("/redline-templates/generate-draft", data),

  generateBatch: (items: AIDraftRequest[]) =>
    api.post<{ results: AIDraftResponse[]; errors: { clause_type: string; error: string }[]; total: number; succeeded: number; failed: number }>(
      "/redline-templates/generate-batch", { items }
    ),

  promoteToTemplate: (data: {
    draft_text: string;
    name: string;
    clause_type: string;
    category: string;
    jurisdiction?: string;
    industry?: string;
    risk_level?: string;
  }) => api.post<RedlineTemplate>("/redline-templates/promote-ai-template", data),

  // Usage
  recordUsage: (id: string, accepted = true) =>
    api.post(`/redline-templates/${id}/use?accepted=${accepted}`),
};
