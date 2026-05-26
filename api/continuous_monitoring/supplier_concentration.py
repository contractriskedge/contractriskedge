"""Supplier concentration analysis report + risk heatmap (V2-036).

Analyzes supplier concentration across the contract portfolio,
identifies over-reliance on single suppliers, and generates
risk heatmap visualizations.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SupplierExposure:
    """A supplier's exposure across the portfolio."""

    supplier_name: str
    supplier_id: str
    contract_count: int
    total_contract_value: float
    currency: str = "USD"
    risk_score: float = 0.0
    risk_level: str = "low"
    industry: Optional[str] = None
    contracts: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    average_contract_value: float = 0.0
    concentration_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supplier_name": self.supplier_name,
            "supplier_id": self.supplier_id,
            "contract_count": self.contract_count,
            "total_contract_value": self.total_contract_value,
            "currency": self.currency,
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level,
            "industry": self.industry,
            "contracts": self.contracts,
            "categories": self.categories,
            "average_contract_value": round(self.average_contract_value, 2),
            "concentration_percent": round(self.concentration_percent, 2),
        }


@dataclass
class ConcentrationRisk:
    """Concentration risk analysis for a supplier category."""

    category: str
    supplier_count: int
    total_value: float
    top_supplier_name: Optional[str] = None
    top_supplier_percent: float = 0.0
    herfindahl_index: float = 0.0  # HHI measure of concentration
    concentration_level: str = "low"  # low, moderate, high, very_high
    risk_score: float = 0.0
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "supplier_count": self.supplier_count,
            "total_value": self.total_value,
            "top_supplier_name": self.top_supplier_name,
            "top_supplier_percent": round(self.top_supplier_percent, 2),
            "herfindahl_index": round(self.herfindahl_index, 4),
            "concentration_level": self.concentration_level,
            "risk_score": round(self.risk_score, 2),
            "recommendation": self.recommendation,
        }


class SupplierConcentrationAnalyzer:
    """Analyzes supplier concentration and generates risk heatmaps.

    Evaluates portfolio-wide supplier exposure, identifies concentration
    risks, and generates actionable recommendations.

    Usage:
        analyzer = SupplierConcentrationAnalyzer()
        report = await analyzer.analyze_portfolio(contracts)
        heatmap = await analyzer.generate_heatmap(tenant_id)
    """

    def __init__(self, db_pool: Optional[Any] = None) -> None:
        """Initialize the supplier concentration analyzer.

        Args:
            db_pool: Optional database pool.
        """
        self._db_pool = db_pool
        self._exposures: Dict[str, SupplierExposure] = {}

        # Concentration thresholds (HHI-based)
        self._concentration_thresholds = {
            "very_high": 0.25,   # HHI > 2500
            "high": 0.15,        # HHI > 1500
            "moderate": 0.10,    # HHI > 1000
            "low": 0.0,          # HHI <= 1000
        }

    async def analyze_portfolio(
        self,
        contracts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze supplier concentration across a contract portfolio.

        Args:
            contracts: List of contract dicts with supplier info.

        Returns:
            Dict with concentration analysis.
        """
        # Group contracts by supplier
        supplier_contracts: Dict[str, List[Dict[str, Any]]] = {}
        supplier_info: Dict[str, Dict[str, Any]] = {}

        for contract in contracts:
            supplier = contract.get("counterparty") or contract.get("supplier_name") or "Unknown"
            supplier_id = contract.get("counterparty_id") or contract.get("supplier_id") or supplier.lower().replace(" ", "_")

            if supplier_id not in supplier_contracts:
                supplier_contracts[supplier_id] = []
                supplier_info[supplier_id] = {
                    "name": supplier,
                    "industry": contract.get("supplier_industry") or contract.get("industry"),
                }
            supplier_contracts[supplier_id].append(contract)

        # Compute total portfolio value
        total_value = sum(
            contract.get("contract_value", 0) or 0
            for contract in contracts
        )

        # Build exposures
        exposures: List[SupplierExposure] = []
        for supplier_id, scontracts in supplier_contracts.items():
            info = supplier_info.get(supplier_id, {})
            total_supplier_value = sum(
                c.get("contract_value", 0) or 0 for c in scontracts
            )

            exposure = SupplierExposure(
                supplier_name=info.get("name", "Unknown"),
                supplier_id=supplier_id,
                contract_count=len(scontracts),
                total_contract_value=total_supplier_value,
                risk_score=self._compute_supplier_risk_score(
                    len(scontracts), total_supplier_value, total_value
                ),
                industry=info.get("industry"),
                contracts=[c.get("contract_id", "unknown") for c in scontracts],
                categories=list(set(
                    c.get("contract_type", "other") for c in scontracts
                )),
                average_contract_value=total_supplier_value / max(len(scontracts), 1),
                concentration_percent=(total_supplier_value / max(total_value, 1)) * 100,
            )
            exposure.risk_level = self._risk_level_from_score(exposure.risk_score)
            exposures.append(exposure)
            self._exposures[supplier_id] = exposure

        # Sort by concentration percent descending
        exposures.sort(key=lambda e: e.concentration_percent, reverse=True)

        # Compute HHI
        market_shares = [e.total_contract_value / max(total_value, 1) for e in exposures]
        hhi = sum(ms ** 2 for ms in market_shares)

        # Determine concentration level
        concentration_level = "low"
        for level, threshold in sorted(
            self._concentration_thresholds.items(), key=lambda x: -x[1]
        ):
            if hhi >= threshold:
                concentration_level = level
                break

        return {
            "total_suppliers": len(exposures),
            "total_contracts": len(contracts),
            "total_portfolio_value": total_value,
            "herfindahl_hirschman_index": round(hhi, 4),
            "concentration_level": concentration_level,
            "top_suppliers": [e.to_dict() for e in exposures[:10]],
            "high_risk_suppliers": [
                e.to_dict() for e in exposures if e.risk_level in ("high", "critical")
            ],
            "single_supplier_dependencies": [
                e.to_dict() for e in exposures if e.concentration_percent > 30
            ],
        }

    def _compute_supplier_risk_score(
        self,
        contract_count: int,
        total_value: float,
        portfolio_value: float,
    ) -> float:
        """Compute risk score for a supplier.

        Args:
            contract_count: Number of contracts.
            total_value: Total contract value with supplier.
            portfolio_value: Total portfolio value.

        Returns:
            Risk score 0-10.
        """
        score = 0.0

        # Concentration risk
        concentration = total_value / max(portfolio_value, 1)
        if concentration > 0.3:
            score += 4.0
        elif concentration > 0.2:
            score += 3.0
        elif concentration > 0.1:
            score += 2.0
        elif concentration > 0.05:
            score += 1.0

        # Single point of failure risk
        if contract_count == 1 and concentration > 0.1:
            score += 2.0

        # Volume risk (many contracts with same supplier)
        if contract_count > 10:
            score += 1.0

        return min(10.0, score)

    def _risk_level_from_score(self, score: float) -> str:
        """Convert risk score to level.

        Args:
            score: Risk score.

        Returns:
            Risk level.
        """
        if score >= 7.0:
            return "critical"
        elif score >= 5.0:
            return "high"
        elif score >= 3.0:
            return "medium"
        else:
            return "low"

    async def generate_heatmap(self, tenant_id: str) -> Dict[str, Any]:
        """Generate supplier risk heatmap data.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with heatmap data.
        """
        exposures = list(self._exposures.values())

        # Heatmap cells: supplier x risk dimension
        heatmap_cells = []
        for exp in exposures[:20]:  # Top 20 suppliers
            cells = {
                "supplier_name": exp.supplier_name,
                "supplier_id": exp.supplier_id,
                "concentration_risk": min(10, exp.concentration_percent / 10),
                "volume_risk": min(10, exp.contract_count * 1.5),
                "value_risk": min(10, exp.total_contract_value / 100000),
                "overall_risk": exp.risk_score,
            }
            heatmap_cells.append(cells)

        return {
            "tenant_id": tenant_id,
            "generated_at": datetime.utcnow().isoformat(),
            "heatmap": heatmap_cells,
            "color_scale": {
                "low": "#22C55E",
                "medium": "#EAB308",
                "high": "#F97316",
                "critical": "#DC2626",
            },
            "dimensions": [
                {"id": "concentration_risk", "name": "Concentration Risk", "description": "Risk from over-reliance on single supplier"},
                {"id": "volume_risk", "name": "Volume Risk", "description": "Risk from high volume of contracts with one supplier"},
                {"id": "value_risk", "name": "Value Risk", "description": "Risk from high financial exposure to supplier"},
                {"id": "overall_risk", "name": "Overall Risk", "description": "Composite supplier risk score"},
            ],
        }

    async def get_category_analysis(self) -> List[Dict[str, Any]]:
        """Get concentration analysis by contract category.

        Returns:
            List of ConcentrationRisk by category.
        """
        # Group exposures by category
        category_data: Dict[str, Dict[str, Any]] = {}

        for exp in self._exposures.values():
            for category in exp.categories:
                if category not in category_data:
                    category_data[category] = {
                        "suppliers": [],
                        "values": [],
                        "total_value": 0.0,
                    }
                category_data[category]["suppliers"].append(exp.supplier_name)
                category_data[category]["values"].append(exp.total_contract_value)
                category_data[category]["total_value"] += exp.total_contract_value

        results = []
        for category, data in category_data.items():
            if not data["values"]:
                continue

            total = data["total_value"]
            shares = [v / max(total, 1) for v in data["values"]]
            hhi = sum(s ** 2 for s in shares)

            # Find top supplier
            max_idx = data["values"].index(max(data["values"]))
            top_supplier = data["suppliers"][max_idx] if data["suppliers"] else None
            top_percent = (data["values"][max_idx] / max(total, 1)) * 100

            # Determine concentration level
            level = "low"
            for lvl, threshold in sorted(
                self._concentration_thresholds.items(), key=lambda x: -x[1]
            ):
                if hhi >= threshold:
                    level = lvl
                    break

            # Generate recommendation
            recommendation = self._generate_category_recommendation(
                level, len(data["suppliers"]), top_percent
            )

            results.append(ConcentrationRisk(
                category=category,
                supplier_count=len(data["suppliers"]),
                total_value=total,
                top_supplier_name=top_supplier,
                top_supplier_percent=top_percent,
                herfindahl_index=hhi,
                concentration_level=level,
                risk_score=min(10.0, hhi * 20),
                recommendation=recommendation,
            ))

        return [r.to_dict() for r in sorted(results, key=lambda r: -r.risk_score)]

    def _generate_category_recommendation(
        self,
        level: str,
        supplier_count: int,
        top_percent: float,
    ) -> str:
        """Generate recommendation based on concentration analysis.

        Args:
            level: Concentration level.
            supplier_count: Number of suppliers.
            top_percent: Top supplier percentage.

        Returns:
            Recommendation string.
        """
        if level == "very_high":
            return f"CRITICAL: Single supplier represents {top_percent:.0f}% of category. Develop diversification strategy immediately."
        elif level == "high":
            return f"High concentration risk. Consider RFQ process to identify alternative suppliers. Top supplier: {top_percent:.0f}%."
        elif level == "moderate":
            return f"Moderate concentration with {supplier_count} suppliers. Monitor and evaluate diversification options."
        else:
            return f"Well-diversified category with {supplier_count} suppliers. Maintain current strategy."

    async def get_report(self, tenant_id: str) -> Dict[str, Any]:
        """Generate a complete supplier concentration report.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with full report.
        """
        exposures = list(self._exposures.values())
        total_value = sum(e.total_contract_value for e in exposures)

        high_risk = [e for e in exposures if e.risk_level in ("high", "critical")]
        single_dependency = [e for e in exposures if e.concentration_percent > 30]

        return {
            "tenant_id": tenant_id,
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.utcnow().isoformat(),
            "executive_summary": {
                "total_suppliers": len(exposures),
                "total_portfolio_value": total_value,
                "high_risk_suppliers": len(high_risk),
                "single_dependency_suppliers": len(single_dependency),
                "top_supplier_percent": exposures[0].concentration_percent if exposures else 0,
            },
            "heatmap": await self.generate_heatmap(tenant_id),
            "category_analysis": await self.get_category_analysis(),
            "top_risks": [
                {
                    "supplier": e.supplier_name,
                    "risk_score": e.risk_score,
                    "risk_level": e.risk_level,
                    "concentration": e.concentration_percent,
                    "contract_count": e.contract_count,
                }
                for e in high_risk[:5]
            ],
            "recommendations": self._generate_portfolio_recommendations(
                high_risk, single_dependency
            ),
        }

    def _generate_portfolio_recommendations(
        self,
        high_risk: List[SupplierExposure],
        single_dependency: List[SupplierExposure],
    ) -> List[str]:
        """Generate portfolio-level recommendations.

        Args:
            high_risk: High risk suppliers.
            single_dependency: Single dependency suppliers.

        Returns:
            List of recommendation strings.
        """
        recommendations = []

        if len(high_risk) > 3:
            recommendations.append(
                f"High supplier concentration detected: {len(high_risk)} suppliers "
                f"pose significant risk. Implement supplier diversification program."
            )

        for dep in single_dependency[:3]:
            recommendations.append(
                f"Single-supplier dependency on {dep.supplier_name} "
                f"({dep.concentration_percent:.1f}% of portfolio). "
                f"Develop contingency sourcing plan."
            )

        if not recommendations:
            recommendations.append("Supplier concentration is within acceptable range. Continue monitoring.")

        return recommendations
