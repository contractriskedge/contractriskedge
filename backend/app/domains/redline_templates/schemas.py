"""Pydantic schemas for RedlineTemplate API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RedlineTemplateCreate(BaseModel):
    name: str
    clause_type: str
    category: str
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    language: str = "en"
    risk_level: Optional[str] = None
    template_text: str
    variables: Optional[dict[str, Any]] = None
    playbook_id: Optional[UUID] = None
    created_by: Optional[str] = None


class RedlineTemplateUpdate(BaseModel):
    name: Optional[str] = None
    clause_type: Optional[str] = None
    category: Optional[str] = None
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    language: Optional[str] = None
    risk_level: Optional[str] = None
    template_text: Optional[str] = None
    variables: Optional[dict[str, Any]] = None
    status: Optional[str] = None
    approved_by: Optional[str] = None


class RedlineTemplateResponse(BaseModel):
    template_id: UUID
    tenant_id: UUID
    name: str
    clause_type: str
    category: str
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    language: str
    risk_level: Optional[str] = None
    template_text: str
    variables: Optional[dict[str, Any]] = None
    version: int
    status: str
    playbook_id: Optional[UUID] = None
    usage_count: int
    accept_rate: float
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    effective_date: Optional[datetime] = None
    retired_date: Optional[datetime] = None
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TemplateCoverageItem(BaseModel):
    clause_type: str
    total_findings: int
    templates_available: int
    coverage_pct: float
    status: str  # "covered", "partial", "missing"


class TemplateCoverageSummary(BaseModel):
    total_findings: int
    total_templates: int
    templates_used: int
    templates_missing: int
    coverage_pct: float
    by_clause_type: list[TemplateCoverageItem]


class AIDraftRequest(BaseModel):
    clause_type: str
    finding_title: str
    finding_description: str
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    risk_level: Optional[str] = None


class AIDraftResponse(BaseModel):
    draft_text: str
    clause_type: str
    confidence: float
    model_used: str


class PromoteAITemplateRequest(BaseModel):
    draft_text: str
    name: str
    clause_type: str
    category: str
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    risk_level: Optional[str] = None
    created_by: Optional[str] = None
