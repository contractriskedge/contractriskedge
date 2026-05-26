"""Workspace Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Dashboard Views ──────────────────────────────────────────────

class DashboardViewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    layout_json: dict = Field(default_factory=dict)
    filters_json: dict = Field(default_factory=dict)
    template_id: Optional[str] = None


class DashboardViewUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    layout_json: Optional[dict] = None
    filters_json: Optional[dict] = None
    template_id: Optional[str] = None


class DashboardViewResponse(BaseModel):
    view_id: str
    name: str
    description: Optional[str] = None
    layout_json: dict
    filters_json: dict
    template_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Action Jobs ──────────────────────────────────────────────────

class ActionJobCreate(BaseModel):
    action_type: str = Field(..., pattern="^(assign|escalate|re_analyze|export|notify)$")
    target_type: str = Field(..., pattern="^(contract|finding|review|clause|batch)$")
    target_ids: list[str] = Field(default_factory=list)
    metadata_json: Optional[dict] = None


class ActionJobResponse(BaseModel):
    job_id: str
    action_type: str
    status: str
    target_type: str
    target_ids: list[str]
    progress: int = 0
    result_message: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ActionJobListResponse(BaseModel):
    jobs: list[ActionJobResponse]
    total: int


# ── Recommendation Feedback ──────────────────────────────────────

class RecommendationFeedbackCreate(BaseModel):
    recommendation_id: str
    status: str = Field(..., pattern="^(accepted|dismissed|snoozed|resolved)$")
    snoozed_until: Optional[datetime] = None
    note: Optional[str] = Field(None, max_length=1000)


class RecommendationFeedbackResponse(BaseModel):
    feedback_id: str
    recommendation_id: str
    status: str
    snoozed_until: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
