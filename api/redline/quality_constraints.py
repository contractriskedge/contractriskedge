"""Quality constraints to prevent legally dangerous redline suggestions.

Enforces a set of hard and soft constraints on generated redlines to
prevent suggestions that are legally unsound, unethical, or could create
liability for the user.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import ClauseType

logger = logging.getLogger(__name__)


@dataclass
class QualityCheckResult:
    """Result of a single quality constraint check."""

    constraint_name: str
    passed: bool
    severity: str  # "error" | "warning" | "info"
    message: str
    details: Optional[Dict[str, Any]] = None


class QualityConstraintViolation(Exception):
    """Raised when a hard quality constraint is violated."""

    def __init__(
        self,
        message: str,
        constraint_name: str,
        clause_type: Optional[ClauseType] = None,
    ) -> None:
        self.constraint_name = constraint_name
        self.clause_type = clause_type
        super().__init__(message)


class QualityConstraintEngine:
    """Quality constraint engine for redline suggestions.

    Enforces both hard constraints (must pass) and soft constraints
    (warnings) on generated redline text. Hard constraints prevent
    legally dangerous suggestions from being returned to the user.

    Usage:
        engine = QualityConstraintEngine()
        results = engine.check_all(proposed_text, ClauseType.LIABILITY_CAPS)
        if not engine.all_hard_passed(results):
            raise QualityConstraintViolation(...)
    """

    # Phrases that should never appear in a redline suggestion
    HARD_BLOCKED_PATTERNS: List[Tuple[str, str, str]] = [
        (r"(?i)\bsue\s+(?:immediately|forthwith|without\s+notice)\b", "Immediate lawsuit threat", "Threatening immediate legal action is unethical and may constitute bad faith"),
        (r"(?i)\bwaive\s+(?:all|any|every)\s+(?:rights?|claims?|defenses?)\b(?!\s*(?:except|other\s+than|excluding))", "Blanket rights waiver", "Blanket waivers of all rights are likely unconscionable"),
        (r"(?i)\bindemnify\s+(?:and\s+)?hold\s+harmless\s+for\s+(?:its?|their?|own)\s+negligence\b", "Negligence indemnity without exception", "Indemnification for own negligence requires explicit, conspicuous language"),
        (r"(?i)\bunlimited\s+liability\b(?!\s*(?:for\s+(?:fraud|gross\s+negligence|willful\s+misconduct|ip\s+infringement|death|personal\s+injury)))", "Unlimited liability without carve-outs", "Unlimited liability without standard carve-outs is commercially unreasonable"),
        (r"(?i)\bno\s+(?:right\s+of\s+)?termination\s+(?:for\s+)?(?:convenience|cause)\b", "No termination rights", "Completely eliminating termination rights may be unconscionable"),
        (r"(?i)\b(?:irrevocably|perpetually)\s+(?:and\s+)?(?:unconditionally)\s+(?:grant|license|assign)\b(?!\s*(?:subject\s+to|except|provided))", "Irrevocable grant without conditions", "Absolute irrevocable grants without any conditions are risky"),
        (r"(?i)\b(?:confess\s+)?judg(?:ment|e)\s+(?:by\s+)?(?:confession|consent)\b", "Confession of judgment", "Confession of judgment clauses are unenforceable in many jurisdictions"),
        (r"(?i)\bindemnify\s+(?:and\s+)?hold\s+harmless\s+for\s+(?:any\s+)?(?:and\s+)?all\s+(?:claims|losses|damages|liabilities)\s+(?:whatsoever|howsoever\s+arising)", "Unlimited indemnification scope", "Unlimited indemnification without causation limitation is overly broad"),
    ]

    # Clause-type-specific forbidden patterns
    CLAUSE_TYPE_BLOCKED: Dict[ClauseType, List[Tuple[str, str, str]]] = {
        ClauseType.LIABILITY_CAPS: [
            (r"(?i)\$0\b", "Zero liability cap", "A $0 liability cap is effectively no cap and may be unenforceable"),
            (r"(?i)\bno\s+(?:limit|cap|maximum)\s+(?:on\s+)?liability\b", "No liability cap", "Completely uncapped liability is commercially unreasonable"),
        ],
        ClauseType.INDEMNIFICATION: [
            (r"(?i)\bindemnify\s+(?:and\s+)?hold\s+harmless\s+for\s+(?:any\s+)?(?:and\s+)?all\s+(?:claims|losses|damages)\s+(?:arising\s+)?(?:out\s+of\s+)?(?:or\s+)?(?:relating\s+to\s+)?this\s+agreement\b", "Overly broad indemnification", "Indemnification for 'all claims arising out of this agreement' without causation limitation is too broad"),
        ],
        ClauseType.IP_OWNERSHIP: [
            (r"(?i)\ball\s+(?:intellectual\s+)?property\s+(?:rights\s+)?(?:developed|created|made)\s+(?:by|during)\b", "Overly broad IP assignment", "Assignment of 'all IP developed' without exception for pre-existing IP is overly broad"),
        ],
        ClauseType.PAYMENT_TERMS: [
            (r"(?i)\binterest\s+(?:rate\s+)?(?:in\s+)?excess\s+of\s+(?:the\s+)?(?:legal|maximum|usury)\s+(?:rate|limit)\b", "Usury risk", "Interest rate exceeding legal limits is unenforceable and may create liability"),
        ],
        ClauseType.GOVERNING_LAW: [
            (r"(?i)\bexclusive\s+jurisdiction\s+(?:in|of)\s+(?:a\s+)?(?:foreign|court\s+(?:in|located\s+in)\s+)?(?:country|jurisdiction)\s+(?:with\s+)?(?:no|limited|unreliable)\s+(?:commercial\s+)?(?:law|courts|legal\s+system)\b", "Unreasonable forum", "Requiring litigation in a forum with no connection to the transaction may be unenforceable"),
        ],
        ClauseType.TERMINATION_RIGHTS: [
            (r"(?i)\bterminat(?:e|ion)\s+(?:this\s+)?agreement\s+(?:immediately|forthwith)\s+(?:upon|for)\s+(?:any\s+)?breach\b", "Immediate termination for any breach", "Termination for any breach without cure period or materiality threshold is disproportionate"),
        ],
        ClauseType.CONFIDENTIALITY: [
            (r"(?i)\bno\s+(?:time\s+)?limit|perpetual\s+(?:confidentiality|obligation)\b", "Perpetual confidentiality", "Perpetual confidentiality obligations (beyond trade secrets) may be unreasonable"),
        ],
        ClauseType.FORCE_MAJEURE: [
            (r"(?i)\bforce\s+majeure\s+(?:shall|will|may)\s+(?:excuse|suspend|waive)\s+(?:payment|fees|compensation)\b", "Force majeure excusing payment", "Force majeure should not excuse payment obligations"),
        ],
    }

    # Soft constraints (warnings, not blocking)
    SOFT_CONSTRAINTS: List[Tuple[str, str, str]] = [
        (r"(?i)\b(?:material|substantial)\s+(?:and\s+)?adverse\s+(?:change|effect|impact)\b", "MAC clause without definition", "Material Adverse Change clauses should be specifically defined"),
        (r"(?i)\b(?:best|reasonable)\s+(?:efforts|endeavors)\b(?!\s*(?:standard|commercially))", "Efforts standard without qualifier", "'Best efforts' is a higher standard than 'commercially reasonable efforts'"),
        (r"(?i)\breasonableness\s+standard\b", "Reasonableness standard without qualifier", "Consider specifying 'commercially reasonable' vs 'good faith' standard"),
        (r"(?i)\b(?:indemnify|hold\s+harmless)\s+(?:and\s+)?(?:defend|indemnify)\b", "Indemnify and defend without scope", "Consider specifying whether 'defend' creates a duty to defend"),
        (r"(?i)\b(?:as\s+)?soon\s+as\s+(?:practicable|reasonably\s+practicable)\b", "Vague timing standard", "'As soon as practicable' is vague — consider specifying a concrete timeframe"),
        (r"(?i)\b(?:any|all)\s+(?:and\s+)?(?:all|any)\s+(?:disputes|claims|controversies)\b", "Overly broad dispute scope", "Consider whether certain claims (IP, confidentiality) should be excluded from mandatory ADR"),
    ]

    def __init__(self, strict_mode: bool = True) -> None:
        """Initialize the quality constraint engine.

        Args:
            strict_mode: If True, hard constraint violations raise exceptions.
                         If False, they are returned as failed checks.
        """
        self._strict_mode = strict_mode

    def check_all(
        self,
        proposed_text: str,
        clause_type: ClauseType,
    ) -> List[QualityCheckResult]:
        """Run all applicable quality checks on proposed text.

        Args:
            proposed_text: The proposed redline text to check.
            clause_type: The type of clause being checked.

        Returns:
            List of QualityCheckResult objects.
        """
        results: List[QualityCheckResult] = []

        # Check hard blocked patterns
        results.extend(self._check_hard_patterns(proposed_text))

        # Check clause-type-specific patterns
        results.extend(self._check_clause_type_patterns(proposed_text, clause_type))

        # Check soft constraints
        results.extend(self._check_soft_constraints(proposed_text))

        # Check structural constraints
        results.extend(self._check_structural(proposed_text, clause_type))

        return results

    def _check_hard_patterns(
        self, text: str
    ) -> List[QualityCheckResult]:
        """Check for globally blocked patterns.

        Args:
            text: The text to check.

        Returns:
            List of quality check results.
        """
        results: List[QualityCheckResult] = []
        for pattern, name, description in self.HARD_BLOCKED_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                results.append(QualityCheckResult(
                    constraint_name=f"hard_blocked:{name}",
                    passed=False,
                    severity="error",
                    message=description,
                    details={"matches": matches, "pattern": pattern},
                ))
        return results

    def _check_clause_type_patterns(
        self, text: str, clause_type: ClauseType
    ) -> List[QualityCheckResult]:
        """Check for clause-type-specific blocked patterns.

        Args:
            text: The text to check.
            clause_type: The clause type.

        Returns:
            List of quality check results.
        """
        results: List[QualityCheckResult] = []
        blocked = self.CLAUSE_TYPE_BLOCKED.get(clause_type, [])
        for pattern, name, description in blocked:
            matches = re.findall(pattern, text)
            if matches:
                results.append(QualityCheckResult(
                    constraint_name=f"clause_type_blocked:{name}",
                    passed=False,
                    severity="error",
                    message=description,
                    details={"matches": matches, "clause_type": clause_type.value},
                ))
        return results

    def _check_soft_constraints(
        self, text: str
    ) -> List[QualityCheckResult]:
        """Check for soft constraint warnings.

        Args:
            text: The text to check.

        Returns:
            List of quality check results.
        """
        results: List[QualityCheckResult] = []
        for pattern, name, description in self.SOFT_CONSTRAINTS:
            matches = re.findall(pattern, text)
            if matches:
                results.append(QualityCheckResult(
                    constraint_name=f"soft_warning:{name}",
                    passed=True,
                    severity="warning",
                    message=description,
                    details={"matches": matches, "pattern": pattern},
                ))
        return results

    def _check_structural(
        self, text: str, clause_type: ClauseType
    ) -> List[QualityCheckResult]:
        """Check structural quality constraints.

        Args:
            text: The proposed text.
            clause_type: The clause type.

        Returns:
            List of quality check results.
        """
        results: List[QualityCheckResult] = []

        # Check minimum length
        if len(text.strip()) < 50:
            results.append(QualityCheckResult(
                constraint_name="structural:minimum_length",
                passed=False,
                severity="error",
                message="Proposed text is too short (less than 50 characters)",
                details={"length": len(text.strip())},
            ))

        # Check for proper sentence structure
        sentences = re.split(r'[.!?]\s+', text.strip())
        if len(sentences) < 2:
            results.append(QualityCheckResult(
                constraint_name="structural:sentence_count",
                passed=False,
                severity="warning",
                message="Proposed text contains fewer than 2 sentences",
                details={"sentence_count": len(sentences)},
            ))

        # Check for defined terms in ALL CAPS (good practice)
        defined_terms = re.findall(r'\b[A-Z][A-Z\s]{3,}[A-Z]\b', text)
        if not defined_terms and len(text) > 200:
            results.append(QualityCheckResult(
                constraint_name="structural:defined_terms",
                passed=True,
                severity="info",
                message="Consider using defined terms (ALL CAPS) for key concepts",
                details={"text_length": len(text)},
            ))

        # Check for section numbering
        if len(text) > 300 and not re.search(r'\(\s*[a-zA-Z0-9]\s*\)', text):
            results.append(QualityCheckResult(
                constraint_name="structural:section_numbering",
                passed=True,
                severity="info",
                message="Consider adding subsection numbering for complex clauses",
                details={"text_length": len(text)},
            ))

        # Check for mutual language (fairness indicator)
        if clause_type in (ClauseType.LIABILITY_CAPS, ClauseType.TERMINATION_RIGHTS, ClauseType.INDEMNIFICATION):
            has_mutual = re.search(r'(?i)\b(?:each|either|both)\s+(?:party|parties)\b', text)
            has_one_sided = re.search(
                r'(?i)(?:client|buyer|licensee|customer)\s+(?:shall|will|may)\b(?!.*\b(?:provider|seller|licensor|vendor)\s+(?:shall|will|may)\b)',
                text,
            )
            if has_one_sided and not has_mutual:
                results.append(QualityCheckResult(
                    constraint_name="structural:one_sided_language",
                    passed=True,
                    severity="warning",
                    message="Clause appears one-sided — consider adding mutual language",
                    details={"clause_type": clause_type.value},
                ))

        return results

    def all_hard_passed(self, results: List[QualityCheckResult]) -> bool:
        """Check if all hard constraint checks passed.

        Args:
            results: List of quality check results.

        Returns:
            True if all error-severity checks passed.
        """
        return all(
            r.passed for r in results if r.severity == "error"
        )

    def get_errors(self, results: List[QualityCheckResult]) -> List[QualityCheckResult]:
        """Get only error-severity results.

        Args:
            results: List of quality check results.

        Returns:
            Filtered list of error results.
        """
        return [r for r in results if r.severity == "error"]

    def get_warnings(self, results: List[QualityCheckResult]) -> List[QualityCheckResult]:
        """Get only warning-severity results.

        Args:
            results: List of quality check results.

        Returns:
            Filtered list of warning results.
        """
        return [r for r in results if r.severity == "warning"]

    def validate(
        self,
        proposed_text: str,
        clause_type: ClauseType,
    ) -> Tuple[bool, List[QualityCheckResult]]:
        """Validate proposed text against all constraints.

        Args:
            proposed_text: The proposed redline text.
            clause_type: The clause type.

        Returns:
            Tuple of (is_valid, list_of_results).

        Raises:
            QualityConstraintViolation: If strict mode is on and hard constraints fail.
        """
        results = self.check_all(proposed_text, clause_type)
        is_valid = self.all_hard_passed(results)

        if not is_valid and self._strict_mode:
            errors = self.get_errors(results)
            error_messages = "; ".join(
                f"[{e.constraint_name}] {e.message}" for e in errors
            )
            raise QualityConstraintViolation(
                message=error_messages,
                constraint_name="quality_constraint_engine",
                clause_type=clause_type,
            )

        return is_valid, results
