"""Operational Resilience & Chaos Validation Tests.

Validates:
- Chaos Engineering Framework (failure injectors, scenarios, resilience scoring)
- Replay Consistency Validation (drift, retrieval, embedding version)
- Event Ordering Validation (sequencing, dedup, out-of-order)
- Cross-Tenant Isolation Stress Testing
- Config Drift Detection (stale rollouts, tenant mismatch, orphan configs)
- DR Simulation Automation
- Operational Runbooks
"""

from __future__ import annotations

import pytest


# ═══════════════════════════════════════════════════════════════════
# 1. CHAOS ENGINEERING FRAMEWORK
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestChaosEngineering:
    """Validate the chaos engineering framework."""

    def test_failure_injectors_registered(self) -> None:
        """All default failure injectors must be registered."""
        from app.domains.platform.chaos import chaos_engineering, FailureMode

        assert chaos_engineering.get_injector("provider_outage") is not None
        assert chaos_engineering.get_injector("queue_corruption") is not None
        assert chaos_engineering.get_injector("vector_db_latency") is not None
        assert chaos_engineering.get_injector("stuck_workflow") is not None
        assert chaos_engineering.get_injector("config_inconsistency") is not None

    def test_chaos_scenarios_registered(self) -> None:
        """All default chaos scenarios must be registered."""
        from app.domains.platform.chaos import chaos_engineering

        scenarios = chaos_engineering.list_scenarios()
        scenario_names = [s["name"] for s in scenarios]
        assert "provider_failover" in scenario_names
        assert "queue_resilience" in scenario_names
        assert "vector_db_stress" in scenario_names
        assert "multi_failure" in scenario_names
        assert "full_system_stress" in scenario_names

    def test_failure_injector_injection(self) -> None:
        """Failure injectors must produce injection results."""
        from app.domains.platform.chaos import ProviderOutageInjector

        injector = ProviderOutageInjector()
        import asyncio
        result = asyncio.run(injector.inject())
        assert result["failure"] == "provider_outage"
        assert "affected_providers" in result
        assert "expected_behavior" in result

    def test_failure_injector_recovery(self) -> None:
        """Failure injectors must produce recovery results."""
        from app.domains.platform.chaos import QueueCorruptionInjector

        injector = QueueCorruptionInjector()
        import asyncio
        result = asyncio.run(injector.recover())
        assert result["recovery"] == "queue_corruption"

    def test_failure_modes_defined(self) -> None:
        """All required failure modes must be defined."""
        from app.domains.platform.chaos import FailureMode

        required = [
            "PROVIDER_OUTAGE", "QUEUE_CORRUPTION", "REDIS_FAILURE",
            "VECTOR_DB_LATENCY", "WEBHOOK_FAILURE", "STUCK_WORKFLOW",
            "WORKER_CRASH", "PARTIAL_DEPLOYMENT", "REPLAY_CORRUPTION",
            "CONFIG_INCONSISTENCY", "DB_CONNECTION_DROP",
        ]
        for mode in required:
            assert hasattr(FailureMode, mode), f"Missing failure mode: {mode}"

    def test_recovery_strategies_defined(self) -> None:
        """All recovery strategies must be defined."""
        from app.domains.platform.chaos import RecoveryStrategy

        assert RecoveryStrategy.AUTOMATIC
        assert RecoveryStrategy.MANUAL
        assert RecoveryStrategy.DEGRADED
        assert RecoveryStrategy.FAIL_SAFE

    def test_resilience_scoring(self) -> None:
        """Resilience scoring must produce grades."""
        from app.domains.platform.chaos import ResilienceScore

        a_plus = ResilienceScore(dimension="test", score=0.98)
        assert a_plus.grade == "A+"

        failing = ResilienceScore(dimension="test", score=0.2)
        assert failing.grade == "F"

    def test_vector_db_latency_injector(self) -> None:
        """Vector DB latency injector must have configurable parameters."""
        from app.domains.platform.chaos import VectorDBLatencyInjector

        injector = VectorDBLatencyInjector(latency_multiplier=10.0, affected_queries_pct=1.0)
        assert injector.latency_multiplier == 10.0
        assert injector.affected_queries_pct == 1.0


# ═══════════════════════════════════════════════════════════════════
# 2. REPLAY CONSISTENCY VALIDATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestReplayConsistency:
    """Validate replay consistency detection."""

    @pytest.fixture
    def validator(self):
        from app.domains.platform.consistency import ReplayConsistencyValidator
        return ReplayConsistencyValidator()

    def test_consistent_replay_passes(self, validator) -> None:
        """Identical runs should be consistent."""
        import asyncio
        result = asyncio.run(validator.validate_replay_consistency(
            original_run={"model": "gpt-4o", "provider": "openai", "prompt_version": 3, "risk_score": 0.5, "findings_count": 5},
            replay_run={"model": "gpt-4o", "provider": "openai", "prompt_version": 3, "risk_score": 0.5, "findings_count": 5},
        ))
        assert result.status.value == "consistent"
        assert result.score == 1.0

    def test_model_mismatch_detected(self, validator) -> None:
        """Different models should be flagged."""
        import asyncio
        result = asyncio.run(validator.validate_replay_consistency(
            original_run={"model": "gpt-4o", "provider": "openai", "prompt_version": 3, "risk_score": 0.5, "findings_count": 5},
            replay_run={"model": "gpt-4-turbo", "provider": "openai", "prompt_version": 3, "risk_score": 0.5, "findings_count": 5},
        ))
        assert result.score < 1.0
        assert "model mismatch" in result.details.lower()

    def test_prompt_version_mismatch_detected(self, validator) -> None:
        """Different prompt versions should be flagged."""
        import asyncio
        result = asyncio.run(validator.validate_replay_consistency(
            original_run={"model": "gpt-4o", "provider": "openai", "prompt_version": 2, "risk_score": 0.5, "findings_count": 5},
            replay_run={"model": "gpt-4o", "provider": "openai", "prompt_version": 3, "risk_score": 0.5, "findings_count": 5},
        ))
        assert result.score < 0.8
        assert "prompt version" in result.details.lower()

    def test_risk_score_drift_detected(self, validator) -> None:
        """Large risk score drift should be flagged."""
        import asyncio
        result = asyncio.run(validator.validate_replay_consistency(
            original_run={"model": "gpt-4o", "provider": "openai", "prompt_version": 3, "risk_score": 0.3, "findings_count": 5},
            replay_run={"model": "gpt-4o", "provider": "openai", "prompt_version": 3, "risk_score": 0.8, "findings_count": 5},
        ))
        assert result.score < 0.7
        assert "risk score drift" in result.details.lower()

    def test_embedding_version_consistency(self, validator) -> None:
        """Stale embedding models should be detected."""
        import asyncio
        result = asyncio.run(validator.validate_embedding_version_consistency(
            active_model="text-embedding-3-large",
            chunks_by_model={
                "text-embedding-3-large": 800,
                "text-embedding-ada-002": 200,
            },
        ))
        assert result.score < 1.0
        assert result.affected_count == 200


# ═══════════════════════════════════════════════════════════════════
# 3. EVENT ORDERING VALIDATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestEventConsistency:
    """Validate event ordering and idempotency."""

    @pytest.fixture
    def validator(self):
        from app.domains.platform.consistency import EventConsistencyValidator
        return EventConsistencyValidator()

    def test_in_order_events_pass(self, validator) -> None:
        """Events in correct order should pass."""
        import asyncio
        result = asyncio.run(validator.check_event_ordering("test.event", 1))
        assert result.status.value == "consistent"

        result = asyncio.run(validator.check_event_ordering("test.event", 2))
        assert result.status.value == "consistent"

    def test_out_of_order_detected(self, validator) -> None:
        """Out-of-order events should be detected."""
        import asyncio
        asyncio.run(validator.check_event_ordering("test.event", 5))
        result = asyncio.run(validator.check_event_ordering("test.event", 3))
        assert result.status.value != "consistent"

    def test_sequence_gap_detected(self, validator) -> None:
        """Sequence gaps should be detected."""
        import asyncio
        asyncio.run(validator.check_event_ordering("test.event", 1))
        result = asyncio.run(validator.check_event_ordering("test.event", 10))
        assert result.score < 1.0
        assert "gap" in result.details.lower()

    def test_idempotency_deduplication(self, validator) -> None:
        """Duplicate idempotency keys should be detected."""
        import asyncio
        result1 = asyncio.run(validator.check_idempotency("key123", "event1"))
        assert result1.status.value == "consistent"

        result2 = asyncio.run(validator.check_idempotency("key123", "event2"))
        assert result2.status.value != "consistent"
        assert "duplicate" in result2.details.lower()

    def test_event_batch_validation(self, validator) -> None:
        """Batch event validation should produce a report."""
        import asyncio
        events = [
            {"event_id": "e1", "event_type": "test", "sequence_number": 1, "idempotency_key": "k1"},
            {"event_id": "e2", "event_type": "test", "sequence_number": 2, "idempotency_key": "k2"},
            {"event_id": "e3", "event_type": "test", "sequence_number": 3, "idempotency_key": "k3"},
        ]
        report = asyncio.run(validator.validate_event_batch(events, expected_type="test"))
        assert report.overall_score == 1.0
        assert report.passed_count > 0


# ═══════════════════════════════════════════════════════════════════
# 4. CROSS-TENANT ISOLATION STRESS TESTING
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestCrossTenantIsolationStress:
    """Validate cross-tenant isolation under stress."""

    def test_isolation_validator_exists(self) -> None:
        """CrossTenantIsolationValidator must exist."""
        from app.domains.platform.consistency import CrossTenantIsolationValidator

        assert hasattr(CrossTenantIsolationValidator, "simulate_concurrent_tenants")
        assert hasattr(CrossTenantIsolationValidator, "detect_query_leakage")
        assert hasattr(CrossTenantIsolationValidator, "detect_telemetry_contamination")
        assert hasattr(CrossTenantIsolationValidator, "run_isolation_stress_suite")

    def test_concurrent_tenant_simulation(self) -> None:
        """Must simulate 100+ tenants without violations."""
        from app.domains.platform.consistency import CrossTenantIsolationValidator

        validator = CrossTenantIsolationValidator()
        import asyncio
        violations = asyncio.run(validator.simulate_concurrent_tenants(
            tenant_count=100,
            operations_per_tenant=10,
        ))
        assert len(violations) == 0

    def test_query_leakage_detection(self) -> None:
        """Query leakage must be detectable."""
        from app.domains.platform.consistency import CrossTenantIsolationValidator

        validator = CrossTenantIsolationValidator()
        import asyncio

        # Simulate leaky queries
        leaky_queries = [
            {
                "tenant_id": "tenant_a",
                "results": [{"tenant_id": "tenant_a"}, {"tenant_id": "tenant_b"}],  # Leak!
            }
        ]
        violations = asyncio.run(validator.detect_query_leakage(leaky_queries))
        assert len(violations) == 1
        assert violations[0].violation_type == "query_leakage"
        assert violations[0].severity == "critical"

    def test_clean_queries_no_leakage(self) -> None:
        """Clean queries must not produce violations."""
        from app.domains.platform.consistency import CrossTenantIsolationValidator

        validator = CrossTenantIsolationValidator()
        import asyncio

        clean_queries = [
            {
                "tenant_id": "tenant_a",
                "results": [{"tenant_id": "tenant_a"}, {"tenant_id": "tenant_a"}],
            }
        ]
        violations = asyncio.run(validator.detect_query_leakage(clean_queries))
        assert len(violations) == 0

    def test_telemetry_contamination_detection(self) -> None:
        """Telemetry contamination must be detectable."""
        from app.domains.platform.consistency import CrossTenantIsolationValidator

        validator = CrossTenantIsolationValidator()
        import asyncio

        contaminated = [
            {"reported_tenant_id": "tenant_a", "actual_tenant_id": "tenant_b"},
        ]
        violations = asyncio.run(validator.detect_telemetry_contamination(contaminated))
        assert len(violations) == 1

    def test_isolation_stress_suite(self) -> None:
        """Full isolation stress suite must run cleanly."""
        from app.domains.platform.consistency import CrossTenantIsolationValidator

        validator = CrossTenantIsolationValidator()
        import asyncio
        result = asyncio.run(validator.run_isolation_stress_suite())
        assert result["passed"] is True
        assert "recommendations" in result


# ═══════════════════════════════════════════════════════════════════
# 5. CONFIG DRIFT DETECTION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestConfigDriftDetection:
    """Validate configuration drift detection."""

    @pytest.fixture
    def detector(self):
        from app.domains.platform.config.drift import ConfigDriftDetector
        d = ConfigDriftDetector()
        d.set_baseline("ai.default_model", "gpt-4o")
        d.set_baseline("ai.max_tokens", 128000)
        d.set_baseline("retention.days", 2555)
        return d

    def test_tenant_mismatch_detected(self, detector) -> None:
        """Tenant config drift should be detected."""
        import asyncio
        drifts = asyncio.run(detector.check_tenant_mismatch(
            tenant_id="tenant_123",
            tenant_config={"ai.default_model": "gpt-4o-mini"},  # Drifted!
        ))
        assert len(drifts) == 1
        assert drifts[0].drift_type.value == "tenant_mismatch"
        assert drifts[0].config_key == "ai.default_model"

    def test_tenant_with_override_not_flagged(self, detector) -> None:
        """Tenants with deliberate overrides should not be flagged."""
        import asyncio
        drifts = asyncio.run(detector.check_tenant_mismatch(
            tenant_id="tenant_123",
            tenant_config={"ai.default_model": "gpt-4o-mini"},
            baseline_overrides={"ai.default_model": "gpt-4o-mini"},
        ))
        assert len(drifts) == 0

    def test_environment_consistency_check(self, detector) -> None:
        """Environment inconsistencies should be detected."""
        import asyncio
        drifts = asyncio.run(detector.check_environment_consistency(
            env_a="staging",
            config_a={"ai.default_model": "gpt-4o-mini", "log_level": "DEBUG"},
            env_b="production",
            config_b={"ai.default_model": "gpt-4o", "log_level": "INFO"},
        ))
        assert len(drifts) == 2

    def test_expected_differences_not_flagged(self, detector) -> None:
        """Expected differences between environments should not be flagged."""
        import asyncio
        drifts = asyncio.run(detector.check_environment_consistency(
            env_a="staging",
            config_a={"ai.default_model": "gpt-4o-mini", "log_level": "DEBUG"},
            env_b="production",
            config_b={"ai.default_model": "gpt-4o", "log_level": "INFO"},
            expected_differences={"ai.default_model", "log_level"},
        ))
        assert len(drifts) == 0

    def test_stale_rollout_detected(self, detector) -> None:
        """Feature flags stuck in rollout should be detected."""
        import asyncio
        from datetime import datetime, timedelta

        stale_flags = {
            "new_engine": {
                "rollout_percentage": 50,
                "created_at": (datetime.utcnow() - timedelta(days=60)).isoformat(),
            }
        }
        drifts = asyncio.run(detector.check_stale_rollouts(
            stale_flags,
            staleness_threshold_days=30,
        ))
        assert len(drifts) == 1
        assert drifts[0].drift_type.value == "stale_rollout"

    def test_orphan_config_detected(self, detector) -> None:
        """Unreferenced config keys should be detected."""
        import asyncio
        detector.register_config_key("old.config.key")
        drifts = asyncio.run(detector.check_orphan_configs(
            active_config_keys={"ai.default_model", "ai.max_tokens", "retention.days"},
        ))
        assert len(drifts) == 1
        assert drifts[0].drift_type.value == "orphan_config"
        assert drifts[0].config_key == "old.config.key"

    def test_prompt_version_drift_detected(self, detector) -> None:
        """Prompt version drift should be detected."""
        import asyncio
        drifts = asyncio.run(detector.check_prompt_version_drift(
            tenant_prompt_versions={
                "tenant_001": {"risk_analysis": "1.0.0"},
                "tenant_002": {"risk_analysis": "2.0.0"},  # Drifted!
            },
            expected_active_versions={"risk_analysis": "2.0.0"},
        ))
        assert len(drifts) == 1
        assert drifts[0].drift_type.value == "prompt_version_drift"

    def test_full_drift_scan(self, detector) -> None:
        """Full drift scan must produce a report."""
        import asyncio
        report = asyncio.run(detector.run_full_drift_scan(
            tenant_configs={
                "tenant_001": {"ai.default_model": "gpt-4o-mini"},  # Drifted
            },
            environment_configs={
                "staging": {"log_level": "DEBUG"},
                "production": {"log_level": "INFO"},
            },
            feature_flags={
                "slow_rollout": {
                    "rollout_percentage": 25,
                    "created_at": "2024-01-01T00:00:00",
                },
            },
            active_config_keys={"ai.default_model"},
        ))
        assert report.total_drifts > 0
        assert hasattr(report, "recommendations")


# ═══════════════════════════════════════════════════════════════════
# 6. DR SIMULATION AUTOMATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestDRSimulation:
    """Validate DR simulation automation."""

    def test_dr_validation_service_exists(self) -> None:
        """DRValidationService must exist with all methods."""
        from app.domains.platform.dr_validation import DRValidationService

        assert hasattr(DRValidationService, "simulate_restore")
        assert hasattr(DRValidationService, "validate_replay_after_restore")
        assert hasattr(DRValidationService, "validate_vector_db_rebuild")
        assert hasattr(DRValidationService, "validate_cross_region_failover")
        assert hasattr(DRValidationService, "validate_audit_chain_integrity")
        assert hasattr(DRValidationService, "run_full_dr_suite")

    def test_dr_test_types_defined(self) -> None:
        """All DR test types must exist."""
        from app.domains.platform.dr_validation import DRTestType

        required = [
            "RESTORE_SIMULATION", "REPLAY_RESTORE", "VECTOR_DB_REBUILD",
            "CROSS_REGION_FAILOVER", "QUEUE_RECOVERY",
            "AUDIT_CHAIN_INTEGRITY", "FULL_SYSTEM_RECOVERY",
        ]
        for t in required:
            assert hasattr(DRTestType, t), f"Missing DR test type: {t}"

    def test_dr_test_result_structure(self) -> None:
        """DR test results must have required fields."""
        from app.domains.platform.dr_validation import DRTestResult, DRTestStatus, DRTestType

        result = DRTestResult(
            test_id="dr_001",
            test_type=DRTestType.RESTORE_SIMULATION,
            status=DRTestStatus.PASSED,
            started_at="2024-01-01T00:00:00",
            passed_checks=5,
            failed_checks=0,
            total_checks=5,
        )
        assert result.test_id == "dr_001"
        assert result.status == DRTestStatus.PASSED
        assert result.passed_checks == 5


# ═══════════════════════════════════════════════════════════════════
# 7. OPERATIONAL RUNBOOKS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestOperationalRunbooks:
    """Validate operational runbooks exist and cover critical scenarios."""

    def test_runbook_file_exists(self) -> None:
        """Runbook README must exist."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        assert os.path.exists(path), f"Runbook not found at {path}"

    def test_runbook_contains_provider_outage(self) -> None:
        """Runbook must cover provider outage recovery."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        with open(path) as f:
            content = f.read()
        assert "PROVIDER OUTAGE" in content
        assert "Circuit Breaker" in content
        assert "kubectl" in content

    def test_runbook_contains_replay_corruption(self) -> None:
        """Runbook must cover replay corruption recovery."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        with open(path) as f:
            content = f.read()
        assert "REPLAY CORRUPTION" in content
        assert "ReplayAIExecutionService" in content

    def test_runbook_contains_tenant_isolation_incident(self) -> None:
        """Runbook must cover tenant isolation incidents."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        with open(path) as f:
            content = f.read()
        assert "TENANT ISOLATION" in content
        assert "tenant_id" in content

    def test_runbook_contains_deployment_rollback(self) -> None:
        """Runbook must cover deployment rollback."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        with open(path) as f:
            content = f.read()
        assert "DEPLOYMENT ROLLBACK" in content
        assert "kubectl rollout undo" in content
        assert "helm rollback" in content

    def test_runbook_contains_vector_db_rebuild(self) -> None:
        """Runbook must cover vector DB rebuild."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        with open(path) as f:
            content = f.read()
        assert "VECTOR DB REBUILD" in content
        assert "ReIndexScheduler" in content

    def test_runbook_contains_stuck_workflow_recovery(self) -> None:
        """Runbook must cover stuck workflow recovery."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        with open(path) as f:
            content = f.read()
        assert "STUCK WORKFLOW" in content
        assert "WorkflowExecutionEngine" in content

    def test_runbook_contains_config_drift_resolution(self) -> None:
        """Runbook must cover config drift resolution."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        with open(path) as f:
            content = f.read()
        assert "CONFIGURATION DRIFT" in content
        assert "ConfigDriftDetector" in content

    def test_runbook_contains_event_bus_failure(self) -> None:
        """Runbook must cover event bus failure."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        with open(path) as f:
            content = f.read()
        assert "EVENT BUS FAILURE" in content
        assert "UnifiedEventBus" in content

    def test_runbook_contains_poison_message_cleanup(self) -> None:
        """Runbook must cover poison message cleanup."""
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks", "README.md")
        with open(path) as f:
            content = f.read()
        assert "POISON MESSAGE" in content
        assert "ReliableQueueManager" in content


# ═══════════════════════════════════════════════════════════════════
# 8. RESILIENCE ASSESSMENT INTEGRATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestResilienceAssessment:
    """Validate the complete resilience assessment pipeline."""

    def test_resilience_assessment_runs(self) -> None:
        """Full resilience assessment must complete."""
        from app.domains.platform.chaos import chaos_engineering

        import asyncio
        report = asyncio.run(chaos_engineering.assess_resilience())

        assert report.overall_score > 0
        assert report.overall_grade is not None
        assert len(report.dimensions) > 0
        assert len(report.recommendations) > 0

    def test_resilience_dimensions_covered(self) -> None:
        """All critical resilience dimensions must be assessed."""
        from app.domains.platform.chaos import chaos_engineering

        import asyncio
        report = asyncio.run(chaos_engineering.assess_resilience())

        dimension_names = [d.dimension for d in report.dimensions]
        assert "provider_failover" in dimension_names
        assert "queue_resilience" in dimension_names
        assert "vector_db_resilience" in dimension_names
        assert "multi_failure_resilience" in dimension_names
        assert "config_consistency" in dimension_names

    def test_consistency_validator_imports(self) -> None:
        """All consistency validators must import cleanly."""
        from app.domains.platform.consistency import (
            ReplayConsistencyValidator,
            EventConsistencyValidator,
            CrossTenantIsolationValidator,
            ConsistencyCheck,
            ConsistencyReport,
            ConsistencyStatus,
        )
        assert ReplayConsistencyValidator
        assert EventConsistencyValidator
        assert ConsistencyStatus.CONSISTENT

    def test_config_drift_types_defined(self) -> None:
        """All drift types must be defined."""
        from app.domains.platform.config.drift import DriftType

        required = [
            "STALE_ROLLOUT", "TENANT_MISMATCH", "ENVIRONMENT_INCONSISTENCY",
            "ORPHAN_CONFIG", "INVALID_POLICY_CHAIN", "PROMPT_VERSION_DRIFT",
            "EMBEDDING_MODEL_DRIFT", "RETENTION_POLICY_DRIFT",
        ]
        for dt in required:
            assert hasattr(DriftType, dt), f"Missing drift type: {dt}"

    def test_event_consistency_validator_reset(self) -> None:
        """Event consistency validator must support reset."""
        from app.domains.platform.consistency import EventConsistencyValidator

        validator = EventConsistencyValidator()
        import asyncio

        asyncio.run(validator.check_idempotency("key1", "event1"))
        validator.reset()

        # After reset, same key should not be flagged as duplicate
        result = asyncio.run(validator.check_idempotency("key1", "event2"))
        assert result.status.value == "consistent"


# ═══════════════════════════════════════════════════════════════════
# 9. CHAOS SCENARIO EXECUTION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestChaosScenarioExecution:
    """Validate chaos scenario execution and recovery."""

    def test_provider_failover_scenario(self) -> None:
        """Provider failover scenario must execute and recover."""
        from app.domains.platform.chaos import chaos_engineering

        import asyncio
        result = asyncio.run(chaos_engineering.run_scenario("provider_failover"))
        assert result["scenario"] == "provider_failover"
        assert len(result["injections"]) > 0
        assert len(result["recoveries"]) > 0

    def test_queue_resilience_scenario(self) -> None:
        """Queue resilience scenario must execute and recover."""
        from app.domains.platform.chaos import chaos_engineering

        import asyncio
        result = asyncio.run(chaos_engineering.run_scenario("queue_resilience"))
        assert result["scenario"] == "queue_resilience"

    def test_vector_db_stress_scenario(self) -> None:
        """Vector DB stress scenario must execute and recover."""
        from app.domains.platform.chaos import chaos_engineering

        import asyncio
        result = asyncio.run(chaos_engineering.run_scenario("vector_db_stress"))
        assert result["scenario"] == "vector_db_stress"

    def test_multi_failure_scenario(self) -> None:
        """Multi-failure scenario must execute and recover."""
        from app.domains.platform.chaos import chaos_engineering

        import asyncio
        result = asyncio.run(chaos_engineering.run_scenario("multi_failure"))
        assert result["scenario"] == "multi_failure"

    def test_chaos_scenario_listing(self) -> None:
        """Scenario listing must return all scenarios."""
        from app.domains.platform.chaos import chaos_engineering

        scenarios = chaos_engineering.list_scenarios()
        assert len(scenarios) >= 5  # At least the 5 default scenarios
        for s in scenarios:
            assert "name" in s
            assert "description" in s
            assert "injector_count" in s
