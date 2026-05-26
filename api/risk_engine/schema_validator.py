"""Pydantic v2 validation for LLM risk flagging output.

Provides runtime validation of every LLM-generated risk flag output
using Pydantic v2. Ensures all outputs conform to the canonical schema
before being persisted or returned to clients.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import ValidationError

from .output_schema import RiskFlagOutput, RiskFlagSet, SuggestedAction, BenchmarkComparison

logger = logging.getLogger(__name__)


class ValidationReport:
    """Report of schema validation results for LLM outputs."""

    def __init__(self) -> None:
        self.total_validated: int = 0
        self.passed: int = 0
        self.failed: int = 0
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[str] = []

    def add_success(self) -> None:
        self.total_validated += 1
        self.passed += 1

    def add_failure(self, error: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.total_validated += 1
        self.failed += 1
        self.errors.append({
            "error": error,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        })

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)

    @property
    def pass_rate(self) -> float:
        if self.total_validated == 0:
            return 1.0
        return self.passed / self.total_validated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_validated": self.total_validated,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 4),
            "errors": self.errors[-10:],  # Last 10 errors
            "warnings": self.warnings[-10:],
        }


class OutputSchemaValidator:
    """Pydantic v2 validation for all LLM risk flagging outputs.

    Validates every risk flag output against the canonical schema.
    Provides detailed error reporting, field-level validation, and
    batch validation capabilities.

    Usage:
        validator = OutputSchemaValidator()
        result = validator.validate_flag(flag_data)
        if result.is_valid:
            flag = result.flag
        else:
            print(f"Validation failed: {result.error}")
    """

    def __init__(self, strict_mode: bool = True) -> None:
        """Initialize the schema validator.

        Args:
            strict_mode: If True, raises on validation failure.
                         If False, attempts to coerce/fix data.
        """
        self._strict_mode = strict_mode
        self._report = ValidationReport()

    def validate_flag(
        self, data: Dict[str, Any]
    ) -> "ValidationResult":
        """Validate a single risk flag output.

        Args:
            data: Dictionary of risk flag data to validate.

        Returns:
            ValidationResult with the validated flag or error details.
        """
        try:
            flag = RiskFlagOutput(**data)
            self._report.add_success()
            return ValidationResult(is_valid=True, flag=flag)
        except ValidationError as exc:
            self._report.add_failure(
                error="Schema validation failed",
                details={"errors": exc.errors(), "input": data},
            )
            if self._strict_mode:
                return ValidationResult(
                    is_valid=False,
                    error=f"Validation failed: {exc}",
                    validation_errors=exc.errors(),
                )
            # Attempt coercion
            return self._coerce_and_validate(data)

    def validate_flag_set(
        self, data: Dict[str, Any]
    ) -> "ValidationResult":
        """Validate a complete risk flag set.

        Args:
            data: Dictionary with flags list and metadata.

        Returns:
            ValidationResult with validated flag set.
        """
        try:
            # Validate individual flags first
            flags_data = data.get("flags", [])
            validated_flags: list[RiskFlagOutput] = []
            for i, flag_data in enumerate(flags_data):
                result = self.validate_flag(flag_data)
                if not result.is_valid:
                    return ValidationResult(
                        is_valid=False,
                        error=f"Flag at index {i} failed validation: {result.error}",
                        validation_errors=result.validation_errors,
                    )
                validated_flags.append(result.flag)

            # Build complete flag set
            flag_set_data = {**data, "flags": validated_flags}
            flag_set = RiskFlagSet(**flag_set_data)
            self._report.add_success()
            return ValidationResult(is_valid=True, flag_set=flag_set)

        except ValidationError as exc:
            self._report.add_failure(
                error="Flag set validation failed",
                details={"errors": exc.errors()},
            )
            return ValidationResult(
                is_valid=False,
                error=f"Flag set validation failed: {exc}",
                validation_errors=exc.errors(),
            )

    def validate_batch(
        self, items: List[Dict[str, Any]]
    ) -> List["ValidationResult"]:
        """Validate a batch of risk flag outputs.

        Args:
            items: List of risk flag data dicts.

        Returns:
            List of validation results.
        """
        return [self.validate_flag(item) for item in items]

    def _coerce_and_validate(
        self, data: Dict[str, Any]
    ) -> "ValidationResult":
        """Attempt to coerce invalid data into valid schema.

        Tries to fix common issues like type mismatches, missing
        optional fields, and format problems.

        Args:
            data: The potentially invalid data.

        Returns:
            ValidationResult with coerced flag or error.
        """
        coerced = dict(data)

        # Fix severity if it's a string
        if isinstance(coerced.get("severity"), str):
            try:
                coerced["severity"] = int(coerced["severity"])
            except (ValueError, TypeError):
                pass

        # Fix confidence case
        if "confidence" in coerced and isinstance(coerced["confidence"], str):
            confidence = coerced["confidence"].lower()
            if confidence in ("high", "medium", "low"):
                coerced["confidence"] = confidence

        # Ensure suggested_action has required fields
        if "suggested_action" in coerced:
            action = coerced["suggested_action"]
            if isinstance(action, dict):
                if "action" not in action:
                    coerced["suggested_action"]["action"] = "review"
                if "description" not in action:
                    coerced["suggested_action"]["description"] = (
                        "Review this clause for potential risk"
                    )

        # Set defaults for optional fields
        coerced.setdefault("metadata", {})

        try:
            flag = RiskFlagOutput(**coerced)
            self._report.add_success()
            self._report.add_warning("Data was coerced to match schema")
            return ValidationResult(
                is_valid=True,
                flag=flag,
                warning="Data was coerced to match schema",
            )
        except ValidationError as exc:
            self._report.add_failure(
                error="Coercion also failed",
                details={"errors": exc.errors()},
            )
            return ValidationResult(
                is_valid=False,
                error=f"Validation and coercion failed: {exc}",
                validation_errors=exc.errors(),
            )

    def get_report(self) -> ValidationReport:
        """Get the validation report.

        Returns:
            Current validation report.
        """
        return self._report

    def reset_report(self) -> None:
        """Reset the validation report."""
        self._report = ValidationReport()

    def validate_field(
        self, field_name: str, value: Any
    ) -> Tuple[bool, Optional[str]]:
        """Validate a single field value against the schema.

        Args:
            field_name: The field name to validate.
            value: The value to check.

        Returns:
            Tuple of (is_valid, error_message).
        """
        schema_fields = RiskFlagOutput.model_fields

        if field_name not in schema_fields:
            return False, f"Unknown field: {field_name}"

        field_info = schema_fields[field_name]
        try:
            # Use Pydantic's type validation
            if field_name == "severity" and isinstance(value, int):
                if value < 1 or value > 10:
                    return False, "Severity must be between 1 and 10"
            elif field_name == "confidence" and isinstance(value, str):
                if value not in ("high", "medium", "low"):
                    return False, "Confidence must be high, medium, or low"
            return True, None
        except Exception as exc:
            return False, str(exc)


class ValidationResult:
    """Result of a schema validation operation."""

    def __init__(
        self,
        is_valid: bool,
        flag: Optional[RiskFlagOutput] = None,
        flag_set: Optional[RiskFlagSet] = None,
        error: Optional[str] = None,
        warning: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.is_valid = is_valid
        self.flag = flag
        self.flag_set = flag_set
        self.error = error
        self.warning = warning
        self.validation_errors = validation_errors or []
