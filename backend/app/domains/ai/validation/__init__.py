"""LLM response validation layer — never trust raw provider output.

This layer sits AFTER provider execution and BEFORE any business logic.
It validates:
- Schema conformity (JSON validity, required fields)
- Hallucination heuristics (citation verification, confidence thresholds)
- Required evidence presence
- Citation completeness
- Confidence thresholds
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    ERROR = "error"      # Must fix — response unusable
    WARNING = "warning"  # Suspicious but usable with caution
    INFO = "info"        # Informational


@dataclass
class ValidationIssue:
    """A single validation issue found in an LLM response."""
    code: str
    message: str
    severity: ValidationSeverity
    field_name: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validating an LLM response."""
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    score: float = 1.0  # 0.0 (fail) to 1.0 (perfect)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": round(self.score, 4),
            "issues": [
                {
                    "code": i.code,
                    "message": i.message,
                    "severity": i.severity.value,
                    "field": i.field_name,
                    "details": i.details,
                }
                for i in self.issues
            ],
        }


# ── Validation Rules ──────────────────────────────────────────────

@dataclass
class ValidationRule:
    """A single validation rule."""
    name: str
    description: str
    severity: ValidationSeverity
    validator: Callable[[dict[str, Any], str | None], list[ValidationIssue]]


class LLMResponseValidator:
    """Validates LLM responses for quality, safety, and structural integrity.

    Usage::
        validator = LLMResponseValidator()
        result = validator.validate(response_content, prompt_text)
        if not result.passed:
            # Handle validation failure
            logger.warning("Response validation failed: %s", result.issues)
    """

    def __init__(self, rules: list[ValidationRule] | None = None):
        self.rules = rules or self._default_rules()

    @staticmethod
    def _default_rules() -> list[ValidationRule]:
        return [
            ValidationRule(
                name="json_validity",
                description="Response must be valid JSON",
                severity=ValidationSeverity.ERROR,
                validator=_validate_json_validity,
            ),
            ValidationRule(
                name="required_fields",
                description="Response must contain required top-level fields",
                severity=ValidationSeverity.ERROR,
                validator=_validate_required_fields,
            ),
            ValidationRule(
                name="findings_structure",
                description="Each finding must have required sub-fields",
                severity=ValidationSeverity.WARNING,
                validator=_validate_findings_structure,
            ),
            ValidationRule(
                name="confidence_range",
                description="Confidence values must be in 0.0-1.0 range",
                severity=ValidationSeverity.WARNING,
                validator=_validate_confidence_range,
            ),
            ValidationRule(
                name="risk_score_range",
                description="Risk score must be in 0.0-1.0 range",
                severity=ValidationSeverity.ERROR,
                validator=_validate_risk_score_range,
            ),
            ValidationRule(
                name="hallucination_heuristic",
                description="Detect plausible-sounding but unverifiable claims",
                severity=ValidationSeverity.WARNING,
                validator=_validate_hallucination_heuristics,
            ),
            ValidationRule(
                name="citation_completeness",
                description="Findings should reference specific chunk indices",
                severity=ValidationSeverity.WARNING,
                validator=_validate_citation_completeness,
            ),
            ValidationRule(
                name="empty_response",
                description="Response should not be empty or trivial",
                severity=ValidationSeverity.ERROR,
                validator=_validate_empty_response,
            ),
            ValidationRule(
                name="clause_type_validity",
                description="Clause types must be from canonical set",
                severity=ValidationSeverity.WARNING,
                validator=_validate_clause_types,
            ),
            ValidationRule(
                name="severity_validity",
                description="Severity values must be valid",
                severity=ValidationSeverity.WARNING,
                validator=_validate_severity_values,
            ),
        ]

    def validate(
        self,
        response_content: str,
        prompt_text: str | None = None,
    ) -> ValidationResult:
        """Validate an LLM response against all configured rules.

        Args:
            response_content: The raw string content from the LLM.
            prompt_text: The original prompt (used for context-dependent checks).

        Returns:
            ValidationResult with pass/fail status and all issues.
        """
        issues: list[ValidationIssue] = []

        # Parse JSON first
        parsed: dict[str, Any] | None = None
        try:
            parsed = json.loads(response_content)
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                code="invalid_json",
                message=f"Response is not valid JSON: {e}",
                severity=ValidationSeverity.ERROR,
                details={"error": str(e)},
            ))
            return ValidationResult(passed=False, issues=issues, score=0.0)

        if not isinstance(parsed, dict):
            issues.append(ValidationIssue(
                code="invalid_structure",
                message="Response parsed but is not a JSON object",
                severity=ValidationSeverity.ERROR,
            ))
            return ValidationResult(passed=False, issues=issues, score=0.0)

        # Run all rules
        for rule in self.rules:
            try:
                rule_issues = rule.validator(parsed, prompt_text)
                issues.extend(rule_issues)
            except Exception as e:
                logger.warning("Validation rule '%s' failed: %s", rule.name, e)
                issues.append(ValidationIssue(
                    code=f"rule_error_{rule.name}",
                    message=f"Validation rule '{rule.name}' raised an error: {e}",
                    severity=ValidationSeverity.WARNING,
                ))

        # Compute score
        score = self._compute_score(issues)

        return ValidationResult(
            passed=len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0,
            issues=issues,
            score=score,
        )

    def _compute_score(self, issues: list[ValidationIssue]) -> float:
        """Compute a quality score from 0.0 to 1.0 based on issues."""
        if not issues:
            return 1.0

        score = 1.0
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                score -= 0.25
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 0.10
            elif issue.severity == ValidationSeverity.INFO:
                score -= 0.02

        return max(0.0, score)


# ── Individual Validators ─────────────────────────────────────────

def _validate_json_validity(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    """Already validated before calling rules — this is a no-op."""
    return []


_REQUIRED_FIELDS = {"risk_score", "summary", "findings"}


def _validate_required_fields(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    missing = _REQUIRED_FIELDS - set(parsed.keys())
    if missing:
        issues.append(ValidationIssue(
            code="missing_required_fields",
            message=f"Response missing required fields: {', '.join(sorted(missing))}",
            severity=ValidationSeverity.ERROR,
            details={"missing_fields": list(missing)},
        ))
    return issues


def _validate_findings_structure(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    findings = parsed.get("findings", [])
    if not isinstance(findings, list):
        issues.append(ValidationIssue(
            code="findings_not_list",
            message="'findings' field must be a list",
            severity=ValidationSeverity.ERROR,
        ))
        return issues

    required_finding_fields = {"clause_type", "severity", "title", "description"}
    for i, finding in enumerate(findings):
        if not isinstance(finding, dict):
            issues.append(ValidationIssue(
                code="finding_not_dict",
                message=f"Finding at index {i} is not a dictionary",
                severity=ValidationSeverity.ERROR,
                details={"index": i},
            ))
            continue
        missing = required_finding_fields - set(finding.keys())
        if missing:
            issues.append(ValidationIssue(
                code="finding_missing_fields",
                message=f"Finding {i} missing fields: {', '.join(sorted(missing))}",
                severity=ValidationSeverity.WARNING,
                details={"index": i, "missing_fields": list(missing)},
            ))

    return issues


def _validate_confidence_range(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    findings = parsed.get("findings", [])
    if not isinstance(findings, list):
        return issues

    for i, finding in enumerate(findings):
        if not isinstance(finding, dict):
            continue
        confidence = finding.get("confidence")
        if confidence is not None:
            try:
                val = float(confidence)
                if not (0.0 <= val <= 1.0):
                    issues.append(ValidationIssue(
                        code="confidence_out_of_range",
                        message=f"Finding {i} has confidence {val} outside [0.0, 1.0]",
                        severity=ValidationSeverity.WARNING,
                        details={"index": i, "confidence": val},
                    ))
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    code="confidence_not_numeric",
                    message=f"Finding {i} has non-numeric confidence: {confidence}",
                    severity=ValidationSeverity.WARNING,
                    details={"index": i, "confidence": str(confidence)},
                ))

    return issues


def _validate_risk_score_range(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    risk_score = parsed.get("risk_score")
    if risk_score is not None:
        try:
            val = float(risk_score)
            if not (0.0 <= val <= 1.0):
                issues.append(ValidationIssue(
                    code="risk_score_out_of_range",
                    message=f"Risk score {val} is outside [0.0, 1.0]",
                    severity=ValidationSeverity.ERROR,
                    details={"risk_score": val},
                ))
        except (ValueError, TypeError):
            issues.append(ValidationIssue(
                code="risk_score_not_numeric",
                message=f"Risk score is not numeric: {risk_score}",
                severity=ValidationSeverity.ERROR,
                details={"risk_score": str(risk_score)},
            ))
    return issues


_HALLUCINATION_PATTERNS = [
    r"\bI (think|believe|guess|assume)\b",
    r"\b(maybe|perhaps|possibly|might be)\b",
    r"\b(unfortunately|regrettably)\b",
    r"\bcannot (determine|verify|confirm)\b",
    r"\bno (information|data|evidence) (was )?provided\b",
    r"\bbased (solely|only) on (the )?(limited )?information\b",
]


def _validate_hallucination_heuristics(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    """Detect language patterns that suggest hallucination or uncertainty."""
    issues: list[ValidationIssue] = []

    text_to_check = json.dumps(parsed).lower()

    for pattern in _HALLUCINATION_PATTERNS:
        matches = re.findall(pattern, text_to_check, re.IGNORECASE)
        if matches:
            issues.append(ValidationIssue(
                code="hallucination_language",
                message=f"Response contains language suggesting uncertainty: '{pattern}'",
                severity=ValidationSeverity.WARNING,
                details={"pattern": pattern, "matches": len(matches)},
            ))

    # Check for specific unsupported claims
    unsupported_claims = [
        "industry standard", "market practice", "typical in the industry",
        "standard practice", "widely accepted", "commonly used",
    ]
    for claim in unsupported_claims:
        if claim.lower() in text_to_check:
            issues.append(ValidationIssue(
                code="unsupported_claim",
                message=f"Response makes unverifiable claim: '{claim}'",
                severity=ValidationSeverity.WARNING,
                details={"claim": claim},
            ))

    return issues


def _validate_citation_completeness(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    """Verify that findings reference specific chunk indices."""
    issues: list[ValidationIssue] = []
    findings = parsed.get("findings", [])

    if not isinstance(findings, list):
        return issues

    uncited_count = 0
    for i, finding in enumerate(findings):
        if not isinstance(finding, dict):
            continue
        chunk_indices = finding.get("chunk_indices")
        if not chunk_indices or (isinstance(chunk_indices, list) and len(chunk_indices) == 0):
            uncited_count += 1

    if uncited_count > 0 and len(findings) > 0:
        ratio = uncited_count / len(findings)
        if ratio > 0.5:
            issues.append(ValidationIssue(
                code="missing_citations",
                message=f"{uncited_count}/{len(findings)} findings lack chunk citations",
                severity=ValidationSeverity.WARNING,
                details={"uncited_count": uncited_count, "total_findings": len(findings), "ratio": ratio},
            ))

    return issues


def _validate_empty_response(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not parsed.get("findings") and not parsed.get("summary"):
        issues.append(ValidationIssue(
            code="empty_response",
            message="Response contains no findings and no summary",
            severity=ValidationSeverity.ERROR,
        ))
    return issues


_VALID_CLAUSE_TYPES = {
    "liability", "payment", "data_privacy", "compliance",
    "indemnification", "termination", "confidentiality",
    "intellectual_property", "insurance", "force_majeure",
    "governing_law", "non_compete", "assignment",
    "dispute_resolution", "warranty", "renewal", "term",
    "security", "other",
}


def _validate_clause_types(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    findings = parsed.get("findings", [])
    if not isinstance(findings, list):
        return issues

    invalid_types = set()
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        ct = finding.get("clause_type", "")
        if ct and ct not in _VALID_CLAUSE_TYPES:
            invalid_types.add(ct)

    if invalid_types:
        issues.append(ValidationIssue(
            code="invalid_clause_types",
            message=f"Response contains non-canonical clause types: {', '.join(sorted(invalid_types))}",
            severity=ValidationSeverity.WARNING,
            details={"invalid_types": list(invalid_types)},
        ))

    return issues


_VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}


def _validate_severity_values(
    parsed: dict[str, Any], prompt: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    findings = parsed.get("findings", [])
    if not isinstance(findings, list):
        return issues

    invalid_severities = set()
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        sev = finding.get("severity", "")
        if sev and sev.lower() not in _VALID_SEVERITIES:
            invalid_severities.add(sev)

    if invalid_severities:
        issues.append(ValidationIssue(
            code="invalid_severities",
            message=f"Response contains invalid severity values: {', '.join(sorted(invalid_severities))}",
            severity=ValidationSeverity.WARNING,
            details={"invalid_severities": list(invalid_severities)},
        ))

    return issues
