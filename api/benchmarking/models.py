"""Pydantic models for benchmark clauses and corpus metadata.

Defines the data structures used throughout the benchmarking module
for representing benchmark clauses, corpus metadata, scoring results,
and segmentation information.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ContractType(str, Enum):
    """Standardized contract type classifications."""

    SaaS_AGREEMENT = "saas_agreement"
    SOFTWARE_LICENSE = "software_license"
    PROFESSIONAL_SERVICES = "professional_services"
    EMPLOYMENT_AGREEMENT = "employment_agreement"
    NON_DISCLOSURE = "non_disclosure"
    SUPPLY_AGREEMENT = "supply_agreement"
    DISTRIBUTION_AGREEMENT = "distribution_agreement"
    PARTNERSHIP_AGREEMENT = "partnership_agreement"
    JOINT_VENTURE = "joint_venture"
    LOAN_AGREEMENT = "loan_agreement"
    LEASE_AGREEMENT = "lease_agreement"
    MERGER_AGREEMENT = "merger_agreement"
    SERVICE_LEVEL = "service_level"
    MASTER_SERVICES = "master_services"
    STATEMENT_OF_WORK = "statement_of_work"
    OTHER = "other"

    def __str__(self) -> str:
        return self.value


class IndustryCategory(str, Enum):
    """Industry categories for benchmark segmentation."""

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


class CounterpartyType(str, Enum):
    """Counterparty type classification."""

    ENTERPRISE = "enterprise"
    SMB = "smb"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"

    def __str__(self) -> str:
        return self.value


class BenchmarkClause(BaseModel):
    """A single benchmark clause entry in the corpus."""

    clause_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique clause identifier",
    )
    source_document_id: str = Field(
        ..., description="Original document identifier"
    )
    clause_type: str = Field(
        ..., description="Type of clause (e.g., 'liability_caps')"
    )
    clause_text: str = Field(
        ..., description="Anonymized clause text"
    )
    contract_type: ContractType = Field(
        ..., description="Type of contract this clause came from"
    )
    industry: IndustryCategory = Field(
        ..., description="Industry of the contract"
    )
    counterparty_type: CounterpartyType = Field(
        ..., description="Type of counterparty"
    )
    deal_size_range: Optional[str] = Field(
        None, description="Deal size range (e.g., '$1M-$10M')"
    )
    jurisdiction: Optional[str] = Field(
        None, description="Governing law jurisdiction"
    )
    quality_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Quality score from attorney review (0-1)",
    )
    is_attorney_reviewed: bool = Field(
        default=False,
        description="Whether this clause was attorney-reviewed",
    )
    favorability: Optional[str] = Field(
        None, description="Favorability: favorable, neutral, unfavorable"
    )
    embedding: Optional[List[float]] = Field(
        None, description="Semantic embedding vector"
    )
    ingested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this clause was added to the corpus",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    @field_validator("clause_text")
    @classmethod
    def clause_text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("clause_text must not be empty")
        return v

    @field_validator("quality_score")
    @classmethod
    def validate_quality_score(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("quality_score must be between 0 and 1")
        return v


class BenchmarkCorpusMetadata(BaseModel):
    """Metadata about the benchmark corpus."""

    total_clauses: int = Field(
        default=0, description="Total number of clauses in corpus"
    )
    total_documents: int = Field(
        default=0, description="Total number of source documents"
    )
    clause_type_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of clauses per clause type",
    )
    contract_type_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of clauses per contract type",
    )
    industry_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of clauses per industry",
    )
    counterparty_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of clauses per counterparty type",
    )
    avg_quality_score: float = Field(
        default=0.0, description="Average quality score across corpus"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the corpus was last updated",
    )
    version: str = Field(
        default="1.0.0", description="Corpus version identifier"
    )


class BenchmarkSegment(BaseModel):
    """A segment definition for benchmark filtering."""

    clause_type: str = Field(
        ..., description="Clause type filter"
    )
    contract_type: Optional[ContractType] = Field(
        None, description="Contract type filter"
    )
    industry: Optional[IndustryCategory] = Field(
        None, description="Industry filter"
    )
    counterparty_type: Optional[CounterpartyType] = Field(
        None, description="Counterparty type filter"
    )
    deal_size_range: Optional[str] = Field(
        None, description="Deal size range filter"
    )
    jurisdiction: Optional[str] = Field(
        None, description="Jurisdiction filter"
    )


class SegmentationResult(BaseModel):
    """Result of a segmentation query."""

    segment: BenchmarkSegment = Field(
        ..., description="The segment definition"
    )
    matching_clause_count: int = Field(
        ..., ge=0, description="Number of clauses matching this segment"
    )
    match_type: str = Field(
        ..., description="Match level: exact, partial, or general_fallback"
    )
    fallback_path: List[str] = Field(
        default_factory=list,
        description="Path of fallback segments tried",
    )


class DistributionStats(BaseModel):
    """Distribution statistics for a benchmark segment."""

    count: int = Field(..., ge=0, description="Number of data points")
    mean: float = Field(..., description="Mean value")
    median: float = Field(..., description="Median (P50) value")
    p25: float = Field(..., description="25th percentile")
    p75: float = Field(..., description="75th percentile")
    p05: float = Field(..., description="5th percentile")
    p95: float = Field(..., description="95th percentile")
    std_dev: float = Field(..., description="Standard deviation")
    min_value: float = Field(..., description="Minimum value")
    max_value: float = Field(..., description="Maximum value")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When these stats were computed",
    )


class BenchmarkScore(BaseModel):
    """Score result for a clause against benchmarks."""

    clause_id: str = Field(
        ..., description="Clause being scored"
    )
    clause_type: str = Field(
        ..., description="Type of clause"
    )
    percentile: float = Field(
        ..., ge=0.0, le=100.0,
        description="Percentile rank vs benchmark corpus",
    )
    distribution_stats: DistributionStats = Field(
        ..., description="Distribution stats for the matched segment"
    )
    segment: SegmentationResult = Field(
        ..., description="The segment used for comparison"
    )
    classification: str = Field(
        ..., description="favorable, at_market, or unfavorable"
    )
    classification_confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Confidence in the classification",
    )
    similar_clause_count: int = Field(
        ..., ge=0, description="Number of similar clauses in corpus"
    )
    scored_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the score was computed",
    )
