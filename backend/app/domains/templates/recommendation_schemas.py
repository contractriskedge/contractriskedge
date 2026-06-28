"""Clause Recommendation Engine — Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Rule CRUD Schemas ────────────────────────────────────────────

class RecommendationRuleCreate(BaseModel):
    """Create a new clause recommendation rule."""
    name: str = Field(..., max_length=300)
    description: Optional[str] = None
    priority: int = 0
    is_active: bool = True
    clause_id: str
    clause_version: int = 1
    recommendation_type: str = "recommended"  # required, recommended, optional
    variable_key: str = Field(..., max_length=200)
    operator: str = Field(..., max_length=20)  # =, !=, >, >=, <, <=, IN, NOT_IN, CONTAINS, BETWEEN, IS_EMPTY, IS_NOT_EMPTY, MATCHES
    condition_value: list[Any] = Field(default_factory=list)
    template_id: Optional[str] = None
    business_unit: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class RecommendationRuleUpdate(BaseModel):
    """Update an existing clause recommendation rule."""
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    clause_id: Optional[str] = None
    clause_version: Optional[int] = None
    recommendation_type: Optional[str] = None
    variable_key: Optional[str] = None
    operator: Optional[str] = None
    condition_value: Optional[list[Any]] = None
    template_id: Optional[str] = None
    business_unit: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class RecommendationRuleResponse(BaseModel):
    """Response model for a recommendation rule."""
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    priority: int
    is_active: bool
    clause_id: str
    clause_version: int
    recommendation_type: str
    variable_key: str
    operator: str
    condition_value: list[Any]
    template_id: Optional[str] = None
    business_unit: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    created_by: str
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedRuleResponse(BaseModel):
    """Paginated list of recommendation rules."""
    data: list[RecommendationRuleResponse]
    total: int
    page: int
    page_size: int


# ── Recommendation Evaluation Schemas ────────────────────────────

class RecommendationContext(BaseModel):
    """Context for evaluating recommendation rules.

    Decoupled from templates — works with any variable set.
    """
    variable_values: dict[str, Any] = Field(default_factory=dict)
    template_id: Optional[str] = None
    business_unit: Optional[str] = None
    tenant_id: Optional[str] = None  # Set from auth context on the server


class SuggestedClause(BaseModel):
    """A single clause suggested by the recommendation engine."""
    clause_id: str
    clause_title: str
    clause_type: str
    clause_content: str
    risk_level: Optional[str] = None
    recommendation_type: str  # required, recommended, optional
    reason: str
    rule_id: str
    rule_name: str
    is_checked: bool  # Pre-checked state based on recommendation_type


class RecommendationResult(BaseModel):
    """Result of evaluating recommendation rules."""
    suggested_clauses: list[SuggestedClause] = Field(default_factory=list)
    rules_evaluated: int = 0
    rules_matched: int = 0


class AcceptRejectClauses(BaseModel):
    """User's accept/reject decisions on suggested clauses."""
    review_id: Optional[str] = None
    generated_contract_id: Optional[str] = None
    accepted_clause_ids: list[str] = Field(default_factory=list)
    rejected_clause_ids: list[str] = Field(default_factory=list)
    suggested_clauses: list[SuggestedClause] = Field(default_factory=list)
