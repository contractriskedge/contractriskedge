"""Distributed Scale & Intelligence Platform Tests.

Validates:
- Multi-Region Runtime (region routing, tenant affinity, failover, residency)
- Distributed Queue Orchestration (sharding, priority, starvation prevention)
- Vector Scaling Architecture (tiering, shard balancing, semantic cache)
- Adaptive Runtime Optimization (cost-quality-latency tradeoffs)
- Contract Intelligence Graph Expansion (obligation deps, vendor intel, risk propagation)
- Benchmark Intelligence Engine (clause scoring, market deviation, renewal forecasting)
- AI Learning Loop (consensus scoring, false-positive clustering, prompt optimization)
- Cross-Contract Intelligence (duplicate obligations, conflicting clauses, renewal overlap)
- Workflow Builder (template CRUD, validation, simulation)
"""

from __future__ import annotations

import pytest


# ═══════════════════════════════════════════════════════════════════
# 1. MULTI-REGION RUNTIME
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestMultiRegionRuntime:
    """Validate multi-region routing and failover."""

    def test_region_enum_defined(self) -> None:
        """All required regions must be defined."""
        from app.domains.distributed import Region

        required = ["US_EAST", "US_WEST", "EU_WEST", "EU_CENTRAL", "AP_SOUTHEAST"]
        for r in required:
            assert hasattr(Region, r), f"Missing region: {r}"

    def test_residency_policies_defined(self) -> None:
        """All residency policies must be defined."""
        from app.domains.distributed import ResidencyPolicy

        assert ResidencyPolicy.DATA_RESIDENT
        assert ResidencyPolicy.COMPUTE_ONLY
        assert ResidencyPolicy.NO_RESTRICTION

    def test_region_router_initialization(self) -> None:
        """RegionRouter must initialize with default state."""
        from app.domains.distributed import RegionRouter

        router = RegionRouter()
        assert router.get_regional_status() == {}

    def test_register_endpoint(self) -> None:
        """Endpoints must be registerable per region."""
        from app.domains.distributed import RegionRouter, RegionalEndpoint, Region

        router = RegionRouter()
        endpoint = RegionalEndpoint(
            region=Region.US_EAST,
            endpoint_url="https://api-us-east.contractriskedge.com",
        )
        router.register_endpoint(endpoint)
        status = router.get_regional_status()
        assert "us-east" in status

    def test_tenant_affinity(self) -> None:
        """Tenant affinity must route to correct region."""
        from app.domains.distributed import RegionRouter, RegionalEndpoint, Region

        router = RegionRouter()
        router.register_endpoint(RegionalEndpoint(region=Region.US_EAST, endpoint_url="https://us-east.example.com"))
        router.register_endpoint(RegionalEndpoint(region=Region.EU_WEST, endpoint_url="https://eu-west.example.com"))

        router.set_tenant_affinity("eu_tenant", Region.EU_WEST)
        region, endpoint = router.get_optimal_region("eu_tenant")
        assert region == Region.EU_WEST

    def test_failover_on_unhealthy_region(self) -> None:
        """Failover must route to healthy region when primary is down."""
        from app.domains.distributed import RegionRouter, RegionalEndpoint, Region

        router = RegionRouter()
        router.register_endpoint(RegionalEndpoint(region=Region.US_EAST, endpoint_url="https://us-east.example.com", health_score=0.1))
        router.register_endpoint(RegionalEndpoint(region=Region.US_WEST, endpoint_url="https://us-west.example.com"))

        router.set_tenant_affinity("us_tenant", Region.US_EAST)
        region, endpoint = router.get_optimal_region("us_tenant")
        assert region == Region.US_WEST  # Failed over

    def test_no_healthy_region_raises(self) -> None:
        """No available region must raise ValueError."""
        from app.domains.distributed import RegionRouter, RegionalEndpoint, Region

        router = RegionRouter()
        router.register_endpoint(RegionalEndpoint(region=Region.US_EAST, endpoint_url="https://us-east.example.com", health_score=0.1, is_active=False))

        with pytest.raises(ValueError):
            router.get_optimal_region("any_tenant")

    def test_health_recording(self) -> None:
        """Health checks must update endpoint status."""
        from app.domains.distributed import RegionRouter, RegionalEndpoint, Region

        router = RegionRouter()
        router.register_endpoint(RegionalEndpoint(region=Region.US_EAST, endpoint_url="https://us-east.example.com"))
        router.record_health(Region.US_EAST, health_score=0.5, latency_ms=200)
        status = router.get_regional_status()
        assert status["us-east"]["health"] == 0.5
        assert status["us-east"]["latency_ms"] == 200


# ═══════════════════════════════════════════════════════════════════
# 2. DISTRIBUTED QUEUE ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestDistributedQueue:
    """Validate distributed queue orchestration."""

    def test_default_shards_registered(self) -> None:
        """Default queue shards must be registered."""
        from app.domains.distributed.queue import distributed_queue

        status = distributed_queue.get_shard_status()
        assert "high_priority" in status
        assert "ai_analysis" in status
        assert "default" in status

    def test_shard_selection_by_priority(self) -> None:
        """Shard selection must respect priority."""
        from app.domains.distributed.queue import DistributedQueueOrchestrator, ShardStrategy

        queue = DistributedQueueOrchestrator()
        queue.set_strategy(ShardStrategy.PRIORITY)

        shard = queue.select_shard("ai_analysis", priority=3)
        assert shard is not None

    def test_shard_selection_by_tenant_affinity(self) -> None:
        """Tenant affinity must route to correct shard."""
        from app.domains.distributed.queue import DistributedQueueOrchestrator

        queue = DistributedQueueOrchestrator()
        queue.set_tenant_affinity("enterprise_tenant", "high_priority")
        shard = queue.select_shard("default", tenant_id="enterprise_tenant")
        assert shard == "high_priority"

    def test_starvation_detection(self) -> None:
        """Shard starvation must be detectable."""
        from app.domains.distributed.queue import DistributedQueueOrchestrator

        queue = DistributedQueueOrchestrator()
        # Use a freshly created queue with known shards
        queue.update_metrics("default", depth=200, processing=0, latency_ms=0)

        import asyncio
        # Run check_starvation multiple times to trigger the counter
        for _ in range(5):
            asyncio.run(queue.check_starvation())
            queue.update_metrics("default", depth=200, processing=0, latency_ms=0)

        starving = asyncio.run(queue.check_starvation())
        # After multiple checks with depth > 100 and processing = 0, should detect starvation
        assert len(starving) > 0

    def test_metrics_update(self) -> None:
        """Shard metrics must be updatable."""
        from app.domains.distributed.queue import distributed_queue

        distributed_queue.update_metrics("ai_analysis", depth=50, processing=5, latency_ms=200)
        status = distributed_queue.get_shard_status()
        assert status["ai_analysis"]["depth"] == 50
        assert status["ai_analysis"]["processing"] == 5

    def test_strategy_setting(self) -> None:
        """Shard strategy must be changeable."""
        from app.domains.distributed.queue import DistributedQueueOrchestrator, ShardStrategy

        queue = DistributedQueueOrchestrator()
        queue.set_strategy(ShardStrategy.LEAST_LOADED)
        shard = queue.select_shard("default")
        assert shard is not None


# ═══════════════════════════════════════════════════════════════════
# 3. VECTOR SCALING ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestVectorScaling:
    """Validate vector scaling architecture."""

    def test_tier_enum_defined(self) -> None:
        """All vector tiers must be defined."""
        from app.domains.vectors.scaling import VectorTier

        assert VectorTier.HOT
        assert VectorTier.WARM
        assert VectorTier.COLD
        assert VectorTier.ARCHIVE

    def test_tier_resolution(self) -> None:
        """Tier resolution must match access frequency."""
        from app.domains.vectors.scaling import VectorScaleManager, VectorTier

        manager = VectorScaleManager()
        assert manager.resolve_tier(200) == VectorTier.HOT
        assert manager.resolve_tier(50) == VectorTier.WARM
        assert manager.resolve_tier(5) == VectorTier.COLD
        assert manager.resolve_tier(0) == VectorTier.ARCHIVE

    def test_tenant_shard_assignment(self) -> None:
        """Tenants must be assignable to shards."""
        from app.domains.vectors.scaling import vector_scale_manager

        shard = vector_scale_manager.assign_tenant_to_shard("new_tenant")
        assert shard is not None

    def test_semantic_cache(self) -> None:
        """Semantic cache must store and retrieve results."""
        from app.domains.vectors.scaling import vector_scale_manager

        key = vector_scale_manager.get_cache_key("test query", "tenant_001")
        vector_scale_manager.cache_set(key, "test query", ["chunk_1", "chunk_2"])

        cached = vector_scale_manager.cache_get(key)
        assert cached == ["chunk_1", "chunk_2"]

    def test_shard_rebalancing(self) -> None:
        """Shard rebalancing must produce actions."""
        from app.domains.vectors.scaling import VectorScaleManager

        manager = VectorScaleManager()
        import asyncio
        actions = asyncio.run(manager.rebalance())
        assert actions is not None

    def test_tenant_migration(self) -> None:
        """Tenant migration between shards must work."""
        from app.domains.vectors.scaling import VectorScaleManager

        manager = VectorScaleManager()
        from_shard = manager.assign_tenant_to_shard("migrating_tenant")
        to_shard = manager.assign_tenant_to_shard("another_tenant")

        import asyncio
        result = asyncio.run(manager.migrate_tenant("migrating_tenant", from_shard, to_shard))
        assert result["tenant_id"] == "migrating_tenant"
        assert result["from_shard"] == from_shard


# ═══════════════════════════════════════════════════════════════════
# 4. ADAPTIVE RUNTIME OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestRuntimeOptimization:
    """Validate adaptive runtime optimization."""

    def test_optimization_modes_defined(self) -> None:
        """All optimization modes must be defined."""
        from app.domains.optimization import OptimizationMode

        assert OptimizationMode.QUALITY
        assert OptimizationMode.BALANCED
        assert OptimizationMode.ECONOMY
        assert OptimizationMode.URGENT

    def test_quality_mode_selects_premium(self) -> None:
        """Quality mode must select premium model."""
        from app.domains.optimization import RuntimeOptimizer, OptimizationContext, OptimizationMode

        optimizer = RuntimeOptimizer()
        context = OptimizationContext(tenant_id="test", operation_type="analysis", mode=OptimizationMode.QUALITY)
        decision = optimizer.optimize(context)
        assert decision.selected_model in ("gpt-4-turbo", "gpt-4o")

    def test_economy_mode_selects_cheapest(self) -> None:
        """Economy mode must select cheapest model."""
        from app.domains.optimization import RuntimeOptimizer, OptimizationContext, OptimizationMode

        optimizer = RuntimeOptimizer()
        context = OptimizationContext(tenant_id="test", operation_type="analysis", mode=OptimizationMode.ECONOMY)
        decision = optimizer.optimize(context)
        assert decision.selected_model == "gpt-4o-mini"
        assert decision.estimated_cost < 0.01

    def test_balanced_mode_default(self) -> None:
        """Balanced mode is the default."""
        from app.domains.optimization import RuntimeOptimizer, OptimizationContext, OptimizationMode

        optimizer = RuntimeOptimizer()
        context = OptimizationContext(tenant_id="test", operation_type="analysis")
        decision = optimizer.optimize(context)
        assert decision is not None

    def test_model_selection_by_quality(self) -> None:
        """Model selection must respect quality requirements."""
        from app.domains.optimization import runtime_optimizer

        model, provider = runtime_optimizer.select_model_for_task("analysis", required_quality=0.9)
        assert model is not None

    def test_execution_recording(self) -> None:
        """Execution metrics must be recordable."""
        from app.domains.optimization import runtime_optimizer

        runtime_optimizer.record_execution("gpt-4o", cost=0.01, latency_ms=5000, quality=0.95)
        report = runtime_optimizer.get_optimization_report()
        assert report["total_executions"] > 0

    def test_chunk_count_estimation(self) -> None:
        """Chunk count must vary by mode."""
        from app.domains.optimization import RuntimeOptimizer, OptimizationMode

        optimizer = RuntimeOptimizer()
        quality_chunks = optimizer.estimate_chunk_count(10000, OptimizationMode.QUALITY)
        economy_chunks = optimizer.estimate_chunk_count(10000, OptimizationMode.ECONOMY)
        assert quality_chunks >= economy_chunks


# ═══════════════════════════════════════════════════════════════════
# 5. CONTRACT INTELLIGENCE GRAPH
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestIntelligenceGraph:
    """Validate contract intelligence graph expansion."""

    def test_intelligence_service_exists(self) -> None:
        """IntelligenceGraphService must exist with all methods."""
        from app.domains.intelligence import IntelligenceGraphService

        assert hasattr(IntelligenceGraphService, "get_obligation_dependencies")
        assert hasattr(IntelligenceGraphService, "get_vendor_intelligence")
        assert hasattr(IntelligenceGraphService, "get_risk_propagation")
        assert hasattr(IntelligenceGraphService, "get_intelligence_summary")

    def test_risk_propagation_score_structure(self) -> None:
        """RiskPropagationScore must have all fields."""
        from app.domains.intelligence import RiskPropagationScore

        score = RiskPropagationScore(
            clause_id="clause_001",
            direct_risk_score=0.7,
            propagated_risk_score=0.3,
            affected_obligations=5,
            affected_contracts=3,
            propagation_depth=2,
        )
        assert score.clause_id == "clause_001"
        assert score.direct_risk_score == 0.7
        assert score.propagated_risk_score == 0.3

    def test_vendor_relationship_structure(self) -> None:
        """VendorRelationship must have all fields."""
        from app.domains.intelligence import VendorRelationship

        vendor = VendorRelationship(
            vendor_id="vendor_001",
            vendor_name="Test Corp",
            contract_count=10,
            total_risk_score=0.45,
            relationship_score=0.55,
        )
        assert vendor.vendor_name == "Test Corp"
        assert vendor.contract_count == 10
        assert -1.0 <= vendor.relationship_score <= 1.0

    def test_obligation_dependency_structure(self) -> None:
        """ObligationDependency must have all fields."""
        from app.domains.intelligence import ObligationDependency

        dep = ObligationDependency(
            source_obligation_id="src_001",
            target_obligation_id="tgt_001",
            dependency_type="prerequisite",
        )
        assert dep.dependency_type == "prerequisite"


# ═══════════════════════════════════════════════════════════════════
# 6. BENCHMARK INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestBenchmarkIntelligence:
    """Validate benchmark intelligence engine."""

    def test_benchmark_categories_defined(self) -> None:
        """All benchmark categories must be defined."""
        from app.domains.benchmark.intelligence import BenchmarkCategory

        required = ["CLAUSE_QUALITY", "NEGOTIATION_EFFECTIVENESS", "VENDOR_RISK", "RENEWAL_RISK"]
        for c in required:
            assert hasattr(BenchmarkCategory, c), f"Missing category: {c}"

    def test_clause_scoring(self) -> None:
        """Clause scoring must produce percentile."""
        from app.domains.benchmark.intelligence import benchmark_intelligence

        score = benchmark_intelligence.score_clause("liability", your_score=0.8)
        assert 0.0 <= score.percentile <= 100.0
        assert score.score == 0.8

    def test_market_deviation_analysis(self) -> None:
        """Market deviation must compare against corpus."""
        from app.domains.benchmark.intelligence import benchmark_intelligence

        deviation = benchmark_intelligence.analyze_market_deviation("indemnification", your_score=0.9)
        assert deviation.your_score == 0.9
        assert deviation.market_average > 0
        assert deviation.deviation > 0  # Above average

    def test_renewal_risk_forecasting(self) -> None:
        """Renewal risk must identify risk factors."""
        from app.domains.benchmark.intelligence import benchmark_intelligence
        from datetime import datetime, timedelta

        forecast = benchmark_intelligence.forecast_renewal_risk(
            contract_id="c_001",
            contract_name="Test Contract",
            counterparty="Test Corp",
            renewal_date=(datetime.utcnow() + timedelta(days=15)).isoformat(),
            current_risk_score=0.8,
        )
        assert len(forecast.risk_factors) > 0
        assert forecast.risk_score > 0

    def test_industry_norms(self) -> None:
        """Industry norms must return corpus data."""
        from app.domains.benchmark.intelligence import benchmark_intelligence

        norms = benchmark_intelligence.get_industry_norms("liability")
        assert "industry_average" in norms
        assert "industry_median" in norms

    def test_benchmark_dashboard(self) -> None:
        """Benchmark dashboard must list available clause types."""
        from app.domains.benchmark.intelligence import benchmark_intelligence

        dashboard = benchmark_intelligence.get_benchmark_dashboard()
        assert len(dashboard["available_clause_types"]) > 0


# ═══════════════════════════════════════════════════════════════════
# 7. AI LEARNING LOOP
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestAILearningLoop:
    """Validate AI learning loop."""

    def test_learning_signal_types_defined(self) -> None:
        """All signal types must be defined."""
        from app.domains.learning import LearningSignalType

        required = ["REVIEWER_ACCEPTED", "REVIEWER_REJECTED", "REVIEWER_MODIFIED",
                     "FALSE_POSITIVE", "FALSE_NEGATIVE"]
        for s in required:
            assert hasattr(LearningSignalType, s), f"Missing signal type: {s}"

    def test_signal_recording(self) -> None:
        """Learning signals must be recordable."""
        from app.domains.learning import ai_learning_loop, LearningSignal, LearningSignalType

        signal = LearningSignal(
            signal_id="sig_001",
            signal_type=LearningSignalType.REVIEWER_ACCEPTED,
            execution_id="exec_001",
            tenant_id="tenant_001",
            confidence=0.85,
        )
        ai_learning_loop.record_signal(signal)
        dashboard = ai_learning_loop.get_learning_dashboard()
        assert dashboard["total_signals"] > 0

    def test_reviewer_feedback_recording(self) -> None:
        """Reviewer feedback must create learning signals."""
        from app.domains.learning import ai_learning_loop

        signal = ai_learning_loop.record_reviewer_feedback(
            execution_id="exec_002",
            finding_id="finding_001",
            tenant_id="tenant_001",
            reviewer_action="accepted",
            ai_confidence=0.9,
        )
        assert signal.signal_type.value == "reviewer_accepted"

    def test_consensus_scoring(self) -> None:
        """Consensus scoring must track agreement rates."""
        from app.domains.learning import ai_learning_loop

        ai_learning_loop.record_reviewer_feedback("exec_1", "finding_a", "t1", "accepted", 0.9)
        ai_learning_loop.record_reviewer_feedback("exec_2", "finding_a", "t1", "accepted", 0.9)
        ai_learning_loop.record_reviewer_feedback("exec_3", "finding_a", "t1", "rejected", 0.9)

        score = ai_learning_loop.get_consensus_score("finding_a")
        assert score is not None
        assert score.total_reviews == 3
        assert score.accepted_count == 2
        assert score.rejected_count == 1

    def test_false_positive_clustering(self) -> None:
        """False-positive clusters must be detectable."""
        from app.domains.learning import ai_learning_loop, LearningSignal, LearningSignalType

        for i in range(5):
            ai_learning_loop.record_signal(LearningSignal(
                signal_id=f"fp_{i}",
                signal_type=LearningSignalType.REVIEWER_REJECTED,
                execution_id=f"exec_{i}",
                tenant_id="t1",
                details={"clause_type": "liability"},
            ))

        clusters = ai_learning_loop.get_false_positive_clusters(min_signals=3)
        assert len(clusters) > 0

    def test_learning_dashboard(self) -> None:
        """Learning dashboard must show acceptance rate."""
        from app.domains.learning import ai_learning_loop

        dashboard = ai_learning_loop.get_learning_dashboard()
        assert "acceptance_rate" in dashboard
        assert "total_signals" in dashboard


# ═══════════════════════════════════════════════════════════════════
# 8. CROSS-CONTRACT INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestCrossContractIntelligence:
    """Validate cross-contract intelligence."""

    def test_cross_contract_service_exists(self) -> None:
        """CrossContractIntelligenceService must exist."""
        from app.domains.intelligence.cross_contract import CrossContractIntelligenceService

        assert hasattr(CrossContractIntelligenceService, "find_duplicate_obligations")
        assert hasattr(CrossContractIntelligenceService, "find_conflicting_clauses")
        assert hasattr(CrossContractIntelligenceService, "analyze_renewal_overlap")
        assert hasattr(CrossContractIntelligenceService, "get_cross_contract_summary")

    def test_text_similarity(self) -> None:
        """Text similarity must work."""
        from app.domains.intelligence.cross_contract import CrossContractIntelligenceService

        service = object.__new__(CrossContractIntelligenceService)
        similarity = service._text_similarity("hello world", "hello world")
        assert similarity > 0.9

        similarity = service._text_similarity("hello world", "completely different text")
        assert similarity < 0.5

    def test_duplicate_obligation_structure(self) -> None:
        """DuplicateObligation must have all fields."""
        from app.domains.intelligence.cross_contract import DuplicateObligation, ConflictSeverity

        dup = DuplicateObligation(
            obligation_text="Test obligation",
            contract_a_id="c_a",
            contract_a_name="Contract A",
            contract_b_id="c_b",
            contract_b_name="Contract B",
            similarity_score=0.95,
            severity=ConflictSeverity.HIGH,
        )
        assert dup.similarity_score == 0.95
        assert dup.severity == ConflictSeverity.HIGH

    def test_conflicting_clause_structure(self) -> None:
        """ConflictingClause must have all fields."""
        from app.domains.intelligence.cross_contract import ConflictingClause, ConflictSeverity

        conflict = ConflictingClause(
            clause_type="liability",
            contract_a_id="c_a",
            contract_a_text="Cap at $1M",
            contract_b_id="c_b",
            contract_b_text="Cap at $5M",
            conflict_type="inconsistent_terms",
            severity=ConflictSeverity.CRITICAL,
        )
        assert conflict.conflict_type == "inconsistent_terms"
        assert conflict.severity == ConflictSeverity.CRITICAL


# ═══════════════════════════════════════════════════════════════════
# 9. WORKFLOW BUILDER
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestWorkflowBuilder:
    """Validate workflow builder backend."""

    def test_default_templates_registered(self) -> None:
        """Default workflow templates must be registered."""
        from app.domains.workflows.builder import workflow_builder

        templates = workflow_builder.list_templates()
        assert len(templates) >= 2
        template_ids = [t["template_id"] for t in templates]
        assert "standard_review" in template_ids
        assert "high_risk_review" in template_ids

    def test_workflow_node_types_defined(self) -> None:
        """All workflow node types must be defined."""
        from app.domains.workflows.builder import WorkflowNodeType

        required = ["START", "END", "AI_ANALYSIS", "HUMAN_REVIEW", "APPROVAL_GATE",
                     "CONDITION", "ESCALATION", "SLA_TIMER", "NOTIFICATION", "EXPORT"]
        for n in required:
            assert hasattr(WorkflowNodeType, n), f"Missing node type: {n}"

    def test_template_crud(self) -> None:
        """Workflow templates must support CRUD."""
        from app.domains.workflows.builder import WorkflowBuilderService, WorkflowTemplate

        builder = WorkflowBuilderService()
        template = WorkflowTemplate(
            template_id="test_template",
            name="Test Workflow",
            description="A test workflow",
        )
        builder.save_template(template)
        assert builder.get_template("test_template") is not None

        builder.delete_template("test_template")
        assert builder.get_template("test_template") is None

    def test_workflow_validation(self) -> None:
        """Workflow validation must detect issues."""
        from app.domains.workflows.builder import WorkflowBuilderService, WorkflowTemplate, WorkflowNode, WorkflowNodeType, WorkflowEdge

        builder = WorkflowBuilderService()

        # Missing start/end
        invalid = WorkflowTemplate(
            template_id="invalid",
            name="Invalid",
            description="Missing start and end",
            nodes=[
                WorkflowNode(node_id="n1", node_type=WorkflowNodeType.AI_ANALYSIS, label="AI"),
            ],
        )
        errors = builder.validate_workflow(invalid)
        assert len(errors) > 0
        assert any("START" in e for e in errors)

        # Valid workflow
        valid = WorkflowTemplate(
            template_id="valid",
            name="Valid",
            description="Valid workflow",
            nodes=[
                WorkflowNode(node_id="start", node_type=WorkflowNodeType.START, label="Start"),
                WorkflowNode(node_id="ai", node_type=WorkflowNodeType.AI_ANALYSIS, label="AI"),
                WorkflowNode(node_id="end", node_type=WorkflowNodeType.END, label="End"),
            ],
            edges=[
                WorkflowEdge(edge_id="e1", source_node_id="start", target_node_id="ai"),
                WorkflowEdge(edge_id="e2", source_node_id="ai", target_node_id="end"),
            ],
        )
        errors = builder.validate_workflow(valid)
        assert len(errors) == 0

    def test_workflow_simulation(self) -> None:
        """Workflow simulation must produce a path."""
        from app.domains.workflows.builder import WorkflowBuilderService, WorkflowTemplate, WorkflowNode, WorkflowNodeType, WorkflowEdge

        builder = WorkflowBuilderService()
        template = WorkflowTemplate(
            template_id="sim_test",
            name="Sim Test",
            description="For simulation testing",
            nodes=[
                WorkflowNode(node_id="start", node_type=WorkflowNodeType.START, label="Start"),
                WorkflowNode(node_id="ai", node_type=WorkflowNodeType.AI_ANALYSIS, label="AI"),
                WorkflowNode(node_id="end", node_type=WorkflowNodeType.END, label="End"),
            ],
            edges=[
                WorkflowEdge(edge_id="e1", source_node_id="start", target_node_id="ai"),
                WorkflowEdge(edge_id="e2", source_node_id="ai", target_node_id="end"),
            ],
        )
        result = builder.simulate_workflow(template)
        assert result["valid"] is True
        assert len(result["simulation"]["path"]) == 3  # start, ai, end

    def test_workflow_edge_condition(self) -> None:
        """Workflow edges must support conditions."""
        from app.domains.workflows.builder import WorkflowEdge

        edge = WorkflowEdge(
            edge_id="e1",
            source_node_id="legal_review",
            target_node_id="escalation",
            condition="sla_breached",
            label="Escalate if SLA breached",
        )
        assert edge.condition == "sla_breached"
        assert edge.label == "Escalate if SLA breached"
