"""Build hierarchical clause structures from flat clause lists.

Constructs parent-child relationships between clauses based on
section numbering (e.g., 2.3.1 is a child of 2.3), heading levels,
and document structure. Enables tree-based navigation of contract
clauses.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ClauseHierarchyError(Exception):
    """Raised when hierarchy construction fails."""


class ClauseHierarchyBuilder:
    """Builds hierarchical clause structures from flat clause lists.

    Analyzes section numbers and heading levels to establish
    parent-child relationships between clauses, producing a
    tree structure suitable for navigation and analysis.

    Attributes:
        section_pattern: Regex for matching section numbers.
    """

    SECTION_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)$")
    ROMAN_PATTERN = re.compile(r"^([IVXLCDM]+)$")

    def __init__(self) -> None:
        """Initialize the hierarchy builder."""
        self._id_counter: int = 0

    def build_hierarchy(
        self,
        clauses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build a clause hierarchy from a flat list of clauses.

        Assigns parent-child relationships based on section numbering
        and heading levels. Modifies clauses in place and returns them
        with updated parent/child references.

        Args:
            clauses: List of clause dicts from ClauseSegmenter.

        Returns:
            The same clause list with parent_clause_id and
            child_clause_ids populated.

        Raises:
            ClauseHierarchyError: If hierarchy construction fails.
        """
        if not clauses:
            return []

        try:
            # Assign section-based hierarchy
            clauses = self._assign_section_hierarchy(clauses)

            # Assign heading-level hierarchy as fallback
            clauses = self._assign_level_hierarchy(clauses)

            # Validate the hierarchy
            self._validate_hierarchy(clauses)

            logger.info(
                "Built clause hierarchy: %d clauses, %d top-level",
                len(clauses),
                sum(1 for c in clauses if c.get("parent_clause_id") is None),
            )
            return clauses

        except Exception as exc:
            raise ClauseHierarchyError(
                f"Failed to build clause hierarchy: {exc}"
            ) from exc

    def _assign_section_hierarchy(
        self,
        clauses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Assign parent-child relationships based on section numbers.

        Uses dotted section notation (e.g., 2.3.1 → parent 2.3)
        to establish hierarchy.

        Args:
            clauses: List of clause dicts.

        Returns:
            Updated clause list with parent/child references.
        """
        # Index clauses by section number
        section_map: Dict[str, Dict[str, Any]] = {}
        for clause in clauses:
            section_num = clause.get("section_number")
            if section_num and self.SECTION_PATTERN.match(section_num):
                section_map[section_num] = clause

        # Assign parent-child relationships
        for clause in clauses:
            section_num = clause.get("section_number")
            if not section_num:
                continue

            parent_section = self._get_parent_section(section_num)
            if parent_section and parent_section in section_map:
                parent = section_map[parent_section]
                clause["parent_clause_id"] = parent.get("clause_id")
                if "child_clause_ids" not in parent:
                    parent["child_clause_ids"] = []
                if clause["clause_id"] not in parent["child_clause_ids"]:
                    parent["child_clause_ids"].append(clause["clause_id"])

        return clauses

    def _get_parent_section(self, section_number: str) -> Optional[str]:
        """Compute the parent section number.

        For "2.3.1", returns "2.3". For "2.3", returns "2". For "2", returns None.

        Args:
            section_number: The section number string.

        Returns:
            Parent section number, or None if top-level.
        """
        parts = section_number.split(".")
        if len(parts) <= 1:
            return None
        return ".".join(parts[:-1])

    def _assign_level_hierarchy(
        self,
        clauses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Assign hierarchy based on heading levels as fallback.

        For clauses without section numbers, uses the heading level
        to establish parent-child relationships. A clause at level N
        becomes a child of the most recent clause at level N-1.

        Args:
            clauses: List of clause dicts.

        Returns:
            Updated clause list with parent/child references.
        """
        # Only process clauses without parent assignments
        unassigned = [
            c for c in clauses
            if c.get("parent_clause_id") is None
            and c.get("section_number") is None
        ]

        if not unassigned:
            return clauses

        # Track the most recent clause at each level
        level_stack: Dict[int, Optional[str]] = {}

        for clause in clauses:
            clause_id = clause.get("clause_id")
            level = clause.get("level", 1)

            # Update level stack
            level_stack[level] = clause_id
            # Clear deeper levels
            for l in range(level + 1, max(level_stack.keys(), default=level) + 1):
                level_stack.pop(l, None)

            # Assign parent if not already assigned
            if clause.get("parent_clause_id") is None and level > 1:
                parent_level = level - 1
                parent_id = level_stack.get(parent_level)
                if parent_id and parent_id != clause_id:
                    clause["parent_clause_id"] = parent_id
                    # Find parent and add child
                    for c in clauses:
                        if c.get("clause_id") == parent_id:
                            if "child_clause_ids" not in c:
                                c["child_clause_ids"] = []
                            if clause_id not in c["child_clause_ids"]:
                                c["child_clause_ids"].append(clause_id)
                            break

        return clauses

    def _validate_hierarchy(self, clauses: List[Dict[str, Any]]) -> None:
        """Validate the constructed hierarchy for consistency.

        Checks for:
        - Circular references
        - Orphaned children (parent not found)
        - Duplicate relationships

        Args:
            clauses: The clause list to validate.

        Raises:
            ClauseHierarchyError: If validation fails.
        """
        clause_ids: Set[str] = {c.get("clause_id", "") for c in clauses}

        for clause in clauses:
            clause_id = clause.get("clause_id", "")
            parent_id = clause.get("parent_clause_id")

            if parent_id and parent_id not in clause_ids:
                logger.warning(
                    "Clause %s has parent %s which does not exist",
                    clause_id,
                    parent_id,
                )

            # Check for self-reference
            if parent_id == clause_id:
                raise ClauseHierarchyError(
                    f"Clause {clause_id} references itself as parent"
                )

        # Check for circular references
        visited: Set[str] = set()
        for clause in clauses:
            current = clause.get("clause_id", "")
            chain: Set[str] = set()

            while current:
                if current in chain:
                    raise ClauseHierarchyError(
                        f"Circular reference detected involving clause {current}"
                    )
                if current in visited:
                    break
                chain.add(current)
                visited.add(current)

                # Find parent
                parent_id = None
                for c in clauses:
                    if c.get("clause_id") == current:
                        parent_id = c.get("parent_clause_id")
                        break
                current = parent_id

    def to_tree(
        self,
        clauses: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Convert the flat clause list to a nested tree structure.

        Args:
            clauses: List of clause dicts with hierarchy assigned.

        Returns:
            List of root clause nodes, each containing a 'children' list.
        """
        clause_map: Dict[str, Dict[str, Any]] = {}
        for clause in clauses:
            clause_map[clause["clause_id"]] = {
                **clause,
                "children": [],
            }

        roots: List[Dict[str, Any]] = []
        for clause in clauses:
            node = clause_map[clause["clause_id"]]
            parent_id = clause.get("parent_clause_id")

            if parent_id and parent_id in clause_map:
                clause_map[parent_id]["children"].append(node)
            else:
                roots.append(node)

        return roots

    def flatten_tree(
        self,
        tree: List[Dict[str, Any]],
        level: int = 1,
    ) -> List[Dict[str, Any]]:
        """Flatten a clause tree back to a list with depth tracking.

        Args:
            tree: Nested clause tree from to_tree().
            level: Starting depth level.

        Returns:
            Flat list of clause dicts with depth information.
        """
        flat: List[Dict[str, Any]] = []

        for node in tree:
            node_copy = {**node, "depth": level}
            children = node_copy.pop("children", [])
            flat.append(node_copy)
            flat.extend(self.flatten_tree(children, level + 1))

        return flat
