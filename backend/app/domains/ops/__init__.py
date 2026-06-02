"""Observability Dashboards — operational visibility for AI infrastructure.

Provides:
- Dashboard metrics for AI latency, provider health, guardrail violations
- Alerting rules and evaluation
- Health check endpoints
- Tenant usage dashboards
- Queue depth monitoring
- Workflow SLA breach tracking
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Alert Severity ─────────────────────────────────────────────────

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SEVERE = "severe"  # Pager-duty worthy


class AlertStatus(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


# ── Dashboard Metrics ──────────────────────────────────────────────

@dataclass
class DashboardMetric:
    """A single dashboard metric with current value and history."""
    name: str
    display_name: str
    value: float = 0.0
    unit: str = "count"
    previous_value: float = 0.0
    change_pct: float = 0.0
    threshold_warning: float | None = None
    threshold_critical: float | None = None
    history: list[float] = field(default_factory=list)
    max_history: int = 100


@dataclass
class DashboardPanel:
    """A panel on the observability dashboard."""
    title: str
    metrics: list[DashboardMetric] = field(default_factory=list)
    panel_type: str = "timeseries"  # timeseries, gauge, stat, table, bar
    refresh_interval: int = 30  # seconds


@dataclass
class Dashboard:
    """A complete observability dashboard."""
    name: str
    description: str = ""
    panels: list[DashboardPanel] = field(default_factory=list)
    refresh_interval: int = 30
    tags: list[str] = field(default_factory=list)


# ── Alert Rule ─────────────────────────────────────────────────────

AlertCheckFn = Callable[[], tuple[bool, str]]


@dataclass
class AlertRule:
    """A single alert rule with evaluation logic."""
    rule_id: str
    name: str
    description: str
    severity: AlertSeverity
    check_fn: AlertCheckFn
    cooldown_minutes: int = 5
    enabled: bool = True
    last_firing: datetime | None = None
    last_resolved: datetime | None = None
    firing_count: int = 0
    notify_channels: list[str] = field(default_factory=lambda: ["log"])

    def evaluate(self) -> tuple[bool, str]:
        """Evaluate the alert rule. Returns (is_firing, message)."""
        if not self.enabled:
            return False, ""
        return self.check_fn()


# ── Alert Manager ──────────────────────────────────────────────────

@dataclass
class AlertManager:
    """Manages alert rules, evaluation, and notification routing."""

    rules: dict[str, AlertRule] = field(default_factory=dict)
    active_alerts: dict[str, dict[str, Any]] = field(default_factory=dict)
    alert_history: list[dict[str, Any]] = field(default_factory=list)
    _notification_handlers: dict[str, list[Callable]] = field(default_factory=dict)

    def register_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self.rules[rule.rule_id] = rule
        logger.info("Registered alert rule: %s (%s)", rule.name, rule.severity.value)

    def register_notification_handler(self, channel: str, handler: Callable) -> None:
        """Register a notification handler for a channel."""
        if channel not in self._notification_handlers:
            self._notification_handlers[channel] = []
        self._notification_handlers[channel].append(handler)

    async def evaluate_all(self) -> list[dict[str, Any]]:
        """Evaluate all alert rules and return firing alerts."""
        firing: list[dict[str, Any]] = []
        now = datetime.utcnow()

        for rule_id, rule in self.rules.items():
            try:
                is_firing, message = rule.evaluate()
                if is_firing:
                    # Check cooldown
                    if rule.last_firing and (now - rule.last_firing).total_seconds() < rule.cooldown_minutes * 60:
                        continue

                    rule.last_firing = now
                    rule.firing_count += 1

                    alert = {
                        "rule_id": rule_id,
                        "name": rule.name,
                        "severity": rule.severity.value,
                        "message": message,
                        "fired_at": now.isoformat(),
                        "status": AlertStatus.FIRING.value,
                    }
                    self.active_alerts[rule_id] = alert
                    self.alert_history.append(alert)
                    firing.append(alert)

                    # Notify
                    await self._notify(alert, rule)
                else:
                    if rule_id in self.active_alerts:
                        resolved = self.active_alerts.pop(rule_id)
                        resolved["status"] = AlertStatus.RESOLVED.value
                        resolved["resolved_at"] = now.isoformat()
                        rule.last_resolved = now

            except Exception as e:
                logger.error("Alert rule '%s' evaluation failed: %s", rule.name, e)

        return firing

    async def _notify(self, alert: dict[str, Any], rule: AlertRule) -> None:
        """Send notifications for an alert through configured channels."""
        for channel in rule.notify_channels:
            handlers = self._notification_handlers.get(channel, [])
            for handler in handlers:
                try:
                    await handler(alert)
                except Exception as e:
                    logger.error("Notification handler failed for channel '%s': %s", channel, e)

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get all currently firing alerts."""
        return list(self.active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent alert history."""
        return list(self.alert_history[-limit:])

    def acknowledge_alert(self, rule_id: str) -> None:
        """Acknowledge a firing alert."""
        if rule_id in self.active_alerts:
            self.active_alerts[rule_id]["status"] = AlertStatus.ACKNOWLEDGED.value

    def suppress_alert(self, rule_id: str, duration_minutes: int = 60) -> None:
        """Suppress an alert for a duration."""
        rule = self.rules.get(rule_id)
        if rule:
            rule.enabled = False
            # Re-enable after duration
            import asyncio
            async def re_enable():
                await asyncio.sleep(duration_minutes * 60)
                rule.enabled = True
            asyncio.create_task(re_enable())


# ── Observability Service ──────────────────────────────────────────

@dataclass
class ObservabilityService:
    """Central observability service that builds dashboards and manages alerts."""

    alert_manager: AlertManager = field(default_factory=AlertManager)
    _dashboards: dict[str, Dashboard] = field(default_factory=dict)

    def register_dashboard(self, dashboard: Dashboard) -> None:
        """Register an observability dashboard."""
        self._dashboards[dashboard.name] = dashboard

    def get_dashboard(self, name: str) -> Dashboard | None:
        """Get a registered dashboard."""
        return self._dashboards.get(name)

    def get_all_dashboards(self) -> list[Dashboard]:
        """Get all registered dashboards."""
        return list(self._dashboards.values())

    def build_ai_performance_dashboard(self) -> Dashboard:
        """Build AI performance dashboard."""
        return Dashboard(
            name="ai_performance",
            description="AI execution performance, latency, and cost metrics",
            panels=[
                DashboardPanel(
                    title="Provider Latency (p50/p95/p99)",
                    panel_type="timeseries",
                    metrics=[
                        DashboardMetric(name="provider_latency_p50", display_name="Latency p50", unit="ms"),
                        DashboardMetric(name="provider_latency_p95", display_name="Latency p95", unit="ms"),
                        DashboardMetric(name="provider_latency_p99", display_name="Latency p99", unit="ms"),
                    ],
                ),
                DashboardPanel(
                    title="Cost Per Execution",
                    panel_type="timeseries",
                    metrics=[
                        DashboardMetric(name="cost_per_execution", display_name="Avg Cost", unit="usd"),
                        DashboardMetric(name="total_daily_cost", display_name="Daily Cost", unit="usd"),
                    ],
                ),
                DashboardPanel(
                    title="Token Usage",
                    panel_type="timeseries",
                    metrics=[
                        DashboardMetric(name="prompt_tokens_per_min", display_name="Prompt Tokens/min", unit="tokens"),
                        DashboardMetric(name="completion_tokens_per_min", display_name="Completion Tokens/min", unit="tokens"),
                    ],
                ),
                DashboardPanel(
                    title="Provider Health",
                    panel_type="stat",
                    metrics=[
                        DashboardMetric(name="provider_success_rate", display_name="Success Rate", unit="%"),
                        DashboardMetric(name="provider_error_rate", display_name="Error Rate", unit="%"),
                        DashboardMetric(name="circuit_breakers_open", display_name="Circuit Breakers Open", unit="count"),
                    ],
                ),
            ],
        )

    def build_guardrail_dashboard(self) -> Dashboard:
        """Build guardrail and safety dashboard."""
        return Dashboard(
            name="guardrail_monitoring",
            description="Guardrail violations, rejection rates, and safety metrics",
            panels=[
                DashboardPanel(
                    title="Guardrail Violations",
                    panel_type="timeseries",
                    metrics=[
                        DashboardMetric(name="guardrail_violations_per_min", display_name="Violations/min", unit="count"),
                        DashboardMetric(name="guardrail_rejection_rate", display_name="Rejection Rate", unit="%"),
                    ],
                ),
                DashboardPanel(
                    title="Top Guardrail Rules",
                    panel_type="table",
                    metrics=[
                        DashboardMetric(name="top_guardrail_rule", display_name="Most Triggered Rule", unit="count"),
                    ],
                ),
            ],
        )

    def build_tenant_usage_dashboard(self) -> Dashboard:
        """Build tenant usage dashboard."""
        return Dashboard(
            name="tenant_usage",
            description="Per-tenant resource usage and quotas",
            panels=[
                DashboardPanel(
                    title="Active Tenants",
                    panel_type="stat",
                    metrics=[
                        DashboardMetric(name="active_tenants", display_name="Active Tenants", unit="count"),
                        DashboardMetric(name="total_tenants", display_name="Total Tenants", unit="count"),
                    ],
                ),
                DashboardPanel(
                    title="API Usage by Tenant",
                    panel_type="bar",
                    metrics=[
                        DashboardMetric(name="api_calls_per_tenant", display_name="API Calls", unit="count"),
                    ],
                ),
            ],
        )

    def build_queue_dashboard(self) -> Dashboard:
        """Build queue monitoring dashboard."""
        return Dashboard(
            name="queue_monitoring",
            description="Async queue depth, processing rates, and dead-letter queue",
            panels=[
                DashboardPanel(
                    title="Queue Depth",
                    panel_type="timeseries",
                    metrics=[
                        DashboardMetric(name="queue_depth", display_name="Pending Jobs", unit="count"),
                        DashboardMetric(name="queue_processing_rate", display_name="Processing Rate", unit="jobs/min"),
                    ],
                ),
                DashboardPanel(
                    title="Dead-Letter Queue",
                    panel_type="stat",
                    metrics=[
                        DashboardMetric(name="dlq_count", display_name="DLQ Entries", unit="count"),
                        DashboardMetric(name="poison_jobs", display_name="Quarantined Jobs", unit="count"),
                    ],
                ),
            ],
        )

    def build_workflow_sla_dashboard(self) -> Dashboard:
        """Build workflow SLA monitoring dashboard."""
        return Dashboard(
            name="workflow_sla",
            description="Workflow execution, SLA breaches, and escalations",
            panels=[
                DashboardPanel(
                    title="Workflow Status",
                    panel_type="stat",
                    metrics=[
                        DashboardMetric(name="active_workflows", display_name="Active", unit="count"),
                        DashboardMetric(name="failed_workflows", display_name="Failed", unit="count"),
                        DashboardMetric(name="sla_breaches", display_name="SLA Breaches", unit="count"),
                    ],
                ),
                DashboardPanel(
                    title="Pending Approvals",
                    panel_type="stat",
                    metrics=[
                        DashboardMetric(name="pending_approvals", display_name="Awaiting Approval", unit="count"),
                        DashboardMetric(name="approval_sla_breach", display_name="Overdue Approvals", unit="count"),
                    ],
                ),
            ],
        )


# ── Default Alert Rules ────────────────────────────────────────────

def create_default_alert_rules() -> list[AlertRule]:
    """Create the default set of alert rules for the platform."""
    return [
        AlertRule(
            rule_id="high_error_rate",
            name="High AI Provider Error Rate",
            description="AI provider error rate exceeds 10% in the last 5 minutes",
            severity=AlertSeverity.CRITICAL,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),  # Placeholder
            cooldown_minutes=10,
            notify_channels=["log", "slack"],
        ),
        AlertRule(
            rule_id="high_latency",
            name="High AI Execution Latency",
            description="p95 AI execution latency exceeds 30 seconds",
            severity=AlertSeverity.WARNING,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),
            cooldown_minutes=5,
        ),
        AlertRule(
            rule_id="guardrail_spike",
            name="Guardrail Violation Spike",
            description="Guardrail violation rate exceeds 20% of total executions",
            severity=AlertSeverity.WARNING,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),
            cooldown_minutes=15,
        ),
        AlertRule(
            rule_id="queue_backlog",
            name="Queue Backlog Growing",
            description="Queue depth exceeds 1000 pending jobs",
            severity=AlertSeverity.WARNING,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),
            cooldown_minutes=5,
        ),
        AlertRule(
            rule_id="dlq_growth",
            name="Dead-Letter Queue Growing",
            description="Dead-letter queue has more than 10 entries",
            severity=AlertSeverity.CRITICAL,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),
            cooldown_minutes=15,
        ),
        AlertRule(
            rule_id="tenant_quota_breach",
            name="Tenant Quota Approaching Limit",
            description="A tenant is using >90% of their quota",
            severity=AlertSeverity.WARNING,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),
            cooldown_minutes=30,
        ),
        AlertRule(
            rule_id="workflow_sla_breach",
            name="Workflow SLA Breach",
            description="A critical workflow has breached its SLA",
            severity=AlertSeverity.CRITICAL,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),
            cooldown_minutes=5,
            notify_channels=["log", "slack", "pager"],
        ),
        AlertRule(
            rule_id="circuit_breaker_open",
            name="Provider Circuit Breaker Open",
            description="An AI provider circuit breaker has opened",
            severity=AlertSeverity.SEVERE,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),
            cooldown_minutes=1,
            notify_channels=["log", "slack", "pager"],
        ),
        AlertRule(
            rule_id="replay_drift_detected",
            name="AI Replay Drift Detected",
            description="Significant output drift detected during replay comparison",
            severity=AlertSeverity.WARNING,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),
            cooldown_minutes=60,
        ),
        AlertRule(
            rule_id="cost_spike",
            name="Daily Cost Spike",
            description="Daily AI cost exceeds 2x the 7-day average",
            severity=AlertSeverity.WARNING,
            check_fn=lambda: (False, "Placeholder — connect to telemetry"),
            cooldown_minutes=60,
        ),
    ]
