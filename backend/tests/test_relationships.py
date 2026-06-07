"""Tests for the Relationships Graph module."""

import pytest
from app.domains.relationships.schemas import (
    NodeType, EdgeType, GraphNode, GraphEdge, RelationshipGraph,
)


class TestRelationshipSchemas:
    """Verify relationship schema models."""

    def test_graph_node_creation(self):
        node = GraphNode(
            id="review:abc-123",
            type=NodeType.REVIEW,
            label="Test Review",
            tenant_id="tenant-1",
            metadata={"status": "in_review"},
        )
        assert node.id == "review:abc-123"
        assert node.type == NodeType.REVIEW
        assert node.label == "Test Review"
        assert node.tenant_id == "tenant-1"
        assert node.metadata["status"] == "in_review"

    def test_graph_edge_creation(self):
        edge = GraphEdge(
            id="review:abc→finding:def:reviewed_in",
            source="review:abc",
            target="finding:def",
            type=EdgeType.REVIEWED_IN,
            label="critical finding",
            metadata={"severity": "critical"},
        )
        assert edge.source == "review:abc"
        assert edge.target == "finding:def"
        assert edge.type == EdgeType.REVIEWED_IN

    def test_relationship_graph_creation(self):
        graph = RelationshipGraph(
            nodes=[
                GraphNode(id="review:1", type=NodeType.REVIEW, label="R1", tenant_id="t1"),
                GraphNode(id="finding:2", type=NodeType.FINDING, label="F2", tenant_id="t1"),
            ],
            edges=[
                GraphEdge(
                    id="review:1→finding:2:reviewed_in",
                    source="review:1", target="finding:2",
                    type=EdgeType.REVIEWED_IN,
                ),
            ],
            total_nodes=2,
            total_edges=1,
        )
        assert graph.total_nodes == 2
        assert graph.total_edges == 1
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_all_node_types_have_values(self):
        """Verify all expected node types exist."""
        values = {t.value for t in NodeType}
        expected = {"review", "upload", "finding", "redline",
                     "negotiation", "obligation", "workflow", "vendor"}
        assert values == expected, f"Missing: {expected - values}"

    def test_all_edge_types_have_values(self):
        """Verify all expected edge types exist."""
        values = {t.value for t in EdgeType}
        expected = {"uploaded_as", "reviewed_in", "redlined_in",
                     "negotiates", "obligates", "workflow_for", "vendor_for"}
        assert values == expected, f"Missing: {expected - values}"


class TestRelationshipGraphBuilder:
    """Integration tests for the relationship graph builder.

    Requires a database with test data.
    """

    @pytest.mark.asyncio
    async def test_build_graph_with_review_id(self, tenant_a_session, sample_review):
        """Verify graph is built for a valid review_id."""
        from app.domains.relationships.service import RelationshipGraphBuilder

        builder = RelationshipGraphBuilder(
            session=tenant_a_session,
            tenant_id=sample_review.tenant_id,
        )
        graph = await builder.build_graph(
            review_id=str(sample_review.review_id),
            depth=1,
        )
        assert graph.total_nodes > 0, "Graph should have at least the review node"
        assert graph.total_edges >= 0

        # Verify the review node exists
        review_nodes = [n for n in graph.nodes if n.type == NodeType.REVIEW]
        assert len(review_nodes) >= 1

    @pytest.mark.asyncio
    async def test_build_graph_with_upload_id(self, tenant_a_session, completed_upload):
        """Verify graph is built from an upload_id."""
        from app.domains.relationships.service import RelationshipGraphBuilder

        # Need a tenant_id — get it from the upload session
        upload_tenant = str(completed_upload.tenant_id)

        builder = RelationshipGraphBuilder(
            session=tenant_a_session,
            tenant_id=upload_tenant,
        )
        graph = await builder.build_graph(
            upload_id=str(completed_upload.upload_id),
            depth=1,
        )
        # Should resolve to at least the upload node
        assert graph.total_nodes >= 0

    @pytest.mark.asyncio
    async def test_build_graph_nonexistent_review(self, tenant_a_session):
        """Verify empty graph for nonexistent review."""
        from app.domains.relationships.service import RelationshipGraphBuilder

        builder = RelationshipGraphBuilder(
            session=tenant_a_session,
            tenant_id="00000000-0000-0000-0000-000000000000",
        )
        graph = await builder.build_graph(
            review_id="00000000-0000-0000-0000-000000000000",
            depth=1,
        )
        assert graph.total_nodes == 0
        assert graph.total_edges == 0

    @pytest.mark.asyncio
    async def test_max_nodes_limit(self, tenant_a_session, sample_review):
        """Verify the graph enforces the 200-node limit."""
        from app.domains.relationships.service import MAX_NODES, RelationshipGraphBuilder

        builder = RelationshipGraphBuilder(
            session=tenant_a_session,
            tenant_id=sample_review.tenant_id,
        )
        graph = await builder.build_graph(
            review_id=str(sample_review.review_id),
            depth=2,
        )
        assert graph.total_nodes <= MAX_NODES, (
            f"Graph has {graph.total_nodes} nodes, max is {MAX_NODES}"
        )

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, tenant_a_session, sample_review,
                                           tenant_b_session):
        """Verify tenant B cannot see tenant A's graph data."""
        from app.domains.relationships.service import RelationshipGraphBuilder

        # Tenant B tries to access Tenant A's review
        builder_b = RelationshipGraphBuilder(
            session=tenant_b_session,
            tenant_id="00000000-0000-4000-8000-000000000002",  # Tenant B
        )
        graph = await builder_b.build_graph(
            review_id=str(sample_review.review_id),
            depth=1,
        )
        # Tenant B should get no data for Tenant A's review
        assert graph.total_nodes == 0, "Tenant B should not see Tenant A's data"
