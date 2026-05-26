"""Search and retrieval Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search query with optional filters."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query text")
    strategy: str = Field(default="hybrid", pattern="^(hybrid|vector|keyword)$")
    filters: Optional[dict] = Field(default=None, description="Metadata filters")
    clause_type: Optional[str] = Field(default=None, description="Filter by clause type")
    contract_id: Optional[str] = Field(default=None, description="Scope search to a contract")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchResultItem(BaseModel):
    """A single search result item with citation metadata."""
    chunk_id: str
    contract_id: Optional[str] = None
    contract_name: Optional[str] = None
    upload_id: Optional[str] = None
    page_numbers: list[int] = Field(default_factory=list)
    section_heading: Optional[str] = None
    clause_type: Optional[str] = None
    snippet: str
    score: float
    strategy: str  # 'vector', 'bm25', 'hybrid'
    token_count: int = 0


class SearchResponse(BaseModel):
    """Search response with results, citations, and metadata."""
    results: list[SearchResultItem]
    total: int
    page: int
    page_size: int
    query: str
    strategy: str
    latency_ms: int


class AutocompleteRequest(BaseModel):
    """Autocomplete query."""
    prefix: str = Field(..., min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=50)


class AutocompleteItem(BaseModel):
    text: str
    type: str  # 'query', 'contract', 'clause_type'
    score: float


class AutocompleteResponse(BaseModel):
    suggestions: list[AutocompleteItem]


class SearchSuggestion(BaseModel):
    """A suggested search query with context."""
    query: str
    description: str
    category: str  # 'risk', 'compliance', 'renewal', 'missing_clause', 'portfolio'
    result_count: int = 0
    severity: str = "info"  # 'critical', 'warning', 'info', 'success'


class DiscoveryInsight(BaseModel):
    """An AI-generated insight about the contract portfolio."""
    type: str = "pattern"  # 'risk', 'anomaly', 'pattern', 'recommendation', 'compliance'
    title: str
    description: str
    severity: str = "info"
    confidence: float = 0.0
    impact: str = "medium"  # 'high', 'medium', 'low'
    entities: list[str] = Field(default_factory=list)
    suggested_query: Optional[str] = None
    finding_count: int = 0


class SearchPulseResponse(BaseModel):
    """Portfolio-level search intelligence returned on page load."""
    total_chunks: int = 0
    total_contracts: int = 0
    total_findings: int = 0
    avg_risk_score: Optional[float] = None
    queries_today: int = 0
    popular_queries: list[dict] = Field(default_factory=list)
    suggestions: list[SearchSuggestion] = Field(default_factory=list)
    insights: list[DiscoveryInsight] = Field(default_factory=list)
