"""Playbook engine: rule builder, versioning, and template library.

Provides the core playbook functionality for defining company-specific
risk rules, clause language requirements, and approval thresholds.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RuleCondition(str, Enum):
    """Supported rule conditions for playbook rules."""

    CONTAINS = "contains"
    EQUALS = "equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    REGEX_MATCH = "regex_match"
    NOT_CONTAINS = "not_contains"


class RuleAction(str, Enum):
    """Actions a playbook rule can take."""

    SET_SEVERITY = "set_severity"
    FLAG_WITH_LABEL = "flag_with_label"
    SUGGEST_LANGUAGE = "suggest_language"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


@dataclass
class PlaybookRule:
    """A single IF/THEN rule in a playbook."""

    rule_id: str = ""
    clause_type: str = ""
    condition: RuleCondition = RuleCondition.CONTAINS
    value: str = ""
    action: RuleAction = RuleAction.SET_SEVERITY
    action_value: str = ""
    priority: int = 0
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.rule_id:
            self.rule_id = str(uuid.uuid4())


@dataclass
class PlaybookVersion:
    """A versioned snapshot of a playbook."""

    version_id: str = ""
    version_number: int = 1
    rules: List[PlaybookRule] = field(default_factory=list)
    created_by: str = ""
    created_at: str = ""
    status: str = "draft"  # draft, in_review, approved, active, archived
    change_summary: str = ""
    approved_by: str = ""
    approved_at: str = ""


@dataclass
class Playbook:
    """A complete playbook with rules and version history."""

    playbook_id: str = ""
    name: str = ""
    description: str = ""
    contract_types: List[str] = field(default_factory=list)
    tenant_id: str = ""
    is_active: bool = False
    versions: List[PlaybookVersion] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class PlaybookEngine:
    """Playbook rule engine for evaluating contract clauses.

    Usage:
        engine = PlaybookEngine()
        engine.add_rule(playbook_id, rule)
        results = engine.evaluate(playbook_id, clause_text, clause_type)
    """

    def __init__(self) -> None:
        """Initialize the playbook engine."""
        self._playbooks: Dict[str, Playbook] = {}

    def create_playbook(
        self,
        name: str,
        description: str = "",
        contract_types: Optional[List[str]] = None,
        tenant_id: str = "default",
    ) -> Playbook:
        """Create a new playbook.

        Args:
            name: Playbook name.
            description: Optional description.
            contract_types: Contract types this applies to.
            tenant_id: Tenant identifier.

        Returns:
            The created Playbook.
        """
        now = datetime.utcnow().isoformat() + "Z"
        playbook = Playbook(
            playbook_id=str(uuid.uuid4()),
            name=name,
            description=description,
            contract_types=contract_types or [],
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
        self._playbooks[playbook.playbook_id] = playbook
        return playbook

    def add_rule(
        self,
        playbook_id: str,
        clause_type: str,
        condition: RuleCondition,
        value: str,
        action: RuleAction,
        action_value: str,
        priority: int = 0,
    ) -> Optional[PlaybookRule]:
        """Add a rule to a playbook.

        Args:
            playbook_id: Target playbook.
            clause_type: Clause type this rule applies to.
            condition: Rule condition.
            value: Value to compare against.
            action: Action to take.
            action_value: Action parameter.
            priority: Rule priority (higher = evaluated first).

        Returns:
            The created rule or None if playbook not found.
        """
        playbook = self._playbooks.get(playbook_id)
        if not playbook:
            return None

        rule = PlaybookRule(
            clause_type=clause_type,
            condition=condition,
            value=value,
            action=action,
            action_value=action_value,
            priority=priority,
        )

        playbook.versions.append(PlaybookVersion(
            rules=playbook.versions[-1].rules + [rule] if playbook.versions else [rule],
            version_number=len(playbook.versions) + 1,
        ))

        return rule

    def evaluate(
        self,
        playbook_id: str,
        clause_text: str,
        clause_type: str,
    ) -> List[Dict[str, Any]]:
        """Evaluate a clause against a playbook's rules.

        Args:
            playbook_id: The playbook to evaluate against.
            clause_text: The clause text to evaluate.
            clause_type: The type of clause.

        Returns:
            List of triggered rule results.
        """
        import re

        playbook = self._playbooks.get(playbook_id)
        if not playbook or not playbook.versions:
            return []

        active_version = playbook.versions[-1]
        if active_version.status not in ("approved", "active"):
            return []

        results = []
        for rule in sorted(active_version.rules, key=lambda r: -r.priority):
            if rule.clause_type != clause_type or not rule.enabled:
                continue

            matched = False
            if rule.condition == RuleCondition.CONTAINS:
                matched = rule.value.lower() in clause_text.lower()
            elif rule.condition == RuleCondition.EQUALS:
                matched = clause_text.strip().lower() == rule.value.lower()
            elif rule.condition == RuleCondition.REGEX_MATCH:
                matched = bool(re.search(rule.value, clause_text, re.IGNORECASE))
            elif rule.condition == RuleCondition.NOT_CONTAINS:
                matched = rule.value.lower() not in clause_text.lower()

            if matched:
                results.append({
                    "rule_id": rule.rule_id,
                    "action": rule.action.value,
                    "action_value": rule.action_value,
                    "clause_type": rule.clause_type,
                })

        return results

    def get_playbook(self, playbook_id: str) -> Optional[Playbook]:
        """Get a playbook by ID.

        Args:
            playbook_id: Playbook identifier.

        Returns:
            Playbook or None.
        """
        return self._playbooks.get(playbook_id)

    def list_playbooks(self, tenant_id: str = "") -> List[Playbook]:
        """List all playbooks, optionally filtered by tenant.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            List of playbooks.
        """
        if tenant_id:
            return [p for p in self._playbooks.values() if p.tenant_id == tenant_id]
        return list(self._playbooks.values())
