"""Workflow Builder Backend — drag/drop workflow definitions, SLA editors, escalation rules, approval trees, simulation.

The runtime semantics already exist in domains/workflows/runtime/.
This is the builder API that creates workflow definitions.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WorkflowNodeType(str, Enum):
    START = "start"
    END = "end"
    AI_ANALYSIS = "ai_analysis"
    HUMAN_REVIEW = "human_review"
    APPROVAL_GATE = "approval_gate"
    CONDITION = "condition"
    ESCALATION = "escalation"
    SLA_TIMER = "sla_timer"
    NOTIFICATION = "notification"
    EXPORT = "export"
    WEBHOOK = "webhook"
    SUB_WORKFLOW = "sub_workflow"


@dataclass
class WorkflowNode:
    """A node in a workflow definition."""
    node_id: str
    node_type: WorkflowNodeType
    label: str
    config: dict[str, Any] = field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0


@dataclass
class WorkflowEdge:
    """An edge connecting workflow nodes."""
    edge_id: str
    source_node_id: str
    target_node_id: str
    condition: str = ""  # Optional condition expression
    label: str = ""


@dataclass
class WorkflowTemplate:
    """A complete workflow template definition."""
    template_id: str
    name: str
    description: str
    version: str = "1.0.0"
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)
    sla_seconds: int = 86400  # 24 hours default
    tags: list[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class WorkflowBuilderService:
    """Backend service for the workflow builder UI.

    Provides:
    - Workflow template CRUD
    - Node/edge validation
    - SLA configuration
    - Escalation rule management
    - Approval tree configuration
    - AI review stage configuration
    - Simulation mode (validate workflow before activation)
    """

    _templates: dict[str, WorkflowTemplate] = field(default_factory=dict)

    def __post_init__(self):
        self._register_default_templates()

    def _register_default_templates(self) -> None:
        """Register default workflow templates."""
        self.save_template(WorkflowTemplate(
            template_id="standard_review",
            name="Standard Contract Review",
            description="Standard 3-stage review: AI Analysis → Procurement → Legal",
            nodes=[
                WorkflowNode(node_id="start", node_type=WorkflowNodeType.START, label="Contract Uploaded"),
                WorkflowNode(node_id="ai_analysis", node_type=WorkflowNodeType.AI_ANALYSIS, label="AI Risk Analysis"),
                WorkflowNode(node_id="procurement_review", node_type=WorkflowNodeType.HUMAN_REVIEW, label="Procurement Review"),
                WorkflowNode(node_id="legal_review", node_type=WorkflowNodeType.HUMAN_REVIEW, label="Legal Review"),
                WorkflowNode(node_id="approval", node_type=WorkflowNodeType.APPROVAL_GATE, label="Final Approval"),
                WorkflowNode(node_id="end", node_type=WorkflowNodeType.END, label="Completed"),
            ],
            edges=[
                WorkflowEdge(edge_id="e1", source_node_id="start", target_node_id="ai_analysis"),
                WorkflowEdge(edge_id="e2", source_node_id="ai_analysis", target_node_id="procurement_review"),
                WorkflowEdge(edge_id="e3", source_node_id="procurement_review", target_node_id="legal_review"),
                WorkflowEdge(edge_id="e4", source_node_id="legal_review", target_node_id="approval"),
                WorkflowEdge(edge_id="e5", source_node_id="approval", target_node_id="end"),
            ],
            sla_seconds=172800,  # 48 hours
            tags=["standard", "review"],
        ))

        self.save_template(WorkflowTemplate(
            template_id="high_risk_review",
            name="High-Risk Contract Review",
            description="Elevated review for high-risk contracts: AI → Procurement → Legal → Security → Executive",
            nodes=[
                WorkflowNode(node_id="start", node_type=WorkflowNodeType.START, label="Contract Uploaded"),
                WorkflowNode(node_id="ai_analysis", node_type=WorkflowNodeType.AI_ANALYSIS, label="AI Risk Analysis"),
                WorkflowNode(node_id="procurement", node_type=WorkflowNodeType.HUMAN_REVIEW, label="Procurement Review"),
                WorkflowNode(node_id="legal", node_type=WorkflowNodeType.HUMAN_REVIEW, label="Legal Review"),
                WorkflowNode(node_id="security", node_type=WorkflowNodeType.HUMAN_REVIEW, label="Security Review"),
                WorkflowNode(node_id="executive", node_type=WorkflowNodeType.APPROVAL_GATE, label="Executive Approval"),
                WorkflowNode(node_id="end", node_type=WorkflowNodeType.END, label="Completed"),
                WorkflowNode(node_id="escalation", node_type=WorkflowNodeType.ESCALATION, label="Escalation Path"),
            ],
            edges=[
                WorkflowEdge(edge_id="e1", source_node_id="start", target_node_id="ai_analysis"),
                WorkflowEdge(edge_id="e2", source_node_id="ai_analysis", target_node_id="procurement"),
                WorkflowEdge(edge_id="e3", source_node_id="procurement", target_node_id="legal"),
                WorkflowEdge(edge_id="e4", source_node_id="legal", target_node_id="security"),
                WorkflowEdge(edge_id="e5", source_node_id="security", target_node_id="executive"),
                WorkflowEdge(edge_id="e6", source_node_id="executive", target_node_id="end"),
                WorkflowEdge(edge_id="e7", source_node_id="legal", target_node_id="escalation", condition="sla_breached"),
            ],
            sla_seconds=345600,  # 96 hours
            tags=["high_risk", "review", "security"],
        ))

    def save_template(self, template: WorkflowTemplate) -> None:
        """Save or update a workflow template."""
        self._templates[template.template_id] = template

    def get_template(self, template_id: str) -> WorkflowTemplate | None:
        """Get a workflow template."""
        return self._templates.get(template_id)

    def list_templates(self) -> list[dict[str, Any]]:
        """List all workflow templates."""
        return [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "version": t.version,
                "node_count": len(t.nodes),
                "edge_count": len(t.edges),
                "sla_hours": t.sla_seconds / 3600,
                "is_active": t.is_active,
                "tags": t.tags,
            }
            for t in self._templates.values()
        ]

    def delete_template(self, template_id: str) -> None:
        """Delete a workflow template."""
        self._templates.pop(template_id, None)

    def validate_workflow(self, template: WorkflowTemplate) -> list[str]:
        """Validate a workflow definition for correctness."""
        errors = []

        # Check for start node
        if not any(n.node_type == WorkflowNodeType.START for n in template.nodes):
            errors.append("Workflow must have a START node")

        # Check for end node
        if not any(n.node_type == WorkflowNodeType.END for n in template.nodes):
            errors.append("Workflow must have an END node")

        # Check for disconnected nodes
        node_ids = {n.node_id for n in template.nodes}
        connected = set()
        for edge in template.edges:
            connected.add(edge.source_node_id)
            connected.add(edge.target_node_id)
        disconnected = node_ids - connected
        if disconnected:
            errors.append(f"Disconnected nodes: {disconnected}")

        # Check for dangling edges
        edge_sources = {e.source_node_id for e in template.edges}
        edge_targets = {e.target_node_id for e in template.edges}
        dangling = edge_sources - node_ids | edge_targets - node_ids
        if dangling:
            errors.append(f"Dangling edges reference non-existent nodes: {dangling}")

        return errors

    def simulate_workflow(self, template: WorkflowTemplate) -> dict[str, Any]:
        """Simulate a workflow execution to validate behavior."""
        errors = self.validate_workflow(template)
        if errors:
            return {"valid": False, "errors": errors, "simulation": None}

        # Simple topological simulation
        path = []
        node_map = {n.node_id: n for n in template.nodes}
        edge_map: dict[str, list[str]] = {}
        for edge in template.edges:
            edge_map.setdefault(edge.source_node_id, []).append(edge.target_node_id)

        current = "start"
        visited = set()
        while current and current != "end":
            if current in visited:
                return {"valid": False, "errors": ["Cycle detected"], "simulation": None}
            visited.add(current)
            node = node_map.get(current)
            if node:
                path.append({"node_id": current, "node_type": node.node_type.value, "label": node.label})
            next_nodes = edge_map.get(current, [])
            current = next_nodes[0] if next_nodes else None

        if current == "end":
            path.append({"node_id": "end", "node_type": "end", "label": "Completed"})

        return {
            "valid": True,
            "errors": [],
            "simulation": {
                "path": path,
                "steps": len(path),
                "estimated_duration_hours": len(path) * 8,
            },
        }

    def get_builder_status(self) -> dict[str, Any]:
        """Get workflow builder status."""
        return {
            "total_templates": len(self._templates),
            "node_types": [t.value for t in WorkflowNodeType],
            "templates": self.list_templates(),
        }


# ── Global singleton ───────────────────────────────────────────────

workflow_builder = WorkflowBuilderService()
