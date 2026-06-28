"""Template Library Pydantic schemas — request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Clause ────────────────────────────────────────────────────────

class TemplateClauseCreate(BaseModel):
    clause_type: str = Field(..., max_length=100)
    title: str = Field(..., max_length=300)
    content: str
    category: Optional[str] = None
    risk_level: Optional[str] = None
    ai_rewrite_allowed: bool = False
    fallback_clause_id: Optional[str] = None
    is_required: bool = False
    is_conditional: bool = False
    condition_expression: Optional[str] = None
    display_order: int = 0
    change_summary: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class TemplateClauseUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    risk_level: Optional[str] = None
    ai_rewrite_allowed: Optional[bool] = None
    fallback_clause_id: Optional[str] = None
    is_required: Optional[bool] = None
    is_conditional: Optional[bool] = None
    condition_expression: Optional[str] = None
    display_order: Optional[int] = None
    status: Optional[str] = None
    change_summary: Optional[str] = None
    tags: Optional[list[str]] = None


class TemplateClauseResponse(BaseModel):
    id: str
    template_id: Optional[str] = None
    clause_type: str
    title: str
    content: str
    category: Optional[str] = None
    risk_level: Optional[str] = None
    ai_rewrite_allowed: bool = False
    fallback_clause_id: Optional[str] = None
    is_required: bool = False
    is_conditional: bool = False
    condition_expression: Optional[str] = None
    display_order: int
    status: str
    version: int
    change_summary: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    usage_count: int = 0
    contract_usage_count: int = 0
    tags: list[str] = Field(default_factory=list)
    created_by: str
    updated_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Clause Ref ────────────────────────────────────────────────────

class TemplateClauseRefCreate(BaseModel):
    clause_id: str
    clause_version: int = 1
    sort_order: int = 0
    is_required: bool = False
    condition_expression: Optional[str] = None
    fallback_clause_id: Optional[str] = None


class TemplateClauseRefResponse(BaseModel):
    id: str
    template_id: str
    template_version_id: str
    clause_id: str
    clause_version: int
    sort_order: int
    is_required: bool
    condition_expression: Optional[str] = None
    fallback_clause_id: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    clause_title: Optional[str] = None
    clause_type: Optional[str] = None
    risk_level: Optional[str] = None


# ── Clause Analytics ──────────────────────────────────────────────

class ClauseAnalytics(BaseModel):
    total_clauses: int = 0
    published_clauses: int = 0
    draft_clauses: int = 0
    most_used_clauses: list[TemplateClauseResponse] = Field(default_factory=list)
    highest_risk_clauses: list[TemplateClauseResponse] = Field(default_factory=list)
    deprecated_still_used: list[TemplateClauseResponse] = Field(default_factory=list)
    avg_ai_rewrite_rate: float = 0
    clauses_by_type: list[dict] = Field(default_factory=list)
    clauses_by_risk: list[dict] = Field(default_factory=list)


# ── Clause Dependency ─────────────────────────────────────────────

class ClauseDependencyInfo(BaseModel):
    clause_id: str
    clause_title: str
    template_count: int
    contract_count: int
    templates: list[dict] = Field(default_factory=list)
    can_delete: bool
    blocking_reasons: list[str] = Field(default_factory=list)


# ── Category ──────────────────────────────────────────────────────

class TemplateCategoryCreate(BaseModel):
    name: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=200)
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0


class TemplateCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class TemplateCategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int
    is_active: bool
    template_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Variable ──────────────────────────────────────────────────────

class TemplateVariableCreate(BaseModel):
    key: str = Field(..., max_length=200)
    label: str = Field(..., max_length=300)
    description: Optional[str] = None
    field_type: str = "text"
    default_value: Optional[str] = None
    options: list[str] = Field(default_factory=list)
    validation_rules: dict[str, Any] = Field(default_factory=dict)
    help_text: Optional[str] = None
    display_order: int = 0
    is_required: bool = False
    variable_source: str = "user_input"
    """user_input, system, calculated"""
    calculation_rule: Optional[str] = None
    """e.g. '{{EffectiveDate}} + 36 months' for calculated variables"""
    section: Optional[str] = None
    """Logical grouping — e.g. 'Parties', 'Dates', 'Financials', 'Legal'"""


class TemplateVariableResponse(BaseModel):
    id: str
    key: str
    label: str
    description: Optional[str] = None
    field_type: str
    default_value: Optional[str] = None
    options: list[Any] = Field(default_factory=list)
    validation_rules: dict[str, Any] = Field(default_factory=dict)
    help_text: Optional[str] = None
    display_order: int
    is_required: bool
    variable_source: str = "user_input"
    calculation_rule: Optional[str] = None
    section: Optional[str] = None


# ── Template Version ──────────────────────────────────────────────

class TemplateVersionCreate(BaseModel):
    version_number: int
    label: Optional[str] = None
    change_summary: Optional[str] = None
    variables: list[TemplateVariableCreate] = Field(default_factory=list)
    clause_refs: list[dict] = Field(default_factory=list)
    placeholder_content: Optional[str] = None
    file_name: Optional[str] = None


class TemplateVersionResponse(BaseModel):
    id: str
    template_id: str
    version_number: int
    label: Optional[str] = None
    change_summary: Optional[str] = None
    status: str
    variables: list[TemplateVariableResponse] = Field(default_factory=list)
    clause_refs: list[dict] = Field(default_factory=list)
    placeholder_content: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: str
    created_by: str
    created_at: Optional[str] = None


# ── Template ──────────────────────────────────────────────────────

class TemplateCreate(BaseModel):
    name: str = Field(..., max_length=300)
    description: Optional[str] = None
    category_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    owner: Optional[str] = None
    department: Optional[str] = None
    business_unit: Optional[str] = None
    default_workflow: Optional[str] = None
    # Optional initial version data
    version: Optional[TemplateVersionCreate] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[list[str]] = None
    owner: Optional[str] = None
    department: Optional[str] = None
    business_unit: Optional[str] = None
    default_workflow: Optional[str] = None
    status: Optional[str] = None


class TemplateListItem(BaseModel):
    """Lightweight list view — no version data."""
    id: str
    name: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    owner: Optional[str] = None
    department: Optional[str] = None
    business_unit: Optional[str] = None
    default_workflow: Optional[str] = None
    status: str
    current_version_number: Optional[int] = None
    current_version_label: Optional[str] = None
    usage_count: int
    is_favorite: bool
    created_by: str
    created_at: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None


class TemplateDetail(BaseModel):
    """Full template detail with versions."""
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[TemplateCategoryResponse] = None
    tags: list[str] = Field(default_factory=list)
    owner: Optional[str] = None
    department: Optional[str] = None
    business_unit: Optional[str] = None
    default_workflow: Optional[str] = None
    status: str
    current_version: Optional[TemplateVersionResponse] = None
    versions: list[TemplateVersionResponse] = Field(default_factory=list)
    usage_count: int
    is_favorite: bool
    created_by: str
    created_at: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None


# ── Generation ────────────────────────────────────────────────────

class ClauseSelectionItem(BaseModel):
    clause_id: str
    included: bool = True
    reason_removed: Optional[str] = None
    """Required if included=False and clause is mandatory."""
    notes: Optional[str] = None
    """Optional user notes for this clause."""


class GenerateContractRequest(BaseModel):
    template_id: str
    template_version_id: Optional[str] = None
    """Pinned template version — if omitted, uses current version at time of generation."""
    variable_values: dict[str, Any] = Field(default_factory=dict)
    clause_selections: list[ClauseSelectionItem] = Field(default_factory=list)
    title: Optional[str] = None
    preview_only: bool = False
    """If true, generates a preview without creating a contract record."""
    idempotency_key: Optional[str] = None
    """Prevents duplicate contract generation on retry."""
    status: str = "draft"
    """draft | finalized — draft allows resume, finalized locks the contract."""


class GenerateContractResponse(BaseModel):
    generated_contract_id: str = ""
    review_id: str = ""
    template_version_id: Optional[str] = None
    title: str
    status: str = "preview"
    variable_values: dict[str, Any] = Field(default_factory=dict)
    clause_selections: list[dict] = Field(default_factory=list)
    generated_docx_url: Optional[str] = None
    generated_pdf_url: Optional[str] = None
    document_version_id: Optional[str] = None
    upload_id: Optional[str] = None
    """Upload session id — ingestion is dispatched after commit."""
    preview_content: Optional[str] = None
    """Rendered text for preview mode."""
    created_at: Optional[str] = None
    is_draft: bool = False
    """True if this is a saved draft that can be resumed."""


# ── Drafts ────────────────────────────────────────────────────────

class DraftSummary(BaseModel):
    id: str
    template_id: str
    template_name: Optional[str] = None
    title: str
    status: str = "draft"
    step: int = 1
    """Which wizard step the user was on (0-4)."""
    variable_count: int = 0
    clause_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DraftDetail(BaseModel):
    id: str
    template_id: str
    template_version_id: Optional[str] = None
    title: str
    status: str = "draft"
    step: int = 1
    variable_values: dict[str, Any] = Field(default_factory=dict)
    clause_selections: list[dict] = Field(default_factory=list)
    created_by: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Validation ────────────────────────────────────────────────────

class ValidationIssue(BaseModel):
    severity: str  # error, warning
    message: str
    field: Optional[str] = None


class TemplateValidationResult(BaseModel):
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    placeholder_count: int = 0
    mapped_count: int = 0
    duplicate_count: int = 0
    unused_variables: list[str] = Field(default_factory=list)
    missing_placeholders: list[str] = Field(default_factory=list)


# ── Dependency Check ──────────────────────────────────────────────

class TemplateDependencyInfo(BaseModel):
    template_id: str
    template_name: str
    generated_contract_count: int
    last_used: Optional[str] = None
    can_archive: bool
    can_delete: bool
    blocking_reasons: list[str] = Field(default_factory=list)


# ── Favorite ──────────────────────────────────────────────────────

class FavoriteToggleResponse(BaseModel):
    template_id: str
    is_favorite: bool


# ── Usage History ─────────────────────────────────────────────────

class UsageHistoryResponse(BaseModel):
    id: str
    template_id: str
    template_name: Optional[str] = None
    action: str
    actor_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


# ── Dashboard Metrics ─────────────────────────────────────────────

class TemplateMetrics(BaseModel):
    total_templates: int = 0
    approved_templates: int = 0
    draft_templates: int = 0
    generated_this_month: int = 0
    most_used_templates: list[TemplateListItem] = Field(default_factory=list)
    top_categories: list[dict[str, Any]] = Field(default_factory=list)
    average_generation_time_ms: float = 0
    templates_never_used: int = 0
    obsolete_templates_in_use: int = 0


# ── Paginated Response ────────────────────────────────────────────

class PaginatedTemplateList(BaseModel):
    data: list[TemplateListItem]
    total: int
    page: int
    page_size: int


class PaginatedCategoryList(BaseModel):
    data: list[TemplateCategoryResponse]
    total: int


class PaginatedClauseList(BaseModel):
    data: list[TemplateClauseResponse]
    total: int


# ── Template Packages ─────────────────────────────────────────────

class PackageItemCreate(BaseModel):
    template_id: str
    display_order: int = 0
    is_required: bool = True


class PackageItemResponse(BaseModel):
    id: str
    package_id: str
    template_id: str
    display_order: int
    is_required: bool
    template_name: Optional[str] = None
    template_status: Optional[str] = None


class TemplatePackageCreate(BaseModel):
    name: str = Field(..., max_length=300)
    industry: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    icon: Optional[str] = None
    items: list[PackageItemCreate] = Field(default_factory=list)


class TemplatePackageUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    icon: Optional[str] = None
    is_published: Optional[bool] = None


class TemplatePackageResponse(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    description: Optional[str] = None
    version: int
    is_published: bool
    tags: list[str] = Field(default_factory=list)
    icon: Optional[str] = None
    items: list[PackageItemResponse] = Field(default_factory=list)
    template_count: int = 0
    created_by: str
    updated_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PaginatedPackageList(BaseModel):
    data: list[TemplatePackageResponse]
    total: int
