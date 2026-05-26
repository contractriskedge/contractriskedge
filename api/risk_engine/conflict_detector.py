"""Cross-contract clause conflict detection engine.

Compares clauses across related contracts (e.g., MSA vs SOW) to
detect contradictions such as different governing law, conflicting
payment terms, or inconsistent liability caps.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Conflict:
    """Represents a detected conflict between contracts."""

    conflict_id: str
    contract_id_a: str
    contract_id_b: str
    relationship_type: str
    category: str
    field: str
    value_a: str
    value_b: str
    severity: str  # "critical", "high", "medium", "low"
    description: str
    recommendation: Optional[str] = None
    clause_reference_a: Optional[str] = None
    clause_reference_b: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "contract_id_a": self.contract_id_a,
            "contract_id_b": self.contract_id_b,
            "relationship_type": self.relationship_type,
            "category": self.category,
            "field": self.field,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "severity": self.severity,
            "description": self.description,
            "recommendation": self.recommendation,
            "clause_reference_a": self.clause_reference_a,
            "clause_reference_b": self.clause_reference_b,
        }


# Patterns to look for in clause text for conflict detection
CONFLICT_PATTERNS: Dict[str, List[Dict[str, Any]]] = {
    "governing_law": [
        {
            "patterns": [
                r"governed by\s+(?:the\s+)?laws?\s+of\s+([^,.]+)",
                r"governing\s+law\s+(?:shall\s+be\s+)?([^,.]+)",
                r"governed\s+(?:and\s+)?construed\s+in\s+accordance\s+with\s+(?:the\s+)?laws?\s+of\s+([^,.]+)",
            ],
            "field": "governing_law",
            "severity": "critical",
            "category": "compliance",
        }
    ],
    "jurisdiction": [
        {
            "patterns": [
                r"(?:exclusive|non-exclusive|nonexclusive)?\s*(?:jurisdiction|venue)\s+(?:shall\s+be\s+)?(?:in\s+)?([^,.]+)",
                r"(?:submit|consent)\s+to\s+(?:the\s+)?(?:exclusive|non-exclusive|nonexclusive)?\s*(?:jurisdiction|venue)\s+of\s+([^,.]+)",
            ],
            "field": "jurisdiction",
            "severity": "high",
            "category": "compliance",
        }
    ],
    "liability_cap": [
        {
            "patterns": [
                r"liability\s+(?:shall\s+)?(?:be\s+)?limited\s+to\s+([^,.]+)",
                r"aggregate\s+liability\s+(?:shall\s+)?(?:not\s+)?exceed\s+([^,.]+)",
                r"cap\s+on\s+liability\s+(?:shall\s+be\s+)?([^,.]+)",
            ],
            "field": "liability_cap",
            "severity": "high",
            "category": "liability_limitation",
        }
    ],
    "confidentiality_term": [
        {
            "patterns": [
                r"confidential(?:ity)?\s+(?:obligations?\s+)?(?:shall\s+)?(?:survive|continue|remain)\s+(?:for\s+)?(?:a\s+period\s+of\s+)?(\d+\s*(?:years?|months?))",
                r"term\s+of\s+confidentiality\s+(?:shall\s+be\s+)?(\d+\s*(?:years?|months?))",
            ],
            "field": "confidentiality_term",
            "severity": "medium",
            "category": "confidentiality",
        }
    ],
    "indemnification": [
        {
            "patterns": [
                r"(?:shall|agrees\s+to)\s+(?:defend|indemnify|hold\s+harmless)\s+([^,.]+)",
                r"indemnification\s+(?:obligations?\s+)?(?:shall\s+)?(?:survive|continue)",
            ],
            "field": "indemnification",
            "severity": "high",
            "category": "indemnification",
        }
    ],
    "payment_terms": [
        {
            "patterns": [
                r"payment\s+(?:shall\s+be\s+)?due\s+(?:within\s+)?(\d+\s*days?)",
                r"net\s+(\d+)",
                r"payable\s+(?:within\s+)?(\d+\s*days?)",
            ],
            "field": "payment_terms",
            "severity": "medium",
            "category": "payment_terms",
        }
    ],
    "termination": [
        {
            "patterns": [
                r"(?:termination|notice)\s+(?:period|shall\s+be)\s+(?:of\s+)?(\d+\s*days?)",
                r"(?:either\s+)?party\s+may\s+terminate\s+(?:this\s+)?agreement\s+(?:upon|with)\s+(\d+\s*(?:days'?|days\s+)?(?:\s*notice)?)",
            ],
            "field": "termination_notice",
            "severity": "medium",
            "category": "termination",
        }
    ],
}


class ConflictDetector:
    """Detects conflicts between related contracts.

    Compares clause-level details across contracts in a relationship
    hierarchy to find contradictions and inconsistencies.
    """

    def __init__(self, repo) -> None:
        """Initialize the detector.

        Args:
            repo: DatabaseRepository instance for data access.
        """
        self._repo = repo

    async def detect_conflicts(
        self, contract_id: str
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between a contract and its related contracts.

        Args:
            contract_id: The contract to check for conflicts.

        Returns:
            List of conflict dicts.
        """
        contract = await self._repo.get_contract(contract_id)
        if contract is None:
            return []

        # Get all relationships
        all_rels = await self._repo.list_all_relationships()
        from models.relationship_graph import ContractRelationship, RelationshipGraph

        relationships = [
            ContractRelationship.from_dict(rel) for rel in all_rels
        ]
        graph = RelationshipGraph(relationships)

        # Get all related contracts (ancestors and descendants)
        related = graph.get_all_related(contract_id)

        all_conflicts: List[Dict[str, Any]] = []
        processed_pairs: Set[Tuple[str, str]] = set()

        for related_id, rel_type, direction in related:
            pair = tuple(sorted([contract_id, related_id]))
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)

            related_contract = await self._repo.get_contract(related_id)
            if related_contract is None:
                continue

            conflicts = await self._compare_contracts(
                contract_a=contract,
                contract_b=related_contract,
                relationship_type=rel_type.value,
            )
            all_conflicts.extend(conflicts)

        return all_conflicts

    async def _compare_contracts(
        self,
        contract_a: Dict[str, Any],
        contract_b: Dict[str, Any],
        relationship_type: str,
    ) -> List[Dict[str, Any]]:
        """Compare two contracts for conflicts.

        Args:
            contract_a: First contract data.
            contract_b: Second contract data.
            relationship_type: Type of relationship between them.

        Returns:
            List of conflict dicts.
        """
        import uuid

        conflicts: List[Dict[str, Any]] = []
        text_a = contract_a.get("metadata", {}).get("extracted_text", "")
        text_b = contract_b.get("metadata", {}).get("extracted_text", "")

        # If we don't have full text, use contract metadata for comparison
        meta_a = contract_a.get("metadata", {})
        if isinstance(meta_a, str):
            try:
                meta_a = json.loads(meta_a)
            except (json.JSONDecodeError, TypeError):
                meta_a = {}

        meta_b = contract_b.get("metadata", {})
        if isinstance(meta_b, str):
            try:
                meta_b = json.loads(meta_b)
            except (json.JSONDecodeError, TypeError):
                meta_b = {}

        # Compare contract types
        type_a = contract_a.get("contract_type", "")
        type_b = contract_b.get("contract_type", "")

        # Compare metadata fields if available
        for field in ["governing_law", "jurisdiction", "effective_date"]:
            val_a = meta_a.get(field)
            val_b = meta_b.get(field)
            if val_a and val_b and val_a != val_b:
                severity = "critical" if field in ("governing_law", "jurisdiction") else "medium"
                conflicts.append(Conflict(
                    conflict_id=str(uuid.uuid4()),
                    contract_id_a=contract_a["contract_id"],
                    contract_id_b=contract_b["contract_id"],
                    relationship_type=relationship_type,
                    category="compliance" if field in ("governing_law", "jurisdiction") else "general",
                    field=field,
                    value_a=str(val_a),
                    value_b=str(val_b),
                    severity=severity,
                    description=f"Different {field.replace('_', ' ')}: '{val_a}' vs '{val_b}'",
                    recommendation=f"Ensure consistent {field.replace('_', ' ')} across related contracts",
                ).to_dict())

        # Pattern-based comparison on extracted text
        if text_a and text_b:
            for category, patterns in CONFLICT_PATTERNS.items():
                for pattern_def in patterns:
                    values_a = self._extract_values(text_a, pattern_def["patterns"])
                    values_b = self._extract_values(text_b, pattern_def["patterns"])

                    if values_a and values_b:
                        best_a = values_a[0]
                        best_b = values_b[0]

                        if best_a.lower() != best_b.lower():
                            conflicts.append(Conflict(
                                conflict_id=str(uuid.uuid4()),
                                contract_id_a=contract_a["contract_id"],
                                contract_id_b=contract_b["contract_id"],
                                relationship_type=relationship_type,
                                category=pattern_def["category"],
                                field=pattern_def["field"],
                                value_a=best_a,
                                value_b=best_b,
                                severity=pattern_def["severity"],
                                description=(
                                    f"Conflict in {pattern_def['field'].replace('_', ' ')}: "
                                    f"'{best_a}' in {contract_a.get('filename', 'unknown')} "
                                    f"vs '{best_b}' in {contract_b.get('filename', 'unknown')}"
                                ),
                                recommendation=self._get_recommendation(pattern_def["field"]),
                            ).to_dict())

        return conflicts

    def _extract_values(self, text: str, patterns: List[str]) -> List[str]:
        """Extract values from text using regex patterns.

        Args:
            text: The text to search.
            patterns: List of regex patterns.

        Returns:
            List of extracted values.
        """
        values = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            values.extend(m.strip() for m in matches if m.strip())
        return values

    def _get_recommendation(self, field: str) -> str:
        """Get a recommendation for resolving a conflict.

        Args:
            field: The conflicting field name.

        Returns:
            Recommendation string.
        """
        recommendations = {
            "governing_law": (
                "Standardize governing law across all related contracts. "
                "Child agreements should reference the parent MSA's governing law."
            ),
            "jurisdiction": (
                "Ensure jurisdiction clauses are consistent. Disputes should "
                "be handled in the same venue for related contracts."
            ),
            "liability_cap": (
                "Verify liability caps are consistent. Child SOWs should not "
                "have higher liability caps than the parent MSA."
            ),
            "confidentiality_term": (
                "Confidentiality terms should be consistent. Child agreements "
                "should not have shorter confidentiality periods than the parent."
            ),
            "indemnification": (
                "Indemnification obligations should align across contracts. "
                "Verify no contradictory indemnification provisions."
            ),
            "payment_terms": (
                "Payment terms should be consistent. Verify net payment "
                "periods align across related contracts."
            ),
            "termination_notice": (
                "Termination notice periods should be consistent. Child "
                "agreements should reference parent termination provisions."
            ),
        }
        return recommendations.get(field, "Review and align conflicting terms across related contracts.")
