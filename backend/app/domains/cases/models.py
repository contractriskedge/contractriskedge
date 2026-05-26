"""Task/Case management models — operational work management for remediation workflows."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.kernel.database.base import Base


class Case(Base):
    """A remediation case — groups findings, tasks, and actions around a contract or issue."""
    __tablename__ = "cases"

    case_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="open")  # open, in_progress, resolved, closed, archived
    priority = Column(Text, nullable=False, default="medium")  # critical, high, medium, low
    severity = Column(Text, nullable=True)  # Matches risk level

    # Related entities
    contract_id = Column(Text, nullable=True)
    review_id = Column(UUID, nullable=True)
    upload_id = Column(UUID, nullable=True)

    # Ownership
    assignee_id = Column(Text, nullable=True, index=True)
    created_by = Column(Text, nullable=False)

    # Metadata
    finding_ids = Column(JSONB, nullable=False, default=list)
    tags = Column(JSONB, nullable=False, default=list)
    metadata_json = Column(JSONB, nullable=True)

    # Dates
    due_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Task(Base):
    """An individual task within a case or standalone."""
    __tablename__ = "case_tasks"

    task_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID, nullable=False, index=True)
    tenant_id = Column(UUID, nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="todo")  # todo, in_progress, done, blocked, skipped
    priority = Column(Text, nullable=False, default="medium")

    assignee_id = Column(Text, nullable=True, index=True)
    created_by = Column(Text, nullable=False)

    due_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CaseComment(Base):
    """Comments on cases and tasks."""
    __tablename__ = "case_comments"

    comment_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID, nullable=False, index=True)
    tenant_id = Column(UUID, nullable=False)
    author_id = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    mentions = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
