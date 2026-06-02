"""Visual Workflow Studio — drag/drop workflow builder, SLA graph editor, escalation designer, AI stage configuration, simulation mode, approval graph visualization, policy binding UI.

Backend for the visual workflow builder — the runtime semantics already exist.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CanvasNodeType(str, Enum):
    START = "start"
    END = "end"
    AI_STAGE = "ai_stage"
    HUMAN_REVIEW = "human_review"
    APPROVAL_GATE = "approval_gate"
    CONDITION = "condition"
    ESCALATION = "escalation"
    SLA_TIMER = "sla_timer"
    NOTIFICATION = "notification"
    INTEGRATION = "integration"
    SUB_WORKFLOW = "sub_workflow"
    POLICY_BINDING = "policy_binding"


@dataclass
class CanvasNode:
    """A node on the visual workflow canvas."""
    node_id: str
    node_type: CanvasNodeType
    label: str
    x: float = 0.0
    y: float = 0.0
    width: float = 180.0
    height: float = 60.0
    config: dict[str, Any] = field(default_factory=dict)
    style: dict[str, Any] = field(default_factory=lambda: {"borderColor": "#4A90D9", "backgroundColor": "#F0F6FF"})


@dataclass
class CanvasEdge:
    """An edge connecting canvas nodes."""
    edge_id: str
    source_id: str
    target_id: str
    label: str = ""
    condition: str = ""
    style: dict[str, Any] = field(default_factory=lambda: {"stroke": "#999", "strokeWidth": 2})


@dataclass
class WorkflowCanvas:
    """A complete visual workflow canvas."""
    canvas_id: str
    name: str
    description: str
    nodes: list[CanvasNode] = field(default_factory=list)
    edges: list[CanvasEdge] = field(default_factory=list)
    version: str = "1.0.0"
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = ""


@dataclass
class VisualWorkflowStudio:
    """Backend for the visual workflow builder.

    Provides:
    - Canvas state management (nodes, edges, positions)
    - Node type catalog with configurations
    - Edge routing with conditions
    - SLA graph editor
    - Escalation designer
    - AI stage configuration
    - Policy binding UI
    - Approval graph visualization
    - Simulation integration
    """

    _canvases: dict[str, WorkflowCanvas] = field(default_factory=dict)

    def create_canvas(self, name: str, description: str = "") -> WorkflowCanvas:
        """Create a new workflow canvas."""
        import uuid
        canvas = WorkflowCanvas(
            canvas_id=str(uuid.uuid4()),
            name=name,
            description=description,
            nodes=[
                CanvasNode(node_id="start", node_type=CanvasNodeType.START, label="Start", x=50, y=200),
                CanvasNode(node_id="end", node_type=CanvasNodeType.END, label="End", x=700, y=200),
            ],
        )
        self._canvases[canvas.canvas_id] = canvas
        return canvas

    def get_canvas(self, canvas_id: str) -> WorkflowCanvas | None:
        """Get a workflow canvas."""
        return self._canvases.get(canvas_id)

    def save_canvas(self, canvas: WorkflowCanvas) -> None:
        """Save a workflow canvas."""
        canvas.updated_at = datetime.utcnow().isoformat()
        self._canvases[canvas.canvas_id] = canvas

    def list_canvases(self) -> list[dict[str, Any]]:
        """List all workflow canvases."""
        return [
            {
                "canvas_id": c.canvas_id,
                "name": c.name,
                "description": c.description,
                "node_count": len(c.nodes),
                "edge_count": len(c.edges),
                "version": c.version,
                "updated_at": c.updated_at or c.created_at,
            }
            for c in self._canvases.values()
        ]

    def get_node_catalog(self) -> list[dict[str, Any]]:
        """Get the catalog of available node types."""
        return [
            {"type": "start", "label": "Start", "category": "flow", "icon": "play", "draggable": True},
            {"type": "end", "label": "End", "category": "flow", "icon": "stop", "draggable": True},
            {"type": "ai_stage", "label": "AI Stage", "category": "ai", "icon": "robot", "draggable": True,
             "config_schema": {"model": {"type": "select", "options": ["gpt-4o", "gpt-4o-mini", "claude-3-sonnet"]},
                               "temperature": {"type": "slider", "min": 0, "max": 1, "default": 0.1},
                               "max_tokens": {"type": "number", "default": 4096}}},
            {"type": "human_review", "label": "Human Review", "category": "workflow", "icon": "user", "draggable": True,
             "config_schema": {"required_role": {"type": "select", "options": ["legal", "procurement", "security", "compliance"]},
                               "sla_hours": {"type": "number", "default": 8},
                               "required_skills": {"type": "tags"}}},
            {"type": "approval_gate", "label": "Approval Gate", "category": "workflow", "icon": "check", "draggable": True,
             "config_schema": {"min_approvers": {"type": "number", "default": 1},
                               "required_roles": {"type": "tags"},
                               "timeout_hours": {"type": "number", "default": 24}}},
            {"type": "condition", "label": "Condition", "category": "logic", "icon": "diamond", "draggable": True,
             "config_schema": {"expression": {"type": "text", "placeholder": "e.g., risk_score > 0.7"}}},
            {"type": "escalation", "label": "Escalation", "category": "workflow", "icon": "alert", "draggable": True,
             "config_schema": {"target_role": {"type": "select", "options": ["manager", "director", "executive", "legal"]},
                               "timeout_minutes": {"type": "number", "default": 60},
                               "condition": {"type": "text", "placeholder": "e.g., sla_breached"}}},
            {"type": "sla_timer", "label": "SLA Timer", "category": "governance", "icon": "clock", "draggable": True,
             "config_schema": {"sla_hours": {"type": "number", "default": 24},
                               "track": {"type": "select", "options": ["express", "standard", "extended"]}}},
            {"type": "notification", "label": "Notification", "category": "communication", "icon": "bell", "draggable": True,
             "config_schema": {"channel": {"type": "select", "options": ["email", "slack", "teams", "in_app"]},
                               "template": {"type": "text"}}},
            {"type": "integration", "label": "Integration Action", "category": "integration", "icon": "plug", "draggable": True,
             "config_schema": {"connector": {"type": "select", "options": ["docusign", "sharepoint", "salesforce", "slack"]},
                               "action": {"type": "text"}}},
            {"type": "policy_binding", "label": "Policy Binding", "category": "governance", "icon": "shield", "draggable": True,
             "config_schema": {"policy_pack": {"type": "select", "options": ["standard_ai_governance", "data_retention", "provider_routing"]}}},
        ]

    def add_node(self, canvas_id: str, node_type: CanvasNodeType, label: str, x: float, y: float) -> CanvasNode:
        """Add a node to the canvas."""
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"Canvas {canvas_id} not found")

        import uuid
        node = CanvasNode(
            node_id=str(uuid.uuid4()),
            node_type=node_type,
            label=label,
            x=x,
            y=y,
        )
        canvas.nodes.append(node)
        return node

    def add_edge(self, canvas_id: str, source_id: str, target_id: str, label: str = "", condition: str = "") -> CanvasEdge:
        """Add an edge between nodes."""
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            raise ValueError(f"Canvas {canvas_id} not found")

        import uuid
        edge = CanvasEdge(
            edge_id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            label=label,
            condition=condition,
        )
        canvas.edges.append(edge)
        return edge

    def validate_canvas(self, canvas_id: str) -> list[str]:
        """Validate a workflow canvas for correctness."""
        canvas = self._canvases.get(canvas_id)
        if not canvas:
            return ["Canvas not found"]

        errors = []
        node_ids = {n.node_id for n in canvas.nodes}

        # Check for start/end
        if not any(n.node_type == CanvasNodeType.START for n in canvas.nodes):
            errors.append("Canvas must have a Start node")
        if not any(n.node_type == CanvasNodeType.END for n in canvas.nodes):
            errors.append("Canvas must have an End node")

        # Check for disconnected nodes
        connected = set()
        for edge in canvas.edges:
            connected.add(edge.source_id)
            connected.add(edge.target_id)
        disconnected = node_ids - connected
        if disconnected:
            errors.append(f"Disconnected nodes: {len(disconnected)}")

        # Check for dangling edges
        edge_sources = {e.source_id for e in canvas.edges}
        edge_targets = {e.target_id for e in canvas.edges}
        dangling = (edge_sources - node_ids) | (edge_targets - node_ids)
        if dangling:
            errors.append(f"Dangling edges: {len(dangling)}")

        return errors


# ── Global singleton ───────────────────────────────────────────────

visual_workflow_studio = VisualWorkflowStudio()
