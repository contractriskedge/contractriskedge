"""Clause Intelligence Graph Scaling schemas — indexing, traversal, edge scoring, caching."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Graph Indexing ──────────────────────────────────────────────────


class GraphIndexConfig(BaseModel):
    """Configuration for clause graph indexing."""
    enabled: bool = True
    index_clause_types: list[str] = Field(default_factory=list)  # empty = all
    min_similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    max_nodes_per_type: int = Field(default=500, ge=10)
    rebuild_interval_hours: int = Field(default=24, ge=1)
    prune_orphaned_nodes: bool = True
    prune_unused_edges: bool = True


class GraphIndexStats(BaseModel):
    """Statistics about the graph index."""
    total_nodes: int = 0
    total_edges: int = 0
    indexed_clause_types: int = 0
    last_indexed_at: Optional[datetime] = None
    index_size_bytes: Optional[int] = None
    average_edges_per_node: float = 0.0
    node_type_distribution: dict[str, int] = Field(default_factory=dict)


# ── Traversal Limits ────────────────────────────────────────────────


class GraphTraversalConfig(BaseModel):
    """Configuration for graph traversal limits."""
    max_depth: int = Field(default=3, ge=1, le=10)
    max_breadth: int = Field(default=50, ge=1, le=500)
    max_results: int = Field(default=100, ge=1, le=1000)
    timeout_ms: int = Field(default=5000, ge=100, le=60000)
    min_edge_strength: float = Field(default=0.1, ge=0.0, le=1.0)
    restrict_by_tenant: bool = True


class TraversalResult(BaseModel):
    """Result of a graph traversal."""
    nodes: list[ClauseNodeSummary] = Field(default_factory=list)
    edges: list[ClauseEdgeSummary] = Field(default_factory=list)
    traversal_path: list[str] = Field(default_factory=list)
    total_nodes_visited: int = 0
    total_edges_traversed: int = 0
    depth_reached: int = 0
    truncated: bool = False
    duration_ms: float = 0.0


class ClauseNodeSummary(BaseModel):
    """Lightweight clause node for traversal results."""
    clause_id: str
    clause_type: str
    canonical_category: str = ""
    text_snippet: str = ""
    source: str = ""
    risk_score: Optional[float] = None
    severity: Optional[str] = None
    node_weight: float = 1.0


class ClauseEdgeSummary(BaseModel):
    """Lightweight clause edge for traversal results."""
    source_clause_id: str
    target_clause_id: str
    relationship_type: str
    strength: float = 1.0
    label: str = ""


# ── Edge Scoring ────────────────────────────────────────────────────


class EdgeScoreComponents(BaseModel):
    """Components that make up an edge score."""
    type_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    text_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_proximity: float = Field(default=0.0, ge=0.0, le=1.0)
    co_occurrence: float = Field(default=0.0, ge=0.0, le=1.0)
    negotiation_link: float = Field(default=0.0, ge=0.0, le=1.0)
    playbook_link: float = Field(default=0.0, ge=0.0, le=1.0)


class ScoredEdge(BaseModel):
    """An edge with scored relationship strength."""
    source_clause_id: str
    target_clause_id: str
    relationship_type: str
    overall_score: float = Field(ge=0.0, le=1.0)
    components: EdgeScoreComponents
    confidence: float = Field(ge=0.0, le=1.0)
    last_scored_at: Optional[datetime] = None


class EdgeScoringConfig(BaseModel):
    """Configuration for edge scoring weights."""
    type_similarity_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    text_similarity_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    risk_proximity_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    co_occurrence_weight: float = Field(default=0.1, ge=0.0, le=1.0)
    negotiation_link_weight: float = Field(default=0.1, ge=0.0, le=1.0)
    playbook_link_weight: float = Field(default=0.1, ge=0.0, le=1.0)
    decay_factor: float = Field(default=0.95, ge=0.0, le=1.0)  # multiplicative decay per month
    min_score_to_keep: float = Field(default=0.05, ge=0.0, le=1.0)


# ── Graph Cache Layer ───────────────────────────────────────────────


class GraphCacheConfig(BaseModel):
    """Configuration for the graph cache layer."""
    enabled: bool = True
    ttl_seconds: int = Field(default=300, ge=1, le=86400)  # 5 min default
    max_cached_graphs: int = Field(default=50, ge=1)
    invalidate_on_update: bool = True
    cache_warm_on_startup: bool = False


class GraphCacheStats(BaseModel):
    """Statistics about the graph cache."""
    cached_graphs: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    avg_build_time_ms: float = 0.0
    cache_size_bytes: Optional[int] = None
    oldest_cached: Optional[datetime] = None
    newest_cached: Optional[datetime] = None


# ── Graph Explainability ────────────────────────────────────────────


class GraphExplanation(BaseModel):
    """Explanation of why two clauses are related."""
    relationship_type: str
    primary_reason: str = ""
    supporting_factors: list[str] = Field(default_factory=list)
    score_breakdown: EdgeScoreComponents
    confidence: float = 0.0
    evidence_snippets: list[str] = Field(default_factory=list)


class GraphExplainabilityRequest(BaseModel):
    """Request to explain relationships in the clause graph."""
    clause_id: str
    max_relationships: int = Field(default=10, ge=1, le=50)
    min_strength: float = Field(default=0.3, ge=0.0, le=1.0)
    include_evidence: bool = True


class GraphExplainabilityResponse(BaseModel):
    """Explainability response for a clause's graph relationships."""
    clause_id: str
    clause_type: str
    text_snippet: str = ""
    relationships: list[ExplainedRelationship] = Field(default_factory=list)
    total_relationships: int = 0


class ExplainedRelationship(BaseModel):
    """A relationship with explanation."""
    target_clause_id: str
    target_clause_type: str
    target_text_snippet: str = ""
    relationship_type: str
    strength: float = 0.0
    explanation: GraphExplanation
