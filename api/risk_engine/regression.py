"""Regression detection for downstream amendment impact alerts.

Detects when amendments or new versions of contracts change terms
in ways that increase risk. Compares pre/post amendment versions
and flags regressions with severity ratings.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Regression:
    """Represents a detected regression in contract terms."""

    regression_id: str
    contract_id: str
    related_contract_id: Optional[str]
    field: str
    old_value: str
    new_value: str
    direction: str  # "worsened", "improved", "changed"
    severity: str  # "critical", "high", "medium", "low", "info"
    description: str
    recommendation: Optional[str] = None
    detected_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "regression_id": self.regression_id,
            "contract_id": self.contract_id,
            "related_contract_id": self.related_contract_id,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "direction": self.direction,
            "severity": self.severity,
            "description": self.description,
            "recommendation": self.recommendation,
            "detected_at": self.detected_at,
        }


# Risk-increasing term changes (what to flag as regressions)
REGRESSION_RULES: Dict[str, Dict[str, Any]] = {
    "liability_cap": {
        "higher_is_riskier": True,
        "severity": "high",
        "description": "Liability cap increased, exposing more risk",
        "recommendation": "Review and negotiate liability cap back to original or acceptable level",
    },
    "indemnification_scope": {
        "broader_is_riskier": True,
        "severity": "high",
        "description": "Indemnification scope expanded",
        "recommendation": "Limit indemnification to direct damages only",
    },
    "confidentiality_term": {
        "longer_is_riskier": True,
        "severity": "medium",
        "description": "Confidentiality obligation period extended",
        "recommendation": "Verify extended confidentiality term is necessary",
    },
    "termination_for_convenience": {
        "removed_is_riskier": True,
        "severity": "high",
        "description": "Termination for convenience clause removed",
        "recommendation": "Restore mutual termination for convenience rights",
    },
    "non_compete_scope": {
        "broader_is_riskier": True,
        "severity": "medium",
        "description": "Non-compete scope broadened",
        "recommendation": "Limit non-compete to reasonable scope and duration",
    },
    "payment_terms": {
        "longer_is_riskier": True,
        "severity": "medium",
        "description": "Payment terms extended, delaying receivables",
        "recommendation": "Negotiate shorter payment terms",
    },
    "audit_rights": {
        "narrower_is_riskier": True,
        "severity": "medium",
        "description": "Audit rights restricted or removed",
        "recommendation": "Restore standard audit rights with reasonable notice",
    },
    "assignment": {
        "restricted_is_riskier": True,
        "severity": "medium",
        "description": "Assignment rights restricted without consent",
        "recommendation": "Ensure assignment rights for mergers and acquisitions",
    },
    "governing_law": {
        "changed_is_riskier": True,
        "severity": "critical",
        "description": "Governing law changed",
        "recommendation": "Ensure governing law remains favorable",
    },
    "dispute_resolution": {
        "changed_is_riskier": True,
        "severity": "high",
        "description": "Dispute resolution mechanism changed",
        "recommendation": "Review new dispute resolution terms carefully",
    },
}


class RegressionDetector:
    """Detects regressions in contract amendments and versions.

    Compares contract versions or related contracts to identify
    term changes that increase risk exposure.
    """

    def __init__(self, repo) -> None:
        """Initialize the detector.

        Args:
            repo: DatabaseRepository instance for data access.
        """
        self._repo = repo

    async def detect_regressions(
        self, contract_id: str
    ) -> List[Dict[str, Any]]:
        """Detect regressions for a contract.

        Compares the contract with its related contracts (amendments,
        addenda) and with any previous versions to find regressions.

        Args:
            contract_id: The contract to check.

        Returns:
            List of regression dicts.
        """
        contract = await self._repo.get_contract(contract_id)
        if contract is None:
            return []

        regressions: List[Dict[str, Any]] = []

        # 1. Check against related contracts (amendments, addenda)
        related_regressions = await self._check_related_contracts(contract)
        regressions.extend(related_regressions)

        # 2. Check against parent contract if this is a child
        parent_regressions = await self._check_parent_contract(contract)
        regressions.extend(parent_regressions)

        return regressions

    async def _check_related_contracts(
        self, contract: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check amendments and addenda for regressions.

        Args:
            contract: The contract data.

        Returns:
            List of regression dicts.
        """
        contract_id = contract["contract_id"]
        all_rels = await self._repo.list_all_relationships()
        from models.relationship_graph import ContractRelationship, RelationshipGraph

        relationships = [
            ContractRelationship.from_dict(rel) for rel in all_rels
        ]
        graph = RelationshipGraph(relationships)

        # Find related contracts (amendments, addenda)
        descendants = graph.find_descendants(contract_id)
        regressions = []

        for child_id, rel_type in descendants:
            if rel_type.value not in ("amendment", "addendum"):
                continue

            child_contract = await self._repo.get_contract(child_id)
            if child_contract is None:
                continue

            # Compare terms
            comparison = self._compare_contract_terms(
                original=contract,
                amendment=child_contract,
                relationship_type=rel_type.value,
            )
            regressions.extend(comparison)

        return regressions

    async def _check_parent_contract(
        self, contract: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check if this contract introduces regressions vs its parent.

        Args:
            contract: The child contract data.

        Returns:
            List of regression dicts.
        """
        contract_id = contract["contract_id"]
        all_rels = await self._repo.list_all_relationships()
        from models.relationship_graph import ContractRelationship, RelationshipGraph

        relationships = [
            ContractRelationship.from_dict(rel) for rel in all_rels
        ]
        graph = RelationshipGraph(relationships)

        parents = graph.find_ancestors(contract_id)
        regressions = []

        for parent_id, rel_type in parents:
            parent_contract = await self._repo.get_contract(parent_id)
            if parent_contract is None:
                continue

            # If this is a child SOW, check if it weakens parent terms
            comparison = self._compare_contract_terms(
                original=parent_contract,
                amendment=contract,
                relationship_type=f"child_vs_{rel_type.value}",
            )
            regressions.extend(comparison)

        return regressions

    def _compare_contract_terms(
        self,
        original: Dict[str, Any],
        amendment: Dict[str, Any],
        relationship_type: str,
    ) -> List[Dict[str, Any]]:
        """Compare terms between original and amendment contracts.

        Args:
            original: The original (parent/earlier) contract.
            amendment: The amendment (child/later) contract.
            relationship_type: Type of relationship.

        Returns:
            List of regression dicts.
        """
        import uuid

        regressions: List[Dict[str, Any]] = []
        now = datetime.utcnow().isoformat()

        meta_orig = original.get("metadata", {})
        if isinstance(meta_orig, str):
            try:
                meta_orig = json.loads(meta_orig)
            except (json.JSONDecodeError, TypeError):
                meta_orig = {}

        meta_amend = amendment.get("metadata", {})
        if isinstance(meta_amend, str):
            try:
                meta_amend = json.loads(meta_amend)
            except (json.JSONDecodeError, TypeError):
                meta_amend = {}

        # Compare key metadata fields
        for field, rules in REGRESSION_RULES.items():
            old_val = meta_orig.get(field, "")
            new_val = meta_amend.get(field, "")

            if not old_val or not new_val:
                continue

            if old_val == new_val:
                continue

            # Determine direction
            direction = self._determine_direction(
                field, old_val, new_val, rules
            )

            if direction == "changed" or direction == "worsened":
                severity = rules["severity"]
                regressions.append(Regression(
                    regression_id=str(uuid.uuid4()),
                    contract_id=amendment["contract_id"],
                    related_contract_id=original["contract_id"],
                    field=field,
                    old_value=str(old_val),
                    new_value=str(new_val),
                    direction=direction,
                    severity=severity,
                    description=rules["description"],
                    recommendation=rules.get("recommendation"),
                    detected_at=now,
                ).to_dict())

        # Pattern-based comparison on contract type
        if original.get("contract_type") != amendment.get("contract_type"):
            regressions.append(Regression(
                regression_id=str(uuid.uuid4()),
                contract_id=amendment["contract_id"],
                related_contract_id=original["contract_id"],
                field="contract_type",
                old_value=original.get("contract_type", "unknown"),
                new_value=amendment.get("contract_type", "unknown"),
                direction="changed",
                severity="info",
                description=f"Contract type changed from {original.get('contract_type')} to {amendment.get('contract_type')}",
                recommendation="Verify contract type change is intentional",
                detected_at=now,
            ).to_dict())

        return regressions

    def _determine_direction(
        self,
        field: str,
        old_val: str,
        new_val: str,
        rules: Dict[str, Any],
    ) -> str:
        """Determine if a change is a worsening, improvement, or neutral.

        Args:
            field: The field being compared.
            old_val: Original value.
            new_val: New value.
            rules: Rules dict for this field.

        Returns:
            "worsened", "improved", or "changed".
        """
        if rules.get("changed_is_riskier"):
            return "worsened" if old_val != new_val else "changed"

        # Try numeric comparison
        old_num = self._extract_number(old_val)
        new_num = self._extract_number(new_val)

        if old_num is not None and new_num is not None:
            if rules.get("higher_is_riskier"):
                return "worsened" if new_num > old_num else ("improved" if new_num < old_num else "changed")
            elif rules.get("longer_is_riskier"):
                return "worsened" if new_num > old_num else ("improved" if new_num < old_num else "changed")

        # Text-based comparison for scope-related fields
        if rules.get("broader_is_riskier") or rules.get("narrower_is_riskier"):
            scope_map = {
                "broader_is_riskier": ("worsened" if self._is_broader(new_val, old_val) else "improved"),
                "narrower_is_riskier": ("worsened" if self._is_narrower(new_val, old_val) else "improved"),
            }
            for key, result in scope_map.items():
                if rules.get(key):
                    return result

        if rules.get("removed_is_riskier"):
            if "not" in new_val.lower() or "removed" in new_val.lower() or "eliminated" in new_val.lower():
                return "worsened"

        return "changed"

    def _extract_number(self, value: str) -> Optional[float]:
        """Extract a numeric value from a string.

        Args:
            value: String potentially containing a number.

        Returns:
            Extracted number or None.
        """
        match = re.search(r"(\d+(?:\.\d+)?)", value)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def _is_broader(self, new_val: str, old_val: str) -> bool:
        """Check if new value represents broader scope.

        Args:
            new_val: New value.
            old_val: Old value.

        Returns:
            True if new value is broader.
        """
        broad_keywords = ["all", "any", "every", "unlimited", "worldwide"]
        narrow_keywords = ["limited", "specific", "certain", "some"]

        new_lower = new_val.lower()
        old_lower = old_val.lower()

        broad_score = sum(1 for kw in broad_keywords if kw in new_lower)
        narrow_score = sum(1 for kw in narrow_keywords if kw in old_lower)

        return broad_score > narrow_score

    def _is_narrower(self, new_val: str, old_val: str) -> bool:
        """Check if new value represents narrower scope.

        Args:
            new_val: New value.
            old_val: Old value.

        Returns:
            True if new value is narrower.
        """
        return self._is_broader(old_val, new_val)
