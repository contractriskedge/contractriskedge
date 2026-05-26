"""User override mechanism for auto-classification results.

Allows users to override auto-detected classifications for deal size,
industry, counterparty type, and contract type with manual values.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import (
    ContractType,
    IndustryCategory,
    CounterpartyType,
)

logger = logging.getLogger(__name__)


@dataclass
class ClassificationOverride:
    """A user override for an auto-classification field."""

    document_id: str
    field_name: str  # deal_size, industry, counterparty_type, contract_type
    original_value: str
    overridden_value: str
    overridden_by: str
    overridden_at: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""
    override_id: str = ""


class OverrideManager:
    """Manages user overrides for auto-classification results.

    Allows users to override auto-detected classifications and tracks
    override history for audit purposes.

    Usage:
        manager = OverrideManager()
        manager.set_override(
            document_id="doc-123",
            field_name="industry",
            original_value="technology",
            overridden_value="healthcare",
            overridden_by="user@example.com",
            reason="Company is a healthcare technology provider",
        )
        override = manager.get_override("doc-123", "industry")
    """

    # Fields that support overrides
    OVERRIDABLE_FIELDS = {
        "deal_size": ["small", "medium", "large", "enterprise", "mega"],
        "industry": [cat.value for cat in IndustryCategory],
        "counterparty_type": [ct.value for ct in CounterpartyType],
        "contract_type": [ct.value for ct in ContractType],
    }

    def __init__(self) -> None:
        """Initialize the override manager."""
        self._overrides: Dict[str, ClassificationOverride] = {}
        self._override_history: Dict[str, List[ClassificationOverride]] = {}

    def set_override(
        self,
        document_id: str,
        field_name: str,
        original_value: str,
        overridden_value: str,
        overridden_by: str,
        reason: str = "",
    ) -> ClassificationOverride:
        """Set a classification override for a document.

        Args:
            document_id: The document identifier.
            field_name: The field to override (deal_size, industry, etc.).
            original_value: The original auto-classified value.
            overridden_value: The user's manual value.
            overridden_by: User identifier making the override.
            reason: Optional reason for the override.

        Returns:
            The created ClassificationOverride.

        Raises:
            ValueError: If the field or value is not valid for override.
        """
        if field_name not in self.OVERRIDABLE_FIELDS:
            raise ValueError(
                f"Field '{field_name}' is not overridable. "
                f"Valid fields: {list(self.OVERRIDABLE_FIELDS.keys())}"
            )

        valid_values = self.OVERRIDABLE_FIELDS[field_name]
        if overridden_value not in valid_values:
            raise ValueError(
                f"Invalid value '{overridden_value}' for field '{field_name}'. "
                f"Valid values: {valid_values}"
            )

        import uuid
        override = ClassificationOverride(
            document_id=document_id,
            field_name=field_name,
            original_value=original_value,
            overridden_value=overridden_value,
            overridden_by=overridden_by,
            reason=reason,
            override_id=str(uuid.uuid4()),
        )

        # Store override
        key = self._override_key(document_id, field_name)
        self._overrides[key] = override

        # Add to history
        self._override_history.setdefault(key, []).append(override)

        logger.info(
            "Override set: %s/%s: %s -> %s (by %s)",
            document_id, field_name, original_value, overridden_value,
            overridden_by,
        )

        return override

    def get_override(
        self,
        document_id: str,
        field_name: str,
    ) -> Optional[ClassificationOverride]:
        """Get the current override for a document field.

        Args:
            document_id: The document identifier.
            field_name: The field name.

        Returns:
            ClassificationOverride if set, None otherwise.
        """
        key = self._override_key(document_id, field_name)
        return self._overrides.get(key)

    def get_applied_value(
        self,
        document_id: str,
        field_name: str,
        auto_classified_value: str,
    ) -> str:
        """Get the effective value, considering any override.

        Args:
            document_id: The document identifier.
            field_name: The field name.
            auto_classified_value: The auto-classified value.

        Returns:
            The overridden value if set, otherwise the auto-classified value.
        """
        override = self.get_override(document_id, field_name)
        if override is not None:
            return override.overridden_value
        return auto_classified_value

    def remove_override(
        self,
        document_id: str,
        field_name: str,
        removed_by: str,
    ) -> bool:
        """Remove an override, reverting to auto-classification.

        Args:
            document_id: The document identifier.
            field_name: The field name.
            removed_by: User removing the override.

        Returns:
            True if an override was removed, False if none existed.
        """
        key = self._override_key(document_id, field_name)
        override = self._overrides.pop(key, None)
        if override is not None:
            logger.info(
                "Override removed: %s/%s (by %s)",
                document_id, field_name, removed_by,
            )
            return True
        return False

    def get_history(
        self,
        document_id: str,
        field_name: str,
    ) -> List[ClassificationOverride]:
        """Get the full override history for a document field.

        Args:
            document_id: The document identifier.
            field_name: The field name.

        Returns:
            List of ClassificationOverride in chronological order.
        """
        key = self._override_key(document_id, field_name)
        return list(self._override_history.get(key, []))

    def get_all_overrides(
        self, document_id: Optional[str] = None
    ) -> List[ClassificationOverride]:
        """Get all overrides, optionally filtered by document.

        Args:
            document_id: Optional document filter.

        Returns:
            List of ClassificationOverride objects.
        """
        if document_id:
            return [
                o for o in self._overrides.values()
                if o.document_id == document_id
            ]
        return list(self._overrides.values())

    def to_json(self) -> str:
        """Serialize overrides to JSON.

        Returns:
            JSON string.
        """
        data = {
            "overrides": [
                {
                    "document_id": o.document_id,
                    "field_name": o.field_name,
                    "original_value": o.original_value,
                    "overridden_value": o.overridden_value,
                    "overridden_by": o.overridden_by,
                    "overridden_at": o.overridden_at.isoformat(),
                    "reason": o.reason,
                    "override_id": o.override_id,
                }
                for o in self._overrides.values()
            ]
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def _override_key(document_id: str, field_name: str) -> str:
        """Generate a unique key for an override.

        Args:
            document_id: Document identifier.
            field_name: Field name.

        Returns:
            Composite key string.
        """
        return f"{document_id}::{field_name}"
