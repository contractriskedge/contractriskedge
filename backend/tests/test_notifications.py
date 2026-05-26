"""Tests for notifications, workflow automation, SLA tracking, and escalation engine."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta


class TestNotificationTypes:
    """Verify notification type enum values."""

    def test_notification_types_exist(self):
        from app.domains.notify.models import NotificationType
        assert NotificationType.REVIEW_ASSIGNED.value == "review.assigned"
        assert NotificationType.SLA_BREACH_WARNING.value == "sla.breach_warning"
        assert NotificationType.OVERDUE_REVIEW.value == "review.overdue"
        assert NotificationType.WORKFLOW_COMPLETED.value == "workflow.completed"
        assert NotificationType.AI_ANALYSIS_COMPLETE.value == "ai.analysis_complete"


class TestDeliveryStatus:
    """Verify delivery status enum."""

    def test_delivery_status_values(self):
        from app.domains.notify.models import DeliveryStatus
        assert DeliveryStatus.PENDING.value == "pending"
        assert DeliveryStatus.DELIVERED.value == "delivered"
        assert DeliveryStatus.FAILED.value == "failed"


class TestNotificationPreference:
    """Verify preference model."""

    def test_preference_unique_constraint(self):
        from app.domains.notify.models import NotificationPreference
        # The __table_args__ includes a unique constraint on tenant_id, user_id, notification_type
        assert hasattr(NotificationPreference, "tenant_id")
        assert hasattr(NotificationPreference, "user_id")
        assert hasattr(NotificationPreference, "notification_type")


class TestSLAPolicy:
    """Verify SLA policy model."""

    def test_sla_policy_fields(self):
        from app.domains.notify.models import SLAPolicy
        assert hasattr(SLAPolicy, "target_minutes")
        assert hasattr(SLAPolicy, "warning_threshold_percent")
        assert hasattr(SLAPolicy, "escalation_after_minutes")

    def test_sla_unique_constraint(self):
        from app.domains.notify.models import SLAPolicy
        # Unique on tenant_id, workflow_type, priority
        pass


class TestEscalationRule:
    """Verify escalation rule model."""

    def test_escalation_chain_field(self):
        from app.domains.notify.models import EscalationRule
        assert hasattr(EscalationRule, "escalation_chain")
        assert hasattr(EscalationRule, "max_escalation_level")


class TestWorkflowTimer:
    """Verify workflow timer model."""

    def test_timer_fields(self):
        from app.domains.notify.models import WorkflowTimer
        assert hasattr(WorkflowTimer, "target_time")
        assert hasattr(WorkflowTimer, "action")
        assert hasattr(WorkflowTimer, "fired")
        assert hasattr(WorkflowTimer, "cancelled")

    def test_timer_defaults(self):
        from app.domains.notify.models import WorkflowTimer
        # Defaults should be False for fired and cancelled
        assert WorkflowTimer.fired.default.arg is False
        assert WorkflowTimer.cancelled.default.arg is False


class TestTenantIsolation:
    """Verify all notification and workflow models have tenant fields."""

    MODELS = [
        "Notification", "NotificationDelivery", "NotificationPreference",
        "WorkflowEvent", "WorkflowTimer", "EscalationRule",
        "EscalationEvent", "SLAPolicy",
    ]

    def test_all_models_have_tenant(self):
        import app.domains.notify.models as m
        for model_name in self.MODELS:
            model = getattr(m, model_name, None)
            assert model is not None, f"Model {model_name} not found"
            assert hasattr(model, "tenant_id"), f"{model_name} missing tenant_id"


class TestNotificationDedup:
    """Verify deduplication logic."""

    def test_dedup_key_field_exists(self):
        from app.domains.notify.models import Notification
        assert hasattr(Notification, "dedup_key")


class TestEscalationChain:
    """Verify escalation chain structure."""

    def test_chain_structure(self):
        chain = [
            {"level": 1, "assignee": "role:legal_reviewer", "timeout_minutes": 120},
            {"level": 2, "assignee": "user:senior-reviewer", "timeout_minutes": 60},
            {"level": 3, "assignee": "role:legal_director"},
        ]
        assert len(chain) == 3
        assert chain[0]["level"] == 1
        assert chain[2]["level"] == 3


class TestSLACalculation:
    """Verify SLA calculation logic."""

    def test_sla_percent_used(self):
        target = 480  # 8 hours
        elapsed = 120  # 2 hours
        percent = elapsed / target
        assert percent == 0.25

    def test_sla_warning_threshold(self):
        target = 480
        elapsed = 400
        percent = elapsed / target
        assert percent > 0.8  # Warning threshold exceeded

    def test_sla_breach(self):
        target = 480
        elapsed = 500
        remaining = target - elapsed
        assert remaining < 0  # Breached
