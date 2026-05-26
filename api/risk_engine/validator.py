"""Taxonomy validation and versioning.

Provides validation logic for the risk taxonomy including structural
validation, version management, and migration support between
taxonomy versions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .taxonomy import RiskTaxonomy
from .schema import TaxonomySchema

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a taxonomy validation operation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validated_at: datetime = datetime.utcnow()


@dataclass
class TaxonomyVersion:
    """A versioned snapshot of the taxonomy."""

    version: str
    created_at: datetime
    category_count: int
    sub_type_count: int
    checksum: str
    changelog: str


class TaxonomyValidator:
    """Validates and manages risk taxonomy versions.

    Provides comprehensive validation of the taxonomy structure,
    version tracking, migration support, and integrity checks.

    Usage:
        taxonomy = RiskTaxonomy()
        validator = TaxonomyValidator(taxonomy)
        result = validator.validate()
        if result.is_valid:
            print("Taxonomy is valid")
    """

    def __init__(self, taxonomy: RiskTaxonomy) -> None:
        """Initialize the validator with a taxonomy instance.

        Args:
            taxonomy: The risk taxonomy to validate.
        """
        self._taxonomy = taxonomy
        self._versions: List[TaxonomyVersion] = []
        self._current_version = TaxonomySchema.TAXONOMY_VERSION

    def validate(self) -> ValidationResult:
        """Perform comprehensive validation of the taxonomy.

        Checks structure, completeness, consistency, and integrity
        of the entire taxonomy definition.

        Returns:
            ValidationResult with errors and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        categories = self._taxonomy.get_all_categories()

        # Check category count
        if len(categories) != 12:
            errors.append(f"Expected 12 categories, found {len(categories)}")

        # Track IDs for uniqueness
        category_ids: set[str] = set()
        sub_type_ids: set[str] = set()

        for cat in categories:
            # Check category ID uniqueness
            if cat.id in category_ids:
                errors.append(f"Duplicate category ID: '{cat.id}'")
            category_ids.add(cat.id)

            # Check required fields
            if not cat.name:
                errors.append(f"Category '{cat.id}' missing name")
            if not cat.description:
                errors.append(f"Category '{cat.id}' missing description")

            # Check description length
            if len(cat.description) < 50:
                warnings.append(
                    f"Category '{cat.id}' description is short ({len(cat.description)} chars)"
                )

            # Check sub-type count
            if len(cat.sub_types) < 4:
                errors.append(
                    f"Category '{cat.id}' has {len(cat.sub_types)} sub-types (minimum 4)"
                )
            elif len(cat.sub_types) > 8:
                errors.append(
                    f"Category '{cat.id}' has {len(cat.sub_types)} sub-types (maximum 8)"
                )

            # Check severity range
            sev_min, sev_max = cat.default_severity_range
            if sev_min < 1 or sev_max > 10 or sev_min > sev_max:
                errors.append(
                    f"Category '{cat.id}' invalid severity range: [{sev_min}, {sev_max}]"
                )

            # Check benchmark dimensions
            if len(cat.benchmark_dimensions) < 3:
                warnings.append(
                    f"Category '{cat.id}' has fewer than 3 benchmark dimensions"
                )

            # Validate each sub-type
            for sub in cat.sub_types:
                if sub.id in sub_type_ids:
                    errors.append(
                        f"Duplicate sub-type ID: '{sub.id}' "
                        f"(in category '{cat.id}')"
                    )
                sub_type_ids.add(sub.id)

                if not sub.name:
                    errors.append(f"Sub-type '{sub.id}' missing name")
                if not sub.description:
                    errors.append(f"Sub-type '{sub.id}' missing description")

                s_min, s_max = sub.default_severity_range
                if s_min < 1 or s_max > 10 or s_min > s_max:
                    errors.append(
                        f"Sub-type '{sub.id}' invalid severity range: [{s_min}, {s_max}]"
                    )

                # Check example language
                if len(sub.example_high_risk_language) < 1:
                    warnings.append(
                        f"Sub-type '{sub.id}' missing high-risk language examples"
                    )
                if len(sub.example_market_standard_language) < 1:
                    warnings.append(
                        f"Sub-type '{sub.id}' missing market-standard language examples"
                    )

        # Check for required category IDs
        required_ids = {
            "indemnification", "liability_limitation", "termination",
            "confidentiality", "data_privacy", "compliance",
            "payment_terms", "force_majeure", "assignment",
            "governing_law", "non_compete", "intellectual_property",
        }
        missing_ids = required_ids - category_ids
        if missing_ids:
            errors.append(f"Missing required categories: {missing_ids}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_category(self, category_id: str) -> ValidationResult:
        """Validate a single category.

        Args:
            category_id: The category to validate.

        Returns:
            ValidationResult for the specific category.
        """
        errors: list[str] = []
        warnings: list[str] = []

        cat = self._taxonomy.get_category(category_id)
        if cat is None:
            errors.append(f"Category '{category_id}' not found")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        if len(cat.sub_types) < 4 or len(cat.sub_types) > 8:
            errors.append(
                f"Sub-type count {len(cat.sub_types)} out of range [4, 8]"
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def compute_checksum(self) -> str:
        """Compute a checksum for the current taxonomy.

        The checksum changes when any category or sub-type definition
        is modified, allowing detection of taxonomy drift.

        Returns:
            SHA-256 hex digest of the serialized taxonomy.
        """
        import hashlib
        import json

        taxonomy_dict = self._taxonomy.to_dict()
        serialized = json.dumps(taxonomy_dict, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def snapshot_version(self, changelog: str = "") -> TaxonomyVersion:
        """Create a versioned snapshot of the current taxonomy.

        Args:
            changelog: Description of changes in this version.

        Returns:
            A TaxonomyVersion record.
        """
        version = TaxonomyVersion(
            version=self._current_version,
            created_at=datetime.utcnow(),
            category_count=len(self._taxonomy.get_all_categories()),
            sub_type_count=self._taxonomy.get_total_sub_type_count(),
            checksum=self.compute_checksum(),
            changelog=changelog,
        )
        self._versions.append(version)
        logger.info(
            "Taxonomy snapshot v%s: %d categories, %d sub-types",
            version.version,
            version.category_count,
            version.sub_type_count,
        )
        return version

    def get_version_history(self) -> List[TaxonomyVersion]:
        """Get the version history of the taxonomy.

        Returns:
            List of version snapshots in chronological order.
        """
        return list(self._versions)

    def detect_drift(self, other_taxonomy: RiskTaxonomy) -> List[str]:
        """Detect differences between this taxonomy and another.

        Args:
            other_taxonomy: Another taxonomy to compare against.

        Returns:
            List of differences found.
        """
        differences: list[str] = []
        other_categories = other_taxonomy.get_all_categories()
        other_by_id = {c.id: c for c in other_categories}

        for cat in self._taxonomy.get_all_categories():
            other_cat = other_by_id.get(cat.id)
            if other_cat is None:
                differences.append(f"Category '{cat.id}' missing from other taxonomy")
                continue

            if len(cat.sub_types) != len(other_cat.sub_types):
                differences.append(
                    f"Category '{cat.id}' sub-type count differs: "
                    f"{len(cat.sub_types)} vs {len(other_cat.sub_types)}"
                )

            other_sub_by_id = {s.id: s for s in other_cat.sub_types}
            for sub in cat.sub_types:
                if sub.id not in other_sub_by_id:
                    differences.append(
                        f"Sub-type '{sub.id}' missing from other taxonomy's '{cat.id}'"
                    )

        return differences

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics.

        Returns:
            Dict with taxonomy statistics.
        """
        categories = self._taxonomy.get_all_categories()
        total_sub_types = self._taxonomy.get_total_sub_type_count()

        severity_ranges = [
            cat.default_severity_range for cat in categories
        ]
        avg_min = sum(r[0] for r in severity_ranges) / len(severity_ranges)
        avg_max = sum(r[1] for r in severity_ranges) / len(severity_ranges)

        return {
            "version": self._current_version,
            "category_count": len(categories),
            "sub_type_count": total_sub_types,
            "avg_severity_range": f"{avg_min:.1f}-{avg_max:.1f}",
            "checksum": self.compute_checksum(),
            "version_count": len(self._versions),
        }
