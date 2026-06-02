"""Enterprise Coordination Graph — department dependencies, reviewer networks, vendor interactions, escalation propagation, organizational bottlenecks.

Enterprise operational topology — understanding how the organization actually works.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CoordinationNodeType(str, Enum):
    DEPARTMENT = "department"
    REVIEWER = "reviewer"
    VENDOR = "vendor"
    WORKFLOW = "workflow"
    ESCALATION_PATH = "escalation_path"
    BOTTLENECK = "bottleneck"


@dataclass
class CoordinationNode:
    """A node in the enterprise coordination graph."""
    node_id: str
    node_type: CoordinationNodeType
    name: str
    metrics: dict[str, float] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class CoordinationEdge:
    """An edge in the enterprise coordination graph."""
    source_id: str
    target_id: str
    relationship: str  # "depends_on", "collaborates_with", "escalates_to", "routes_to"
    weight: float = 1.0
    latency_hours: float = 0.0
    volume: int = 0


@dataclass
class CoordinationGraphService:
    """Enterprise coordination graph — maps how the organization operates.

    Tracks:
    - Department dependencies (who depends on whom)
    - Reviewer collaboration networks (who works with whom)
    - Vendor interaction networks (which vendors interact with which depts)
    - Escalation propagation (how escalations flow)
    - Organizational bottlenecks (where work gets stuck)
    - Negotiation influence paths (who influences whom)
    """

    _nodes: dict[str, CoordinationNode] = field(default_factory=dict)
    _edges: list[CoordinationEdge] = field(default_factory=list)

    def register_node(self, node: CoordinationNode) -> None:
        """Register a coordination graph node."""
        self._nodes[node.node_id] = node

    def register_edge(self, edge: CoordinationEdge) -> None:
        """Register a coordination graph edge."""
        self._edges.append(edge)

    def build_department_graph(self, departments: list[dict], dependencies: list[dict]) -> None:
        """Build department dependency graph."""
        for dept in departments:
            self.register_node(CoordinationNode(
                node_id=dept["id"],
                node_type=CoordinationNodeType.DEPARTMENT,
                name=dept["name"],
                metrics={"workload": dept.get("workload", 0), "capacity": dept.get("capacity", 0)},
            ))

        for dep in dependencies:
            self.register_edge(CoordinationEdge(
                source_id=dep["from_dept"],
                target_id=dep["to_dept"],
                relationship="depends_on",
                weight=dep.get("weight", 1.0),
                latency_hours=dep.get("avg_latency_hours", 0),
                volume=dep.get("volume", 0),
            ))

    def build_reviewer_network(self, reviewers: list[dict], collaborations: list[dict]) -> None:
        """Build reviewer collaboration network."""
        for r in reviewers:
            self.register_node(CoordinationNode(
                node_id=r["id"],
                node_type=CoordinationNodeType.REVIEWER,
                name=r["name"],
                metrics={
                    "workload": r.get("current_reviews", 0),
                    "capacity": r.get("max_capacity", 10),
                    "efficiency": r.get("efficiency_score", 1.0),
                },
            ))

        for collab in collaborations:
            self.register_edge(CoordinationEdge(
                source_id=collab["reviewer_a"],
                target_id=collab["reviewer_b"],
                relationship="collaborates_with",
                weight=collab.get("frequency", 1),
                volume=collab.get("shared_reviews", 0),
            ))

    def detect_bottlenecks(self) -> list[dict[str, Any]]:
        """Detect organizational bottlenecks from the coordination graph."""
        # Find nodes with high incoming dependency but low throughput
        incoming_volume: dict[str, int] = {}
        outgoing_volume: dict[str, int] = {}
        latencies: dict[str, list[float]] = {}

        for edge in self._edges:
            if edge.source_id not in outgoing_volume:
                outgoing_volume[edge.source_id] = 0
            if edge.target_id not in incoming_volume:
                incoming_volume[edge.target_id] = 0
            outgoing_volume[edge.source_id] += edge.volume
            incoming_volume[edge.target_id] += edge.volume
            if edge.target_id not in latencies:
                latencies[edge.target_id] = []
            latencies[edge.target_id].append(edge.latency_hours)

        bottlenecks = []
        for node_id, node in self._nodes.items():
            in_v = incoming_volume.get(node_id, 0)
            out_v = outgoing_volume.get(node_id, 0)
            avg_lat = sum(latencies.get(node_id, [0])) / max(len(latencies.get(node_id, [1])), 1)
            throughput_ratio = out_v / max(in_v, 1)

            if throughput_ratio < 0.5 and in_v > 10:
                bottlenecks.append({
                    "node_id": node_id,
                    "name": node.name,
                    "type": node.node_type.value,
                    "incoming_volume": in_v,
                    "outgoing_volume": out_v,
                    "throughput_ratio": round(throughput_ratio, 4),
                    "avg_latency_hours": round(avg_lat, 1),
                    "severity": "critical" if throughput_ratio < 0.3 else "high",
                })

        return sorted(bottlenecks, key=lambda b: b["incoming_volume"], reverse=True)

    def find_escalation_paths(self) -> list[dict[str, Any]]:
        """Find common escalation propagation paths."""
        escalation_edges = [e for e in self._edges if e.relationship == "escalates_to"]
        paths = []
        for edge in escalation_edges:
            source = self._nodes.get(edge.source_id)
            target = self._nodes.get(edge.target_id)
            if source and target:
                paths.append({
                    "from": source.name,
                    "to": target.name,
                    "volume": edge.volume,
                    "avg_latency_hours": edge.latency_hours,
                })
        return sorted(paths, key=lambda p: p["volume"], reverse=True)

    def get_coordination_summary(self) -> dict[str, Any]:
        """Get coordination graph summary."""
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "departments": sum(1 for n in self._nodes.values() if n.node_type == CoordinationNodeType.DEPARTMENT),
            "reviewers": sum(1 for n in self._nodes.values() if n.node_type == CoordinationNodeType.REVIEWER),
            "bottlenecks": self.detect_bottlenecks(),
            "escalation_paths": self.find_escalation_paths(),
        }


# ── Global singleton ───────────────────────────────────────────────

coordination_graph = CoordinationGraphService()
