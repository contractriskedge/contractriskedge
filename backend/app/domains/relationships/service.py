"""Relationships Graph service — builds entity relationship graphs from database data.

Traverses foreign-key relationships across domain tables to produce a
graph centered on a review or upload. Supports depth-1 (direct FKs) and
depth-2 (indirect relationships via intermediate entities).

Multi-tenant safe — all queries include tenant_id filtering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.relationships.schemas import (
    RelationshipGraph, GraphNode, GraphEdge,
    NodeType, EdgeType,
)

logger = logging.getLogger(__name__)

# ── In-memory cache ───────────────────────────────────────────────
# {cache_key: {graph, expires_at}}
_graph_cache: dict[str, dict] = {}

MAX_NODES = 200
CACHE_TTL_MINUTES = 5


@dataclass
class RelationshipGraphBuilder:
    """Builds entity relationship graphs from database data."""

    session: AsyncSession
    tenant_id: str

    async def build_graph(
        self,
        review_id: Optional[str] = None,
        upload_id: Optional[str] = None,
        depth: int = 1,
    ) -> RelationshipGraph:
        """Build a relationship graph centered on a review or upload.

        Args:
            review_id: Center the graph on this review.
            upload_id: Center the graph on this upload (alternative to review_id).
            depth: Traversal depth (1 = direct FKs, 2 = indirect relationships).

        Returns:
            RelationshipGraph with nodes and edges.
        """
        # Resolve review_id from upload_id if needed
        if not review_id and upload_id:
            review_id = await self._resolve_review_from_upload(upload_id)

        if not review_id:
            return RelationshipGraph(
                nodes=[], edges=[], total_nodes=0, total_edges=0,
                generated_at=datetime.now(timezone.utc),
            )

        # Check cache
        cache_key = f"{self.tenant_id}:{review_id}:depth={depth}"
        cached = _graph_cache.get(cache_key)
        if cached and cached["expires_at"] > datetime.now(timezone.utc):
            return cached["graph"]

        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}

        # Ensure tenant_id is a string for SQL queries
        tid = str(self.tenant_id)

        # ── Depth 1: Core review + direct FK relationships ──────
        await self._add_review_node(nodes, review_id)
        await self._add_upload_node(nodes, edges, review_id)
        await self._add_finding_nodes(nodes, edges, review_id)
        await self._add_redline_nodes(nodes, edges, review_id)
        await self._add_negotiation_nodes(nodes, edges, review_id)
        await self._add_obligation_nodes(nodes, edges, review_id)
        await self._add_workflow_nodes(nodes, edges, review_id)
        await self._add_vendor_node(nodes, edges, review_id)

        # ── Depth 2: Indirect relationships ─────────────────────
        if depth >= 2:
            # Follow findings to their AI source findings
            await self._add_finding_children(nodes, edges, review_id)

        # Enforce node limit
        if len(nodes) > MAX_NODES:
            # Trim to the first MAX_NODES by keeping review + most connected
            node_list = list(nodes.values())
            # Always keep the review node
            review_node = next((n for n in node_list if n.type == NodeType.REVIEW), None)
            others = [n for n in node_list if n.type != NodeType.REVIEW]
            others.sort(key=lambda n: -len(n.metadata.get("connection_count", 0)))
            trimmed = [review_node] + others[:MAX_NODES - 1] if review_node else others[:MAX_NODES]
            trimmed_ids = {n.id for n in trimmed}
            nodes = {n.id: n for n in trimmed}
            edges = {k: v for k, v in edges.items() if v.source in trimmed_ids and v.target in trimmed_ids}

        # Cache the result
        _graph_cache[cache_key] = {
            "graph": RelationshipGraph(
                nodes=list(nodes.values()),
                edges=list(edges.values()),
                total_nodes=len(nodes),
                total_edges=len(edges),
                generated_at=datetime.now(timezone.utc),
            ),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=CACHE_TTL_MINUTES),
        }

        return _graph_cache[cache_key]["graph"]

    async def _resolve_review_from_upload(self, upload_id: str) -> Optional[str]:
        """Find the most recent review for a given upload."""
        result = await self.session.execute(
            sa_text("""
                SELECT review_id::text FROM contract_reviews
                WHERE tenant_id = :tid AND upload_id = :uid
                  AND is_deleted = FALSE
                ORDER BY created_at DESC LIMIT 1
            """),
            {"tid": self.tenant_id, "uid": upload_id},
        )
        row = result.fetchone()
        return str(row[0]) if row else None

    async def _add_review_node(self, nodes: dict, review_id: str) -> None:
        """Add the central review node."""
        result = await self.session.execute(
            sa_text("""
                SELECT review_id::text, status, workflow_stage, assigned_to,
                       finding_count, redline_count, priority, created_at::text
                FROM contract_reviews
                WHERE review_id::text = :rid AND tenant_id = :tid
            """),
            {"rid": review_id, "tid": self.tenant_id},
        )
        row = result.fetchone()
        if not row:
            return
        node_id = f"review:{row.review_id}"
        nodes[node_id] = GraphNode(
            id=node_id,
            type=NodeType.REVIEW,
            label=f"Review {row.review_id[:8]}...",
            tenant_id=str(self.tenant_id),
            metadata={
                "status": row.status,
                "workflow_stage": row.workflow_stage or "",
                "assigned_to": row.assigned_to or "",
                "finding_count": row.finding_count,
                "redline_count": row.redline_count,
                "priority": row.priority,
                "created_at": row.created_at or "",
            },
        )

    async def _add_upload_node(self, nodes: dict, edges: dict, review_id: str) -> None:
        """Add the upload/document node linked to the review."""
        result = await self.session.execute(
            sa_text("""
                SELECT u.upload_id::text, u.filename, u.content_type,
                       u.file_size, u.metadata->>'counterparty' AS counterparty,
                       u.created_at::text
                FROM upload_sessions u
                JOIN contract_reviews r ON r.upload_id = u.upload_id
                WHERE r.review_id::text = :rid AND r.tenant_id = :tid
            """),
            {"rid": review_id, "tid": self.tenant_id},
        )
        row = result.fetchone()
        if not row:
            return
        node_id = f"upload:{row.upload_id}"
        nodes[node_id] = GraphNode(
            id=node_id,
            type=NodeType.UPLOAD,
            label=row.filename or f"Upload {row.upload_id[:8]}...",
            tenant_id=str(self.tenant_id),
            metadata={
                "filename": row.filename or "",
                "content_type": row.content_type or "",
                "file_size": row.file_size or 0,
                "counterparty": row.counterparty or "",
                "created_at": row.created_at or "",
            },
        )
        edges[f"review:{review_id}→{node_id}:uploaded_as"] = GraphEdge(
            id=f"review:{review_id}→{node_id}:uploaded_as",
            source=f"review:{review_id}",
            target=node_id,
            type=EdgeType.UPLOADED_AS,
            label="uploaded as",
        )

    async def _add_finding_nodes(self, nodes: dict, edges: dict, review_id: str) -> None:
        """Add finding nodes linked to the review."""
        result = await self.session.execute(
            sa_text("""
                SELECT finding_id::text, clause_type, severity, title,
                       resolution, created_at::text
                FROM review_findings
                WHERE review_id::text = :rid AND tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT 50
            """),
            {"rid": review_id, "tid": self.tenant_id},
        )
        for row in result.fetchall():
            node_id = f"finding:{row.finding_id}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type=NodeType.FINDING,
                label=row.title or f"Finding {row.finding_id[:8]}...",
                tenant_id=str(self.tenant_id),
                metadata={
                    "clause_type": row.clause_type or "",
                    "severity": row.severity,
                    "resolution": row.resolution or "",
                    "created_at": row.created_at or "",
                },
            )
            edges[f"review:{review_id}→{node_id}:reviewed_in"] = GraphEdge(
                id=f"review:{review_id}→{node_id}:reviewed_in",
                source=f"review:{review_id}",
                target=node_id,
                type=EdgeType.REVIEWED_IN,
                label=f"{row.severity} finding",
                metadata={"severity": row.severity},
            )

    async def _add_redline_nodes(self, nodes: dict, edges: dict, review_id: str) -> None:
        """Add redline nodes linked to the review."""
        result = await self.session.execute(
            sa_text("""
                SELECT redline_id::text, clause_type, status, risk_level,
                       operation, created_at::text
                FROM review_redlines
                WHERE review_id::text = :rid AND tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT 50
            """),
            {"rid": review_id, "tid": self.tenant_id},
        )
        for row in result.fetchall():
            node_id = f"redline:{row.redline_id}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type=NodeType.REDLINE,
                label=f"Redline {row.redline_id[:8]}...",
                tenant_id=str(self.tenant_id),
                metadata={
                    "clause_type": row.clause_type or "",
                    "status": row.status,
                    "risk_level": row.risk_level or "",
                    "operation": row.operation or "",
                    "created_at": row.created_at or "",
                },
            )
            edges[f"review:{review_id}→{node_id}:redlined_in"] = GraphEdge(
                id=f"review:{review_id}→{node_id}:redlined_in",
                source=f"review:{review_id}",
                target=node_id,
                type=EdgeType.REDLINED_IN,
                label=f"{row.status} redline",
                metadata={"status": row.status},
            )

    async def _add_negotiation_nodes(self, nodes: dict, edges: dict, review_id: str) -> None:
        """Add negotiation session nodes linked to the review via contract_id FK."""
        result = await self.session.execute(
            sa_text("""
                SELECT session_id::text, contract_title, counterparty, stage,
                       health_score, created_at::text
                FROM negotiation_sessions
                WHERE contract_id::text = :rid AND tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT 20
            """),
            {"rid": review_id, "tid": self.tenant_id},
        )
        for row in result.fetchall():
            node_id = f"negotiation:{row.session_id}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type=NodeType.NEGOTIATION,
                label=row.contract_title or f"Negotiation {row.session_id[:8]}...",
                tenant_id=str(self.tenant_id),
                metadata={
                    "counterparty": row.counterparty or "",
                    "stage": row.stage,
                    "health_score": row.health_score,
                    "created_at": row.created_at or "",
                },
            )
            edges[f"review:{review_id}→{node_id}:negotiates"] = GraphEdge(
                id=f"review:{review_id}→{node_id}:negotiates",
                source=f"review:{review_id}",
                target=node_id,
                type=EdgeType.NEGOTIATES,
                label=f"{row.stage} negotiation",
                metadata={"stage": row.stage},
            )

    async def _add_obligation_nodes(self, nodes: dict, edges: dict, review_id: str) -> None:
        """Add obligation nodes linked to the review via contract_id."""
        result = await self.session.execute(
            sa_text("""
                SELECT id::text, name, obligation_type, status,
                       vendor, risk_level, created_at::text
                FROM obligations
                WHERE contract_id::text = :rid AND tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT 20
            """),
            {"rid": review_id, "tid": self.tenant_id},
        )
        for row in result.fetchall():
            node_id = f"obligation:{row.id}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type=NodeType.OBLIGATION,
                label=row.name or f"Obligation {row.id[:8]}...",
                tenant_id=str(self.tenant_id),
                metadata={
                    "obligation_type": row.obligation_type or "",
                    "status": row.status,
                    "vendor_name": row.vendor or "",
                    "risk_level": row.risk_level or "",
                    "created_at": row.created_at or "",
                },
            )
            edges[f"review:{review_id}→{node_id}:obligates"] = GraphEdge(
                id=f"review:{review_id}→{node_id}:obligates",
                source=f"review:{review_id}",
                target=node_id,
                type=EdgeType.OBLIGATES,
                label=f"{row.status} obligation",
                metadata={"status": row.status},
            )

    async def _add_workflow_nodes(self, nodes: dict, edges: dict, review_id: str) -> None:
        """Add workflow instance nodes linked to the review."""
        result = await self.session.execute(
            sa_text("""
                SELECT workflow_id::text, workflow_type, status,
                       current_step, started_at::text, context
                FROM workflow_instances
                WHERE tenant_id = :tid
                  AND context->>'review_id' = :rid
                ORDER BY started_at DESC
                LIMIT 20
            """),
            {"tid": str(self.tenant_id), "rid": review_id},
        )
        for row in result.fetchall():
            node_id = f"workflow:{row.workflow_id}"
            nodes[node_id] = GraphNode(
                id=node_id,
                type=NodeType.WORKFLOW,
                label=f"{row.workflow_type} workflow",
                tenant_id=str(self.tenant_id),
                metadata={
                    "workflow_type": row.workflow_type,
                    "status": row.status,
                    "current_step": row.current_step or "",
                    "started_at": str(row.started_at or ""),
                },
            )
            edges[f"review:{review_id}→{node_id}:workflow_for"] = GraphEdge(
                id=f"review:{review_id}→{node_id}:workflow_for",
                source=f"review:{review_id}",
                target=node_id,
                type=EdgeType.WORKFLOW_FOR,
                label=f"{row.status} workflow",
                metadata={"status": row.status},
            )

    async def _add_vendor_node(self, nodes: dict, edges: dict, review_id: str) -> None:
        """Add vendor/counterparty node linked through the upload session."""
        result = await self.session.execute(
            sa_text("""
                SELECT u.metadata->>'counterparty' AS counterparty,
                       u.upload_id::text
                FROM upload_sessions u
                JOIN contract_reviews r ON r.upload_id = u.upload_id
                WHERE r.review_id::text = :rid AND r.tenant_id = :tid
                  AND u.metadata->>'counterparty' IS NOT NULL
                  AND u.metadata->>'counterparty' != ''
            """),
            {"rid": review_id, "tid": self.tenant_id},
        )
        row = result.fetchone()
        if not row or not row.counterparty:
            return
        node_id = f"vendor:{row.counterparty}"
        nodes[node_id] = GraphNode(
            id=node_id,
            type=NodeType.VENDOR,
            label=row.counterparty,
            tenant_id=str(self.tenant_id),
            metadata={"name": row.counterparty},
        )
        edges[f"upload:{row.upload_id}→{node_id}:vendor_for"] = GraphEdge(
            id=f"upload:{row.upload_id}→{node_id}:vendor_for",
            source=f"upload:{row.upload_id}",
            target=node_id,
            type=EdgeType.VENDOR_FOR,
            label="vendor",
        )

    async def _add_finding_children(self, nodes: dict, edges: dict, review_id: str) -> None:
        """Depth-2: follow findings to their AI source findings."""
        result = await self.session.execute(
            sa_text("""
                SELECT af.finding_id::text, af.run_id::text,
                       af.clause_type, af.severity, af.title
                FROM ai_findings af
                JOIN review_findings rf ON rf.finding_id = af.finding_id
                WHERE rf.review_id::text = :rid AND rf.tenant_id = :tid
                LIMIT 50
            """),
            {"rid": review_id, "tid": self.tenant_id},
        )
        for row in result.fetchall():
            finding_node_id = f"finding:{row.finding_id}"
            if finding_node_id not in nodes:
                nodes[finding_node_id] = GraphNode(
                    id=finding_node_id,
                    type=NodeType.FINDING,
                    label=row.title or f"AI Finding {row.finding_id[:8]}...",
                    tenant_id=str(self.tenant_id),
                    metadata={
                        "clause_type": row.clause_type or "",
                        "severity": row.severity,
                        "source": "ai",
                    },
                )
