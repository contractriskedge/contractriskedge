"""Enterprise Adoption, UX, and Strategic Expansion Tests.

Validates:
- Enterprise Workspace Experience (6 role-specific workspaces)
- Executive Command Center (risk heatmaps, vendor maps, renewal timelines, AI trust metrics)
- Reviewer Productivity System (bulk actions, macros, smart routing, coaching)
- Visual Workflow Studio (canvas, node catalog, validation)
- Enterprise Collaboration Layer (threads, annotations, mentions, escalation context)
- Customer Success Intelligence (health scores, adoption analysis, underutilized features)
- API & Marketplace Expansion (endpoints, marketplace, webhooks)
"""

from __future__ import annotations

import pytest


# ═══════════════════════════════════════════════════════════════════
# 1. ENTERPRISE WORKSPACE EXPERIENCE
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestWorkspaceExperience:
    """Validate enterprise workspaces."""

    def test_workspace_roles_defined(self) -> None:
        """All workspace roles must be defined."""
        from app.domains.workspaces import WorkspaceRole

        required = ["REVIEWER", "LEGAL_OPS", "PROCUREMENT", "EXECUTIVE", "COMPLIANCE", "ADMIN"]
        for r in required:
            assert hasattr(WorkspaceRole, r), f"Missing role: {r}"

    def test_all_workspaces_accessible(self) -> None:
        """All workspace roles must produce a workspace."""
        from app.domains.workspaces import workspace_service, WorkspaceRole

        for role in WorkspaceRole:
            ws = workspace_service.get_workspace(role)
            assert ws.name is not None
            assert len(ws.kpis) > 0
            assert len(ws.quick_actions) > 0

    def test_workspace_has_kpis(self) -> None:
        """Workspaces must have role-specific KPIs."""
        from app.domains.workspaces import workspace_service, WorkspaceRole

        ws = workspace_service.get_workspace(WorkspaceRole.EXECUTIVE)
        kpi_names = [k.name for k in ws.kpis]
        assert "Portfolio Risk Score" in kpi_names
        assert "AI Trust Score" in kpi_names
        assert "Annual Savings" in kpi_names

    def test_workspace_has_alerts(self) -> None:
        """Workspaces must have operational alerts."""
        from app.domains.workspaces import workspace_service, WorkspaceRole

        ws = workspace_service.get_workspace(WorkspaceRole.COMPLIANCE)
        assert len(ws.alerts) > 0

    def test_workspace_has_widgets(self) -> None:
        """Workspaces must have dashboard widgets."""
        from app.domains.workspaces import workspace_service, WorkspaceRole

        ws = workspace_service.get_workspace(WorkspaceRole.ADMIN)
        assert len(ws.widgets) > 0


# ═══════════════════════════════════════════════════════════════════
# 2. EXECUTIVE COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestExecutiveCommandCenter:
    """Validate executive command center."""

    def test_portfolio_risk_heatmap(self) -> None:
        """Risk heatmap must segment contracts by risk."""
        from app.domains.executive_ui import ExecutiveCommandCenter

        center = ExecutiveCommandCenter()
        heatmap = center.build_portfolio_risk_heatmap([
            {"segment": "Technology", "risk_score": 0.3},
            {"segment": "Technology", "risk_score": 0.4},
            {"segment": "Healthcare", "risk_score": 0.7},
            {"segment": "Healthcare", "risk_score": 0.8},
            {"segment": "Finance", "risk_score": 0.5},
        ])
        assert len(heatmap.segments) == 3
        assert heatmap.total_contracts == 5
        assert heatmap.overall_risk > 0

    def test_vendor_concentration_map(self) -> None:
        """Vendor concentration must detect over-reliance."""
        from app.domains.executive_ui import ExecutiveCommandCenter

        center = ExecutiveCommandCenter()
        concentration = center.build_vendor_concentration_map({
            "Vendor A": [{"value": 500000}] * 10,
            "Vendor B": [{"value": 50000}] * 2,
            "Vendor C": [{"value": 25000}] * 1,
        })
        assert len(concentration.vendors) == 3
        assert concentration.top_vendor_pct > 50  # Vendor A dominates

    def test_renewal_timeline(self) -> None:
        """Renewal timeline must identify imminent renewals."""
        from app.domains.executive_ui import ExecutiveCommandCenter
        from datetime import datetime, timedelta

        center = ExecutiveCommandCenter()
        timeline = center.build_renewal_timeline([
            {"contract_id": "c1", "contract_name": "Contract A", "renewal_date": (datetime.utcnow() + timedelta(days=15)).isoformat(), "risk_score": 0.8, "value": 100000},
            {"contract_id": "c2", "contract_name": "Contract B", "renewal_date": (datetime.utcnow() + timedelta(days=120)).isoformat(), "risk_score": 0.3, "value": 50000},
        ])
        assert timeline.imminent_count == 1
        assert timeline.at_risk_count >= 1

    def test_ai_trust_metrics(self) -> None:
        """AI trust metrics must calculate acceptance rate."""
        from app.domains.executive_ui import ExecutiveCommandCenter

        center = ExecutiveCommandCenter()
        metrics = center.build_ai_trust_metrics([
            {"reviewer_action": "accepted"},
            {"reviewer_action": "accepted"},
            {"reviewer_action": "rejected"},
            {"reviewer_action": "accepted"},
        ])
        assert metrics["acceptance_rate"] == 0.75
        assert metrics["trust_score"] > 0

    def test_full_dashboard(self) -> None:
        """Full dashboard must aggregate all visualizations."""
        from app.domains.executive_ui import ExecutiveCommandCenter

        center = ExecutiveCommandCenter()
        dashboard = center.build_full_dashboard({
            "contracts": [{"risk_score": 0.5}],
            "vendor_contracts": {"Vendor": [{"value": 1000}]},
            "renewals": [],
            "execution_history": [],
        })
        assert dashboard.risk_heatmap.total_contracts == 1


# ═══════════════════════════════════════════════════════════════════
# 3. REVIEWER PRODUCTIVITY SYSTEM
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestReviewerProductivity:
    """Validate reviewer productivity system."""

    def test_default_macros_registered(self) -> None:
        """Default review macros must be registered."""
        from app.domains.productivity import reviewer_productivity

        macros = reviewer_productivity.get_macros()
        assert len(macros) >= 5
        macro_names = [m.name for m in macros]
        assert "Accept All High Confidence" in macro_names
        assert "Escalate to Legal" in macro_names

    def test_macros_filterable_by_category(self) -> None:
        """Macros must be filterable by category."""
        from app.domains.productivity import reviewer_productivity

        bulk = reviewer_productivity.get_macros(category="bulk_actions")
        assert len(bulk) >= 1
        assert bulk[0].category == "bulk_actions"

    def test_bulk_action_suggestion(self) -> None:
        """Bulk actions must be suggested for grouped findings."""
        from app.domains.productivity import ReviewerProductivityService

        service = ReviewerProductivityService()
        findings = [
            {"finding_id": "f1", "confidence": 0.95, "clause_type": "liability"},
            {"finding_id": "f2", "confidence": 0.92, "clause_type": "liability"},
            {"finding_id": "f3", "confidence": 0.94, "clause_type": "liability"},
            {"finding_id": "f4", "confidence": 0.60, "clause_type": "payment"},
        ]
        actions = service.suggest_bulk_actions(findings)
        assert len(actions) >= 2  # High confidence group + clause type group

    def test_smart_routing(self) -> None:
        """Reviews must route to best available reviewer."""
        from app.domains.productivity import ReviewerProductivityService

        service = ReviewerProductivityService()
        reviewer_id = service.smart_route_review(
            {"required_role": "legal", "clause_types": ["liability"], "risk_score": 0.7},
            [
                {"user_id": "r1", "roles": ["legal"], "current_reviews": 5, "max_concurrent_reviews": 10, "skills": ["liability"], "accuracy_score": 0.95},
                {"user_id": "r2", "roles": ["procurement"], "current_reviews": 2, "max_concurrent_reviews": 10, "skills": [], "accuracy_score": 0.9},
            ],
        )
        assert reviewer_id == "r1"  # Legal role, liability skill

    def test_performance_coaching(self) -> None:
        """Coaching tips must be personalized."""
        from app.domains.productivity import ReviewerProductivityService

        service = ReviewerProductivityService()
        tips = service.get_performance_coaching({
            "avg_review_time_hours": 6,
            "accuracy_score": 0.85,
            "reviews_completed": 50,
            "sla_breaches": 5,
        })
        assert len(tips) > 0
        assert any("review time" in t.lower() for t in tips)


# ═══════════════════════════════════════════════════════════════════
# 4. VISUAL WORKFLOW STUDIO
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestVisualWorkflowStudio:
    """Validate visual workflow studio."""

    def test_canvas_creation(self) -> None:
        """Canvas must initialize with start and end nodes."""
        from app.domains.workflows.studio import visual_workflow_studio

        canvas = visual_workflow_studio.create_canvas("Test Workflow")
        assert canvas.name == "Test Workflow"
        assert len(canvas.nodes) == 2  # start + end

    def test_node_catalog(self) -> None:
        """Node catalog must include all node types."""
        from app.domains.workflows.studio import visual_workflow_studio

        catalog = visual_workflow_studio.get_node_catalog()
        catalog_types = [n["type"] for n in catalog]
        assert "start" in catalog_types
        assert "ai_stage" in catalog_types
        assert "human_review" in catalog_types
        assert "approval_gate" in catalog_types
        assert "escalation" in catalog_types
        assert "policy_binding" in catalog_types

    def test_add_node(self) -> None:
        """Nodes must be addable to canvas."""
        from app.domains.workflows.studio import visual_workflow_studio, CanvasNodeType

        canvas = visual_workflow_studio.create_canvas("Test")
        node = visual_workflow_studio.add_node(canvas.canvas_id, CanvasNodeType.AI_STAGE, "AI Analysis", x=200, y=200)
        assert node.node_type == CanvasNodeType.AI_STAGE
        assert node.x == 200

    def test_add_edge(self) -> None:
        """Edges must connect nodes."""
        from app.domains.workflows.studio import visual_workflow_studio, CanvasNodeType

        canvas = visual_workflow_studio.create_canvas("Test")
        node = visual_workflow_studio.add_node(canvas.canvas_id, CanvasNodeType.HUMAN_REVIEW, "Review", x=200, y=200)
        edge = visual_workflow_studio.add_edge(canvas.canvas_id, "start", node.node_id, label="Next")
        assert edge.source_id == "start"
        assert edge.target_id == node.node_id

    def test_canvas_validation(self) -> None:
        """Canvas validation must detect issues."""
        from app.domains.workflows.studio import visual_workflow_studio, CanvasNodeType

        canvas = visual_workflow_studio.create_canvas("Test")
        # Remove end node to trigger validation error
        canvas.nodes = [n for n in canvas.nodes if n.node_type != CanvasNodeType.END]
        errors = visual_workflow_studio.validate_canvas(canvas.canvas_id)
        assert len(errors) > 0

    def test_save_and_list_canvases(self) -> None:
        """Canvases must be savable and listable."""
        from app.domains.workflows.studio import visual_workflow_studio

        canvas = visual_workflow_studio.create_canvas("Save Test")
        visual_workflow_studio.save_canvas(canvas)
        canvases = visual_workflow_studio.list_canvases()
        assert any(c["name"] == "Save Test" for c in canvases)


# ═══════════════════════════════════════════════════════════════════
# 5. ENTERPRISE COLLABORATION LAYER
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestCollaboration:
    """Validate enterprise collaboration layer."""

    def test_comment_types_defined(self) -> None:
        """All comment types must be defined."""
        from app.domains.collaboration import CommentType

        required = ["DISCUSSION", "ANNOTATION", "CLAUSE_COMMENT", "REVIEW_NOTE", "MENTION", "ESCALATION", "APPROVAL"]
        for c in required:
            assert hasattr(CommentType, c), f"Missing comment type: {c}"

    def test_create_thread(self) -> None:
        """Discussion threads must be creatable."""
        from app.domains.collaboration import collaboration_service

        thread = collaboration_service.create_thread("review_001", "Discussion about liability clause", "user_001")
        assert thread.review_id == "review_001"
        assert thread.title == "Discussion about liability clause"

    def test_add_comment(self) -> None:
        """Comments must be addable to threads."""
        from app.domains.collaboration import collaboration_service

        thread = collaboration_service.create_thread("review_001", "Test thread", "user_001")
        comment = collaboration_service.add_comment(thread.thread_id, "user_002", "Jane", "I agree with this finding @user_001")
        assert comment.body == "I agree with this finding @user_001"
        assert "user_001" in comment.mentions

    def test_add_annotation(self) -> None:
        """Annotations must be addable on evidence."""
        from app.domains.collaboration import collaboration_service

        annotation = collaboration_service.add_annotation(
            review_id="review_001",
            chunk_id="chunk_001",
            author_id="user_001",
            text="The liability cap is $1M",
            comment="This cap seems low for the contract value",
            annotation_type="concern",
        )
        assert annotation.annotation_type == "concern"
        assert annotation.chunk_id == "chunk_001"

    def test_escalation_context(self) -> None:
        """Escalation context must include all discussions."""
        from app.domains.collaboration import collaboration_service

        thread = collaboration_service.create_thread("review_002", "Escalation discussion", "user_001")
        collaboration_service.add_comment(thread.thread_id, "user_002", "Jane", "This needs executive attention")
        collaboration_service.add_annotation("review_002", "chunk_001", "user_001", "text", "High risk clause")

        context = collaboration_service.get_escalation_context("review_002")
        assert context["thread_count"] == 1
        assert context["comment_count"] == 1
        assert context["annotation_count"] == 1

    def test_collaboration_summary(self) -> None:
        """Collaboration summary must show activity."""
        from app.domains.collaboration import collaboration_service

        summary = collaboration_service.get_collaboration_summary("review_003")
        assert "review_id" in summary
        assert "threads" in summary


# ═══════════════════════════════════════════════════════════════════
# 6. CUSTOMER SUCCESS INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestCustomerSuccess:
    """Validate customer success intelligence."""

    def test_health_statuses_defined(self) -> None:
        """All health statuses must be defined."""
        from app.domains.customer_success import HealthStatus

        assert HealthStatus.HEALTHY
        assert HealthStatus.AT_RISK
        assert HealthStatus.CHURN_RISK

    def test_healthy_tenant_scoring(self) -> None:
        """Healthy tenant must get high score."""
        from app.domains.customer_success import CustomerSuccessService, HealthStatus

        service = CustomerSuccessService()
        from datetime import datetime
        score = service.calculate_health_score({
            "tenant_id": "t1",
            "tenant_name": "Healthy Corp",
            "features": {"ai_analysis": {"enabled": True, "times_used": 100},
                         "redlines": {"enabled": True, "times_used": 50},
                         "benchmarks": {"enabled": True, "times_used": 20}},
            "workflows": [{"is_custom": True}, {"is_custom": False}],
            "reviewers": [{"avg_review_time_hours": 2, "sla_compliance_rate": 0.98}],
            "execution_history": [{"reviewer_action": "accepted"}] * 90 + [{"reviewer_action": "rejected"}] * 10,
            "last_active": datetime.utcnow().isoformat(),
        })
        assert score.status == HealthStatus.HEALTHY
        assert score.overall_score > 0.5

    def test_churn_risk_tenant(self) -> None:
        """Inactive tenant must get churn risk."""
        from app.domains.customer_success import CustomerSuccessService, HealthStatus

        service = CustomerSuccessService()
        score = service.calculate_health_score({
            "tenant_id": "t2",
            "tenant_name": "At Risk Corp",
            "features": {},
            "workflows": [],
            "reviewers": [],
            "execution_history": [],
            "last_active": "2024-01-01T00:00:00",
        })
        assert score.status in (HealthStatus.AT_RISK, HealthStatus.CHURN_RISK)
        assert score.overall_score < 0.5

    def test_feature_adoption_analysis(self) -> None:
        """Feature adoption must identify usage patterns."""
        from app.domains.customer_success import CustomerSuccessService

        service = CustomerSuccessService()
        features = service.analyze_feature_adoption({
            "features": {
                "ai_analysis": {"category": "ai", "enabled": True, "times_used": 100},
                "benchmarks": {"category": "intelligence", "enabled": True, "times_used": 5},
                "simulation": {"category": "advanced", "enabled": True, "times_used": 0},
            },
            "total_actions": 500,
        })
        assert len(features) == 3
        assert features[0].adoption_rate <= features[-1].adoption_rate  # Sorted ascending

    def test_underutilized_features(self) -> None:
        """Underutilized features must be identifiable."""
        from app.domains.customer_success import CustomerSuccessService

        service = CustomerSuccessService()
        underutilized = service.get_underutilized_features({
            "features": {
                "simulation": {"category": "advanced", "enabled": True, "times_used": 0},
            },
            "total_actions": 100,
        })
        assert len(underutilized) == 1
        assert underutilized[0].feature_name == "simulation"

    def test_tenant_segmentation(self) -> None:
        """Tenant segmentation must group by health."""
        from app.domains.customer_success import CustomerSuccessService, TenantHealthScore, HealthStatus

        service = CustomerSuccessService()
        scores = [
            TenantHealthScore(tenant_id="t1", tenant_name="A", overall_score=0.9, status=HealthStatus.HEALTHY),
            TenantHealthScore(tenant_id="t2", tenant_name="B", overall_score=0.4, status=HealthStatus.AT_RISK),
            TenantHealthScore(tenant_id="t3", tenant_name="C", overall_score=0.2, status=HealthStatus.CHURN_RISK),
        ]
        segment = service.get_tenant_segment(scores)
        assert segment["healthy"] == 1
        assert segment["at_risk"] == 1
        assert segment["churn_risk"] == 1


# ═══════════════════════════════════════════════════════════════════
# 7. API & MARKETPLACE EXPANSION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestAPIMarketplace:
    """Validate API and marketplace expansion."""

    def test_api_plans_defined(self) -> None:
        """All API plans must be defined."""
        from app.domains.extensions.marketplace import ApiPlan

        assert ApiPlan.FREE
        assert ApiPlan.STARTER
        assert ApiPlan.PROFESSIONAL
        assert ApiPlan.ENTERPRISE

    def test_default_endpoints_registered(self) -> None:
        """Default API endpoints must be registered."""
        from app.domains.extensions.marketplace import api_marketplace

        endpoints = api_marketplace.get_endpoints()
        assert len(endpoints) >= 10
        paths = [e["path"] for e in endpoints]
        assert "/contracts" in paths
        assert "/search" in paths
        assert "/reviews" in paths

    def test_endpoint_plan_access(self) -> None:
        """Enterprise endpoints must not be accessible on free plan."""
        from app.domains.extensions.marketplace import api_marketplace, ApiPlan

        free_endpoints = api_marketplace.get_endpoints(plan=ApiPlan.FREE)
        enterprise_paths = {"/replay/", "/simulation/", "/governance/"}
        for ep in free_endpoints:
            for restricted in enterprise_paths:
                assert restricted not in ep["path"]

    def test_marketplace_listings(self) -> None:
        """Marketplace must have default listings."""
        from app.domains.extensions.marketplace import api_marketplace

        listings = api_marketplace.get_marketplace()
        assert len(listings) >= 5
        listing_names = [l["name"] for l in listings]
        assert "DocuSign Integration" in listing_names
        assert "Slack Notifications" in listing_names

    def test_marketplace_filtering(self) -> None:
        """Marketplace must support category filtering."""
        from app.domains.extensions.marketplace import api_marketplace

        integrations = api_marketplace.get_marketplace(category="integration")
        assert all(l["category"] == "integration" for l in integrations)

    def test_webhook_creation(self) -> None:
        """Webhook subscriptions must be creatable."""
        from app.domains.extensions.marketplace import api_marketplace

        import asyncio
        sub = asyncio.run(api_marketplace.create_webhook(
            tenant_id="tenant_001",
            url="https://example.com/webhook",
            events=["review.assigned", "review.completed"],
        ))
        assert sub.tenant_id == "tenant_001"
        assert len(sub.secret) > 0

    def test_webhook_listing(self) -> None:
        """Webhooks must be listable by tenant."""
        from app.domains.extensions.marketplace import api_marketplace

        webhooks = api_marketplace.get_webhooks("tenant_001")
        assert len(webhooks) >= 1

    def test_api_portal_data(self) -> None:
        """API portal data must include all sections."""
        from app.domains.extensions.marketplace import api_marketplace

        portal = api_marketplace.get_api_portal_data()
        assert "endpoints" in portal
        assert "marketplace" in portal
        assert "webhook_events" in portal
        assert "sdks" in portal
