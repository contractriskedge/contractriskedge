"""Pydantic models for RAG pipeline data structures.

Defines the data types used throughout the retrieval-augmented
generation pipeline including search queries, retrieved chunks,
and complete RAG results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """A search query for the RAG pipeline."""

    query_text: str = Field(..., description="The search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    diversity_factor: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="MMR diversity factor (0=no diversity, 1=max diversity)",
    )
    category_filter: Optional[str] = Field(
        None, description="Optional risk category filter"
    )
    tenant_id: Optional[str] = Field(
        None, description="Tenant for namespace isolation"
    )
    min_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Minimum similarity score threshold",
    )
    metadata_filter: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata filters",
    )


class RetrievedChunk(BaseModel):
    """A single chunk retrieved from the vector store."""

    chunk_id: str = Field(..., description="Chunk identifier")
    text: str = Field(..., description="Chunk text content")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    rerank_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Re-ranking score if applied"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Chunk metadata"
    )
    contract_id: Optional[str] = Field(None, description="Source contract ID")
    clause_id: Optional[str] = Field(None, description="Source clause ID")
    page_number: Optional[int] = Field(None, ge=1, description="Source page number")
    section: Optional[str] = Field(None, description="Section heading")
    risk_category: Optional[str] = Field(
        None, description="Associated risk category"
    )


class RAGResult(BaseModel):
    """Complete result from a RAG retrieval operation."""

    query: SearchQuery = Field(..., description="The original search query")
    results: List[RetrievedChunk] = Field(
        ..., description="Retrieved and ranked chunks"
    )
    total_found: int = Field(..., ge=0, description="Total matching chunks found")
    retrieval_time_ms: float = Field(
        ..., ge=0, description="Retrieval time in milliseconds"
    )
    embedding_time_ms: float = Field(
        default=0.0, ge=0, description="Embedding generation time"
    )
    rerank_time_ms: float = Field(
        default=0.0, ge=0, description="Re-ranking time if applied"
    )
    query_embedding_model: str = Field(
        ..., description="Model used for query embedding"
    )
    has_reranked: bool = Field(
        default=False, description="Whether re-ranking was applied"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this result was generated",
    )
