"""Industry Operating Models — healthcare_os, procurement_os, finance_os, manufacturing_os.

Each includes: workflows, governance, intelligence, benchmarks, simulations, strategy models, operational playbooks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IndustryOS(str, Enum):
    HEALTHCARE = "healthcare_os"
    PROCUREMENT = "procurement_os"
    FINANCE = "finance_os"
    MANUFACTURING = "manufacturing_os"


@dataclass
class OperatingModel:
    """A complete industry operating model."""
    industry: IndustryOS
    name: str
    description: str
    workflow_count: int = 0
    governance_policies: int = 0
    benchmark_metrics: int = 0
    simulation_scenarios: int = 0
    strategy_models: int = 0
    playbook_steps: int = 0
    capabilities: list[str] = field(default_factory=list)


@dataclass
class IndustryOperatingModelService:
    """Industry operating models — productized industry operating systems.

    Each OS includes:
    - Pre-built workflows for the industry
    - Governance policies calibrated for industry regulations
    - Intelligence models with industry-specific benchmarks
    - Simulations calibrated for industry scenarios
    - Strategy models for industry-specific optimization
    - Operational playbooks for common scenarios
    """

    _models: dict[IndustryOS, OperatingModel] = field(default_factory=dict)

    def __post_init__(self):
        self._register_all_models()

    def _register_all_models(self) -> None:
        """Register all industry operating models."""
        self._models[IndustryOS.HEALTHCARE] = OperatingModel(
            industry=IndustryOS.HEALTHCARE,
            name="Healthcare Operating System",
            description="Complete healthcare contract intelligence operating model with HIPAA compliance, clinical agreement workflows, and provider network management",
            workflow_count=8,
            governance_policies=12,
            benchmark_metrics=25,
            simulation_scenarios=6,
            strategy_models=4,
            playbook_steps=45,
            capabilities=[
                "HIPAA compliance automation",
                "Clinical trial agreement workflows",
                "Provider network management",
                "Value-based contract modeling",
                "Regulatory change tracking",
                "Patient data privacy governance",
                "Revenue cycle intelligence",
            ],
        )

        self._models[IndustryOS.PROCUREMENT] = OperatingModel(
            industry=IndustryOS.PROCUREMENT,
            name="Procurement Operating System",
            description="Strategic procurement operating model with vendor management, SLA optimization, and supply chain risk intelligence",
            workflow_count=10,
            governance_policies=8,
            benchmark_metrics=30,
            simulation_scenarios=8,
            strategy_models=5,
            playbook_steps=55,
            capabilities=[
                "Vendor risk intelligence",
                "SLA optimization and monitoring",
                "Strategic sourcing workflows",
                "Supply chain risk modeling",
                "Contract lifecycle automation",
                "Negotiation intelligence",
                "Category management analytics",
            ],
        )

        self._models[IndustryOS.FINANCE] = OperatingModel(
            industry=IndustryOS.FINANCE,
            name="Financial Services Operating System",
            description="Banking and financial services operating model with SOX/SEC compliance, regulatory reporting, and risk management",
            workflow_count=9,
            governance_policies=15,
            benchmark_metrics=28,
            simulation_scenarios=7,
            strategy_models=4,
            playbook_steps=50,
            capabilities=[
                "SOX/SEC compliance automation",
                "Regulatory reporting workflows",
                "Financial risk modeling",
                "Vendor due diligence automation",
                "Audit trail management",
                "Cross-border compliance",
                "Capital adequacy monitoring",
            ],
        )

        self._models[IndustryOS.MANUFACTURING] = OperatingModel(
            industry=IndustryOS.MANUFACTURING,
            name="Manufacturing Operating System",
            description="Manufacturing contract intelligence operating model with supply chain management, quality agreements, and regulatory compliance",
            workflow_count=7,
            governance_policies=10,
            benchmark_metrics=22,
            simulation_scenarios=5,
            strategy_models=3,
            playbook_steps=40,
            capabilities=[
                "Supply chain contract intelligence",
                "Quality agreement management",
                "ISO compliance automation",
                "Supplier risk monitoring",
                "Intellectual property protection",
                "Environmental compliance tracking",
                "Production agreement workflows",
            ],
        )

    def get_model(self, industry: IndustryOS) -> OperatingModel | None:
        """Get an industry operating model."""
        return self._models.get(industry)

    def list_models(self) -> list[dict[str, Any]]:
        """List all industry operating models."""
        return [
            {"industry": m.industry.value, "name": m.name, "description": m.description,
             "workflows": m.workflow_count, "governance": m.governance_policies,
             "benchmarks": m.benchmark_metrics, "simulations": m.simulation_scenarios,
             "strategies": m.strategy_models, "playbook_steps": m.playbook_steps,
             "capabilities": m.capabilities}
            for m in self._models.values()
        ]

    def get_os_summary(self) -> dict[str, Any]:
        """Get industry OS summary."""
        return {
            "total_models": len(self._models),
            "models": self.list_models(),
            "total_workflows": sum(m.workflow_count for m in self._models.values()),
            "total_governance": sum(m.governance_policies for m in self._models.values()),
            "total_capabilities": sum(len(m.capabilities) for m in self._models.values()),
        }


# ── Global singleton ───────────────────────────────────────────────

industry_os = IndustryOperatingModelService()
