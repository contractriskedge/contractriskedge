"""Relationships Graph schemas — node and edge types for entity relationship graphs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Entity types that can appear as nodes in the relationship graph."""
    REVIEW = "review"
    UPLOAD = "upload"
    FINDING = "finding"
    REDLINE = "redline"
    NEGOTIATION = "negotiation"
    OBLIGATION = "obligation"
    WORKFLOW = "workflow"
    VENDOR = "vendor"


class EdgeType(str, Enum):
    """Relationship types that can appear as edges in the relationship graph."""
    UPLOADED_AS = "uploaded_as"
    REVIEWED_IN = "reviewed_in"
    REDLINED_IN = "redlined_in"
    NEGOTIATES = "negotiates"
    OBLIGATES = "obligates"
    WORKFLOW_FOR = "workflow_for"
    VENDOR_FOR = "vendor_for"


class GraphNode(BaseModel):
    """A single entity node in the relationship graph."""
    id: str = Field(..., description="Unique node ID: {node_type}:{entity_id}")
    type: NodeType
    label: str = Field(..., description="Display name for the node")
    tenant_id: str
    metadata: dict[str, Any] = Field(default_factory=dict, description="Entity-specific fields")


class GraphEdge(BaseModel):
    """A single relationship edge connecting two nodes."""
    id: str = Field(..., description="Unique edge ID: {source}→{target}:{edge_type}")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: EdgeType
    label: str = Field(default="", description="Display label for the edge")
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationshipGraph(BaseModel):
    """Complete relationship graph response."""
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
