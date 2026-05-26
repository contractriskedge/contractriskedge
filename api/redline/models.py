"""Pydantic models for redline suggestion data structures.

Defines all data models used by the redline engine including request/
response schemas, clause type enumerations, and status tracking models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ClauseType(str, Enum):
    """Supported clause types for redline suggestions."""

    LIABILITY_CAPS = "liability_caps"
    INDEMNIFICATION = "indemnification"
    IP_OWNERSHIP = "ip_ownership"
    PAYMENT_TERMS = "payment_terms"
    GOVERNING_LAW = "governing_law"
    TERMINATION_RIGHTS = "termination_rights"
    CONFIDENTIALITY = "confidentiality"
    FORCE_MAJEURE = "force_majeure"

    def __str__(self) -> str:
        return self.value


class ChangeType(str, Enum):
    """Type of change in a redline suggestion."""

    INSERTION = "insertion"
    DELETION = "deletion"
    MODIFICATION = "modification"
    REWRITE = "rewrite"

    def __str__(self) -> str:
        return self.value


class PartyRole(str, Enum):
    """Role of the party in the contract relationship."""

    BUYER = "buyer"
    SELLER = "seller"
    SERVICE_PROVIDER = "service_provider"
    CLIENT = "client"
    LICENSEE = "licensee"
    LICENSOR = "licensor"
    EMPLOYER = "employer"
    CONTRACTOR = "contractor"
    DISTRIBUTOR = "distributor"
    SUPPLIER = "supplier"

    def __str__(self) -> str:
        return self.value


class DealSizeTier(str, Enum):
    """Deal size tiers for benchmark comparison."""

    SMALL = "small"  # < $100K
    MEDIUM = "medium"  # $100K - $1M
    LARGE = "large"  # $1M - $10M
    ENTERPRISE = "enterprise"  # $10M - $100M
    MEGA = "mega"  # > $100M

    def __str__(self) -> str:
        return self.value


class Industry(str, Enum):
    """Industry classifications for contract analysis."""

    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIAL_SERVICES = "financial_services"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    ENERGY = "energy"
    REAL_ESTATE = "real_estate"
    TELECOMMUNICATIONS = "telecommunications"
    GOVERNMENT = "government"
    PHARMACEUTICALS = "pharmaceuticals"

    def __str__(self) -> str:
        return self.value


class CounterpartyAggressiveness(str, Enum):
    """Expected counterparty negotiation stance."""

    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"

    def __str__(self) -> str:
        return self.value


class RedlineSuggestion(BaseModel):
    """A single redline suggestion with original and proposed text.

    Represents a proposed change to a contract clause with the
    original text, suggested replacement, rationale, and metadata
    for tracking and review.
    """

    suggestion_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this suggestion",
    )
    contract_id: str = Field(
        ..., description="Identifier of the contract being reviewed"
    )
    clause_type: ClauseType = Field(
        ..., description="Type of clause being modified"
    )
    original_text: str = Field(
        ..., description="Original clause text from the contract"
    )
    proposed_text: str = Field(
        ..., description="AI-generated proposed replacement text"
    )
    change_type: ChangeType = Field(
        ..., description="Type of change being suggested"
    )
    word_diff: Optional[str] = Field(
        None, description="Word-level diff summary"
    )
    rationale: str = Field(
        ..., min_length=10,
        description="Legal rationale for the suggested change",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence score for this suggestion (0-1)",
    )
    attorney_review_required: bool = Field(
        default=True,
        description="Whether this change requires attorney review",
    )
    risk_impact: str = Field(
        default="medium",
        description="Risk impact: critical, high, medium, low",
    )
    status: str = Field(
        default="pending",
        description="Review status: pending, accepted, rejected, modified",
    )
    status_changed_at: Optional[datetime] = Field(
        None, description="When the status was last changed"
    )
    status_changed_by: Optional[str] = Field(
        None, description="User who changed the status"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this suggestion was created",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for extensibility",
    )

    @field_validator("rationale")
    @classmethod
    def rationale_min_length(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError("rationale must be at least 10 characters")
        return stripped

    @field_validator("original_text")
    @classmethod
    def original_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("original_text must not be empty")
        return v

    @field_validator("proposed_text")
    @classmethod
    def proposed_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("proposed_text must not be empty")
        return v


class RedlineRequest(BaseModel):
    """Request payload for generating a redline suggestion."""

    contract_id: str = Field(
        ..., description="Identifier of the contract"
    )
    clause_type: ClauseType = Field(
        ..., description="Type of clause to redline"
    )
    original_clause_text: str = Field(
        ..., min_length=10,
        description="The original clause text to be revised",
    )
    party_role: PartyRole = Field(
        ..., description="Your party's role in the contract"
    )
    deal_size_tier: DealSizeTier = Field(
        default=DealSizeTier.MEDIUM,
        description="Deal size tier for context",
    )
    industry: Industry = Field(
        default=Industry.TECHNOLOGY,
        description="Industry for context",
    )
    counterparty_aggressiveness: CounterpartyAggressiveness = Field(
        default=CounterpartyAggressiveness.MODERATE,
        description="Expected counterparty negotiation stance",
    )
    jurisdiction: str = Field(
        default="New York, USA",
        description="Governing law jurisdiction",
    )
    tenant_id: Optional[str] = Field(
        None, description="Tenant identifier"
    )
    user_id: Optional[str] = Field(
        None, description="User identifier"
    )

    @field_validator("original_clause_text")
    @classmethod
    def validate_clause_length(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError("Clause text must be at least 10 characters")
        if len(stripped) > 50_000:
            raise ValueError("Clause text exceeds maximum length of 50,000 characters")
        return stripped


class RedlineResponse(BaseModel):
    """Response payload for a redline suggestion request."""

    suggestion: RedlineSuggestion = Field(
        ..., description="The generated redline suggestion"
    )
    quality_checks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results of quality constraint checks",
    )
    processing_time_ms: int = Field(
        ..., description="Time taken to generate the suggestion in milliseconds"
    )
    model_version: str = Field(
        ..., description="Version of the redline model used"
    )
