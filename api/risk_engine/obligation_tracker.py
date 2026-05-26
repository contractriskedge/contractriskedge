"""Obligation inheritance tracking across contract hierarchies.

Tracks how obligations flow from parent contracts (e.g., MSAs) to
child contracts (e.g., SOWs). When a parent MSA has obligations,
child SOWs should inherit them unless explicitly overridden.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class Obligation:
    """Represents a contractual obligation."""

    obligation_id: str
    contract_id: str
    clause_reference: str
    description: str
    category: str  # e.g., "confidentiality", "indemnification", "payment", "compliance"
    status: str = "active"  # active, fulfilled, waived, breached
    due_date: Optional[str] = None
    source: str = "direct"  # "direct" or "inherited"
    parent_obligation_id: Optional[str] = None
    override: bool = False  # True if child explicitly overrides parent obligation
    risk_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "obligation_id": self.obligation_id,
            "contract_id": self.contract_id,
            "clause_reference": self.clause_reference,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "due_date": self.due_date,
            "source": self.source,
            "parent_obligation_id": self.parent_obligation_id,
            "override": self.override,
            "risk_score": self.risk_score,
        }


# Default obligations by contract type
DEFAULT_OBLIGATIONS: Dict[str, List[Dict[str, Any]]] = {
    "master_service_agreement": [
        {
            "clause_reference": "Confidentiality",
            "description": "Maintain confidentiality of proprietary information shared during the engagement",
            "category": "confidentiality",
            "risk_score": 0.6,
        },
        {
            "clause_reference": "Indemnification",
            "description": "Indemnify against claims arising from breach of agreement",
            "category": "indemnification",
            "risk_score": 0.8,
        },
        {
            "clause_reference": "Limitation of Liability",
            "description": "Liability capped at total contract value unless otherwise specified",
            "category": "liability_limitation",
            "risk_score": 0.5,
        },
        {
            "clause_reference": "Governing Law",
            "description": "Disputes governed by specified jurisdiction's laws",
            "category": "compliance",
            "risk_score": 0.4,
        },
        {
            "clause_reference": "Termination",
            "description": "Either party may terminate with 30 days written notice",
            "category": "termination",
            "risk_score": 0.3,
        },
    ],
    "nda": [
        {
            "clause_reference": "Confidentiality",
            "description": "Protect confidential information with reasonable care for duration of agreement plus 3 years",
            "category": "confidentiality",
            "risk_score": 0.7,
        },
        {
            "clause_reference": "Non-Disclosure",
            "description": "Do not disclose confidential information to third parties without written consent",
            "category": "confidentiality",
            "risk_score": 0.6,
        },
    ],
    "statement_of_work": [
        {
            "clause_reference": "Deliverables",
            "description": "Deliver specified work products according to agreed timeline",
            "category": "compliance",
            "risk_score": 0.5,
        },
        {
            "clause_reference": "Payment Terms",
            "description": "Payment due within 30 days of invoice receipt",
            "category": "payment_terms",
            "risk_score": 0.4,
        },
    ],
    "license": [
        {
            "clause_reference": "License Grant",
            "description": "Grant non-exclusive, non-transferable license to use software",
            "category": "intellectual_property",
            "risk_score": 0.5,
        },
        {
            "clause_reference": "Usage Restrictions",
            "description": "No reverse engineering, sublicensing, or unauthorized distribution",
            "category": "compliance",
            "risk_score": 0.6,
        },
    ],
}


class ObligationTracker:
    """Tracks obligations across contract hierarchies.

    Handles inheritance of obligations from parent contracts to
    children, detects overrides, and identifies gaps in obligation
    coverage.
    """

    def __init__(self, repo) -> None:
        """Initialize the tracker.

        Args:
            repo: DatabaseRepository instance for data access.
        """
        self._repo = repo

    async def get_obligations(
        self, contract_id: str, include_inherited: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all obligations for a contract, including inherited ones.

        Args:
            contract_id: The contract to get obligations for.
            include_inherited: Whether to include inherited obligations.

        Returns:
            List of obligation dicts.
        """
        contract = await self._repo.get_contract(contract_id)
        if contract is None:
            return []

        direct_obligations = self._get_direct_obligations(contract)
        result = list(direct_obligations)

        if include_inherited:
            inherited = await self._get_inherited_obligations(contract_id, contract)
            result.extend(inherited)

        return result

    def _get_direct_obligations(
        self, contract: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get direct obligations based on contract type.

        Args:
            contract: Contract data dict.

        Returns:
            List of direct obligation dicts.
        """
        import uuid
        contract_type = contract.get("contract_type", "other")
        defaults = DEFAULT_OBLIGATIONS.get(contract_type, [])

        obligations = []
        for i, obl in enumerate(defaults):
            obligations.append({
                "obligation_id": f"obl_{contract['contract_id']}_{i}",
                "contract_id": contract["contract_id"],
                "clause_reference": obl["clause_reference"],
                "description": obl["description"],
                "category": obl["category"],
                "status": "active",
                "due_date": None,
                "source": "direct",
                "parent_obligation_id": None,
                "override": False,
                "risk_score": obl["risk_score"],
            })

        return obligations

    async def _get_inherited_obligations(
        self, contract_id: str, contract: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get obligations inherited from parent contracts.

        Args:
            contract_id: The child contract ID.
            contract: The child contract data.

        Returns:
            List of inherited obligation dicts.
        """
        # Get all relationships
        all_rels = await self._repo.list_all_relationships()
        from models.relationship_graph import ContractRelationship, RelationshipGraph

        relationships = [
            ContractRelationship.from_dict(rel) for rel in all_rels
        ]
        graph = RelationshipGraph(relationships)

        # Find parent contracts
        parents = graph.find_ancestors(contract_id)
        if not parents:
            return []

        inherited = []
        seen_categories: Set[str] = set()

        # Get direct obligations of this contract to check for overrides
        direct = self._get_direct_obligations(contract)
        direct_categories = {o["category"] for o in direct}

        for parent_id, rel_type in parents:
            parent_contract = await self._repo.get_contract(parent_id)
            if parent_contract is None:
                continue

            parent_obligations = self._get_direct_obligations(parent_contract)

            for i, obl in enumerate(parent_obligations):
                category = obl["category"]

                # Skip if this category is already covered (direct or inherited)
                if category in seen_categories:
                    continue

                # Check if child explicitly overrides this category
                is_overridden = category in direct_categories
                seen_categories.add(category)

                inherited.append({
                    "obligation_id": f"inh_{contract_id}_{parent_id}_{i}",
                    "contract_id": contract_id,
                    "clause_reference": obl["clause_reference"],
                    "description": obl["description"],
                    "category": category,
                    "status": "active",
                    "due_date": None,
                    "source": "inherited",
                    "parent_obligation_id": obl["obligation_id"],
                    "override": is_overridden,
                    "risk_score": obl["risk_score"] * (0.8 if is_overridden else 1.0),
                    "inherited_from": {
                        "contract_id": parent_id,
                        "relationship_type": rel_type.value,
                    },
                })

        return inherited

    async def get_obligation_summary(
        self, contract_id: str
    ) -> Dict[str, Any]:
        """Get a summary of obligations for a contract.

        Args:
            contract_id: The contract to summarize.

        Returns:
            Dict with obligation summary.
        """
        obligations = await self.get_obligations(contract_id)

        total = len(obligations)
        direct = sum(1 for o in obligations if o["source"] == "direct")
        inherited = sum(1 for o in obligations if o["source"] == "inherited")
        overridden = sum(1 for o in obligations if o.get("override"))
        by_category: Dict[str, int] = {}
        total_risk = 0.0

        for o in obligations:
            cat = o["category"]
            by_category[cat] = by_category.get(cat, 0) + 1
            total_risk += o["risk_score"]

        avg_risk = total_risk / total if total > 0 else 0.0

        return {
            "contract_id": contract_id,
            "total_obligations": total,
            "direct_obligations": direct,
            "inherited_obligations": inherited,
            "overridden_obligations": overridden,
            "average_risk_score": round(avg_risk, 3),
            "categories": by_category,
            "obligations": obligations,
        }
