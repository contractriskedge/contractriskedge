"""Industry-Specific Intelligence Packs — healthcare, finance, manufacturing, procurement, insurance, energy verticals.

Each includes: regulatory models, benchmark datasets, workflow templates, clause intelligence, industry risk scoring, compliance mappings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Vertical(str, Enum):
    HEALTHCARE = "healthcare"
    FINANCE = "finance"
    MANUFACTURING = "manufacturing"
    PROCUREMENT = "procurement"
    INSURANCE = "insurance"
    ENERGY = "energy"


@dataclass
class VerticalPack:
    """An industry-specific intelligence pack."""
    vertical: Vertical
    name: str
    description: str
    regulations: list[dict[str, Any]] = field(default_factory=list)
    clause_models: dict[str, Any] = field(default_factory=dict)
    risk_thresholds: dict[str, float] = field(default_factory=dict)
    workflow_templates: list[str] = field(default_factory=list)
    benchmark_data: dict[str, float] = field(default_factory=dict)
    compliance_mappings: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class VerticalIntelligenceService:
    """Industry-specific intelligence packs that verticalize the platform.

    Each vertical pack includes:
    - Regulatory models (which regulations apply)
    - Benchmark datasets (industry-specific norms)
    - Workflow templates (pre-built for industry)
    - Clause intelligence (industry-specific clause patterns)
    - Industry risk scoring (calibrated per industry)
    - Compliance mappings (regulation to clause type)
    """

    _packs: dict[Vertical, VerticalPack] = field(default_factory=dict)

    def __post_init__(self):
        self._register_all_packs()

    def _register_all_packs(self) -> None:
        """Register all vertical intelligence packs."""
        self._packs[Vertical.HEALTHCARE] = VerticalPack(
            vertical=Vertical.HEALTHCARE,
            name="Healthcare Intelligence Pack",
            description="Healthcare-specific contract intelligence with HIPAA, GDPR, and FDA compliance",
            regulations=[
                {"name": "HIPAA", "jurisdiction": "US", "severity": "critical", "clause_types": ["data_privacy", "security", "breach_notification"]},
                {"name": "GDPR", "jurisdiction": "EU", "severity": "high", "clause_types": ["data_privacy", "compliance"]},
                {"name": "FDA Regulations", "jurisdiction": "US", "severity": "high", "clause_types": ["compliance", "liability", "warranty"]},
                {"name": "HITECH", "jurisdiction": "US", "severity": "medium", "clause_types": ["data_privacy", "security"]},
            ],
            risk_thresholds={"data_privacy": 0.7, "liability": 0.6, "compliance": 0.65, "security": 0.7},
            workflow_templates=["hipaa_compliance_review", "healthcare_vendor_onboarding", "clinical_agreement_review"],
            benchmark_data={"avg_risk_score": 0.52, "avg_negotiation_days": 45, "sla_compliance_rate": 0.88},
            compliance_mappings={"HIPAA": ["data_privacy", "security", "breach_notification"], "GDPR": ["data_privacy", "compliance"]},
        )

        self._packs[Vertical.FINANCE] = VerticalPack(
            vertical=Vertical.FINANCE,
            name="Financial Services Intelligence Pack",
            description="Banking and financial services contract intelligence with SOX, SEC, and Basel compliance",
            regulations=[
                {"name": "SOX", "jurisdiction": "US", "severity": "critical", "clause_types": ["compliance", "audit", "liability"]},
                {"name": "SEC Rules", "jurisdiction": "US", "severity": "high", "clause_types": ["compliance", "disclosure", "liability"]},
                {"name": "Basel III", "jurisdiction": "Global", "severity": "medium", "clause_types": ["compliance", "risk_management"]},
                {"name": "MiFID II", "jurisdiction": "EU", "severity": "high", "clause_types": ["compliance", "reporting"]},
            ],
            risk_thresholds={"compliance": 0.75, "liability": 0.7, "data_privacy": 0.65, "financial_reporting": 0.8},
            workflow_templates=["sox_compliance_review", "vendor_due_diligence", "regulatory_filing_review"],
            benchmark_data={"avg_risk_score": 0.58, "avg_negotiation_days": 52, "sla_compliance_rate": 0.92},
            compliance_mappings={"SOX": ["compliance", "audit", "liability"], "SEC": ["compliance", "disclosure"]},
        )

        self._packs[Vertical.MANUFACTURING] = VerticalPack(
            vertical=Vertical.MANUFACTURING,
            name="Manufacturing Intelligence Pack",
            description="Manufacturing contract intelligence with supply chain, quality, and regulatory compliance",
            regulations=[
                {"name": "ISO 9001", "jurisdiction": "Global", "severity": "medium", "clause_types": ["quality", "compliance", "warranty"]},
                {"name": "REACH", "jurisdiction": "EU", "severity": "high", "clause_types": ["compliance", "environmental"]},
                {"name": "Cyber Resilience Act", "jurisdiction": "EU", "severity": "high", "clause_types": ["security", "compliance"]},
            ],
            risk_thresholds={"warranty": 0.6, "liability": 0.65, "quality": 0.7, "supply_chain": 0.6},
            workflow_templates=["supplier_quality_review", "manufacturing_agreement", "supply_chain_risk_assessment"],
            benchmark_data={"avg_risk_score": 0.38, "avg_negotiation_days": 35, "sla_compliance_rate": 0.90},
            compliance_mappings={"ISO 9001": ["quality", "compliance", "warranty"], "REACH": ["compliance", "environmental"]},
        )

        self._packs[Vertical.PROCUREMENT] = VerticalPack(
            vertical=Vertical.PROCUREMENT,
            name="Procurement Intelligence Pack",
            description="Strategic procurement contract intelligence with vendor management and SLA optimization",
            regulations=[
                {"name": "Public Procurement Directives", "jurisdiction": "EU", "severity": "high", "clause_types": ["compliance", "transparency"]},
                {"name": "Anti-Kickback", "jurisdiction": "US", "severity": "critical", "clause_types": ["compliance", "ethics"]},
            ],
            risk_thresholds={"payment": 0.6, "liability": 0.65, "sla": 0.7, "termination": 0.55},
            workflow_templates=["vendor_onboarding", "procurement_review", "sla_negotiation"],
            benchmark_data={"avg_risk_score": 0.40, "avg_negotiation_days": 30, "sla_compliance_rate": 0.85},
            compliance_mappings={"Public Procurement": ["compliance", "transparency"]},
        )

        self._packs[Vertical.INSURANCE] = VerticalPack(
            vertical=Vertical.INSURANCE,
            name="Insurance Intelligence Pack",
            description="Insurance contract intelligence with regulatory compliance and risk modeling",
            regulations=[
                {"name": "Solvency II", "jurisdiction": "EU", "severity": "critical", "clause_types": ["compliance", "risk_management", "reporting"]},
                {"name": "State Insurance Regulations", "jurisdiction": "US", "severity": "high", "clause_types": ["compliance", "licensing"]},
            ],
            risk_thresholds={"liability": 0.75, "indemnification": 0.7, "compliance": 0.7, "coverage": 0.65},
            workflow_templates=["policy_review", "reinsurance_agreement", "claims_handling_review"],
            benchmark_data={"avg_risk_score": 0.55, "avg_negotiation_days": 40, "sla_compliance_rate": 0.87},
            compliance_mappings={"Solvency II": ["compliance", "risk_management", "reporting"]},
        )

        self._packs[Vertical.ENERGY] = VerticalPack(
            vertical=Vertical.ENERGY,
            name="Energy Intelligence Pack",
            description="Energy sector contract intelligence with environmental, regulatory, and commodity risk",
            regulations=[
                {"name": "EPA Regulations", "jurisdiction": "US", "severity": "high", "clause_types": ["compliance", "environmental", "liability"]},
                {"name": "Paris Agreement", "jurisdiction": "Global", "severity": "medium", "clause_types": ["compliance", "environmental"]},
                {"name": "FERC Regulations", "jurisdiction": "US", "severity": "high", "clause_types": ["compliance", "pricing"]},
            ],
            risk_thresholds={"environmental": 0.7, "liability": 0.65, "compliance": 0.65, "pricing": 0.6},
            workflow_templates=["energy_trading_agreement", "environmental_compliance_review", "infrastructure_contract"],
            benchmark_data={"avg_risk_score": 0.48, "avg_negotiation_days": 38, "sla_compliance_rate": 0.89},
            compliance_mappings={"EPA": ["compliance", "environmental", "liability"], "FERC": ["compliance", "pricing"]},
        )

    def get_pack(self, vertical: Vertical) -> VerticalPack | None:
        """Get the intelligence pack for a vertical."""
        return self._packs.get(vertical)

    def list_verticals(self) -> list[dict[str, Any]]:
        """List all available vertical packs."""
        return [
            {"vertical": v.value, "name": p.name, "description": p.description,
             "regulations": len(p.regulations), "workflows": len(p.workflow_templates)}
            for v, p in self._packs.items()
        ]

    def get_risk_thresholds(self, vertical: Vertical) -> dict[str, float]:
        """Get industry-specific risk thresholds."""
        pack = self._packs.get(vertical)
        return pack.risk_thresholds if pack else {}

    def get_compliance_mappings(self, vertical: Vertical) -> dict[str, list[str]]:
        """Get compliance mappings for a vertical."""
        pack = self._packs.get(vertical)
        return pack.compliance_mappings if pack else {}

    def get_vertical_summary(self) -> dict[str, Any]:
        """Get vertical intelligence summary."""
        return {
            "total_verticals": len(self._packs),
            "verticals": self.list_verticals(),
            "total_regulations": sum(len(p.regulations) for p in self._packs.values()),
            "total_workflows": sum(len(p.workflow_templates) for p in self._packs.values()),
        }


# ── Global singleton ───────────────────────────────────────────────

vertical_intelligence = VerticalIntelligenceService()
