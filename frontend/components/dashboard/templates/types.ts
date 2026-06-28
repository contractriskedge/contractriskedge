/** Template Library — TypeScript types matching backend schemas. */

export interface TemplateCategory {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  icon?: string | null;
  display_order: number;
  is_active: boolean;
  template_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TemplateVariable {
  key: string;
  label: string;
  description?: string | null;
  field_type: string;
  default_value?: string | null;
  options?: string[];
  validation_rules?: Record<string, unknown>;
  display_order: number;
  is_required: boolean;
  variable_source?: string;
  calculation_rule?: string | null;
  section?: string | null;
  /** Extended field metadata for gold-standard UX */
  placeholder?: string | null;
  /** Unit label shown inside input (e.g. "days", "months") */
  unit_label?: string | null;
  /** Min/max length for text fields */
  min_length?: number | null;
  max_length?: number | null;
  /** Regex pattern for validation */
  pattern?: string | null;
  /** Pattern error message */
  pattern_message?: string | null;
  /** For select/choice fields */
  choices?: Array<{ value: string; label: string }> | null;
  /** Conditional display */
  depends_on?: { field: string; value: any } | null;
}

export interface TemplateVersion {
  id: string;
  template_id: string;
  version_number: number;
  label?: string | null;
  change_summary?: string | null;
  status: string;
  variables: TemplateVariable[];
  clause_refs?: Array<{
    clause_id: string;
    clause_version: number;
    sort_order: number;
    is_required: boolean;
  }>;
  placeholder_content?: string | null;
  file_name?: string | null;
  file_size_bytes?: number | null;
  mime_type: string;
  created_by: string;
  created_at?: string | null;
}

export interface TemplateListItem {
  id: string;
  name: string;
  description?: string | null;
  category_id?: string | null;
  category_name?: string | null;
  tags: string[];
  owner?: string | null;
  department?: string | null;
  business_unit?: string | null;
  default_workflow?: string | null;
  status: string;
  current_version_number?: number | null;
  current_version_label?: string | null;
  usage_count: number;
  is_favorite: boolean;
  created_by: string;
  created_at?: string | null;
  updated_by?: string | null;
  updated_at?: string | null;
}

export interface TemplateDetail {
  id: string;
  name: string;
  description?: string | null;
  category?: TemplateCategory | null;
  tags: string[];
  owner?: string | null;
  department?: string | null;
  business_unit?: string | null;
  default_workflow?: string | null;
  status: string;
  current_version?: TemplateVersion | null;
  versions: TemplateVersion[];
  usage_count: number;
  is_favorite: boolean;
  created_by: string;
  created_at?: string | null;
  updated_by?: string | null;
  updated_at?: string | null;
}

export interface GenerateContractRequest {
  template_id: string;
  variable_values: Record<string, unknown>;
  title?: string | null;
  preview_only?: boolean;
}

export interface GenerateContractResponse {
  generated_contract_id: string;
  review_id: string;
  title: string;
  status: string;
  variable_values: Record<string, unknown>;
  generated_docx_url?: string | null;
  generated_pdf_url?: string | null;
  document_version_id?: string | null;
  preview_content?: string | null;
  created_at?: string | null;
}

export interface TemplateMetrics {
  total_templates: number;
  approved_templates: number;
  draft_templates: number;
  generated_this_month: number;
  most_used_templates: TemplateListItem[];
  top_categories: Array<{ name: string; count: number }>;
  average_generation_time_ms: number;
}

export interface PaginatedTemplateList {
  data: TemplateListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PaginatedCategoryList {
  data: TemplateCategory[];
  total: number;
}

// ── Clause Types ─────────────────────────────────────────────────

export interface TemplateClause {
  id: string;
  template_id?: string | null;
  clause_type: string;
  title: string;
  content: string;
  category?: string | null;
  risk_level?: string | null;
  ai_rewrite_allowed: boolean;
  fallback_clause_id?: string | null;
  is_required: boolean;
  is_conditional: boolean;
  condition_expression?: string | null;
  display_order: number;
  status: string;
  version: number;
  change_summary?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  usage_count: number;
  contract_usage_count: number;
  tags: string[];
  created_by: string;
  updated_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TemplateClauseCreate {
  clause_type: string;
  title: string;
  content: string;
  category?: string | null;
  risk_level?: string | null;
  ai_rewrite_allowed?: boolean;
  fallback_clause_id?: string | null;
  is_required?: boolean;
  is_conditional?: boolean;
  condition_expression?: string | null;
  display_order?: number;
  change_summary?: string | null;
  tags?: string[];
}

export interface ClauseAnalytics {
  total_clauses: number;
  published_clauses: number;
  draft_clauses: number;
  most_used_clauses: TemplateClause[];
  highest_risk_clauses: TemplateClause[];
  deprecated_still_used: TemplateClause[];
  avg_ai_rewrite_rate: number;
  clauses_by_type: Array<{ type: string; count: number }>;
  clauses_by_risk: Array<{ level: string; count: number }>;
}

export interface ClauseDependencyInfo {
  clause_id: string;
  clause_title: string;
  template_count: number;
  contract_count: number;
  templates: Array<{ id: string; name: string }>;
  can_delete: boolean;
  blocking_reasons: string[];
}

export interface ClauseRef {
  id: string;
  template_id: string;
  template_version_id: string;
  clause_id: string;
  clause_version: number;
  sort_order: number;
  is_required: boolean;
  condition_expression?: string | null;
  fallback_clause_id?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  clause_title?: string | null;
  clause_type?: string | null;
  risk_level?: string | null;
}

export interface ValidationIssue {
  severity: 'error' | 'warning';
  message: string;
  field?: string | null;
}

export interface TemplateValidationResult {
  is_valid: boolean;
  issues: ValidationIssue[];
  placeholder_count: number;
  mapped_count: number;
  duplicate_count: number;
  unused_variables: string[];
  missing_placeholders: string[];
}

export interface TemplateDependencyInfo {
  template_id: string;
  template_name: string;
  generated_contract_count: number;
  last_used?: string | null;
  can_archive: boolean;
  can_delete: boolean;
  blocking_reasons: string[];
}

export interface PaginatedClauseList {
  data: TemplateClause[];
  total: number;
}

// ── Template Package Types ───────────────────────────────────────

export interface PackageItemCreate {
  template_id: string;
  display_order?: number;
  is_required?: boolean;
}

export interface PackageItem {
  id: string;
  package_id: string;
  template_id: string;
  display_order: number;
  is_required: boolean;
  template_name?: string | null;
  template_status?: string | null;
}

export interface TemplatePackage {
  id: string;
  name: string;
  industry?: string | null;
  description?: string | null;
  version: number;
  is_published: boolean;
  tags: string[];
  icon?: string | null;
  items: PackageItem[];
  template_count: number;
  created_by: string;
  updated_by?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TemplatePackageCreate {
  name: string;
  industry?: string | null;
  description?: string | null;
  tags?: string[];
  icon?: string | null;
  items?: PackageItemCreate[];
}

export interface PaginatedPackageList {
  data: TemplatePackage[];
  total: number;
}
