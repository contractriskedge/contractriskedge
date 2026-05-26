"""Task/Case management schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(critical|high|medium|low)$")
    contract_id: Optional[str] = None
    review_id: Optional[str] = None
    upload_id: Optional[str] = None
    assignee_id: Optional[str] = None
    finding_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    due_at: Optional[datetime] = None


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(open|in_progress|resolved|closed|archived)$")
    priority: Optional[str] = Field(None, pattern="^(critical|high|medium|low)$")
    assignee_id: Optional[str] = None
    finding_ids: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    due_at: Optional[datetime] = None


class CaseResponse(BaseModel):
    case_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    severity: Optional[str] = None
    contract_id: Optional[str] = None
    review_id: Optional[str] = None
    upload_id: Optional[str] = None
    assignee_id: Optional[str] = None
    created_by: str
    finding_ids: list[str]
    tags: list[str]
    due_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    task_count: int = 0


class TaskCreate(BaseModel):
    case_id: str
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(critical|high|medium|low)$")
    assignee_id: Optional[str] = None
    due_at: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done|blocked|skipped)$")
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    due_at: Optional[datetime] = None


class TaskResponse(BaseModel):
    task_id: str
    case_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignee_id: Optional[str] = None
    created_by: str
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CaseCommentCreate(BaseModel):
    case_id: str
    body: str = Field(..., min_length=1, max_length=5000)
    mentions: list[str] = Field(default_factory=list)


class CaseCommentResponse(BaseModel):
    comment_id: str
    case_id: str
    author_id: str
    body: str
    mentions: list[str]
    created_at: datetime
