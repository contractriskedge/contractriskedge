"""Enterprise Memory Graph — unified persistent enterprise cognition that compounds over time.

Unifies org memory, coordination graph, and knowledge fabric into institutional intelligence accumulation.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MemoryNodeType(str, Enum):
    DECISION = "decision"
    WORKFLOW = "workflow"
    ESCALATION = "escalation"
    NEGOTIATION = "negotiation"
    OBLIGATION = "obligation"
    POLICY = "policy"
    VENDOR = "vendor"
    REVIEWER = "reviewer"
    CONTRACT = "contract"
    OUTCOME = "outcome"


class MemoryRelationshipType(str, Enum):
    LED_TO = "led_to"
    INFLUENCED = "influenced"
    RESOLVED = "resolved"
    PRECEDED = "preceded"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"
    OUTCOMES = "outcomes"


@dataclass
class MemoryGraphNode:
    """A node in the enterprise memory graph."""
    node_id: str
    node_type: MemoryNodeType
    label: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    properties: dict[str, Any] = field(default_factory=dict)
    significance: float = 1.0  # How significant is this memory (0.0-1.0)


@dataclass
class MemoryGraphEdge:
    """An edge in the enterprise memory graph."""
    source_id: str
    target_id: str
    relationship: MemoryRelationshipType
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryQuery:
    """A query against the enterprise memory graph."""
    query_type: str  # "decision_trace", "outcome_analysis", "influence_path"
    filters: dict[str, Any] = field(default_factory=dict)
    max_depth: int = 3
    min_significance: float = 0.0


@dataclass
class MemoryGraphService:
    """Enterprise memory graph — persistent institutional intelligence accumulation.

    Unifies:
    - Organizational memory (decisions, outcomes, lessons)
    - Coordination graph (dependencies, networks, bottlenecks)
    - Knowledge fabric (cross-domain reasoning, lineage, impact)

    Tracks:
    - Decisions and their outcomes
    - Workflow evolution and optimization
    - Escalation patterns and resolutions
    - Negotiation strategies and results
    - Obligation lifecycles
    - Policy changes and exceptions
    - Vendor relationships and risk
    - Reviewer performance patterns
    """

    _nodes: dict[str, MemoryGraphNode] = field(default_factory=dict)
    _edges: list[MemoryGraphEdge] = field(default_factory=list)

    def record_node(self, node: MemoryGraphNode) -> str:
        """Record a node in the memory graph."""
        if not node.node_id:
            node.node_id = str(uuid.uuid4())
        self._nodes[node.node_id] = node
        return node.node_id

    def record_edge(self, edge: MemoryGraphEdge) -> None:
        """Record an edge in the memory graph."""
        self._edges.append(edge)

    def record_decision(self, title: str, outcome: str, significance: float = 0.8) -> MemoryGraphNode:
        """Record a decision in the memory graph."""
        node = MemoryGraphNode(
            node_id=str(uuid.uuid4()),
            node_type=MemoryNodeType.DECISION,
            label=title,
            properties={"outcome": outcome},
            significance=significance,
        )
        self._nodes[node.node_id] = node
        return node

    def record_outcome(self, title: str, success: bool, significance: float = 0.7) -> MemoryGraphNode:
        """Record an outcome."""
        node = MemoryGraphNode(
            node_id=str(uuid.uuid4()),
            node_type=MemoryNodeType.OUTCOME,
            label=title,
            properties={"success": success},
            significance=significance,
        )
        self._nodes[node.node_id] = node
        return node

    def link_nodes(self, source_id: str, target_id: str, relationship: MemoryRelationshipType, weight: float = 1.0) -> None:
        """Link two nodes in the memory graph."""
        self._edges.append(MemoryGraphEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=weight,
        ))

    def query_memory(self, query: MemoryQuery) -> list[dict[str, Any]]:
        """Query the enterprise memory graph."""
        results = []
        for node in self._nodes.values():
            if node.significance < query.min_significance:
                continue

            # Apply filters
            match = True
            for key, value in query.filters.items():
                if key == "node_type" and node.node_type.value != value:
                    match = False
                if key == "label_contains" and value not in node.label:
                    match = False
            if not match:
                continue

            # Find related nodes
            related = []
            queue = [(node.node_id, 0)]
            visited = {node.node_id}
            while queue and len(related) < 20:
                current, depth = queue.pop(0)
                if depth >= query.max_depth:
                    continue
                for edge in self._edges:
                    neighbor = None
                    if edge.source_id == current:
                        neighbor = edge.target_id
                    elif edge.target_id == current:
                        neighbor = edge.source_id
                    if neighbor and neighbor not in visited:
                        visited.add(neighbor)
                        neighbor_node = self._nodes.get(neighbor)
                        if neighbor_node:
                            related.append({
                                "node_id": neighbor,
                                "label": neighbor_node.label,
                                "type": neighbor_node.node_type.value,
                                "relationship": edge.relationship.value,
                                "depth": depth + 1,
                            })
                        queue.append((neighbor, depth + 1))

            results.append({
                "node": {"id": node.node_id, "label": node.label, "type": node.node_type.value, "significance": node.significance},
                "related": related,
                "timestamp": node.timestamp,
            })

        return sorted(results, key=lambda r: r["node"]["significance"], reverse=True)

    def get_decision_trace(self, decision_id: str) -> dict[str, Any]:
        """Get the full trace of a decision — what led to it and what followed."""
        node = self._nodes.get(decision_id)
        if not node:
            return {"error": "Decision not found"}

        # What led to this decision
        predecessors = []
        for edge in self._edges:
            if edge.target_id == decision_id:
                source = self._nodes.get(edge.source_id)
                if source:
                    predecessors.append({"node": source.label, "type": source.node_type.value, "relationship": edge.relationship.value})

        # What followed from this decision
        successors = []
        for edge in self._edges:
            if edge.source_id == decision_id:
                target = self._nodes.get(edge.target_id)
                if target:
                    successors.append({"node": target.label, "type": target.node_type.value, "relationship": edge.relationship.value})

        return {
            "decision": {"id": node.node_id, "label": node.label, "type": node.node_type.value},
            "preceded_by": predecessors,
            "led_to": successors,
            "significance": node.significance,
            "timestamp": node.timestamp,
        }

    def find_similar_decisions(self, label: str, min_significance: float = 0.5) -> list[dict[str, Any]]:
        """Find similar decisions in the memory graph."""
        similar = []
        for node in self._nodes.values():
            if node.node_type == MemoryNodeType.DECISION and node.significance >= min_significance:
                if any(word in node.label.lower() for word in label.lower().split()):
                    similar.append({
                        "node_id": node.node_id,
                        "label": node.label,
                        "outcome": node.properties.get("outcome", "unknown"),
                        "significance": node.significance,
                    })
        return sorted(similar, key=lambda s: s["significance"], reverse=True)

    def get_memory_graph_summary(self) -> dict[str, Any]:
        """Get memory graph summary."""
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "by_type": {t.value: sum(1 for n in self._nodes.values() if n.node_type == t) for t in MemoryNodeType},
            "avg_significance": round(sum(n.significance for n in self._nodes.values()) / max(len(self._nodes), 1), 4),
            "total_decisions": sum(1 for n in self._nodes.values() if n.node_type == MemoryNodeType.DECISION),
            "total_outcomes": sum(1 for n in self._nodes.values() if n.node_type == MemoryNodeType.OUTCOME),
        }


# ── Global singleton ───────────────────────────────────────────────

memory_graph = MemoryGraphService()
