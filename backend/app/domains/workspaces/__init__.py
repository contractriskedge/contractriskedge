"""Enterprise Workspace Experience — role-specific workspaces with intelligence, queues, KPIs, recommendations, alerts.

Each workspace becomes a daily operational dependency for its role.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WorkspaceRole(str, Enum):
    REVIEWER = "reviewer"
    LEGAL_OPS = "legal_ops"
    PROCUREMENT = "procurement"
    EXECUTIVE = "executive"
    COMPLIANCE = "compliance"
    ADMIN = "admin"


@dataclass
class WorkspaceWidget:
    """A widget on a workspace dashboard."""
    widget_id: str
    title: str
    widget_type: str  # kpi, queue, chart, alert, recommendation, activity
    data: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    refresh_interval: int = 30


@dataclass
class WorkspaceAlert:
    """An operational alert in a workspace."""
    alert_id: str
    severity: str  # critical, high, medium, low
    title: str
    description: str
    action_url: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class WorkspaceKPI:
    """A key performance indicator in a workspace."""
    name: str
    value: float
    unit: str = ""
    trend: str = "stable"  # improving, stable, declining
    target: float | None = None
    threshold_warning: float | None = None
    threshold_critical: float | None = None


@dataclass
class Workspace:
    """A role-specific workspace with curated intelligence."""
    role: WorkspaceRole
    name: str
    description: str
    widgets: list[WorkspaceWidget] = field(default_factory=list)
    alerts: list[WorkspaceAlert] = field(default_factory=list)
    kpis: list[WorkspaceKPI] = field(default_factory=list)
    quick_actions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkspaceService:
    """Generates role-specific workspaces with operational intelligence.

    Each workspace provides:
    - Role-specific KPIs and metrics
    - Prioritized queues
    - Operational alerts
    - Intelligence recommendations
    - Quick actions
    """

    def get_workspace(self, role: WorkspaceRole, user_id: str = "", tenant_id: str = "") -> Workspace:
        """Get the workspace for a specific role."""
        builders = {
            WorkspaceRole.REVIEWER: self._build_reviewer_workspace,
            WorkspaceRole.LEGAL_OPS: self._build_legal_ops_workspace,
            WorkspaceRole.PROCUREMENT: self._build_procurement_workspace,
            WorkspaceRole.EXECUTIVE: self._build_executive_workspace,
            WorkspaceRole.COMPLIANCE: self._build_compliance_workspace,
            WorkspaceRole.ADMIN: self._build_admin_workspace,
        }
        builder = builders.get(role)
        if not builder:
            raise ValueError(f"Unknown workspace role: {role}")
        return builder(user_id, tenant_id)

    def _build_reviewer_workspace(self, user_id: str, tenant_id: str) -> Workspace:
        """Build reviewer workspace with inbox, triage, and productivity tools."""
        return Workspace(
            role=WorkspaceRole.REVIEWER,
            name="Reviewer Workspace",
            description="Your review queue with AI-powered triage and productivity tools",
            kpis=[
                WorkspaceKPI(name="Pending Reviews", value=12, trend="stable", threshold_warning=20, threshold_critical=30),
                WorkspaceKPI(name="SLA Compliance", value=94.5, unit="%", trend="improving", target=95.0),
                WorkspaceKPI(name="Avg Review Time", value=3.2, unit="hours", trend="improving"),
                WorkspaceKPI(name="AI Confidence", value=87.0, unit="%", trend="improving"),
            ],
            alerts=[
                WorkspaceAlert(alert_id="a1", severity="high", title="3 reviews approaching SLA deadline", description="Complete within 4 hours"),
                WorkspaceAlert(alert_id="a2", severity="medium", title="New vendor playbook available", description="Updated negotiation guidelines"),
            ],
            widgets=[
                WorkspaceWidget(widget_id="w1", title="Priority Queue", widget_type="queue", priority=1),
                WorkspaceWidget(widget_id="w2", title="AI Triage Summary", widget_type="chart", priority=2),
                WorkspaceWidget(widget_id="w3", title="Recent Activity", widget_type="activity", priority=3),
            ],
            quick_actions=[
                {"label": "Start Next Review", "action": "start_review", "icon": "play"},
                {"label": "View Queue", "action": "view_queue", "icon": "list"},
                {"label": "Bulk Actions", "action": "bulk_actions", "icon": "checklist"},
            ],
        )

    def _build_legal_ops_workspace(self, user_id: str, tenant_id: str) -> Workspace:
        """Build legal operations workspace with portfolio oversight."""
        return Workspace(
            role=WorkspaceRole.LEGAL_OPS,
            name="Legal Operations Workspace",
            description="Portfolio oversight, obligation tracking, and team analytics",
            kpis=[
                WorkspaceKPI(name="Active Contracts", value=847, trend="stable"),
                WorkspaceKPI(name="Obligations Due", value=23, trend="declining", threshold_warning=30),
                WorkspaceKPI(name="Team Capacity", value=72.0, unit="%", trend="stable", threshold_critical=90),
                WorkspaceKPI(name="Avg Cycle Time", value=4.5, unit="days", trend="improving", target=3.0),
            ],
            alerts=[
                WorkspaceAlert(alert_id="a1", severity="critical", title="5 obligations overdue", description="Legal exposure risk"),
                WorkspaceAlert(alert_id="a2", severity="high", title="Q3 renewal wave approaching", description="12 contracts renewing next month"),
            ],
            widgets=[
                WorkspaceWidget(widget_id="w1", title="Obligation Heatmap", widget_type="chart"),
                WorkspaceWidget(widget_id="w2", title="Team Workload", widget_type="chart"),
                WorkspaceWidget(widget_id="w3", title="Renewal Timeline", widget_type="chart"),
            ],
            quick_actions=[
                {"label": "Assign Reviews", "action": "assign_reviews", "icon": "assign"},
                {"label": "Obligation Report", "action": "obligation_report", "icon": "report"},
                {"label": "Team Settings", "action": "team_settings", "icon": "settings"},
            ],
        )

    def _build_procurement_workspace(self, user_id: str, tenant_id: str) -> Workspace:
        """Build procurement workspace with vendor intelligence."""
        return Workspace(
            role=WorkspaceRole.PROCUREMENT,
            name="Procurement Workspace",
            description="Vendor intelligence, contract pipeline, and negotiation tracking",
            kpis=[
                WorkspaceKPI(name="Active Vendors", value=156, trend="stable"),
                WorkspaceKPI(name="Contracts in Review", value=18, trend="stable"),
                WorkspaceKPI(name="Avg Negotiation Cycle", value=22, unit="days", trend="improving", target=15),
                WorkspaceKPI(name="Vendor Risk Score", value=0.32, trend="improving", threshold_warning=0.5, threshold_critical=0.7),
            ],
            alerts=[
                WorkspaceAlert(alert_id="a1", severity="high", title="Vendor concentration risk: Vendor A", description="15 contracts, $2.5M total"),
                WorkspaceAlert(alert_id="a2", severity="medium", title="3 vendor renewals this month", description="Prepare negotiation strategies"),
            ],
            widgets=[
                WorkspaceWidget(widget_id="w1", title="Vendor Risk Matrix", widget_type="chart"),
                WorkspaceWidget(widget_id="w2", title="Pipeline Status", widget_type="queue"),
                WorkspaceWidget(widget_id="w3", title="Negotiation Tracker", widget_type="chart"),
            ],
            quick_actions=[
                {"label": "New Contract", "action": "new_contract", "icon": "add"},
                {"label": "Vendor Report", "action": "vendor_report", "icon": "report"},
                {"label": "Negotiation Playbook", "action": "playbook", "icon": "book"},
            ],
        )

    def _build_executive_workspace(self, user_id: str, tenant_id: str) -> Workspace:
        """Build executive workspace with strategic intelligence."""
        return Workspace(
            role=WorkspaceRole.EXECUTIVE,
            name="Executive Command Center",
            description="Enterprise risk posture, intelligence, and strategic recommendations",
            kpis=[
                WorkspaceKPI(name="Portfolio Risk Score", value=0.28, trend="improving", threshold_warning=0.4, threshold_critical=0.6),
                WorkspaceKPI(name="AI Trust Score", value=92.0, unit="%", trend="improving", target=95.0),
                WorkspaceKPI(name="Annual Savings", value=450000, unit="$", trend="improving"),
                WorkspaceKPI(name="SLA Compliance", value=96.5, unit="%", trend="improving", target=99.0),
            ],
            alerts=[
                WorkspaceAlert(alert_id="a1", severity="critical", title="Vendor concentration risk detected", description="Top 3 vendors represent 60% of contract value"),
                WorkspaceAlert(alert_id="a2", severity="high", title="Compliance exposure: GDPR update pending", description="15 contracts may need updates"),
            ],
            widgets=[
                WorkspaceWidget(widget_id="w1", title="Risk Heatmap", widget_type="chart"),
                WorkspaceWidget(widget_id="w2", title="ROI Trends", widget_type="chart"),
                WorkspaceWidget(widget_id="w3", title="Strategic Recommendations", widget_type="recommendation"),
                WorkspaceWidget(widget_id="w4", title="Organizational Bottlenecks", widget_type="chart"),
            ],
            quick_actions=[
                {"label": "Risk Report", "action": "risk_report", "icon": "report"},
                {"label": "Executive Summary", "action": "exec_summary", "icon": "summary"},
                {"label": "Board Deck", "action": "board_deck", "icon": "presentation"},
            ],
        )

    def _build_compliance_workspace(self, user_id: str, tenant_id: str) -> Workspace:
        """Build compliance workspace with regulatory oversight."""
        return Workspace(
            role=WorkspaceRole.COMPLIANCE,
            name="Compliance Workspace",
            description="Regulatory compliance, audit readiness, and policy enforcement",
            kpis=[
                WorkspaceKPI(name="Compliance Rate", value=94.0, unit="%", trend="improving", target=99.0),
                WorkspaceKPI(name="Open Violations", value=3, trend="declining", threshold_warning=5, threshold_critical=10),
                WorkspaceKPI(name="Audit Readiness", value=88.0, unit="%", trend="improving", target=100.0),
                WorkspaceKPI(name="Overdue Remediations", value=2, trend="declining"),
            ],
            alerts=[
                WorkspaceAlert(alert_id="a1", severity="high", title="SOC2 audit in 45 days", description="Begin evidence collection"),
                WorkspaceAlert(alert_id="a2", severity="medium", title="3 policy exceptions expiring", description="Review and renew or close"),
            ],
            widgets=[
                WorkspaceWidget(widget_id="w1", title="Compliance Heatmap", widget_type="chart"),
                WorkspaceWidget(widget_id="w2", title="Audit Timeline", widget_type="chart"),
                WorkspaceWidget(widget_id="w3", title="Policy Exceptions", widget_type="queue"),
            ],
            quick_actions=[
                {"label": "Run Compliance Check", "action": "compliance_check", "icon": "check"},
                {"label": "Generate Report", "action": "generate_report", "icon": "report"},
                {"label": "Evidence Collection", "action": "evidence", "icon": "collect"},
            ],
        )

    def _build_admin_workspace(self, user_id: str, tenant_id: str) -> Workspace:
        """Build admin workspace with platform operations."""
        return Workspace(
            role=WorkspaceRole.ADMIN,
            name="Admin Console",
            description="Platform operations, tenant management, and system health",
            kpis=[
                WorkspaceKPI(name="Platform Health", value=98.5, unit="%", trend="stable", threshold_critical=95.0),
                WorkspaceKPI(name="Active Users", value=47, trend="growing"),
                WorkspaceKPI(name="AI Executions (24h)", value=1250, trend="growing"),
                WorkspaceKPI(name="System Cost (MTD)", value=4250, unit="$", trend="stable"),
            ],
            alerts=[
                WorkspaceAlert(alert_id="a1", severity="medium", title="Queue depth elevated", description="AI analysis queue at 85% capacity"),
                WorkspaceAlert(alert_id="a2", severity="low", title="Embedding model upgrade available", description="text-embedding-3-large v2 released"),
            ],
            widgets=[
                WorkspaceWidget(widget_id="w1", title="System Health", widget_type="chart"),
                WorkspaceWidget(widget_id="w2", title="Queue Status", widget_type="queue"),
                WorkspaceWidget(widget_id="w3", title="Tenant Usage", widget_type="chart"),
                WorkspaceWidget(widget_id="w4", title="Recent Incidents", widget_type="activity"),
            ],
            quick_actions=[
                {"label": "System Status", "action": "system_status", "icon": "health"},
                {"label": "Manage Tenants", "action": "manage_tenants", "icon": "tenants"},
                {"label": "View Audit Log", "action": "audit_log", "icon": "audit"},
            ],
        )


# ── Global singleton ───────────────────────────────────────────────

workspace_service = WorkspaceService()
