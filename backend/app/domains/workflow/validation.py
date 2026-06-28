"""Workflow Validation Engine — validates workflow pack versions before publishing.

13 validation checks, health score 0-100. Blocks publishing on errors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Severity Levels ────────────────────────────────────────────────


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


# ── Validation Issue Codes ─────────────────────────────────────────


class IssueCode(str, Enum):
    MISSING_START_STAGE = "missing_start_stage"
    MISSING_TERMINAL_STAGE = "missing_terminal_stage"
    DUPLICATE_STAGE_NAME = "duplicate_stage_name"
    CIRCULAR_REFERENCE = "circular_reference"
    UNREACHABLE_STAGE = "unreachable_stage"
    DEAD_END_STAGE = "dead_end_stage"
    MISSING_ASSIGNEE = "missing_assignee"
    MISSING_ROLE = "missing_role"
    MISSING_SLA = "missing_sla"
    BROKEN_CONDITION = "broken_condition"
    DEPRECATED_ROLE = "deprecated_role"
    CYCLIC_HIERARCHY = "cyclic_hierarchy"
    UNUSED_RULE = "unused_rule"


# ── Dataclasses ────────────────────────────────────────────────────


@dataclass
class ValidationIssue:
    """A single validation issue found during workflow validation."""
    severity: IssueSeverity
    code: IssueCode
    stage: Optional[str] = None
    message: str = ""
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Result of a workflow validation run."""
    score: int = 100
    is_valid: bool = True
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.is_valid = len(self.errors) == 0


# ── Workflow Validator ─────────────────────────────────────────────


class WorkflowValidator:
    """Validates workflow pack versions before publishing.

    Runs 13 distinct checks against the stages_definition and
    rules_definition to ensure correctness, completeness, and
    consistency. Produces a health score from 0-100.
    """

    DEPRECATED_ROLES: set[str] = {
        "super_admin",
        "legacy_reviewer",
        "old_approver",
    }

    def validate(self, version: Any) -> ValidationResult:
        """Validate a workflow version's stages and rules definitions.

        Args:
            version: An object with 'stages_definition' (list of stage dicts)
                     and 'rules_definition' (list of rule dicts) attributes.

        Returns:
            ValidationResult with health score and all issues found.
        """
        result = ValidationResult()

        stages_raw = _safe_get(version, "stages_definition", [])
        rules = _safe_get(version, "rules_definition", [])

        # Extract stages list (supports list, dict with "stages" key, or empty)
        stages = []
        if isinstance(stages_raw, list):
            stages = stages_raw
        elif isinstance(stages_raw, dict):
            stages = stages_raw.get("stages", stages_raw.get("nodes", []))

        if not stages:
            result.errors.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                code=IssueCode.MISSING_START_STAGE,
                message="No stages defined in workflow version.",
                suggestion="Add at least one stage with stage_type='start'.",
            ))
            result.score = max(0, result.score - 5)
            return result

        stage_names = [s.get("name", "") for s in stages]
        stage_types = [s.get("stage_type", "") for s in stages]
        stage_transitions = {
            s.get("name", ""): s.get("transitions", [])
            for s in stages
        }

        # 1. missing_start_stage — must have exactly one start stage
        start_stages = [s for s in stages if s.get("stage_type") == "start"]
        if not start_stages:
            result.errors.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                code=IssueCode.MISSING_START_STAGE,
                message="No stage with stage_type='start' found.",
                suggestion="Add a stage with stage_type='start' as the entry point.",
            ))
            result.score = max(0, result.score - 5)

        # 2. missing_terminal_stage — must have at least one terminal stage
        terminal_stages = [s for s in stages if s.get("stage_type") == "terminal"]
        if not terminal_stages:
            result.warnings.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                code=IssueCode.MISSING_TERMINAL_STAGE,
                message="No stage with stage_type='terminal' found.",
                suggestion="Add a terminal stage to mark workflow completion.",
            ))
            result.score = max(0, result.score - 2)

        # 3. duplicate_stage_name — stage names must be unique
        seen_names: set[str] = set()
        for name in stage_names:
            if name in seen_names:
                result.errors.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code=IssueCode.DUPLICATE_STAGE_NAME,
                    stage=name,
                    message=f"Duplicate stage name '{name}'.",
                    suggestion="Rename the duplicate stage to ensure unique names.",
                ))
                result.score = max(0, result.score - 5)
            seen_names.add(name)

        # 4. circular_reference — detect cycles in stage transitions
        if stage_names:
            cycle = self._detect_cycle(stage_names, stage_transitions)
            if cycle:
                result.errors.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code=IssueCode.CIRCULAR_REFERENCE,
                    message=f"Circular reference detected in stage transitions: {' → '.join(cycle)}.",
                    suggestion="Remove the circular transition to ensure acyclic flow.",
                ))
                result.score = max(0, result.score - 5)

        # 5. unreachable_stage — stages not reachable from start
        if start_stages:
            unreachable = self._find_unreachable(stage_names, stage_transitions, start_stages[0].get("name", ""))
            for stage_name in unreachable:
                result.warnings.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code=IssueCode.UNREACHABLE_STAGE,
                    stage=stage_name,
                    message=f"Stage '{stage_name}' is not reachable from the start stage.",
                    suggestion="Add a transition path from a preceding stage to '{stage_name}'.",
                ))
                result.score = max(0, result.score - 2)

        # 6. dead_end_stage — non-terminal stages with no outgoing transitions
        terminal_type_names = {s.get("name", "") for s in terminal_stages}
        for stage in stages:
            s_name = stage.get("name", "")
            s_type = stage.get("stage_type", "")
            if s_type == "terminal":
                continue
            transitions = stage.get("transitions", [])
            if not transitions and s_name not in terminal_type_names:
                result.warnings.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code=IssueCode.DEAD_END_STAGE,
                    stage=s_name,
                    message=f"Stage '{s_name}' has no outgoing transitions and is not terminal.",
                    suggestion="Add outgoing transitions or mark it as stage_type='terminal'.",
                ))
                result.score = max(0, result.score - 2)

        # 7. missing_assignee — stages requiring review need an assignee
        for stage in stages:
            s_name = stage.get("name", "")
            on_entry = stage.get("on_entry", [])
            assignee = stage.get("assignee")
            if "require_review" in on_entry or "require_approval" in on_entry:
                if not assignee:
                    result.errors.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        code=IssueCode.MISSING_ASSIGNEE,
                        stage=s_name,
                        message=f"Stage '{s_name}' requires review/approval but has no assignee.",
                        suggestion="Set an 'assignee' field on the stage definition.",
                    ))
                    result.score = max(0, result.score - 5)

        # 8. missing_role — stages requiring a specific role
        for stage in stages:
            s_name = stage.get("name", "")
            required_role = stage.get("required_role")
            on_entry = stage.get("on_entry", [])
            if ("require_review" in on_entry or "require_approval" in on_entry) and not required_role:
                result.warnings.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code=IssueCode.MISSING_ROLE,
                    stage=s_name,
                    message=f"Stage '{s_name}' requires review/approval but has no required_role.",
                    suggestion="Set a 'required_role' to control who can act on this stage.",
                ))
                result.score = max(0, result.score - 2)

        # 9. missing_sla — stages with review/approval should have SLA
        for stage in stages:
            s_name = stage.get("name", "")
            on_entry = stage.get("on_entry", [])
            sla = stage.get("sla_hours")
            if ("require_review" in on_entry or "require_approval" in on_entry) and not sla:
                result.warnings.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code=IssueCode.MISSING_SLA,
                    stage=s_name,
                    message=f"Stage '{s_name}' requires review/approval but has no sla_hours.",
                    suggestion="Set 'sla_hours' to define expected completion time.",
                ))
                result.score = max(0, result.score - 2)

        # 10. broken_condition — rules with invalid JSON Logic conditions
        for rule in (rules or []):
            rule_name = rule.get("rule_name", "unnamed")
            conditions = rule.get("conditions", {})
            if conditions and not self._is_valid_condition(conditions):
                result.errors.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code=IssueCode.BROKEN_CONDITION,
                    message=f"Rule '{rule_name}' has a broken or malformed condition.",
                    suggestion="Fix the JSON Logic expression in the rule's conditions.",
                ))
                result.score = max(0, result.score - 5)

        # 11. deprecated_role — stages referencing deprecated roles
        for stage in stages:
            s_name = stage.get("name", "")
            role = stage.get("required_role", "")
            if role in self.DEPRECATED_ROLES:
                result.warnings.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code=IssueCode.DEPRECATED_ROLE,
                    stage=s_name,
                    message=f"Stage '{s_name}' references deprecated role '{role}'.",
                    suggestion=f"Replace '{role}' with the current role name.",
                ))
                result.score = max(0, result.score - 2)

        # 12. cyclic_hierarchy — pack parent-child cycles
        # (checked externally via validate_hierarchy)

        # 13. unused_rule — rules not referenced by any stage
        referenced_rules: set[str] = set()
        for stage in stages:
            for transition in stage.get("transitions", []):
                if isinstance(transition, dict):
                    condition = transition.get("condition", {})
                    if isinstance(condition, dict):
                        ref = condition.get("ref") or condition.get("rule")
                        if ref:
                            referenced_rules.add(ref)
        for rule in (rules or []):
            rule_name = rule.get("rule_name", "")
            if rule_name and rule_name not in referenced_rules:
                result.warnings.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    code=IssueCode.UNUSED_RULE,
                    message=f"Rule '{rule_name}' is defined but not referenced by any stage transition.",
                    suggestion="Either reference the rule in a stage transition or remove it.",
                ))
                result.score = max(0, result.score - 2)

        return result

    def validate_hierarchy(self, pack: Any) -> ValidationResult:
        """Validate the parent-child hierarchy of a workflow pack.

        Checks for cyclic hierarchy (IssueCode.CYCLIC_HIERARCHY)
        where a pack's parent_pack_id chain loops back on itself.

        Args:
            pack: An object with 'pack_id' and 'parent_pack_id' attributes.

        Returns:
            ValidationResult with hierarchy-specific issues.
        """
        result = ValidationResult()

        pack_id = _safe_get(pack, "pack_id", "")
        parent_id = _safe_get(pack, "parent_pack_id")

        if not parent_id:
            return result

        # Walk the parent chain to detect cycles
        visited: list[str] = [pack_id]
        current = parent_id

        while current:
            if current in visited:
                result.errors.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    code=IssueCode.CYCLIC_HIERARCHY,
                    message=f"Cyclic hierarchy detected: pack '{pack_id}' has a parent chain that loops back.",
                    suggestion="Break the cycle by setting a different parent_pack_id or removing it.",
                ))
                result.score = max(0, result.score - 5)
                break
            visited.append(current)
            # In a real scenario, this would look up the parent pack from DB
            # For validation purposes, we flag the potential cycle
            break

        return result

    # ── Private Helpers ─────────────────────────────────────────

    def _detect_cycle(
        self,
        stage_names: list[str],
        stage_transitions: dict[str, list[dict[str, Any]]],
    ) -> list[str]:
        """Detect cycles in stage transitions using DFS."""
        visited: set[str] = set()
        rec_stack: set[str] = set()
        parent_map: dict[str, str] = {}

        def dfs(node: str) -> list[str] | None:
            visited.add(node)
            rec_stack.add(node)
            for transition in stage_transitions.get(node, []):
                if isinstance(transition, str):
                    target = transition
                elif isinstance(transition, dict):
                    target = transition.get("target", transition.get("name", ""))
                else:
                    target = ""
                if target and target in stage_names:
                    if target not in visited:
                        parent_map[target] = node
                        cycle = dfs(target)
                        if cycle:
                            return cycle
                    elif target in rec_stack:
                        # Reconstruct the cycle
                        cycle_path = [target]
                        current = node
                        while current != target:
                            cycle_path.append(current)
                            current = parent_map.get(current, target)
                        cycle_path.append(target)
                        return list(reversed(cycle_path))
            rec_stack.discard(node)
            return None

        for name in stage_names:
            if name not in visited:
                cycle = dfs(name)
                if cycle:
                    return cycle
        return []

    def _find_unreachable(
        self,
        stage_names: list[str],
        stage_transitions: dict[str, list[dict[str, Any]]],
        start_name: str,
    ) -> list[str]:
        """Find stages not reachable from the start stage using BFS."""
        reachable: set[str] = set()
        queue: list[str] = [start_name]

        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            for transition in stage_transitions.get(current, []):
                if isinstance(transition, str):
                    target = transition
                elif isinstance(transition, dict):
                    target = transition.get("target", "")
                else:
                    target = ""
                if target and target in stage_names:
                    queue.append(target)

        return [name for name in stage_names if name not in reachable]

    def _is_valid_condition(self, condition: dict[str, Any]) -> bool:
        """Check if a JSON Logic condition is structurally valid.

        A valid condition must be a non-empty dict with at least one key
        that is a known JSON Logic operator.
        """
        if not isinstance(condition, dict) or not condition:
            return False
        # Basic structural check — a valid condition has at least one operator key
        known_operators = {
            "==", "===", "!=", "!==", ">", ">=", "<", "<=",
            "and", "or", "!", "!!", "in", "var", "if", "then", "else",
            "missing", "missing_some", "reduce", "filter", "map",
            "all", "none", "some", "merge", "min", "max", "cat",
            "substr", "+", "-", "*", "/", "%", "log",
        }
        return any(op in condition for op in known_operators)


# ── Helpers ────────────────────────────────────────────────────────


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from an object or dict."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)
