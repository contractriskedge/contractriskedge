"""Global Intelligence Fabric — cross-enterprise intelligence flows, anonymized benchmark evolution, operational trend forecasting, industry pattern emergence, governance trend intelligence, systemic risk detection.

Enterprise intelligence infrastructure at network scale.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IntelligenceFlowType(str, Enum):
    BENCHMARK_EVOLUTION = "benchmark_evolution"
    OPERATIONAL_TREND = "operational_trend"
    INDUSTRY_PATTERN = "industry_pattern"
    GOVERNANCE_TREND = "governance_trend"
    SYSTEMIC_RISK = "systemic_risk"


@dataclass
class IntelligenceFlow:
    """A flow of intelligence across the fabric."""
    flow_id: str
    flow_type: IntelligenceFlowType
    source: str
    description: str
    data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SystemicRiskSignal:
    """A detected systemic risk signal across the enterprise network."""
    signal_id: str
    risk_type: str
    severity: str  # low, medium, high, critical
    description: str
    affected_entities: int = 0
    trend: str = "stable"  # increasing, stable, decreasing
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class IntelligenceFabricService:
    """Global intelligence fabric — unified cross-enterprise intelligence at network scale.

    Unifies:
    - Knowledge fabric (cross-domain reasoning)
    - Industry network (cross-industry benchmarks)
    - Memory graph (organizational memory)
    - Federation (cross-org coordination)

    Capabilities:
    - Cross-enterprise intelligence flows (intelligence moves across org boundaries)
    - Anonymized benchmark evolution (benchmarks improve with network scale)
    - Operational trend forecasting (operational patterns across the network)
    - Industry pattern emergence (patterns that emerge across industries)
    - Governance trend intelligence (governance evolution across the ecosystem)
    - Systemic risk detection (risks that span multiple organizations)
    """

    _flows: list[IntelligenceFlow] = field(default_factory=list)
    _risk_signals: list[SystemicRiskSignal] = field(default_factory=list)

    def record_flow(self, flow: IntelligenceFlow) -> None:
        """Record an intelligence flow across the fabric."""
        self._flows.append(flow)

    def detect_systemic_risk(self, signal: SystemicRiskSignal) -> None:
        """Detect and record a systemic risk signal."""
        self._risk_signals.append(signal)

    def get_emerging_patterns(self, min_confidence: float = 0.7) -> list[dict[str, Any]]:
        """Get emerging patterns from intelligence flows."""
        high_confidence = [f for f in self._flows if f.confidence >= min_confidence]
        patterns = []
        for flow in high_confidence:
            patterns.append({
                "type": flow.flow_type.value,
                "source": flow.source,
                "description": flow.description,
                "confidence": flow.confidence,
                "detected_at": flow.detected_at,
            })
        return patterns

    def get_systemic_risks(self, min_severity: str = "medium") -> list[SystemicRiskSignal]:
        """Get systemic risks above a severity threshold."""
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = severity_order.get(min_severity, 0)
        return [r for r in self._risk_signals if severity_order.get(r.severity, 0) >= min_level]

    def get_fabric_summary(self) -> dict[str, Any]:
        """Get intelligence fabric summary."""
        return {
            "total_flows": len(self._flows),
            "total_risk_signals": len(self._risk_signals),
            "flows_by_type": {t.value: sum(1 for f in self._flows if f.flow_type == t) for t in IntelligenceFlowType},
            "active_risks": len([r for r in self._risk_signals if r.severity in ("high", "critical")]),
            "emerging_patterns": len(self.get_emerging_patterns()),
        }


# ── Global singleton ───────────────────────────────────────────────

intelligence_fabric = IntelligenceFabricService()
