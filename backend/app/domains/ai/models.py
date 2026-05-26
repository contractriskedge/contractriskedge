"""AI analysis domain — execution tracking, findings, redlines, prompts, and cache models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Text,
    BigInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base


class ExecutionStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"


class FindingSeverity(str, PyEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingType(str, PyEnum):
    RISK = "risk"
    CLASSIFICATION = "classification"
    OBLIGATION = "obligation"
    REDLINE = "redline"
    MISSING_CLAUSE = "missing_clause"


class AIExecutionRun(Base):
    """Tracks a complete AI analysis execution for a contract/upload session."""
    __tablename__ = "ai_execution_runs"

    run_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Text, nullable=True)

    analysis_type = Column(Text, nullable=False)  # 'full', 'risk_only', 'redline_only'
    status = Column(SAEnum("pending", "processing", "completed", "failed", "cancelled", "awaiting_approval", name="ai_exec_status", create_type=True), nullable=False, default=ExecutionStatus.PENDING)

    model = Column(Text, nullable=False)
    provider = Column(Text, nullable=False, default="openai")

    # Prompt version tracking for auditability and reproducibility
    prompt_version = Column(Integer, nullable=True, default=1)
    extraction_prompt_version = Column(Integer, nullable=True, default=1)
    analysis_prompt_version = Column(Integer, nullable=True, default=1)

    total_chunks = Column(Integer, nullable=False, default=0)
    chunks_used = Column(Integer, nullable=False, default=0)

    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    latency_ms = Column(Integer, nullable=True)

    risk_score = Column(Float, nullable=True)
    findings_count = Column(Integer, nullable=False, default=0)
    redlines_count = Column(Integer, nullable=False, default=0)

    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIExecutionStep(Base):
    """Individual step within an AI analysis execution."""
    __tablename__ = "ai_execution_steps"

    step_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID, ForeignKey("ai_execution_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    step_type = Column(Text, nullable=False)  # 'risk_analysis', 'clause_classify', 'obligation_extract', 'redline_gen'
    step_order = Column(Integer, nullable=False)
    status = Column(SAEnum("pending", "processing", "completed", "failed", "cancelled", "awaiting_approval", name="ai_step_status", create_type=True), nullable=False, default=ExecutionStatus.PENDING)

    prompt_text = Column(Text, nullable=True)
    response_text = Column(Text, nullable=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)

    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIFinding(Base):
    """A single finding from AI analysis — risk, classification, obligation, or missing clause."""
    __tablename__ = "ai_findings"

    finding_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID, ForeignKey("ai_execution_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    finding_type = Column(SAEnum("risk", "classification", "obligation", "redline", "missing_clause", name="finding_type", create_type=True), nullable=False)
    severity = Column(SAEnum("critical", "high", "medium", "low", "info", name="finding_severity", create_type=True), nullable=False)
    clause_type = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)

    confidence = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)

    chunk_ids = Column(ARRAY(UUID), nullable=False, default=list)
    clause_text = Column(Text, nullable=True)
    page_numbers = Column(ARRAY(Integer), nullable=False, default=list)

    status = Column(Text, nullable=False, default="open")  # 'open', 'acknowledged', 'resolved', 'dismissed'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIRedline(Base):
    """AI-generated redline suggestion with rationale and citations."""
    __tablename__ = "ai_redlines"

    redline_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID, ForeignKey("ai_execution_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    clause_type = Column(Text, nullable=True)
    original_text = Column(Text, nullable=False)
    proposed_text = Column(Text, nullable=False)
    operation = Column(Text, nullable=True)
    anchor_text = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)
    risk_level = Column(Text, nullable=True)

    confidence = Column(Float, nullable=True)
    chunk_ids = Column(ARRAY(UUID), nullable=False, default=list)
    page_numbers = Column(ARRAY(Integer), nullable=False, default=list)

    ai_metadata = Column("metadata", JSONB, nullable=True, default=dict)  # Traceability and other AI metadata

    status = Column(Text, nullable=False, default="proposed")  # 'proposed', 'accepted', 'rejected', 'modified'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIPromptVersion(Base):
    """Versioned prompt template registry."""
    __tablename__ = "ai_prompt_versions"

    version_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    prompt_key = Column(Text, nullable=False, index=True)  # 'risk_analysis', 'clause_classify'
    version = Column(Integer, nullable=False)
    template = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=True)
    model = Column(Text, nullable=True)
    temperature = Column(Float, nullable=True, default=0.1)
    max_tokens = Column(Integer, nullable=True, default=4096)
    response_schema = Column(JSONB, nullable=True)  # JSON Schema for structured output

    is_active = Column(Boolean, nullable=False, default=False)
    change_notes = Column(Text, nullable=True)
    created_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("prompt_key", "version", name="uq_ai_prompt_template_version"),
    )


class AICacheEntry(Base):
    """Cache for AI responses keyed by prompt hash — tenant-isolated."""
    __tablename__ = "ai_cache_entries"

    cache_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_hash = Column(Text, nullable=False, index=True)
    prompt_key = Column(Text, nullable=False)
    model = Column(Text, nullable=False)
    response = Column(JSONB, nullable=False)
    hit_count = Column(Integer, nullable=False, default=1)
    ttl_seconds = Column(Integer, nullable=False, default=3600)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class AIFailure(Base):
    """Records AI execution failures for monitoring."""
    __tablename__ = "ai_failures"

    failure_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID, ForeignKey("ai_execution_runs.run_id", ondelete="CASCADE"), nullable=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    failure_type = Column(Text, nullable=False)  # 'timeout', 'rate_limit', 'invalid_response', 'model_error'
    error_message = Column(Text, nullable=False)
    model_attempted = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
