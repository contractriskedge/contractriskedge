"""Clause Recommendation Rule ORM model — tenant-isolated, versioned, auditable.

Each rule defines a condition (based on template variables) that, when matched,
suggests a clause from the clause library for inclusion in the generated contract.

Rules are decoupled from templates — they evaluate against any contract context
(variables, metadata, AI-extracted fields), making them reusable across:
- Create from Template
- Upload Existing Contract (after AI extraction)
- Future metadata import
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.database.session import Base

import enum


class RecommendationType(str, enum.Enum):
    """How strongly a clause is recommended."""
    REQUIRED = "required"        # Must be included, cannot be unchecked
    RECOMMENDED = "recommended"  # Pre-checked, user can opt out
    OPTIONAL = "optional"        # Unchecked by default, user can opt in


class ConditionOperator(str, enum.Enum):
    """Supported operators for rule conditions."""
    EQ = "="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    IN = "IN"
    NOT_IN = "NOT_IN"
    CONTAINS = "CONTAINS"
    BETWEEN = "BETWEEN"
    IS_EMPTY = "IS_EMPTY"
    IS_NOT_EMPTY = "IS_NOT_EMPTY"
    MATCHES = "MATCHES"  # Regex match


class ClauseRecommendationRule(Base):
    """A rule that recommends a clause based on variable values."""

    __tablename__ = "clause_recommendation_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Rule metadata
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # The clause to recommend (from clause library — stored as string ID, validated at app level)
    clause_id: Mapped[str] = mapped_column(String(36), nullable=False)
    clause_version: Mapped[int] = mapped_column(Integer, default=1)

    # Recommendation strength
    recommendation_type: Mapped[str] = mapped_column(
        String(20), default="recommended",
    )  # required, recommended, optional

    # Condition: variable key + operator + value(s)
    variable_key: Mapped[str] = mapped_column(String(200), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    # For single values: ["value"]; for IN/BETWEEN: ["val1", "val2"]
    condition_value: Mapped[dict] = mapped_column(JSONB, default=list)

    # Optional template scope — if set, rule only applies to this template
    # If null, rule applies to all templates (decoupled)
    template_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
    )

    # Optional business unit scope
    business_unit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Effective dating
    effective_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    effective_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Audit
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_recommendation_rules_tenant_active", "tenant_id", "is_active"),
        Index("ix_recommendation_rules_variable", "tenant_id", "variable_key"),
    )


class RecommendationAudit(Base):
    """Audit trail for clause recommendations — what was suggested and what the user decided."""

    __tablename__ = "clause_recommendation_audit"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Context
    review_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("contract_reviews.review_id", ondelete="CASCADE"),
        nullable=True,
    )
    generated_contract_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("generated_contracts.id", ondelete="CASCADE"),
        nullable=True,
    )
    template_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("contract_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # What was evaluated
    variable_values: Mapped[dict] = mapped_column(JSONB, default=dict)
    rules_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    rules_matched: Mapped[int] = mapped_column(Integer, default=0)

    # What was suggested and what the user did
    suggested_clauses: Mapped[dict] = mapped_column(JSONB, default=list)
    # [{clause_id, clause_title, recommendation_type, reason, accepted}]
    accepted_clause_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    rejected_clause_ids: Mapped[dict] = mapped_column(JSONB, default=list)

    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_recommendation_audit_review", "review_id"),
        Index("ix_recommendation_audit_tenant_created", "tenant_id", "created_at"),
    )
