"""Model versioning, metadata management, and rollback support.

Provides a model registry for tracking model versions, storing
metadata, managing deployments, and supporting rollback operations.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelVersion:
    """A versioned model entry in the registry."""

    model_id: str
    version: str
    model_type: str  # 'lora', 'full', 'embedding'
    base_model: str
    description: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    metrics: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    status: str = "staging"  # staging, production, archived, rolled_back
    path: str = ""
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_version: Optional[str] = None
    deployed_by: Optional[str] = None
    deployed_at: Optional[datetime] = None


class ModelRegistry:
    """Registry for managing model versions and deployments.

    Provides version tracking, metadata storage, deployment management,
    and rollback capabilities for ML models.

    Usage:
        registry = ModelRegistry(storage_path="./model_registry")
        version = registry.register_model(
            model_id="contract-risk-lora-v1",
            model_type="lora",
            base_model="mistralai/Mistral-7B-v0.1",
            path="/path/to/model",
            metrics={"accuracy": 0.89, "f1": 0.87},
        )
        registry.promote_to_production("contract-risk-lora-v1")
    """

    def __init__(self, storage_path: str = "./model_registry") -> None:
        """Initialize the model registry.

        Args:
            storage_path: Path to store registry data.
        """
        self._storage_path = storage_path
        self._registry_file = os.path.join(storage_path, "registry.json")
        self._versions: Dict[str, ModelVersion] = {}
        self._production_model: Optional[str] = None
        self._load_registry()

    def _load_registry(self) -> None:
        """Load registry from disk."""
        if os.path.exists(self._registry_file):
            try:
                with open(self._registry_file) as f:
                    data = json.load(f)
                for v_data in data.get("versions", []):
                    version = ModelVersion(**v_data)
                    self._versions[version.model_id] = version
                self._production_model = data.get("production_model")
                logger.info(
                    "Loaded registry with %d versions",
                    len(self._versions),
                )
            except Exception as exc:
                logger.warning("Failed to load registry: %s", exc)

    def _save_registry(self) -> None:
        """Save registry to disk."""
        os.makedirs(self._storage_path, exist_ok=True)
        data = {
            "production_model": self._production_model,
            "updated_at": datetime.utcnow().isoformat(),
            "versions": [
                {
                    "model_id": v.model_id,
                    "version": v.version,
                    "model_type": v.model_type,
                    "base_model": v.base_model,
                    "description": v.description,
                    "created_at": v.created_at.isoformat(),
                    "metrics": v.metrics,
                    "tags": v.tags,
                    "status": v.status,
                    "path": v.path,
                    "checksum": v.checksum,
                    "metadata": v.metadata,
                    "parent_version": v.parent_version,
                    "deployed_by": v.deployed_by,
                    "deployed_at": (
                        v.deployed_at.isoformat()
                        if v.deployed_at else None
                    ),
                }
                for v in self._versions.values()
            ],
        }
        with open(self._registry_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def register_model(
        self,
        model_id: str,
        model_type: str,
        base_model: str,
        path: str,
        description: str = "",
        metrics: Optional[Dict[str, float]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_version: Optional[str] = None,
    ) -> ModelVersion:
        """Register a new model version.

        Args:
            model_id: Unique model identifier.
            model_type: Type of model ('lora', 'full', 'embedding').
            base_model: Base model name.
            path: Path to model files.
            description: Human-readable description.
            metrics: Evaluation metrics for this version.
            tags: Tags for categorization.
            metadata: Additional metadata.
            parent_version: Optional parent version ID.

        Returns:
            The registered ModelVersion.
        """
        # Compute checksum of model files
        checksum = self._compute_model_checksum(path)

        version = ModelVersion(
            model_id=model_id,
            version=model_id.split("-v")[-1] if "-v" in model_id else "1.0.0",
            model_type=model_type,
            base_model=base_model,
            description=description,
            metrics=metrics or {},
            tags=tags or [],
            status="staging",
            path=path,
            checksum=checksum,
            metadata=metadata or {},
            parent_version=parent_version,
        )

        self._versions[model_id] = version
        self._save_registry()

        logger.info(
            "Registered model '%s' (type=%s, base=%s)",
            model_id,
            model_type,
            base_model,
        )
        return version

    def promote_to_production(
        self,
        model_id: str,
        deployed_by: Optional[str] = None,
    ) -> bool:
        """Promote a model version to production.

        Args:
            model_id: The model to promote.
            deployed_by: Who deployed the model.

        Returns:
            True if promotion was successful.
        """
        version = self._versions.get(model_id)
        if version is None:
            logger.error("Model '%s' not found in registry", model_id)
            return False

        # Archive current production model
        if self._production_model:
            current = self._versions.get(self._production_model)
            if current:
                current.status = "archived"
                logger.info(
                    "Archived previous production model '%s'",
                    self._production_model,
                )

        # Promote new model
        version.status = "production"
        version.deployed_by = deployed_by
        version.deployed_at = datetime.utcnow()
        self._production_model = model_id
        self._save_registry()

        logger.info(
            "Promoted model '%s' to production", model_id
        )
        return True

    def rollback(self, model_id: str) -> bool:
        """Rollback to a specific model version.

        Args:
            model_id: The model version to rollback to.

        Returns:
            True if rollback was successful.
        """
        version = self._versions.get(model_id)
        if version is None:
            logger.error("Cannot rollback: model '%s' not found", model_id)
            return False

        # Archive current production
        if self._production_model:
            current = self._versions.get(self._production_model)
            if current:
                current.status = "rolled_back"

        # Restore target version
        version.status = "production"
        self._production_model = model_id
        self._save_registry()

        logger.info(
            "Rolled back to model '%s' (previous: %s)",
            model_id,
            self._production_model,
        )
        return True

    def get_version(self, model_id: str) -> Optional[ModelVersion]:
        """Get a specific model version.

        Args:
            model_id: The model identifier.

        Returns:
            ModelVersion or None.
        """
        return self._versions.get(model_id)

    def get_production_model(self) -> Optional[ModelVersion]:
        """Get the current production model.

        Returns:
            Current production ModelVersion or None.
        """
        if self._production_model:
            return self._versions.get(self._production_model)
        return None

    def list_versions(
        self,
        status: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[ModelVersion]:
        """List model versions with optional filters.

        Args:
            status: Optional status filter.
            model_type: Optional model type filter.

        Returns:
            List of matching ModelVersions.
        """
        versions = list(self._versions.values())

        if status:
            versions = [v for v in versions if v.status == status]
        if model_type:
            versions = [v for v in versions if v.model_type == model_type]

        return sorted(
            versions,
            key=lambda v: v.created_at,
            reverse=True,
        )

    def get_version_history(self, model_id: str) -> List[ModelVersion]:
        """Get the version history for a model lineage.

        Args:
            model_id: Starting model ID.

        Returns:
            List of versions in the lineage.
        """
        history: list[ModelVersion] = []
        current_id: Optional[str] = model_id

        while current_id:
            version = self._versions.get(current_id)
            if version:
                history.append(version)
                current_id = version.parent_version
            else:
                break

        return history

    def delete_version(self, model_id: str) -> bool:
        """Delete a model version from the registry.

        Args:
            model_id: The model to delete.

        Returns:
            True if deletion was successful.
        """
        if model_id == self._production_model:
            logger.error("Cannot delete production model")
            return False

        version = self._versions.pop(model_id, None)
        if version is None:
            return False

        self._save_registry()
        logger.info("Deleted model '%s' from registry", model_id)
        return True

    def _compute_model_checksum(self, path: str) -> str:
        """Compute SHA-256 checksum of model files.

        Args:
            path: Path to model directory or file.

        Returns:
            SHA-256 hex digest.
        """
        if not os.path.exists(path):
            return ""

        sha256 = hashlib.sha256()

        if os.path.isfile(path):
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
        elif os.path.isdir(path):
            for root, _, files in sorted(os.walk(path)):
                for filename in sorted(files):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "rb") as f:
                            for chunk in iter(lambda: f.read(8192), b""):
                                sha256.update(chunk)
                    except (IOError, OSError):
                        pass

        return sha256.hexdigest()

    def export_registry(self, output_path: str) -> None:
        """Export the registry to a JSON file.

        Args:
            output_path: Path to export to.
        """
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "production_model": self._production_model,
            "version_count": len(self._versions),
            "versions": [
                {
                    "model_id": v.model_id,
                    "version": v.version,
                    "model_type": v.model_type,
                    "base_model": v.base_model,
                    "status": v.status,
                    "metrics": v.metrics,
                    "tags": v.tags,
                }
                for v in self._versions.values()
            ],
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info("Registry exported to %s", output_path)

    @property
    def summary(self) -> Dict[str, Any]:
        """Get a summary of the registry.

        Returns:
            Dict with registry statistics.
        """
        status_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}

        for v in self._versions.values():
            status_counts[v.status] = status_counts.get(v.status, 0) + 1
            type_counts[v.model_type] = type_counts.get(v.model_type, 0) + 1

        production = self.get_production_model()

        return {
            "total_versions": len(self._versions),
            "production_model": production.model_id if production else None,
            "production_metrics": production.metrics if production else {},
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "storage_path": self._storage_path,
        }
