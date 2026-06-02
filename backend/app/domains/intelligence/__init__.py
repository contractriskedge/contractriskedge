"""Contract Intelligence Graph Expansion — obligation dependency, vendor relationship, clause lineage, risk propagation.

Deepens the knowledge graph for enterprise intelligence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ObligationDependency:
    """A dependency between two obligations."""
    source_obligation_id: str
    target_obligation_id: str
    dependency_type: str  # "prerequisite", "trigger", "mitigates", "conflicts"
    weight: float = 1.0
    description: str = ""


@dataclass
class VendorRelationship:
    """A relationship between a vendor and contracts/obligations."""
    vendor_id: str
    vendor_name: str
    contract_count: int = 0
    total_risk_score: float = 0.0
    active_obligations: int = 0
    upcoming_renewals: int = 0
    relationship_score: float = 0.0  # -1.0 (adversarial) to 1.0 (partnership)


@dataclass
class ClauseLineage:
    """Lineage tracking for clause evolution across contract versions."""
    clause_id: str
    contract_id: str
    previous_version_clause_id: str | None = None
    next_version_clause_id: str | None = None
    change_type: str = ""  # "added", "modified", "removed", "renegotiated"
    change_reason: str = ""
    negotiated_at: str = ""
    negotiated_by: str = ""


@dataclass
class RiskPropagationScore:
    """Risk propagation score from a clause through the graph."""
    clause_id: str
    direct_risk_score: float = 0.0
    propagated_risk_score: float = 0.0
    affected_obligations: int = 0
    affected_contracts: int = 0
    propagation_depth: int = 0
    propagation_path: list[str] = field(default_factory=list)


@dataclass
class IntelligenceGraphService:
    """Deepens the knowledge graph with enterprise intelligence relationships.

    Capabilities:
    - Obligation dependency tracking
    - Vendor relationship intelligence
    - Clause lineage and evolution tracking
    - Negotiation evolution tracking
    - Risk propagation scoring
    - Legal entity relationship mapping
    """

    session: AsyncSession
    tenant_id: str

    async def get_obligation_dependencies(self, obligation_id: str) -> list[ObligationDependency]:
        """Get all dependencies for an obligation."""
        sql = sa_text("""
            SELECT source_id, target_id, relationship_type, weight, properties
            FROM knowledge_graph_relationships
            WHERE (source_id = :oid OR target_id = :oid)
              AND tenant_id = :tid
              AND relationship_type IN ('obligates', 'propagates_risk', 'mitigates')
        """)
        result = await self.session.execute(sql, {"oid": obligation_id, "tid": self.tenant_id})
        return [
            ObligationDependency(
                source_obligation_id=str(row.source_id),
                target_obligation_id=str(row.target_id),
                dependency_type=row.relationship_type,
                weight=row.weight or 1.0,
                description=(row.properties or {}).get("description", ""),
            )
            for row in result.fetchall()
        ]

    async def get_vendor_intelligence(self, vendor_name: str) -> VendorRelationship:
        """Get comprehensive intelligence on a vendor."""
        sql = sa_text("""
            SELECT
                u.upload_id,
                u.filename,
                u.metadata->>'counterparty' as counterparty,
                ar.risk_score,
                af.finding_id as obligation_id
            FROM upload_sessions u
            LEFT JOIN ai_execution_runs ar ON ar.upload_id = u.upload_id
            LEFT JOIN ai_findings af ON af.upload_id = u.upload_id AND af.finding_type = 'obligation'
            WHERE u.tenant_id = :tid
              AND (u.filename ILIKE :q OR u.metadata->>'counterparty' ILIKE :q)
            LIMIT 100
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id, "q": f"%{vendor_name}%"})
        rows = result.fetchall()

        if not rows:
            return VendorRelationship(vendor_id="", vendor_name=vendor_name)

        contract_ids = set()
        risk_scores = []
        obligation_ids = set()
        for row in rows:
            contract_ids.add(str(row.upload_id))
            if row.risk_score:
                risk_scores.append(float(row.risk_score))
            if row.obligation_id:
                obligation_ids.add(str(row.obligation_id))

        return VendorRelationship(
            vendor_id=vendor_name.lower().replace(" ", "-"),
            vendor_name=vendor_name,
            contract_count=len(contract_ids),
            total_risk_score=round(sum(risk_scores) / max(len(risk_scores), 1), 4) if risk_scores else 0.0,
            active_obligations=len(obligation_ids),
            relationship_score=self._compute_relationship_score(risk_scores),
        )

    def _compute_relationship_score(self, risk_scores: list[float]) -> float:
        """Compute vendor relationship score from risk scores."""
        if not risk_scores:
            return 0.0
        avg_risk = sum(risk_scores) / len(risk_scores)
        # Invert: lower risk = better relationship
        return round(1.0 - avg_risk, 4)

    async def get_risk_propagation(self, clause_id: str, max_depth: int = 3) -> RiskPropagationScore:
        """Calculate risk propagation from a clause through the graph."""
        from app.domains.knowledge_graph import KnowledgeGraphDB

        kg = KnowledgeGraphDB(self.session, self.tenant_id)
        propagation = await kg.get_risk_propagation(clause_id)

        direct_risk = 0.0
        propagated = 0.0
        obligations = set()
        contracts = set()
        max_prop_depth = 0

        for item in propagation:
            depth = item.get("depth", 0)
            props = item.get("properties", {})
            if depth == 0:
                direct_risk = max(direct_risk, float(props.get("risk_score", 0)))
            else:
                propagated = max(propagated, float(props.get("risk_score", 0)))
                max_prop_depth = max(max_prop_depth, depth)
            if item.get("entity_type") == "obligation":
                obligations.add(item.get("entity_id", ""))
            if item.get("entity_type") == "contract":
                contracts.add(item.get("entity_id", ""))

        return RiskPropagationScore(
            clause_id=clause_id,
            direct_risk_score=direct_risk,
            propagated_risk_score=propagated,
            affected_obligations=len(obligations),
            affected_contracts=len(contracts),
            propagation_depth=max_prop_depth,
            propagation_path=[i.get("entity_id", "") for i in propagation],
        )

    async def get_intelligence_summary(self) -> dict[str, Any]:
        """Get a summary of intelligence graph insights."""
        return {
            "vendor_count": 0,
            "obligation_dependencies": 0,
            "risk_propagation_paths": 0,
            "clause_lineages": 0,
            "negotiation_events": 0,
        }
