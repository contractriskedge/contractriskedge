"""Exposure propagation across contract families.

Rolls up risk scores through contract hierarchies so that a parent
contract's risk score reflects aggregated risks from all children.
Supports weighted propagation based on relationship type.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# Weights for different relationship types in risk propagation
RELATIONSHIP_RISK_WEIGHTS = {
    "parent": 0.0,  # Parents don't inherit risk from parents
    "child": 0.3,   # Children contribute 30% of their risk to parents
    "amendment": 0.5,  # Amendments contribute 50%
    "addendum": 0.4,   # Addenda contribute 40%
    "dpa": 0.2,        # DPAs contribute 20%
}


@dataclass
class PropagatedRisk:
    """Result of risk propagation for a contract family."""

    contract_id: str
    direct_risk_score: float
    propagated_risk_score: float
    total_risk_score: float
    contribution_breakdown: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "contract_id": self.contract_id,
            "direct_risk_score": round(self.direct_risk_score, 3),
            "propagated_risk_score": round(self.propagated_risk_score, 3),
            "total_risk_score": round(self.total_risk_score, 3),
            "contribution_breakdown": self.contribution_breakdown,
        }


class ExposurePropagator:
    """Propagates risk scores through contract hierarchies.

    Computes aggregate risk scores by rolling up child contract
    risks to parent contracts, weighted by relationship type.
    """

    def __init__(self, repo) -> None:
        """Initialize the propagator.

        Args:
            repo: DatabaseRepository instance for data access.
        """
        self._repo = repo

    async def propagate_for_contract(
        self, contract_id: str
    ) -> PropagatedRisk:
        """Compute propagated risk for a single contract.

        Calculates the total risk score by combining the contract's
        own risk with propagated risks from its children.

        Args:
            contract_id: The contract to propagate risk for.

        Returns:
            PropagatedRisk result.
        """
        contract = await self._repo.get_contract(contract_id)
        if contract is None:
            return PropagatedRisk(
                contract_id=contract_id,
                direct_risk_score=0.0,
                propagated_risk_score=0.0,
                total_risk_score=0.0,
                contribution_breakdown=[],
            )

        direct_score = self._get_contract_risk_score(contract)

        # Get all relationships
        all_rels = await self._repo.list_all_relationships()
        from models.relationship_graph import ContractRelationship, RelationshipGraph

        relationships = [
            ContractRelationship.from_dict(rel) for rel in all_rels
        ]
        graph = RelationshipGraph(relationships)

        # Find all descendants (children, amendments, etc.)
        descendants = graph.find_descendants(contract_id)

        propagated_score = 0.0
        contribution_breakdown = []

        for child_id, rel_type in descendants:
            child_contract = await self._repo.get_contract(child_id)
            if child_contract is None:
                continue

            child_score = self._get_contract_risk_score(child_contract)
            weight = RELATIONSHIP_RISK_WEIGHTS.get(rel_type.value, 0.3)
            contribution = child_score * weight

            propagated_score += contribution
            contribution_breakdown.append({
                "child_contract_id": child_id,
                "child_filename": child_contract.get("filename", "unknown"),
                "relationship_type": rel_type.value,
                "child_risk_score": round(child_score, 3),
                "weight": weight,
                "contribution": round(contribution, 3),
            })

        total_score = min(direct_score + propagated_score, 1.0)

        return PropagatedRisk(
            contract_id=contract_id,
            direct_risk_score=direct_score,
            propagated_risk_score=propagated_score,
            total_risk_score=total_score,
            contribution_breakdown=contribution_breakdown,
        )

    async def propagate_all(self) -> List[PropagatedRisk]:
        """Propagate risks for all contracts in the database.

        Propagates from leaves upward, updating each contract's
        risk score in the database.

        Returns:
            List of PropagatedRisk results for all contracts.
        """
        # Get all contracts
        all_rels = await self._repo.list_all_relationships()
        from models.relationship_graph import ContractRelationship, RelationshipGraph

        relationships = [
            ContractRelationship.from_dict(rel) for rel in all_rels
        ]
        graph = RelationshipGraph(relationships)

        # Collect all unique contract IDs from relationships
        contract_ids: Set[str] = set()
        for rel in all_rels:
            contract_ids.add(rel["parent_contract_id"])
            contract_ids.add(rel["child_contract_id"])

        results = []
        for cid in contract_ids:
            result = await self.propagate_for_contract(cid)
            results.append(result)

            # Update the contract's risk score in the database
            await self._repo.update_contract_risk_score(
                cid, result.total_risk_score
            )

        return results

    def _get_contract_risk_score(self, contract: Dict[str, Any]) -> float:
        """Extract or compute the risk score for a contract.

        Args:
            contract: Contract data dict.

        Returns:
            Risk score between 0.0 and 1.0.
        """
        # Check if contract has a stored risk_score
        score = contract.get("risk_score")
        if score is not None:
            try:
                return float(score)
            except (ValueError, TypeError):
                pass

        # Compute from metadata if available
        metadata = contract.get("metadata", {})
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        # Default risk based on contract type
        type_risk_map = {
            "master_service_agreement": 0.3,
            "nda": 0.2,
            "statement_of_work": 0.4,
            "license": 0.3,
            "employment": 0.5,
            "lease": 0.3,
            "service_agreement": 0.35,
            "other": 0.25,
        }

        return type_risk_map.get(contract.get("contract_type", "other"), 0.25)
