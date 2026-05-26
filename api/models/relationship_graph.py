"""Contract relationship graph schema and traversal logic.

Provides data structures for representing contract relationship
hierarchies (parent/child/amendment/addendum/DPA) and algorithms
for traversing the contract graph.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RelationshipType(str, Enum):
    """Types of relationships between contracts."""

    PARENT = "parent"
    CHILD = "child"
    AMENDMENT = "amendment"
    ADDENDUM = "addendum"
    DPA = "dpa"


@dataclass
class ContractRelationship:
    """Represents a relationship between two contracts."""

    relationship_id: str
    parent_contract_id: str
    child_contract_id: str
    relationship_type: RelationshipType
    effective_date: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "relationship_id": self.relationship_id,
            "parent_contract_id": self.parent_contract_id,
            "child_contract_id": self.child_contract_id,
            "relationship_type": self.relationship_type.value,
            "effective_date": self.effective_date,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ContractRelationship:
        """Create from dictionary."""
        return cls(
            relationship_id=data["relationship_id"],
            parent_contract_id=data["parent_contract_id"],
            child_contract_id=data["child_contract_id"],
            relationship_type=RelationshipType(data["relationship_type"]),
            effective_date=data.get("effective_date"),
            notes=data.get("notes"),
            created_at=data.get("created_at"),
        )


@dataclass
class RelationshipNode:
    """A node in the contract relationship tree."""

    contract_id: str
    contract_data: Optional[Dict[str, Any]] = None
    children: List[RelationshipNode] = field(default_factory=list)
    relationship_type: Optional[RelationshipType] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "contract_id": self.contract_id,
            "contract_data": self.contract_data,
            "relationship_type": self.relationship_type.value if self.relationship_type else None,
            "children": [child.to_dict() for child in self.children],
        }


class RelationshipGraph:
    """Traverses and analyzes the contract relationship graph.

    Provides methods for building trees, finding paths, and
    detecting cycles in the contract relationship network.
    """

    def __init__(self, relationships: List[ContractRelationship]) -> None:
        """Initialize the graph with a list of relationships.

        Args:
            relationships: All known contract relationships.
        """
        self._relationships = relationships
        self._parent_map: Dict[str, List[Tuple[str, RelationshipType]]] = {}
        self._child_map: Dict[str, List[Tuple[str, RelationshipType]]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Build parent/child lookup maps for efficient traversal."""
        self._parent_map.clear()
        self._child_map.clear()

        for rel in self._relationships:
            # parent -> children
            if rel.parent_contract_id not in self._child_map:
                self._child_map[rel.parent_contract_id] = []
            self._child_map[rel.parent_contract_id].append(
                (rel.child_contract_id, rel.relationship_type)
            )

            # child -> parents
            if rel.child_contract_id not in self._parent_map:
                self._parent_map[rel.child_contract_id] = []
            self._parent_map[rel.child_contract_id].append(
                (rel.parent_contract_id, rel.relationship_type)
            )

    def get_children(
        self, contract_id: str
    ) -> List[Tuple[str, RelationshipType]]:
        """Get all direct children of a contract.

        Args:
            contract_id: The contract to query.

        Returns:
            List of (child_id, relationship_type) tuples.
        """
        return self._child_map.get(contract_id, [])

    def get_parents(
        self, contract_id: str
    ) -> List[Tuple[str, RelationshipType]]:
        """Get all direct parents of a contract.

        Args:
            contract_id: The contract to query.

        Returns:
            List of (parent_id, relationship_type) tuples.
        """
        return self._parent_map.get(contract_id, [])

    def build_tree(
        self,
        root_id: str,
        contract_map: Optional[Dict[str, Dict[str, Any]]] = None,
        max_depth: int = 10,
    ) -> RelationshipNode:
        """Build a relationship tree rooted at the given contract.

        Uses BFS to traverse the graph up to max_depth.

        Args:
            root_id: The root contract ID.
            contract_map: Optional map of contract_id -> contract data.
            max_depth: Maximum traversal depth.

        Returns:
            Root RelationshipNode with children populated.
        """
        root = RelationshipNode(
            contract_id=root_id,
            contract_data=contract_map.get(root_id) if contract_map else None,
        )

        visited: Set[str] = set()
        queue: List[Tuple[RelationshipNode, int]] = [(root, 0)]

        while queue:
            node, depth = queue.pop(0)
            if node.contract_id in visited or depth >= max_depth:
                continue
            visited.add(node.contract_id)

            children = self.get_children(node.contract_id)
            for child_id, rel_type in children:
                child_node = RelationshipNode(
                    contract_id=child_id,
                    contract_data=contract_map.get(child_id) if contract_map else None,
                    relationship_type=rel_type,
                )
                node.children.append(child_node)
                queue.append((child_node, depth + 1))

        return root

    def find_ancestors(
        self, contract_id: str, max_depth: int = 20
    ) -> List[Tuple[str, RelationshipType]]:
        """Find all ancestors of a contract.

        Args:
            contract_id: The contract to find ancestors for.
            max_depth: Maximum traversal depth.

        Returns:
            List of (ancestor_id, relationship_type) tuples.
        """
        ancestors: List[Tuple[str, RelationshipType]] = []
        visited: Set[str] = set()
        queue: List[Tuple[str, RelationshipType, int]] = [
            (pid, rtype, 0) for pid, rtype in self.get_parents(contract_id)
        ]

        while queue:
            node_id, rel_type, depth = queue.pop(0)
            if node_id in visited or depth >= max_depth:
                continue
            visited.add(node_id)
            ancestors.append((node_id, rel_type))

            for pid, rtype in self.get_parents(node_id):
                queue.append((pid, rtype, depth + 1))

        return ancestors

    def find_descendants(
        self, contract_id: str, max_depth: int = 20
    ) -> List[Tuple[str, RelationshipType]]:
        """Find all descendants of a contract.

        Args:
            contract_id: The contract to find descendants for.
            max_depth: Maximum traversal depth.

        Returns:
            List of (descendant_id, relationship_type) tuples.
        """
        descendants: List[Tuple[str, RelationshipType]] = []
        visited: Set[str] = set()
        queue: List[Tuple[str, RelationshipType, int]] = [
            (cid, rtype, 0) for cid, rtype in self.get_children(contract_id)
        ]

        while queue:
            node_id, rel_type, depth = queue.pop(0)
            if node_id in visited or depth >= max_depth:
                continue
            visited.add(node_id)
            descendants.append((node_id, rel_type))

            for cid, rtype in self.get_children(node_id):
                queue.append((cid, rtype, depth + 1))

        return descendants

    def get_all_related(
        self, contract_id: str, max_depth: int = 20
    ) -> List[Tuple[str, RelationshipType, str]]:
        """Get all contracts related to the given one.

        Returns both ancestors and descendants with direction.

        Args:
            contract_id: The contract to query.
            max_depth: Maximum traversal depth.

        Returns:
            List of (related_id, relationship_type, direction) tuples
            where direction is "up" (ancestor/parent) or "down" (descendant/child).
        """
        related: List[Tuple[str, RelationshipType, str]] = []

        for aid, rtype in self.find_ancestors(contract_id, max_depth):
            related.append((aid, rtype, "up"))

        for did, rtype in self.find_descendants(contract_id, max_depth):
            related.append((did, rtype, "down"))

        return related

    def detect_cycles(self) -> List[List[str]]:
        """Detect cycles in the relationship graph.

        Uses DFS to find all cycles.

        Returns:
            List of cycles, where each cycle is a list of contract IDs.
        """
        all_nodes: Set[str] = set()
        for rel in self._relationships:
            all_nodes.add(rel.parent_contract_id)
            all_nodes.add(rel.child_contract_id)

        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for child_id, _ in self.get_children(node):
                if child_id not in visited:
                    dfs(child_id)
                elif child_id in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(child_id)
                    cycles.append(path[cycle_start:] + [child_id])

            path.pop()
            rec_stack.discard(node)

        for node in all_nodes:
            if node not in visited:
                dfs(node)

        return cycles
