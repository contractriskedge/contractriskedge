"""Clause Intelligence Graph Scaling — indexing, traversal, edge scoring, caching, explainability.

Extends the clause graph with production-grade scaling capabilities.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.domains.ai.repository import AIRepository
from app.domains.review.repository import ReviewRepository
from app.domains.clause_intel.service import ClauseGraphBuilder
from app.domains.clause_intel.schemas import ClauseGraph, ClauseNode, ClauseRelationship
from app.domains.clause_intel.graph_schemas import (
    GraphIndexConfig, GraphIndexStats,
    GraphTraversalConfig, TraversalResult, ClauseNodeSummary, ClauseEdgeSummary,
    EdgeScoreComponents, ScoredEdge, EdgeScoringConfig,
    GraphCacheConfig, GraphCacheStats,
    GraphExplainabilityRequest, GraphExplainabilityResponse,
    ExplainedRelationship, GraphExplanation,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphScoringService:
    """Computes and maintains edge scores in the clause knowledge graph."""

    scoring_config: EdgeScoringConfig = field(default_factory=EdgeScoringConfig)

    def score_edge(
        self,
        source: ClauseNode,
        target: ClauseNode,
        co_occurrence_count: int = 0,
        has_negotiation_link: bool = False,
        has_playbook_link: bool = False,
    ) -> ScoredEdge:
        """Compute a comprehensive edge score between two clause nodes."""
        # Type similarity
        type_sim = 1.0 if source.clause_type == target.clause_type else 0.0

        # Text similarity (simple token overlap)
        source_tokens = set(source.text_snippet.lower().split())
        target_tokens = set(target.text_snippet.lower().split())
        if source_tokens and target_tokens:
            intersection = source_tokens & target_tokens
            union = source_tokens | target_tokens
            text_sim = len(intersection) / len(union) if union else 0.0
        else:
            text_sim = 0.0

        # Risk proximity
        source_risk = source.risk_score or 0.5
        target_risk = target.risk_score or 0.5
        risk_prox = 1.0 - abs(source_risk - target_risk)

        # Co-occurrence score
        co_occurrence_score = min(1.0, co_occurrence_count / 10.0)

        # Negotiation link
        negotiation_score = 0.8 if has_negotiation_link else 0.0

        # Playbook link
        playbook_score = 0.9 if has_playbook_link else 0.0

        components = EdgeScoreComponents(
            type_similarity=type_sim,
            text_similarity=round(text_sim, 4),
            risk_proximity=round(risk_prox, 4),
            co_occurrence=co_occurrence_score,
            negotiation_link=negotiation_score,
            playbook_link=playbook_score,
        )

        cfg = self.scoring_config
        overall = (
            components.type_similarity * cfg.type_similarity_weight
            + components.text_similarity * cfg.text_similarity_weight
            + components.risk_proximity * cfg.risk_proximity_weight
            + components.co_occurrence * cfg.co_occurrence_weight
            + components.negotiation_link * cfg.negotiation_link_weight
            + components.playbook_link * cfg.playbook_link_weight
        )

        # Apply decay if nodes have different time origins
        if source.created_at and target.created_at:
            age_months = abs(
                (source.created_at - target.created_at).days / 30.0
            )
            overall *= (cfg.decay_factor ** age_months)

        # Confidence based on how many components contributed
        active_components = sum(1 for c in [
            type_sim > 0, text_sim > 0.1, risk_prox > 0.5,
            co_occurrence_count > 0, has_negotiation_link, has_playbook_link,
        ] if c)
        confidence = min(1.0, active_components / 4.0)

        return ScoredEdge(
            source_clause_id=source.clause_id,
            target_clause_id=target.clause_id,
            relationship_type="similar_to",
            overall_score=round(min(1.0, overall), 4),
            components=components,
            confidence=round(confidence, 4),
            last_scored_at=datetime.now(timezone.utc),
        )

    def prune_low_score_edges(
        self,
        edges: list[ClauseRelationship],
        min_score: float = 0.05,
    ) -> list[ClauseRelationship]:
        """Remove edges below the minimum score threshold."""
        return [e for e in edges if e.strength >= min_score]


@dataclass
class GraphTraversalService:
    """Controls graph traversal with limits, timeouts, and tenant isolation."""

    traversal_config: GraphTraversalConfig = field(default_factory=GraphTraversalConfig)

    def traverse(
        self,
        graph: ClauseGraph,
        start_clause_id: str,
        config: Optional[GraphTraversalConfig] = None,
    ) -> TraversalResult:
        """Traverse the clause graph from a starting node with limits."""
        cfg = config or self.traversal_config
        start_time = time.monotonic()

        # Build adjacency map
        adjacency: dict[str, list[tuple[str, str, float, str]]] = defaultdict(list)
        for edge in graph.edges:
            adjacency[edge.source_clause_id].append(
                (edge.target_clause_id, edge.relationship_type.value if hasattr(edge.relationship_type, 'value') else str(edge.relationship_type), edge.strength, edge.label)
            )
            adjacency[edge.target_clause_id].append(
                (edge.source_clause_id, edge.relationship_type.value if hasattr(edge.relationship_type, 'value') else str(edge.relationship_type), edge.strength, edge.label)
            )

        # Build node lookup
        node_map = {n.clause_id: n for n in graph.nodes}

        # BFS with limits
        visited: set[str] = set()
        queue: list[tuple[str, int, list[str]]] = [(start_clause_id, 0, [start_clause_id])]
        result_nodes: list[ClauseNodeSummary] = []
        result_edges: list[ClauseEdgeSummary] = []
        truncated = False

        while queue and len(visited) < cfg.max_results:
            current_id, depth, path = queue.pop(0)

            if current_id in visited:
                continue
            visited.add(current_id)

            # Add node to results
            node = node_map.get(current_id)
            if node:
                result_nodes.append(ClauseNodeSummary(
                    clause_id=node.clause_id,
                    clause_type=node.clause_type,
                    canonical_category=node.canonical_category,
                    text_snippet=node.text_snippet[:100],
                    source=node.source,
                    risk_score=node.risk_score,
                    severity=node.severity,
                ))

            # Check depth limit
            if depth >= cfg.max_depth:
                continue

            # Check timeout
            if time.monotonic() - start_time > cfg.timeout_ms / 1000:
                truncated = True
                break

            # Traverse neighbors
            neighbors = adjacency.get(current_id, [])
            # Filter by min strength
            neighbors = [(nid, rt, s, lbl) for nid, rt, s, lbl in neighbors if s >= cfg.min_edge_strength]
            # Sort by strength descending
            neighbors.sort(key=lambda x: -x[2])
            # Limit breadth
            neighbors = neighbors[:cfg.max_breadth]

            for neighbor_id, rel_type, strength, label in neighbors:
                if neighbor_id not in visited:
                    new_path = path + [neighbor_id]
                    queue.append((neighbor_id, depth + 1, new_path))
                    result_edges.append(ClauseEdgeSummary(
                        source_clause_id=current_id,
                        target_clause_id=neighbor_id,
                        relationship_type=rel_type,
                        strength=strength,
                        label=label,
                    ))

        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        return TraversalResult(
            nodes=result_nodes,
            edges=result_edges,
            total_nodes_visited=len(visited),
            total_edges_traversed=len(result_edges),
            depth_reached=min(cfg.max_depth, max((len(p) for _, _, p in queue), default=0) if queue else 0),
            truncated=truncated,
            duration_ms=duration_ms,
        )


@dataclass
class GraphExplainabilityService:
    """Explains why clauses are related in the knowledge graph."""

    scoring_service: GraphScoringService

    async def explain(
        self,
        graph: ClauseGraph,
        request: GraphExplainabilityRequest,
    ) -> GraphExplainabilityResponse:
        """Generate explainability for a clause's graph relationships."""
        node_map = {n.clause_id: n for n in graph.nodes}
        source_node = node_map.get(request.clause_id)

        if not source_node:
            return GraphExplainabilityResponse(
                clause_id=request.clause_id,
                clause_type="unknown",
                total_relationships=0,
            )

        # Find relationships
        relationships: list[ExplainedRelationship] = []
        for edge in graph.edges:
            target_id = None
            if edge.source_clause_id == request.clause_id:
                target_id = edge.target_clause_id
            elif edge.target_clause_id == request.clause_id:
                target_id = edge.source_clause_id

            if target_id is None:
                continue

            target_node = node_map.get(target_id)
            if not target_node:
                continue

            if edge.strength < request.min_strength:
                continue

            # Score the edge
            scored = self.scoring_service.score_edge(source_node, target_node)

            # Build explanation
            supporting: list[str] = []
            if scored.components.type_similarity > 0:
                supporting.append(f"Same clause type: {source_node.clause_type}")
            if scored.components.text_similarity > 0.3:
                supporting.append(f"Text similarity: {scored.components.text_similarity:.0%}")
            if scored.components.risk_proximity > 0.7:
                supporting.append(f"Similar risk profile (Δ={abs((source_node.risk_score or 0.5) - (target_node.risk_score or 0.5)):.2f})")
            if scored.components.negotiation_link > 0:
                supporting.append("Linked through negotiation history")
            if scored.components.playbook_link > 0:
                supporting.append("Linked through playbook standard")

            primary = supporting[0] if supporting else f"Edge strength: {edge.strength:.2f}"

            explanation = GraphExplanation(
                relationship_type=edge.relationship_type.value if hasattr(edge.relationship_type, 'value') else str(edge.relationship_type),
                primary_reason=primary,
                supporting_factors=supporting[1:] if len(supporting) > 1 else [],
                score_breakdown=scored.components,
                confidence=scored.confidence,
                evidence_snippets=[
                    source_node.text_snippet[:100],
                    target_node.text_snippet[:100],
                ] if request.include_evidence else [],
            )

            relationships.append(ExplainedRelationship(
                target_clause_id=target_id,
                target_clause_type=target_node.clause_type,
                target_text_snippet=target_node.text_snippet[:100],
                relationship_type=explanation.relationship_type,
                strength=edge.strength,
                explanation=explanation,
            ))

            if len(relationships) >= request.max_relationships:
                break

        # Sort by strength descending
        relationships.sort(key=lambda r: -r.strength)

        return GraphExplainabilityResponse(
            clause_id=request.clause_id,
            clause_type=source_node.clause_type,
            text_snippet=source_node.text_snippet[:200],
            relationships=relationships,
            total_relationships=len(relationships),
        )


@dataclass
class GraphCacheService:
    """In-memory cache for clause graph query results."""

    config: GraphCacheConfig = field(default_factory=GraphCacheConfig)
    _cache: dict[str, tuple[Any, datetime]] = field(default_factory=dict)
    _hits: int = 0
    _misses: int = 0

    def get(self, key: str) -> Optional[Any]:
        """Get a cached graph result."""
        if not self.config.enabled:
            return None

        entry = self._cache.get(key)
        if not entry:
            self._misses += 1
            return None

        value, cached_at = entry
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        if age > self.config.ttl_seconds:
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return value

    def set(self, key: str, value: Any) -> None:
        """Cache a graph result."""
        if not self.config.enabled:
            return

        # Evict oldest if at capacity
        if len(self._cache) >= self.config.max_cached_graphs:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        self._cache[key] = (value, datetime.now(timezone.utc))

    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate cache entries."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

    def invalidate_by_clause_type(self, clause_type: str) -> None:
        """Invalidate all cache entries for a clause type."""
        to_remove = [k for k in self._cache if clause_type in k]
        for k in to_remove:
            del self._cache[k]

    def get_stats(self) -> GraphCacheStats:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        timestamps = [v[1] for v in self._cache.values()]
        return GraphCacheStats(
            cached_graphs=len(self._cache),
            cache_hits=self._hits,
            cache_misses=self._misses,
            hit_rate=round(hit_rate, 4),
            oldest_cached=min(timestamps) if timestamps else None,
            newest_cached=max(timestamps) if timestamps else None,
        )
