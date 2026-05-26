"""Workspace domain — dashboard views, action jobs, recommendation feedback, and user preferences.

This domain provides server-side persistence for:
- Dashboard views (widget layout, filters, template)
- Action jobs (async execution with status tracking)
- Recommendation feedback (accept/dismiss/snooze/resolve)
- User preferences (widget visibility, theme, density)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.kernel.database.base import Base


class DashboardView(Base):
    """Saved dashboard view configuration per user/tenant."""
    __tablename__ = "dashboard_views"

    view_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    user_id = Column(Text, nullable=False, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    layout_json = Column(JSONB, nullable=False, default=dict)
    filters_json = Column(JSONB, nullable=False, default=dict)
    template_id = Column(Text, nullable=True)
    is_default = Column(UUID, nullable=True, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ActionJob(Base):
    """Async action job with execution status tracking.

    Supports: assign, escalate, re-analyze, export, notify
    Status: pending, running, completed, failed, retrying
    """
    __tablename__ = "action_jobs"

    job_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    user_id = Column(Text, nullable=False)
    action_type = Column(Text, nullable=False)  # assign, escalate, re_analyze, export, notify
    status = Column(Text, nullable=False, default="pending")  # pending, running, completed, failed, retrying
    target_type = Column(Text, nullable=False)  # contract, finding, review, clause, batch
    target_ids = Column(JSONB, nullable=False, default=list)
    metadata_json = Column(JSONB, nullable=True)
    result_message = Column(Text, nullable=True)
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class RecommendationFeedback(Base):
    """User feedback on AI-generated recommendations.

    Tracks recommendation lifecycle for measuring AI value.
    """
    __tablename__ = "recommendation_feedback"

    feedback_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    user_id = Column(Text, nullable=False)
    recommendation_id = Column(Text, nullable=False, index=True)  # Matches frontend recommendation id
    status = Column(Text, nullable=False, default="pending")  # pending, accepted, dismissed, snoozed, resolved, auto_resolved
    snoozed_until = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
