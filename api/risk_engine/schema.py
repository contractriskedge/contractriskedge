"""JSON Schema for the 12-category risk taxonomy.

Provides JSON Schema definitions for validating taxonomy instances,
category definitions, and sub-type configurations.
"""

from __future__ import annotations

import json
from typing import Any, Dict


class TaxonomySchema:
    """JSON Schema definitions for the risk taxonomy.

    Provides schema generation, validation, and versioning support
    for the 12-category risk taxonomy.
    """

    TAXONOMY_VERSION = "2.0.0"

    @classmethod
    def get_taxonomy_schema(cls) -> Dict[str, Any]:
        """Get the JSON Schema for the complete taxonomy.

        Returns:
            JSON Schema dict for taxonomy validation.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "https://contractriskanalyzer.com/schemas/taxonomy/v2.json",
            "title": "Contract Risk Taxonomy",
            "description": "12-category risk taxonomy for contract clause analysis",
            "version": cls.TAXONOMY_VERSION,
            "type": "object",
            "required": ["version", "categories"],
            "properties": {
                "version": {
                    "type": "string",
                    "description": "Taxonomy version identifier",
                    "pattern": r"^\d+\.\d+\.\d+$",
                },
                "category_count": {
                    "type": "integer",
                    "minimum": 12,
                    "maximum": 12,
                    "description": "Number of risk categories (must be 12)",
                },
                "sub_type_count": {
                    "type": "integer",
                    "minimum": 48,
                    "description": "Total number of sub-types across all categories",
                },
                "categories": {
                    "type": "object",
                    "description": "Risk categories keyed by category ID",
                    "minProperties": 12,
                    "maxProperties": 12,
                    "patternProperties": {
                        "^[a-z_]+$": {"$ref": "#/definitions/CategoryDef"}
                    },
                    "additionalProperties": False,
                },
            },
            "definitions": {
                "CategoryDef": {
                    "type": "object",
                    "required": ["id", "name", "description", "sub_types"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique category identifier",
                        },
                        "name": {
                            "type": "string",
                            "description": "Display name",
                        },
                        "description": {
                            "type": "string",
                            "description": "Category description",
                            "minLength": 50,
                        },
                        "default_severity_range": {
                            "type": "array",
                            "items": [
                                {"type": "integer", "minimum": 1, "maximum": 10},
                                {"type": "integer", "minimum": 1, "maximum": 10},
                            ],
                            "minItems": 2,
                            "maxItems": 2,
                        },
                        "benchmark_dimensions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 3,
                        },
                        "sub_types": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/SubTypeDef"},
                            "minItems": 4,
                            "maxItems": 8,
                        },
                    },
                },
                "SubTypeDef": {
                    "type": "object",
                    "required": ["id", "name", "description"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique sub-type identifier",
                        },
                        "name": {
                            "type": "string",
                            "description": "Sub-type display name",
                        },
                        "description": {
                            "type": "string",
                            "description": "Sub-type description",
                            "minLength": 30,
                        },
                        "default_severity_range": {
                            "type": "array",
                            "items": [
                                {"type": "integer", "minimum": 1, "maximum": 10},
                                {"type": "integer", "minimum": 1, "maximum": 10},
                            ],
                            "minItems": 2,
                            "maxItems": 2,
                        },
                    },
                },
            },
        }

    @classmethod
    def get_category_schema(cls) -> Dict[str, Any]:
        """Get the JSON Schema for a single category definition.

        Returns:
            JSON Schema dict for category validation.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "https://contractriskanalyzer.com/schemas/category/v1.json",
            "title": "Risk Category Definition",
            "type": "object",
            "required": ["id", "name", "description", "sub_types"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string", "minLength": 50},
                "default_severity_range": {
                    "type": "array",
                    "items": [
                        {"type": "integer", "minimum": 1, "maximum": 10},
                        {"type": "integer", "minimum": 1, "maximum": 10},
                    ],
                    "minItems": 2,
                    "maxItems": 2,
                },
                "benchmark_dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 3,
                },
                "sub_types": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/SubTypeDef"},
                    "minItems": 4,
                    "maxItems": 8,
                },
            },
            "definitions": {
                "SubTypeDef": {
                    "type": "object",
                    "required": ["id", "name", "description"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string", "minLength": 30},
                        "default_severity_range": {
                            "type": "array",
                            "items": [
                                {"type": "integer", "minimum": 1, "maximum": 10},
                                {"type": "integer", "minimum": 1, "maximum": 10},
                            ],
                            "minItems": 2,
                            "maxItems": 2,
                        },
                    },
                }
            },
        }

    @classmethod
    def validate_taxonomy(cls, taxonomy_dict: Dict[str, Any]) -> bool:
        """Validate a taxonomy dictionary against the schema.

        Performs structural validation to ensure the taxonomy
        conforms to the expected schema.

        Args:
            taxonomy_dict: The taxonomy data to validate.

        Returns:
            True if valid, raises ValueError if invalid.
        """
        errors: list[str] = []

        # Check version
        if "version" not in taxonomy_dict:
            errors.append("Missing 'version' field")

        # Check categories exist
        categories = taxonomy_dict.get("categories")
        if not categories:
            errors.append("Missing or empty 'categories' field")
            if errors:
                raise ValueError("; ".join(errors))
            return False

        # Check category count
        if len(categories) != 12:
            errors.append(
                f"Expected 12 categories, got {len(categories)}"
            )

        # Validate each category
        required_cat_fields = {"id", "name", "description", "sub_types"}
        required_sub_fields = {"id", "name", "description"}

        for cat_id, cat in categories.items():
            missing = required_cat_fields - set(cat.keys())
            if missing:
                errors.append(
                    f"Category '{cat_id}' missing fields: {missing}"
                )

            sub_types = cat.get("sub_types", [])
            if len(sub_types) < 4 or len(sub_types) > 8:
                errors.append(
                    f"Category '{cat_id}' has {len(sub_types)} sub-types "
                    f"(expected 4-8)"
                )

            for sub in sub_types:
                missing = required_sub_fields - set(sub.keys())
                if missing:
                    errors.append(
                        f"Sub-type in '{cat_id}' missing fields: {missing}"
                    )

        if errors:
            raise ValueError("Taxonomy validation failed: " + "; ".join(errors))

        return True

    @classmethod
    def to_json(cls, taxonomy_dict: Dict[str, Any], indent: int = 2) -> str:
        """Serialize taxonomy to formatted JSON string.

        Args:
            taxonomy_dict: The taxonomy data.
            indent: JSON indentation level.

        Returns:
            Formatted JSON string.
        """
        return json.dumps(taxonomy_dict, indent=indent, default=str)
