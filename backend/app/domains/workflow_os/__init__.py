"""Workflow Operating System — reusable packs, policy-attached workflows, dynamic SLA routing, AI-human hybrid stages.

Workflows become organizational infrastructure — not just automation.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WorkflowPackCategory(str, Enum):
    PROCUREMENT = "procurement"
    LEGAL = "legal"
    COMPLIANCE = "compliance"
    SECURITY = "security"
    FINANCE = "finance"
    HR = "hr"
    SALES = "sales"
    CUSTOM = "custom"


class HybridStageType(str, Enum):
    AI_ONLY = "ai_only"                   # Fully automated
    AI_WITH_REVIEW = "ai_with_review"      # AI recommends, human reviews
    HUMAN_WITH_AI = "human_with_ai"        # Human decides, AI assists
    HUMAN_ONLY = "human_only"              # Fully manual
    ESCALATION_AWARE = "escalation_aware"  # Auto-escalates on conditions


@dataclass
class WorkflowPack:
    """A reusable workflow pack that encapsulates a complete business process."""
    pack_id: str
    name: str
    description: str
    category: WorkflowPackCategory
    version: str = "1.0.0"
    stages: list["WorkflowStage"] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)
    required_integrations: list[str] = field(default_factory=list)
    estimated_duration_hours: int = 24
    tags: list[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class WorkflowStage:
    """A single stage in a workflow pack with hybrid AI-human execution."""
    stage_id: str
    name: str
    stage_type: HybridStageType
    order: int = 0
    sla_hours: int = 8
    required_roles: list[str] = field(default_factory=list)
    ai_model: str = "gpt-4o"
    escalation_policy: str = ""
    condition: str = ""  # Expression to skip/apply this stage
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class DynamicSLARouter:
    """Routes workflows to different SLA tracks based on context.

    SLA tracks:
    - EXPRESS: 4 hours (urgent, high-priority contracts)
    - STANDARD: 24 hours (normal contracts)
    - EXTENDED: 72 hours (low-priority, complex contracts)
    """

    def resolve_sla(self, risk_score: float, contract_value: float, tenant_tier: str) -> tuple[int, str]:
        """Resolve SLA based on contract context."""
        if risk_score > 0.8 or contract_value > 1_000_000 or tenant_tier == "enterprise":
            return (4, "express")
        elif risk_score > 0.5 or contract_value > 100_000:
            return (24, "standard")
        else:
            return (72, "extended")


@dataclass
class EscalationGraphEngine:
    """Graph-based escalation engine — escalations follow relationship paths."""

    _escalation_paths: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def register_path(self, from_role: str, to_role: str, conditions: list[str], timeout_minutes: int = 60) -> None:
        """Register an escalation path between roles."""
        if from_role not in self._escalation_paths:
            self._escalation_paths[from_role] = []
        self._escalation_paths[from_role].append({
            "to_role": to_role,
            "conditions": conditions,
            "timeout_minutes": timeout_minutes,
        })

    def resolve_escalation(self, current_role: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Resolve the next escalation target based on context."""
        paths = self._escalation_paths.get(current_role, [])
        applicable = []
        for path in paths:
            for condition in path["conditions"]:
                if self._evaluate_condition(condition, context):
                    applicable.append(path)
                    break
        return applicable

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Evaluate an escalation condition against context."""
        if condition == "sla_breached" and context.get("sla_breached"):
            return True
        if condition == "risk_score_high" and (context.get("risk_score", 0) or 0) > 0.7:
            return True
        if condition == "value_high" and (context.get("contract_value", 0) or 0) > 500_000:
            return True
        if condition == "reviewer_unavailable":
            return True
        return False


@dataclass
class WorkflowSimulationSandbox:
    """Sandbox for simulating workflow execution before deployment."""

    def simulate(self, pack: WorkflowPack, context: dict[str, Any]) -> dict[str, Any]:
        """Simulate a workflow pack execution."""
        path = []
        total_sla = 0
        bottlenecks = []

        for stage in sorted(pack.stages, key=lambda s: s.order):
            stage_result = {
                "stage_id": stage.stage_id,
                "name": stage.name,
                "stage_type": stage.stage_type.value,
                "sla_hours": stage.sla_hours,
                "required_roles": stage.required_roles,
            }

            # Simulate AI execution
            if stage.stage_type in (HybridStageType.AI_ONLY, HybridStageType.AI_WITH_REVIEW):
                stage_result["ai_execution_ms"] = 5000
                stage_result["ai_confidence"] = 0.85

            # Simulate human review if needed
            if stage.stage_type in (HybridStageType.AI_WITH_REVIEW, HybridStageType.HUMAN_WITH_AI, HybridStageType.HUMAN_ONLY):
                stage_result["estimated_review_time_hours"] = stage.sla_hours * 0.7
                stage_result["reviewer_required"] = True

            # Check for bottlenecks
            if stage.sla_hours > 24:
                bottlenecks.append({"stage": stage.name, "reason": f"SLA of {stage.sla_hours}h exceeds 24h threshold"})

            total_sla += stage.sla_hours
            path.append(stage_result)

        return {
            "pack_id": pack.pack_id,
            "pack_name": pack.name,
            "stages": len(pack.stages),
            "estimated_total_hours": total_sla,
            "estimated_business_days": round(total_sla / 8, 1),
            "path": path,
            "bottlenecks": bottlenecks,
            "ai_stages": sum(1 for s in pack.stages if s.stage_type in (HybridStageType.AI_ONLY, HybridStageType.AI_WITH_REVIEW)),
            "human_stages": sum(1 for s in pack.stages if s.stage_type in (HybridStageType.HUMAN_ONLY, HybridStageType.HUMAN_WITH_AI)),
            "feasible": len(bottlenecks) == 0,
        }


@dataclass
class WorkflowOS:
    """Workflow Operating System — the central workflow orchestration platform.

    Capabilities:
    - Reusable workflow packs by category
    - Policy-attached workflows (policies travel with the workflow)
    - Dynamic SLA routing based on risk/value/tier
    - AI-human hybrid stage execution
    - Graph-based escalation engine
    - Simulation sandbox for pre-deployment validation
    - Versioned workflow deployments
    - Workflow migration between versions
    """

    _packs: dict[str, WorkflowPack] = field(default_factory=dict)
    _deployments: dict[str, str] = field(default_factory=dict)  # pack_id -> version
    sla_router: DynamicSLARouter = field(default_factory=DynamicSLARouter)
    escalation_engine: EscalationGraphEngine = field(default_factory=EscalationGraphEngine)
    sandbox: WorkflowSimulationSandbox = field(default_factory=WorkflowSimulationSandbox)

    def __post_init__(self):
        self._register_default_packs()

    def _register_default_packs(self) -> None:
        """Register default workflow packs."""
        self.register_pack(WorkflowPack(
            pack_id="procurement_standard",
            name="Standard Procurement Review",
            description="Standard procurement contract review with AI analysis, procurement review, and legal approval",
            category=WorkflowPackCategory.PROCUREMENT,
            stages=[
                WorkflowStage(stage_id="ai_analysis", name="AI Risk Analysis", stage_type=HybridStageType.AI_ONLY, order=1, sla_hours=1),
                WorkflowStage(stage_id="procurement_review", name="Procurement Review", stage_type=HybridStageType.AI_WITH_REVIEW, order=2, sla_hours=8, required_roles=["procurement"]),
                WorkflowStage(stage_id="legal_review", name="Legal Review", stage_type=HybridStageType.HUMAN_WITH_AI, order=3, sla_hours=16, required_roles=["legal"]),
                WorkflowStage(stage_id="approval", name="Final Approval", stage_type=HybridStageType.HUMAN_ONLY, order=4, sla_hours=4, required_roles=["executive"]),
            ],
            tags=["procurement", "standard", "review"],
        ))

        self.register_pack(WorkflowPack(
            pack_id="legal_high_risk",
            name="High-Risk Legal Review",
            description="Elevated review for high-risk contracts with security and compliance stages",
            category=WorkflowPackCategory.LEGAL,
            stages=[
                WorkflowStage(stage_id="ai_analysis", name="AI Risk Analysis", stage_type=HybridStageType.AI_ONLY, order=1, sla_hours=1),
                WorkflowStage(stage_id="legal_review", name="Legal Review", stage_type=HybridStageType.AI_WITH_REVIEW, order=2, sla_hours=16, required_roles=["legal"]),
                WorkflowStage(stage_id="security_review", name="Security Review", stage_type=HybridStageType.HUMAN_WITH_AI, order=3, sla_hours=16, required_roles=["security"]),
                WorkflowStage(stage_id="compliance_review", name="Compliance Review", stage_type=HybridStageType.HUMAN_WITH_AI, order=4, sla_hours=8, required_roles=["compliance"]),
                WorkflowStage(stage_id="executive_approval", name="Executive Approval", stage_type=HybridStageType.HUMAN_ONLY, order=5, sla_hours=8, required_roles=["executive"]),
            ],
            tags=["legal", "high_risk", "security", "compliance"],
        ))

        self.register_pack(WorkflowPack(
            pack_id="vendor_onboarding",
            name="Vendor Onboarding",
            description="Complete vendor onboarding with procurement, security, and legal review",
            category=WorkflowPackCategory.PROCUREMENT,
            stages=[
                WorkflowStage(stage_id="ai_analysis", name="AI Risk Analysis", stage_type=HybridStageType.AI_ONLY, order=1, sla_hours=1),
                WorkflowStage(stage_id="procurement_review", name="Procurement Review", stage_type=HybridStageType.AI_WITH_REVIEW, order=2, sla_hours=8, required_roles=["procurement"]),
                WorkflowStage(stage_id="security_review", name="Security Assessment", stage_type=HybridStageType.HUMAN_WITH_AI, order=3, sla_hours=24, required_roles=["security"]),
                WorkflowStage(stage_id="legal_review", name="Legal Review", stage_type=HybridStageType.HUMAN_WITH_AI, order=4, sla_hours=16, required_roles=["legal"]),
                WorkflowStage(stage_id="final_approval", name="Final Approval", stage_type=HybridStageType.HUMAN_ONLY, order=5, sla_hours=8, required_roles=["executive"]),
            ],
            tags=["vendor", "onboarding", "procurement"],
        ))

    def register_pack(self, pack: WorkflowPack) -> None:
        """Register a workflow pack."""
        self._packs[pack.pack_id] = pack
        logger.info("Registered workflow pack: %s (%s)", pack.name, pack.pack_id)

    def get_pack(self, pack_id: str) -> WorkflowPack | None:
        """Get a workflow pack by ID."""
        return self._packs.get(pack_id)

    def list_packs(self, category: WorkflowPackCategory | None = None) -> list[dict[str, Any]]:
        """List workflow packs, optionally filtered by category."""
        packs = self._packs.values()
        if category:
            packs = [p for p in packs if p.category == category]
        return [
            {
                "pack_id": p.pack_id,
                "name": p.name,
                "description": p.description,
                "category": p.category.value,
                "version": p.version,
                "stage_count": len(p.stages),
                "estimated_hours": sum(s.sla_hours for s in p.stages),
                "tags": p.tags,
                "is_active": p.is_active,
            }
            for p in packs
        ]

    def deploy_pack(self, pack_id: str, version: str = "1.0.0") -> None:
        """Deploy a specific version of a workflow pack."""
        self._deployments[pack_id] = version
        logger.info("Deployed workflow pack %s version %s", pack_id, version)

    def migrate_pack(self, pack_id: str, target_version: str) -> dict[str, Any]:
        """Migrate a workflow pack to a new version."""
        current = self._deployments.get(pack_id, "none")
        self._deployments[pack_id] = target_version
        return {
            "pack_id": pack_id,
            "from_version": current,
            "to_version": target_version,
            "migrated_at": datetime.utcnow().isoformat(),
        }

    def get_os_status(self) -> dict[str, Any]:
        """Get Workflow OS status."""
        return {
            "total_packs": len(self._packs),
            "active_deployments": len(self._deployments),
            "categories": [c.value for c in WorkflowPackCategory],
            "packs": self.list_packs(),
            "escalation_paths": len(self.escalation_engine._escalation_paths),
        }


# ── Global singleton ───────────────────────────────────────────────

workflow_os = WorkflowOS()
