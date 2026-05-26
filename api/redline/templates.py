"""Template manager with versioning for redline prompt templates.

Manages versioned prompt templates, supports template migration between
versions, and provides template registration and lookup capabilities.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import ClauseType
from .prompts import RedlinePromptSet, RedlinePromptTemplates

logger = logging.getLogger(__name__)


@dataclass
class TemplateVersion:
    """A versioned snapshot of a prompt template.

    Tracks the evolution of prompt templates over time, allowing
    rollback and audit of template changes.
    """

    clause_type: ClauseType
    version: str
    system_prompt_hash: str
    user_prompt_hash: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    change_notes: str = ""
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class TemplateVersionError(Exception):
    """Raised when a template version operation fails."""

    def __init__(self, message: str, clause_type: Optional[ClauseType] = None) -> None:
        self.clause_type = clause_type
        super().__init__(message)


class TemplateManager:
    """Manages versioned redline prompt templates.

    Supports registering new template versions, retrieving specific
    versions, rolling back to previous versions, and listing version
    history for each clause type.

    Usage:
        manager = TemplateManager()
        version = manager.register_version(prompt_set, "Initial templates")
        active = manager.get_active_version(ClauseType.LIABILITY_CAPS)
        history = manager.get_version_history(ClauseType.INDEMNIFICATION)
        rolled_back = manager.rollback(ClauseType.CONFIDENTIALITY, "1.0.0")
    """

    def __init__(self, initial_templates: Optional[RedlinePromptTemplates] = None) -> None:
        """Initialize the template manager.

        Args:
            initial_templates: Optional pre-built templates. If not provided,
                               a new RedlinePromptTemplates instance is created.
        """
        self._templates: RedlinePromptTemplates = (
            initial_templates or RedlinePromptTemplates()
        )
        self._versions: Dict[ClauseType, List[TemplateVersion]] = {
            ct: [] for ct in ClauseType
        }
        self._versioned_prompts: Dict[str, RedlinePromptSet] = {}
        self._current_versions: Dict[ClauseType, str] = {}

        # Register initial versions
        self._register_initial_versions()

    def _register_initial_versions(self) -> None:
        """Register version 1.0.0 for all clause types."""
        for clause_type in ClauseType:
            try:
                prompt_set = self._templates.get_prompt(clause_type)
                version = TemplateVersion(
                    clause_type=clause_type,
                    version="1.0.0",
                    system_prompt_hash=self._compute_hash(prompt_set.system_prompt),
                    user_prompt_hash=self._compute_hash(prompt_set.user_prompt_template),
                    change_notes="Initial template version",
                    is_active=True,
                )
                version_key = self._version_key(clause_type, "1.0.0")
                self._versioned_prompts[version_key] = prompt_set
                self._versions[clause_type].append(version)
                self._current_versions[clause_type] = "1.0.0"
            except ValueError:
                logger.warning("No prompt set found for %s, skipping", clause_type)

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute a simple hash of template content.

        Args:
            content: The template content to hash.

        Returns:
            A hex digest string.
        """
        import hashlib
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _version_key(clause_type: ClauseType, version: str) -> str:
        """Generate a unique key for a versioned template.

        Args:
            clause_type: The clause type.
            version: The version string.

        Returns:
            A composite key string.
        """
        return f"{clause_type.value}::{version}"

    def register_version(
        self,
        clause_type: ClauseType,
        system_prompt: str,
        user_prompt_template: str,
        chain_of_thought: str,
        output_format_spec: str,
        change_notes: str = "",
    ) -> TemplateVersion:
        """Register a new version of a prompt template.

        Args:
            clause_type: The clause type to register.
            system_prompt: The system prompt content.
            user_prompt_template: The user prompt template content.
            chain_of_thought: The chain-of-thought reasoning instructions.
            output_format_spec: The output format specification.
            change_notes: Description of changes in this version.

        Returns:
            The newly created TemplateVersion.

        Raises:
            TemplateVersionError: If the version already exists or content is invalid.
        """
        if not system_prompt.strip() or not user_prompt_template.strip():
            raise TemplateVersionError(
                "System prompt and user prompt must not be empty",
                clause_type=clause_type,
            )

        current_version = self._current_versions.get(clause_type, "0.0.0")
        parts = current_version.split(".")
        new_version = f"{parts[0]}.{int(parts[1]) + 1}.0"

        version_key = self._version_key(clause_type, new_version)
        if version_key in self._versioned_prompts:
            raise TemplateVersionError(
                f"Version {new_version} already exists for {clause_type}",
                clause_type=clause_type,
            )

        prompt_set = RedlinePromptSet(
            clause_type=clause_type,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            chain_of_thought=chain_of_thought,
            output_format_spec=output_format_spec,
            version=new_version,
        )

        # Deactivate current version
        for v in self._versions.get(clause_type, []):
            if v.is_active:
                v.is_active = False

        version = TemplateVersion(
            clause_type=clause_type,
            version=new_version,
            system_prompt_hash=self._compute_hash(system_prompt),
            user_prompt_hash=self._compute_hash(user_prompt_template),
            change_notes=change_notes or f"Updated to version {new_version}",
            is_active=True,
        )

        self._versioned_prompts[version_key] = prompt_set
        self._versions.setdefault(clause_type, []).append(version)
        self._current_versions[clause_type] = new_version

        logger.info(
            "Registered %s version %s: %s",
            clause_type.value, new_version, change_notes,
        )
        return version

    def get_active_version(self, clause_type: ClauseType) -> Optional[TemplateVersion]:
        """Get the active version for a clause type.

        Args:
            clause_type: The clause type to query.

        Returns:
            The active TemplateVersion, or None if not found.
        """
        versions = self._versions.get(clause_type, [])
        for v in reversed(versions):
            if v.is_active:
                return v
        return None

    def get_active_prompt(self, clause_type: ClauseType) -> Optional[RedlinePromptSet]:
        """Get the active prompt set for a clause type.

        Args:
            clause_type: The clause type to query.

        Returns:
            The active RedlinePromptSet, or None if not found.
        """
        version = self.get_active_version(clause_type)
        if version is None:
            return None
        version_key = self._version_key(clause_type, version.version)
        return self._versioned_prompts.get(version_key)

    def get_version(
        self, clause_type: ClauseType, version: str
    ) -> Optional[RedlinePromptSet]:
        """Get a specific version of a prompt set.

        Args:
            clause_type: The clause type.
            version: The version string to retrieve.

        Returns:
            The RedlinePromptSet for the specified version, or None.
        """
        version_key = self._version_key(clause_type, version)
        return self._versioned_prompts.get(version_key)

    def rollback(
        self, clause_type: ClauseType, target_version: str
    ) -> RedlinePromptSet:
        """Rollback a clause type to a previous template version.

        Args:
            clause_type: The clause type to rollback.
            target_version: The version to rollback to.

        Returns:
            The RedlinePromptSet for the target version.

        Raises:
            TemplateVersionError: If the target version doesn't exist.
        """
        version_key = self._version_key(clause_type, target_version)
        prompt_set = self._versioned_prompts.get(version_key)
        if prompt_set is None:
            raise TemplateVersionError(
                f"Version {target_version} not found for {clause_type}",
                clause_type=clause_type,
            )

        # Deactivate current version
        for v in self._versions.get(clause_type, []):
            if v.is_active:
                v.is_active = False

        # Activate target version
        for v in self._versions.get(clause_type, []):
            if v.version == target_version:
                v.is_active = True
                break

        self._current_versions[clause_type] = target_version
        logger.info(
            "Rolled back %s to version %s",
            clause_type.value, target_version,
        )
        return prompt_set

    def get_version_history(self, clause_type: ClauseType) -> List[TemplateVersion]:
        """Get the full version history for a clause type.

        Args:
            clause_type: The clause type to query.

        Returns:
            List of TemplateVersion objects in chronological order.
        """
        return list(self._versions.get(clause_type, []))

    def get_all_active_versions(self) -> Dict[ClauseType, TemplateVersion]:
        """Get the active version for all clause types.

        Returns:
            Dict mapping clause types to their active TemplateVersion.
        """
        result: Dict[ClauseType, TemplateVersion] = {}
        for clause_type in ClauseType:
            version = self.get_active_version(clause_type)
            if version is not None:
                result[clause_type] = version
        return result

    def to_json(self) -> str:
        """Serialize the template manager state to JSON.

        Returns:
            JSON string of the current state.
        """
        data: Dict[str, Any] = {
            "current_versions": {
                ct.value: v for ct, v in self._current_versions.items()
            },
            "versions": {
                ct.value: [
                    {
                        "version": v.version,
                        "system_prompt_hash": v.system_prompt_hash,
                        "user_prompt_hash": v.user_prompt_hash,
                        "created_at": v.created_at.isoformat(),
                        "change_notes": v.change_notes,
                        "is_active": v.is_active,
                    }
                    for v in versions
                ]
                for ct, versions in self._versions.items()
            },
        }
        return json.dumps(data, indent=2)
