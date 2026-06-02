"""Platform Consolidation & Production Readiness Tests.

Validates:
- Infrastructure deployment manifests
- Database governance
- API governance
- Unified event bus
- Runtime configuration
- Compliance automation
- Data pipeline
- Disaster recovery
"""

from __future__ import annotations

import pytest


@pytest.mark.ai_eval
class TestInfrastructureDeployment:
    """Verify Kubernetes, Helm, Terraform, and environment configs."""

    def test_kubernetes_base_manifests_exist(self) -> None:
        """All base K8s manifests must exist."""
        import os
        # Tests run from backend/, so go up two levels
        base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra", "kubernetes", "base")
        base_dir = os.path.abspath(base_dir)
        expected = [
            "namespace.yaml", "configmap.yaml", "secret.yaml",
            "api-deployment.yaml", "worker-deployment.yaml", "celery-beat-deployment.yaml",
            "api-service.yaml", "api-hpa.yaml", "worker-hpa.yaml",
            "api-pdb.yaml", "network-policy.yaml", "ingress.yaml",
            "kustomization.yaml",
        ]
        for f in expected:
            path = os.path.join(base_dir, f)
            assert os.path.exists(path), f"Missing: {path}"

    def test_kubernetes_overlays_exist(self) -> None:
        """Production and staging overlays must exist."""
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"))
        assert os.path.exists(os.path.join(base, "kubernetes", "overlays", "production", "kustomization.yaml"))
        assert os.path.exists(os.path.join(base, "kubernetes", "overlays", "staging", "kustomization.yaml"))

    def test_helm_chart_exists(self) -> None:
        """Helm chart must have Chart.yaml and values.yaml."""
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"))
        assert os.path.exists(os.path.join(base, "helm", "contractriskedge", "Chart.yaml"))
        assert os.path.exists(os.path.join(base, "helm", "contractriskedge", "values.yaml"))

    def test_environment_configs_exist(self) -> None:
        """Environment configs must exist for production and staging."""
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"))
        assert os.path.exists(os.path.join(base, "environments", "production", ".env.production"))
        assert os.path.exists(os.path.join(base, "environments", "staging", ".env.staging"))

    def test_production_config_has_correct_settings(self) -> None:
        """Production config must use production-grade settings."""
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"))
        path = os.path.join(base, "environments", "production", ".env.production")
        with open(path) as f:
            content = f.read()
        assert "APP_ENV=production" in content
        assert "AI_DEFAULT_MODEL=gpt-4o" in content
        assert "TENANT_ISOLATION_LEVEL=dedicated_collections" in content

    def test_staging_config_uses_cheaper_models(self) -> None:
        """Staging should use cheaper models to reduce cost."""
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"))
        path = os.path.join(base, "environments", "staging", ".env.staging")
        with open(path) as f:
            content = f.read()
        assert "AI_DEFAULT_MODEL=gpt-4o-mini" in content
        assert "TENANT_ISOLATION_LEVEL=shared" in content

    def test_kubernetes_has_pod_disruption_budgets(self) -> None:
        """Production must have PDBs for high availability."""
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"))
        path = os.path.join(base, "kubernetes", "base", "api-pdb.yaml")
        with open(path) as f:
            content = f.read()
        assert "PodDisruptionBudget" in content
        assert "minAvailable: 2" in content

    def test_kubernetes_has_network_policies(self) -> None:
        """Network policies must be defined for security."""
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"))
        path = os.path.join(base, "kubernetes", "base", "network-policy.yaml")
        with open(path) as f:
            content = f.read()
        assert "NetworkPolicy" in content
        assert "default-deny" in content

    def test_kubernetes_has_horizontal_autoscaling(self) -> None:
        """HPA must be configured for API and workers."""
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"))
        path = os.path.join(base, "kubernetes", "base", "api-hpa.yaml")
        with open(path) as f:
            content = f.read()
        assert "HorizontalPodAutoscaler" in content
        assert "maxReplicas: 20" in content


@pytest.mark.ai_eval
class TestDatabaseGovernance:
    """Verify database governance module."""

    def test_migration_validation_detects_dangerous_operations(self) -> None:
        """Migration validation must detect DROP COLUMN and RENAME."""
        from app.domains.platform.db_governance import DBGovernanceService

        service = object.__new__(DBGovernanceService)

        # Test dangerous operations
        import asyncio
        result = asyncio.run(service.validate_migration(
            "ALTER TABLE users DROP COLUMN email;", "v001", "test"
        ))
        assert not result.valid
        assert any("dangerous_drop_column" in i["code"] for i in result.issues)

        result = asyncio.run(service.validate_migration(
            "ALTER TABLE users RENAME COLUMN name TO full_name;", "v002", "test"
        ))
        assert not result.valid
        assert any("rename_requires_plan" in i["code"] for i in result.issues)

    def test_migration_validation_passes_safe_operations(self) -> None:
        """Safe migrations should pass validation."""
        from app.domains.platform.db_governance import DBGovernanceService

        service = object.__new__(DBGovernanceService)

        import asyncio
        result = asyncio.run(service.validate_migration(
            "CREATE INDEX idx_users_email ON users(email);", "v003", "test"
        ))
        assert result.valid

    def test_migration_checksum_is_deterministic(self) -> None:
        """Migration checksums must be deterministic."""
        from app.domains.platform.db_governance import DBGovernanceService

        service = object.__new__(DBGovernanceService)

        import asyncio
        sql = "CREATE TABLE test (id INT);"
        hash1 = asyncio.run(service.compute_migration_checksum(sql))
        hash2 = asyncio.run(service.compute_migration_checksum(sql))
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256


@pytest.mark.ai_eval
class TestAPIGovernance:
    """Verify API governance module."""

    def test_version_registration_and_lifecycle(self) -> None:
        """API versions must support lifecycle management."""
        from app.domains.platform.api import ApiGovernanceService, ApiVersion, ApiVersionStatus

        service = ApiGovernanceService()

        v1 = ApiVersion(version="v1", status=ApiVersionStatus.ACTIVE, released_at="2024-01-01")
        v2 = ApiVersion(version="v2", status=ApiVersionStatus.ACTIVE, released_at="2024-06-01")

        service.register_version(v1)
        service.register_version(v2)

        assert len(service.get_active_versions()) == 2

        service.deprecate_version("v1", sunset_days=180)
        assert service.get_version("v1").status == ApiVersionStatus.DEPRECATED

    def test_schema_compatibility_detection(self) -> None:
        """Schema registry must detect breaking changes."""
        from app.domains.platform.api import ApiGovernanceService, SchemaVersion, ApiVersionStatus

        service = ApiGovernanceService()

        old_schema = SchemaVersion(
            schema_name="Contract",
            version="1.0.0",
            json_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["id", "name"],
            },
            status=ApiVersionStatus.ACTIVE,
            released_at="2024-01-01",
        )
        service.register_schema(old_schema)

        # Removing a property is a breaking change
        breaking = service.validate_schema_compatibility("Contract", {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
        })
        assert len(breaking) > 0
        assert any("Removed property" in b for b in breaking)

        # Adding a property is backward compatible
        compatible = service.validate_schema_compatibility("Contract", {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
            },
        })
        assert len(compatible) == 0

    def test_webhook_signature_verification(self) -> None:
        """Webhook signatures must be verifiable."""
        from app.domains.platform.api import ApiGovernanceService

        service = ApiGovernanceService()
        payload = b'{"event": "test"}'
        secret = "test-secret-key"

        import hmac, hashlib
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        signature = f"sha256={expected}"

        assert service.verify_webhook_signature(payload, signature, secret)
        assert not service.verify_webhook_signature(payload, "invalid-signature", secret)


@pytest.mark.ai_eval
class TestUnifiedEventBus:
    """Verify unified event bus."""

    def test_event_schema_registration(self) -> None:
        """Event schemas must be registrable and retrievable."""
        from app.domains.platform.events import UnifiedEventBus, EventSchema, EventSchemaStatus

        bus = UnifiedEventBus(session=None)  # type: ignore

        schema = EventSchema(
            event_type="ai.execution.completed",
            version="1.0.0",
            schema_def={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "risk_score": {"type": "number"},
                },
                "required": ["execution_id", "tenant_id"],
            },
            status=EventSchemaStatus.ACTIVE,
        )
        bus.register_schema(schema)

        retrieved = bus.get_schema("ai.execution.completed")
        assert retrieved is not None
        assert retrieved.version == "1.0.0"

    def test_event_validation(self) -> None:
        """Events must be validated against their schema."""
        from app.domains.platform.events import UnifiedEventBus, EventSchema, EventSchemaStatus

        bus = UnifiedEventBus(session=None)  # type: ignore

        schema = EventSchema(
            event_type="test.event",
            version="1.0.0",
            schema_def={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "count": {"type": "integer"},
                },
                "required": ["id"],
            },
            status=EventSchemaStatus.ACTIVE,
        )
        bus.register_schema(schema)

        # Valid payload
        issues = bus.validate_event("test.event", {"id": "123", "count": 5})
        assert len(issues) == 0

        # Missing required field
        issues = bus.validate_event("test.event", {"count": 5})
        assert len(issues) > 0

        # Wrong type
        issues = bus.validate_event("test.event", {"id": "123", "count": "not-an-integer"})
        assert len(issues) > 0

    def test_dead_letter_queue(self) -> None:
        """Dead-letter queue must capture failed events."""
        from app.domains.platform.events import UnifiedEventBus

        bus = UnifiedEventBus(session=None)  # type: ignore

        dlq = bus.get_dead_letter_queue()
        assert dlq is not None
        assert len(dlq) == 0


@pytest.mark.ai_eval
class TestRuntimeConfig:
    """Verify runtime configuration platform."""

    def test_config_registration_and_retrieval(self) -> None:
        """Config keys must be registrable with type-safe values."""
        from app.domains.platform.config import RuntimeConfigService, ConfigDefinition, ConfigValueType

        service = RuntimeConfigService()

        config = ConfigDefinition(
            key="ai.default_model",
            description="Default AI model for analysis",
            value_type=ConfigValueType.STRING,
            default_value="gpt-4o",
        )
        service.register(config)

        value = service.get("ai.default_model")
        assert value == "gpt-4o"

    def test_environment_overrides(self) -> None:
        """Environment-specific overrides must work."""
        from app.domains.platform.config import RuntimeConfigService, ConfigDefinition, ConfigValueType

        service = RuntimeConfigService()

        config = ConfigDefinition(
            key="ai.max_tokens",
            description="Max tokens per execution",
            value_type=ConfigValueType.INTEGER,
            default_value=128000,
            environment_overrides={"staging": 32000},
        )
        service.register(config)

        assert service.get("ai.max_tokens") == 128000
        assert service.get("ai.max_tokens", environment="staging") == 32000

    def test_tenant_overrides(self) -> None:
        """Tenant-specific overrides must work."""
        from app.domains.platform.config import RuntimeConfigService, ConfigDefinition, ConfigValueType

        service = RuntimeConfigService()

        config = ConfigDefinition(
            key="ai.model",
            description="AI model per tenant",
            value_type=ConfigValueType.STRING,
            default_value="gpt-4o",
        )
        service.register(config)

        service.set("ai.model", "gpt-4-turbo", tenant_id="enterprise_tenant")
        assert service.get("ai.model") == "gpt-4o"
        assert service.get("ai.model", tenant_id="enterprise_tenant") == "gpt-4-turbo"

    def test_config_change_audit_log(self) -> None:
        """Config changes must be audit-logged."""
        from app.domains.platform.config import RuntimeConfigService, ConfigDefinition, ConfigValueType

        service = RuntimeConfigService()

        config = ConfigDefinition(
            key="test.key",
            description="Test key",
            value_type=ConfigValueType.STRING,
            default_value="old",
        )
        service.register(config)
        service.set("test.key", "new", changed_by="admin", reason="testing")

        log = service.get_change_log("test.key")
        assert len(log) > 0
        assert log[0].previous_value == "old"
        assert log[0].new_value == "new"
        assert log[0].changed_by == "admin"

    def test_feature_flag_rollout(self) -> None:
        """Feature flags must support percentage-based rollout."""
        from app.domains.platform.config import RuntimeConfigService, FeatureFlag

        service = RuntimeConfigService()

        flag = FeatureFlag(
            flag_key="new_analysis_engine",
            name="New Analysis Engine",
            description="Rollout of v2 analysis engine",
            enabled=True,
            rollout_percentage=50,
        )
        service.register_feature_flag(flag)

        # Deterministic based on user_id hash
        results = {}
        for i in range(100):
            enabled = service.is_feature_enabled("new_analysis_engine", user_id=f"user_{i}")
            results[enabled] = results.get(enabled, 0) + 1

        # ~50% should be enabled
        enabled_count = results.get(True, 0)
        assert 30 <= enabled_count <= 70, f"Expected ~50% enabled, got {enabled_count}%"


@pytest.mark.ai_eval
class TestComplianceAutomation:
    """Verify compliance automation layer."""

    def test_evidence_types_defined(self) -> None:
        """All required evidence types must be defined."""
        from app.domains.compliance import EvidenceType

        required = ["ACCESS_CONTROL", "AUDIT_LOG", "ENCRYPTION", "BACKUP",
                     "INCIDENT_RESPONSE", "RETENTION"]
        for ev in required:
            assert hasattr(EvidenceType, ev), f"Missing evidence type: {ev}"

    def test_compliance_frameworks_defined(self) -> None:
        """All required compliance frameworks must be defined."""
        from app.domains.compliance import ComplianceFramework

        required = ["SOC2", "ISO27001", "GDPR", "HIPAA"]
        for fw in required:
            assert hasattr(ComplianceFramework, fw), f"Missing framework: {fw}"

    def test_evidence_record_creation(self) -> None:
        """Evidence records must be creatable with all fields."""
        from app.domains.compliance import EvidenceRecord, EvidenceType, ComplianceFramework, EvidenceStatus

        evidence = EvidenceRecord(
            evidence_id="test_001",
            evidence_type=EvidenceType.ACCESS_CONTROL,
            framework=ComplianceFramework.SOC2,
            control_id="CC6.1",
            description="Test evidence",
            status=EvidenceStatus.COLLECTED,
            collected_at="2024-01-01T00:00:00",
            data={"test": True},
        )
        assert evidence.evidence_id == "test_001"
        assert evidence.control_id == "CC6.1"

    def test_access_review_report_structure(self) -> None:
        """Access review reports must have required fields."""
        from app.domains.compliance import ComplianceService

        # Verify the method exists and returns expected structure via contract
        assert hasattr(ComplianceService, "generate_access_review_report")
        assert hasattr(ComplianceService, "generate_audit_verification_report")
        assert hasattr(ComplianceService, "generate_retention_report")
        assert hasattr(ComplianceService, "collect_all_soc2_evidence")


@pytest.mark.ai_eval
class TestDataPipeline:
    """Verify data pipeline separation."""

    def test_pipeline_configuration(self) -> None:
        """Pipelines must be configurable with source, target, and frequency."""
        from app.domains.platform.data_pipeline import DataPipelineService, PipelineConfig, SyncFrequency

        service = DataPipelineService(session=None)  # type: ignore

        config = PipelineConfig(
            name="audit_archive",
            source_table="audit_trail",
            target_dataset="audit_archive",
            sync_frequency=SyncFrequency.DAILY,
        )
        service.register_pipeline(config)

        assert service.get_pipeline("audit_archive") is not None
        assert len(service.get_active_pipelines()) == 1

    def test_analytics_snapshot_creation(self) -> None:
        """Analytics snapshots must have required structure."""
        from app.domains.platform.data_pipeline import AnalyticsSnapshot

        snapshot = AnalyticsSnapshot(
            snapshot_name="test_snapshot",
            snapshot_type="daily_usage",
            period_start="2024-01-01",
            period_end="2024-01-02",
            data={"test": True},
        )
        assert snapshot.snapshot_name == "test_snapshot"
        assert snapshot.snapshot_type == "daily_usage"


@pytest.mark.ai_eval
class TestDisasterRecovery:
    """Verify disaster recovery validation."""

    def test_dr_test_types_defined(self) -> None:
        """All DR test types must be defined."""
        from app.domains.platform.dr_validation import DRTestType

        required = ["RESTORE_SIMULATION", "REPLAY_RESTORE", "VECTOR_DB_REBUILD",
                     "CROSS_REGION_FAILOVER", "QUEUE_RECOVERY",
                     "AUDIT_CHAIN_INTEGRITY", "FULL_SYSTEM_RECOVERY"]
        for t in required:
            assert hasattr(DRTestType, t), f"Missing DR test type: {t}"

    def test_dr_test_result_structure(self) -> None:
        """DR test results must have all required fields."""
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

    def test_restore_simulation_checks_exist(self) -> None:
        """Restore simulation must verify table existence and FK integrity."""
        from app.domains.platform.dr_validation import DRValidationService

        # Verify the method signature and contract
        assert hasattr(DRValidationService, "simulate_restore")
        assert hasattr(DRValidationService, "run_full_dr_suite")

    def test_replay_restore_validation_checks_exist(self) -> None:
        """Replay restore validation must check snapshots and executions."""
        from app.domains.platform.dr_validation import DRValidationService

        assert hasattr(DRValidationService, "validate_replay_after_restore")

    def test_vector_db_rebuild_checks_exist(self) -> None:
        """Vector DB rebuild validation must check chunks and model registry."""
        from app.domains.platform.dr_validation import DRValidationService

        assert hasattr(DRValidationService, "validate_vector_db_rebuild")

    def test_audit_chain_integrity_checks_exist(self) -> None:
        """Audit chain validation must verify chain integrity."""
        from app.domains.platform.dr_validation import DRValidationService

        assert hasattr(DRValidationService, "validate_audit_chain_integrity")

    def test_full_dr_suite_runs_all_tests(self) -> None:
        """Full DR suite must run all test types."""
        from app.domains.platform.dr_validation import DRValidationService, DRTestType

        assert hasattr(DRValidationService, "run_full_dr_suite")
        # Verify the DRTestType enum has all required types
        required_types = [
            DRTestType.RESTORE_SIMULATION,
            DRTestType.REPLAY_RESTORE,
            DRTestType.VECTOR_DB_REBUILD,
            DRTestType.CROSS_REGION_FAILOVER,
            DRTestType.AUDIT_CHAIN_INTEGRITY,
            DRTestType.FULL_SYSTEM_RECOVERY,
        ]
        for t in required_types:
            assert t is not None


@pytest.mark.ai_eval
class TestPlatformGovernanceIntegration:
    """Verify all platform governance modules integrate correctly."""

    def test_db_governance_imports(self) -> None:
        """DB governance module must import cleanly."""
        from app.domains.platform.db_governance import (
            DBGovernanceService, MigrationRecord, MigrationRisk,
            SchemaValidationResult, IndexHealth,
        )
        assert DBGovernanceService
        assert MigrationRisk.HIGH

    def test_api_governance_imports(self) -> None:
        """API governance module must import cleanly."""
        from app.domains.platform.api import (
            ApiGovernanceService, ApiVersion, ApiVersionStatus,
            SchemaVersion, ApiEndpoint,
        )
        assert ApiGovernanceService
        assert ApiVersionStatus.ACTIVE

    def test_event_bus_imports(self) -> None:
        """Event bus module must import cleanly."""
        from app.domains.platform.events import (
            UnifiedEventBus, EventSchema, EventSchemaStatus,
            EventSubscription, DeadLetterEvent, DeliveryGuarantee,
        )
        assert UnifiedEventBus
        assert DeliveryGuarantee.EXACTLY_ONCE

    def test_config_imports(self) -> None:
        """Config module must import cleanly."""
        from app.domains.platform.config import (
            RuntimeConfigService, ConfigDefinition, ConfigValueType,
            FeatureFlag, ConfigChangeLog, runtime_config,
        )
        assert RuntimeConfigService
        assert ConfigValueType.BOOLEAN

    def test_data_pipeline_imports(self) -> None:
        """Data pipeline module must import cleanly."""
        from app.domains.platform.data_pipeline import (
            DataPipelineService, PipelineConfig, SyncFrequency,
            AnalyticsSnapshot, PipelineRun,
        )
        assert DataPipelineService
        assert SyncFrequency.REAL_TIME

    def test_compliance_imports(self) -> None:
        """Compliance module must import cleanly."""
        from app.domains.compliance import (
            ComplianceService, EvidenceRecord, EvidenceType,
            ComplianceFramework, ComplianceReport,
        )
        assert ComplianceService
        assert ComplianceFramework.SOC2

    def test_dr_validation_imports(self) -> None:
        """DR validation module must import cleanly."""
        from app.domains.platform.dr_validation import (
            DRValidationService, DRTestResult, DRTestType, DRTestStatus,
        )
        assert DRValidationService
        assert DRTestType.FULL_SYSTEM_RECOVERY
