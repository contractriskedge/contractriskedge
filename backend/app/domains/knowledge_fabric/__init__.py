"""Enterprise Knowledge Fabric — cross-domain reasoning, relationship traversal, operational lineage, dependency mapping, impact analysis.

Unified enterprise cognition infrastructure — connects contracts, workflows, reviewers, obligations, vendors, escalations, decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DomainType(str, Enum):
    CONTRACT = "contract"
    WORKFLOW = "workflow"
    REVIEWER = "reviewer"
    OBLIGATION = "obligation"
    VENDOR = "vendor"
    ESCALATION = "escalation"
    DECISION = "decision"
    POLICY = "policy"
    FINDING = "finding"


@dataclass
class KnowledgeNode:
    """A node in the enterprise knowledge fabric."""
    node_id: str
    domain: DomainType
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class KnowledgeRelationship:
    """A relationship between knowledge fabric nodes."""
    source_id: str
    target_id: str
    relationship_type: str
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImpactAnalysis:
    """Result of an impact analysis query."""
    affected_nodes: list[dict[str, Any]] = field(default_factory=list)
    impact_score: float = 0.0
    propagation_depth: int = 0
    critical_paths: list[list[str]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class KnowledgeFabricService:
    """Enterprise knowledge fabric — unified cross-domain reasoning infrastructure.

    Capabilities:
    - Cross-domain reasoning (connect contracts to reviewers to decisions)
    - Relationship traversal (navigate the enterprise graph)
    - Operational lineage (trace how decisions were made)
    - Enterprise dependency mapping (who and what depends on what)
    - Impact analysis (what happens if X changes)
    """

    _nodes: dict[str, KnowledgeNode] = field(default_factory=dict)
    _relationships: list[KnowledgeRelationship] = field(default_factory=list)

    def register_node(self, node: KnowledgeNode) -> None:
        """Register a knowledge fabric node."""
        self._nodes[node.node_id] = node

    def register_relationship(self, rel: KnowledgeRelationship) -> None:
        """Register a knowledge fabric relationship."""
        self._relationships.append(rel)

    def find_related(self, node_id: str, max_depth: int = 2) -> list[dict[str, Any]]:
        """Find all related nodes within a given depth."""
        visited = {node_id}
        queue = [(node_id, 0)]
        related = []

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for rel in self._relationships:
                neighbor = None
                if rel.source_id == current:
                    neighbor = rel.target_id
                elif rel.target_id == current:
                    neighbor = rel.source_id

                if neighbor and neighbor not in visited:
                    visited.add(neighbor)
                    node = self._nodes.get(neighbor)
                    if node:
                        related.append({
                            "node_id": neighbor,
                            "domain": node.domain.value,
                            "label": node.label,
                            "relationship": rel.relationship_type,
                            "depth": depth + 1,
                        })
                    queue.append((neighbor, depth + 1))

        return related

    def analyze_impact(self, node_id: str, change_description: str) -> ImpactAnalysis:
        """Analyze the impact of changing a node."""
        affected = self.find_related(node_id, max_depth=3)
        node = self._nodes.get(node_id)

        # Calculate impact score based on connectedness
        direct = [a for a in affected if a["depth"] == 1]
        indirect = [a for a in affected if a["depth"] > 1]
        impact_score = min(1.0, (len(direct) * 0.15 + len(indirect) * 0.05))

        # Find critical paths
        critical_paths = []
        for a in affected[:5]:
            path = [node_id, a["node_id"]]
            critical_paths.append(path)

        recommendations = []
        if impact_score > 0.5:
            recommendations.append(f"High impact: {len(direct)} direct dependencies affected")
            recommendations.append("Consider phased rollout to minimize disruption")
        if any(a["domain"] == "workflow" for a in affected):
            recommendations.append("Verify workflow integrity after change")

        return ImpactAnalysis(
            affected_nodes=affected,
            impact_score=round(impact_score, 4),
            propagation_depth=max(a["depth"] for a in affected) if affected else 0,
            critical_paths=critical_paths,
            recommendations=recommendations,
        )

    def get_lineage(self, node_id: str) -> list[dict[str, Any]]:
        """Get the operational lineage of a node — how it came to be."""
        lineage = []
        visited = {node_id}
        queue = [(node_id, 0, "self")]

        while queue:
            current, depth, rel_type = queue.pop(0)
            node = self._nodes.get(current)
            if node:
                lineage.append({
                    "node_id": current,
                    "domain": node.domain.value,
                    "label": node.label,
                    "relationship": rel_type,
                    "depth": depth,
                })

            if depth >= 3:
                continue

            for rel in self._relationships:
                if rel.target_id == current and rel.source_id not in visited:
                    visited.add(rel.source_id)
                    queue.append((rel.source_id, depth + 1, rel.relationship_type))

        return sorted(lineage, key=lambda x: x["depth"])

    def get_dependency_map(self, node_id: str) -> dict[str, Any]:
        """Get the dependency map for a node — what depends on it."""
        dependents = [r for r in self._relationships if r.source_id == node_id]
        dependencies = [r for r in self._relationships if r.target_id == node_id]

        return {
            "node": self._nodes.get(node_id),
            "depends_on": [
                {"node": self._nodes.get(r.target_id), "relationship": r.relationship_type}
                for r in dependencies
            ],
            "depended_by": [
                {"node": self._nodes.get(r.target_id), "relationship": r.relationship_type}
                for r in dependents
            ],
        }

    def get_fabric_summary(self) -> dict[str, Any]:
        """Get knowledge fabric summary."""
        return {
            "total_nodes": len(self._nodes),
            "total_relationships": len(self._relationships),
            "by_domain": {
                d.value: sum(1 for n in self._nodes.values() if n.domain == d)
                for d in DomainType
            },
        }


# ── Global singleton ───────────────────────────────────────────────

knowledge_fabric = KnowledgeFabricService()
