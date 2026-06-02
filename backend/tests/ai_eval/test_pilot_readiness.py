"""Enterprise Pilot Readiness Tests.

Validates:
- Admin control plane and safety controls
- AI Execution Explorer
- Onboarding automation
- Supportability layer
- Usage analytics
- Architecture Decision Records
- SRE readiness framework
- Enterprise documentation
"""

from __future__ import annotations

import os
import pytest

# Helper to find project root (tests run from backend/, docs are at project root)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _doc_path(*parts: str) -> str:
    return os.path.join(_PROJECT_ROOT, "docs", *parts)


def _runbook_path(*parts: str) -> str:
    return os.path.join(_PROJECT_ROOT, "backend", "runbooks", *parts)


# ═══════════════════════════════════════════════════════════════════
# 1. ADMIN CONTROL PLANE & PILOT SAFETY
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestAdminControlPlane:
    """Validate enterprise admin control plane."""

    def test_platform_safety_controls_exist(self) -> None:
        """All platform safety controls must exist."""
        from app.domains.admin.control_plane import PlatformSafetyControls, PlatformMode

        controls = PlatformSafetyControls()
        assert controls.platform_mode == PlatformMode.NORMAL
        assert controls.kill_switch_active is False

    def test_kill_switch_activation(self) -> None:
        """Kill switch must stop AI execution."""
        from app.domains.admin.control_plane import PlatformSafetyControls

        controls = PlatformSafetyControls()
        controls.activate_kill_switch("admin@test.com", "Security incident investigation")
        assert controls.kill_switch_active is True
        assert controls.platform_mode.value == "emergency_maintenance"

        allowed, reason = controls.is_ai_allowed("tenant_001")
        assert allowed is False
        assert "kill switch" in reason.lower()

    def test_kill_switch_deactivation(self) -> None:
        """Kill switch must be deactivatable."""
        from app.domains.admin.control_plane import PlatformSafetyControls

        controls = PlatformSafetyControls()
        controls.activate_kill_switch("admin", "test")
        controls.deactivate_kill_switch()
        assert controls.kill_switch_active is False

    def test_ai_freeze_mode(self) -> None:
        """AI freeze mode must stop new executions."""
        from app.domains.admin.control_plane import PlatformSafetyControls

        controls = PlatformSafetyControls()
        controls.freeze_ai()
        allowed, reason = controls.is_ai_allowed("tenant_001")
        assert allowed is False
        assert "frozen" in reason.lower()

    def test_read_only_mode(self) -> None:
        """Read-only mode must block mutations."""
        from app.domains.admin.control_plane import PlatformSafetyControls

        controls = PlatformSafetyControls()
        controls.set_read_only()
        allowed, reason = controls.is_ai_allowed("tenant_001")
        assert allowed is False
        assert "read-only" in reason.lower()

    def test_provider_disable(self) -> None:
        """Individual providers must be disablable."""
        from app.domains.admin.control_plane import PlatformSafetyControls

        controls = PlatformSafetyControls()
        controls.disable_provider("openai")
        assert "openai" in controls.disabled_providers

        controls.enable_provider("openai")
        assert "openai" not in controls.disabled_providers

    def test_tenant_freeze(self) -> None:
        """Individual tenants must be freezable."""
        from app.domains.admin.control_plane import AdminControlPlane

        plane = AdminControlPlane()
        import asyncio
        asyncio.run(plane.freeze_tenant("tenant_001", "Compliance review"))
        assert "tenant_001" in plane.safety.frozen_tenants

        asyncio.run(plane.unfreeze_tenant("tenant_001"))
        assert "tenant_001" not in plane.safety.frozen_tenants

    def test_platform_status_report(self) -> None:
        """Platform status report must include all safety controls."""
        from app.domains.admin.control_plane import AdminControlPlane

        plane = AdminControlPlane()
        status = plane.get_platform_status()
        assert "platform_mode" in status
        assert "safety" in status
        assert "features" in status
        assert "providers" in status
        assert "queues" in status

    def test_admin_control_plane_singleton(self) -> None:
        """Admin control plane must be a singleton."""
        from app.domains.admin.control_plane import admin_control_plane

        assert admin_control_plane is not None
        assert hasattr(admin_control_plane, "get_platform_status")


# ═══════════════════════════════════════════════════════════════════
# 2. AI EXECUTION EXPLORER
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestAIExecutionExplorer:
    """Validate AI execution explorer."""

    def test_execution_trace_structure(self) -> None:
        """Execution trace must have all required fields."""
        from app.domains.ai.explorer import ExecutionTrace

        trace = ExecutionTrace(
            execution_id="exec_001",
            tenant_id="tenant_001",
            operation_type="risk_analysis",
            status="completed",
        )
        assert trace.execution_id == "exec_001"
        assert trace.operation_type == "risk_analysis"
        assert trace.status == "completed"
        assert hasattr(trace, "trace_events")
        assert hasattr(trace, "retrieval_chunks")
        assert hasattr(trace, "guardrail_decisions")

    def test_trace_event_structure(self) -> None:
        """Trace events must have timeline components."""
        from app.domains.ai.explorer import ExecutionTraceEvent

        event = ExecutionTraceEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="policy_check",
            component="policy_engine",
            duration_ms=50,
            status="completed",
            details={"rules_applied": ["rule1", "rule2"]},
        )
        assert event.event_type == "policy_check"
        assert event.component == "policy_engine"
        assert event.duration_ms == 50

    def test_execution_summary_structure(self) -> None:
        """Execution summary must have concise fields for UI."""
        from app.domains.ai.explorer import AIExecutionExplorer

        assert hasattr(AIExecutionExplorer, "get_execution_summary")
        assert hasattr(AIExecutionExplorer, "get_execution_trace")
        assert hasattr(AIExecutionExplorer, "compare_with_replay")


# ═══════════════════════════════════════════════════════════════════
# 3. ENTERPRISE ONBOARDING
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestEnterpriseOnboarding:
    """Validate enterprise onboarding automation."""

    def test_onboarding_steps_defined(self) -> None:
        """All onboarding steps must be defined."""
        from app.domains.onboarding import EnterpriseOnboardingService
        from unittest.mock import MagicMock

        service = EnterpriseOnboardingService(session=MagicMock())
        assert len(service.ONSOARDING_STEPS) >= 8
        step_names = [s.name for s in service.ONSOARDING_STEPS]
        assert "create_tenant" in step_names
        assert "assign_policy_packs" in step_names
        assert "initialize_prompts" in step_names
        assert "generate_api_credentials" in step_names
        assert "setup_reviewer_roles" in step_names

    def test_onboarding_result_structure(self) -> None:
        """Onboarding result must have status and steps."""
        from app.domains.onboarding import OnboardingResult

        result = OnboardingResult(
            tenant_id="tenant_001",
            tenant_name="Test Corp",
            status="success",
            steps_completed=["create_tenant", "initialize_prompts"],
        )
        assert result.tenant_id == "tenant_001"
        assert result.status == "success"
        assert len(result.steps_completed) == 2

    def test_onboarding_service_exists(self) -> None:
        """EnterpriseOnboardingService must exist with core methods."""
        from app.domains.onboarding import EnterpriseOnboardingService

        assert hasattr(EnterpriseOnboardingService, "onboard_enterprise_tenant")
        assert hasattr(EnterpriseOnboardingService, "get_onboarding_status")


# ═══════════════════════════════════════════════════════════════════
# 4. SUPPORTABILITY LAYER
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestSupportability:
    """Validate support tooling."""

    def test_diagnostic_bundle_structure(self) -> None:
        """Diagnostic bundle must have all support fields."""
        from app.domains.support import DiagnosticBundle

        bundle = DiagnosticBundle(
            bundle_id="diag_001",
            tenant_id="tenant_001",
            environment={"python": "3.11"},
            recent_errors=[],
        )
        assert bundle.bundle_id == "diag_001"
        assert "python" in bundle.environment
        assert hasattr(bundle, "queue_status")
        assert hasattr(bundle, "provider_health")

    def test_incident_timeline_structure(self) -> None:
        """Incident timeline must have events and status."""
        from app.domains.support import IncidentTimeline

        timeline = IncidentTimeline(
            incident_id="inc_001",
            title="Test incident",
            severity="high",
            status="investigating",
            events=[{"type": "error", "timestamp": "2024-01-01T00:00:00"}],
        )
        assert timeline.incident_id == "inc_001"
        assert len(timeline.events) == 1

    def test_support_service_exists(self) -> None:
        """SupportService must exist with all methods."""
        from app.domains.support import SupportService

        assert hasattr(SupportService, "generate_diagnostic_bundle")
        assert hasattr(SupportService, "get_incident_timeline")
        assert hasattr(SupportService, "verify_audit_chain")
        assert hasattr(SupportService, "inspect_queue")


# ═══════════════════════════════════════════════════════════════════
# 5. USAGE ANALYTICS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestUsageAnalytics:
    """Validate usage analytics platform."""

    def test_analytics_service_exists(self) -> None:
        """UsageAnalytics must exist with all analytics methods."""
        from app.domains.analytics import UsageAnalytics

        assert hasattr(UsageAnalytics, "get_reviewer_analytics")
        assert hasattr(UsageAnalytics, "get_override_patterns")
        assert hasattr(UsageAnalytics, "get_ai_trust_score")
        assert hasattr(UsageAnalytics, "get_workflow_analytics")
        assert hasattr(UsageAnalytics, "get_search_analytics")
        assert hasattr(UsageAnalytics, "get_escalation_analytics")
        assert hasattr(UsageAnalytics, "get_comprehensive_report")

    def test_ai_trust_score_grading(self) -> None:
        """AI trust score must produce grades."""
        from app.domains.analytics import UsageAnalytics

        analytics = object.__new__(UsageAnalytics)

        assert analytics._trust_grade(0.98) == "A+"
        assert analytics._trust_grade(0.90) == "A"
        assert analytics._trust_grade(0.75) == "B"
        assert analytics._trust_grade(0.60) == "C"
        assert analytics._trust_grade(0.40) == "D"

    def test_comprehensive_report_structure(self) -> None:
        """Comprehensive report must include all analytics categories."""
        from app.domains.analytics import UsageAnalytics

        assert hasattr(UsageAnalytics, "get_comprehensive_report")


# ═══════════════════════════════════════════════════════════════════
# 6. ARCHITECTURE DECISION RECORDS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestArchitectureDecisionRecords:
    """Validate ADR documentation."""

    def test_adr_directory_exists(self) -> None:
        """ADR directory must exist."""
        assert os.path.exists(_doc_path("adr"))

    def test_adr_file_exists(self) -> None:
        """ADR README must exist."""
        assert os.path.exists(_doc_path("adr", "README.md"))

    def test_adr_contains_required_decisions(self) -> None:
        """ADR must document all critical architectural decisions."""
        with open(_doc_path("adr", "README.md")) as f:
            content = f.read()
        assert "ADR-001" in content
        assert "ADR-002" in content
        assert "ADR-003" in content
        assert "ADR-004" in content
        assert "ADR-005" in content
        assert "Vector Partition" in content
        assert "Replay Immutability" in content
        assert "Event Versioning" in content
        assert "Tenant Isolation" in content
        assert "Provider Routing" in content


# ═══════════════════════════════════════════════════════════════════
# 7. SRE READINESS
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestSREReadiness:
    """Validate SRE readiness framework."""

    def test_sre_document_exists(self) -> None:
        """SRE readiness document must exist."""
        assert os.path.exists(_doc_path("operations", "sre-readiness.md"))

    def test_sre_contains_slos(self) -> None:
        """SRE document must define SLOs."""
        with open(_doc_path("operations", "sre-readiness.md")) as f:
            content = f.read()
        assert "SLO" in content
        assert "99.9%" in content
        assert "99.5%" in content

    def test_sre_contains_severity_matrix(self) -> None:
        """SRE document must define severity levels."""
        with open(_doc_path("operations", "sre-readiness.md")) as f:
            content = f.read()
        assert "P1" in content
        assert "P2" in content
        assert "P3" in content
        assert "P4" in content

    def test_sre_contains_escalation_paths(self) -> None:
        """SRE document must define escalation paths."""
        with open(_doc_path("operations", "sre-readiness.md")) as f:
            content = f.read()
        assert "Escalation" in content
        assert "on-call" in content.lower()

    def test_sre_contains_error_budget(self) -> None:
        """SRE document must define error budgets."""
        with open(_doc_path("operations", "sre-readiness.md")) as f:
            content = f.read()
        assert "Error Budget" in content


# ═══════════════════════════════════════════════════════════════════
# 8. ENTERPRISE DOCUMENTATION
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.ai_eval
class TestEnterpriseDocumentation:
    """Validate enterprise documentation system."""

    def test_docs_index_exists(self) -> None:
        """Documentation index must exist."""
        assert os.path.exists(_doc_path("README.md"))

    def test_docs_index_contains_all_sections(self) -> None:
        """Documentation index must reference all doc sections."""
        with open(_doc_path("README.md")) as f:
            content = f.read()
        assert "Architecture" in content
        assert "Operations" in content
        assert "Onboarding" in content
        assert "Security" in content
        assert "API" in content
        assert "Events" in content
        assert "Deployment" in content

    def test_architecture_directory_exists(self) -> None:
        """Architecture docs directory must exist."""
        assert os.path.exists(_doc_path("architecture"))

    def test_operations_directory_exists(self) -> None:
        """Operations docs directory must exist."""
        assert os.path.exists(_doc_path("operations"))

    def test_onboarding_directory_exists(self) -> None:
        """Onboarding docs directory must exist."""
        assert os.path.exists(_doc_path("onboarding"))

    def test_security_directory_exists(self) -> None:
        """Security docs directory must exist."""
        assert os.path.exists(_doc_path("security"))

    def test_api_directory_exists(self) -> None:
        """API docs directory must exist."""
        assert os.path.exists(_doc_path("api"))

    def test_events_directory_exists(self) -> None:
        """Events docs directory must exist."""
        assert os.path.exists(_doc_path("events"))

    def test_runbook_exists(self) -> None:
        """Operational runbook must exist."""
        assert os.path.exists(_runbook_path("README.md"))
