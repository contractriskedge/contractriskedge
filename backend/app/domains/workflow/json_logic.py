"""JSON Logic Rule Engine — evaluates portable JSON Logic expressions.

Follows the JSON Logic standard (https://jsonlogic.com).
Supports all standard operators plus custom contract-specific operations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────


@dataclass
class ExplanationNode:
    """A single node in the rule evaluation explanation tree."""
    operator: str = ""
    result: Any = None
    children: list["ExplanationNode"] = field(default_factory=list)
    summary: str = ""


@dataclass
class RuleReference:
    """Reference to a rule in the business rule catalog."""
    rule_id: str = ""
    name: str = ""
    logic: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    status: str = "active"


@dataclass
class BusinessRuleCatalog:
    """In-memory catalog of business rules for a workflow.

    Not a DB model — a simple dataclass for holding rule references
    during evaluation and simulation.
    """
    rules: list[RuleReference] = field(default_factory=list)
    catalog_name: str = ""
    description: str = ""


# ── JSON Logic Engine ──────────────────────────────────────────────


def json_logic(rule: Any, context: dict[str, Any]) -> Any:
    """Evaluate a JSON Logic rule against a context dictionary.

    This is a pure Python implementation of the JSON Logic standard.
    Supports all standard operators defined at https://jsonlogic.com.

    Args:
        rule: A JSON Logic rule (dict with operator as key) or a literal value.
        context: Dictionary of data to evaluate against.

    Returns:
        The result of the rule evaluation.
    """
    if rule is None:
        return None

    # Literal values — return as-is
    if not isinstance(rule, dict):
        return rule

    # A dict with exactly one key is a JSON Logic operation
    if len(rule) != 1:
        # If it's a dict with multiple keys, treat as a data object
        return rule

    operator = next(iter(rule))
    values = rule[operator]

    # Normalize values to a list for consistent handling
    if not isinstance(values, list):
        values = [values]

    # Dispatch to the appropriate operator handler
    handler = _OPERATORS.get(operator)
    if handler is None:
        logger.warning("Unknown JSON Logic operator: %s", operator)
        return None

    return handler(values, context)


# ── Operator Implementations ───────────────────────────────────────


def _op_equal(values: list, context: dict[str, Any]) -> bool:
    """== : Abstract equality (type-coercing)."""
    a, b = json_logic(values[0], context), json_logic(values[1], context)
    try:
        return a == b
    except (ValueError, TypeError):
        return str(a) == str(b)


def _op_strict_equal(values: list, context: dict[str, Any]) -> bool:
    """=== : Strict equality (no type coercion)."""
    a, b = json_logic(values[0], context), json_logic(values[1], context)
    return a is b if type(a) is type(b) else False


def _op_not_equal(values: list, context: dict[str, Any]) -> bool:
    """!= : Abstract inequality."""
    return not _op_equal(values, context)


def _op_strict_not_equal(values: list, context: dict[str, Any]) -> bool:
    """!== : Strict inequality."""
    return not _op_strict_equal(values, context)


def _op_greater(values: list, context: dict[str, Any]) -> bool:
    """> : Greater than."""
    a, b = json_logic(values[0], context), json_logic(values[1], context)
    try:
        return float(a) > float(b)
    except (ValueError, TypeError):
        return False


def _op_greater_equal(values: list, context: dict[str, Any]) -> bool:
    """>= : Greater than or equal."""
    a, b = json_logic(values[0], context), json_logic(values[1], context)
    try:
        return float(a) >= float(b)
    except (ValueError, TypeError):
        return False


def _op_less(values: list, context: dict[str, Any]) -> bool:
    """< : Less than."""
    a, b = json_logic(values[0], context), json_logic(values[1], context)
    try:
        return float(a) < float(b)
    except (ValueError, TypeError):
        return False


def _op_less_equal(values: list, context: dict[str, Any]) -> bool:
    """<= : Less than or equal."""
    a, b = json_logic(values[0], context), json_logic(values[1], context)
    try:
        return float(a) <= float(b)
    except (ValueError, TypeError):
        return False


def _op_and(values: list, context: dict[str, Any]) -> bool:
    """and : Logical AND — returns first falsy or last truthy value."""
    result = True
    for v in values:
        result = json_logic(v, context)
        if not result:
            return result
    return result


def _op_or(values: list, context: dict[str, Any]) -> bool:
    """or : Logical OR — returns first truthy or last falsy value."""
    for v in values:
        result = json_logic(v, context)
        if result:
            return result
    return result


def _op_not(values: list, context: dict[str, Any]) -> bool:
    """! : Logical NOT."""
    return not json_logic(values[0], context)


def _op_double_not(values: list, context: dict[str, Any]) -> bool:
    """!! : Coerce to boolean."""
    return bool(json_logic(values[0], context))


def _op_in(values: list, context: dict[str, Any]) -> bool:
    """in : Check if a value is in an array or string."""
    a = json_logic(values[0], context)
    b = json_logic(values[1], context)
    if isinstance(b, (list, tuple)):
        return a in b
    if isinstance(b, str) and isinstance(a, str):
        return a in b
    return False


def _op_var(values: list, context: dict[str, Any]) -> Any:
    """var : Retrieve a value from the context by path.

    Supports dot-separated paths (e.g., "contract.risk_score").
    """
    path = json_logic(values[0], context) if isinstance(values[0], dict) else values[0]
    default = json_logic(values[1], context) if len(values) > 1 else None

    if not isinstance(path, str):
        return default

    parts = path.split(".")
    current = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, (list, tuple)) and part.isdigit():
            idx = int(part)
            current = current[idx] if 0 <= idx < len(current) else None
        else:
            return default
        if current is None:
            return default
    return current


def _op_if(values: list, context: dict[str, Any]) -> Any:
    """if : Conditional — pairs of condition/value, with optional else."""
    for i in range(0, len(values) - 1, 2):
        condition = json_logic(values[i], context)
        if condition:
            return json_logic(values[i + 1], context)
    if len(values) % 2 == 1:
        return json_logic(values[-1], context)
    return None


def _op_missing(values: list, context: dict[str, Any]) -> list[str]:
    """missing : Return array of keys not present in context."""
    keys = []
    for v in values:
        key = json_logic(v, context) if isinstance(v, dict) else v
        if isinstance(key, str):
            parts = key.split(".")
            current = context
            found = True
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    found = False
                    break
            if not found:
                keys.append(key)
    return keys


def _op_missing_some(values: list, context: dict[str, Any]) -> list[str]:
    """missing_some : Return missing keys if more than allowed are missing."""
    if len(values) < 2:
        return []
    required_count = json_logic(values[0], context)
    keys_to_check = json_logic(values[1], context) if isinstance(values[1], (list, dict)) else values[1]
    if not isinstance(keys_to_check, list):
        return []
    missing_keys = [k for k in keys_to_check if k not in context]
    if len(missing_keys) > required_count:
        return missing_keys
    return []


def _op_reduce(values: list, context: dict[str, Any]) -> Any:
    """reduce : Fold over an array with an accumulator."""
    if len(values) < 3:
        return None
    arr = json_logic(values[0], context)
    rule = values[1]
    initial = json_logic(values[2], context)
    if not isinstance(arr, list):
        return initial
    accumulator = initial
    for item in arr:
        local_context = {**context, "current": item, "accumulator": accumulator}
        accumulator = json_logic(rule, local_context)
    return accumulator


def _op_filter(values: list, context: dict[str, Any]) -> list:
    """filter : Filter an array using a rule."""
    if len(values) < 2:
        return []
    arr = json_logic(values[0], context)
    rule = values[1]
    if not isinstance(arr, list):
        return []
    result = []
    for item in arr:
        local_context = {**context, "current": item}
        if json_logic(rule, local_context):
            result.append(item)
    return result


def _op_map(values: list, context: dict[str, Any]) -> list:
    """map : Transform each element of an array."""
    if len(values) < 2:
        return []
    arr = json_logic(values[0], context)
    rule = values[1]
    if not isinstance(arr, list):
        return []
    result = []
    for item in arr:
        local_context = {**context, "current": item}
        result.append(json_logic(rule, local_context))
    return result


def _op_all(values: list, context: dict[str, Any]) -> bool:
    """all : Check if all elements satisfy a rule."""
    if len(values) < 2:
        return False
    arr = json_logic(values[0], context)
    rule = values[1]
    if not isinstance(arr, list):
        return False
    for item in arr:
        local_context = {**context, "current": item}
        if not json_logic(rule, local_context):
            return False
    return True


def _op_none(values: list, context: dict[str, Any]) -> bool:
    """none : Check if no elements satisfy a rule."""
    if len(values) < 2:
        return True
    arr = json_logic(values[0], context)
    rule = values[1]
    if not isinstance(arr, list):
        return True
    for item in arr:
        local_context = {**context, "current": item}
        if json_logic(rule, local_context):
            return False
    return True


def _op_some(values: list, context: dict[str, Any]) -> bool:
    """some : Check if at least one element satisfies a rule."""
    if len(values) < 2:
        return False
    arr = json_logic(values[0], context)
    rule = values[1]
    if not isinstance(arr, list):
        return False
    for item in arr:
        local_context = {**context, "current": item}
        if json_logic(rule, local_context):
            return True
    return False


def _op_merge(values: list, context: dict[str, Any]) -> list:
    """merge : Merge multiple arrays into one."""
    result: list = []
    for v in values:
        item = json_logic(v, context)
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result


def _op_min(values: list, context: dict[str, Any]) -> float | int:
    """min : Minimum value from an array or arguments."""
    nums = _collect_numbers(values, context)
    return min(nums) if nums else 0


def _op_max(values: list, context: dict[str, Any]) -> float | int:
    """max : Maximum value from an array or arguments."""
    nums = _collect_numbers(values, context)
    return max(nums) if nums else 0


def _op_cat(values: list, context: dict[str, Any]) -> str:
    """cat : Concatenate strings."""
    parts = []
    for v in values:
        item = json_logic(v, context)
        if item is not None:
            parts.append(str(item))
    return "".join(parts)


def _op_substr(values: list, context: dict[str, Any]) -> str:
    """substr : Extract a substring."""
    if len(values) < 2:
        return ""
    string = str(json_logic(values[0], context))
    start = int(json_logic(values[1], context))
    length = int(json_logic(values[2], context)) if len(values) > 2 else len(string)
    return string[start:start + length]


def _op_add(values: list, context: dict[str, Any]) -> float | int:
    """+ : Addition."""
    nums = _collect_numbers(values, context)
    return sum(nums) if nums else 0


def _op_subtract(values: list, context: dict[str, Any]) -> float | int:
    """- : Subtraction."""
    nums = _collect_numbers(values, context)
    if not nums:
        return 0
    result = nums[0]
    for n in nums[1:]:
        result -= n
    return result


def _op_multiply(values: list, context: dict[str, Any]) -> float | int:
    """* : Multiplication."""
    nums = _collect_numbers(values, context)
    if not nums:
        return 0
    result = nums[0]
    for n in nums[1:]:
        result *= n
    return result


def _op_divide(values: list, context: dict[str, Any]) -> float | int:
    """/ : Division."""
    nums = _collect_numbers(values, context)
    if len(nums) < 2:
        return 0
    result = float(nums[0])
    for n in nums[1:]:
        if n == 0:
            return float("inf")
        result /= float(n)
    return result


def _op_modulo(values: list, context: dict[str, Any]) -> int:
    """% : Modulo."""
    nums = _collect_numbers(values, context)
    if len(nums) < 2:
        return 0
    return int(nums[0]) % int(nums[1])


def _op_log(values: list, context: dict[str, Any]) -> Any:
    """log : Log a value and return it (for debugging)."""
    result = json_logic(values[0], context)
    logger.debug("JSON Logic log: %s = %s", values[0], result)
    return result


# ── Operator Registry ──────────────────────────────────────────────


_OPERATORS: dict[str, Any] = {
    "==": _op_equal,
    "===": _op_strict_equal,
    "!=": _op_not_equal,
    "!==": _op_strict_not_equal,
    ">": _op_greater,
    ">=": _op_greater_equal,
    "<": _op_less,
    "<=": _op_less_equal,
    "and": _op_and,
    "or": _op_or,
    "!": _op_not,
    "!!": _op_double_not,
    "in": _op_in,
    "var": _op_var,
    "if": _op_if,
    "missing": _op_missing,
    "missing_some": _op_missing_some,
    "reduce": _op_reduce,
    "filter": _op_filter,
    "map": _op_map,
    "all": _op_all,
    "none": _op_none,
    "some": _op_some,
    "merge": _op_merge,
    "min": _op_min,
    "max": _op_max,
    "cat": _op_cat,
    "substr": _op_substr,
    "+": _op_add,
    "-": _op_subtract,
    "*": _op_multiply,
    "/": _op_divide,
    "%": _op_modulo,
    "log": _op_log,
}


# ── Helpers ────────────────────────────────────────────────────────


def _collect_numbers(values: list, context: dict[str, Any]) -> list[float | int]:
    """Collect and flatten numeric values from JSON Logic arguments."""
    nums: list[float | int] = []
    for v in values:
        item = json_logic(v, context)
        if isinstance(item, (int, float)):
            nums.append(item)
        elif isinstance(item, list):
            for sub in item:
                if isinstance(sub, (int, float)):
                    nums.append(sub)
    return nums


# ── Rule Evaluator ─────────────────────────────────────────────────


class RuleEvaluator:
    """High-level rule evaluator with explanation support.

    Wraps the json_logic function with additional features like
    explanation trees and rule catalog integration.
    """

    def __init__(self, catalog: Optional[BusinessRuleCatalog] = None) -> None:
        self.catalog = catalog or BusinessRuleCatalog()

    def evaluate(self, rule: dict[str, Any], context: dict[str, Any]) -> bool:
        """Evaluate a rule and return a boolean result.

        Args:
            rule: A JSON Logic rule expression.
            context: The data context for evaluation.

        Returns:
            Boolean result of the rule evaluation.
        """
        result = json_logic(rule, context)
        return bool(result)

    def explain(self, rule: dict[str, Any], context: dict[str, Any]) -> ExplanationNode:
        """Evaluate a rule and build an explanation tree.

        Args:
            rule: A JSON Logic rule expression.
            context: The data context for evaluation.

        Returns:
            An ExplanationNode tree showing how the result was derived.
        """
        return self._explain_node(rule, context)

    def _explain_node(self, node: Any, context: dict[str, Any]) -> ExplanationNode:
        """Recursively build an explanation tree for a rule node."""
        if not isinstance(node, dict) or len(node) != 1:
            result = json_logic(node, context)
            return ExplanationNode(
                operator="literal",
                result=result,
                summary=f"Literal value: {node!r} → {result!r}",
            )

        operator = next(iter(node))
        values = node[operator]
        if not isinstance(values, list):
            values = [values]

        children: list[ExplanationNode] = []
        for v in values:
            if isinstance(v, dict):
                children.append(self._explain_node(v, context))
            else:
                child_result = json_logic(v, context)
                children.append(ExplanationNode(
                    operator="value",
                    result=child_result,
                    summary=f"Value: {v!r} → {child_result!r}",
                ))

        result = json_logic(node, context)
        child_summaries = "; ".join(c.summary for c in children)
        return ExplanationNode(
            operator=operator,
            result=result,
            children=children,
            summary=f"({operator}) {child_summaries} → {result!r}",
        )
